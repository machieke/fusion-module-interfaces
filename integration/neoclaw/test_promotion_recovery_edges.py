"""Actual native unavailable-owner and context work-budget recovery gates."""
import json
from pathlib import Path
import signal
import sqlite3
import time
import unittest
from fusion.contracts import canonical
from .test_promotion_loop import NativePromotionLoop
from .embedding_run import start

class ContextRecovery(unittest.TestCase):
    setUpClass=classmethod(NativePromotionLoop.setUpClass.__func__)
    setup_run=NativePromotionLoop.setup_run
    finish=NativePromotionLoop.finish
    pause=NativePromotionLoop.pause
    resume=NativePromotionLoop.resume
    evidence=NativePromotionLoop.evidence

    def test_unavailable_owner_stops_native_context_then_recovers_exact_capture(self):
        target=self.corpus['records'][5]['time'];run,cfg=self.setup_run(['promote '+target,''])
        process=self.pause(run,'after_global_capture',2);run.kill(process)
        with sqlite3.connect(run.h.client['database']) as db:
            before=db.execute('SELECT binding,rendered,deadline FROM app_priority_contexts WHERE slot=2').fetchone()
        policy=cfg['attention_policy'];hidden=policy.with_suffix('.unavailable');policy.rename(hidden)
        run.app.pop('pause_at');run.save();process=start(run);process.wait(timeout=90)
        result=run.finish(process);self.assertEqual(result,(2,{'status':'PENDING_OR_FAILED','code':'NOT_AVAILABLE'}))
        self.assertEqual(len(run.observations()),1) # missing owner did not send empty/cached context
        hidden.rename(policy);self.finish(run)
        with sqlite3.connect(run.h.client['database']) as db:
            after=db.execute('SELECT binding,rendered,deadline FROM app_priority_contexts WHERE slot=2').fetchone()
        self.assertEqual(before,after);self.assertIn(self.corpus['records'][5]['content'],run.observations()[1]['context'])
        self.evidence('native-owner-outage',dict(result=result,binding=json.loads(before[0]),captured=before[1],deadline=before[2],fallback=False,observations=run.observations()))
    def test_native_context_restarts_keep_spent_budget_and_original_deadline(self):
        run,cfg=self.setup_run(['']);snapshots=[]
        process=self.pause(run,'after_global_selection')
        result=None
        for attempt in range(3):
            with sqlite3.connect(run.h.client['database']) as db:
                row=db.execute('SELECT slot,view,deadline,calls,binding,result FROM app_priority_contexts').fetchone();snapshots.append(list(row))
            run.kill(process);self.assertEqual(process.returncode,-signal.SIGKILL)
            if attempt<2:
                Path(run.app['failpoint_marker']).unlink();process=start(run)
                until=time.monotonic()+60
                while not Path(run.app['failpoint_marker']).exists() and process.poll() is None and time.monotonic()<until:time.sleep(.05)
                if process.poll() is not None:
                    result=run.finish(process);break
                self.assertTrue(Path(run.app['failpoint_marker']).exists())
        if result is None:
            run.app.pop('pause_at');run.save();process=start(run);process.wait(timeout=90);result=run.finish(process)
        self.assertEqual(result[0],2);self.assertEqual(result[1]['status'],'PENDING_OR_FAILED')
        self.assertIn(result[1]['code'],('OVERLOADED','DEADLINE_EXCEEDED'))
        if result[1]['code']=='DEADLINE_EXCEEDED':self.assertGreaterEqual(time.time()*1000,snapshots[0][2])
        else:self.assertEqual(len(snapshots),3)
        self.assertEqual([r[3] for r in snapshots],list(range(1,len(snapshots)+1)))
        self.assertEqual(len({tuple(r[:3]) for r in snapshots}),1);self.assertEqual(len({r[4] for r in snapshots}),1)
        with sqlite3.connect(run.h.client['database']) as db:
            final=db.execute('SELECT slot,view,deadline,calls,binding,result FROM app_priority_contexts').fetchone()
            self.assertEqual(list(final),snapshots[-1]);self.assertEqual(db.execute('SELECT count(*) FROM app_priority_contexts').fetchone()[0],1)
        self.assertEqual(run.observations(),[])
        self.evidence('native-context-budget',dict(snapshots=snapshots,result=result,refunded=False,new_contexts_created=1))

if __name__=='__main__':unittest.main()
