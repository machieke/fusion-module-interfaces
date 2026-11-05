"""Real owner SQLite clone; native results/provider selections are explicit fixtures."""
import json,sqlite3,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion.contracts import canonical,ContractError
from fusion.guarded_continuation import Workflow,PROFILE
from fusion.sustained_sessions import SustainedSessionStore
from integration.single_node.pilot_workflow_restore import invoke
from integration.single_node.sustained_restore_host import ReadPorts
from tests.test_phase3_sessions import policy
from tests.test_pilot_workflows import steps

class WorkflowRestore(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.state=self.root/'state';self.state.mkdir();self.path=self.state/'session-inbox.sqlite';self.cfg=policy()
        self.scope=self.cfg['templates']['shared']['scope'];self.wid=str(uuid.uuid4())
        store=SustainedSessionStore(self.path,lambda *_:None,self.cfg,clock=lambda:1000)
        try:
            self.sid=store.allocate('A','fixture-native-session','shared')['session']
            obs=SimpleNamespace(scope=self.scope,selections={'fixture':'original-no-live-client'})
            owner=Workflow(store,'A',obs,lambda *_:None,clock=lambda:1000)
            owner.admit(self.wid,self.sid,'knowledge-handoff/1',steps(),9000);owner.advance(self.wid,1)
            pending=store.next_input('A',self.sid)
            store.complete('A',self.sid,pending['id'],dict(turn=1,projection='fixture native captured result',occurrences=['fixture']))
            owner.advance(self.wid,1);checkpoint=owner.checkpoint(self.wid,'review',1,'fixture explicit bounded review')['checkpoints'][-1]
            owner.decide(self.wid,'review','decision','operator',checkpoint['binding_sha256'],'approve')
            owner.advance(self.wid,1);self.original=owner.observe(self.wid)
        finally:store.close()
        (self.state/'restore-fence.json').write_bytes(canonical(dict(mode='READ_ONLY_RECONCILIATION',external_effect_authority=False)))
        self.configuration=dict(principals={'operator':dict(credential='fresh-fixture-only',scopes={self.scope:['sessions.observe','sessions.disclose','sessions.list']})},
            native_sessions=dict(principal='A',database=str(self.path),allocation=self.cfg))
        self.config=self.root/'owner.json';self.config.write_bytes(canonical(self.configuration))
        self.request=dict(profile=PROFILE,id='observation',session=self.sid,workflow=self.wid,operation='observe',body={})
    def call(self,request=None,credential='fresh-fixture-only'):
        return invoke(self.config,self.state,credential,request or self.request)['value']
    def test_exact_saved_captures_checkpoints_deadlines_spent_budget_and_no_writes(self):
        before=self.path.read_bytes()
        with patch('socket.socket',side_effect=AssertionError('network prohibited')),patch('subprocess.run',side_effect=AssertionError('runtime prohibited')), \
             patch('integration.single_node.sustained_runtime.materialize',side_effect=AssertionError('materialization prohibited')):
            value=self.call();self.assertEqual(value,self.call())
        for key in ('steps','checkpoints','deadline_ms','reservations_spent','observations_spent','plan','version','status'):
            self.assertEqual(value[key],self.original[key])
        self.assertEqual(value['reservations_spent'],2);self.assertTrue(value['observation_only']);self.assertTrue(value['restore_fenced'])
        self.assertFalse(value['execution_authorized']);self.assertFalse(value['guard_refresh_performed'])
        self.assertEqual(before,self.path.read_bytes())
        wal=Path(str(self.path)+'-wal');self.assertTrue(not wal.exists() or wal.stat().st_size==0)
    def test_fresh_authority_revocation_and_closed_mutation_surface(self):
        for operation in ('admit','advance','amend','checkpoint','decide','catalogue'):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call(dict(self.request,operation=operation))
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):ReadPorts(self.root,'omega-agent').invoke('/preview/workflows','fresh-fixture-only',dict(self.request,operation=operation))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call(credential='historical-fixture-only')
        self.configuration['principals']['operator']['scopes']={};self.config.write_bytes(canonical(self.configuration))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call()
    def test_scoped_bounded_list_contains_only_retained_owner_rows(self):
        value=self.call(dict(self.request,operation='list',workflow=None))
        self.assertEqual(len(value['workflows']),1);self.assertEqual(value['workflows'][0]['workflow'],self.wid)
        self.assertEqual(value['workflows'][0]['deadline_ms'],9000);self.assertFalse(value['execution_authorized'])
        with self.assertRaisesRegex(ContractError,'NOT_FOUND'):self.call(dict(self.request,workflow=str(uuid.uuid4())))
    def test_malformed_capture_refuses_without_repair(self):
        with sqlite3.connect(self.path) as db:db.execute("UPDATE pilot_workflow_steps SET result_digest=? WHERE node='remember'",('0'*64,))
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.call()
        self.assertEqual(before,self.path.read_bytes())
    def test_malformed_accepted_limits_and_extended_step_deadline_refuse(self):
        with sqlite3.connect(self.path) as db:
            old=db.execute('SELECT accepted FROM pilot_workflows').fetchone()[0];bad=json.loads(old);bad['limits']['steps']=100
            db.execute('UPDATE pilot_workflows SET accepted=?',(canonical(bad).decode(),))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.call()
        with sqlite3.connect(self.path) as db:
            db.execute('UPDATE pilot_workflows SET accepted=?',(old,));db.execute('UPDATE pilot_workflow_steps SET deadline=9001')
        before=self.path.read_bytes()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.call()
        self.assertEqual(before,self.path.read_bytes())
    def test_uncertain_reserved_step_does_not_manufacture_acceptance(self):
        with sqlite3.connect(self.path) as db:
            key=db.execute("SELECT input_id FROM pilot_workflow_steps WHERE node='delegate'").fetchone()[0]
            db.execute('DELETE FROM preview_inputs WHERE id=?',(key,));db.execute("UPDATE pilot_workflow_steps SET receipt=NULL WHERE node='delegate'")
        value=self.call();self.assertEqual(value['status'],'needs-reconciliation')
        self.assertIsNone(value['steps']['delegate']['receipt']);self.assertEqual(value['reservations_spent'],2)
    def test_native_completion_newer_than_workflow_observation_is_not_recaptured(self):
        result=dict(turn=2,projection='fixture committed after workflow snapshot',occurrences=['fixture'])
        with sqlite3.connect(self.path) as db:
            key=db.execute("SELECT input_id FROM pilot_workflow_steps WHERE node='delegate'").fetchone()[0]
            db.execute("UPDATE preview_inputs SET state='complete',result=? WHERE id=?",(canonical(result).decode(),key))
        value=self.call();self.assertEqual(value['status'],'needs-reconciliation')
        self.assertEqual(value['steps']['delegate']['receipt']['state'],'accepted')
        self.assertIsNone(value['steps']['delegate']['result_sha256']);self.assertEqual(value['reservations_spent'],2)

    def test_restore_mode_and_owner_role_must_be_explicit(self):
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):ReadPorts(self.root,'fusion-storage').invoke('/preview/workflows','fresh-fixture-only',self.request)
        (self.state/'restore-fence.json').write_bytes(canonical(dict(mode='WRITABLE',external_effect_authority=True)))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call()


