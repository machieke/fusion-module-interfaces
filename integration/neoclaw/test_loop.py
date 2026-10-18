"""Actual native loop/skill, original NAL worker, DeTTa, authenticated HTTPS.

External model/channel/memory fixtures and fault injection are explicitly labelled.
The model observes the loop's next context; it never injects an operation result.
"""
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import time
import unittest

from fusion import neoclaw_contracts as c
from fusion.contracts import canonical
from fusion.ports import Mutation
from .controlled_run import ControlledRun
from tests.neoclaw_support import COMMAND, GOLDEN, RUNTIME, DETTA

CHANGED='metta (Truth_Deduction (stv 0.6 0.9) (stv 0.7 0.8))'


def evidence(name, data):
    output=os.environ.get('S01_1_EVIDENCE')
    if output:
        path=Path(output);path.mkdir(parents=True,exist_ok=True)
        (path/(name+'.json')).write_bytes(canonical(data))


class NativeLoop(unittest.TestCase):
    def fresh(self, *args, **kwargs):
        self.assertTrue(RUNTIME.is_file(),'BLOCKED: S01 runtime')
        self.assertTrue(DETTA.is_file(),'BLOCKED: real DeTTa')
        run=ControlledRun(*args,**kwargs);self.addCleanup(run.close)
        return run

    def success(self, run, process=None):
        result=run.finish(process or run.start())
        self.assertEqual(result,(0,dict(status='BOUNDED_STOP')), (result,(run.h.root/'native.log').read_text()[-1800:]))

    def failed(self, run, code, process=None):
        result=run.finish(process or run.start())
        self.assertEqual(result,(2,dict(status='PENDING_OR_FAILED',code=code)),result)
        self.assertTrue(all(GOLDEN not in x['feedback'] for x in run.observations()))

    def pause(self, run, stage):
        marker=Path(run.app['failpoint_marker']);marker.unlink(missing_ok=True)
        run.app['pause_at']=stage;run.save()
        process=run.start();run.h.wait_file(marker,process)
        paused=json.loads(marker.read_text())
        self.assertEqual(paused['stage'],stage)
        return process,paused

    def killed(self, run, process, marker):
        os.kill(marker['pid'],signal.SIGKILL)
        code=process.wait(timeout=5)
        self.assertIn(code,(-9,137))
        run.app.pop('pause_at');run.save()
        return code

    def wait(self, predicate):
        until=time.monotonic()+12
        while time.monotonic()<until:
            if predicate():return
            time.sleep(.02)
        self.fail('observation timeout')

    def test_multi_turn_original_oracle_local_and_https_same_caller(self):
        reports=[]
        for placement in ('local','network'):
            with self.subTest(placement=placement):
                run=self.fresh(placement,[COMMAND,CHANGED,COMMAND,COMMAND+'\n'+COMMAND,'metta (+ 1 2)',''])
                original=run.h.native(COMMAND,original=True)['values']
                changed=run.h.native(CHANGED,original=True)['values']
                self.assertEqual(original,[GOLDEN]);self.assertEqual(len(changed),1)
                run.model['expected_feedback']={'1':[[original[0],1]],'2':[[changed[0],1]],'3':[[original[0],1]],
                                               '4':[[original[0],2]],'5':[[' 3)',1]]};run.save()
                secret='PRIVATE-CANARY-'+os.urandom(12).hex()
                (run.h.server_root/'private-canary').write_text(secret)
                config=run.h.client_path.read_bytes();run.operator();self.success(run)
                self.assertEqual(config,run.h.client_path.read_bytes())
                rows=run.rows('app_occurrences');selected=[x for x in rows if x['premises']]
                self.assertEqual(len(selected),5);self.assertEqual(len({x['id'] for x in selected}),5)
                self.assertEqual([x['result'] for x in selected],[GOLDEN,changed[0],GOLDEN,GOLDEN,GOLDEN])
                self.assertEqual([x['position'] for x in selected[-2:]],[0,1])
                self.assertEqual(run.h.counts()['jobs'],5);self.assertEqual(run.h.counts()['unacked'],0)
                self.assertEqual(len(run.observations()),6)
                # Public payloads and model-visible context never include caller secrets,
                # operator paths or a generated private canary planted only at the provider.
                report=run.report();public=canonical(report).decode()
                for forbidden in (secret,run.h.client['credential'],str(run.h.config_path),str(run.h.server_root)):
                    self.assertNotIn(forbidden,public)
                reports.append(dict(original_native=original,changed_native=changed,**report))
                # A bounded restart neither regenerates commands nor adds occurrences.
                self.success(run);self.assertEqual(run.h.counts()['jobs'],5)
                self.assertEqual(len(run.observations()),6)
        for component in ('skills.metta','loop.metta','lib_llm.metta'):
            self.assertEqual(reports[0]['startup']['overlay_hashes'][component],reports[1]['startup']['overlay_hashes'][component])
        evidence('multi-turn',reports)

    def test_sigkill_recovers_accepted_turn_without_model_regeneration(self):
        reports=[]
        for stage in ('after_occurrence_bind','after_submit_reply','after_caller_completion','after_application_projection'):
            with self.subTest(stage=stage):
                run=self.fresh();run.operator()
                process,marker=self.pause(run,stage)
                before=run.rows('app_occurrences');counts=run.h.counts()
                self.assertEqual(len(run.observations()),1)
                if stage=='after_occurrence_bind': self.assertEqual(counts.get('caller_requests',0),0)
                if stage=='after_caller_completion':
                    self.assertEqual(counts['caller_acked'],1);self.assertIsNone(before[0]['result'])
                code=self.killed(run,process,marker)
                self.success(run)
                after=run.rows('app_occurrences')
                for field in ('id','premises','deadline','turn','position'):
                    self.assertEqual(before[0][field],after[0][field])
                self.assertEqual(after[0]['result'],GOLDEN)
                self.assertEqual(len(run.observations()),2)
                self.assertEqual(run.observations()[1]['feedback'].count(GOLDEN),1)
                final=run.h.counts()
                for k in ('jobs','attempts','messages','caller_requests','caller_completed','caller_acked'):
                    self.assertEqual(final[k],1,(stage,final))
                self.assertEqual(final['unacked'],0)
                self.assertGreaterEqual(final['caller_calls'],counts.get('caller_calls',0))
                reports.append(dict(stage=stage,killed_native_pid=marker['pid'],signal=9,exit_code=code,before=counts,**run.report()))
        evidence('native-loop-kills',reports)

    def test_network_outage_wrong_ca_and_revocation_are_typed_no_fallback(self):
        reports=[]
        for fault,code in (('outage','NOT_AVAILABLE'),('wrong-ca','NOT_AVAILABLE'),('revocation','UNAUTHORIZED')):
            with self.subTest(fault=fault):
                run=self.fresh();run.h.client['max_calls']=2;run.h.save_client()
                run.h.service().close()
                if fault=='outage':run.h.stop_server()
                elif fault=='wrong-ca':
                    wrong=run.h.caller_root/'wrong.pem'
                    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(run.h.caller_root/'wrong.key'),
                        '-out',str(wrong),'-days','1','-subj','/CN=wrong'],check=True,capture_output=True)
                    run.h.client['endpoint']['ca_file']=str(wrong);run.h.save_client()
                else:
                    run.h.config['principals']['A']['scopes'][c.SCOPE].remove('execution.submit');run.h.save()
                self.failed(run,code);self.assertEqual(run.h.counts()['jobs'],0)
                self.assertEqual(len(run.observations()),1)
                first=run.rows('app_occurrences')[0]
                self.failed(run,code if fault=='revocation' else 'NOT_AVAILABLE')
                self.assertEqual(run.rows('app_occurrences')[0],first)
                self.assertEqual(len(run.observations()),1)
                reports.append(dict(fault=fault,code=code,counts=run.h.counts(),observed_model_calls=1))
        evidence('network-failures',reports)

    def test_native_invalid_selected_input_and_profile_never_fall_through(self):
        reports=[]
        for expression in ('(Truth_Deduction (stv 2 1) (stv 1 1))','(Truth_Deduction (stv $f 1) (stv 1 1))',
                           '(Truth_Deduction (stv 1 1) (stv 1 1) extra)'):
            run=self.fresh(responses=['metta '+expression,'']);run.operator()
            self.failed(run,'INVALID_ARGUMENT')
            self.assertEqual(run.h.counts()['jobs'],0);self.assertEqual(run.rows('app_occurrences'),[])
            reports.append(dict(fault='invalid-selected-input',code='INVALID_ARGUMENT',jobs=0))
        run=self.fresh()
        for d in run.h.client['catalogue']:
            if d['interface']=='execution':d['profiles']=['unrelated-profile/1']
        run.h.save_client();self.failed(run,'UNSUPPORTED_PROFILE')
        self.assertEqual(run.observations(),[])
        reports.append(dict(fault='incompatible-profile',code='UNSUPPORTED_PROFILE',model_calls=0))
        evidence('native-validation',reports)

    def test_malformed_bound_payload_refused_before_handoff(self):
        run=self.fresh();run.operator()
        process,marker=self.pause(run,'after_submit_reply')
        self.wait(lambda:run.h.counts()['outbox']==1)
        self.wait(lambda:run.h.counts()['messages']==1)
        service=run.h.service()
        try:
            row=service.db.execute('SELECT id,result FROM jobs').fetchone()
            original=json.loads(row['result'])
            data=json.loads(service.atoms_for('worker').get(original['ref']).bytes)
            forged=service.atoms_for('worker').create(Mutation(c.SCOPE,'malformed-result-test'),
                'application/neoclaw-nal-result',canonical(dict(data,profile='unrelated-profile/1')))
            with service.db:service.db.execute('UPDATE jobs SET result=?',(canonical(forged).decode(),))
        finally:service.close()
        os.kill(marker['pid'],signal.SIGCONT)
        self.failed(run,'NOT_AVAILABLE',process)
        self.assertIsNone(run.rows('app_occurrences')[0]['result'])
        self.assertEqual(run.h.counts()['unacked'],1)
        self.assertEqual(run.h.counts()['caller_completed'],0)
        evidence('malformed-payload',dict(injection='owner-state corruption fixture, valid digest real DeTTa payload',
                 code='NOT_AVAILABLE',counts=run.h.counts(),model_calls=len(run.observations())))

    def test_killed_rpc_reservations_do_not_refund_or_start_new_turn(self):
        run=self.fresh();run.h.client['max_calls']=2;run.h.save_client();run.h.service().close()
        original=None
        for count in (1,2):
            process,marker=self.pause(run,'after_call_reservation')
            row=run.rows('app_occurrences')[0]
            if original is None: original=row
            self.assertEqual(row,original)
            self.killed(run,process,marker)
            self.assertEqual(run.h.counts()['caller_calls'],count)
        self.failed(run,'NOT_AVAILABLE')
        self.assertEqual(run.h.counts()['jobs'],0);self.assertEqual(len(run.observations()),1)
        evidence('application-budget',dict(counts=run.h.counts(),occurrence=original,model_calls=1,deadline_renewed=False))

    def test_deadline_before_submit_is_not_renewed_on_native_restart(self):
        run=self.fresh();run.app['invocation_timeout_ms']=1000;run.save();run.operator()
        process,marker=self.pause(run,'after_occurrence_bind')
        row=run.rows('app_occurrences')[0];self.killed(run,process,marker)
        self.wait(lambda:time.time()*1000>row['deadline'])
        self.failed(run,'DEADLINE_EXCEEDED')
        self.assertEqual(run.rows('app_occurrences')[0]['deadline'],row['deadline'])
        self.assertEqual(run.h.counts()['jobs'],0);self.assertEqual(len(run.observations()),1)
        evidence('application-deadline',dict(deadline=row['deadline'],code='DEADLINE_EXCEEDED',jobs=0,model_calls=1))

    def test_completed_receipt_revocation_blocks_recovery_context(self):
        for stage in ('after_caller_completion','after_application_projection'):
            run=self.fresh();run.operator()
            process,marker=self.pause(run,stage)
            self.killed(run,process,marker)
            methods=run.h.config['principals']['A']['scopes'][c.SCOPE]
            methods.remove('atom.storage.get');run.h.save()
            self.failed(run,'UNAUTHORIZED')
            self.assertEqual(len(run.observations()),1)
            methods.append('atom.storage.get');run.h.save();self.success(run)
            self.assertEqual(run.h.counts()['jobs'],1)
            self.assertEqual(len(run.observations()),2)
            evidence('handoff-revocation-'+stage,dict(revoked='UNAUTHORIZED',restored='same result and occurrence',**run.report()))

    def test_mixed_pending_batch_recovery_is_explicitly_unsupported(self):
        run=self.fresh(responses=[COMMAND+'\nmetta (+ 1 2)','']);run.operator()
        process,marker=self.pause(run,'after_caller_completion')
        self.killed(run,process,marker)
        self.failed(run,'UNSUPPORTED_PROFILE')
        self.assertEqual(len(run.observations()),1)
        self.assertEqual(run.h.counts()['jobs'],1)
        self.assertEqual(run.rows('app_occurrences')[1]['done'],0)
        evidence('mixed-batch-recovery',dict(code='UNSUPPORTED_PROFILE',local_tool_replayed=False,model_calls=1))

    def test_second_position_restart_preserves_batch_order_and_single_route(self):
        reports=[]
        for stage in ('after_submit_reply','after_caller_completion'):
            with self.subTest(stage=stage):
                run=self.fresh(responses=[COMMAND+'\n'+COMMAND,''],expected={'1':[[GOLDEN,2]]})
                run.operator();process,marker=self.pause(run,stage)
                path=Path(run.app['failpoint_marker']);path.unlink()
                os.kill(marker['pid'],signal.SIGCONT)
                run.h.wait_file(path,process)
                second=json.loads(path.read_text())
                before=run.rows('app_occurrences')
                self.assertEqual(before[0]['done'],1);self.assertEqual(before[1]['done'],0)
                self.killed(run,process,second);self.success(run)
                after=run.rows('app_occurrences')
                self.assertEqual([x['id'] for x in before],[x['id'] for x in after])
                self.assertEqual(run.h.counts()['jobs'],2);self.assertEqual(run.h.counts()['attempts'],2)
                self.assertEqual(len(run.observations()),2)
                self.assertEqual(run.observations()[1]['feedback'].count(GOLDEN),2)
                reports.append(dict(stage=stage,**run.report()))
        evidence('second-position-recovery',reports)

    def test_capacity_failure_does_not_advance_or_replenish_budget(self):
        from fusion.neoclaw_client import Caller
        from tests.neoclaw_support import PREMISES
        run=self.fresh(capacity=1)
        run.h.client['max_calls']=3;run.h.save_client()
        # Real competing accepted request; no worker runs, so capacity stays full.
        config=run.h.client_config('capacity-occupant','network','B')
        config['database']=str(run.h.caller_root/'competing.db')
        path=run.h.caller_root/'competing.json';path.write_bytes(canonical(config))
        caller=Caller(path)
        try:caller._call(caller.prepare(PREMISES))
        finally:caller.close()
        self.failed(run,'OVERLOADED')
        before=run.rows('app_occurrences')[0]
        self.assertEqual(run.h.counts()['caller_calls'],3)
        self.failed(run,'NOT_AVAILABLE')
        self.assertEqual(run.rows('app_occurrences')[0],before)
        self.assertEqual(run.h.counts()['jobs'],1)
        self.assertEqual(len(run.observations()),1)
        evidence('capacity',dict(capacity=1,competing_real_acceptance=1,new_jobs=0,
                 first='OVERLOADED',restart='NOT_AVAILABLE',budget_reserved=3,model_calls=1))
