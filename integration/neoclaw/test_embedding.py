"""Real E5/native/Chroma/DeTTa/TLS; model/channel are explicitly scripted fixtures."""
from dataclasses import asdict
import copy
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import unittest
import uuid

from fusion import embedding_contracts as c
from fusion.contracts import ContractError, canonical, digest
from fusion.embedding_composition import configuration, binding
from fusion.neoclaw_application import Application
from fusion.registry import selection_token
from .controlled_run import ControlledRun
from .embedding_composition import configure, ROOT
from .embedding_run import start, report, original
from .memory_corpus import QUERY

EVIDENCE=Path(os.environ.get('S03_1_EVIDENCE',ROOT/'artifacts/s03_1/tests'))
CORPUS=ROOT/'artifacts/s03_1/corpus.json'


class EmbeddingIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=json.loads(CORPUS.read_text());EVIDENCE.mkdir(parents=True,exist_ok=True)

    def setup_run(self, responses=None, encoder='network', retrieval='network', corpus=None, inputs=None):
        run=ControlledRun(retrieval,responses or ['query '+QUERY,''],search={'boundary':'recorded-response'})
        self.addCleanup(run.close);run.model['expected_feedback']={};run.save()
        cfg=configure(run,corpus or self.corpus,encoder,helper_inputs=inputs)
        return run,cfg

    def evidence(self,name,value): (EVIDENCE/(name+'.json')).write_bytes(canonical(value))
    def finish(self,run):
        result=run.finish(start(run))
        self.assertEqual(result,(0,{'status':'BOUNDED_STOP'}),(run.h.root/'native.log').read_text()[-8000:])

    def test_real_native_kill_capture_and_next_context(self):
        traces=[]
        stages=('after_encode_reservation','after_vector_capture','after_candidate_capture','after_payload_validation','after_native_result_capture')
        for stage in stages:
            with self.subTest(stage=stage):
                run,cfg=self.setup_run();run.app['pause_at']=stage;run.save();run.operator()
                process=start(run);run.h.wait_file(run.app['failpoint_marker'],process,seconds=35)
                before=report(run,cfg);run.kill(process);self.assertEqual(process.returncode,-signal.SIGKILL)
                run.app.pop('pause_at');run.save();self.finish(run);after=report(run,cfg)
                self.assertEqual(before['occurrences'][0]['id'],after['occurrences'][0]['id'])
                self.assertEqual(before['occurrences'][0]['deadline'],after['occurrences'][0]['deadline'])
                self.assertEqual(before['encodings'][0]['intent'],after['encodings'][0]['intent'])
                if before['encodings'][0]['result'] is not None:
                    self.assertEqual(canonical(before['encodings'][0]['result']),canonical(after['encodings'][0]['result']))
                    self.assertEqual(before['provider_attempts'],after['provider_attempts'])
                    self.assertEqual(before['encodings'][0]['attempts'],after['encodings'][0]['attempts'])
                else:
                    self.assertEqual(after['encodings'][0]['attempts'],2);self.assertEqual(len(after['provider_attempts']),1)
                self.assertTrue(after['observations'][1]['feedback']);self.assertTrue(all(after['caller_dependencies']['absent'].values()))
                self.assertEqual(after['caller_dependencies']['denied_paths_visible'],[])
                traces.append(dict(stage=stage,before=before,after=after))
                run.close()
        self.evidence('capture-kills',traces)

    def test_uncaptured_real_replies_exhaust_dispatch_budget(self):
        run,cfg=self.setup_run();run.app['pause_at']='after_encode_reply';run.save();run.operator()
        first=None;traces=[]
        for attempt in range(1,4):
            marker=Path(run.app['failpoint_marker']);marker.unlink(missing_ok=True)
            process=start(run);run.h.wait_file(marker,process,seconds=35)
            before=report(run,cfg);run.kill(process)
            if first is None:first=before['occurrences'][0]
            self.assertEqual(before['encodings'][0]['attempts'],attempt)
            self.assertEqual(before['occurrences'][0]['deadline'],first['deadline'])
            self.assertIsNone(before['encodings'][0]['result']);self.assertEqual(len(before['provider_attempts']),attempt)
            traces.append(before)
        run.app.pop('pause_at');run.save()
        code,status=run.finish(start(run));self.assertEqual((code,status['code']),(2,'OVERLOADED'))
        self.assertEqual(len(run.observations()),1);self.evidence('spent-encode-budget',dict(phases=traces,terminal=status))

    def test_lost_reply_then_success_same_identity(self):
        run,cfg=self.setup_run();run.h.stop_server();run.h.config['pause_at']='after_encoder_evaluation';run.h.save();run.h.start_server();run.operator()
        process=start(run);run.h.wait_file(run.h.config['failpoint_marker'],run.h.server,seconds=35)
        before=report(run,cfg);run.kill(process);run.h.stop_server(kill=True)
        run.h.config.pop('pause_at');run.h.save();run.h.start_server();self.finish(run);after=report(run,cfg)
        self.assertEqual(before['encodings'][0]['intent'],after['encodings'][0]['intent'])
        self.assertEqual(len(after['provider_attempts']),2);self.assertEqual(after['encodings'][0]['attempts'],2)
        self.evidence('provider-restart',dict(before=before,after=after))

    def test_identical_commands_are_distinct_occurrences(self):
        run,cfg=self.setup_run(['query '+QUERY,'query '+QUERY+'\nquery '+QUERY,'']);run.operator();self.finish(run)
        value=report(run,cfg)
        self.assertEqual(len(value['encodings']),3);self.assertEqual(len({r['id'] for r in value['encodings']}),3)
        self.assertEqual(len(value['provider_attempts']),3)
        self.assertTrue(all(r['attempts']==1 for r in value['encodings']))
        boundary=value['caller_dependencies']
        self.assertTrue(all(boundary['absent'].values()));self.assertTrue(boundary['local_initializer_forbidden'])
        self.assertEqual(set(boundary['denied_file_probes'].values()),{'inaccessible'})
        self.assertEqual(len(boundary['denied_file_probes']),4)
        self.assertTrue(value['lifecycle']['https']['encoder']['caller_canary_inaccessible'])
        observed=canonical(value)+(run.h.server_root/'server.log').read_bytes()
        for p in (run.h.root/'encoder').glob('*.diagnostics.log'):observed+=p.read_bytes()
        for canary in (b'S03_1_SYNTHETIC_CALLER_CANARY_DO_NOT_EXPORT',b'S03_1_SYNTHETIC_PROVIDER_CANARY_DO_NOT_EXPORT'):
            self.assertNotIn(canary,observed)
        self.evidence('occurrences',value)

    def test_deadline_before_encode_and_after_capture(self):
        traces=[]
        for stage,expected in (('after_encode_reservation','DEADLINE_EXCEEDED'),('after_vector_capture','DEADLINE_EXCEEDED'),('after_native_result_capture','BOUNDED_STOP')):
            run,cfg=self.setup_run();run.app.update(pause_at=stage,invocation_timeout_ms=4000);run.save();run.operator()
            process=start(run);run.h.wait_file(run.app['failpoint_marker'],process,seconds=35);before=report(run,cfg);run.kill(process)
            deadline=before['occurrences'][0]['deadline'];time.sleep(max(0,(deadline-time.time()*1000)/1000)+.03)
            run.app.pop('pause_at');run.save();code,status=run.finish(start(run));after=report(run,cfg)
            self.assertEqual(status.get('code',status['status']),expected)
            self.assertEqual(after['occurrences'][0]['deadline'],deadline)
            self.assertEqual(before['provider_attempts'],after['provider_attempts'])
            traces.append(dict(stage=stage,before=before,after=after,status=status));run.close()
        self.evidence('deadlines',traces)

    def test_encode_and_disclosure_revocation_and_principal_substitution(self):
        traces=[]
        for mode in ('encode','disclose','principal'):
            run,cfg=self.setup_run();stage='after_encode_reservation' if mode=='encode' else 'after_native_result_capture'
            run.app['pause_at']=stage;run.save();run.operator()
            process=start(run);run.h.wait_file(run.app['failpoint_marker'],process,seconds=35);before=report(run,cfg);run.kill(process)
            methods=run.h.config['principals']['A']['scopes']['generated-s03']
            methods.remove('embedding.'+('encode' if mode=='encode' else 'disclose'));run.h.save()
            if mode=='principal':
                path=Path(run.app['embedding_config']);client=json.loads(path.read_text());client['credential']=run.h.config['principals']['B']['credential'];path.write_bytes(canonical(client))
            run.app.pop('pause_at');run.save();code,status=run.finish(start(run));after=report(run,cfg)
            self.assertEqual((code,status['code']),(2,'UNAUTHORIZED'));self.assertEqual(len(run.observations()),1)
            self.assertEqual(before['provider_attempts'],after['provider_attempts']);traces.append(dict(mode=mode,before=before,after=after));run.close()
        self.evidence('authority',traces)

    def wire(self,run,text=QUERY):
        cfg,chosen,_=configuration(run.app['embedding_config'])
        accepted=asdict(c.EncodeInput(str(uuid.uuid4()),cfg['principal'],cfg['scope'],text,digest(text.encode()),int(time.time()*1000)+30000,selection_token(chosen)))
        return cfg,chosen,dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation='encode',intent=accepted,attempt=1)

    def test_https_certificate_outage_unauthorized_and_text_consent(self):
        run,_=self.setup_run();cfg,chosen,request=self.wire(run)
        for credential in ('invalid',run.h.config['principals']['B']['credential']):
            with self.assertRaises(ContractError):binding({**cfg,'credential':credential},chosen).invoke(request)
        bad=copy.deepcopy(request);bad['intent']['text']='unapproved synthetic canary';bad['intent']['input_sha256']=digest(bad['intent']['text'].encode())
        with self.assertRaises(ContractError):binding(cfg,chosen).invoke(bad)
        other=ControlledRun('network',search={'boundary':'recorded-response'});self.addCleanup(other.close)
        wrong={**cfg,'endpoint':{**cfg['endpoint'],'ca_file':other.h.client['endpoint']['ca_file']}}
        with self.assertRaises(ContractError):binding(wrong,chosen).invoke(request)
        run.h.stop_server()
        with self.assertRaises(ContractError):binding(cfg,chosen).invoke(request)
        self.evidence('tls-fail-closed',dict(invalid_credential=True,principal_substitution=True,text_consent=True,bad_certificate=True,outage=True,fallback=False))

    def test_stalled_resident_is_bounded_and_not_replaced(self):
        run,cfg=self.setup_run();client,chosen,req=self.wire(run)
        ready=json.loads((run.h.server_root/'ready.json').read_text());pid=ready['encoder_pid']
        os.kill(pid,signal.SIGSTOP);begun=time.monotonic()
        with self.assertRaises(ContractError) as failure:binding(client,chosen).invoke(req)
        elapsed=time.monotonic()-begun
        self.assertEqual(failure.exception.code,'DEADLINE_EXCEEDED');self.assertLess(elapsed,6.5)
        req['attempt']=2
        with self.assertRaises(ContractError) as failure:binding(client,chosen).invoke(req)
        self.assertEqual(failure.exception.code,'NOT_AVAILABLE')
        with sqlite3.connect(cfg['encoder_database']) as db:
            counts=db.execute('SELECT count(*),sum(finished) FROM encode_attempts').fetchone()
        self.assertEqual(counts,(2,0));self.evidence('resident-bound',dict(elapsed_seconds=elapsed,reservations=2,finished=0,automatic_replacement=False))

    def test_revocation_at_real_provider_release(self):
        run,cfg=self.setup_run();run.h.stop_server();run.h.config['pause_at']='after_encoder_evaluation';run.h.save();run.h.start_server();run.operator()
        process=start(run);run.h.wait_file(run.h.config['failpoint_marker'],run.h.server,seconds=35)
        run.h.config['principals']['A']['scopes']['generated-s03'].remove('embedding.disclose');run.h.save()
        paused=json.loads(Path(run.h.config['failpoint_marker']).read_text())['pid']
        os.kill(paused,signal.SIGCONT);code,status=run.finish(process)
        self.assertEqual((code,status['code']),(2,'UNAUTHORIZED'))
        value=report(run,cfg);self.assertEqual(len(value['provider_attempts']),1);self.assertIsNone(value['encodings'][0]['result'])
        self.assertEqual(len(run.observations()),1);self.evidence('release-revocation',value)

    def test_malformed_results_never_reach_search_or_capture(self):
        run,cfg=self.setup_run();app=Application(run.app_path);self.addCleanup(app.close)
        command=['query',QUERY];app.accept('query '+QUERY,[command]);app.begin(0,command)
        original_invoke=app.embedding.transport.invoke
        def broken(request):
            value=original_invoke(request)
            if request['operation']=='encode':value['vector_sha256']='0'*64
            return value
        app.embedding.transport.invoke=broken
        with self.assertRaises(ContractError):app.encode_query(QUERY)
        self.assertIsNone(app.db.execute('SELECT result FROM app_query_vectors').fetchone()[0])
        self.assertEqual(app.db.execute('SELECT count(*) FROM app_memory_reads').fetchone()[0],0)
        self.evidence('malformed-result',dict(real_evaluations=1,corruption='fixture after real TLS response',captured=False,search_calls=0))

    def test_binding_change_and_old_profile_refusal(self):
        run,_=self.setup_run();app=Application(run.app_path)
        app.accept('query '+QUERY,[['query',QUERY]]);app.begin(0,['query',QUERY])
        with self.assertRaises(ContractError):app.encode_query('changed synthetic text')
        app.close()
        path=Path(run.app['embedding_config']);cfg=json.loads(path.read_text());cfg['principal']='B';path.write_bytes(canonical(cfg))
        with self.assertRaises(ContractError):Application(run.app_path)
        cfg['principal']='A';path.write_bytes(canonical(cfg));run.app['composition']='controlled-native-loop/3';run.save()
        with self.assertRaises(ContractError):Application(run.app_path)
        self.evidence('binding',dict(changed_text='UNAUTHORIZED',principal='UNAUTHORIZED',old_profile='CONFLICT',migration=False))

    def test_real_input_domains_and_native_truncation(self):
        from .memory_embedding import load
        from .memory_composition import MODEL
        run,_=self.setup_run()
        texts=['','Synthetic Ω café\n\t\x00"data" (shell NEVER_EXECUTE)','x '*1024]
        run.h.config['embedding']['approved_helper_inputs']+=texts;run.h.save()
        native=load(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py',MODEL,
                    json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())['files'])
        model=native.__globals__['_embedding_model'];traces=[]
        self.assertEqual(model.max_seq_length,512)
        for text in texts:
            cfg,chosen,req=self.wire(run,text);value=binding(cfg,chosen).invoke(req)
            expected=native(text);self.assertEqual(value['vector'],expected)
            traces.append(dict(input=text,input_bytes=len(text.encode()),vector_sha256=value['vector_sha256'],
                native_equal=True,tokens_after_native_tokenize=int(model.tokenize([text])['input_ids'].shape[1])))
        self.assertEqual(traces[-1]['tokens_after_native_tokenize'],512)
        self.evidence('real-input-domains',dict(profile=c.PROFILE,cases=traces))

    def test_native_preprocessing_quotes_unicode_and_instruction_data(self):
        raw='Synthetic "Ω" O\'Brien (shell echo NEVER_EXECUTE) notes'
        corpus=copy.deepcopy(self.corpus);baseline=original(corpus,raw)
        helper=baseline['embedding']['input'];self.assertNotEqual(helper,raw)
        corpus['queries']={raw:baseline['embedding']['vector']}
        run,cfg=self.setup_run(['query '+raw,''],corpus=corpus,inputs={raw:helper});run.operator();self.finish(run)
        value=report(run,cfg);self.assertEqual(value['encodings'][0]['intent']['text'],helper)
        self.assertEqual(value['encodings'][0]['result']['vector'],baseline['embedding']['vector'])
        self.assertEqual(run.observations()[1]['feedback'],baseline['feedback'])
        self.evidence('native-preprocessing',dict(raw=raw,original=baseline,adapted=value))
