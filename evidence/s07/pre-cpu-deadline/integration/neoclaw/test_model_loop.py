"""Recorded MODEL fixture, real native loop/NAL/DeTTa/IRC/HTTPS. Never a live-model gate."""
import json
from pathlib import Path
import signal
import time
import unittest
from fusion.contracts import canonical
from .controlled_run import ControlledRun
from .model_composition import configure,runtime_lock,INPUTS,OUTPUT
from .embedding_run import start
from .channel_composition import ROOT

OUT=ROOT/'artifacts/s07/model-loop-fixture';OUT.mkdir(parents=True,exist_ok=True)


class ModelLoop(unittest.TestCase):
    def run_case(self,stage=None,recorded=None,rejection=None):
        corpus=json.loads((ROOT/'artifacts/s07/corpus.json').read_text())
        run=ControlledRun('local',['',''],search={'boundary':'recorded-response'});self.addCleanup(run.close)
        cfg=configure(run,corpus,'network',runtime_lock=runtime_lock(OUT));ch=cfg['channel'];self.addCleanup(ch.close)
        root=cfg['completion_root'];ready=root/'ready.json';port=json.loads(ready.read_text())['port']
        # Explicit substitution at the model provider only, BEFORE any admission.
        host=run.processes[-1];run.kill(host);time.sleep(.1);ready.unlink()
        if recorded is not None:
            policy=json.loads(cfg['completion_policy'].read_text());policy['test_recorded_model_response']=recorded
            cfg['completion_policy'].write_bytes(canonical(policy))
        host=run.spawn('integration.neoclaw.model_fixture_host',[cfg['completion_policy'],'--port',port,'--ready',ready],'recorded-model-host')
        run.h.wait_file(ready,host)
        if stage:run.app['pause_at']=stage;run.save()
        run.operator();ch.start_bridge();ch.start_peer();p=start(run)
        for text in INPUTS:ch.send(text)
        before=None
        try:
            if stage:
                run.h.wait_file(run.app['failpoint_marker'],p,seconds=45)
                before=ch.rows(run.h.client['database'],'app_model_calls')
                run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL)
                run.app.pop('pause_at');run.save();p=start(run)
            p.wait(timeout=45)
            if rejection:
                self.assertEqual(run.finish(p),(2,{'status':'PENDING_OR_FAILED','code':rejection}))
                self.assertEqual(run.rows('app_occurrences'),[])
                rows=ch.rows(run.h.client['database'],'app_model_calls')
                self.assertIsNotNone(rows[0]['result']);self.assertIsNotNone(rows[0]['normalized']);self.assertIsNotNone(rows[0]['parse_text'])
                self.assertTrue(rows[0]['admission'].startswith('rejected:'))
                self.assertFalse(any(' :'+OUTPUT in r.get('received','') for r in ch.traffic()))
                (OUT/(rejection+'.json')).write_bytes(canonical(dict(classification='RECORDED_MODEL_RESPONSE_FIXTURE',
                    live_generation=False,model_calls=rows,occurrences=[],status=rejection)))
                return
            self.assertEqual(run.finish(p),(0,{'status':'BOUNDED_STOP'}))
            until=time.monotonic()+5
            while time.monotonic()<until and not any(' :'+OUTPUT in r.get('received','') for r in ch.traffic()):time.sleep(.05)
            self.assertTrue(any(' :'+OUTPUT in r.get('received','') for r in ch.traffic()))
            rows=ch.rows(run.h.client['database'],'app_model_calls');provider=ch.rows(root/'model.sqlite','model_calls')
            self.assertEqual(len(rows),2);self.assertEqual(len(provider),2);self.assertEqual(sum(r['reserved'] for r in provider),2)
            if before:
                for old,new in zip(before,rows):
                    for key in ('id','intent','context_view','result'):self.assertEqual(old[key],new[key])
            self.assertTrue(all(r['admission']=='authorized' for r in rows))
            report=dict(classification='RECORDED_MODEL_RESPONSE_FIXTURE',live_generation=False,stage=stage,
                model_calls=rows,provider_calls=provider,turns=run.rows('app_turns'),traffic=ch.traffic(),
                real=['native Omega parser/loop','original NAL Truth_Deduction','DeTTa','ngIRCd','socket peer','same-host HTTPS'])
            (OUT/((stage or 'normal')+'.json')).write_bytes(canonical(report))
        except BaseException:
            (OUT/((stage or 'normal')+'-failure.log')).write_text((run.h.root/'native.log').read_text())
            path=Path(run.app['status_file'])
            if path.exists():(OUT/((stage or 'normal')+'-status.json')).write_bytes(path.read_bytes())
            raise
        finally:ch.close();run.close()
    def test_native_next_context_and_approved_send_with_recorded_model(self):self.run_case()
    def test_native_kill_after_application_capture_with_recorded_model(self):self.run_case('after_model_application_capture')
    def test_native_whole_batch_refuses_before_first_valid_command(self):
        from .model_composition import EXPRESSION
        self.run_case(recorded='metta '+EXPRESSION+'\nshell echo synthetic',rejection='UNSUPPORTED_OPERATION')
    def test_native_malformed_parser_result_is_retained_without_regeneration(self):
        from .model_composition import EXPRESSION
        self.run_case(recorded='((metta "'+EXPRESSION+'"))',rejection='INVALID_ARGUMENT')
