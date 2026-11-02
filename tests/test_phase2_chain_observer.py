"""Light readback tests: fake node and explicit fixture AtomStorage only.

No node, TLS connection, native application, generative runtime or journal owner
is started. The real observer and existing observe_effect validator execute.
"""
import copy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from examples import preview_chain_observer as observer
from fusion import registry
from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.adapters import f1r3_m4 as m4
from fusion.contracts import ContractError, canonical, digest
from fusion.lookup_contracts import make_head
from fusion.ports import Mutation
from fusion import preview_artifact_contracts as artifact
from fusion import preview_vector_contracts as active, vector_contracts as vector
from fusion.preview_lifecycle import PROFILE as LIFECYCLE
from fusion.registry import descriptor_wire, selection_token
from tests.test_m4_chain import API


class ReadOnlyNodeFixture(API):
    def __init__(self):
        super().__init__()
        self.calls = []

    def request(self, path, body=None):
        if path not in ('/api/status', '/api/blocks/0/0?view=summary',
                '/api/data-at-name-by-block-hash') and not path.startswith(
                    ('/api/deploy-finalization-status/', '/api/deploy/')):
            raise AssertionError('Observer attempted a non-read node operation')
        self.calls.append((path, copy.deepcopy(body)))
        return super().request(path, body)

    def submit_signed(self, signed):
        raise AssertionError('Observer must never submit')


