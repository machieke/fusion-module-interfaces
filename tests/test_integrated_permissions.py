"""Metadata preflight over actual configured catalogue and application owner.

No service probe, native process, model, provider effect or private payload read.
"""
import json,sqlite3,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,ContractError
from fusion.preview_session_service import SessionPorts
from fusion.sustained_sessions import PROFILE as SESSIONS
from fusion.preview_tools import Catalogue,SessionAuthority,context_tools
from integration.single_node.integrated_permissions import PROFILE,invoke,explain
from integration.single_node.sustained_current import observation_template
from tests import test_phase3_composition as fixture


class CapabilityInspection(unittest.TestCase):
    settings=fixture.DynamicConfiguration.settings
    build=fixture.DynamicConfiguration.build
    def setUp(self):
        fixture.DynamicConfiguration.setUp(self)
        for spec in self.preview['agents'].values():spec['tools']+=['pin','unpin','task-context']
        _,self.cfg,self.state,self.run=self.build();self.path=self.run/'owner.json';self.token=self.cfg['principals']['operator']['credential']
        result=SessionPorts(self.path).invoke(self.token,dict(id='allocate',profile=SESSIONS,operation='allocate',body=dict(identity='metadata-test',template='shared')))
        self.sid=result['value']['session']
    def request(self,commands=None,principal='A',token=None):
        return invoke(self.path,self.state,self.run,self.token if token is None else token,
            dict(profile=PROFILE,id=str(uuid.uuid4()),session=self.sid,principal=principal,commands=commands))['value']
    def test_no_application_materialization_or_provider_call_and_batch_matches_real_catalogue(self):
        with patch('fusion.preview_transport.invoke',side_effect=AssertionError('no remote call')):
            value=self.request([['pin','task','Unverified synthetic task']])
        self.assertTrue(value['preflight']['admissible']);self.assertFalse(value['acceptance_created'])
        self.assertFalse((self.run/'sessions'/self.sid).exists())
        with sqlite3.connect(self.cfg['native_sessions']['database']) as db:self.assertEqual(db.execute('SELECT count(*) FROM preview_inputs').fetchone()[0],0)
        denied=self.request([['pin','task','Synthetic'],['execute-anything','bad']])
        self.assertFalse(denied['preflight']['admissible']);self.assertEqual(denied['preflight']['reason'],'UNSUPPORTED_OPERATION')
        self.assertNotIn('Synthetic',canonical(denied).decode())
    def test_current_revocation_substituted_principal_and_operator_authority(self):
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.request(principal='B')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.request(token='wrong-token')
        recipe=self.cfg['native_sessions']['runtime_templates']['shared'];app=observation_template(recipe)
        file=Path(app['preview']['authority_file']);raw=json.loads(file.read_bytes());raw['revoked']=True;file.write_bytes(canonical(raw))
        value=self.request([['task-context']]);self.assertFalse(value['preflight']['admissible']);self.assertTrue(value['revoked'])
        self.assertTrue(all(not x['local_authority'] for x in value['tools']))
        self.cfg['principals']['operator']['scopes'][self.scope]=[];self.path.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.request()
    def test_self_recipient_wrong_shapes_and_scope_do_not_pass_preflight(self):
        from fusion.preview_tools import task_tools
        from fusion.preview_tasks import descriptor
        tools=task_tools();cat=Catalogue(tools,{t.tool_id for t in tools},[descriptor()])
        now=time.time_ns()//1000000;authority=SessionAuthority('A',self.scope,frozenset({'delegate'}),'p1',now+60000)
        value=explain(cat,authority,'A',self.scope,now,[['delegate','A','synthetic retrieval']],session_state='active',model_boundary='RECORDED_FIXTURE')
        self.assertFalse(value['preflight']['admissible'])
        self.assertEqual(value['preflight']['reason'],'UNAUTHORIZED')
        value=self.request([['pin','invalid label','note']]);self.assertFalse(value['preflight']['admissible'])
        with self.assertRaises(ContractError):self.request('raw unparsed command')
    def test_lifecycle_disabled_provider_and_live_model_are_separate_denials(self):
        tools=context_tools();cat=Catalogue(tools,{t.tool_id for t in tools},[])
        authority=SessionAuthority('A',self.scope,frozenset({'task-context'}),'p1',time.time_ns()//1000000+60000)
        def check(state='active',model='RECORDED_FIXTURE',providers=None):
            return explain(cat,authority,'A',self.scope,time.time_ns()//1000000,[['task-context']],session_state=state,model_boundary=model,provider_states=providers)['preflight']
        self.assertTrue(check()['admissible'])
        self.assertEqual(check(state='paused')['reason'],'SESSION_NOT_ACTIVE')
        self.assertEqual(check(model='LIVE_APPROVAL_REQUIRED')['reason'],'MODEL_LIVE_APPROVAL_REQUIRED')
        self.assertEqual(check(providers={'synthetic':{'current':{'state':'disabled'}}})['reason'],'SELECTED_PROVIDER_DISABLED')

if __name__=='__main__':unittest.main()
