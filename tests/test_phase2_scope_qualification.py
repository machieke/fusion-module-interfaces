"""Scope qualification harness tests with explicit Kubernetes/client/TLS fixtures.

The actual embedded Python and qualification control flow execute. Kubernetes,
AtomStorage and OpenSSL are fixtures; no deployed/native/provider pass is claimed.
The only SQLite file is a new synthetic accounting fixture owned by this test.
"""
import base64
import contextlib
import copy
import io
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError, digest
from integration.single_node.preview_scope_qualification import Qualification


REAL_PATH = Path
NOW = 1793620800000
ROLES = ('omega-agent', 'omega-agent-b')


class AtomClientFixture:
    def __init__(self, operator, cfg, deadline):
        self.op, self.cfg = operator, cfg
        operator.client_constructions.append((copy.deepcopy(cfg), deadline))

    def check(self, operation, scope):
        self.op.port_calls.append((self.cfg['principal'], operation, scope))
        if not self.op.storage_up: raise ContractError('NOT_AVAILABLE')
        who = self.cfg['principal']
        if self.cfg['credential'] != self.op.storage_tokens[who] or scope != self.op.scopes[who]:
            raise ContractError('UNAUTHORIZED')

    def create(self, mutation, content_type, data):
        self.check('create', mutation.scope_ref)
        assert mutation.idempotency_key == 'phase2-private-scope-record'
        assert content_type == 'text/plain'
        who = self.cfg['principal']
        if who not in self.op.records:
            self.op.records[who] = dict(scope_ref=mutation.scope_ref, id='fixture-'+who, revision=1, digest=digest(data))
            self.op.payloads[who] = data
        return {'ref': copy.deepcopy(self.op.records[who])}

    def get(self, ref):
        self.check('get', ref['scope_ref'])
        assert ref == self.op.records[self.cfg['principal']]
        return SimpleNamespace(bytes=self.op.payloads[self.cfg['principal']])

    def getMany(self, refs):
        self.check('getMany', refs[0]['scope_ref'])
        return tuple(self.get(ref) for ref in refs)

    def availability(self, ref):
        self.check('availability', ref['scope_ref']); return {'available': True}

    def head(self, scope):
        self.check('head', scope)
        return dict(scope_ref=scope, sequence=1, source='fixture-feed-source')

    def readCommits(self, scope, after, through, limit):
        self.check('readCommits', scope)
        assert after == 0 and limit == 8 and through['scope_ref'] == scope
        refs = [copy.deepcopy(self.op.records[self.cfg['principal']])]
        if self.op.corrupt_feed == 'empty': refs = []
        if self.op.corrupt_feed == 'wrong-ref': refs[0]['id'] = 'fixture-incorrect-ref'
        return dict(complete=self.op.corrupt_feed != 'incomplete', records=[{'ref': ref} for ref in refs])


