"""Qualification-runner guard tests with explicit authored transport fixtures."""
import copy,unittest
from examples.pilot_browser_qualification import qualify,BrowserClient
from integration.single_node.pilot_browser_provision import provision


class Fixture:
    user='alice'
    def __init__(self,live=False):self.live=live;self.calls=[]
    def login(self):pass
    def request(self,path,body=None):
        self.calls.append((path,body))
        if path=='/api/state':return {'additional_live_generations':0,'namespace':'omega-ref-fixture','agents':{'omega-agent':{
            'model_boundary':['LIVE_APPROVAL_REQUIRED' if self.live else 'RECORDED_FIXTURE'],'assignments':['test']}}}
        if path=='/api/action' and body['operation']=='allocate':return {'session':'fixture-session'}
        if path.startswith('/api/capabilities?'):return dict(model_boundary='RECORDED_FIXTURE',advisory=True,acceptance_created=False,catalogue='fixture-catalogue')
        if path=='/api/preflight':return {'preflight':{'admissible':True}}
        raise RuntimeError('LOST_RESPONSE_FIXTURE')


class Qualification(unittest.TestCase):
    plan=dict(identity='fixture',role='omega-agent',template='shared',commands=[[['pin','note','synthetic']]],denied_sessions=[])
    def test_live_selection_denied_before_allocation(self):
        client=Fixture(True)
        with self.assertRaises(ValueError):qualify(client,self.plan)
        self.assertFalse(any(path=='/api/action' for path,_ in client.calls))
    def test_unknown_submission_response_keeps_identity_evidence_without_retry(self):
        client=Fixture();events=[]
        with self.assertRaisesRegex(RuntimeError,'LOST_RESPONSE_FIXTURE'):qualify(client,self.plan,lambda v:events.append(copy.deepcopy(v)))
        self.assertEqual(events[-1]['attempts'],[dict(caller_identity='fixture-input-0',state='SUBMISSION_OUTCOME_NOT_YET_OBSERVED')])
        self.assertEqual(sum(path=='/api/action' and body['operation']=='submit' for path,body in client.calls),1)
    def test_provision_is_explicit_scoped_distinct_and_private(self):
        users={'alice':dict(role='developer',scopes=['synthetic-shared'],credential_key='browser-alice-token'),
            'operator':dict(role='operator',scopes=['synthetic-shared'],credential_key='browser-operator-token')}
        agents={r:dict(principal=p,scopes=['synthetic-shared']) for r,p in [('omega-agent','A'),('omega-agent-b','B')]}
        value=provision('omega-ref-browser-fixture',users,agents,cleanup=True)
        self.assertEqual(set(value['required_secret_keys']),{'omega-agent','omega-agent-b','fusion-search'})
        self.assertNotEqual(value['owner_credentials']['omega-agent']['browser-alice-token'],value['owner_credentials']['omega-agent-b']['browser-alice-token'])
        self.assertNotIn(value['bootstrap']['alice'],str(value['gateway_configuration']))
        self.assertNotIn('search_maintenance',value['gateway_configuration']['users']['alice']['targets']['omega-agent'])
        self.assertIn('search_maintenance',value['gateway_configuration']['users']['operator']['targets']['omega-agent'])
    def test_client_refuses_public_endpoint_before_any_request(self):
        with self.assertRaises(ValueError):BrowserClient('https://public.example.invalid','alice','not-contacted')


