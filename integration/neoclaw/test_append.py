"""S03.2 real providers; external model/channel and fault injection are declared."""
import copy
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import unittest
from fusion import append_contracts as c,vector_contracts as v
from fusion.contracts import canonical,ContractError,digest
from fusion.neoclaw_application import Application
from fusion.append_composition import configuration,AppendService
from fusion.append_transport import binding
from fusion.registry import selection_token
from .append_composition import configure
from .append_oracle import TEXT,QUERY,original
from .append_run import report,compare
from .controlled_run import ControlledRun
from .embedding_run import start
from .memory_composition import ROOT

EVIDENCE=Path(os.environ.get('S03_2_EVIDENCE',ROOT/'artifacts/s03_2/tests'))


class AppendIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=json.loads((ROOT/'artifacts/s03_2/corpus.json').read_text());EVIDENCE.mkdir(parents=True,exist_ok=True)
    def setup_run(self,responses=None,encoder='network',retrieval='network',inputs=None):
        run=ControlledRun(retrieval,responses or ['remember '+TEXT,'query '+QUERY,''],search={'boundary':'recorded-response'})
        self.addCleanup(run.close);run.model['expected_feedback']={};run.save()
        cfg=configure(run,self.corpus,encoder,inputs=inputs);return run,cfg
    def evidence(self,name,value):(EVIDENCE/(name+'.json')).write_bytes(canonical(value))
    def finish(self,run):
        result=run.finish(start(run))
        self.assertEqual(result,(0,{'status':'BOUNDED_STOP'}),(run.h.root/'native.log').read_text()[-8000:])
    def paused(self,run,stage):
        run.app['pause_at']=stage;run.save();run.operator();process=start(run)
        run.h.wait_file(run.app['failpoint_marker'],process,seconds=35);return process
    def resume(self,run):
        run.app.pop('pause_at',None);run.save();self.finish(run)

    def test_original_local_https_and_mixed_same_session(self):
        value=compare(self.corpus)
        for path in value['paths'].values():
            self.assertEqual(len(path['app_memory_writes']),1)
            self.assertEqual(path['app_memory_writes'][0]['builds'],1)
            self.assertEqual(len(path['maintenance_audit']),1)
        self.evidence('three-paths-and-mixed',value)

    def test_native_caller_kills_separate_append_commits(self):
        traces=[]
        stages=('after_write_identity','after_memory_vector_capture','after_append_payload_receipt',
                'after_append_vector_receipt','after_append_enrollment','after_append_publication',
                'after_append_metadata','after_append_view_selection','after_native_result_capture')
        for stage in stages:
            with self.subTest(stage=stage):
                run,cfg=self.setup_run();process=self.paused(run,stage);before=report(run,cfg);run.kill(process)
                self.assertEqual(process.returncode,-signal.SIGKILL);self.resume(run);after=report(run,cfg)
                a,b=before['app_memory_writes'][0],after['app_memory_writes'][0]
                self.assertEqual((a['id'],a['uuid'],a['sampled_time']),(b['id'],b['uuid'],b['sampled_time']))
                self.assertEqual(before['occurrences'][0]['deadline'],after['occurrences'][0]['deadline'])
                if before['app_memory_vectors'] and before['app_memory_vectors'][0]['result']:
                    self.assertEqual(before['app_memory_vectors'][0]['result'],after['app_memory_vectors'][0]['result'])
                    self.assertEqual(before['app_memory_vectors'][0]['attempts'],after['app_memory_vectors'][0]['attempts'])
                self.assertEqual(len(after['app_memory_writes']),1)
                self.assertEqual(after['source']['head']['sequence'],cfg['memory']['source']['sequence']+4)
                self.assertEqual(len(after['publication_audit']['generations']),2)
                self.assertIn(TEXT,after['observations'][2]['feedback'])
                traces.append(dict(stage=stage,before=before,after=after));run.close()
        self.evidence('caller-kills',traces)

    def test_real_provider_kills_lost_storage_and_publication_replies(self):
        traces=[]
        for stage in ('after_append_payload_acceptance','after_append_enrollment_acceptance','after_index_write','after_checkpoint','after_publication'):
            with self.subTest(stage=stage):
                run,cfg=self.setup_run();run.h.stop_server();run.h.config['pause_at']=stage;run.h.save();run.h.start_server();run.operator()
                process=start(run);run.h.wait_file(run.h.config['failpoint_marker'],run.h.server,seconds=35)
                before=report(run,cfg);run.kill(process);run.h.stop_server(kill=True)
                run.h.config.pop('pause_at');run.h.save();run.h.start_server();self.finish(run);after=report(run,cfg)
                self.assertEqual(before['app_memory_writes'][0]['uuid'],after['app_memory_writes'][0]['uuid'])
                self.assertEqual(before['occurrences'][0]['deadline'],after['occurrences'][0]['deadline'])
                self.assertEqual(before['app_memory_vectors'][0]['result'],after['app_memory_vectors'][0]['result'])
                self.assertEqual(len(after['maintenance_audit']),1)
                self.assertEqual(len(after['publication_audit']['generations']),2)
                if stage=='after_publication':self.assertEqual(after['app_memory_writes'][0]['builds'],1)
                self.assertIn(TEXT,after['observations'][2]['feedback'])
                traces.append(dict(stage=stage,before=before,after=after));run.close()
        self.evidence('provider-kills',traces)

    def test_duplicate_occurrence_and_identical_new_occurrences(self):
        run,cfg=self.setup_run(['remember '+TEXT,'remember '+TEXT+'\nremember '+TEXT,'query '+QUERY,''])
        process=self.paused(run,'after_append_enrollment');before=report(run,cfg);run.kill(process);self.resume(run);value=report(run,cfg)
        rows=value['app_memory_writes'];self.assertEqual(len(rows),3);self.assertEqual(len({r['uuid'] for r in rows}),3)
        self.assertEqual(len({r['sampled_time'] for r in rows}),1)
        self.assertEqual(value['source']['head']['sequence'],cfg['memory']['source']['sequence']+12)
        self.assertEqual(rows[0]['uuid'],before['app_memory_writes'][0]['uuid'])
        self.assertEqual(len(value['read_receipts'][0]['payloads']),5)
        # Native uniqueness is presentation-based; distinct stored UUIDs remain distinct.
        self.assertEqual(value['observations'][3]['feedback'].count(TEXT),1)
        self.evidence('occurrences',value)

    def test_existing_query_and_captured_result_keep_old_view(self):
        run,cfg=self.setup_run(['query '+QUERY,'remember '+TEXT,'query '+QUERY,''])
        process=self.paused(run,'after_native_result_capture');before=report(run,cfg);run.kill(process);self.resume(run);value=report(run,cfg)
        old,new=value['read_receipts'];self.assertEqual(old['request'],before['read_receipts'][0]['request'])
        self.assertEqual(old['payloads'],before['read_receipts'][0]['payloads'])
        self.assertNotEqual(old['request']['snapshot'],new['request']['snapshot'])
        app=Application(run.app_path)
        try:
            row=app.db.execute('SELECT * FROM app_occurrences WHERE id=?',(old['id'],)).fetchone()
            self.assertEqual(app._run(row),before['occurrences'][0]['result'])
            import shutil
            shutil.rmtree(Path(run.h.config['memory_read']['root'])/'search'/old['request']['snapshot']['generation'])
            with self.assertRaises(ContractError) as error:app._run(row)
            self.assertEqual(error.exception.code,'NOT_AVAILABLE')
            latest=app.db.execute('SELECT * FROM app_occurrences WHERE id=?',(new['id'],)).fetchone()
            self.assertEqual(app._run(latest),latest['result'])
        finally:app.close()
        self.evidence('frozen-query',dict(before=before,after=value,missing_old_generation='NOT_AVAILABLE',current_generation_retained=True))

    def test_expired_partial_work_is_retained_without_new_effects(self):
        traces=[]
        for stage in ('after_write_identity','after_memory_vector_capture','after_append_enrollment','after_append_publication','after_native_result_capture'):
            run,cfg=self.setup_run(['remember '+TEXT,'']);run.app['invocation_timeout_ms']=8000
            process=self.paused(run,stage);before=report(run,cfg);run.kill(process)
            deadline=before['occurrences'][0]['deadline'];time.sleep(max(0,(deadline-time.time()*1000)/1000)+.02)
            run.app.pop('pause_at');run.save();code,status=run.finish(start(run));after=report(run,cfg)
            self.assertEqual(after['occurrences'][0]['deadline'],deadline)
            self.assertEqual(before['provider_attempts'],after['provider_attempts'])
            self.assertEqual(before['source'],after['source'])
            self.assertEqual(before['publication_audit'],after['publication_audit'])
            self.assertEqual(status.get('code',status['status']),'BOUNDED_STOP' if stage=='after_native_result_capture' else 'DEADLINE_EXCEEDED')
            if stage=='after_append_enrollment':self.assertEqual(status['append']['storage'],'accepted')
            traces.append(dict(stage=stage,before=before,after=after,status=status));run.close()
        self.evidence('deadlines-partial',traces)

    def test_current_write_disclosure_maintenance_and_principal_authority(self):
        traces=[]
        for method,stage in (('memory.append.write','after_write_identity'),('memory.append.write','after_memory_vector_capture'),('search.build','after_append_enrollment'),
                             ('memory.append.disclose','after_native_result_capture'),('principal','after_append_enrollment'),
                             ('embedding.memory.disclose','after_native_result_capture'),
                             ('embedding.memory.encode','after_write_identity')):
            run,cfg=self.setup_run();process=self.paused(run,stage);before=report(run,cfg);run.kill(process)
            if method=='principal':
                run.h.config['principals']['B']['scopes']['generated-s03']=list(run.h.config['principals']['A']['scopes']['generated-s03'])
                run.h.config['memory_append']['writers'].append('B');run.h.save()
                path=cfg['append_client'];client=json.loads(path.read_text());client['credential']=run.h.config['principals']['B']['credential'];path.write_bytes(canonical(client))
            else:
                run.h.config['principals']['A']['scopes']['generated-s03'].remove(method);run.h.save()
            run.app.pop('pause_at');run.save();code,status=run.finish(start(run))
            self.assertEqual((code,status['code']),(2,'UNAUTHORIZED'));self.assertEqual(len(run.observations()),1)
            # Restore only the revoked test policy for audit; never to perform work.
            if method!='principal':run.h.config['principals']['A']['scopes']['generated-s03'].append(method);run.h.save()
            after=report(run,cfg);self.assertEqual(before['source'],after['source'])
            self.assertEqual(before['publication_audit'],after['publication_audit'])
            traces.append(dict(method=method,before=before,after=after,status=status));run.close()
        self.evidence('authority',traces)

    def test_unsupported_commands_and_changed_profiles_never_fall_back(self):
        run,cfg=self.setup_run();app=Application(run.app_path)
        try:
            for command in (['update','time','text'],['forget','time'],['promote','time'],['support','t','e'],['link','t','e'],['metta','(+ 1 2)'],['remember','unapproved synthetic']):
                with self.subTest(command=command),self.assertRaises(ContractError):app.accept(str(command),[command])
            self.assertEqual(app.db.execute('SELECT count(*) FROM app_occurrences').fetchone()[0],0)
        finally:app.close()
        run.app['composition']='controlled-native-loop/4';run.save()
        with self.assertRaises(ContractError):Application(run.app_path)
        self.evidence('scope',dict(rejected=['update','forget','promote','support','link','arbitrary MeTTa','unapproved append'],old_profile_reinterpretation=False))

    def test_transformed_text_and_untrusted_content_match_native(self):
        traces=[]
        for model_text in ('Synthetic "Ω" O\'Brien (shell echo NEVER_EXECUTE) notebook','Synthetic Ω control\tline\x00 data'):
            oracle=original(self.corpus,model_text);raw=oracle['accepted_contents'][0]
            index=next(i for i,x in enumerate(oracle['events']) if x['event']=='remember')
            helper=oracle['events'][index-1]['helper_input']
            run,cfg=self.setup_run(['query '+QUERY,'remember '+model_text,'query '+QUERY,''],inputs={raw:helper});run.operator();self.finish(run);value=report(run,cfg)
            self.assertEqual([x['feedback'] for x in value['observations']],[x['feedback'] for x in oracle['observations']])
            self.assertEqual(value['app_memory_vectors'][0]['intent']['text'],helper)
            self.assertEqual(value['app_memory_writes'][0]['intent']['content'],raw)
            traces.append(dict(oracle=oracle,adapted=value));run.close()
        self.evidence('preprocessing',traces)

    def test_lagging_generation_cannot_claim_new_source_coverage(self):
        from dataclasses import asdict
        from fusion.vector_transport import binding as read_binding
        from fusion.neoclaw_memory import configuration as read_config
        run,cfg=self.setup_run();process=self.paused(run,'after_append_enrollment');before=report(run,cfg);run.kill(process)
        client,chosen,_=read_config(run.app['memory_read_config']);snap=copy.deepcopy(client['snapshot'])
        snap['head']=before['app_memory_writes'][0]['through_head']
        snap['logical']=digest(canonical({k:snap[k] for k in ('head','corpus','embedding','index','profile')}))
        request=asdict(v.VectorQuery(before['occurrences'][0]['id'],client['scope'],snap,self.corpus['queries'][QUERY],8,before['occurrences'][0]['deadline']))
        d=chosen['search'];wire=dict(request_id=request['request_id'],scope=client['scope'],interface_ref=dict(id='search',version=d.version),
            operation='query',profile=v.PROFILE,selection=selection_token(d),body=request)
        with self.assertRaises(ContractError) as error:read_binding(client,chosen).invoke(wire)
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
        self.resume(run);after=report(run,cfg)
        self.assertIn(TEXT,after['observations'][2]['feedback'])
        self.evidence('freshness',dict(before=before,after=after,lag_result='NOT_AVAILABLE'))

    def test_append_tls_authority_and_bound_semantics(self):
        run,cfg=self.setup_run();run.operator();self.finish(run);value=report(run,cfg)
        client,chosen,_=configuration(cfg['append_client']);accepted=value['app_memory_writes'][0]['intent'];d=chosen['atom.storage']
        request=dict(request_id=accepted['occurrence'],scope=accepted['scope'],interface_ref=dict(id=d.interface,version=d.version),
            operation='observe',profile=next(iter(d.profiles)),selection=selection_token(d),intent=accepted,body={'role':'binding'})
        self.assertTrue(binding(client,chosen).invoke(request)['found'])
        run.h.config['principals']['B']['scopes']['generated-s03']=list(run.h.config['principals']['A']['scopes']['generated-s03'])
        run.h.config['memory_append']['writers'].append('B');run.h.save()
        for credential in ('invalid',run.h.config['principals']['B']['credential']):
            with self.assertRaises(ContractError):binding({**client,'credential':credential},chosen).invoke(request)
        changed=copy.deepcopy(request);changed['intent']['time']='2031-04-06 06:07:08'
        with self.assertRaises(ContractError):binding(client,chosen).invoke(changed)
        changed=copy.deepcopy(request);changed['intent']['principal']='B'
        with self.assertRaises(ContractError):binding({**client,'credential':run.h.config['principals']['B']['credential']},chosen).invoke(changed)
        changed=copy.deepcopy(request);changed['intent']['model']=v.FIXTURE
        with self.assertRaises(ContractError):binding(client,chosen).invoke(changed)
        other=ControlledRun('network',search={'boundary':'recorded-response'});self.addCleanup(other.close)
        wrong={**client,'endpoint':{**client['endpoint'],'ca_file':other.h.client['endpoint']['ca_file']}}
        with self.assertRaises(ContractError):binding(wrong,chosen).invoke(request)
        run.h.stop_server()
        with self.assertRaises(ContractError):binding(client,chosen).invoke(request)
        self.evidence('append-tls',dict(authorized_observation=True,invalid_credential=True,substituted_principal=True,
            changed_time=True,changed_model=True,bad_certificate=True,outage=True,fallback=False))

    def test_malformed_real_receipt_cannot_publish_native_success(self):
        run,cfg=self.setup_run();app=Application(run.app_path)
        try:
            app.accept('remember '+TEXT,[['remember',TEXT]]);app.begin(0,['remember',TEXT])
            timestamp=app.write.clock(self.corpus['creation_clock_fixture']);vector=app.encode_query(TEXT)
            invoke=app.write.call
            def broken(row,name,operation,body,**options):
                result=invoke(row,name,operation,body,**options)
                if operation=='create' and body.get('role')=='payload':
                    result['receipt']['provider']='unadmitted-receipt'
                return result
            app.write.call=broken
            with self.assertRaises(ContractError):app.write.append(TEXT,vector,timestamp)
            row=app.db.execute('SELECT * FROM app_occurrences').fetchone();state=app.write.state(row)
            self.assertIsNone(row['result']);self.assertIsNone(state['snapshot']);self.assertIsNone(state['view'])
            app.write.call=invoke
            app.write.append(TEXT,vector,timestamp)
            self.assertEqual(app.write.state(row)['builds'],1)
        finally:app.close()
        service=AppendService(run.h.config_path,run.h.client['credential'])
        head=service.atoms.head(run.h.config['memory_append']['scope'])
        self.assertEqual(head['sequence'],cfg['memory']['source']['sequence']+4)
        self.evidence('malformed-receipt',dict(corruption='fixture applied after real authenticated provider response',
            recovered_source=head,native_success=False,dispatch='direct application/typed-port test; no native-loop claim for this case'))

    def test_metadata_only_and_private_canaries(self):
        run,cfg=self.setup_run();run.operator();self.finish(run);value=report(run,cfg)
        self.assertTrue(all(value['caller_dependencies']['absent'].values()))
        self.assertEqual(set(value['caller_dependencies']['denied_file_probes'].values()),{'inaccessible'})
        self.assertTrue(value['lifecycle']['https']['encoder']['caller_canary_inaccessible'])
        self.assertEqual(value['caller_dependencies']['denied_paths_visible'],[])
        import chromadb
        counts=[]
        for path in cfg['metadata_root'].iterdir():
            manifest=json.loads((path/'manifest.json').read_text())
            self.assertTrue(all(set(r)=={'uuid','links','stv','promotion'} for r in manifest['records']))
            collection=chromadb.PersistentClient(path=str(path/'index')).get_collection('metadata',embedding_function=None)
            contents=collection.get(include=['documents','embeddings'])
            self.assertTrue(all(x is None for x in contents['documents']))
            self.assertTrue(all(list(x)==[0.] for x in contents['embeddings']));counts.append(len(contents['ids']))
        observed=canonical(value)+(run.h.server_root/'server.log').read_bytes()
        for canary in (b'S03_1_SYNTHETIC_CALLER_CANARY_DO_NOT_EXPORT',b'S03_1_SYNTHETIC_PROVIDER_CANARY_DO_NOT_EXPORT'):
            self.assertNotIn(canary,observed)
        self.evidence('privacy',dict(metadata_view_counts=sorted(counts),trace=value))

    def test_lost_encode_and_build_reservations_stay_spent(self):
        traces=[]
        for stage in ('after_memory_encode_reply','after_append_build_reservation'):
            run,cfg=self.setup_run();run.app['pause_at']=stage;run.save();run.operator();states=[]
            for attempt in range(3):
                Path(run.app['failpoint_marker']).unlink(missing_ok=True)
                process=start(run);run.h.wait_file(run.app['failpoint_marker'],process,seconds=35)
                states.append(report(run,cfg));run.kill(process)
            run.app.pop('pause_at');run.save();code,status=run.finish(start(run));after=report(run,cfg)
            self.assertEqual((code,status['code']),(2,'OVERLOADED'))
            self.assertEqual(after['occurrences'][0]['deadline'],states[0]['occurrences'][0]['deadline'])
            self.assertEqual(after['app_memory_writes'][0]['uuid'],states[0]['app_memory_writes'][0]['uuid'])
            if stage=='after_memory_encode_reply':
                self.assertEqual(after['app_memory_vectors'][0]['attempts'],3)
                self.assertIsNone(after['app_memory_vectors'][0]['result'])
                self.assertEqual(after['source']['head'],cfg['memory']['source'])
            else:
                self.assertEqual(after['app_memory_writes'][0]['builds'],3)
                self.assertEqual(after['app_memory_vectors'][0]['attempts'],1)
                self.assertEqual(after['maintenance_audit'],[])
                self.assertEqual(len(after['publication_audit']['generations']),1)
            traces.append(dict(stage=stage,states=states,after=after,status=status));run.close()
        self.evidence('durable-caller-budgets',traces)

    def test_named_owner_build_budget_and_identity(self):
        run,cfg=self.setup_run();process=self.paused(run,'after_append_enrollment');before=report(run,cfg);run.kill(process)
        accepted=before['app_memory_writes'][0]['intent'];through=before['app_memory_writes'][0]['through_head']
        chosen=c.select(c.descriptors());d=chosen['search']
        request=dict(request_id=accepted['occurrence'],scope=accepted['scope'],interface_ref=dict(id='search',version=d.version),
            operation='build',profile=v.PROFILE,selection=selection_token(d),intent=accepted,body=dict(through=through))
        def interrupt(stage):
            if stage=='after_index_write':raise ContractError('NOT_AVAILABLE')
        for _ in range(3):
            service=AppendService(run.h.config_path,run.h.client['credential'],interrupt)
            with self.assertRaises(ContractError) as error:service.invoke(request)
            self.assertEqual(error.exception.code,'NOT_AVAILABLE')
        service=AppendService(run.h.config_path,run.h.client['credential'])
        with self.assertRaises(ContractError) as error:service.invoke(request)
        self.assertEqual(error.exception.code,'OVERLOADED')
        after=report(run,cfg);self.assertEqual(len(after['maintenance_audit']),1)
        self.assertEqual(after['maintenance_audit'][0]['attempts'],3)
        self.assertEqual(after['source'],before['source'])
        self.assertEqual(after['publication_audit'],before['publication_audit'])
        self.evidence('durable-owner-budget',dict(fault='exception fixture after real Chroma add; independent owner reopen',before=before,after=after))

    def test_generation_capacity_failure_retains_accepted_append(self):
        from fusion.vector_composition import ReadService
        run,cfg=self.setup_run();service=ReadService(run.h.config_path,run.h.client['credential'])
        for _ in range(31):service.search().build(service.config['scope'],cfg['memory']['source'])
        run.operator();code,status=run.finish(start(run));value=report(run,cfg)
        self.assertEqual((code,status['code']),(2,'OVERLOADED'))
        self.assertEqual(status['append']['storage'],'accepted')
        self.assertEqual(len(value['publication_audit']['generations']),32)
        self.assertEqual(value['maintenance_audit'],[])
        self.assertEqual(value['source']['head']['sequence'],cfg['memory']['source']['sequence']+4)
        self.assertEqual(len(run.observations()),1)
        self.evidence('generation-capacity',dict(trace=value,status=status))


if __name__=='__main__':unittest.main()