class OperatorFixture:
    namespace = 'omega-ref-scope-fixture'

    def __init__(self, root):
        self.root = root; self.commands = []; self.sources = []; self.port_calls = []
        self.client_constructions = []; self.records = {}; self.payloads = {}; self.applied = []
        self.storage_up = True; self.corrupt_feed = None; self.delete_wait_failure = False
        self.nonidle = False; self.accounting_change = False; self.session_change = False
        self.inventory_calls = 0; self.model_reads = 0
        self.scopes = {who:'synthetic-fixture-private-'+who.lower() for who in ('A','B')}
        self.storage_tokens = {who:who+'-fixture-secret-token' for who in ('A','B')}
        self.uids = {role:0 for role in (*ROLES,'fusion-storage','fusion-model')}
        self.configs = {}
        self.secret_data = {}
        enc = lambda value:base64.b64encode(value.encode()).decode()
        for role, who in zip(ROLES, ('A','B')):
            cfg = dict(scope=self.scopes[who],principal=who,credential=self.storage_tokens[who],
                endpoint=dict(host='fusion-storage.fixture.svc.cluster.local',port=8443,ca_file='/secrets/ca.crt'))
            self.configs[role] = root/(role+'.json'); self.configs[role].write_text(json.dumps(cfg))
            self.secret_data[role] = dict(metadata={'name':role+'-tls-auth'},data={'atom-'+who+'-token':enc(self.storage_tokens[who])})
        self.secret_data['fusion-storage'] = dict(metadata={'name':'fusion-storage-tls-auth'},
            data={'cog-caller-A-token':enc(self.storage_tokens['A']), 'tls.crt':enc('old-fixture-cert'), 'tls.key':enc('old-fixture-key')})
        self.model_db = root/'model.sqlite'
        with sqlite3.connect(self.model_db) as db:
            db.execute('CREATE TABLE model_calls(id TEXT,reserved INTEGER,captured_ms INTEGER,response TEXT)')
            db.execute('INSERT INTO model_calls VALUES(?,?,?,?)',('captured-fixture',1,100,'fixture captured response'))

    def owned(self): return {'metadata': {'uid': 'fixture-namespace-uid'}}

    def apply(self, value):
        self.applied.append(copy.deepcopy(value))
        role = value['metadata']['name'].removesuffix('-tls-auth')
        self.secret_data[role] = copy.deepcopy(value)

    def execute_embedded(self, role, source):
        self.sources.append(source); code = compile(source,'<actual-embedded-pod-code>','exec')
        def path(value):
            if value == '/run/fusion/private-atoms.json': return self.configs[role]
            if value == '/state/model.sqlite': return self.model_db
            raise AssertionError('unexpected embedded path '+str(value))
        stream = io.StringIO()
        with (patch('pathlib.Path', side_effect=path), patch('fusion.preview_atoms.client',
                side_effect=lambda cfg, deadline:AtomClientFixture(self,cfg,deadline)),
                patch('time.time_ns',return_value=NOW*1000000), contextlib.redirect_stdout(stream)):
            exec(code, {})
        return stream.getvalue()

    def k(self, *args, **kwargs):
        self.commands.append((args, kwargs))
        if args[0] == 'exec' and args[1] == '-i':
            role = args[2].removesuffix('-0')
            if role == 'fusion-model':
                self.model_reads += 1
                if self.accounting_change and self.model_reads == 2:
                    with sqlite3.connect(self.model_db) as db:
                        db.execute('INSERT INTO model_calls VALUES(?,?,?,?)',('unexpected-reservation',1,None,None))
            return self.execute_embedded(role, kwargs['data'])
        if args[0] == 'exec':
            role = args[1].removesuffix('-0'); operation = args[args.index('integration.single_node.preview_operator')+1]
            if operation == 'inventory':
                self.inventory_calls += 1
                return json.dumps({'sessions': {role+'-session':{}}})
            assert operation == 'observe'
            state = 'accepted' if self.nonidle else 'complete'
            after = '--after' in args
            inputs = [{'state':state, 'id':'fixture-second' if after else 'fixture-first'}]
            if self.session_change and self.inventory_calls > 2: inputs.append({'state':'complete','id':'new-input'})
            return json.dumps(dict(inputs=inputs,next_after=None if after else 1))
        if args[:2] == ('get','pod'):
            role = args[2].removesuffix('-0')
            return json.dumps(dict(metadata=dict(uid=role+'-'+str(self.uids[role])),
                status=dict(containerStatuses=[dict(imageID='fixture-image-'+role)]),
                spec=dict(volumes=[dict(persistentVolumeClaim={'claimName':'state-'+role})])))
        if args[:2] == ('get','secret'):
            return json.dumps(self.secret_data[args[2].removesuffix('-tls-auth')])
        if args[0] == 'scale':
            self.storage_up = args[2] == '--replicas=1'; return ''
        if args[0] == 'wait':
            if '--for=delete' in args and self.delete_wait_failure:
                raise RuntimeError('fixture deletion wait failed')
            return ''
        if args[:2] == ('delete','pod'):
            role = args[2].removesuffix('-0'); self.uids[role] += 1
            if role == 'fusion-storage':
                self.storage_tokens['A'] = base64.b64decode(self.secret_data[role]['data']['cog-caller-A-token']).decode()
            if role == 'omega-agent':
                cfg = json.loads(self.configs[role].read_text())
                cfg['credential'] = base64.b64decode(self.secret_data[role]['data']['atom-A-token']).decode()
                self.configs[role].write_text(json.dumps(cfg))
            return ''
        raise AssertionError('unexpected fixture operator command '+repr(args))

    def openssl(self, args, *, cwd, **kwargs):
        assert args[0] == 'openssl' and kwargs == dict(check=True,capture_output=True)
        if args[1] == 'req':
            (cwd/'server.key').write_text('fixture-new-private-key')
            (cwd/'server.csr').write_text('fixture-request')
        else:
            assert args[1] == 'x509'
            (cwd/'server.crt').write_text('fixture-new-certificate')
        return SimpleNamespace(returncode=0)


class ScopeQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-scope-qualifier-fixture-')
        self.addCleanup(self.temp.cleanup); self.root = REAL_PATH(self.temp.name)
        self.op = OperatorFixture(self.root)
        material = self.root/'private-material'; material.mkdir()
        (material/'ca.crt').write_text('fixture-ca'); (material/'ca.key').write_text('fixture-ca-key')
        self.q = Qualification(self.op,self.root/'output',material)

    def full_run(self):
        with patch('integration.single_node.preview_scope_qualification.subprocess.run',side_effect=self.op.openssl):
            self.q.run()

    def test_embedded_all_six_atom_operations_compile_execute_and_bind_original_configuration(self):
        ref = self.q.call('omega-agent','create')['value']['ref']
        self.assertEqual(self.q.call('omega-agent','get',ref=ref)['value']['digest'],ref['digest'])
        self.assertEqual(self.q.call('omega-agent','getMany',ref=ref)['value']['digests'],[ref['digest']])
        self.assertTrue(self.q.call('omega-agent','availability',ref=ref)['value']['available'])
        head = self.q.call('omega-agent','head')['value']
        self.assertEqual(self.q.call('omega-agent','readCommits',through=head)['value']['records'],[{'ref':ref}])
        self.assertTrue(all(deadline == NOW+30000 for _,deadline in self.op.client_constructions))
        self.assertTrue(all(cfg['endpoint']['timeout_seconds'] == 25 for cfg,_ in self.op.client_constructions))
        self.assertNotIn('timeout_seconds',json.loads(self.op.configs['omega-agent'].read_text())['endpoint'])

    def test_embedded_wrong_credentials_and_foreign_scope_remain_typed_failures(self):
        ref = self.q.call('omega-agent-b','create')['value']['ref']
        self.assertEqual(self.q.call('omega-agent','get',scope=ref['scope_ref'],ref=ref),{'error':'UNAUTHORIZED'})
        self.assertEqual(self.q.call('omega-agent','head',wrong=True),{'error':'UNAUTHORIZED'})
        self.assertEqual(set(self.op.records),{'B'})

    def test_embedded_model_snapshot_reads_without_reserving_or_mutating(self):
        before = self.op.model_db.read_bytes(); rows = self.q.models()
        self.assertEqual(rows,[dict(id='captured-fixture',reserved=1,captured_ms=100,
            response_sha256=digest(b'fixture captured response'))])
        self.assertEqual(self.op.model_db.read_bytes(),before)
        self.assertNotIn('fixture captured response',json.dumps(rows))

    def test_idle_observer_drains_all_pages_for_both_agents(self):
        result = self.q.idle()
        self.assertEqual(result,{role:{role+'-session':dict(completed_inputs=2,pending_inputs=0)} for role in ROLES})
        self.assertEqual(sum('--after' in args for args,_ in self.op.commands),2)

    def test_nonidle_session_refuses_before_any_atom_calls_or_disruption(self):
        self.op.nonidle = True
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.full_run()
        self.assertEqual(self.op.port_calls,[]); self.assertEqual(self.op.applied,[])
        self.assertFalse(any(args[0] in ('scale','delete') for args,_ in self.op.commands))

    def test_full_fixture_run_preserves_counters_verifies_revocation_and_never_reports_secrets(self):
        self.full_run(); report = self.q.report
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['model_accounting_before'],report['model_accounting_after'])
        self.assertEqual(report['idle_before'],report['idle_after'])
        cases = {case['name']:case for case in report['cases']}
        self.assertTrue(all(case['passed'] for case in cases.values()))
        self.assertEqual(cases['revoked-old-A-credential']['result'],{'error':'UNAUTHORIZED'})
        self.assertIn('value',cases['new-A-credential']['result'])
        self.assertEqual(len(self.op.records),2)
        self.assertEqual(report['application_occurrences_submitted'],0)
        self.assertTrue(self.op.storage_up)
        text = json.dumps(report)
        for secret in ('fixture-secret-token','fixture-new-private-key','fixture-ca-key'):
            self.assertNotIn(secret,text)
        self.assertNotIn('private-atoms.json',text)

    def test_failed_storage_deletion_wait_restores_replica_before_propagating_failure(self):
        self.op.delete_wait_failure = True
        with self.assertRaisesRegex(RuntimeError,'fixture deletion wait failed'): self.full_run()
        self.assertTrue(self.op.storage_up)
        self.assertIn(('scale','statefulset/fusion-storage','--replicas=1'),[args for args,_ in self.op.commands])
        self.assertEqual(self.op.applied,[])
        self.assertNotEqual(self.q.report.get('status'),'PASS')

    def test_wrong_private_feed_record_is_refused_before_outage_or_rotation(self):
        self.op.corrupt_feed = 'wrong-ref'
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.full_run()
        self.assertEqual(self.op.applied,[])
        self.assertFalse(any(args[0] == 'scale' for args,_ in self.op.commands))

    def test_new_model_reservation_invalidates_full_run(self):
        self.op.accounting_change = True
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.full_run()
        self.assertNotEqual(self.q.report.get('status'),'PASS')
        self.assertNotEqual(self.q.report['model_accounting_before'],self.q.report['model_accounting_after'])

    def test_added_complete_session_input_is_not_mistaken_for_unchanged_idle_state(self):
        self.op.session_change = True
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.full_run()
        self.assertNotEqual(self.q.report.get('status'),'PASS')
        self.assertNotEqual(self.q.report['idle_before'],self.q.report['idle_after'])


if __name__ == '__main__': unittest.main()
