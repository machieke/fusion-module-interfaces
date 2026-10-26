"""Opt-in real native/IRC/E5/Chroma/DeTTa qualification, authored model only.

All artifacts retained. Run under preparation_guard with FUSION_RUNNER_NATIVE=1.
Tests mutate only their fresh recorded campaigns, never the final live plan.
"""
import json
import os
from pathlib import Path
import time
import unittest
import uuid
from fusion.contracts import canonical
from integration.neoclaw import retrieval_campaign as c
from integration.neoclaw import retrieval_runner as r
from integration.neoclaw.retrieval_freeze import prepare
from integration.neoclaw.retrieval_preparation import QUERY,BODIES
from integration.neoclaw.embedding_run import start
from integration.neoclaw.channel_composition import write

@unittest.skipUnless(os.environ.get('FUSION_RUNNER_NATIVE')=='1','explicit isolated native qualification required')
class NativeRunner(unittest.TestCase):
    def run_case(self,name,responses=None,checkpoint=None,variant=0):
        root=c.ROOT/'artifacts/retrieval-runner'/(name+'-'+uuid.uuid4().hex[:8])
        path=prepare(root,recorded=True,responses=responses,variant=variant);r.test_approval(path)
        reports=r.execute(path,root/'approval.json',recorded=True,checkpoint=checkpoint)
        output=c.ROOT/'evidence/retrieval-runner'/('native-'+root.name+'.json')
        c.atomic(output,dict(test=self.id(),campaign_manifest=str(path),manifest_sha256=c.sha(path),sources=c.plan(path)[0]['sources'],reports=reports,
                             additional_live_generations=0,live_memory_workflow='NOT_RUN'))
        self.assertEqual(len(reports),2)
        return reports
    def assert_workflow(self,report,expected='PASS'):
        self.assertEqual(report['outcome'],expected,report.get('failure'))
        self.assertTrue(report['evaluation']['output_permitted']);self.assertTrue(report['evaluation']['peer_observed'])
        calls=report['application']['app_model_calls'];self.assertEqual(len(calls),2)
        self.assertTrue(all(x['result'] is not None and x['admission']=='authorized' for x in calls))
        first=json.loads(calls[0]['intent'])['native_prompt']
        for body in BODIES[:3]:self.assertNotIn(body.removeprefix('Synthetic answer: '),first)
        self.assertIn(report['query_capture'],json.loads(calls[1]['intent'])['native_prompt'])
        self.assertEqual(report['application']['app_channel_outputs'][0]['send_calls'],1)
        self.assertEqual(len(report['bridge']),1);self.assertEqual(report['bridge'][0]['reserved'],1)
    def test_correct_and_wrong_permitted_actual_bodies(self):
        reports=self.run_case('actual-bodies',responses={'local':['query '+QUERY,'send '+BODIES[0]],'network':['query '+QUERY,'send '+BODIES[1]]})
        self.assert_workflow(reports[0]);self.assert_workflow(reports[1],'FAIL')
        self.assertEqual(reports[1]['actual_admitted_send_body'],BODIES[1]);self.assertFalse(reports[1]['evaluation']['answer_correct'])
    def test_early_send_and_mixed_batch_rejected(self):
        reports=self.run_case('reject-stage',responses={'local':['send '+BODIES[0],'send '+BODIES[0]],'network':['query '+QUERY+'\nsend '+BODIES[0],'send '+BODIES[0]]})
        for report in reports:
            self.assertEqual(report['outcome'],'FAILED');self.assertEqual(len(report['application']['app_model_calls']),1)
            self.assertTrue(report['application']['app_model_calls'][0]['admission'].startswith('rejected:'))
            self.assertFalse(report['application']['app_channel_outputs'])
    def test_unsupported_command_and_missing_target_stop(self):
        reports=self.run_case('reject-or-no-target',responses={'local':['shell echo synthetic','send '+BODIES[0]],'network':['query '+QUERY,'send '+BODIES[0]]},variant=2)
        self.assertTrue(reports[0]['application']['app_model_calls'][0]['admission'].startswith('rejected:'))
        self.assertEqual(reports[1]['failure'],'RETRIEVAL_NOT_DECISIVE');self.assertEqual(len(reports[1]['application']['app_model_calls']),1)
    def test_capture_and_query_process_kill_recovery(self):
        killed=[]
        def checkpoint(stage,run,ch,process):
            placement=c.read(run.app['model_config'])['placement']
            pause='after_model_application_capture' if placement=='local' else 'after_native_result_capture'
            if stage=='before-start':
                run.app.update(pause_at=pause);write(run.app_path,run.app)
            if stage=='first-input':
                marker=Path(run.app['failpoint_marker'])
                r.wait(marker.exists,time.time_ns()//1_000_000+90000,process)
                before=r.Application.inspect(run.app_path)
                run.kill(process);killed.append(dict(stage=pause,before=before,exit=process.returncode))
                run.app.pop('pause_at');write(run.app_path,run.app)
                return start(run)
        reports=self.run_case('capture-recovery',checkpoint=checkpoint)
        self.assertEqual(len(killed),2)
        for report,kill in zip(reports,killed):
            self.assert_workflow(report);self.assertLess(kill['exit'],0)
            before=kill['before']['app_model_calls'][0];after=report['application']['app_model_calls'][0]
            self.assertEqual(before['intent'],after['intent']);self.assertEqual(before['result'],after['result'])
            self.assertEqual(len(report['ledger']['started']),2 if report['placement']=='local' else 4)
    def test_current_revocation_and_observer_expiry(self):
        def checkpoint(stage,run,ch,process):
            if stage!='query-captured':return
            placement=c.read(run.app['model_config'])['placement']
            if placement=='local':
                policy=Path(c.read(run.app['model_config'])['disclosure']['authority_policy']);cfg=c.read(policy)
                cfg['principals']['A']['scopes'][cfg['model_completion']['scope']].remove('model.disclose');write(policy,cfg)
            else:raise r.ObserverExpired('TEST_BOUNDED_OBSERVER_EXPIRED')
        reports=self.run_case('revoke-timeout',checkpoint=checkpoint)
        self.assertEqual(reports[0]['outcome'],'FAILED');self.assertEqual(reports[0]['native_status']['code'],'UNAUTHORIZED')
        self.assertEqual(reports[1]['outcome'],'OBSERVER_TIMEOUT')
        for report in reports:self.assertEqual(len(report['application']['app_model_calls']),1)
    def test_retrieval_revocation_and_uncaptured_reservation_process_kill(self):
        killed=[]
        def checkpoint(stage,run,ch,process):
            placement=c.read(run.app['model_config'])['placement']
            policy=Path(c.read(run.app['model_config'])['disclosure']['authority_policy'])
            if stage=='before-start' and placement=='network':
                # Restore only this test's prior fault before the independent
                # reservation scenario; both sessions share the corpus owner.
                readcfg=c.read(run.app['memory_read_config']);provider=Path(readcfg['provider_config']);state=c.read(provider)
                methods=state['principals']['A']['scopes'][readcfg['scope']]
                if 'atom.storage.get' not in methods:methods.append('atom.storage.get')
                write(provider,state)
                cfg=c.read(policy);cfg['pause_at']='after_model_reservation';write(policy,cfg)
            if stage=='ready' and placement=='local':
                readcfg=c.read(run.app['memory_read_config']);p=Path(readcfg['provider_config']);cfg=c.read(p)
                scope=readcfg['scope'];cfg['principals']['A']['scopes'][scope].remove('atom.storage.get');write(p,cfg)
            if stage=='first-input' and placement=='network':
                marker=Path(c.read(policy)['failpoint_marker']);r.wait(marker.exists,time.time_ns()//1_000_000+30000,process)
                host=run.processes[0];run.kill(host);killed.append(host.returncode)
                cfg=c.read(policy);cfg.pop('pause_at');write(policy,cfg)
                selected=run.app['campaign_backend'];plan,_=c.plan(selected['manifest']);session=next(x for x in plan['sessions'] if x['id']==selected['session'])
                ready=Path(session['completion_root'])/'ready.json';ready.unlink(missing_ok=True)
                host=run.spawn('integration.neoclaw.retrieval_backend',[session['backend_selection'],policy,session['model_port'],ready],'model-host-recovery');ch.wait(ready,host)
                process.wait(timeout=10)
                return start(run)
        reports=self.run_case('retrieval-spent',checkpoint=checkpoint)
        self.assertEqual(len(killed),1);self.assertLess(killed[0],0)
        self.assertEqual(reports[0]['outcome'],'FAILED');self.assertEqual(reports[0]['native_status']['code'],'UNAUTHORIZED')
        owner=reports[1]['model_owner'];self.assertEqual(len(owner),1);self.assertEqual(owner[0]['reserved'],1);self.assertIsNone(owner[0]['response'])
        self.assertEqual(reports[1]['outcome'],'FAILED');self.assertEqual(len(reports[1]['application']['app_model_calls']),1)
    def test_uncertain_send_is_never_automatically_resent(self):
        killed=[]
        def checkpoint(stage,run,ch,process):
            if stage=='before-start':
                ch.bridge_config['pause_at']='after_socket_write';write(ch.bridge_config_path,ch.bridge_config)
            if stage=='send-accepted':
                marker=Path(ch.bridge_config['failpoint_marker']);r.wait(marker.exists,time.time_ns()//1_000_000+10000)
                ch.kill(ch.bridge);killed.append(True);ch.bridge_config.pop('pause_at');ch.start_bridge(seconds=40)
                # Reconnect produces a new bridge epoch; a reserved send may
                # only be observed, never executed in that new epoch.
        reports=self.run_case('uncertain-send',checkpoint=checkpoint)
        self.assertEqual(len(killed),2)
        for report in reports:
            self.assert_workflow(report);self.assertEqual(report['bridge'][0]['outcome'],'unknown')
            body=report['actual_admitted_send_body'];target='#s06-generated'
            self.assertEqual(sum(r.peer_received([row],body,target) for row in report['peer']),1)

if __name__=='__main__':unittest.main()
