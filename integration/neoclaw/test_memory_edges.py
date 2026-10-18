"""Additional real projection boundaries; vectors remain mathematical fixtures."""
import copy,json,math,os,sqlite3,time,unittest,uuid
from pathlib import Path
from fusion import vector_contracts as c
from fusion.contracts import canonical,digest,ContractError
from fusion.vector_enrollment import enroll
from . import test_memory as helpers
from .memory_corpus import generated

# Reuse setup helpers without inheriting/recounting the parent test methods.
class MemoryEdges(unittest.TestCase):
    run_fixture=helpers.MemoryIntegration.run_fixture
    service=helpers.MemoryIntegration.service
    request=helpers.MemoryIntegration.request
    evidence=helpers.MemoryIntegration.evidence

    def test_credential_substitution_cannot_release_captured_result(self):
        run=self.run_fixture('network');run.app['pause_at']='after_native_result_capture';run.save();run.operator()
        process=run.start();run.h.wait_file(run.app['failpoint_marker'],process);run.kill(process)
        run.h.config['principals']['A']['scopes']['generated-s03']=[];run.h.save()
        path=Path(run.app['memory_read_config']);cfg=json.loads(path.read_text())
        # Worker retains genuine permission, but cannot become this occurrence's
        # accepted application principal merely by replacing the credential.
        cfg['credential']=run.h.config['principals']['worker']['credential'];path.write_bytes(canonical(cfg))
        run.app.pop('pause_at');run.save();code,status=run.finish(run.start())
        self.assertEqual((code,status['code']),(2,'UNAUTHORIZED'));self.assertEqual(len(run.observations()),1)
        cfg['principal']='worker';path.write_bytes(canonical(cfg))
        code,status=run.finish(run.start());self.assertEqual((code,status['code']),(2,'CONFLICT'))
        self.evidence('principal-binding',dict(credential_change='UNAUTHORIZED',principal_change='CONFLICT',no_next_context=True))

    def test_native_metadata_and_embedding_binding_refusal(self):
        results=[]
        for field,value in (('metadata_seal','wrong'),('embedding_boundary','real')):
            run=self.run_fixture();path=Path(run.app['memory_native_config']);cfg=json.loads(path.read_text());cfg[field]=value;path.write_bytes(canonical(cfg))
            code,status=run.finish(run.start());self.assertNotEqual(code,0);self.assertEqual(len(run.observations()),0)
            results.append(dict(field=field,exit_code=code,model_calls=0))
        self.evidence('native-binding-refusal',results)

    def test_new_enrollment_freshness_and_native_metadata_immutability(self):
        run=self.run_fixture('network');svc=self.service(run);q=self.request(run)
        before=Path(run.h.caller_root/'promotions.db').read_bytes()
        metadata=Path(run.h.caller_root/'metadata.json').read_bytes()
        head=svc.atoms.head(q['scope']);value=dict(scope=q['scope'],corpus=svc.config['corpus'],uuid=str(uuid.uuid4()),time='2030-03-01 00:00:00',content='New generated enrollment after the admitted source head')
        enroll(svc.atoms,q['scope'],svc.config['corpus'],c.FIXTURE,'new-enrollment',value,[1.]+[0.]*1023)
        latest=svc.atoms.head(q['scope']);self.assertEqual(latest['sequence'],head['sequence']+3)
        new=copy.deepcopy(q);new['snapshot']['head']=latest
        new['snapshot']['logical']=digest(canonical({k:new['snapshot'][k] for k in ('head','corpus','embedding','index','profile')}))
        with self.assertRaises(ContractError):svc.search().query(new)
        run.operator();self.assertEqual(run.finish(run.start()),(0,{'status':'BOUNDED_STOP'}))
        self.assertNotIn(value['content'],run.observations()[1]['feedback'])
        self.assertEqual(Path(run.h.caller_root/'promotions.db').read_bytes(),before)
        self.assertEqual(Path(run.h.caller_root/'metadata.json').read_bytes(),metadata)
        self.assertEqual(svc.atoms.head(q['scope']),latest)
        import chromadb
        local=chromadb.PersistentClient(path=str(run.h.caller_root/'native/chroma_db')).get_collection('memories',embedding_function=None).get(include=['metadatas','documents'])
        rows=json.loads(metadata)['records']
        self.assertEqual(dict(zip(local['ids'],local['metadatas'])),{r['uuid']:dict(linkedEpisodes=r['links'],strength=r['stv'][0],confidence=r['stv'][1]) for r in rows})
        self.assertTrue(all(x is None for x in local['documents']))
        snap=svc.search().build(q['scope'],latest);hits=svc.search().query({**q,'snapshot':snap})['hits']
        self.assertIn(value['uuid'],[h['uuid'] for h in hits])
        self.evidence('fresh-enrollment-immutability',dict(admitted_head=head,unindexed_head=latest,rebuilt_snapshot=snap,
            promotion_file_byte_identical=True,linked_labels_and_stvs_unchanged=True,local_documents_absent=True,source_unchanged_by_reads_and_rebuild=True))

    def test_near_ties_and_ties_are_observed_not_reordered(self):
        run=self.run_fixture();svc=self.service(run);q=self.request(run)
        first=svc.search().query(q);traces=[]
        # Additional source enrollments have nearly coincident float32 vectors.
        for i,angle in enumerate((.2,.20000001)):
            value=dict(scope=q['scope'],corpus=svc.config['corpus'],uuid=str(uuid.uuid4()),time='2030-03-01 00:00:00',content='Near tie '+str(i))
            enroll(svc.atoms,q['scope'],svc.config['corpus'],c.FIXTURE,'near-tie-'+str(i),value,[math.cos(angle),math.sin(angle)]+[0.]*1022)
        head=svc.atoms.head(q['scope'])
        for _ in range(2):
            snap=svc.search().build(q['scope'],head)
            for _ in range(2):traces.append(svc.search().query({**q,'snapshot':snap}))
        for result in traces:
            self.assertEqual(len(result['hits']),8)
            self.assertEqual([h['distance'] for h in result['hits']],sorted(h['distance'] for h in result['hits']))
        # No deterministic tie-breaker is inserted by this provider. Record native
        # output across repeated queries and independent physical generations.
        self.evidence('ties-near-ties',dict(original=first,queries=traces,
            repeat_order_equal=traces[0]['hits']==traces[1]['hits'],rebuild_order_equal=traces[0]['hits']==traces[2]['hits'],
            guarantee='distance order only; no stable tie order or ANN recall claim'))

if __name__=='__main__':unittest.main()
