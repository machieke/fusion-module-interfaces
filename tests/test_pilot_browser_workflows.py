"""Real HTTP/scoped policy/session/workflow SQLite; authored native captures.

No native runtime, Kubernetes, E5 or model runs. Native completion and time are
explicit fixtures; checkpoint/decision commits and response validation are real.
"""
import copy,json,time,unittest,uuid
from unittest.mock import patch
from fusion.contracts import canonical,ContractError
from fusion.guarded_continuation import PROFILE,Workflow
from fusion.sustained_sessions import SustainedSessionStore
from integration.single_node import pilot_workflows as ports
from tests import test_pilot_browser as browser_fixture
from tests.test_pilot_workflows import steps


class BrowserWorkflows(unittest.TestCase):
    def setUp(self):
        self.f=browser_fixture.BrowserTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.f.cfg['native_sessions']['workflow_profile']=PROFILE
        self.f.cfg['native_sessions']['assignments'].append('synthetic-task')
        self.f.cfg['principals']['operator']['scopes'][self.f.scope].extend('sessions.workflows-'+op for op in ports.FIELDS)
        self.f.path.write_bytes(canonical(self.f.cfg));self.sid=self.f.allocate('checkpoint-session')
        runtime=self.f.run/'sessions'/self.sid;runtime.mkdir(parents=True)
        # Minimal fixture application selection has no foreign provider clients.
        (runtime/'application.json').write_bytes(canonical(dict(session_id=self.sid,preview={'scope':self.f.scope})))
        self.now=[time.time_ns()//1000000]
        clock=patch.object(ports,'Workflow',side_effect=lambda *a,**kw:Workflow(*a,clock=lambda:self.now[0],**kw))
        clock.start();self.addCleanup(clock.stop)
        self.original=self.f.transport
        def transport(cfg,path,q):
            if path==ports.ROUTE:
                self.f.calls.append((path,copy.deepcopy(q),cfg['credential']))
                return ports.invoke(self.f.path,self.f.state,self.f.run,cfg['credential'],q)
            return self.original(cfg,path,q)
        self.transport=transport;dispatch=patch('integration.single_node.pilot_workbench.invoke',side_effect=transport)
        dispatch.start();self.addCleanup(dispatch.stop)
        self.wid=str(uuid.uuid4());self.f.login('operator')

    def owner(self,operation,body,*,workflow=None):
        return ports.invoke(self.f.path,self.f.state,self.f.run,self.f.cfg['principals']['operator']['credential'],
            dict(profile=PROFILE,id=str(uuid.uuid4()),session=self.sid,workflow=workflow or self.wid,operation=operation,body=body))['value']

    def checkpoint(self):
        plan=steps();plan[-1]['checkpoint']=True
        self.owner('admit',dict(recipe='knowledge-handoff/1',steps=plan,deadline_ms=self.now[0]+60000))
        for _ in range(2):
            self.owner('advance',dict(version=1))
            store=SustainedSessionStore(self.f.cfg['native_sessions']['database'],lambda *_:None,self.f.cfg['native_sessions']['allocation'])
            try:
                value=store.next_input('A',self.sid)
                store.complete('A',self.sid,value['id'],dict(turn=value['sequence'],projection='AUTHORED_NATIVE_CAPTURE_FIXTURE',occurrences=['fixture']))
            finally:store.close()
            self.owner('advance',dict(version=1))
        value=self.owner('checkpoint',dict(identity='review',version=1,reason='Explicit fixture review'))
        self.assertEqual(value['reservations_spent'],2)
        return value,value['checkpoints'][-1]

    def body(self,operation='observe',payload=None):
        return dict(role='omega-agent',session=self.sid,workflow=self.wid,operation=operation,body=payload or {})

    def decide(self,checkpoint,action='approve',identity='stable-decision'):
        return self.body('decide',dict(checkpoint=checkpoint['identity'],identity=identity,binding_sha256=checkpoint['binding_sha256'],action=action))

    def read(self,body):
        status,_,raw=self.f.request('/api/workflows',body);self.assertEqual(status,200,raw);return json.loads(raw)

    def test_lost_decision_reconnect_exact_replay_preserves_captures_deadlines_and_spent(self):
        before,cp=self.checkpoint();body=self.decide(cp)
        def lost(cfg,path,q):
            result=self.transport(cfg,path,q)
            if path==ports.ROUTE and q['operation']=='decide':raise ContractError('NOT_AVAILABLE')
            return result
        with patch('integration.single_node.pilot_workbench.invoke',side_effect=lost):
            self.assertEqual(self.f.request('/api/workflows',body)[0],400)
        observed=self.read(self.body());self.f.request('/api/logout',{});self.f.login('operator')
        replay=self.read(body);self.assertEqual(replay,observed)
        for key in ('steps','deadline_ms','reservations_spent'):self.assertEqual(before[key],replay[key])
        self.assertEqual(replay['status'],'ready');decision=replay['checkpoints'][-1]['decision']
        self.assertEqual(decision['actor'],'browser-operator');self.assertTrue(decision['effective'])
        with self.f.workbench.as_user('operator'):self.assertEqual(decision['identity'],self.f.workbench.identity('workflow-decision','stable-decision'))
        self.assertEqual(self.f.request('/api/workflows',self.decide(cp,identity='new-identity'))[0],400)
        self.assertEqual(self.f.request('/api/workflows',self.decide(cp,action='refuse'))[0],400)
        self.assertEqual(sum(q['operation']=='advance' for path,q,_ in self.f.calls if path==ports.ROUTE),0)

    def test_refusal_and_expired_approval_are_distinct_without_new_inputs(self):
        before,cp=self.checkpoint();refused=self.read(self.decide(cp,'refuse'))
        self.assertEqual(refused['status'],'refused');self.assertTrue(refused['checkpoints'][-1]['decision']['effective'])
        self.assertEqual(refused['steps'],before['steps'])
        # A separate already accepted workflow has its own original deadline.
        self.wid=str(uuid.uuid4());before,cp=self.checkpoint();self.now[0]=before['deadline_ms']
        expired=self.read(self.decide(cp));decision=expired['checkpoints'][-1]['decision']
        self.assertEqual(expired['status'],'expired');self.assertFalse(decision['effective'])
        for key in ('steps','deadline_ms','reservations_spent'):self.assertEqual(expired[key],before[key])
        self.assertEqual(decision['original_deadline_ms'],before['deadline_ms']);self.assertEqual(expired['refunded_reservations'],0)

    def test_role_scope_current_revocation_csrf_and_unselected_operations_refuse(self):
        _,cp=self.checkpoint();body=self.decide(cp)
        self.assertEqual(self.f.request('/api/workflows',body,csrf=False)[0],400)
        for user in ('alice','bob'):
            self.f.login(user);self.assertEqual(self.f.request('/api/workflows',self.body())[0],400)
        self.f.login('operator')
        for operation in ('advance','admit','checkpoint','amend'):
            self.assertEqual(self.f.request('/api/workflows',self.body(operation))[0],400)
        self.assertEqual(self.f.request('/api/workflows',dict(body,session=str(uuid.uuid4())))[0],400)
        altered=copy.deepcopy(body);altered['body']['binding_sha256']='0'*64
        self.assertEqual(self.f.request('/api/workflows',altered)[0],400)
        self.f.cfg['principals']['browser-operator']['scopes'][self.f.scope].remove('sessions.workflows-decide')
        self.f.path.write_bytes(canonical(self.f.cfg))
        self.assertEqual(self.f.request('/api/workflows',body)[0],400)
        self.assertIsNone(self.read(self.body())['checkpoints'][-1]['decision'])

    def test_malformed_owner_binding_and_configuration_grant_boundaries(self):
        _,cp=self.checkpoint()
        for user in ('alice','bob'):
            for methods in self.f.cfg['principals']['browser-'+user]['scopes'].values():
                self.assertFalse(any(x.startswith('sessions.workflows-') for x in methods))
        methods=self.f.cfg['principals']['browser-operator']['scopes'][self.f.scope]
        self.assertEqual({x for x in methods if x.startswith('sessions.workflows-')},{'sessions.workflows-observe','sessions.workflows-decide'})
        def malformed(cfg,path,q):
            result=self.transport(cfg,path,q)
            if path==ports.ROUTE:result['value']['checkpoints'][0]['binding']['scope']='synthetic-foreign'
            return result
        with patch('integration.single_node.pilot_workbench.invoke',side_effect=malformed):
            status,_,raw=self.f.request('/api/workflows',self.body())
            self.assertEqual(status,400);self.assertEqual(json.loads(raw),{'error':'NOT_AVAILABLE'})


if __name__=='__main__':unittest.main()
