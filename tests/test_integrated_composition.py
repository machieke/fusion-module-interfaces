"""Resident selection on real configuration/SQLite; subprocesses explicitly fake."""
import json,unittest,uuid
from unittest.mock import Mock,patch
from fusion.contracts import ContractError,canonical
from fusion.preview_session_service import SessionPorts
from fusion.resident_workers import Workers,LIMITS,Ports,PROFILE
from fusion.sustained_sessions import PROFILE as SESSIONS
from integration.single_node.preview_host import NativeSupervisor
from integration.single_node.sustained_runtime import materialize
from tests import test_phase3_composition as fixture


class Composition(unittest.TestCase):
    settings=fixture.DynamicConfiguration.settings
    build=fixture.DynamicConfiguration.build
    def setUp(self):
        fixture.DynamicConfiguration.setUp(self)
        self.preview['sustained']['resident_worker']=dict(LIMITS,inputs=5)
        _,self.cfg,self.state,self.run=self.build()
        self.path=self.run/'owner.json';self.ports=SessionPorts(self.path)
        self.sid=self.call('allocate',identity='resident',template='shared')['session']
    def call(self,op,**body):
        if op not in ('allocate','list','capacity'):body['session']=self.sid
        return self.ports.invoke(self.cfg['principals']['operator']['credential'],dict(id='q',profile=SESSIONS,operation=op,body=body))['value']
    def test_frozen_selection_and_unfenced_worker_port_refusal(self):
        app=json.loads(materialize(self.path,self.state,self.run,self.sid).read_bytes())
        self.assertEqual(app['resident_worker']['inputs'],5);self.assertNotIn('native_dispatch_quantum',app)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):
            self.ports.invoke(self.cfg['principals']['worker']['credential'],dict(id='q',profile=SESSIONS,operation='next',body=dict(session=self.sid)))
        p=self.run/'templates/shared/application.json';app=json.loads(p.read_bytes());app['resident_worker']['inputs']=6;p.write_bytes(canonical(app))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):materialize(self.path,self.state,self.run,self.sid)
    def test_supervisor_passes_epoch_and_does_not_launch_while_same_child_is_alive(self):
        self.call('submit',identity='input',text='pin task Synthetic note',assignment=self.cfg['native_sessions']['assignments'][0])
        host=NativeSupervisor(self.path,self.state,self.run);host.wake(self.sid)
        # This process-host unit test does not claim memory readiness or native
        # execution. Remove that unrelated fixture recipe before fake spawn.
        path=self.run/'sessions'/self.sid/'application.json';app=json.loads(path.read_bytes());app.pop('active_memory_configs',None);path.write_bytes(canonical(app))
        child=Mock(pid=77);child.poll.return_value=None
        with patch('integration.single_node.preview_host.subprocess.Popen',return_value=child) as spawn:
            host.tick();self.assertEqual(spawn.call_args.args[0][-2], '--incarnation');epoch=host.incarnation
            host.wake(self.sid);host.tick();self.assertEqual(spawn.call_count,1);self.assertEqual(host.pending,[])
            self.assertEqual(str(uuid.UUID(epoch)),epoch)
            child.poll.return_value=0;host.stopped=True;host.tick()
        self.assertIsNone(host.child)
        owner=host.workers()
        try:self.assertEqual(owner.db.execute('SELECT state FROM native_worker_epochs').fetchone()[0],'stopped')
        finally:owner.close()
    def test_restart_fences_uncertain_input_without_starting_worker(self):
        self.call('submit',identity='input',text='pin task Synthetic note',assignment=self.cfg['native_sessions']['assignments'][0])
        host=NativeSupervisor(self.path,self.state,self.run);owner=host.workers();epoch=str(uuid.uuid4())
        try:
            owner.register(self.cfg['native_sessions']['principal'],self.sid,epoch)
            owner.invoke(self.cfg['native_sessions']['principal'],self.sid,epoch,'ready',{})
            owner.invoke(self.cfg['native_sessions']['principal'],self.sid,epoch,'next',{})
        finally:owner.close()
        with patch('integration.single_node.preview_host.subprocess.Popen',side_effect=AssertionError('uncertain relaunch')):
            host.recover();host.tick()
        self.assertEqual(host.pending,[])
        observed=self.call('observe',content=False);self.assertEqual(observed['inputs'][0]['state'],'dispatched')
    def test_ready_needs_current_worker_authority_not_operator_authority(self):
        host=NativeSupervisor(self.path,self.state,self.run);owner=host.workers();epoch=str(uuid.uuid4())
        try:owner.register(self.cfg['native_sessions']['principal'],self.sid,epoch)
        finally:owner.close()
        request=dict(id='q',profile=PROFILE,operation='ready',session=self.sid,incarnation=epoch,body={})
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):Ports(self.path).invoke(self.cfg['principals']['operator']['credential'],request)
        Ports(self.path).invoke(self.cfg['principals']['worker']['credential'],request)
        self.cfg['principals']['worker']['scopes']={};self.path.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):Ports(self.path).invoke(self.cfg['principals']['worker']['credential'],request)

if __name__=='__main__':unittest.main()
