"""Real pinned native session loop; authored model proposals, no live model."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import unittest
import uuid

from fusion import preview_model_contracts as c
from fusion.contracts import canonical, digest
from fusion.model_service import ModelService
from fusion.preview_application import APPLICATION, configuration
from fusion.preview_session_client import Client
from fusion.preview_sessions import PROFILE
from fusion.registry import descriptor_wire
from .controlled_run import ControlledRun


class NativeSessions(unittest.TestCase):
    def fresh(self, responses, *, workspace=False, history=False):
        root = None
        if os.environ.get('PHASE2_EVIDENCE'):
            root = Path(os.environ['PHASE2_EVIDENCE']).resolve()/'private-runs'/uuid.uuid4().hex
        run = ControlledRun('local', ['unused'], root=root)
        self.addCleanup(run.close)
        sid, scope = str(uuid.uuid4()), 'synthetic-preview-session'
        authority = run.h.caller_root/'authority.json'
        tools=['pin','unpin','task-context']+(['read-file','write-file','append-file'] if workspace else [])
        if history:tools.append('episodes')
        authority.write_bytes(canonical(dict(principal='A', scope=scope, tools=tools,
            revision='preview-session-policy-1', expires_ms=int(time.time()*1000)+120000, revoked=False)))
        run.app.update(composition=APPLICATION, session_id=sid, turn_limit=8, preparation_diagnostics=True,
            preview=dict(profile=APPLICATION, base='controlled-native-loop/1', authority_file=str(authority),
                         tools=tools, scope=scope))
        if workspace:
            from fusion.preview_ports import COMPOSITION,descriptor,OPERATIONS
            selected=descriptor_wire(descriptor('execution.workspace'))
            owner=run.h.server_root/'workspace.json'
            owner.write_bytes(canonical(dict(composition=COMPOSITION,scope=scope,root=str(run.h.server_root/'workspace'),
                descriptors={'execution.workspace':selected},principals={'A':dict(credential='workspace-token',
                    scopes={scope:['execution.workspace.'+op for op in OPERATIONS['execution.workspace']]})})))
            client=run.h.caller_root/'workspace-client.json'
            client.write_bytes(canonical(dict(composition=COMPOSITION,scope=scope,principal='A',placement='local',fallback=False,
                credential='workspace-token',provider_config=str(owner),descriptors={'execution.workspace':selected})))
            run.app['facet_configs']={'execution.workspace':str(client)}
            run.app['preview']['providers']=[selected]
        if history:
            from .preview_history_qualification import configure
            self.addCleanup(configure(run,scope))
        run.app.pop('model_fixture')
        catalogue = configuration(run.app['preview'])
        policy = dict(principals={
            'operator':dict(credential='operator-token',scopes={scope:['sessions.'+op for op in ('create','submit','observe','disclose','pause','resume','close')]}),
            'worker':dict(credential='worker-token',scopes={scope:['sessions.next','sessions.complete']})},
            native_sessions=dict(profile=PROFILE, model_boundary='RECORDED_FIXTURE', principal='A',scope=scope,
                database=str(run.h.caller_root/'inbox.db'), assignments=['notes'],session_templates={sid:dict(
                    catalogue=catalogue.identity,policy='preview-session-policy-1',model_boundary='RECORDED_FIXTURE',
                    limits=dict(inputs=8,pending=4,timeout_ms=30000))}))
        session_policy = run.h.caller_root/'session-policy.json'; session_policy.write_bytes(canonical(policy))
        operator_cfg = dict(profile=PROFILE, placement='local', provider_config=str(session_policy),
                            actor='operator', principal='A',session=sid, credential='operator-token')
        operator = run.h.caller_root/'session-operator.json'; operator.write_bytes(canonical(operator_cfg))
        worker = run.h.caller_root/'session-worker.json'; worker.write_bytes(canonical(dict(operator_cfg,actor='worker',credential='worker-token')))
        run.app['session_config'] = str(worker)
        proposals = {sid+'/'+str(i+1):text for i,text in enumerate(responses)}
        disclosure = dict(profile='synthetic-recorded-prompt/1',scope=scope,principals=['A'],max_prompt_bytes=c.MAX_PROMPT)
        provider_cfg = dict(principals={'A':dict(credential='model-token',scopes={scope:['model.'+op for op in ('disclose','complete','observe','authorize')]})},
            model_completion=dict(database=str(run.h.server_root/'preview-model.db'),scope=scope,sharing=c.PRIVACY,
                sessions=[sid],max_calls=8,expires_ms=int(time.time()*1000)+120000,
                catalogue=[descriptor_wire(c.descriptor())],disclosure=disclosure,recorded_proposals=proposals,
                runtime_lock=dict(profile=c.PROFILE,generative_runtime='FORBIDDEN',proposals_sha256=digest(canonical(proposals)))))
        provider = run.h.server_root/'preview-model.json'; provider.write_bytes(canonical(provider_cfg))
        model = run.h.caller_root/'preview-model-client.json'
        model.write_bytes(canonical(dict(profile=c.PROFILE,placement='local',fallback=False,
            provider_config=str(provider),principal='A',scope=scope,session=sid,disclosure=disclosure,
            catalogue=[descriptor_wire(c.descriptor())],credential='model-token')))
        run.app['model_config'] = str(model); run.save()
        client = Client(operator); client.invoke('create')
        return run, client, provider

    def finish(self, run, process):
        result = run.finish(process)
        self.assertEqual(result,(0,{'status':'BOUNDED_STOP'}),
                         (result,(run.h.root/'native.log').read_text()[-5500:]))

    def test_new_inputs_same_configuration_and_actual_next_context(self):
        run, client, provider = self.fresh(['pin task Native session note','task-context','unpin task'])
        bound = run.app_path.read_bytes()
        first = client.invoke('submit',identity='first',text='Set a synthetic task note',assignment='notes')
        self.finish(run,run.start())
        state = client.invoke('observe',content=True)
        self.assertEqual(state['inputs'][0]['state'],'complete')
        self.assertIn('Native session note',state['inputs'][0]['result']['projection'])
        second = client.invoke('submit',identity='second',text='Set a synthetic task note',assignment='notes')
        self.assertNotEqual(first['id'],second['id'])
        self.finish(run,run.start())
        client.invoke('submit',identity='third',text='Clear the task',assignment='notes')
        self.finish(run,run.start())
        self.assertEqual(bound,run.app_path.read_bytes())
        captures = ModelService.inspect(provider)
        self.assertEqual(len(captures),3)
        prompt = json.loads(captures[1]['intent'])['native_prompt']
        self.assertIn('COMMAND_RETURN',prompt)
        self.assertIn('Native session note',prompt.split('UNVERIFIED_TASK_CONTEXT_JSON: ')[1])
        for row, inp in zip(run.rows('app_occurrences'),client.invoke('observe',content=False)['inputs']):
            self.assertEqual(row['deadline'],inp['deadline'])
        self.assertEqual([x['reserved'] for x in captures],[1,1,1])
        self.assertTrue(all(x['response'] is not None for x in captures))

    def test_native_capture_recovery_and_whole_batch_rejection(self):
        run, client, provider = self.fresh(['pin task Captured proposal','pin task must not commit\nmetta (+ 1 2)'])
        client.invoke('submit',identity='first',text='Pin a synthetic note',assignment='notes')
        run.app['pause_at']='after_model_provider_reply'; run.save()
        process=run.start(); marker=Path(run.app['failpoint_marker']); run.h.wait_file(marker,process)
        before=ModelService.inspect(provider)[0]
        os.kill(json.loads(marker.read_text())['pid'],signal.SIGKILL)
        self.assertIn(process.wait(timeout=5),(-9,137))
        run.app.pop('pause_at');run.save();self.finish(run,run.start())
        self.assertEqual(before,ModelService.inspect(provider)[0])
        client.invoke('submit',identity='second',text='An unsupported proposal should fail',assignment='notes')
        result=run.finish(run.start())
        self.assertEqual(result,(2,{'status':'PENDING_OR_FAILED','code':'UNSUPPORTED_OPERATION'}))
        self.assertEqual(len(run.rows('app_occurrences')),1)
        self.assertEqual(client.invoke('observe',content=False)['inputs'][1]['state'],'accepted')

    def test_native_bounded_file_tools_and_next_model_feedback(self):
        run,client,provider=self.fresh(['write-file note.txt Native file text',
            'append-file note.txt Second native line','read-file note.txt'],workspace=True)
        for index in range(3):
            client.invoke('submit',identity='input-'+str(index),text='Synthetic file task '+str(index),assignment='notes')
            self.finish(run,run.start())
        result=json.loads(run.rows('app_occurrences')[-1]['result'])
        self.assertEqual(result['text'],'Native file textSecond native line\n')
        self.assertEqual(result['revision'],2)
        self.assertIn('COMMAND_RETURN',json.loads(ModelService.inspect(provider)[-1]['intent'])['native_prompt'])
        self.assertEqual((run.h.server_root/'workspace/workspace/note.txt').read_text(),result['text'])

    def test_native_history_episodes_through_real_detta_and_https(self):
        run,client,provider=self.fresh(['pin task History note','episodes current'],history=True)
        for index in range(2):
            client.invoke('submit',identity='history-'+str(index),text='Synthetic history request '+str(index),assignment='notes')
            self.finish(run,run.start())
        result=json.loads(run.rows('app_occurrences')[-1]['result'])
        kinds=[event['kind'] for event in result['events']]
        self.assertEqual(kinds[:4],['input-receipt','model-proposal','command-admitted','tool-result'])
        self.assertIn('History note',json.dumps(result))
        self.assertTrue(result['episode'].startswith('oh1:episode:'))
        prompt=json.loads(ModelService.inspect(provider)[1]['intent'])['native_prompt']
        history=prompt.split(' HISTORY: ',1)[1].split(' MOST_PROMOTED_MEMORIES:',1)[0]
        self.assertIn('tool-result',history)
        self.assertIn('History note',history)
        # Restart after completed turns performs owner-authoritative handoff,
        # never appends duplicate administrative events or calls the fixture.
        before=ModelService.inspect(provider)
        self.finish(run,run.start())
        self.assertEqual(before,ModelService.inspect(provider))


if __name__ == '__main__': unittest.main()