class ChainObserver(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='observer-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.scope = 'synthetic-readback-fixture'
        self.node = ReadOnlyNodeFixture()
        self.feed = FileFeedFixture(self.root / 'fixture-feed.json',
            SimpleNamespace(authorize=lambda *_: 'fixture-authority'))
        self.reads = []
        self.override = {}
        self.atoms = SimpleNamespace(get=self.get)
        catalogue = registry.descriptors
        self.addCleanup(patch.stopall)
        patch.object(registry, 'descriptors', side_effect=lambda: catalogue(atom_provider='fixture-files')).start()
        self.atom_factory = patch.object(observer, 'atoms_client', return_value=self.atoms).start()
        self.node_factory = patch.object(observer, 'F1R3HTTP', return_value=self.node).start()
        self.token = self.root / 'read-token'
        self.token.write_text('fixture-read-only-credential\n')
        self.config = dict(profile=observer.PROFILE, node_endpoint='http://f1r3node.omega-ref-test.svc.cluster.local:40403',
            atoms=dict(composition='synthetic-cognitive-services/1', principal='commit-observer',
                scope=self.scope, credential_file=str(self.token),
                endpoint=dict(host='fusion-storage.omega-ref-test.svc.cluster.local', port=8443,
                    ca_file='/mounted/fixture-ca.crt', path='/reference-cognition'),
                descriptor=descriptor_wire(registry.select(registry.descriptors())['atom.storage'])))
        result = self.store('task-result', 'application/json', b'{"fixture":"result"}')
        payload = self.store('memory', 'text/plain', b'Synthetic prism in violet crate')
        view = dict(generation=str(uuid.uuid4()), head=make_head(str(uuid.uuid4()), self.scope, 2),
            corpus='generated-readback-fixture', embedding=vector.FIXTURE, index=vector.INDEX,
            profile=active.PROFILE, lifecycle=make_head(str(uuid.uuid4()), self.scope, 1, LIFECYCLE),
            active_digest='d' * 64)
        view['logical'] = digest(canonical({k:v for k,v in view.items() if k != 'generation'}))
        self.artifact = dict(profile=artifact.PROFILE, scope=self.scope, task=str(uuid.uuid4()),
            query='synthetic prism', sender='A', reporter='B', result_ref=result['ref'], view=view,
            observations=[dict(payload_ref=payload['ref'], content='Synthetic prism in violet crate')])
        self.trace = self.make_trace(canonical(self.artifact))

    def store(self, name, content_type, data):
        return self.feed.create(Mutation(self.scope, name), content_type, data)

    def get(self, ref):
        self.reads.append(copy.deepcopy(ref))
        return self.override.get(ref['id']) or self.feed.get(ref)

    def make_trace(self, artifact_raw, artifact_type=artifact.PROFILE):
        key = str(uuid.uuid4())
        source = self.store('source/' + key, artifact_type, artifact_raw)
        output = self.store('inspection/' + key, 'application/json', canonical(dict(
            digest=digest(artifact_raw), length=len(artifact_raw), operation='inspect_atom', provider_version='0.1.0')))
        binding = dict(profile=m4.PROFILE, selection=selection_token(m4.DESCRIPTOR), chain=copy.deepcopy(self.node.chain),
            signer='04' + 'f' * 128, limits=copy.deepcopy(observer.LIMITS), operation='synthetic-readback-1',
            protobuf_sha256=observer.PROTOBUF_SHA256, owner_journal='/unmounted/never-open/commitments.sqlite',
            authority=dict(purpose='approved-synthetic-agent-artifact', expires_at_ms=1,
                           artifact_digest=source['ref']['digest']))
        approved = dict(scope_ref=self.scope, result_ref=output['ref'], commitment_digest=output['ref']['digest'],
                        approval_record='synthetic-explicit-readback-approval')
        reg = dict(profile='synthetic-workflow-commitment/1', approved=approved, binding=binding,
                   job_id='actual-inspection-fixture', result=output, artifact=source['ref'], principal='A')
        signature = 'ab' * 70
        term = 'new commitment in { commitment!(("' + m4.NAMESPACE + '", "' + binding['operation'] + '", "' + approved['commitment_digest'] + '")) }'
        plan = dict(term=term, timestamp=1000000, **observer.LIMITS, shardId='fusion-m4', expiration_timestamp=None)
        signed = dict(data=plan, deployer=binding['signer'], sigAlgorithm='secp256k1', signature=signature)
        block = 'b' * 64
        self.node.responses = {
            '/api/deploy-finalization-status/' + signature: dict(state='Finalized', rejection_count=0, latest_block_hash=block),
            '/api/deploy/' + signature: dict(deployId=signature, blockHash=block, blockNumber=1, timestamp=plan['timestamp'],
                cost=603, errored=False, isFinalized=True, finalizationState='Finalized', rejectionCount=0,
                deployer=signed['deployer'], term=term, sigAlgorithm='secp256k1', **observer.LIMITS),
            '/api/data-at-name-by-block-hash': dict(expr=m4.expected_expr(binding['operation'], approved['commitment_digest']),
                block=dict(blockHash=block, blockNumber=1, postStateHash='e' * 64, shardId='fusion-m4', isFinalized=True), cost=0)}
        final = asdict(m4.observe_effect(self.node, signed, 'c' * 64, binding['operation'], approved['commitment_digest'], binding['chain']))
        self.assertEqual(final['effect_finality'], 'finalized')
        self.node.calls.clear()
        return dict(reg=reg, saved_intent=dict(deploy_id=signature, read_name='c' * 64, receipt=None), final_observation=final)

    def denied(self, call, code=None):
        with self.assertRaises(ContractError) as caught: call()
        if code: self.assertEqual(caught.exception.code, code)

    def test_independent_reads_exact_artifact_and_effect_without_owner_or_signer(self):
        # The historical authority has expired; read-only observation never
        # renews it or treats it as permission to sign a new operation.
        with patch('sqlite3.connect', side_effect=AssertionError('No owner journal access')):
            result = observer.observe(self.trace, self.config)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(self.reads, [self.trace['reg']['artifact'], self.trace['reg']['approved']['result_ref']])
        self.assertEqual(len(self.node.calls), 5)
        self.assertEqual(self.node.calls[-1][1], self.trace['final_observation']['evidence']['effect_query'])
        self.assertFalse(result['owner_journals_accessed'])
        self.assertFalse(result['signing_performed'])
        self.assertEqual(result['submissions'], 0)
        output = json.dumps(result)
        self.assertNotIn('fixture-read-only-credential', output)
        self.assertNotIn('Synthetic prism in violet crate', output)
        self.assertEqual(self.trace['reg']['binding']['authority']['expires_at_ms'], 1)

    def test_trace_shape_private_scope_and_malformed_dtos_fail_before_ports(self):
        variants = []
        for key in ('unexpected',):
            item = copy.deepcopy(self.trace); item[key] = 'extra'; variants.append(item)
        item = copy.deepcopy(self.trace); item['reg']['approved']['scope_ref'] = 'private'; variants.append(item)
        item = copy.deepcopy(self.trace); item['saved_intent'] = None; variants.append(item)
        item = copy.deepcopy(self.trace); item['final_observation']['evidence']['inclusion'] = []; variants.append(item)
        for item in variants:
            with self.subTest(item=item): self.denied(lambda: observer.observe(item, self.config))
        self.atom_factory.assert_not_called(); self.node_factory.assert_not_called()

    def test_fixed_term_limits_signer_timestamp_and_profile_binding(self):
        for key, bad in [('term', 'arbitrary term'), ('deployer', '04' + '0' * 128), ('timestamp', True),
                         ('phloLimit', 999), ('sigAlgorithm', 'other'), ('shardId', 'other')]:
            item = copy.deepcopy(self.trace); item['final_observation']['evidence']['inclusion'][key] = bad
            with self.subTest(key=key): self.denied(lambda: observer.observe(item, self.config))
        for key, bad in [('profile', 'old'), ('protobuf_sha256', '0'*64), ('selection', 'wrong')]:
            item = copy.deepcopy(self.trace); item['reg']['binding'][key] = bad
            with self.subTest(key=key): self.denied(lambda: observer.observe(item, self.config))
        self.atom_factory.assert_not_called(); self.node_factory.assert_not_called()

    def test_receipt_read_name_and_final_deploy_are_bound_to_saved_intent(self):
        for change in ('deploy', 'name', 'receipt', 'tuple'):
            item = copy.deepcopy(self.trace)
            if change == 'deploy': item['saved_intent']['deploy_id'] = 'ef' * 70
            elif change == 'name': item['saved_intent']['read_name'] = 'd' * 64
            elif change == 'receipt':
                item['saved_intent']['receipt'] = dict(deploy_id='ef'*70, inclusion_block=None, effect_finality='pending', evidence={})
            else: item['final_observation']['evidence']['effect']['expr'] = m4.expected_expr('different', 'd'*64)
            with self.subTest(change=change): self.denied(lambda: observer.observe(item, self.config))
        self.atom_factory.assert_not_called()

    def test_artifact_closed_shape_canonical_bytes_and_sender_are_checked(self):
        for alteration in ('extra', 'spacing', 'sender', 'type'):
            value = copy.deepcopy(self.artifact)
            if alteration == 'extra': value['unexpected'] = 'extra'
            if alteration == 'sender': value['sender'], value['reporter'] = 'B', 'A'
            raw = json.dumps(value, indent=2).encode() if alteration == 'spacing' else canonical(value)
            trace = self.make_trace(raw, 'text/plain' if alteration == 'type' else artifact.PROFILE)
            with self.subTest(alteration=alteration): self.denied(lambda: observer.observe(trace, self.config))
        self.node_factory.assert_not_called()

    def test_atom_integrity_and_exact_inspection_output_are_required(self):
        ref = self.trace['reg']['approved']['result_ref']; original = self.feed.get(ref)
        self.override[ref['id']] = replace(original, bytes=b'wrong bytes')
        self.denied(lambda: observer.observe(self.trace, self.config), 'NOT_AVAILABLE')
        self.override[ref['id']] = replace(original, content_type='text/plain')
        self.denied(lambda: observer.observe(self.trace, self.config), 'CONFLICT')
        self.node_factory.assert_not_called()

    def test_independent_chain_identity_is_required(self):
        self.node.chain['genesis'] = 'f' * 64
        self.denied(lambda: observer.observe(self.trace, self.config), 'CONFLICT')
        self.assertEqual(len(self.node.calls), 2)

    def test_wrong_node_term_tuple_or_unfinalized_effect_cannot_pass(self):
        original = copy.deepcopy(self.node.responses)
        signature = self.trace['saved_intent']['deploy_id']
        for change in ('term', 'tuple', 'unfinalized'):
            self.node.responses = copy.deepcopy(original)
            if change == 'term': self.node.responses['/api/deploy/' + signature]['term'] = 'another'
            elif change == 'tuple': self.node.responses['/api/data-at-name-by-block-hash']['expr'] = []
            else: self.node.responses['/api/data-at-name-by-block-hash']['block']['isFinalized'] = False
            with self.subTest(change=change):
                result = observer.observe(self.trace, self.config)
                self.assertEqual(result['status'], 'OBSERVATION_NOT_FINAL')
                self.assertEqual(result['observation']['effect_finality'], 'not-observed')

    def test_changed_post_state_of_same_block_is_rejected(self):
        self.node.responses['/api/data-at-name-by-block-hash']['block']['postStateHash'] = 'f' * 64
        self.denied(lambda: observer.observe(self.trace, self.config), 'CONFLICT')

    def test_unavailable_node_is_retained_without_retry(self):
        with patch.object(self.node, 'request', side_effect=ContractError('NOT_AVAILABLE')) as request:
            result = observer.observe(self.trace, self.config)
        self.assertEqual(result['status'], 'OBSERVATION_NOT_FINAL')
        self.assertEqual(result['observation']['evidence']['error']['code'], 'NOT_AVAILABLE')
        self.assertEqual(request.call_count, 1)

    def test_external_credentials_and_isolated_endpoint_only(self):
        configured, endpoint = observer.configuration(self.config, self.scope)
        self.assertEqual(configured['credential'], 'fixture-read-only-credential')
        self.assertNotIn('credential_file', configured)
        env = copy.deepcopy(self.config); env['atoms'].pop('credential_file'); env['atoms']['credential_env'] = 'CHAIN_OBSERVER_TEST_TOKEN'
        with patch.dict(os.environ, {'CHAIN_OBSERVER_TEST_TOKEN': 'other-read-token'}):
            self.assertEqual(observer.configuration(env, self.scope)[0]['credential'], 'other-read-token')
        for selected in ('http://example.com:40403', 'http://127.0.0.1:40403/api/deploy',
                         'http://user:password@127.0.0.1:40403', 'http://127.0.0.1:40401'):
            item = copy.deepcopy(self.config); item['node_endpoint'] = selected
            with self.subTest(endpoint=selected): self.denied(lambda: observer.configuration(item, self.scope), 'UNAUTHORIZED')
        item = copy.deepcopy(self.config); item['atoms']['credential'] = 'inline-secret'
        self.denied(lambda: observer.configuration(item, self.scope), 'UNAUTHORIZED')

    def test_cli_reports_failure_without_exposing_configuration_or_credentials(self):
        trace_path = self.root / 'trace.json'; trace_path.write_bytes(canonical(self.trace))
        config_path = self.root / 'config.json'; config_path.write_bytes(canonical(self.config))
        with patch('sys.argv', ['observer', '--trace', str(trace_path), '--config', str(config_path)]), \
                patch.object(observer, 'observe', side_effect=OSError('fixture-read-only-credential')), \
                patch('builtins.print') as output, self.assertRaises(SystemExit) as exited:
            observer.main()
        self.assertEqual(exited.exception.code, 1)
        report = json.loads(output.call_args.args[0])
        self.assertEqual(report['status'], 'FAILED')
        self.assertNotIn('fixture-read-only-credential', output.call_args.args[0])


if __name__ == '__main__': unittest.main()
