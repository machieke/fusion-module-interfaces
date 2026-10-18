"""Additional S05 native tie, isolation and expired partial-state gates."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import time
import unittest
import uuid
from fusion.contracts import canonical,ContractError
from fusion.neoclaw_application import Application
from fusion.vector_composition import ReadService
from fusion.vector_enrollment import enroll
from .promotion_oracle import original
from .promotion_run import execute,report
from .test_promotion_loop import NativePromotionLoop,segment,OUT
from .append_oracle import QUERY

# Reuse harness helpers, without inheriting and rerunning its test methods.
class PromotionEdges(unittest.TestCase):
    setUpClass=classmethod(NativePromotionLoop.setUpClass.__func__)
    setup_run=NativePromotionLoop.setup_run
    finish=NativePromotionLoop.finish
    pause=NativePromotionLoop.pause
    resume=NativePromotionLoop.resume
    evidence=NativePromotionLoop.evidence

    def test_native_distinct_query_and_global_tie_orders(self):
        # Select native vector candidates whose lexicographic UUID order differs
        # from their measured distance order. No answer references go to consumer.
        source=json.loads((Path(__file__).resolve().parents[2]/'evidence/s05/native-oracle.json').read_text())
        hits=next(x['rows'] for x in source['events'] if x['kind']=='query')
        rows={x['uuid']:x for x in self.corpus['records']};eligible=[x for x in hits if x[0] in rows]
        pair=next((a,b) for i,a in enumerate(eligible) for b in eligible[i+1:] if a[0]>b[0] and a[-1]<b[-1])
        a,b=[rows[x[0]] for x in pair]
        commands=['promote '+a['time'],'promote '+b['time'],'query '+QUERY,'']
        oracle=original(self.corpus,responses=commands);values=[]
        for provider in ('sqlite','file-fixture'):
            value=execute(self.corpus,provider,responses=commands)
            self.assertEqual([r['feedback'] for r in value['observations']],[r['feedback'] for r in oracle['observations']])
            self.assertEqual([segment(r['context']) for r in value['observations']],[segment(r['context']) for r in oracle['observations']])
            self.assertLess(value['observations'][-1]['feedback'].index(a['time']),value['observations'][-1]['feedback'].index(b['time']))
            self.assertLess(segment(value['observations'][-1]['context']).index(b['time']),segment(value['observations'][-1]['context']).index(a['time']))
            values.append(dict(provider=provider,trace=value))
        self.evidence('native-tie-orders',dict(oracle=oracle,adapted=values,pair=[a['uuid'],b['uuid']]))
    def test_real_other_scope_and_no_legacy_promotion_file(self):
        run,cfg=self.setup_run();original=copy.deepcopy(run.h.config)
        foreign='generated-s05-other-scope';memory=run.h.config['memory_read'];selected_scope=memory['scope'];memory['scope']=foreign
        run.h.config['principals']['A']['scopes'][foreign]=list(run.h.config['principals']['A']['scopes'][selected_scope]);run.h.save()
        svc=ReadService(run.h.config_path,run.h.client['credential']);r=self.corpus['records'][0];other=str(uuid.uuid4())
        # Same real vector, different explicitly generated scope; same AtomStorage
        # owner proves the caller cannot obtain it by scanning another owner's DB.
        ref=enroll(svc.atoms,foreign,memory['corpus'],memory['embedding'],'foreign-generated',dict(scope=foreign,corpus=memory['corpus'],
            uuid=other,time=r['time'],content=r['content']),r['vector'])
        head=svc.atoms.head(foreign);run.h.config=original;run.h.save()
        native=json.loads(Path(run.app['memory_native_config']).read_text());Path(native['promotions']).unlink()
        run.operator();self.finish(run);value=report(run,cfg)
        self.assertTrue(all(other not in r['binding']['request']['targets'] for r in value['app_priority_contexts']))
        app=Application(run.app_path)
        try:
            with self.assertRaises(ContractError):app.priority.atoms.get(ref)
        finally:app.close()
        self.evidence('real-scope-isolation',dict(other_scope=foreign,other_head=head,other_uuid=other,legacy_promotion_file_deleted=True,trace=value))
    def test_expired_native_commit_observed_without_visibility_or_retiming(self):
        target=self.corpus['records'][5]['time'];run,cfg=self.setup_run(responses=['promote '+target,''])
        p=self.pause(run,'after_priority_commit')
        with sqlite3.connect(run.h.client['database']) as db:
            original=db.execute('SELECT id,deadline FROM app_occurrences').fetchone()
            binding=json.loads(db.execute('SELECT binding FROM app_priority').fetchone()[0])
        run.kill(p)
        while time.time()*1000<=original[1]:time.sleep(.1)
        run.app.pop('pause_at');run.save()
        from .embedding_run import start
        resumed=start(run);resumed.wait(timeout=90);result=run.finish(resumed)
        self.assertEqual(result,(2,{'status':'PENDING_OR_FAILED','code':'DEADLINE_EXCEEDED'}))
        app=Application(run.app_path)
        try:
            row=app.db.execute('SELECT * FROM app_priority').fetchone();occ=app.db.execute('SELECT * FROM app_occurrences').fetchone()
            self.assertEqual((occ['id'],occ['deadline']),original);self.assertIsNone(occ['result']);self.assertFalse(row['visible'])
            receipt=app.priority.owner.observe(binding);self.assertEqual(receipt['revision'],1);self.assertEqual(receipt['time'],binding['time'])
            self.assertEqual(json.loads(row['binding']),binding)
            self.evidence('expired-native-partial',dict(original=list(original),binding=binding,receipt=receipt,result=result,visible=False,native_result=None))
        finally:app.close()

if __name__=='__main__':unittest.main()
