"""Real loopback HTTP and guarded command construction; operator is a fixture."""
import json,unittest,uuid
from unittest.mock import patch
from fusion.contracts import canonical
from tests import test_phase2_workbench as fixture


class MaintenanceHTTP(fixture.WorkbenchHTTPTests):
    def test_new_routes_require_separate_browser_authority_before_operator(self):
        before=len(self.operator.calls)
        requests=[('/api/preflight',dict(role='omega-agent',session=self.operator.sid,commands=[['query','synthetic']])),
            ('/api/continuation',dict(role='omega-agent',session=self.operator.sid,occurrence=str(uuid.uuid4()),operation='cancel',identity='stable')),
            ('/api/search-maintenance',dict(role='omega-agent',session=self.operator.sid,operation='planRepair',args=[{}]))]
        for route,body in requests:
            raw=canonical(body);headers=[('Host','127.0.0.1:'+str(self.port)),('Origin','http://127.0.0.1:'+str(self.port)),('Content-Type','application/json'),('Content-Length',str(len(raw))),('Authorization','Bearer wrong')]
            self.assert_error(self.request('POST',route,raw=raw,headers=headers),'UNAUTHORIZED')
        self.assertEqual(len(self.operator.calls),before)
    def test_preflight_passes_typed_batch_as_stdin_not_shell_or_tool_execution(self):
        commands=[['pin','note','literal $(no-execution) <script>not html</script>']]
        with patch.object(self.operator,'k',return_value=json.dumps(dict(preflight='RECORDED_FIXTURE'))) as called:
            status,_,raw=self.request('POST','/api/preflight',dict(role='omega-agent',session=self.operator.sid,commands=commands))
        self.assertEqual(status,200);args,kwargs=called.call_args
        self.assertEqual(json.loads(kwargs['data']),commands);self.assertNotIn(commands[0][2],' '.join(args))
        self.assertIn('preview_operator import capabilities',args[-2])
    def test_repair_scope_is_selected_session_and_no_arbitrary_maintenance(self):
        self.workbench.agents['omega-agent']['sessions'][self.operator.sid]={'scope':'synthetic-workbench'}
        body=dict(role='omega-agent',session=self.operator.sid,operation='repair',args=[{'plan':'EXPLICIT_FIXTURE'},'stable-repair',123])
        with patch.object(self.operator,'k',return_value=json.dumps(dict(state='FIXTURE'))) as called:
            status,_,_=self.request('POST','/api/search-maintenance',body)
        self.assertEqual(status,200);args,kwargs=called.call_args
        self.assertIn('fusion-search-0',args);self.assertEqual(json.loads(kwargs['data'])['scope'],'synthetic-workbench')
        for changes in (dict(operation='erase-source'),dict(scope='synthetic-other'),dict(session=str(uuid.uuid4()))):
            self.assert_error(self.request('POST','/api/search-maintenance',{**body,**changes}))
    def test_continuation_control_preserves_explicit_occurrence_and_identity(self):
        occurrence=str(uuid.uuid4());body=dict(role='omega-agent',session=self.operator.sid,occurrence=occurrence,operation='cancel',identity='do-not-renew')
        self.assertEqual(self.request('POST','/api/continuation',body)[0],200)
        args=self.operator.calls[-1][0];self.assertIn(occurrence,args);self.assertIn('do-not-renew',args)
        self.assert_error(self.request('POST','/api/continuation',{**body,'operation':'restart'}),'UNSUPPORTED_OPERATION')

def load_tests(loader,tests,pattern):
    names=[n for n in MaintenanceHTTP.__dict__ if n.startswith('test_')]
    return unittest.TestSuite(MaintenanceHTTP(n) for n in names)

if __name__=='__main__':unittest.main()
