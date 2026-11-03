"""Actual pinned native consumer, inactive real model binding; ZERO generation.

The service refuses missing campaign approval before accepting/reserving a call.
The historical recorded model test remains a separate exercised path.
"""
import json,time,unittest,uuid,sqlite3
from pathlib import Path
from fusion import model_contracts as c
from fusion.contracts import canonical
from fusion.model_service import ModelService
from fusion.preview_model_binding import PROFILE as BINDING
from fusion.preview_session_client import Client
from fusion.preview_session_service import SessionPorts
from fusion.registry import descriptor_wire
from fusion.sustained_sessions import PROFILE,ALLOCATION
from . import test_preview_session as native_test


class NativeBinding(unittest.TestCase):
    fresh=native_test.NativeSessions.fresh
    def test_same_native_consumer_denies_live_before_provider_acceptance(self):
        run,old,provider=self.fresh(['UNUSED_RECORDED_PROVIDER'])
        path=Path(old.path) if hasattr(old,'path') else Path(run.app['session_config']).with_name('session-operator.json')
        operator_cfg=json.loads(path.read_bytes());policy_path=Path(operator_cfg['provider_config']);policy=json.loads(policy_path.read_bytes())
        selected=policy['native_sessions'];scope=selected['scope'];binding=next(iter(selected['session_templates'].values()))
        binding.update(model_boundary='LIVE_APPROVAL_REQUIRED',limits=dict(inputs=4,pending=4,timeout_ms=30000))
        template=dict(principal='A',scope=scope,binding=binding,lifetime_ms=120000,runtime_digest='a'*64)
        allocation=dict(profile=ALLOCATION,owner=str(uuid.uuid4()),active=1,retained=1,pending=4,bytes=1048576,templates={'live-disabled':template})
        policy['native_sessions']=dict(profile=PROFILE,principal='A',scope=scope,database=str(run.h.caller_root/'live-inbox.sqlite'),assignments=['notes'],allocation=allocation)
        policy['principals']['operator']['scopes'][scope]+=['sessions.allocate']
        policy['principals']['worker']['scopes'][scope]+=['sessions.permit']
        policy_path.write_bytes(canonical(policy))
        accepted=SessionPorts(policy_path).invoke('operator-token',dict(id='allocate',profile=PROFILE,operation='allocate',body=dict(identity='disabled-live-consumer',template='live-disabled')))['value']
        sid=accepted['session']
        for name in ('session-operator.json','session-worker.json'):
            target=run.h.caller_root/name;cfg=json.loads(target.read_bytes());cfg.update(profile=PROFILE,session=sid);target.write_bytes(canonical(cfg))
        client=Client(run.h.caller_root/'session-operator.json')
        disclosure=dict(profile='synthetic-session-prompt/1',scope=scope,principals=['A'],max_prompt_bytes=c.MAX_PROMPT,session_authority='bounded-authenticated-model-sessions/1')
        cfg=json.loads(provider.read_bytes());m=cfg['model_completion']
        m.update(sessions=[sid],max_calls=2,disclosure=disclosure,catalogue=[descriptor_wire(c.descriptor(c.CPU_PROFILE))],
            runtime_lock=dict(path='/opt/generative/missing-lock.json',sha256='0'*64))
        m.pop('recorded_proposals');cfg['model_binding']=dict(profile=BINDING,kind='approved-pinned-ollama',manifest='/config/not-approved.json',approval=None)
        provider.write_bytes(canonical(cfg))
        target=Path(run.app['model_config']);cfg=json.loads(target.read_bytes());cfg.update(binding=BINDING,profile=c.CPU_PROFILE,session=sid,disclosure=disclosure,catalogue=m['catalogue']);target.write_bytes(canonical(cfg))
        run.app.update(session_id=sid,turn_limit=4);run.save()
        received=client.invoke('submit',identity='original-live-occurrence',text='Read the synthetic task context',assignment='notes')
        result=run.finish(run.start())
        self.assertEqual(result,(2,{'status':'PENDING_OR_FAILED','code':'UNAUTHORIZED'}),result)
        self.assertEqual(ModelService.inspect(provider),[])
        with sqlite3.connect(run.h.client['database']) as db:
            db.row_factory=sqlite3.Row
            rows=[dict(r) for r in db.execute('SELECT * FROM app_model_calls')]
        self.assertEqual(len(rows),1)
        self.assertEqual(json.loads(rows[0]['intent'])['deadline_ms'],received['deadline'])
        self.assertIsNone(rows[0]['result']);self.assertEqual(run.rows('app_occurrences'),[])
        observed=client.invoke('observe',content=False)['inputs'][0]
        self.assertEqual(observed['state'],'dispatched')  # Denial is not fabricated no-effect completion.

if __name__=='__main__':unittest.main()
