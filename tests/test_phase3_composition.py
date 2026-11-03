"""Real configuration/SQLite, explicitly fake TLS bytes and authored model replies.

No native process, cluster or generative runtime is contacted by these tests.
"""
import copy,json,sqlite3,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,ContractError,digest
from fusion.preview_session_service import SessionPorts
from fusion.sustained_sessions import PROFILE
from integration.single_node.preview_configure import configure
from integration.single_node.sustained_configure import COMPOSITION
from integration.single_node.sustained_runtime import materialize,saved_projections
from tests import test_phase2_cognitive_wiring as wiring_fixture
from tests import test_phase2_fault_configuration as settings_fixture
from tests import test_phase2_model as model_fixture

class DynamicConfiguration(unittest.TestCase):
    def setUp(self):
        wiring_fixture.CognitiveWiringTests.setUp(self)
        self.preview['profile']=COMPOSITION
        self.preview['sustained']=dict(allocation=dict(active=2,retained=8,pending=8,bytes=2097152,lifetime_ms=86400000),feed_capacity=dict(profile='bounded-feed-capacity/1',records=2048,bytes=33554432))
    settings=settings_fixture.PreviewFaultConfigurationTests.settings
    def build(self,role='omega-agent'):
        settings=self.settings(role,enabled=False);settings['service_composition']=COMPOSITION
        return configure(settings)
    def test_application_cognitive_model_configuration_and_materialization(self):
        for role in self.roles:
            if role!='fusion-embedding':self.build(role)
        _,cfg,state,run=self.build()
        path=run/'owner.json';ports=SessionPorts(path);credential=cfg['principals']['operator']['credential']
        q=dict(id='allocate',profile=PROFILE,operation='allocate',body=dict(identity='new-session',template='shared'))
        accepted=ports.invoke(credential,q)['value'];sid=accepted['session']
        app=materialize(path,state,run,sid);value=json.loads(app.read_bytes())
        self.assertEqual(value['session_id'],sid)
        self.assertEqual(value['workdir'],str(state/'sessions'/sid/'native'))
        self.assertEqual(json.loads((app.parent/'session.json').read_bytes())['profile'],PROFILE)
        self.assertEqual(materialize(path,state,run,sid),app)
        self.assertEqual(ports.invoke(credential,q)['value'],accepted)
        self.assertFalse((state/'sessions'/sid/'caller.sqlite').exists())
        original=(state/'sessions'/sid/'allocation-binding.json').read_bytes()
        # Current tokens can rotate; scope/endpoint/template cannot silently change.
        seed=run/'templates'/'shared'/'session.json';v=json.loads(seed.read_bytes());v['credential']='synthetic-rotated-token';seed.write_bytes(canonical(v))
        materialize(path,state,run,sid)
        self.assertEqual((state/'sessions'/sid/'allocation-binding.json').read_bytes(),original)
        v['endpoint']['host']='other.invalid';seed.write_bytes(canonical(v))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):materialize(path,state,run,sid)
    def test_disabled_sustained_worker_accepts_durably_without_native_start(self):
        from integration.single_node.preview_host import NativeSupervisor
        _,cfg,state,run=self.build();path=run/'owner.json'
        supervisor=NativeSupervisor(path,state,run,enabled=False)
        ports=SessionPorts(path,supervisor.wake);credential=cfg['principals']['operator']['credential']
        def call(op,body):return ports.invoke(credential,dict(id='worker-denied',profile=PROFILE,operation=op,body=body))['value']
        sid=call('allocate',dict(identity='paused-install',template='shared'))['session']
        accepted=call('submit',dict(session=sid,identity='queued',text='pin note Synthetic pending note',assignment=cfg['native_sessions']['assignments'][0]))
        with patch('integration.single_node.preview_host.subprocess.Popen',side_effect=AssertionError('disabled native launch')):
            supervisor.recover();supervisor.tick()
        observed=call('observe',dict(session=sid,content=True))
        self.assertEqual(observed['inputs'][0]['state'],'accepted')
        self.assertEqual(observed['inputs'][0]['deadline'],accepted['deadline'])
        self.assertIsNone(supervisor.child)

    def test_one_shot_test_barrier_consumption_does_not_rebind_business_configuration(self):
        _,cfg,state,run=self.build();path=run/'owner.json';ports=SessionPorts(path)
        sid=ports.invoke(cfg['principals']['operator']['credential'],dict(id='a',profile=PROFILE,operation='allocate',body=dict(identity='fault-consumption',template='shared')))['value']['session']
        materialize(path,state,run,sid)
        target=run/'templates'/'shared'/'application.json';before=json.loads(target.read_bytes())
        modified=dict(before,test_failpoints=True,pause_at='after_input_acceptance_commit');target.write_bytes(canonical(modified))
        self.assertEqual(json.loads(materialize(path,state,run,sid).read_bytes())['pause_at'],'after_input_acceptance_commit')
        target.write_bytes(canonical(before));materialize(path,state,run,sid)
        target.write_bytes(canonical(dict(before,invocation_timeout_ms=before['invocation_timeout_ms']+1)))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):materialize(path,state,run,sid)

    def test_saved_projection_observer_never_finishes_missing_task_publication(self):
        _,cfg,state,run=self.build();path=run/'owner.json';ports=SessionPorts(path)
        value=ports.invoke(cfg['principals']['operator']['credential'],dict(id='a',profile=PROFILE,operation='allocate',body=dict(identity='observed',template='shared')))['value'];sid=value['session']
        directory=state/'sessions'/sid;directory.mkdir(parents=True)
        source=dict(session=sid,id='input',occurrence=str(uuid.uuid5(uuid.UUID(sid),'input')))
        with sqlite3.connect(directory/'caller.sqlite') as db:
            db.executescript('''CREATE TABLE preview_native_inputs(turn INTEGER,identity TEXT,source TEXT,acknowledged INTEGER);
                CREATE TABLE app_turns(id INTEGER,projection TEXT);
                CREATE TABLE app_occurrences(id TEXT,turn INTEGER,position INTEGER,done INTEGER);''')
            db.execute('INSERT INTO preview_native_inputs VALUES(1,?,?,0)',('input',canonical(source).decode()))
            db.execute('INSERT INTO app_turns VALUES(1,?)',('Actual committed projection fixture',))
            db.execute('INSERT INTO app_occurrences VALUES("command",1,0,1)')
        self.assertEqual(saved_projections(path,state,sid),[dict(identity='input',result=dict(turn=1,projection='Actual committed projection fixture',occurrences=['command']))])
        source['task_origin']=dict(record=dict(kind='task',id='not-published'))
        with sqlite3.connect(directory/'caller.sqlite') as db:db.execute('UPDATE preview_native_inputs SET source=?',(canonical(source).decode(),))
        self.assertEqual(saved_projections(path,state,sid),[])

