"""Real Registry/SQLite/policy and process restart; cluster observations fixtures."""
import io
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fusion.contracts import canonical, digest, ContractError
from fusion.policy import Policy
from fusion.pilot_writer_fence import Handover, PROFILE
from fusion.provider_lifecycle import Registry
from fusion.sustained_sessions import SustainedSessionStore
from integration.single_node.backup_payload import export
from integration.single_node.pilot_upgrade import upgrade, semantic
from tests.test_integrated_registry import selection
from tests.test_phase3_sessions import policy


class CopyUpgrade(unittest.TestCase):
    def test_noncanonical_wire_fixture_is_retained_instead_of_reencoded(self):
        from integration.single_node.pilot_upgrade import transform
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'disposable-copy.sqlite';cfg=policy()
            store=SustainedSessionStore(path,lambda *_:None,cfg,clock=lambda:1000)
            reg=Registry(store,selection(cfg['templates']['shared']['scope']),lambda *_:None);reg.act('add','add','storage')
            # Explicit old-format byte fixture: identical JSON meaning with
            # noncanonical whitespace, never a native/runtime evidence claim.
            original=json.loads(store.db.execute('SELECT result FROM integrated_provider_actions').fetchone()[0])
            wire=json.dumps(original,indent=2)
            with store.db:store.db.execute('UPDATE integrated_provider_actions SET result=?',(wire,))
            store.close();result=transform(path);self.assertEqual(result['raw_wire_bytes'],len(wire.encode()))
            with sqlite3.connect(path) as db:
                actual=db.execute("SELECT wire,sha256,encoding FROM pilot_registry_upgrade_originals WHERE table_name='integrated_provider_actions' AND column_name='result'").fetchone()
                self.assertEqual(actual,(wire,digest(wire.encode()),'exact-raw-json/1'));self.assertEqual(semantic(db)['integrated_provider_actions'][0]['result'],original)

    def test_empty_and_private_archived_uncertain_exports_keep_nonregistry_state_exact(self):
        for scenario in ('empty','private-archived-uncertain'):
            with self.subTest(scenario=scenario),tempfile.TemporaryDirectory() as td:
                root=Path(td);owner=root/'owner';owner.mkdir()
                (owner/'owner-seal.json').write_bytes(canonical(dict(role='omega-agent',scope='synthetic-upgrade',composition='omega-single-node-sustained-preview/1',provider_registry='trusted-provider-lifecycle/1')))
                cfg=policy();cfg['bytes']=4*1024*1024;now=[1000]
                if scenario!='empty':
                    cfg['templates']['private']=cfg['templates'].pop('shared');cfg['templates']['private']['scope']='synthetic-upgrade-private-A'
                store=SustainedSessionStore(owner/'session-inbox.sqlite',lambda *_:None,cfg,clock=lambda:now[0])
                template=next(iter(cfg['templates']));selected=selection(cfg['templates'][template]['scope']);selected['templates']={template:['storage']}
                reg=Registry(store,selected,lambda *_:None)
                if scenario!='empty':
                    reg.act('add','add','storage');reg.probe('probe','storage',lambda _:True);reg.act('enable','enable','storage')
                    sid=store.allocate('A','archived-private',template,admission=reg.admit)['session']
                    store.submit('A',sid,'private-input','pin private fixture','task');store.next_input('A',sid)
                    store.complete('A',sid,'private-input',dict(turn=1,projection='EXPLICIT_RECORDED_RESULT_FIXTURE',occurrences=['private-occurrence']))
                    store.control('A',sid,'close','close');store.control('A',sid,'archive','archive')
                    unknown=store.allocate('A','uncertain-private',template,admission=reg.admit)['session']
                    accepted=store.submit('A',unknown,'uncertain','write-file x synthetic','task');store.next_input('A',unknown)
                    now[0]=accepted['deadline'];store.reconcile('A',unknown)
                    self.assertEqual(store.observe('A',unknown)['inputs'][0]['state'],'needs-reconciliation')
                tables=[r[0] for r in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'integrated_provider%'")]
                before={t:store.db.execute('SELECT * FROM '+t).fetchall() for t in tables}
                before={t:[tuple(row) for row in rows] for t,rows in before.items()};store.close()
                stream=io.BytesIO()
                with patch('sys.stdout',SimpleNamespace(buffer=stream)):export(owner,'omega-agent')
                source=root/'source.tar.gz';source.write_bytes(stream.getvalue());raw=source.read_bytes()
                result=upgrade(source,digest(raw),root/'copy');self.assertEqual(result['status'],'VERIFIED_FENCED_COPY')
                with sqlite3.connect(root/'copy/session-inbox.sqlite') as db:
                    self.assertEqual({t:db.execute('SELECT * FROM '+t).fetchall() for t in tables},before)
                self.assertEqual(source.read_bytes(),raw)

    def test_actual_old_registry_capacity_boundary_is_not_silently_expanded_during_copy(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);owner=root/'owner';owner.mkdir()
            (owner/'owner-seal.json').write_bytes(canonical(dict(role='omega-agent',scope='synthetic-upgrade',composition='omega-single-node-sustained-preview/1',provider_registry='trusted-provider-lifecycle/1')))
            cfg=policy();cfg['bytes']=8*1024*1024
            store=SustainedSessionStore(owner/'session-inbox.sqlite',lambda *_:None,cfg,clock=lambda:1000)
            reg=Registry(store,selection(cfg['templates']['shared']['scope']),lambda *_:None);reg.act('add','add','storage')
            count=0
            for index in range(256):
                try:reg.probe('boundary-'+str(index),'storage',lambda _:False)
                except ContractError as error:
                    self.assertEqual(error.code,'OVERLOADED');break
                count+=1
            self.assertGreater(count,1);self.assertLess(count,256);before=semantic(store.db);store.close()
            stream=io.BytesIO()
            with patch('sys.stdout',SimpleNamespace(buffer=stream)):export(owner,'omega-agent')
            source=root/'boundary.tar.gz';source.write_bytes(stream.getvalue());raw=source.read_bytes()
            # /2's finite active representation has its own bound. An old full
            # store may require explicit later sealing support; copy must fail
            # closed rather than auto-discard old receipts or enlarge limits.
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):upgrade(source,digest(raw),root/'copy')
            self.assertFalse((root/'copy/format-upgrade.json').exists())
            self.assertEqual(source.read_bytes(),raw);self.assertTrue((root/'copy/restore-fence.json').exists())

    def test_actual_registry_copy_preserves_selection_wire_unknown_and_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); owner = root/'owner'; owner.mkdir()
            seal = dict(role='omega-agent',scope='synthetic-upgrade',composition='omega-single-node-sustained-preview/1',provider_registry='trusted-provider-lifecycle/1')
            (owner/'owner-seal.json').write_bytes(canonical(seal)); cfg = policy()
            store = SustainedSessionStore(owner/'session-inbox.sqlite', lambda *_:None, cfg, clock=lambda:1000)
            reg = Registry(store, selection(cfg['templates']['shared']['scope']), lambda *_:None)
            reg.act('add','add','storage'); reg.probe('probe','storage',lambda _:True); reg.act('enable','enable','storage')
            session = store.allocate('A','kept','shared',admission=reg.admit)
            reg.probe('unknown','storage',lambda _:False)
            before = semantic(store.db); store.close()
            output = io.BytesIO()
            with patch('sys.stdout',SimpleNamespace(buffer=output)): export(owner,'omega-agent')
            source = root/'original.tar.gz'; source.write_bytes(output.getvalue()); raw = source.read_bytes(); expected = digest(raw)
            dry = upgrade(source,expected,dry_run=True); self.assertEqual(dry['status'],'DRY_RUN')
            dest = root/'copy'; result = upgrade(source,expected,dest)
            self.assertEqual(result['status'],'VERIFIED_FENCED_COPY'); self.assertEqual(source.read_bytes(),raw)
            with sqlite3.connect(dest/'session-inbox.sqlite') as db:
                self.assertEqual(semantic(db),before)
                originals = db.execute('SELECT table_name,key_value,column_name,wire,sha256,encoding FROM pilot_registry_upgrade_originals').fetchall()
                self.assertTrue(originals)
                for table,key,column,wire,h,encoding in originals:
                    self.assertIsNone(wire);self.assertEqual(encoding,'canonical-json/1')
                    field='session' if table=='integrated_provider_bindings' else 'id'
                    selected=next(row for row in before[table] if row[field]==key)
                    self.assertEqual(digest(canonical(selected[column])),h)
                self.assertEqual(result['result']['raw_wire_bytes'],0)
                self.assertEqual(result['result']['canonical_reconstructed_columns'],len(originals))
            self.assertTrue((dest/'restore-fence.json').exists()); self.assertFalse(result['writable_activation'])
            with self.assertRaisesRegex(ContractError,'CONFLICT'): upgrade(source,'0'*64,root/'bad')
            self.assertFalse((root/'bad').exists())

    def test_unknown_profile_and_existing_destination_refuse(self):
        # Arbitrary inputs cannot be interpreted as a supported Registry export.
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'source'; p.write_bytes(b'not-an-owner-export')
            with self.assertRaises(Exception):upgrade(p,digest(p.read_bytes()),Path(td)/'copy')
            self.assertFalse((Path(td)/'copy').exists())


