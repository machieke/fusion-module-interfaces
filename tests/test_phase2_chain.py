"""Preview exact commitment tests with explicit fake chain/signing/ports.

The actual GeneratedCommitments journal and preview service execute. Chain,
signing protobuf, signature, inspection, AtomStorage and HTTPS are labelled test
substitutions; these tests never claim the real CHAIN or native-workflow gate.
"""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.adapters import f1r3_m4 as m4
from fusion.contracts import ContractError, canonical, digest, require
from fusion.lookup_contracts import make_head
from fusion.ports import Mutation
from fusion import preview_artifact_contracts as artifact
from fusion import preview_chain as chain
from fusion import registry
from fusion import preview_vector_contracts as active, vector_contracts as vector
from fusion.preview_lifecycle import PROFILE as LIFECYCLE
from fusion.registry import selection_token
from integration.single_node import preview_chain_configure as configure
from tests.test_m4_chain import API as HistoricalFakeChain


SCOPE = 'synthetic-chain-port-fixture'
SIGNATURE = 'ab' * 70


class FakeChain(HistoricalFakeChain):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.responses['/api/deploy-finalization-status/' + SIGNATURE] = {
            'state': 'Pending', 'rejection_count': 0, 'latest_block_hash': None}

    def request(self, path, body=None):
        self.calls.append(('request', path, copy.deepcopy(body)))
        return super().request(path, body)

    def submit_signed(self, signed):
        self.calls.append(('submit', canonical(signed)))
        return super().submit_signed(signed)


