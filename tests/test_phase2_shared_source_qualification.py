"""Explicit Operator/HTTPS fixtures for the shared-source operator qualifier.

Executes the actual embedded pod code against FileFeedFixture, including real
concurrent threads and filesystem commits. No Kubernetes, DeTTa, native-loop,
HTTPS, or live-model pass is claimed. Temporary reports are not published.
"""
import builtins
import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from examples.preview_shared_source_qualification import Qualification, ROLES, embedded
from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, digest, require
from fusion.ports import Mutation


NOW = 1793620800000
SCOPE = 'synthetic-shared-source-fixture'
IMAGE = 'sha256:' + 'a' * 64


class AccessFixture:
    def __init__(self, principal): self.principal = principal
    def authorize(self, scope, operation):
        require(scope == SCOPE, 'UNAUTHORIZED')
        return self.principal


class OperatorFixture:
    namespace = 'omega-ref-shared-source-fixture'

    def __init__(self, root):
        self.root = root; self.calls = []; self.rpc_calls = []; self.sources = []
        self.create_barrier = threading.Barrier(2)
        self.lock = threading.Lock(); self.create_calls = []; self.active = 0; self.max_active = 0
        self.nonidle = False; self.running = False; self.lost_response = False
        self.corrupt_snapshot = False; self.corrupt_hydration = False; self.change_models = False
        self.cross_scope = False; self.bad_image = False; self.model_reads = 0
        self.source = root / 'feed.json'; self.paths = {}
        self.clients = {role: FileFeedFixture(self.source, AccessFixture(who)) for role, who in zip(ROLES, ('A', 'B'))}
        for index in range(9):
            self.clients[ROLES[0]].create(Mutation(SCOPE, 'fixture-baseline-' + str(index)), 'text/plain', ('opaque-' + str(index)).encode())
        agents = {r: dict(principal=p, private_scope=SCOPE + '-private-' + p.lower()) for r, p in zip(ROLES, ('A', 'B'))}
        for role in ROLES:
            cfg = dict(scope=agents[role]['private_scope'], principal=agents[role]['principal'], credential='fixture-secret-'+role,
                endpoint=dict(host='fusion-storage.fixture.svc.cluster.local', port=8443, path='/reference-cognition', ca_file='/secrets/ca.crt'))
            settings = dict(role=role, preview=dict(enabled=True, scope=SCOPE, model_boundary='RECORDED_FIXTURE', agents=agents))
            config, component = root / (role + '.json'), root / (role + '-component.json')
            config.write_text(json.dumps(cfg)); component.write_text(json.dumps(settings))
            self.paths[role] = {'/run/fusion/private-atoms.json': config, '/config/component.json': component}

    def owned(self): return {'metadata': {'uid': 'fixture-owned-namespace'}}

    def client(self, role, cfg, deadline):
        assert cfg['scope'] == SCOPE
        assert cfg['endpoint']['timeout_seconds'] == 25
        assert cfg['credential'] == 'fixture-secret-' + role
        assert 0 < deadline - NOW <= 30000
        self.rpc_calls.append((role, copy.deepcopy(cfg), deadline))
        provider = self.clients[role]; owner = self
        class Client:
            def create(self, command, content_type, data):
                # The persisted report already owns both identities before
                # either create enters its fixture provider.
                saved = json.loads((owner.root / 'report' / 'report.json').read_text())
                assert len(saved['writes']) == 2
                assert {r['status'] for r in saved['writes']} == {'SUBMISSION_INTENT_OUTCOME_UNKNOWN'}
                with owner.lock:
                    owner.create_calls.append((role, command, content_type, data))
                    owner.active += 1; owner.max_active = max(owner.max_active, owner.active)
                owner.create_barrier.wait(timeout=3)
                result = provider.create(command, content_type, data)
                with owner.lock: owner.active -= 1
                if owner.lost_response and role == ROLES[0]:
                    raise RuntimeError('fixture-secret-do-not-publish after acceptance')
                return result
            def head(self, scope):
                value = provider.head(scope)
                if owner.cross_scope: value['scope_ref'] = SCOPE + '-other'
                return value
            def readCommits(self, scope, after, through, limit):
                value = provider.readCommits(scope, after, through, limit)
                if owner.corrupt_snapshot and len(owner.create_calls) == 2 and through['sequence'] == 9 and value['records']:
                    value['records'][0]['ref']['digest'] = 'f' * 64
                return value
            def getMany(self, refs):
                values = provider.getMany(refs)
                if owner.corrupt_hydration:
                    values = tuple(SimpleNamespace(ref=x.ref, content_type=x.content_type, bytes=b'wrong') for x in values)
                return values
        return Client()

    def execute(self, role, source):
        self.sources.append(source)
        original_import = builtins.__import__; output = []
        def imports(name, *args, **kwargs):
            if name == 'pathlib': return SimpleNamespace(Path=lambda path: self.paths[role][path])
            if name == 'fusion.preview_atoms': return SimpleNamespace(client=lambda cfg, deadline:self.client(role,cfg,deadline))
            if name == 'time': return SimpleNamespace(time_ns=lambda:NOW * 1000000)
            return original_import(name, *args, **kwargs)
        namespace = {'__builtins__': {**vars(builtins), '__import__': imports}, 'print': lambda text:output.append(text)}
        exec(compile(source, '<actual-embedded-shared-source>', 'exec'), namespace)
        return '\n'.join(output)

    def k(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args[:2] == ('get', 'pod'):
            role = args[2].removesuffix('-0')
            return json.dumps(dict(metadata=dict(uid='fixture-'+role), status=dict(containerStatuses=[dict(imageID='containerd://' + (IMAGE if not self.bad_image else 'sha256:'+'b'*64))]),
                spec=dict(volumes=[dict(persistentVolumeClaim={'claimName': 'state-'+role})])))
        assert args[0] == 'exec', args
        if args[1] == '-i':
            role = args[2].removesuffix('-0')
            if role == 'fusion-model':
                self.model_reads += 1
                return json.dumps([dict(id='fixture-capture', reserved=2 if self.change_models and self.model_reads > 1 else 1, captured_ms=1, response_sha256='c'*64)])
            return self.execute(role, kwargs['data'])
        role = args[1].removesuffix('-0')
        operation = args[args.index('integration.single_node.preview_operator')+1]
        if operation == 'inventory':
            return json.dumps(dict(sessions={role+'-session': {}}, worker=dict(status='RUNNING' if self.running else 'NATIVE_STOPPED')))
        assert operation == 'observe'
        return json.dumps(dict(inputs=[dict(state='accepted' if self.nonidle else 'complete')], next_after=None))


class SharedSourceQualificationTests(unittest.TestCase):
    def setUp(self):
        from unittest.mock import patch
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.op = OperatorFixture(self.root)
        self.images = self.root / 'images.json'
        self.images.write_text(json.dumps(dict(source_export_verification='PASS', source_manifest_sha256='d'*64,
            images=[dict(kind=kind, manifest_digest=IMAGE, configuration_digest=IMAGE, repository='fixture/'+kind) for kind in ('base','caller')])) )
        self.clock = patch('examples.preview_shared_source_qualification.time.time_ns', return_value=NOW*1000000)
        self.clock.start(); self.addCleanup(self.clock.stop)
        self.q = Qualification(self.op, self.root / 'report', self.images)

    def test_two_concurrent_one_shot_writes_preserve_retained_snapshot(self):
        self.q.run()
        report = self.q.report
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(self.op.max_active, 2)
        self.assertEqual(len(self.op.create_calls), 2)
        self.assertEqual(report['before']['head']['sequence'], 9)
        self.assertEqual(report['after']['head']['sequence'], 11)
        self.assertEqual(report['before']['snapshot_sha256'], report['after']['retained_snapshot_sha256'])
        self.assertEqual(report['model_accounting_before'], report['model_accounting_after'])
        self.assertEqual(report['idle_before'], report['idle_after'])
        self.assertEqual(report['source_manifest_sha256'], 'd'*64)
        for row in report['writes']:
            self.assertEqual(row['submission_attempts'], 1)
            self.assertEqual(row['deadline_ms'], NOW+30000)
            self.assertTrue(row['occurrence'].startswith('phase2-source-'))
        self.assertNotEqual(report['writes'][0]['occurrence'], report['writes'][1]['occurrence'])
        self.assertTrue(all(deadline==NOW+30000 for _,_,deadline in self.op.rpc_calls))
        self.assertNotIn('fixture-secret', (self.root/'report/report.json').read_text())
        self.assertEqual({r for r,_,_ in self.op.rpc_calls},set(ROLES))
        self.assertEqual(report['application_occurrences_submitted'], 0)
        with self.assertRaises(FileExistsError): Qualification(self.op, self.root/'report', self.images)

    def test_pending_input_refuses_before_any_write(self):
        self.op.nonidle=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(self.op.create_calls,[])

    def test_running_native_worker_refuses_even_if_input_rows_complete(self):
        self.op.running=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(self.op.create_calls,[])

    def test_wrong_source_image_refuses_before_submission(self):
        self.op.bad_image=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(self.op.create_calls,[])

    def test_unknown_committed_response_never_resubmits_and_retains_both_outcomes(self):
        self.op.lost_response=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(len(self.op.create_calls),2)
        self.assertEqual(self.op.clients[ROLES[0]].head(SCOPE)['sequence'],11)
        rows=self.q.report['writes']
        self.assertEqual([row['status'] for row in rows], ['FAILED_OR_UNKNOWN','CAPTURED_ACCEPTANCE'])
        self.assertNotIn('fixture-secret', (self.root/'report/report.json').read_text())
        self.assertEqual(self.q.report['automatic_write_retries'],0)

    def test_changed_prior_snapshot_is_a_failure(self):
        self.op.corrupt_snapshot=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(self.q.report['status'],'FAILED')
        self.assertEqual(len(self.op.create_calls),2)

    def test_wrong_hydrated_payload_is_a_failure(self):
        self.op.corrupt_hydration=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(len(self.op.create_calls),2)

    def test_wrong_scope_head_is_rejected_before_mutation(self):
        self.op.cross_scope=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(self.op.create_calls,[])

    def test_model_accounting_change_fails_without_retry(self):
        self.op.change_models=True
        with self.assertRaises(ContractError): self.q.run()
        self.assertEqual(len(self.op.create_calls),2)
        self.assertEqual(self.q.report['status'],'FAILED')

    def test_embedded_scope_binding_expiry_and_operation_limits(self):
        for operation in ('binding','create','head','readCommits','getMany'):
            compile(embedded(ROLES[0],operation,{},None,NOW+30000),'<embedded>','exec')
        for deadline in (NOW,NOW+30001):
            result=json.loads(self.op.execute(ROLES[0],embedded(ROLES[0],'head',{},SCOPE,deadline)))
            self.assertEqual(result,{'error':'DEADLINE_EXCEEDED'})
        result=json.loads(self.op.execute(ROLES[0],embedded(ROLES[0],'head',{},SCOPE+'-wrong',NOW+30000)))
        self.assertEqual(result,{'error':'CONFLICT'})
        with self.assertRaises(ContractError): embedded(ROLES[0],'delete',{},None,NOW+30000)
        self.assertEqual(self.op.create_calls,[])


if __name__ == '__main__': unittest.main()
