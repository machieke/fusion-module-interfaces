"""SIGKILL boundaries with independent owners and real native formula invocations."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import unittest
from fusion.contracts import canonical
from fusion.ports import Stimulus, Mutation
from tests.m3_support import CognitionHarness,SCOPE

class CrashRecovery(unittest.TestCase):
    def worker(self,h,request,stage,operation='step'):
        path=h.root/'worker.json';marker=h.root/'marker';output=h.root/'result';calls=h.root/'invocations'
        config={'private_config':str(h.path),'credential':h.credential,'scope':SCOPE,'stage':stage,
            'marker':str(marker),'result':str(output),'invocations':str(calls),'operation':operation,'request':asdict(request)}
        path.write_bytes(canonical(config))
        with open(h.root/'worker.log','w') as log:
            process=subprocess.Popen([sys.executable,'-m','integration.pln.m3_worker',str(path)],stdout=log,stderr=subprocess.STDOUT)
            try:
                deadline=time.monotonic()+60
                while not marker.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
                self.assertTrue(marker.exists(),(h.root/'worker.log').read_text())
                process.kill();process.wait(timeout=10);self.assertEqual(process.returncode,-signal.SIGKILL)
            finally:
                if process.poll() is None:process.kill();process.wait()
        config['stage']=None;path.write_bytes(canonical(config))
        recovered=subprocess.run([sys.executable,'-m','integration.pln.m3_worker',str(path)],capture_output=True,text=True,timeout=60)
        self.assertEqual(recovered.returncode,0,recovered.stderr)
        return json.loads(output.read_text()),len(calls.read_text().splitlines()) if calls.exists() else 0

    def test_attention_commit_before_response_both_providers(self):
        for provider in ('sqlite','atomic-file-fixture'):
            with self.subTest(provider=provider):
                h=CognitionHarness(real=True,provider=provider)
                try:
                    entry,_,_=h.generated();request=Stimulus(Mutation(SCOPE,'kill-stimulus'),'generated',entry['task'],'10','cause',0,h.attention.policy,0,'ingress')
                    result,calls=self.worker(h,request,'after_attention_commit','stimulus');self.assertEqual(result['applied'],'10');self.assertEqual(calls,0)
                    self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'10')
                finally:h.close()

    def test_reservation_and_kernel_return_spend_crash_slots(self):
        for stage in ('after_attempt_reservation','after_kernel_return'):
            for budget in (1,2):
                with self.subTest(stage=stage,budget=budget):
                    h=CognitionHarness(real=True)
                    try:
                        entry,roles,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),attempts=budget,candidates=1)
                        result,calls=self.worker(h,request,stage)
                        self.assertEqual(result['counts']['reserved'],budget);self.assertLessEqual(calls,budget)
                        if budget==1:
                            self.assertEqual(result['reason'],'rule-budget');self.assertIsNone(h.beliefs.readBelief(roles['pr'],'generated',None)['truth'])
                        else:
                            self.assertEqual(result['counts']['unique_admissions'],1);self.assertEqual(result['counts']['feedback_applied'],1)
                        self.assertEqual(calls,(0 if stage=='after_attempt_reservation' else 1)+(1 if budget==2 else 0))
                    finally:h.close()

    def test_belief_commit_and_feedback_commit_replay_without_new_native_work(self):
        for stage in ('after_derived_commit','after_feedback_commit'):
            for provider in ('sqlite','atomic-file-fixture'):
                with self.subTest(stage=stage,provider=provider):
                    h=CognitionHarness(real=True,provider=provider)
                    try:
                        entry,roles,_=h.generated();h.stimulate(entry);request=h.request(h.workset([entry]),candidates=1)
                        result,calls=self.worker(h,request,stage)
                        self.assertEqual(calls,1);self.assertEqual(result['counts']['reserved'],1)
                        self.assertEqual(result['counts']['unique_admissions'],1);self.assertEqual(result['counts']['feedback_applied'],1)
                        self.assertEqual(h.attention.readAttention(entry['task'],'generated')['value']['sti'],'11')
                        self.assertEqual(len(h.beliefs.readBelief(roles['pr'],'generated',None)['supports']),1)
                    finally:h.close()

if __name__=='__main__':unittest.main()