class PreviewChain(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-chain-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.api = FakeChain()
        self.signs = []
        self.inspection_reads = []
        def authorize(scope, operation):
            require(scope == SCOPE and operation in ('create', 'get'), 'UNAUTHORIZED')
            return 'fixture-artifact-owner'
        self.atoms = FileFeedFixture(self.root / 'fixture-atoms.json',
                                    SimpleNamespace(authorize=authorize))
        result_ref = self.atoms.create(Mutation(SCOPE, 'task-result'), 'text/plain',
                                       b'Labelled synthetic task-result fixture')['ref']
        payload = self.atoms.create(Mutation(SCOPE, 'payload'), 'text/plain',
                                   b'Synthetic marker is amber')['ref']
        view = dict(generation=str(uuid.uuid4()), head=make_head(str(uuid.uuid4()), SCOPE, 2),
            corpus='generated-chain-fixture', embedding=vector.FIXTURE, index=vector.INDEX,
            profile=active.PROFILE, lifecycle=make_head(str(uuid.uuid4()), SCOPE, 1, LIFECYCLE),
            active_digest='a' * 64)
        view['logical'] = digest(canonical({k: v for k, v in view.items() if k != 'generation'}))
        self.artifact = dict(profile=artifact.PROFILE, scope=SCOPE, task=str(uuid.uuid4()),
            query='synthetic marker', sender='A', reporter='B', result_ref=result_ref,
            view=view, observations=[dict(payload_ref=payload, content='Synthetic marker is amber')])
        self.raw = artifact.encode(self.artifact)
        stored = self.atoms.create(Mutation(SCOPE, 'artifact'), artifact.PROFILE, self.raw)
        self.result = self.atoms.create(Mutation(SCOPE, 'inspect-result'), 'application/json',
            canonical(dict(digest=digest(self.raw), length=len(self.raw),
                           operation='inspect_atom', provider_version='0.1.0')))
        self.status = dict(execution='succeeded', error=None)
        self.protobuf = self.root / 'fixture-protobuf.bytes'
        self.protobuf.write_bytes(b'Explicit fixture protobuf identity; no executable source')
        self.binding = dict(profile=m4.PROFILE, selection=selection_token(m4.DESCRIPTOR),
            chain=copy.deepcopy(self.api.chain), signer='04' + 'f' * 128,
            limits=dict(phloPrice=1, phloLimit=10000000, validAfterBlockNumber=0),
            operation='synthetic-task-result-1', protobuf_sha256=digest(self.protobuf.read_bytes()),
            owner_journal=str(self.root / 'owner/commitments.sqlite'),
            authority=dict(purpose='approved-synthetic-agent-artifact',
                           expires_at_ms=time.time_ns() // 1000000 + 600000,
                           artifact_digest=stored['ref']['digest']))
        self.registration = dict(profile=chain.PROFILE, approved=dict(scope_ref=SCOPE,
            result_ref=self.result['ref'], commitment_digest=self.result['ref']['digest'],
            approval_record='synthetic-exact-approval-1'), binding=self.binding,
            job_id='inspect-job-1', result=self.result, artifact=stored['ref'], principal='A')
        state, run = self.root / 'owner', self.root / 'config'
        state.mkdir(); run.mkdir()
        self.ca = self.root / 'ca.crt'; self.ca.write_text('transport-fixture-not-a-certificate')
        self.settings = dict(role='fusion-commitment', peers={'f1r3node': 'fixture-node'},
            preview=dict(scope=SCOPE, inspection=dict(enabled=True),
                         chain=dict(enabled=True, registration=self.registration)))
        self.cfg = {}
        configure.provider(self.settings, self.cfg, state, run, self.token, self.endpoint)
        self.cfg['protobuf'] = str(self.protobuf)
        self.path = run / 'owner.json'
        self.save()
        self.client_path = run / 'commitment-client.json'
        self.command = Mutation(SCOPE, self.binding['operation'])
        self.addCleanup(patch.stopall)
        # Keep fixture receipt identity explicit through the selected catalogue;
        # never relabel fixture payloads as DeTTa receipts.
        catalogue = registry.descriptors
        patch.object(registry, 'descriptors', side_effect=lambda: catalogue(atom_provider='fixture-files')).start()
        patch.object(chain, 'F1R3HTTP', return_value=self.api).start()
        patch.object(chain, 'atoms_client', return_value=self.atoms).start()
        patch.object(chain, 'Inspection', return_value=SimpleNamespace(invoke=self.inspection)).start()
        patch.object(chain, 'signer', return_value=self.sign).start()
        loader = SimpleNamespace(exec_module=lambda _: None)
        util = SimpleNamespace(spec_from_file_location=lambda *_: SimpleNamespace(loader=loader),
                               module_from_spec=lambda _: SimpleNamespace(DeployDataProto=object))
        patch.object(chain, 'importlib', SimpleNamespace(util=util)).start()
        patch.object(chain, 'invoke', side_effect=self.transport).start()

    @staticmethod
    def token(name): return 'fixture-credential-' + name

    def endpoint(self, role): return dict(host=role, port=8443, ca_file=str(self.ca))

    def save(self): self.path.write_bytes(canonical(self.cfg))

    def inspection(self, request):
        self.inspection_reads.append(copy.deepcopy(request))
        require(request['scope_ref'] == SCOPE and request['body']['job_id'] == self.registration['job_id'], 'UNAUTHORIZED')
        require(request['operation'] in ('result', 'status'), 'UNSUPPORTED_OPERATION')
        return copy.deepcopy(self.result if request['operation'] == 'result' else self.status)

    def sign(self, plan):
        # The real owner must have committed its logical identity before the
        # fixture signer can observe it from an independent SQLite connection.
        with sqlite3.connect(self.cfg['journal']) as db:
            self.assertEqual(json.loads(db.execute('SELECT plan FROM m4_intent').fetchone()[0]), plan)
        self.signs.append(copy.deepcopy(plan))
        return dict(data=plan, deployer=self.binding['signer'], signature=SIGNATURE, sigAlgorithm='secp256k1')

    def transport(self, cfg, path, q, deadline=None):
        return json.loads(canonical(chain.Ports(self.path).invoke(path, cfg['credential'], json.loads(canonical(q)))))

    def request(self, operation='submit', body=None):
        if body is None: body = dict(command=asdict(self.command)) if operation == 'submit' else {}
        return dict(profile=chain.PROFILE, selection=selection_token(m4.DESCRIPTOR),
            registration=digest(canonical(self.registration)), operation=operation, body=body)

    def invoke(self, operation='submit', body=None, hook=lambda _: None, credential=None):
        return chain.Ports(self.path, hook).invoke(chain.ROUTE, credential or self.token('caller-token'),
                                                self.request(operation, body))['value']

    def denied(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def intent_row(self):
        with sqlite3.connect(self.cfg['journal']) as db:
            db.row_factory = sqlite3.Row
            return dict(db.execute('SELECT * FROM m4_intent').fetchone())

    def finalized(self, operation=None, commitment=None):
        signed = json.loads(self.intent_row()['signed'])
        block = 'b' * 64
        self.api.responses['/api/deploy-finalization-status/' + SIGNATURE] = {
            'state': 'Finalized', 'rejection_count': 0, 'latest_block_hash': block}
        self.api.responses['/api/deploy/' + SIGNATURE] = dict(
            deployId=SIGNATURE, blockHash=block, blockNumber=1, errored=False, cost=603,
            isFinalized=True, finalizationState='Finalized', rejectionCount=0,
            deployer=signed['deployer'], sigAlgorithm='secp256k1',
            **{k: v for k, v in signed['data'].items() if k != 'expiration_timestamp'})
        self.api.responses['/api/data-at-name-by-block-hash'] = dict(
            expr=m4.expected_expr(operation or self.binding['operation'],
                                  commitment or self.registration['approved']['commitment_digest']),
            block=dict(blockHash=block, blockNumber=1, postStateHash='e' * 64,
                       shardId='fusion-m4', isFinalized=True), cost=0)

    def test_configurator_preserves_read_only_inspection_and_atom_authority(self):
        cfg = self.cfg
        self.assertEqual(cfg['atoms']['principal'], 'commit-observer')
        self.assertEqual(cfg['atoms']['endpoint']['host'], 'fusion-storage')
        self.assertEqual(cfg['principals']['operator']['scopes'][SCOPE],
                         ['consensus.finality.submit', 'consensus.finality.observe'])
        selected = json.loads(Path(cfg['inspection']).read_text())
        self.assertEqual(selected['principal'], 'commit-A')
        self.assertFalse(selected['fallback'])
        self.assertEqual(cfg['node_endpoint'], 'http://fixture-node:40403')
        self.assertNotIn('signer_file', json.loads(self.client_path.read_text()))
        self.assertNotIn('journal', json.loads(self.client_path.read_text()))

    def test_registration_exact_fields_scope_digest_and_authority(self):
        approved = chain.registration(self.registration, SCOPE)
        self.assertEqual(asdict(approved), self.registration['approved'])
        cases = []
        for key in ('approved', 'binding', 'job_id', 'result', 'artifact', 'principal'):
            bad = copy.deepcopy(self.registration); del bad[key]; cases.append((key, bad))
        bad = copy.deepcopy(self.registration); bad['extra'] = True; cases.append(('extra', bad))
        for key, value in (('scope_ref', 'private-A'), ('commitment_digest', 'd' * 64),
                           ('result_ref', {**self.result['ref'], 'id': 'another'})):
            bad = copy.deepcopy(self.registration); bad['approved'][key] = value; cases.append((key, bad))
        for key, value in (('purpose', 'arbitrary-deploy'), ('artifact_digest', '0' * 64),
                           ('expires_at_ms', True)):
            bad = copy.deepcopy(self.registration); bad['binding']['authority'][key] = value; cases.append((key, bad))
        for name, value in cases:
            with self.subTest(name=name), self.assertRaises(ContractError): chain.registration(value, SCOPE)

    def test_registration_malformed_nested_dtos_are_contract_errors(self):
        for key, value in (('approved', None), ('approved', {}), ('result', []),
                           ('artifact', None), ('binding', {}), ('principal', [])):
            bad = copy.deepcopy(self.registration); bad[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ContractError):
                chain.registration(bad, SCOPE)

    def test_missing_registration_wrong_credential_and_exact_hash_deny_before_node(self):
        self.denied('UNAUTHORIZED', self.invoke, credential='wrong-credential')
        q = self.request(); q['registration'] = '0' * 64
        self.denied('CONFLICT', chain.Ports(self.path).invoke, chain.ROUTE, self.token('caller-token'), q)
        self.cfg['registration'] = None; self.save()
        self.denied('UNAUTHORIZED', self.invoke)
        self.assertEqual(self.api.calls, [])
        self.assertFalse(Path(self.cfg['journal']).exists())

    def test_source_result_content_type_exact_bytes_and_inspection_status(self):
        original = copy.deepcopy(self.registration)
        for name in ('artifact-type', 'noncanonical-artifact', 'output-type', 'wrong-output', 'sender'):
            with self.subTest(name=name):
                self.registration = copy.deepcopy(original)
                self.result = copy.deepcopy(original['result'])
                if name in ('artifact-type', 'noncanonical-artifact'):
                    written = self.atoms.create(Mutation(SCOPE, name),
                        'text/plain' if name == 'artifact-type' else artifact.PROFILE,
                        self.raw if name == 'artifact-type' else self.raw + b' ')
                    self.registration['artifact'] = written['ref']
                    self.registration['binding']['authority']['artifact_digest'] = written['ref']['digest']
                elif name == 'sender': self.registration['principal'] = 'B'
                else:
                    written = self.atoms.create(Mutation(SCOPE, name),
                        'text/plain' if name == 'output-type' else 'application/json',
                        self.atoms.get(original['result']['ref']).bytes if name == 'output-type' else b'{}')
                    self.result = written; self.registration['result'] = written
                    self.registration['approved'].update(result_ref=written['ref'], commitment_digest=written['ref']['digest'])
                self.cfg['registration'] = self.registration; self.save()
                with self.assertRaises(ContractError): self.invoke('intent')
                self.assertEqual(self.api.calls, [])
        self.registration = original; self.result = original['result']
        self.cfg['registration'] = original; self.save()
        self.status = dict(execution='queued', error=None)
        self.denied('NOT_AVAILABLE', self.invoke, 'intent')
        self.assertEqual(self.api.calls, [])

    def test_saved_intent_is_read_only_and_rechecks_current_authority(self):
        self.assertIsNone(self.invoke('intent'))
        self.assertEqual(self.api.calls, [])
        self.invoke()
        before = copy.deepcopy(self.api.calls)
        saved = self.invoke('intent')
        self.assertEqual(set(saved), {'deploy_id', 'read_name', 'receipt'})
        self.assertEqual((saved['deploy_id'], saved['read_name']), (SIGNATURE, 'c' * 64))
        self.assertEqual(self.api.calls, before)
        self.cfg['principals']['operator']['scopes'][SCOPE].remove('consensus.finality.observe'); self.save()
        self.denied('UNAUTHORIZED', self.invoke, 'intent')
        self.assertEqual(self.api.calls, before)

    def test_signed_intent_observed_before_exact_replay_without_new_timestamp(self):
        def interrupt(stage):
            if stage == 'after_signed_intent': raise RuntimeError('signed before submit')
        with self.assertRaisesRegex(RuntimeError, 'signed before submit'): self.invoke(hook=interrupt)
        first = self.intent_row()
        self.assertEqual(self.api.sent, [])
        self.assertIsNone(first['receipt'])
        self.assertEqual(self.invoke('intent')['deploy_id'], SIGNATURE)
        self.api.calls.clear()
        self.invoke()
        observe_index = next(i for i, event in enumerate(self.api.calls)
                             if event[:2] == ('request', '/api/deploy-finalization-status/' + SIGNATURE))
        submit_index = next(i for i, event in enumerate(self.api.calls) if event[0] == 'submit')
        self.assertLess(observe_index, submit_index)
        self.assertEqual(len(self.signs), 1)
        self.assertEqual(canonical(self.api.sent[0]).decode(), first['signed'])
        self.assertEqual(self.intent_row()['plan'], first['plan'])
        self.assertEqual(self.intent_row()['read_name'], first['read_name'])

    def test_lost_submission_observes_finalized_effect_without_resend(self):
        def interrupt(stage):
            if stage == 'after_node_submission': raise RuntimeError('submitted before receipt')
        with self.assertRaisesRegex(RuntimeError, 'submitted before receipt'): self.invoke(hook=interrupt)
        saved = self.intent_row()
        self.assertIsNone(saved['receipt'])
        self.finalized()
        value = self.invoke()
        self.assertEqual(value['effect_finality'], 'finalized')
        self.assertEqual((len(self.signs), len(self.api.sent)), (1, 1))
        self.assertEqual(self.intent_row()['signed'], saved['signed'])
        self.assertEqual(self.intent_row()['plan'], saved['plan'])

    def test_revoked_registration_blocks_saved_intent_and_signed_replay(self):
        def revoke(stage):
            if stage == 'after_signed_intent':
                self.cfg['registration'] = None; self.save()
        self.denied('UNAUTHORIZED', self.invoke, hook=revoke)
        saved = self.intent_row()
        self.assertIsNotNone(saved['signed'])
        self.assertEqual(self.api.sent, [])
        self.denied('UNAUTHORIZED', self.invoke, 'intent')
        self.denied('UNAUTHORIZED', self.invoke)
        self.assertEqual(len(self.signs), 1)

    def test_changed_operation_approval_or_genesis_cannot_replace_saved_intent(self):
        self.invoke()
        saved = self.intent_row()
        original = copy.deepcopy(self.registration)
        for name in ('operation', 'approval', 'genesis'):
            with self.subTest(name=name):
                self.registration = copy.deepcopy(original)
                if name == 'operation': self.registration['binding']['operation'] = 'replacement-operation'
                elif name == 'approval': self.registration['approved']['approval_record'] = 'replacement-approval'
                else: self.registration['binding']['chain']['genesis'] = 'b' * 64
                self.cfg['registration'] = self.registration; self.save()
                self.denied('CONFLICT', self.invoke, 'intent')
                self.assertEqual(self.intent_row(), saved)
        self.assertEqual((len(self.signs), len(self.api.sent)), (1, 1))

    def test_client_rejects_other_artifact_effect_and_malformed_intent(self):
        self.invoke(); self.finalized()
        observed = self.invoke('observe', {'deploy_id': SIGNATURE})
        for name in ('value', 'expr'):
            changed = copy.deepcopy(observed)
            if name == 'value': changed['evidence']['value']['digest'] = '0' * 64
            else: changed['evidence']['effect']['expr'] = m4.expected_expr('wrong-operation', '0' * 64)
            def response(cfg, path, q, deadline=None):
                return dict(profile=chain.PROFILE, request_digest=digest(canonical(q)), value=changed)
            with self.subTest(name=name), patch.object(chain, 'invoke', side_effect=response):
                self.denied('NOT_AVAILABLE', chain.Client(self.client_path).call,
                            'observe', {'deploy_id': SIGNATURE})
        for value in ({}, {'deploy_id': 'invalid', 'read_name': 'c' * 64, 'receipt': None},
                      {'deploy_id': SIGNATURE, 'read_name': 'bad', 'receipt': None}):
            def response(cfg, path, q, deadline=None):
                return dict(profile=chain.PROFILE, request_digest=digest(canonical(q)), value=value)
            with self.subTest(intent=value), patch.object(chain, 'invoke', side_effect=response):
                self.denied('NOT_AVAILABLE', chain.Client(self.client_path).call, 'intent', {})

    def test_client_rejects_changed_placement_and_modified_registration(self):
        client = chain.Client(self.client_path)
        cfg = json.loads(self.client_path.read_text())
        cfg['endpoint']['host'] = 'replacement-service'
        self.client_path.write_bytes(canonical(cfg))
        self.denied('CONFLICT', client.call, 'intent', {})
        cfg['endpoint'] = self.endpoint('fusion-commitment')
        cfg['registration']['approved']['approval_record'] = 'changed-approval'
        self.client_path.write_bytes(canonical(cfg))
        self.denied('CONFLICT', client.call, 'intent', {})

    def test_observation_response_must_match_requested_deploy_identity(self):
        def wrong_deploy(cfg, path, q, deadline=None):
            return dict(profile=chain.PROFILE, request_digest=digest(canonical(q)),
                value=dict(deploy_id='cd' * 70, inclusion_block=None, effect_finality='pending',
                           evidence={'classification': 'explicit-response-fixture'}))
        with patch.object(chain, 'invoke', side_effect=wrong_deploy):
            self.denied('NOT_AVAILABLE', chain.Client(self.client_path).call,
                        'observe', {'deploy_id': SIGNATURE})


if __name__ == '__main__':
    unittest.main()