class StoryGuards(unittest.TestCase):
    """Authored transport only: verify the public driver cannot retry effects."""
    def plan(self):
        return dict(profile='bounded-native-browser-story/1',namespace='omega-ref-pilot-fixture',identity='fixture-story',corpus={user:dict(
            remember='Authored fixture token '+user+' is at placeholder-target',query='authored fixture '+user,
            expected='placeholder-target',disclosure='synthetic-shareable' if user=='shared' else 'synthetic-private') for user in ('alice','bob','shared')})

    def test_plan_rejects_answer_in_query_wrong_disclosure_and_extra_execution_fields(self):
        from examples.pilot_browser_story import validate_plan
        for mutate in (lambda p:p['corpus']['alice'].update(query='placeholder-target'),
                       lambda p:p['corpus']['bob'].update(disclosure='synthetic-shareable'),
                       lambda p:p.update(endpoint='https://not-selected.invalid')):
            plan=self.plan();mutate(plan)
            with self.assertRaises(ValueError):validate_plan(plan)
        self.assertEqual(validate_plan(self.plan()),self.plan())

    def execute(self,failure):
        import json,os,sys,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from examples import pilot_browser_story as story
        calls=[];namespace=self.plan()['namespace']
        class AuthoredClient:
            def __init__(self,base,user,bootstrap):self.user=user
            def login(self):pass
            def request(self,path,body=None):
                calls.append((path,copy.deepcopy(body)))
                if path=='/api/state':return dict(namespace=namespace,additional_live_generations=0,agents={role:dict(model_boundary=['LIVE_APPROVAL_REQUIRED' if failure=='live' else 'RECORDED_FIXTURE']) for role in ('omega-agent','omega-agent-b')})
                if path=='/api/action' and body['operation']=='allocate':
                    if failure=='allocation':raise RuntimeError('LOST_ALLOCATION_RESPONSE_FIXTURE')
                    return dict(session='authored-session-'+self.user)
                if path.startswith('/api/capabilities?'):return dict(model_boundary='RECORDED_FIXTURE',catalogue='fixture-only')
                if path=='/api/preflight':return dict(preflight=dict(admissible=True))
                if path=='/api/action' and body['operation']=='submit':raise RuntimeError('LOST_SUBMISSION_RESPONSE_FIXTURE')
                raise AssertionError(path)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'plan.json').write_text(json.dumps(self.plan()))
            for user in ('alice','bob'):(root/(user+'.bootstrap')).write_text('fixture-bootstrap-only')
            args=['story','--root',str(root),'--plan',str(root/'plan.json'),'--phase','private','--output',str(root/'report.json')]
            with patch.object(story,'BrowserClient',AuthoredClient),patch.object(sys,'argv',args),patch.object(sys,'path',[]),patch.dict(os.environ,{},clear=True):
                with self.assertRaises((RuntimeError,ValueError)):story.main()
            report=json.loads((root/'report.json').read_bytes());self.assertEqual(report['status'],'FAILED_RETAINED')
            self.assertEqual((root/'report.json').stat().st_mode&0o777,0o600)
            return calls,report

    def test_live_selection_refuses_before_any_allocation_or_submission(self):
        calls,report=self.execute('live')
        self.assertFalse(any(path=='/api/action' for path,_ in calls));self.assertEqual(report['inputs'],[])

    def test_lost_allocation_preserves_one_named_attempt_without_reissue(self):
        calls,report=self.execute('allocation')
        attempts=report['allocation_attempts'];self.assertEqual(len(attempts),1)
        self.assertEqual(attempts[0]['intent']['identity'],'fixture-story-private-alice-allocation')
        self.assertEqual(attempts[0]['state'],'BEFORE_SUBMISSION')
        self.assertEqual(sum(path=='/api/action' for path,_ in calls),1)

    def test_lost_submission_preserves_identity_and_does_not_retry_or_allocate_replacement(self):
        calls,report=self.execute('submission')
        self.assertEqual(len(report['inputs']),1);self.assertEqual(report['inputs'][0]['identity'],'fixture-story-private-alice-0')
        self.assertEqual(report['inputs'][0]['state'],'BEFORE_SUBMISSION')
        self.assertEqual(sum(path=='/api/action' and body['operation']=='submit' for path,body in calls),1)
        self.assertEqual(len(report['allocation_attempts']),2)

    def test_observation_retries_only_transient_reads_with_original_deadline(self):
        import time
        from unittest.mock import Mock,patch
        from examples.pilot_browser_story import observe_accepted
        deadline=time.time_ns()//1000000+30000;row=dict(id='accepted',deadline=deadline,state='complete',result={'fixture':'captured'})
        client=Mock();client.observe.side_effect=[RuntimeError('OVERLOADED'),RuntimeError('NOT_AVAILABLE'),{'inputs':[row]}];entry={}
        with patch('examples.pilot_browser_story.time.sleep'):
            self.assertEqual(observe_accepted(client,dict(role='owner',session='session'),row,entry,lambda:None),row)
        self.assertEqual(client.observe.call_count,3);client.request.assert_not_called()
        self.assertEqual([x.get('code') for x in entry['observation_windows'][0]['attempts']],['OVERLOADED','NOT_AVAILABLE',None])
        self.assertEqual(entry['observation_windows'][0]['original_deadline_ms'],deadline)

    def test_expired_capture_is_read_once_without_regeneration(self):
        from unittest.mock import Mock
        from examples.pilot_browser_story import observe_accepted
        row=dict(id='accepted',deadline=1,state='complete',result={'fixture':'durable'})
        client=Mock();client.observe.return_value={'inputs':[row]};entry={'observed':copy.deepcopy(row)}
        self.assertEqual(observe_accepted(client,dict(role='owner',session='session'),row,entry,lambda:None),row)
        self.assertEqual(client.observe.call_count,1);client.request.assert_not_called();self.assertEqual(entry['observation_windows'][0]['maximum_reads'],1)

    def test_current_revocation_and_changed_deadline_fail_without_read_retry(self):
        from unittest.mock import Mock
        from examples.pilot_browser_story import observe_accepted
        client=Mock();client.observe.side_effect=RuntimeError('UNAUTHORIZED')
        with self.assertRaisesRegex(RuntimeError,'UNAUTHORIZED'):observe_accepted(client,dict(role='owner',session='session'),dict(id='accepted',deadline=1),{},lambda:None)
        self.assertEqual(client.observe.call_count,1);client.request.assert_not_called()
        client=Mock();client.observe.return_value={'inputs':[dict(id='accepted',deadline=2,state='complete')]}
        with self.assertRaisesRegex(ValueError,'DEADLINE_CHANGED'):observe_accepted(client,dict(role='owner',session='session'),dict(id='accepted',deadline=1),{},lambda:None)
        self.assertEqual(client.observe.call_count,1)

    def test_expired_unavailable_observation_stops_without_effect_retry(self):
        from unittest.mock import Mock
        from examples.pilot_browser_story import observe_accepted
        client=Mock();client.observe.side_effect=RuntimeError('OVERLOADED');entry={}
        with self.assertRaisesRegex(ValueError,'OBSERVATION_EXPIRED'):observe_accepted(client,dict(role='owner',session='session'),dict(id='accepted',deadline=1),entry,lambda:None)
        self.assertEqual(client.observe.call_count,1);client.request.assert_not_called();self.assertEqual(entry['observation_windows'][0]['attempts'][0]['code'],'OVERLOADED')

    def test_refusal_evidence_keeps_transport_failure_distinct_from_disclosure(self):
        from unittest.mock import Mock
        from examples.pilot_browser_story import refusal_observation
        for code in ['OVERLOADED','NOT_AVAILABLE','INVALID_ARGUMENT']:
            client=Mock();client.request.side_effect=RuntimeError(code);records=[]
            with self.assertRaisesRegex(RuntimeError,code):refusal_observation(client,'/api/current?fixture',None,records.append)
            self.assertEqual(records,[dict(path='/api/current?fixture',state='REFUSED',code=code)]);self.assertEqual(client.request.call_count,1)
        client=Mock();client.request.side_effect=RuntimeError('UNAUTHORIZED');records=[]
        self.assertTrue(refusal_observation(client,'/api/current?fixture',None,records.append));self.assertEqual(records[0]['code'],'UNAUTHORIZED')
        client=Mock();client.request.return_value={'authored_fixture_body':'unexpected'};records=[]
        self.assertFalse(refusal_observation(client,'/api/current?fixture',None,records.append));self.assertEqual(records[0]['state'],'RETURNED_BODY');self.assertEqual(records[0]['body'],client.request.return_value)

    def test_resume_observes_acknowledged_capture_without_reallocating_or_resubmitting(self):
        import json,os,sys,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from examples import pilot_browser_story as story
        plan=self.plan();calls=[];selection=dict(role='omega-agent',session='retained-session');identity='fixture-story-shared-shared-0'
        receipt=dict(id='accepted-first',deadline=1);row=dict(receipt,state='complete',result={'projection':json.dumps({'memory':{'handle':'returned-native-handle'}})})
        intent=dict(role='omega-agent',session='',operation='allocate',identity='fixture-story-shared-shared-allocation',template='shared');allocation={'session':selection['session']}
        previous=dict(profile='pilot-browser-deployed-native-story/1',status='FAILED_RETAINED',phase='shared',namespace=plan['namespace'],plan_sha256=story.fingerprint(plan),additional_live_generations=0,model='RECORDED_FIXTURE',source_sha256='a'*64,checks=[],failure={'code':'OVERLOADED'},
            client_environment=dict(kubeconfig_present=False,repository_on_import_path=False),sessions={'shared':dict(selection,allocation=allocation)},allocation_attempts=[dict(intent=intent,state='ACCEPTANCE_OBSERVED',receipt=allocation)],
            inputs=[dict(identity=identity,selected=selection,command=['remember',plan['corpus']['shared']['remember']],state='ACCEPTED',receipt=receipt)])
        class Client:
            def __init__(self,base,user,token):self.user=user
            def login(self):pass
            def observe(self,role,session):calls.append(('observe',dict(role=role,session=session)));return {'inputs':[row]}
            def request(self,path,body=None):
                calls.append((path,copy.deepcopy(body)))
                if path=='/api/state':return dict(namespace=plan['namespace'],additional_live_generations=0,agents={'omega-agent':dict(model_boundary=['RECORDED_FIXTURE'])})
                if path.startswith('/api/capabilities?'):return dict(model_boundary='RECORDED_FIXTURE',catalogue='fixture')
                if path=='/api/preflight':return {'preflight':{'admissible':True}}
                if path=='/api/action':raise RuntimeError('NEW_SUBMISSION_RESPONSE_LOST_FIXTURE')
                raise AssertionError(path)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'plan.json').write_text(json.dumps(plan));(root/'prior.json').write_text(json.dumps(previous));original=(root/'prior.json').read_bytes();(root/'shared.bootstrap').write_text('fixture')
            args=['story','--root',str(root),'--plan',str(root/'plan.json'),'--phase','shared','--resume-from',str(root/'prior.json'),'--output',str(root/'new.json')]
            with patch.object(story,'BrowserClient',Client),patch.object(sys,'argv',args),patch.object(sys,'path',[]),patch.dict(os.environ,{},clear=True):
                with self.assertRaisesRegex(RuntimeError,'NEW_SUBMISSION_RESPONSE_LOST_FIXTURE'):story.main()
            result=json.loads((root/'new.json').read_bytes());self.assertEqual((root/'prior.json').read_bytes(),original)
            self.assertEqual(result['inputs'][0]['observed'],row);self.assertEqual(result['resumptions'][0]['previous_failure'],{'code':'OVERLOADED'})
        effects=[body for path,body in calls if path=='/api/action'];self.assertEqual(len(effects),1);self.assertEqual(effects[0]['operation'],'submit');self.assertEqual(effects[0]['text'],'episodes current');self.assertEqual(effects[0]['identity'],'fixture-story-shared-shared-1')
        changed=copy.deepcopy(previous);changed['plan_sha256']='b'*64
        with self.assertRaisesRegex(ValueError,'RESUME_BINDING'):story.resume_report(changed,plan,'shared','c'*64)
        unknown=copy.deepcopy(previous);unknown['inputs'][0]['state']='BEFORE_SUBMISSION'
        with self.assertRaisesRegex(ValueError,'UNKNOWN_SUBMISSION_OUTCOME'):story.resume_report(unknown,plan,'shared','c'*64)

