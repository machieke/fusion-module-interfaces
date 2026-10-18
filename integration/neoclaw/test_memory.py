"""Real Chroma + DeTTa + native PeTTa/HTTPS. Embeddings here are labelled vector fixtures.

Real E5 comparisons are an additional memory_run gate, not counted as these methods.
"""
from dataclasses import asdict
import copy,json,os,shutil,signal,sqlite3,subprocess,sys,time,unittest,uuid
from pathlib import Path
from fusion import vector_contracts as c
from fusion.contracts import ContractError,canonical,digest
from fusion.vector_composition import ReadService
from fusion.vector_enrollment import enroll
from fusion.neoclaw_memory import configuration
from fusion.vector_transport import binding
from fusion.registry import selection_token
from fusion.ports import Mutation
from .controlled_run import ControlledRun
from .memory_composition import configure
from .memory_corpus import generated,QUERY
from .memory_run import report,compare
from .search_composition import COMMAND as SEARCH_COMMAND
from tests.neoclaw_support import COMMAND,GOLDEN

EVIDENCE=Path(os.environ.get('S03_EVIDENCE','artifacts/s03/tests'));EVIDENCE.mkdir(parents=True,exist_ok=True)

class MemoryIntegration(unittest.TestCase):
    def run_fixture(self,placement='local',responses=None):
        run=ControlledRun(placement,responses or ['query '+QUERY,''],search={'boundary':'recorded-response'})
        self.addCleanup(run.close);run.model['expected_feedback']={};run.save();configure(run)
        return run
    def service(self,run):return ReadService(run.h.config_path,run.h.config['principals']['A']['credential'])
    def request(self,run):
        cfg,_,_=configuration(run.app['memory_read_config'])
        return asdict(c.VectorQuery(str(uuid.uuid4()),cfg['scope'],cfg['snapshot'],[1.]+[0.]*1023,8,int(time.time()*1000)+30000))
    def evidence(self,name,value): (EVIDENCE/(name+'.json')).write_bytes(canonical(value))
    def test_original_local_https_parity(self):
        value=compare(generated());self.evidence('three-paths',value)
        feedback=value['oracle']['feedback']
        self.assertLess(feedback.index('promoted synthetic'),feedback.index('Solar panels'))
        self.assertEqual(feedback.count('Duplicated presentation'),1)
        self.assertEqual(feedback.count('2030-01-01 00:00:00'),2)
        self.assertIn('NEVER_EXECUTE',feedback);self.assertIn('Ω',feedback)
    def test_same_installation_sequential_s01_s02_memory_and_occurrences(self):
        values=[]
        for placement in ('local','network'):
            with self.subTest(placement=placement):
                run=self.run_fixture(placement,[COMMAND,SEARCH_COMMAND,'query '+QUERY,'query '+QUERY+'\nquery '+QUERY,''])
                run.operator();self.assertEqual(run.finish(run.start()),(0,{'status':'BOUNDED_STOP'}))
                value=report(run);self.assertIn(GOLDEN,value['observations'][1]['feedback']);self.assertIn('recorded observation A',value['observations'][2]['feedback'])
                self.assertEqual(len(value['read_receipts']),3);self.assertEqual(len({r['id'] for r in value['read_receipts']}),3)
                self.assertEqual(len(value['requests']),2)  # reads never manufacture jobs/mailboxes
                values.append(value)
        self.evidence('mixed-session',values)
    def test_real_metric_freshness_rebuild_empty_and_missing_payload(self):
        run=self.run_fixture();svc=self.service(run);q=self.request(run);first=svc.search().query(q)
        rows=generated()['records'];byid={r['uuid']:r for r in rows}
        for hit in first['hits']:
            expected=sum((a-b)**2 for a,b in zip(c.vector(byid[hit['uuid']]['vector']),q['vector']))
            self.assertAlmostEqual(hit['distance'],expected,places=6)
        # A fresh accepted source head is not silently claimed by the old generation.
        svc.atoms.create(Mutation(q['scope'],'new-opaque'),'application/generated',b'opaque generated input')
        newer=copy.deepcopy(q);newer['snapshot']['head']=svc.atoms.head(q['scope'])
        newer['snapshot']['logical']=digest(canonical({k:newer['snapshot'][k] for k in ('head','corpus','embedding','index','profile')}))
        with self.assertRaises(ContractError) as error:svc.search().query(newer)
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
        before=svc.atoms.head(q['scope']);root=Path(svc.config['root'])/'search'
        shutil.rmtree(root/q['snapshot']['generation'])
        with self.assertRaises(ContractError):svc.search().query(q)
        rebuilt=svc.search().build(q['scope'],q['snapshot']['head']);self.assertEqual(rebuilt['logical'],q['snapshot']['logical']);self.assertNotEqual(rebuilt['generation'],q['snapshot']['generation'])
        after=svc.search().query({**q,'snapshot':rebuilt});self.assertEqual(after['hits'],first['hits']);self.assertEqual(before,svc.atoms.head(q['scope']))
        with self.assertRaises(ContractError):svc.search().query(q)
        empty=svc.search().build(q['scope'],{**q['snapshot']['head'],'sequence':0})
        self.assertEqual(svc.search().query({**q,'snapshot':empty})['hits'],[])
        shutil.rmtree(Path(svc.config['root'])/'payloads')
        with self.assertRaises(ContractError) as error:svc.atoms.get(first['hits'][0]['ref'])
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
        self.evidence('source-rebuild',dict(first=first,rebuilt=after,empty=empty,source_unchanged_by_rebuild=before))
    def test_index_process_kills(self):
        run=self.run_fixture();svc=self.service(run);q=self.request(run);first=svc.search().query(q);traces=[]
        for stage in ('after_index_write','before_checkpoint','after_checkpoint','after_publication'):
            marker=Path(run.h.config['failpoint_marker']);marker.unlink(missing_ok=True)
            process=run.spawn('integration.neoclaw.memory_maintenance',[run.h.config_path,'--pause-at',stage],'maintenance-'+stage)
            run.h.wait_file(marker,process);run.kill(process);self.assertEqual(process.returncode,-signal.SIGKILL)
            # Previous published generation remains usable regardless of abandoned staging.
            self.assertEqual(svc.search().query(q)['hits'],first['hits'])
            snap=svc.search().build(q['scope'],q['snapshot']['head'])
            self.assertEqual(svc.search().query({**q,'snapshot':snap})['hits'],first['hits'])
            traces.append(dict(stage=stage,killed=True,reconstructed=snap))
        self.evidence('index-kills',traces)
    def test_native_process_kills_and_frozen_handoff(self):
        traces=[]
        for stage in ('after_read_reply','after_candidate_capture','after_payload_validation','after_native_result_capture','after_application_projection'):
            with self.subTest(stage=stage):
                run=self.run_fixture('network');run.app['pause_at']=stage;run.save();run.operator()
                process=run.start();marker=Path(run.app['failpoint_marker']);run.h.wait_file(marker,process)
                before=report(run);run.kill(process);self.assertEqual(process.returncode,-signal.SIGKILL)
                run.app.pop('pause_at');run.save()
                self.assertEqual(run.finish(run.start()),(0,{'status':'BOUNDED_STOP'}))
                after=report(run)
                self.assertEqual(before['occurrences'][0]['id'],after['occurrences'][0]['id'])
                self.assertEqual(before['occurrences'][0]['deadline'],after['occurrences'][0]['deadline'])
                if before['read_receipts'][0]['candidates'] is not None:
                    self.assertEqual(before['read_receipts'][0]['candidates'],after['read_receipts'][0]['candidates'])
                    self.assertEqual(before['read_receipts'][0]['queries'],after['read_receipts'][0]['queries'])
                if before['occurrences'][0]['result'] is not None:self.assertEqual(before['occurrences'][0]['result'],after['occurrences'][0]['result'])
                self.assertIn('Solar panels',after['observations'][1]['feedback']);traces.append(dict(stage=stage,before=before,after=after))
        self.evidence('caller-kills',traces)
    def test_https_auth_scope_model_certificate_and_outage(self):
        run=self.run_fixture('network');cfg,chosen,_=configuration(run.app['memory_read_config']);q=self.request(run);d=chosen['search']
        wire=dict(request_id=q['request_id'],scope=q['scope'],interface_ref=dict(id='search',version=d.version),operation='query',profile=c.PROFILE,selection=selection_token(d),body=q)
        self.assertEqual(len(binding(cfg,chosen).invoke(wire)['hits']),8)
        for changed in ({**cfg,'credential':'invalid'},):
            with self.assertRaises(ContractError):binding(changed,chosen).invoke(wire)
        bad=copy.deepcopy(wire);bad['scope']='private'
        with self.assertRaises(ContractError):binding(cfg,chosen).invoke(bad)
        bad=copy.deepcopy(wire);bad['body']['snapshot']['embedding']=c.EMBEDDING
        bad['body']['snapshot']['logical']=digest(canonical({k:bad['body']['snapshot'][k] for k in ('head','corpus','embedding','index','profile')}))
        with self.assertRaises(ContractError):binding(cfg,chosen).invoke(bad)
        # A valid certificate from another generated service is not trusted here.
        other=self.run_fixture('network');badcfg={**cfg,'endpoint':{**cfg['endpoint'],'ca_file':other.h.client['endpoint']['ca_file']}}
        with self.assertRaises(ContractError):binding(badcfg,chosen).invoke(wire)
        run.h.config['principals']['A']['scopes'][q['scope']]=[];run.h.save()
        with self.assertRaises(ContractError) as error:binding(cfg,chosen).invoke(wire)
        self.assertEqual(error.exception.code,'UNAUTHORIZED')
        run.h.stop_server()
        with self.assertRaises(ContractError) as error:binding(cfg,chosen).invoke(wire)
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
    def test_captured_disclosure_revocation(self):
        run=self.run_fixture('network');run.app['pause_at']='after_native_result_capture';run.save();run.operator()
        process=run.start();run.h.wait_file(run.app['failpoint_marker'],process);run.kill(process)
        run.h.config['principals']['A']['scopes']['generated-s03']=[];run.h.save();run.app.pop('pause_at');run.save()
        code,status=run.finish(run.start());self.assertEqual(code,2);self.assertEqual(status['code'],'UNAUTHORIZED')
        self.assertEqual(len(run.observations()),1);self.evidence('revoked-capture',report(run))
    def test_lost_replies_spend_original_budget(self):
        run=self.run_fixture('network');run.app['pause_at']='after_read_reply';run.save();run.operator()
        before=None
        for attempt in range(3):
            marker=Path(run.app['failpoint_marker']);marker.unlink(missing_ok=True)
            process=run.start();run.h.wait_file(marker,process);run.kill(process)
            value=report(run)
            if before is None:before=value['occurrences'][0]
            self.assertEqual(value['occurrences'][0]['id'],before['id'])
            self.assertEqual(value['occurrences'][0]['deadline'],before['deadline'])
            self.assertEqual(value['read_receipts'][0]['queries'],attempt+1)
        run.app.pop('pause_at');run.save()
        code,status=run.finish(run.start());self.assertEqual((code,status['code']),(2,'OVERLOADED'))
        self.assertEqual(len(run.observations()),1);self.evidence('spent-budget',report(run))

    def test_expired_uncaptured_read_and_expired_captured_disclosure(self):
        traces=[]
        for stage,expected in (('after_candidate_capture','DEADLINE_EXCEEDED'),('after_native_result_capture','BOUNDED_STOP')):
            run=self.run_fixture('network');run.app.update(pause_at=stage,invocation_timeout_ms=5000);run.save();run.operator()
            process=run.start();run.h.wait_file(run.app['failpoint_marker'],process);run.kill(process)
            before=report(run);deadline=before['occurrences'][0]['deadline']
            time.sleep(max(0,(deadline-int(time.time()*1000))/1000)+.03)
            run.app.pop('pause_at');run.save();code,status=run.finish(run.start())
            self.assertEqual(status.get('code',status['status']),expected)
            after=report(run);self.assertEqual(deadline,after['occurrences'][0]['deadline'])
            self.assertEqual(before['read_receipts'][0]['queries'],after['read_receipts'][0]['queries'])
            traces.append(dict(stage=stage,before=before,after=after,status=status))
        self.evidence('original-deadline',traces)

    def test_malformed_hydration_and_changed_selection_fail_closed(self):
        from unittest.mock import patch
        from fusion.neoclaw_application import Application
        from fusion.vector_transport import ReadLocal
        run=self.run_fixture();original=ReadLocal.invoke
        def damaged(transport,request):
            value=original(transport,request)
            if request['operation']=='getMany':value[0]['data']='Y29ycnVwdA=='
            return value
        app=Application(run.app_path)
        try:
            commands=[['query',QUERY]];app.accept('query '+QUERY,commands);app.begin(0,commands[0])
            with patch.object(ReadLocal,'invoke',damaged),self.assertRaises(ContractError):app.read_candidates([1.]+[0.]*1023,8)
            self.assertIsNone(app.memory.current()['result'])
            cfg=json.loads(Path(run.app['memory_read_config']).read_text());cfg['catalogue'][0]['implementation_version']='9.0.0'
            Path(run.app['memory_read_config']).write_bytes(canonical(cfg))
            with self.assertRaises(ContractError):app.read_candidates([1.]+[0.]*1023,8)
        finally:app.close()

    def test_enrollment_replay_and_invalid_feed_do_not_publish(self):
        run=self.run_fixture();svc=self.service(run);q=self.request(run);head=svc.atoms.head(q['scope'])
        row=generated()['records'][0];value=dict(scope=q['scope'],corpus=svc.config['corpus'],uuid=row['uuid'],time=row['time'],content=row['content'])
        # Original enrollment was operator-owned: replay with that same authenticated owner.
        worker=ReadService(run.h.config_path,run.h.config['principals']['worker']['credential'])
        enroll(worker.atoms,q['scope'],svc.config['corpus'],c.FIXTURE,'generated-0',value,row['vector'])
        self.assertEqual(head,svc.atoms.head(q['scope']))
        with self.assertRaises(ContractError):enroll(worker.atoms,q['scope'],svc.config['corpus'],c.FIXTURE,'generated-0',{**value,'content':'changed'},row['vector'])
        old=svc.search().current()
        svc.atoms.create(Mutation(q['scope'],'bad-enrollment'),c.ENROLLMENT,canonical({'scope':q['scope'],'corpus':svc.config['corpus']}))
        with self.assertRaises(ContractError):svc.search().build(q['scope'],svc.atoms.head(q['scope']))
        self.assertEqual(svc.search().current(),old);self.assertEqual(len(svc.search().query(q)['hits']),8)

    def test_other_scope_does_not_affect_rank_or_watermark(self):
        run=self.run_fixture();svc=self.service(run);q=self.request(run);first=svc.search().query(q);head=svc.atoms.head(q['scope'])
        original=copy.deepcopy(run.h.config)
        # Operator prepares a second explicitly generated scope through the same
        # AtomStorage owner and genuine current policy, before any loop admission.
        other='generated-other';run.h.config['memory_read']['scope']=other
        run.h.config['principals']['A']['scopes'][other]=list(run.h.config['principals']['A']['scopes'][q['scope']]);run.h.save()
        second=self.service(run)
        row=generated()['records'][0]
        value=dict(scope=other,corpus=svc.config['corpus'],uuid=str(uuid.uuid4()),time=row['time'],content='Other scope must not rank')
        enroll(second.atoms,other,svc.config['corpus'],c.FIXTURE,'other',value,[1.]+[0.]*1023)
        other_head=second.atoms.head(other);other_snapshot=second.search().build(other,other_head)
        run.h.config=original;run.h.save()
        self.assertEqual(svc.atoms.head(q['scope']),head)
        self.assertEqual(svc.search().query(q)['hits'],first['hits'])
        with self.assertRaises(ContractError):svc.atoms.head(other)
        with self.assertRaises(ContractError):svc.search().query({**q,'scope':other,'snapshot':other_snapshot})
        self.evidence('scope-isolation',dict(visible_head=head,foreign_sequence=other_head['sequence'],unchanged_hits=True))

    def test_mutable_and_mixed_admission_rejected(self):
        for command in ('promote 2030-01-01_00:00:00','metta (+ 1 2)','query '+QUERY+'\n'+SEARCH_COMMAND):
            with self.subTest(command=command):
                run=self.run_fixture(responses=[command,'']);code,status=run.finish(run.start())
                self.assertEqual(code,2);self.assertEqual(status['code'],'UNSUPPORTED_PROFILE' if '\n' in command else 'UNSUPPORTED_OPERATION')
                self.assertEqual(run.rows('app_occurrences'),[])

if __name__=='__main__':unittest.main()
