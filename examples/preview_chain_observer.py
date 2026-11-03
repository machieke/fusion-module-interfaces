"""Independent, read-only observation of an approved synthetic chain trace.

Run ``python -m examples.preview_chain_observer --trace TRACE --config CONFIG``.
TRACE is exactly {reg, saved_intent, final_observation}, exported by the
authorized operator. CONFIG is exactly {profile, atoms, node_endpoint}; profile
is synthetic-chain-readback/1. atoms is the existing preview AtomStorage client
configuration (with an explicit optional feed_profile), with credential replaced by credential_file OR credential_env.
The mounted credential must have only atom.storage.get authority. Neither an
approval label nor this read-only example grants signing/submission authority.

The node endpoint is the isolated f1r3node Kubernetes service on port 40403 (or
loopback for an explicitly isolated composition). Namespace NetworkPolicy must
already isolate it. This example performs two AtomStorage reads and one bounded
observe_effect call, without retries, signing, preparation, mutation or journals.
It does not re-evaluate retrieval correctness or claim validator computation.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from fusion.adapters.f1r3 import F1R3HTTP
from fusion.adapters import f1r3_m4 as m4
from fusion.chain_services import observation
from fusion.contracts import ContractError, canonical, digest, label, require
from fusion.preview_artifact_contracts import PROFILE as ARTIFACT, encode, record
from fusion.preview_atoms import client as atoms_client
from fusion.preview_chain import registration
from fusion.preview_client import strict_json
from fusion.registry import selection_token
from fusion.responses import envelope


PROFILE = 'synthetic-chain-readback/1'
LIMITS = dict(phloPrice=1, phloLimit=10000000, validAfterBlockNumber=0)
PROTOBUF_SHA256 = 'ba9b8ebd44e73cabac064ec00e4f93d9a08a8681bcb3bce3eb5dca6366ba23e6'


def fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()), 'INVALID_ARGUMENT')


def _trace_plan(trace):
    """Validate public trace and reconstruct its fixed, already signed plan.

    The historical signing authorization may have expired: this observer only
    requests currently authorized storage reads and public isolated node reads.
    The expiry is retained, never renewed or reused to authorize submission.
    """
    fields(trace, 'reg saved_intent final_observation')
    reg = trace['reg']
    require(type(reg) is dict and type(reg.get('approved')) is dict, 'INVALID_ARGUMENT')
    scope = reg['approved'].get('scope_ref')
    require(type(scope) is str and scope.startswith('synthetic-'), 'UNAUTHORIZED')
    approved = registration(reg, scope)
    binding = reg['binding']
    fields(binding, 'profile selection chain signer limits operation protobuf_sha256 owner_journal authority')
    require(binding['profile'] == m4.PROFILE and binding['selection'] == selection_token(m4.DESCRIPTOR), 'UNSUPPORTED_PROFILE')
    fields(binding['chain'], 'network shard genesis source profile')
    require(binding['chain']['network'] == 'fusion-m4-isolated' and binding['chain']['shard'] == 'fusion-m4'
            and binding['chain']['source'] == m4.SOURCE and binding['chain']['profile'] == m4.PROFILE
            and m4.hex64(binding['chain']['genesis']), 'UNSUPPORTED_PROFILE')
    require(binding['limits'] == LIMITS and all(type(v) is int for v in binding['limits'].values()), 'UNSUPPORTED_PROFILE')
    require(type(binding['signer']) is str and re.fullmatch('04[0-9a-f]{128}', binding['signer']) is not None
            and label(binding['operation']), 'INVALID_ARGUMENT')
    require(binding['protobuf_sha256'] == PROTOBUF_SHA256, 'UNSUPPORTED_PROFILE')
    require(type(binding['owner_journal']) is str, 'INVALID_ARGUMENT')  # Descriptive only; never opened.
    saved = trace['saved_intent']
    fields(saved, 'deploy_id read_name receipt')
    require(type(saved['deploy_id']) is str and re.fullmatch('[0-9a-f]{128,144}', saved['deploy_id']) is not None
            and m4.hex64(saved['read_name']), 'INVALID_ARGUMENT')
    if saved['receipt'] is not None:
        receipt = observation(saved['receipt'])
        require(receipt.deploy_id == saved['deploy_id'], 'CONFLICT')
    final = observation(trace['final_observation'])
    require(final.effect_finality == 'finalized' and final.deploy_id == saved['deploy_id'], 'NOT_AVAILABLE')
    evidence = final.evidence
    require(evidence.get('profile') == m4.PROFILE and evidence.get('source') == 'isolated-node-http', 'UNSUPPORTED_PROFILE')
    require(evidence.get('value') == dict(namespace=m4.NAMESPACE, operation=binding['operation'], digest=approved.commitment_digest), 'CONFLICT')
    require(evidence.get('effect_query') == dict(name={'UnforgPrivate': {'data': saved['read_name']}},
            blockHash=final.inclusion_block, usePreStateHash=False), 'CONFLICT')
    require(evidence['effect'].get('expr') == m4.expected_expr(binding['operation'], approved.commitment_digest), 'CONFLICT')
    require(m4.hex64(evidence['effect']['block'].get('postStateHash')), 'INVALID_ARGUMENT')
    inclusion = evidence['inclusion']
    term = 'new commitment in { commitment!(("' + m4.NAMESPACE + '", "' + binding['operation'] + '", "' + approved.commitment_digest + '")) }'
    require(inclusion.get('term') == term and inclusion.get('deployer') == binding['signer']
            and inclusion.get('sigAlgorithm') == 'secp256k1'
            and all(type(inclusion.get(k)) is int and inclusion[k] == v for k, v in LIMITS.items()), 'CONFLICT')
    require(type(inclusion.get('timestamp')) is int and 0 < inclusion['timestamp'] < 2**63, 'INVALID_ARGUMENT')
    # The pinned node's DeployResponse does not return shardId. Chain identity
    # and the inclusion block's post-state bind the shard independently below.
    if 'shardId' in inclusion:
        require(inclusion['shardId'] == binding['chain']['shard'], 'CONFLICT')
    plan = dict(term=term, timestamp=inclusion['timestamp'], **LIMITS,
                shardId=binding['chain']['shard'], expiration_timestamp=None)
    signed = dict(data=plan, deployer=binding['signer'], sigAlgorithm='secp256k1', signature=saved['deploy_id'])
    return approved, signed


def trace_plan(trace):
    try:
        return _trace_plan(trace)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise ContractError('INVALID_ARGUMENT') from None


def configuration(config, scope):
    """Resolve a separate read credential without placing it in trace/output."""
    fields(config, 'profile atoms node_endpoint')
    require(config['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    atoms = config['atoms']
    require(type(atoms) is dict, 'INVALID_ARGUMENT')
    secret = set(atoms) & {'credential_file', 'credential_env'}
    require(len(secret) == 1 and 'credential' not in atoms, 'UNAUTHORIZED')
    name = next(iter(secret))
    fields(atoms, 'composition principal scope endpoint descriptor ' + name + (' feed_profile' if 'feed_profile' in atoms else ''))
    if 'feed_profile' in atoms:
        from fusion import lookup_contracts as source
        require(atoms['feed_profile'] in (source.FEED,source.SUSTAINED_FEED),'UNSUPPORTED_PROFILE')
    require(atoms['scope'] == scope and label(atoms['principal']), 'UNAUTHORIZED')
    require(type(atoms[name]) is str and atoms[name], 'UNAUTHORIZED')
    if name == 'credential_file':
        with Path(atoms[name]).open('rb') as stream:
            raw = stream.read(258)
        require(len(raw) <= 257, 'UNAUTHORIZED')
        try: credential = raw.decode('ascii').strip()
        except UnicodeError: raise ContractError('UNAUTHORIZED') from None
    else:
        require(re.fullmatch('[A-Z][A-Z0-9_]{0,127}', atoms[name]) is not None, 'UNAUTHORIZED')
        credential = os.environ.get(atoms[name], '')
    require(type(credential) is str and credential.isascii() and 1 <= len(credential) <= 256
            and '\r' not in credential and '\n' not in credential, 'UNAUTHORIZED')
    endpoint = config['node_endpoint']
    require(type(endpoint) is str, 'INVALID_ARGUMENT')
    try: address = urlsplit(endpoint); port = address.port
    except ValueError: raise ContractError('INVALID_ARGUMENT') from None
    require(address.scheme == 'http' and address.username is None and address.password is None
            and not address.path and not address.query and not address.fragment and port == 40403
            and (address.hostname == '127.0.0.1' or re.fullmatch(
                r'f1r3node\.[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\.svc\.cluster\.local', address.hostname or '') is not None), 'UNAUTHORIZED')
    return {**{k:v for k,v in atoms.items() if k != name}, 'credential': credential}, endpoint


def observe(trace, config):
    """A single independent read pass. Unavailable finality is not a pass."""
    approved, signed = trace_plan(trace)
    atoms_config, node_endpoint = configuration(config, approved.scope_ref)
    atoms = atoms_client(atoms_config)
    reg = trace['reg']
    artifact = atoms.get(reg['artifact'])
    envelope(artifact, reg['artifact'])
    require(artifact.content_type == ARTIFACT, 'CONFLICT')
    value = record(strict_json(artifact.bytes), approved.scope_ref)
    require(artifact.bytes == encode(value) and value['sender'] == reg['principal'], 'CONFLICT')
    result = atoms.get(approved.result_ref)
    envelope(result, approved.result_ref)
    require(result.content_type == 'application/json' and result.bytes == canonical(dict(
        digest=digest(artifact.bytes), length=len(artifact.bytes), operation='inspect_atom', provider_version='0.1.0')),
        'CONFLICT')
    require(digest(result.bytes) == approved.commitment_digest, 'CONFLICT')
    actual = m4.observe_effect(F1R3HTTP(node_endpoint), signed, trace['saved_intent']['read_name'],
                              reg['binding']['operation'], approved.commitment_digest, reg['binding']['chain'])
    prior = trace['final_observation']
    if actual.effect_finality == 'finalized':
        require(actual.inclusion_block == prior['inclusion_block'] and
                actual.evidence['effect']['block']['postStateHash'] == prior['evidence']['effect']['block']['postStateHash'], 'CONFLICT')
    return dict(profile=PROFILE, status='PASS' if actual.effect_finality == 'finalized' else 'OBSERVATION_NOT_FINAL',
        trace_sha256=digest(canonical(trace)), scope=approved.scope_ref, approval_record=approved.approval_record,
        artifact_ref=reg['artifact'], artifact_bytes=len(artifact.bytes), inspect_result_ref=approved.result_ref,
        inspect_result_sha256=digest(result.bytes), deploy_id=trace['saved_intent']['deploy_id'],
        read_name=trace['saved_intent']['read_name'], observation=asdict(actual),
        owner_journals_accessed=False, signing_performed=False, submissions=0,
        additional_live_generations=0, independent_reads=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', required=True)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    try:
        inputs = []
        for filename in (args.trace, args.config):
            with Path(filename).open('rb') as stream: inputs.append(strict_json(stream.read(131073)))
        report = observe(*inputs)
    except (ContractError, OSError) as error:
        # Do not print exception text: it could include a credential/file path.
        report = dict(profile=PROFILE, status='FAILED', error=getattr(error, 'code', 'NOT_AVAILABLE'),
                      submissions=0, signing_performed=False, additional_live_generations=0)
    print(json.dumps(report, sort_keys=True), flush=True)
    raise SystemExit(0 if report['status'] == 'PASS' else 1)


if __name__ == '__main__': main()