class DynamicModelPolicy(unittest.TestCase):
    setUp=model_fixture.PreviewModelTests.setUp
    save=model_fixture.PreviewModelTests.save
    close_owners=model_fixture.PreviewModelTests.close_owners
    disclosure=staticmethod(model_fixture.PreviewModelTests.disclosure)
    owner=model_fixture.PreviewModelTests.owner
    request=model_fixture.PreviewModelTests.request
    invoke=model_fixture.PreviewModelTests.invoke
    error=model_fixture.PreviewModelTests.error
    def test_session_admission_retained_and_bounded_without_exact_id_list(self):
        self.cfg['model_completion']['sessions']=dict(profile='bounded-authenticated-model-sessions/1',principals=['A'],max_sessions=1)
        self.cfg['model_completion']['max_calls']=4;self.save();backend=model_fixture.RecordedProposals();owner=self.owner(backend)
        first=self.invoke(owner);self.assertEqual(first['state'],'captured')
        owner.close();self.owners.remove(owner);owner=self.owner(backend)
        self.assertEqual(self.invoke(owner)['response'],first['response'])
        second=copy.deepcopy(self.accepted);second.update(id=str(uuid.uuid4()),session=str(uuid.uuid4()),source_id=str(uuid.uuid4()))
        self.error('OVERLOADED',self.invoke,owner,accepted=second)
        self.assertEqual(owner.db.execute('SELECT count(*),sum(reserved) FROM model_calls').fetchone()[:],(1,1))
    def test_recorded_dynamic_recipe_is_explicit_and_has_no_tool_executor(self):
        from fusion.preview_recorded_model import service,disclosure
        from fusion import preview_model_contracts as c
        m=self.cfg['model_completion'];m['sessions']=dict(profile='bounded-authenticated-model-sessions/1',principals=['A'],max_sessions=2)
        m['session_proposals']={'A':{'proposal':'input-command'}}
        m['runtime_lock']=dict(profile=c.PROFILE,generative_runtime='FORBIDDEN',session_proposals_sha256=digest(canonical(m['session_proposals'])))
        m['disclosure']=dict(profile='synthetic-session-prompt/1',scope=m['scope'],principals=['A'],max_prompt_bytes=32768,session_authority=m['sessions']['profile'])
        self.save();owner=service(self.path);self.owners.append(owner)
        text="Synthetic context :-:-:-: ['HUMAN-MSG:', 'pin task Synthetic dynamic command']"
        self.accepted.update(native_prompt=text,messages=c.messages(text))
        observed=self.invoke(owner)
        self.assertEqual(observed['response']['native_text'],'pin task Synthetic dynamic command')
        self.assertEqual(owner.db.execute('SELECT sum(reserved) FROM model_calls').fetchone()[0],1)

if __name__=='__main__':unittest.main()
