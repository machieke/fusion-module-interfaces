"""Actual killed processes; owner journals survive, no cross-owner transaction claim."""
from dataclasses import asdict
import json
from pathlib import Path
import signal,subprocess,sys,time,unittest
from fusion.contracts import canonical
from fusion.ports import Mutation
from tests.m3_1_support import ClosureHarness,SCOPE

class ClosureRecovery(unittest.TestCase):
    def worker(self,h,stage,operation,request=None,episode=None,*,resume=None,now_ms=None):
        marker=h.root/'marker';output=h.root/'result';calls=h.root/'calls';path=h.root/'worker.json'
        marker.unlink(missing_ok=True)
        cfg=dict(private_config=str(h.path),credential=h.credential,scope=SCOPE,stage=stage,operation=operation,
                 marker=str(marker),result=str(output),invocations=str(calls),request=asdict(request) if request else None,episode=episode)
        path.write_bytes(canonical(cfg))
        with open(h.root/'worker.log','w') as log:
            process=subprocess.Popen([sys.executable,'-m','integration.pln.m3_1_worker',str(path)],stdout=log,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+90
                while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(marker.exists(),(h.root/'worker.log').read_text())
                process.kill();process.wait(timeout=10);self.assertEqual(process.returncode,-signal.SIGKILL)
            finally:
                if process.poll() is None:process.kill();process.wait()
        cfg.update(stage=None,operation=resume or operation,now_ms=now_ms);path.write_bytes(canonical(cfg))
        completed=subprocess.run([sys.executable,'-m','integration.pln.m3_1_worker',str(path)],capture_output=True,text=True,timeout=90)
        self.assertEqual(completed.returncode,0,completed.stderr)
        return json.loads(output.read_text()),len(calls.read_text().splitlines()) if calls.exists() else 0

    def test_evidence_separate_commit_kills(self):
        for provider in ('sqlite','atomic-file-fixture'):
            for stage in ('after_evidence_decision_commit','after_relay_decision_commit','after_evidence_ack_commit','after_relay_ack_commit'):
                with self.subTest(provider=provider,stage=stage):
                    h=ClosureHarness(real=True,provider=provider)
                    try:
                        claim=h.atoms.create(Mutation(SCOPE,'p'),'application/fusion-claim',canonical({'predicate':'pln:proposition','arguments':['p'],'positive':True}))['ref']
                        episode=h.episode();h.append(episode,h.event(claim))
                        _,calls=self.worker(h,stage,'drain',episode=episode)
                        self.assertEqual(calls,0);self.assertEqual(h.episodes.pendingEvidence(episode,16),())
                        self.assertEqual(len(h.modules.relay.decisions(episode)),1)
                        self.assertEqual(len(h.beliefs.readBelief(claim,'generated',None)['observations']),1)
                    finally:h.close()

    def test_applied_kill_deadline_expired_before_restart(self):
        for provider in ('sqlite','atomic-file-fixture'):
            with self.subTest(provider=provider):
                h=ClosureHarness(real=True,provider=provider)
                try:
                    entry,_,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),candidates=1,deadline=int(time.time()*1000)+120000)
                    execution,calls=self.worker(h,'after_feedback_commit','step',request,now_ms=request.budget.deadline_ms+1)
                    self.assertEqual(calls,1);self.assertEqual(execution['reason'],'deadline');self.assertEqual(execution['counts']['reserved'],1)
                    # The resumed step has terminated, but the original receipt remains recoverable.
                    from unittest.mock import patch
                    with patch('time.time',return_value=(request.budget.deadline_ms+1)/1000):
                        result=h.controller.reconcile(Mutation(SCOPE,'recover'),request,1)
                    self.assertEqual(result['closure']['counts']['applied'],1);self.assertEqual(result['execution'],execution)
                    self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'11')
                finally:h.close()

    def test_retirement_and_controller_progress_kills(self):
        for provider in ('sqlite','atomic-file-fixture'):
            for stage in ('after_feedback_retirement_commit','after_closure_provider_response','after_closure_progress_commit'):
                with self.subTest(provider=provider,stage=stage):
                    h=ClosureHarness(real=True,provider=provider)
                    try:
                        entry,_,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),candidates=1,deadline=int(time.time()*1000)+120000)
                        def hook(where):
                            if where=='after_derived_commit':h.attention.advance(Mutation(SCOPE,'advance'),'generated',0,1)
                        h.hook=hook;h.reopen();execution=h.controller.step(request)
                        self.assertEqual(execution['reason'],'feedback-unavailable')
                        result,calls=self.worker(h,stage,'reconcile',request)
                        self.assertEqual(calls,0);self.assertEqual(result['closure']['counts']['retired'],1)
                        self.assertEqual(result['execution'],execution)
                        self.assertEqual(h.controller.reconcile(Mutation(SCOPE,'recover'),request,1),result)
                        self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'9')
                    finally:h.close()

if __name__=='__main__':unittest.main()
