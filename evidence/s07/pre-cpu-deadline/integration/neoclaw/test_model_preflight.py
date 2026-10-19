"""Real native /9 prompt binding only. SIGSTOP/SIGKILL occurs before generation."""
import json
import os
from pathlib import Path
import signal
import unittest
from fusion.contracts import canonical
from .controlled_run import ControlledRun
from .model_composition import configure,runtime_lock,INPUTS
from .embedding_run import start
from .channel_composition import ROOT

OUT=ROOT/'artifacts/s07/preflight';OUT.mkdir(parents=True,exist_ok=True)


class ModelPreflight(unittest.TestCase):
    def test_real_native_local_and_https_prompt_bound_before_generation(self):
        corpus=json.loads((ROOT/'artifacts/s07/corpus.json').read_text());reports=[]
        for placement in ('local','network'):
            with self.subTest(placement=placement):
                run=ControlledRun('local',['',''],search={'boundary':'recorded-response'});self.addCleanup(run.close)
                cfg=configure(run,corpus,placement,runtime_lock=runtime_lock(OUT));ch=cfg['channel'];self.addCleanup(ch.close)
                run.app['pause_at']='after_model_prompt_bind';run.save()
                ch.start_bridge();ch.start_peer();p=start(run);ch.send(INPUTS[0])
                try:
                    run.h.wait_file(run.app['failpoint_marker'],p,seconds=45)
                    rows=ch.rows(run.h.client['database'],'app_model_calls');self.assertEqual(len(rows),1)
                    self.assertEqual(rows[0]['calls'],0);self.assertIsNone(rows[0]['result'])
                    self.assertFalse((cfg['completion_root']/'model.sqlite').exists())
                    boundary=json.loads((Path(run.app['workdir'])/'model-boundary.json').read_text())
                    self.assertEqual(boundary['raw_ollama_connect_refused'],placement=='network')
                    self.assertFalse(boundary['scripted_model_imported'])
                    report=dict(placement=placement,real=['native loop','IRC','DeTTa','Chroma metadata','Attention context read'],
                        model_generation='UNRUN: stopped before provider RPC',prompt=json.loads(rows[0]['intent']),boundary=boundary,
                        startup=json.loads((Path(run.app['workdir'])/'startup.json').read_text()))
                    run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL)
                    # Replay must keep its first TIME/prompt/deadline. Stop again
                    # before the first observe RPC; this still makes no model call.
                    run.app['pause_at']='after_model_rpc_reservation';run.save()
                    Path(run.app['failpoint_marker']).unlink();p=start(run)
                    run.h.wait_file(run.app['failpoint_marker'],p,seconds=30)
                    replay=ch.rows(run.h.client['database'],'app_model_calls')
                    for key in ('id','intent','context_view'):self.assertEqual(rows[0][key],replay[0][key])
                    self.assertEqual(replay[0]['calls'],1);self.assertIsNone(replay[0]['result'])
                    self.assertFalse((cfg['completion_root']/'model.sqlite').exists())
                    run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL)
                    report['pre_submission_recovery']=dict(signal='SIGKILL',exact_prompt_and_deadline_retained=True,rpc_reservations=1,provider_calls=0)
                    reports.append(report)
                except BaseException:
                    (OUT/(placement+'-failure.log')).write_text((run.h.root/'native.log').read_text())
                    path=Path(run.app['status_file'])
                    if path.exists():(OUT/(placement+'-status.json')).write_bytes(path.read_bytes())
                    raise
                finally:ch.close();run.close()
        (OUT/'native-prompt-bind.json').write_bytes(canonical(reports))
