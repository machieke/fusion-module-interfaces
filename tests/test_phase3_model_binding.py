"""Offline real-adapter translation, with process/network contact denied.

Model responses and approval clocks are explicit fixtures. The native text
transformation is the pinned original source; ModelService is real SQLite.
No real model binary/assets/runtime are constructed, loaded or contacted.
"""
from dataclasses import asdict
import json,socket,subprocess,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
from fusion import model_contracts as c
from fusion.contracts import canonical,digest,ContractError
from fusion.preview_model_binding import PROFILE,Client,service,inspect_configuration
from fusion.registry import descriptor_wire,selection_token


class IndependentModelBinding(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.scope='synthetic-phase3-model';self.sid=str(uuid.uuid4());self.token='synthetic-private-model-token'
        self.disclosure=dict(profile='synthetic-session-prompt/1',scope=self.scope,principals=['A'],
            max_prompt_bytes=c.MAX_PROMPT,session_authority='bounded-authenticated-model-sessions/1')
        self.path=self.root/'provider.json'
        self.cfg=dict(principals={'A':dict(credential=self.token,scopes={self.scope:['model.'+x for x in ('complete','observe','authorize','disclose')]})},
            model_binding=dict(profile=PROFILE,kind='approved-pinned-ollama',manifest=str(self.root/'plan.json'),approval=None),
            model_completion=dict(database=str(self.root/'model.sqlite'),scope=self.scope,sharing=c.PRIVACY,
                sessions=dict(profile='bounded-authenticated-model-sessions/1',principals=['A'],max_sessions=2),
                max_calls=2,expires_ms=int(time.time()*1000)+120000,catalogue=[descriptor_wire(c.descriptor(c.CPU_PROFILE))],
                disclosure=self.disclosure,runtime_lock=dict(path='/opt/generative/absent-lock.json',sha256='0'*64)))
        self.path.write_bytes(canonical(self.cfg))
        cfg=dict(binding=PROFILE,profile=c.CPU_PROFILE,fallback=False,placement='local',provider_config=str(self.path),
            principal='A',scope=self.scope,session=self.sid,credential=self.token,catalogue=self.cfg['model_completion']['catalogue'],disclosure=self.disclosure)
        self.client_path=self.root/'client.json';self.client_path.write_bytes(canonical(cfg))
        prompt="Selected synthetic native tools and retained context:-:-:-:['HUMAN-MSG:', 'task-context']"
        self.intent=asdict(c.CompletionInput(id=str(uuid.uuid4()),session=self.sid,slot=1,source_id=str(uuid.uuid4()),
            principal='A',scope=self.scope,selection=selection_token(c.descriptor(c.CPU_PROFILE)),native_prompt=prompt,
            messages=c.messages(prompt),deadline_ms=int(time.time()*1000)+30000,profile=c.CPU_PROFILE,limits=c.limits(c.CPU_PROFILE)))

    def test_missing_approval_denied_before_adapter_constructor_acceptance_or_reservation(self):
        with patch('fusion.adapters.ollama_completion.OllamaCompletion',side_effect=AssertionError('REAL_CONSTRUCTOR_FORBIDDEN')) as adapter, \
             patch.object(socket,'create_connection',side_effect=AssertionError('NETWORK_FORBIDDEN')), \
             patch.object(subprocess,'Popen',side_effect=AssertionError('PROCESS_FORBIDDEN')):
            inspect_configuration(self.path);client=Client(self.client_path)
            self.assertIs(client.contracts,c)
            self.assertEqual(client.invoke('observe',self.intent)['state'],'absent')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):client.invoke('complete',self.intent)
            self.assertEqual(client.invoke('observe',self.intent)['reserved'],0)
            adapter.assert_not_called()
        import sqlite3
        with sqlite3.connect(self.root/'model.sqlite') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM model_calls').fetchone()[0],0)

    def test_wrong_expired_and_unbound_approval_do_not_construct_backend(self):
        from integration.single_node import future_live
        approval=self.root/'approval.json';approval.write_text('{}')
        self.cfg['model_binding']['approval']=str(approval);self.path.write_bytes(canonical(self.cfg))
        # The existing approval checker itself is exercised with an immutable
        # synthetic plan. It rejects before any source/runtime asset checks.
        plan=dict(schema=future_live.SCHEMA,kind='live',freeze='COMPLETE',campaign_id='synthetic-phase3-denial',
            slots=[dict(name='first',slot=1,id=self.intent['id'],session=self.sid),dict(name='second',slot=2,id=str(uuid.uuid4()),session=self.sid)],
            provider_state='/state/live-campaign',runtime_lock=self.cfg['model_completion']['runtime_lock'])
        path=self.root/'plan.json';path.write_bytes(canonical(plan));path.with_suffix('.sha256').write_text(digest(path.read_bytes()))
        now=int(time.time()*1000)
        valid=dict(authority='EXPLICIT_USER_APPROVAL',user_statement='SYNTHETIC TEST AUTHORITY; no live permission',
            campaign_id=plan['campaign_id'],manifest_sha256=digest(path.read_bytes()),slots=['first','second'],max_generations=2,
            not_before_ms=now-5000,expires_ms=now+5000)
        with patch('fusion.adapters.ollama_completion.OllamaCompletion',side_effect=AssertionError('FORBIDDEN')) as adapter:
            for changes in ({'manifest_sha256':'0'*64},{'expires_ms':now-1},{'campaign_id':'wrong'},{'max_generations':3}):
                approval.write_bytes(canonical(dict(valid,**changes)))
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):Client(self.client_path).invoke('complete',self.intent)
            adapter.assert_not_called()

    def test_original_real_adapter_translation_with_recorded_http_boundary(self):
        from fusion.adapters.ollama_completion import OllamaCompletion,VERSION
        from fusion.adapters.neoclaw_model_text import NativeChatText
        from tests.test_model_oracle import SOURCE
        if not SOURCE.is_file():self.skipTest('PINNED_NATIVE_TEXT_SOURCE_UNAVAILABLE; offline adapter translation is not a fixture substitute')
        # Constructor asset checks are separately unrun, never bypassed in the
        # service. Here only actual request/response methods are under test.
        backend=object.__new__(OllamaCompletion);backend.port=48173;backend.native=NativeChatText(SOURCE)
        calls=[]
        def exchange(path,body=None,**kwargs):
            calls.append((path,body,kwargs))
            if path=='/api/version':return dict(version=VERSION)
            if path=='/api/tags':return dict(models=[dict(name=c.MODEL,digest=c.MODEL_DIGEST)])
            self.assertEqual(path,'/api/chat')
            return dict(model=c.MODEL,done=True,done_reason='stop',message=dict(role='assistant',content='task-context'),prompt_eval_count=7,eval_count=3)
        with patch('fusion.adapters.ollama_completion.exchange',side_effect=exchange), \
             patch.object(socket,'create_connection',side_effect=AssertionError('CONTACT_FORBIDDEN')), \
             patch.object(subprocess,'Popen',side_effect=AssertionError('LAUNCH_FORBIDDEN')):
            result=backend.complete(c.CompletionInput(**self.intent))
        self.assertEqual([x[0] for x in calls],['/api/version','/api/tags','/api/chat'])
        self.assertEqual(calls[-1][1],dict(model=c.MODEL,messages=self.intent['messages'],stream=False,think=False,truncate=False,options=c.OPTIONS))
        self.assertEqual(result['native_text'],'task-context');self.assertIsNone(result['usage']['reasoning_tokens'])

    def test_capture_observation_never_requires_new_execution_authority(self):
        from fusion.model_service import ModelService
        from tests.test_phase2_model import recorded
        result=recorded('task-context');result['observed_model']=c.MODEL
        class RecordedResponseBoundary:
            def complete(_,accepted):return result
        checks=[]
        owner=ModelService(self.path,RecordedResponseBoundary(),disclosure=lambda *args:None,contracts=c,
            execution_authority=lambda accepted:checks.append(accepted['id']))
        q=dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation='complete',intent=self.intent)
        try:first=owner.invoke(self.token,q)
        finally:owner.close()
        self.assertEqual(len(checks),2)
        owner=ModelService(self.path,RecordedResponseBoundary(),disclosure=lambda *args:None,contracts=c,
            execution_authority=lambda _:self.fail('Captured result must not request new allowance'))
        try:self.assertEqual(owner.invoke(self.token,q),first)
        finally:owner.close()

if __name__=='__main__':unittest.main()
