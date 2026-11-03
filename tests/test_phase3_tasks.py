"""Actual Messaging/session journals; explicit in-process ports and payload fixtures."""
import json,unittest,uuid
from unittest.mock import patch
from fusion.contracts import canonical,ContractError
from fusion.sustained_sessions import PROFILE,ALLOCATION,SustainedSessionStore
from fusion.preview_session_service import SessionPorts
from tests import test_phase2_tasks as fixture

class AllocatedTaskRouting(unittest.TestCase):
    def setUp(self):
        self.f=fixture.TaskHandoffTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        f=self.f;self.allocations={}
        for who in ('A','B'):
            cfg=json.loads(f.configs[who].read_bytes())
            a=dict(profile=ALLOCATION,owner=str(uuid.uuid4()),active=2,retained=8,pending=8,bytes=2097152,
                templates={'shared':dict(principal=who,scope=fixture.SCOPE,binding=f.binding,lifetime_ms=86400000,runtime_digest='a'*64)})
            self.allocations[who]=a
            cfg['native_sessions'].update(profile=PROFILE,principal=who,scope=fixture.SCOPE,allocation=a)
            cfg['native_sessions'].pop('session_templates')
            cfg['task_ingress'].update(allocation_profile='allocated-native-task-routing/1',template='shared');cfg['task_ingress'].pop('session')
            cfg['principals']['task-router']=dict(credential='task-router-'+who,scopes={fixture.SCOPE:['sessions.binding']})
            f.configs[who].write_bytes(canonical(cfg))
    def owner(self,who):return SustainedSessionStore(self.f.root/('sessions-'+who+'.sqlite'),lambda *_:None,self.allocations[who])
    def setup_routes(self):
        f=self.f
        for who in ('A','B'):
            owner=self.owner(who)
            try:f.sessions[who]=owner.allocate(who,'manual','shared')['session']
            finally:owner.close()
        f.policy.pop('sessions');f.policy['session_authority']=dict(profile='allocated-native-task-routing/1',principals={who:dict(fixture_principal=who,credential='task-router-'+who) for who in ('A','B')});f.save_policy()
        def transport(cfg,route,q,deadline=None):
            f.calls.append(q)
            if route=='/preview/session':return SessionPorts(f.configs[cfg['fixture_principal']]).invoke(cfg['credential'],q)
            return f.ports.invoke(cfg['credential'],q)
        mock=patch('fusion.preview_transport.invoke',side_effect=transport);mock.start();self.addCleanup(mock.stop)
    def test_task_allocates_once_and_freezes_original_deadline(self):
        self.setup_routes();f=self.f;task=f.task();f.send(task)
        self.assertEqual(f.ingress().drain(),'accepted');row=f.row();sid=row['session'];self.assertNotEqual(sid,f.sessions['B'])
        owner=self.owner('B')
        try:
            observed=owner.observe('B',sid,True);self.assertEqual(observed['inputs'][0]['deadline'],task['deadline'])
            self.assertEqual(observed['inputs'][0]['payload']['text'],'query '+task['query'])
            self.assertEqual(owner.capacity('B')['retained'],2)
        finally:owner.close()
        self.assertEqual(f.ingress().drain(),'empty');self.assertEqual(f.row()['session'],sid)
    def test_expired_task_is_terminal_without_allocating_a_session(self):
        self.setup_routes();f=self.f;task=f.task();f.send(task);f.now=task['deadline']
        self.assertEqual(f.ingress().drain(),'refused');self.assertEqual(f.row()['ack'],1)
        owner=self.owner('B')
        try:self.assertEqual(owner.capacity('B')['retained'],1)
        finally:owner.close()
    def test_late_result_is_retained_as_observation_without_native_dispatch(self):
        self.setup_routes();f=self.f;task=f.task();ref,_=f.send(task);result=f.result(task,ref);f.send(result)
        f.now=task['deadline'];self.assertEqual(f.ingress('A').drain(),'observed-late-result')
        row=f.row('A');self.assertEqual(json.loads(row['origin'])['record']['projection'],result['projection']);self.assertEqual(row['ack'],1)
        owner=self.owner('A')
        try:self.assertEqual(owner.observe('A',f.sessions['A'])['inputs'],[])
        finally:owner.close()
        self.assertEqual(f.wakes,[])
    def test_unallocated_sender_and_revoked_binding_are_denied_before_mailbox_acceptance(self):
        self.setup_routes();f=self.f
        with self.assertRaises(ContractError):f.send(f.task(session=str(uuid.uuid4())))
        cfg=json.loads(f.configs['A'].read_bytes());cfg['principals']['task-router']['scopes']={};f.configs['A'].write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):f.send(f.task())
        self.assertEqual(f.mailbox_rows(),[])

if __name__=='__main__':unittest.main()


class CompletedTurnPermit(unittest.TestCase):
    def test_result_reservation_uses_captured_origin_after_processing_slot_advanced(self):
        from types import SimpleNamespace
        from fusion.preview_input import NativeInput
        from fusion.preview_native_tasks import NativeTasks
        import sqlite3,tempfile
        with tempfile.TemporaryDirectory() as directory:
            db=sqlite3.connect(directory+'/caller.sqlite');db.row_factory=sqlite3.Row
            db.execute('CREATE TABLE preview_task_outbox(id TEXT PRIMARY KEY,calls INTEGER NOT NULL)')
            db.execute('INSERT INTO preview_task_outbox VALUES(?,0)',('result/task',));db.commit()
            received=[];source=dict(id='accepted-task',session='original-session',deadline=2000)
            client=SimpleNamespace(binding={'profile':PROFILE},invoke=lambda operation,**body:(received.append((operation,body)) or dict(identity=body['identity'],deadline=2000,authorized=True)))
            native=object.__new__(NativeInput);native.client=client;native.app=SimpleNamespace(session='original-session')
            native.source=lambda:(_ for _ in ()).throw(AssertionError('advanced turn has no accepted input'))
            task=object.__new__(NativeTasks);task.db=db;task.app=SimpleNamespace(preview=SimpleNamespace(input=native),hook=lambda _:None)
            with patch('fusion.preview_native_tasks.time.time_ns',return_value=1000000000):task.reserve('result/task',2000,input_source=source)
            self.assertEqual(received,[('permit',{'identity':'accepted-task'})]);self.assertEqual(db.execute('SELECT calls FROM preview_task_outbox').fetchone()[0],1)
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                task.reserve('result/task',2000,input_source=dict(source,session='other-session'))
            self.assertEqual(db.execute('SELECT calls FROM preview_task_outbox').fetchone()[0],1)
            db.close()
