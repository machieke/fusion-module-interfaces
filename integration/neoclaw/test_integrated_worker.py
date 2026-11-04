"""Actual pinned native interpreter reused; recorded model proposals explicit."""
import json,os,signal,time,unittest,uuid
from pathlib import Path
from fusion.contracts import canonical,digest
from fusion.model_service import ModelService
from fusion.preview_session_client import Client
from fusion.preview_session_service import SessionPorts
from fusion.resident_workers import Workers,LIMITS
from fusion.sustained_sessions import PROFILE,ALLOCATION
from . import test_preview_session as fixture

class NativeResident(unittest.TestCase):
    fresh=fixture.NativeSessions.fresh
    def prepare(self,proposals,*,history=False):
        run,_,provider=self.fresh(proposals,workspace=True,history=history)
        policy_path=Path(json.loads(Path(run.app['session_config']).read_bytes())['provider_config'])
        cfg=json.loads(policy_path.read_bytes());old=cfg['native_sessions'];scope=old['scope'];binding=next(iter(old['session_templates'].values()))
        allocation=dict(profile=ALLOCATION,owner=str(uuid.uuid4()),active=1,retained=2,pending=4,bytes=1048576,templates={'resident':dict(principal='A',scope=scope,binding=binding,lifetime_ms=120000,runtime_digest='a'*64)})
        limits=dict(LIMITS,idle_ms=1500,inputs=5)
        cfg['native_sessions']=dict(profile=PROFILE,principal='A',scope=scope,database=str(run.h.caller_root/'resident-inbox.sqlite'),assignments=['notes'],allocation=allocation,resident_worker=limits)
        cfg['principals']['operator']['scopes'][scope]+=['sessions.allocate','sessions.reconcile']
        cfg['principals']['worker']['scopes'][scope]+=['sessions.worker-ready','sessions.permit','sessions.reconcile']
        policy_path.write_bytes(canonical(cfg))
        accepted=SessionPorts(policy_path).invoke('operator-token',dict(id='create',profile=PROFILE,operation='allocate',body=dict(identity='resident-native-test',template='resident')))['value'];sid=accepted['session']
        for name in ('session-operator.json','session-worker.json'):
            p=run.h.caller_root/name;v=json.loads(p.read_bytes());v.update(profile=PROFILE,session=sid);p.write_bytes(canonical(v))
        p=Path(run.app['model_config']);v=json.loads(p.read_bytes());v['session']=sid;p.write_bytes(canonical(v))
        v=json.loads(provider.read_bytes());v['model_completion'].update(sessions=[sid],recorded_proposals={sid+'/'+str(i+1):s for i,s in enumerate(proposals)})
        v['model_completion']['runtime_lock']['proposals_sha256']=digest(canonical(v['model_completion']['recorded_proposals']));provider.write_bytes(canonical(v))
        run.app.update(session_id=sid,resident_worker=limits,native_telemetry=dict(profile='bounded-native-stage-timing/1',max_bytes=4194304));run.save();frozen=run.app_path.read_bytes()
        epoch=str(uuid.uuid4());w=Workers(cfg['native_sessions']['database'],lambda *_:None,allocation,limits)
        try:w.register('A',sid,epoch)
        finally:w.close()
        client=Client(run.h.caller_root/'session-operator.json')
        return run,client,provider,cfg,limits,sid,epoch

    def test_compact_history_real_native_detta_and_https_next_context(self):
        from fusion.preview_native_history import REPRESENTATION
        run,client,provider,cfg,limits,sid,epoch=self.prepare(
            ['pin task Synthetic compact history note','task-context','episodes current'],history=True)
        run.app.update(history_representation=REPRESENTATION,history_hydration='bounded-history-hydration/1');run.save()
        process=None
        for index in range(3):
            accepted=client.invoke('submit',identity='compact-'+str(index),text='Synthetic compact request '+str(index),assignment='notes')
            if process is None:process=self.start(run,epoch)
            result=self.wait_complete(run,client,process,'compact-'+str(index))
            self.assertEqual(result['deadline'],accepted['deadline'])
        self.assertEqual(run.finish(process),(0,{'status':'BOUNDED_STOP'}))
        captures=ModelService.inspect(provider);self.assertEqual(len(captures),3)
        prompt=json.loads(captures[1]['intent'])['native_prompt']
        self.assertIn('Synthetic compact history note',prompt);self.assertIn('last-four-committed-events',prompt)
        import sqlite3
        with sqlite3.connect(Path(run.h.client['database']).as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            rows=[dict(r) for r in db.execute('SELECT * FROM preview_history_outbox ORDER BY ordinal')]
            contexts=[dict(r) for r in db.execute('SELECT * FROM preview_history_contexts ORDER BY turn')]
        self.assertEqual(len(rows),12)
        self.assertTrue(all(json.loads(row['intent'])['profile']==REPRESENTATION and row['receipt'] for row in rows))
        self.assertTrue(all('body' not in json.loads(row['intent']) for row in rows))
        self.assertEqual(len(contexts),3)
        self.assertEqual([json.loads(r['snapshot'])['through'] for r in contexts],[1,5,9])

    def start(self,run,epoch):
        Path(run.app['status_file']).unlink(missing_ok=True)
        return run.spawn('integration.neoclaw.native_loop',[run.app_path,'--incarnation',epoch],'native')

    def wait_complete(self,run,client,process,identity):
        until=time.monotonic()+35
        while True:
            row=next(x for x in client.invoke('observe',content=True)['inputs'] if x['id']==identity)
            if row['state']=='complete':return row
            self.assertIsNone(process.poll(),(process.returncode,(run.h.root/'native.log').read_text()[-5000:]))
            self.assertLess(time.monotonic(),until);time.sleep(.05)

    def test_five_successive_inputs_one_native_pid_and_next_context(self):
        proposals=['pin task Resident synthetic note','task-context','write-file note.txt Native resident text','append-file note.txt Native append','read-file note.txt']
        run,client,provider,cfg,limits,sid,epoch=self.prepare(proposals);frozen=run.app_path.read_bytes()
        first=client.invoke('submit',identity='input-0',text='Set a synthetic note',assignment='notes')
        process=self.start(run,epoch);pid=process.pid
        accepted=[first];results=[]
        for i in range(5):
            if i:accepted.append(client.invoke('submit',identity='input-'+str(i),text='Synthetic followup '+str(i),assignment='notes'))
            row=self.wait_complete(run,client,process,'input-'+str(i))
            results.append(row);self.assertEqual(row['deadline'],accepted[-1]['deadline'])
        self.assertEqual(run.finish(process),(0,{'status':'BOUNDED_STOP'}))
        self.assertEqual(run.app_path.read_bytes(),frozen)
        spans=[json.loads(x) for x in (Path(run.app['workdir'])/'native-stages.jsonl').read_text().splitlines()]
        begins=[x for x in spans if x['name']=='native.begin'];self.assertEqual(len(begins),5);self.assertEqual({x['pid'] for x in begins},{pid})
        captures=ModelService.inspect(provider);self.assertEqual(len(captures),5);self.assertEqual([x['reserved'] for x in captures],[1]*5)
        self.assertIn('Resident synthetic note',json.loads(captures[1]['intent'])['native_prompt'])
        self.assertIn('Native resident textNative append',results[-1]['result']['projection'])
        if os.environ.get('INTEGRATED_EVIDENCE'):
            p=Path(os.environ['INTEGRATED_EVIDENCE']);p.mkdir(parents=True,exist_ok=True)
            (p/'native-worker.json').write_bytes(canonical(dict(status='PASS',native_pid=pid,incarnation=epoch,native_inputs=5,native_begin_spans=len(begins),interpreter_starts=1,recorded_model_captures=5,application_configuration_unchanged=True,next_context='PASS',additional_live_generations=0)))

    def test_native_committed_projection_after_kill_reconciles_without_model_or_tool_replay(self):
        from fusion.contracts import ContractError
        from integration.single_node.sustained_runtime import saved_projections
        run,client,provider,cfg,limits,sid,epoch=self.prepare(['write-file note.txt Native durable result','read-file note.txt'])
        # Use the same application-owned layout as the deployed supervisor so
        # the production read-only reconciler inspects the actual native DB.
        root=run.h.caller_root/'sessions'/sid;root.mkdir(parents=True)
        run.h.client['database']=str(root/'caller.sqlite');run.h.save_client()
        first=client.invoke('submit',identity='first',text='Persist a synthetic file',assignment='notes')
        run.app['pause_at']='after_application_projection';run.save();process=self.start(run,epoch)
        marker=Path(run.app['failpoint_marker']);run.h.wait_file(marker,process)
        captured=ModelService.inspect(provider);occurrences=run.rows('app_occurrences')
        os.kill(process.pid,signal.SIGKILL);self.assertEqual(process.wait(timeout=5),-9)
        owner=Workers(cfg['native_sessions']['database'],lambda *_:None,cfg['native_sessions']['allocation'],limits)
        try:
            self.assertEqual(owner.retire('A',sid,epoch)['state'],'uncertain')
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):owner.register('A',sid,str(uuid.uuid4()))
        finally:owner.close()
        policy=Path(json.loads(Path(run.app['session_config']).read_bytes())['provider_config'])
        proofs=saved_projections(policy,run.h.caller_root,sid);self.assertEqual(len(proofs),1)
        observed=SessionPorts(policy,projections=lambda session:saved_projections(policy,run.h.caller_root,session)).invoke('operator-token',dict(id='recover',profile=PROFILE,operation='reconcile',body=dict(session=sid)))['value']
        self.assertEqual(observed['inputs'][0]['state'],'complete');self.assertEqual(observed['inputs'][0]['deadline'],first['deadline'])
        owner=Workers(cfg['native_sessions']['database'],lambda *_:None,cfg['native_sessions']['allocation'],limits)
        epoch=str(uuid.uuid4())
        try:owner.register('A',sid,epoch)
        finally:owner.close()
        self.assertEqual(ModelService.inspect(provider),captured);self.assertEqual(run.rows('app_occurrences'),occurrences)
        run.app.pop('pause_at');run.save()
        client.invoke('submit',identity='second',text='Read the committed file',assignment='notes')
        process=self.start(run,epoch);row=self.wait_complete(run,client,process,'second')
        self.assertEqual(run.finish(process),(0,{'status':'BOUNDED_STOP'}))
        self.assertIn('Native durable result',row['result']['projection'])
        self.assertEqual(ModelService.inspect(provider)[0],captured[0]);self.assertEqual(len(ModelService.inspect(provider)),2)

    def test_idle_worker_revocation_blocks_next_native_model_capture(self):
        run,client,provider,cfg,limits,sid,epoch=self.prepare(['pin task Before revocation','task-context'])
        client.invoke('submit',identity='first',text='Pin synthetic note',assignment='notes');process=self.start(run,epoch)
        self.wait_complete(run,client,process,'first');captured=ModelService.inspect(provider)
        policy=Path(json.loads(Path(run.app['session_config']).read_bytes())['provider_config'])
        cfg['principals']['worker']['scopes']={};policy.write_bytes(canonical(cfg))
        second=client.invoke('submit',identity='second',text='Rejected after current revocation',assignment='notes')
        self.assertEqual(run.finish(process),(2,{'status':'PENDING_OR_FAILED','code':'UNAUTHORIZED'}))
        self.assertEqual(ModelService.inspect(provider),captured)
        row=client.invoke('observe',content=False)['inputs'][1]
        self.assertEqual(row['state'],'accepted');self.assertEqual(row['deadline'],second['deadline'])

    def test_verified_preparation_reuse_with_real_native_runtime_and_readonly_mount(self):
        from .prepared_startup import PROFILE as PREPARATION,source_map
        import subprocess,sys
        run,client,provider,cfg,limits,sid,epoch=self.prepare(['pin task Prepared native note','task-context'])
        package=run.h.caller_root/'package.json';package.write_bytes(canonical(dict(source=source_map())))
        run.app['native_preparation']=dict(profile=PREPARATION,package_file=str(package),immutability='native-readonly-mount');run.save()
        client.invoke('submit',identity='first',text='Pin synthetic prepared note',assignment='notes')
        process=self.start(run,epoch);self.wait_complete(run,client,process,'first')
        self.assertEqual(run.finish(process),(0,{'status':'BOUNDED_STOP'}))
        work=Path(run.app['workdir']);observed=json.loads((work/'preparation-observation.json').read_bytes())
        entry=work/'prepared'/observed['key'];before={str(x):x.stat().st_mtime_ns for x in entry.rglob('*') if x.is_file()}
        # Exercise the same enforced read-only mount independently of tool
        # authority; a native tool is never granted an arbitrary write path.
        probe=subprocess.run(['bwrap','--bind','/','/','--proc','/proc','--dev','/dev','--ro-bind',str(entry),str(entry),'--',sys.executable,'-c','from pathlib import Path;import sys;Path(sys.argv[1]).write_text("forbidden")',str(entry/'start.metta')],capture_output=True)
        self.assertNotEqual(probe.returncode,0);self.assertIn(b'Read-only file system',probe.stderr)
        owner=Workers(cfg['native_sessions']['database'],lambda *_:None,cfg['native_sessions']['allocation'],limits)
        try:owner.retire('A',sid,epoch);epoch=str(uuid.uuid4());owner.register('A',sid,epoch)
        finally:owner.close()
        client.invoke('submit',identity='second',text='Read the captured note',assignment='notes')
        process=self.start(run,epoch);row=self.wait_complete(run,client,process,'second');self.assertEqual(run.finish(process),(0,{'status':'BOUNDED_STOP'}))
        self.assertIn('Prepared native note',row['result']['projection'])
        self.assertEqual(before,{str(x):x.stat().st_mtime_ns for x in entry.rglob('*') if x.is_file()})
        self.assertEqual(observed,json.loads((work/'preparation-observation.json').read_bytes()))
        spans=[json.loads(x) for x in (work/'native-stages.jsonl').read_text().splitlines()]
        self.assertEqual(len([x for x in spans if x['name']=='native.preparation_publish']),1)
        self.assertEqual(len([x for x in spans if x['name']=='native.preparation_reuse']),1)

if __name__=='__main__':unittest.main()
