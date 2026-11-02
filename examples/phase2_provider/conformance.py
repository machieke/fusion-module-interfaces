"""Shared invariant cases, used by repository and installed HTTPS qualification."""
import argparse
import json
from pathlib import Path
import time
import uuid

from fusion.contracts import ContractError
from fusion.ports import Mutation
from fusion.preview_client import AtomFeedClient, Endpoint
from fusion.registry import descriptor_read


def must_fail(code, call):
    try:
        call()
    except ContractError as exc:
        assert exc.code == code, (code, exc.code)
    else:
        raise AssertionError('Expected ' + code)


def run_contract_cases(atoms, scope, *, namespace=None):
    """Exercise only declared ports; never inspect provider files or SQL."""
    namespace = namespace or str(uuid.uuid4())
    start = atoms.head(scope)
    command = Mutation(scope, 'sdk/' + namespace)
    data = b'approved synthetic independent-provider conformance'
    write = atoms.create(command, 'application/synthetic', data)
    assert atoms.create(command, 'application/synthetic', data) == write
    must_fail('CONFLICT', lambda: atoms.create(command, 'application/synthetic', b'changed'))
    ref = write['ref']
    assert atoms.get(ref).bytes == data
    assert atoms.getMany((ref, ref))[0].bytes == data
    assert atoms.availability(ref)['available'] is True
    through = atoms.head(scope)
    assert through['sequence'] == start['sequence'] + 1
    page = atoms.readCommits(scope, start['sequence'], through, 1)
    assert page['complete'] and page['records'][0]['ref'] == ref
    for number in range(2):
        atoms.create(Mutation(scope, f'sdk/{namespace}/{number}'), 'application/synthetic', str(number).encode())
    # Previously selected source head stays fixed despite subsequent appends.
    assert atoms.readCommits(scope, start['sequence'], through, 1) == page
    must_fail('UNAUTHORIZED', lambda: atoms.get({**ref, 'scope_ref': scope + '-foreign'}))
    must_fail('CONFLICT', lambda: atoms.get({**ref, 'digest': '0' * 64}))
    return {'status': 'PASS', 'invariant_cases': ['idempotent-create', 'same-key-conflict',
            'verified-hydration', 'ordered-batch', 'availability', 'authoritative-feed',
            'retained-source-head', 'scope-refusal', 'digest-refusal'], 'ref': ref}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client-config', required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.client_config).read_text())
    atoms = AtomFeedClient(Endpoint(**cfg['endpoint']), cfg['credential'], cfg['principal'],
                          cfg['scope'], descriptor_read(cfg['descriptor']),
                          deadline_ms=cfg['deadline_ms'])
    print(json.dumps(run_contract_cases(atoms, cfg['scope']), sort_keys=True))