class StaticRecipeBinding(unittest.TestCase):
    def parameters(self):
        from examples.pilot_browser_bind_recipes import KEYS
        result={key:'/private/fixture/'+key.lower() for key in KEYS}
        result.update(NAMESPACE='omega-ref-pilot-fixture',BROWSER_SESSION='fixture-browser',IDENTITY='fixture')
        return result

    def test_static_recipe_binding_compiles_without_executing_or_overwriting(self):
        import tempfile
        from pathlib import Path
        from examples.pilot_browser_bind_recipes import bind,NAMES
        source=Path(__file__).resolve().parents[1]/'examples/pilot_browser_recipes'
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'bound';report=bind(source,self.parameters(),out)
            self.assertEqual(set(report['files']),set(NAMES));self.assertEqual(report['process_calls'],0)
            self.assertTrue(all((out/name).stat().st_mode&0o777==0o600 for name in NAMES))
            self.assertIn('omega-ref-pilot-fixture',(out/'workflow_browser_case.py').read_text())
            self.assertFalse((Path(directory)/'private').exists())
            with self.assertRaisesRegex(ValueError,'FRESH_OUTPUT_REQUIRED'):bind(source,self.parameters(),out)

    def test_static_recipe_parameters_and_mutated_template_refuse_before_output(self):
        import tempfile,shutil
        from pathlib import Path
        from examples.pilot_browser_bind_recipes import bind
        source=Path(__file__).resolve().parents[1]/'examples/pilot_browser_recipes'
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);out=root/'bound'
            for key,value in [('NAMESPACE','omega-demo'),('KUBECONFIG',"/private/quote'"),('PRIVATE_ROOT','relative')]:
                parameters=self.parameters();parameters[key]=value
                with self.assertRaises(ValueError):bind(source,parameters,out)
                self.assertFalse(out.exists())
            copy=root/'templates';shutil.copytree(source,copy);target=copy/'rotate_browser_policy.py.in';target.write_bytes(target.read_bytes()+b'\n# changed\n')
            with self.assertRaisesRegex(ValueError,'TEMPLATE_MISMATCH'):bind(copy,self.parameters(),out)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