class WriterFence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.root = Path(self.tmp.name)
        self.authority = self.root/'policy-authority.json'; self.allowed = True; self.stale_refused = True
        self.h = Handover(self.authority,self.authorize,self.observe,imported_roots=[self.root/'imported'])
        self.h.initialize('original','writer-1',['writer.start','writer.request'])
        self.config = self.root/'policy.json'
        self.config.write_bytes(canonical(dict(principals={'A':dict(credential='synthetic',scopes={'synthetic-scope':['memory.read','memory.write']})},
            writer_fence=dict(profile=PROFILE,authority_file=str(self.authority),deployment='original',incarnation='writer-1',generation=1))))
    def authorize(self,_):
        if not self.allowed:raise ContractError('UNAUTHORIZED')
    def observe(self,stage,deployment):
        if stage=='initial':return dict(task_owned=True,fresh_synthetic=True,writers=1)
        if stage=='drained-current-checkpoint':return dict(task_owned=True,fresh_synthetic=True,admission_closed=True,writers=0,
            unresolved_effects_fenced=True,accounting_verified=True,checkpoint_sha256='a'*64,closure_sha256='b'*64)
        if stage=='retired-original':return dict(writers=0,network_fenced=True,service_credentials_revoked=True,
            stale_restart_refused=self.stale_refused,authority_outside_imported_state=True)
        return dict(task_owned=True,fresh_synthetic=True,writers=0,checkpoint_sha256='a'*64,closure_sha256='b'*64,
            accounting_verified=True,historical_effects_observation_only=True,execution_authority_imported=False)
    def test_cutover_stale_policy_real_process_restart_and_rollback_refuse(self):
        p = Policy(self.config); p.check('A','synthetic-scope','memory.write')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.check('A','synthetic-scope','not-granted')
        planned=self.h.plan('handover','replacement','writer-2','a'*64,'b'*64)
        self.assertEqual(self.h.plan('handover','replacement','writer-2','a'*64,'b'*64),planned)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.check('A','synthetic-scope','memory.read')
        self.h.retire('handover'); active=self.h.activate('handover'); self.assertEqual(active['generation'],2)
        process=subprocess.run([sys.executable,'-c',"from fusion.policy import Policy;import sys;Policy(sys.argv[1]).check('A','synthetic-scope','memory.write')",str(self.config)],capture_output=True)
        self.assertNotEqual(process.returncode,0);self.assertIn(b'UNAUTHORIZED',process.stderr)
        changed=json.loads(self.config.read_bytes());changed['writer_fence'].update(deployment='replacement',incarnation='writer-2',generation=2)
        self.config.write_bytes(canonical(changed));p.check('A','synthetic-scope','memory.write')
        self.assertEqual(self.h.activate('handover'),active)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_OPERATION'):self.h.rollback()
        self.assertEqual(self.h.read()['generation'],2)
    def test_stale_checkpoint_revocation_missing_guard_and_weak_retirement_refuse(self):
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.h.plan('bad','replacement','writer-2','c'*64,'b'*64)
        self.allowed=False
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.h.plan('denied','replacement','writer-2','a'*64,'b'*64)
        self.allowed=True;self.h.plan('handover','replacement','writer-2','a'*64,'b'*64);self.stale_refused=False
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.h.retire('handover')
        self.assertEqual(self.h.read()['state'],'drained')
        self.authority.unlink()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):Policy(self.config).check('A','synthetic-scope','memory.read')
    def test_authority_cannot_live_inside_imported_state(self):
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
            Handover(self.root/'imported'/'authority',self.authorize,self.observe,imported_roots=[self.root/'imported'])


if __name__=='__main__':unittest.main()