class CloneSelection(unittest.TestCase):
    def case(self):
        from integration.single_node.sustained_restore_qualification import clone_values
        source=dict(preview=dict(profile='omega-single-node-sustained-preview/1',scope='synthetic-clone-test',
            pilot=dict(profile='operator-pilot/1',writer_fence=dict(deployment='omega-ref-pilot-original'),handover={'fixture':True}),
            chain=dict(enabled=True,nodeEnabled=True,registration={'fixture':True})),
            futureLive=dict(enabled=False,activated=False),components={'omega-agent':dict(writerAuthoritySecret='source-authority')})
        restored=dict(status='RESTORED_FENCED',namespace='omega-ref-pilot-clone',automatic_resume=False,
            roles=[dict(role='omega-agent',status='RESTORED_FENCED')])
        fences={'omega-agent':dict(mode='READ_ONLY_RECONCILIATION',external_effect_authority=False,role='omega-agent',
            namespace='omega-ref-pilot-clone',original_scope='synthetic-clone-test')}
        return source,clone_values(source),restored,fences
    def test_fenced_clone_omits_writer_selection_and_keeps_source_exact(self):
        from integration.single_node.sustained_restore_qualification import readonly_pilot_values
        source,selected,restored,fences=self.case();before=canonical(source);selected_before=canonical(selected)
        value=readonly_pilot_values(selected,'omega-ref-pilot-original','omega-ref-pilot-clone',restored,fences)
        self.assertNotIn('writer_fence',value['preview']['pilot']);self.assertNotIn('handover',value['preview']['pilot'])
        self.assertNotIn('writerAuthoritySecret',value['components']['omega-agent'])
        self.assertEqual(before,canonical(source));self.assertEqual(selected_before,canonical(selected))
        self.assertFalse(value['components']['omega-agent']['config']['nativeEnabled'])
        self.assertFalse(value['components']['omega-agent']['config']['workerEnabled'])
    def test_writable_missing_fence_or_mismatched_namespace_refused(self):
        from integration.single_node.sustained_restore_qualification import readonly_pilot_values
        for change in ('mode','authority','missing','namespace','source','native','resume'):
            with self.subTest(change=change):
                source,selected,restored,fences=self.case()
                if change=='mode':fences['omega-agent']['mode']='WRITABLE'
                if change=='authority':fences['omega-agent']['external_effect_authority']=True
                if change=='missing':fences={}
                if change=='namespace':fences['omega-agent']['namespace']='omega-ref-pilot-other'
                if change=='source':selected['preview']['pilot']['writer_fence']['deployment']='omega-ref-pilot-other'
                if change=='native':selected['components']['omega-agent']['config']['nativeEnabled']=True
                if change=='resume':restored['automatic_resume']=True
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                    readonly_pilot_values(selected,'omega-ref-pilot-original','omega-ref-pilot-clone',restored,fences)

if __name__=='__main__':unittest.main()
