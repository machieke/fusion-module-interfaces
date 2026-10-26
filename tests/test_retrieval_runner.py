"""Generation-denied campaign authorization, monotonic slots and observers."""
import copy
import concurrent.futures
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch
from fusion.contracts import canonical,digest
from integration.neoclaw import retrieval_campaign as c
from integration.neoclaw import retrieval_runner as r


class Campaign(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path=self.root/'manifest.json';self.config=self.root/'config.json';c.atomic(self.config,dict(selected='fixed'))
        sessions=[dict(id=str(uuid.uuid4()),placement=p) for p in ('local','network')]
        self.value=dict(schema='retrieval-grounded-campaign/1',campaign_id='test-only-'+uuid.uuid4().hex,kind='recorded-qualification',sources={},
            bindings=[dict(path=str(self.config),sha256=c.sha(self.config))],runtime_required_files=[],sessions=sessions,execution_root=str(self.root/'execution'),
            slots=[dict(id=str(uuid.uuid5(uuid.UUID(s['id']),'model/'+str(i))),session=s['id'],slot=i,name=s['placement']+'-'+str(i)) for s in sessions for i in (1,2)])
        self.freeze();c.initialize(self.path);r.test_approval(self.path)
        self.approval=self.root/'approval.json'
        self.intent=dict(self.value['slots'][0],deadline_ms=time.time_ns()//1_000_000+300000)
    def freeze(self):
        self.path.write_bytes(canonical(self.value));self.path.with_suffix('.sha256').write_text(digest(self.path.read_bytes())+'\n')
    def test_positive_test_authority_is_recorded_only(self):
        c.approve(self.path,self.approval,recorded=True)
        with self.assertRaisesRegex(RuntimeError,'WRONG_CAMPAIGN_KIND'):c.approve(self.path,self.approval)
        self.value['kind']='live';self.freeze()
        with self.assertRaisesRegex(RuntimeError,'INVALID_AUTHORITY'):c.approve(self.path,self.approval)
    def test_missing_approval_precedes_any_process_or_backend(self):
        self.value['kind']='live';self.freeze();self.approval.unlink()
        with patch.object(r,'observe_session') as observer,patch('fusion.adapters.ollama_completion.OllamaCompletion') as backend:
            with self.assertRaisesRegex(RuntimeError,'AWAITING_LIVE_AUTHORIZATION'):r.execute(self.path,self.approval)
            observer.assert_not_called();backend.assert_not_called()
        self.assertFalse(c.read(self.root/'execution/ledger.json')['started'])
    def test_manifest_flags_and_hash_are_not_approval(self):
        a=c.read(self.approval)
        for value in ({'enabled':True},{'manifest_sha256':a['manifest_sha256']},{'authority':'EXPLICIT_USER_APPROVAL'}):
            c.atomic(self.approval,value)
            with self.assertRaises(RuntimeError):c.approve(self.path,self.approval,recorded=True)
    def test_stale_mismatched_authority_session_slots_and_window(self):
        old=c.read(self.approval)
        for key,value in [('campaign_id','other'),('manifest_sha256','0'*64),('slots',['other']),('expires_ms',1),('max_generations',5),('user_statement','')]:
            with self.subTest(key=key):
                c.atomic(self.approval,dict(old,**{key:value}))
                with self.assertRaises(RuntimeError):c.approve(self.path,self.approval,recorded=True)
    def test_config_source_model_and_tls_drift_denied(self):
        c.atomic(self.config,dict(selected='changed'))
        with self.assertRaisesRegex(RuntimeError,'FROZEN_INPUT_DRIFT'):c.approve(self.path,self.approval,recorded=True)
        for name in ('source.py','model.json','server.pem'):
            p=self.root/name;p.write_text('original');self.value['bindings']=[dict(path=str(p),sha256=c.sha(p))]
            self.freeze();r.test_approval(self.path);p.write_text('changed')
            with self.assertRaisesRegex(RuntimeError,'FROZEN_INPUT_DRIFT'):c.approve(self.path,self.approval,recorded=True)
    def test_duplicate_and_reopened_spent_slot_cannot_evaluate_again(self):
        c.claim(self.path,self.approval,self.intent,recorded=True)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError,'EVALUATION_ALREADY_SPENT'):c.claim(self.path,self.approval,self.intent,recorded=True)
        self.assertEqual(len(c.ledger(self.path)['started']),1)
    def test_projection_reset_never_refunds_write_once_claim(self):
        c.claim(self.path,self.approval,self.intent,recorded=True)
        state=c.ledger(self.path);state['started']={};c.atomic(self.root/'execution/ledger.json',state)
        self.assertEqual(len(c.ledger(self.path)['started']),1)
        with self.assertRaisesRegex(RuntimeError,'EVALUATION_ALREADY_SPENT'):c.claim(self.path,self.approval,self.intent,recorded=True)
    def test_claim_deletion_or_modification_is_detected(self):
        c.claim(self.path,self.approval,self.intent,recorded=True)
        p=self.root/'execution/claims'/(self.intent['id']+'.json');data=c.read(p);data['deadline_ms']+=1;c.atomic(p,data)
        with self.assertRaisesRegex(RuntimeError,'LEDGER_TAMPER'):c.ledger(self.path)
        p.unlink()
        with self.assertRaisesRegex(RuntimeError,'LEDGER_ROLLBACK'):c.ledger(self.path)
    def test_concurrent_claim_has_one_winner(self):
        def invoke(_):
            try:c.claim(self.path,self.approval,self.intent,recorded=True);return 'claimed'
            except RuntimeError:return 'refused'
        with concurrent.futures.ThreadPoolExecutor(4) as pool:outcomes=list(pool.map(invoke,range(4)))
        self.assertEqual(outcomes.count('claimed'),1)
    def test_unplanned_or_cross_session_slot_refused(self):
        for change in (dict(id=str(uuid.uuid4())),dict(session=str(uuid.uuid4())),dict(slot=2)):
            with self.assertRaises(RuntimeError):c.claim(self.path,self.approval,dict(self.intent,**change),recorded=True)
    def test_real_process_kill_preserves_spent_claim(self):
        intent=self.root/'intent.json';c.atomic(intent,self.intent)
        code='from integration.neoclaw import retrieval_campaign as c; import os,signal,sys; c.claim(sys.argv[1],sys.argv[2],c.read(sys.argv[3]),recorded=True); os.kill(os.getpid(),signal.SIGSTOP)'
        p=subprocess.Popen([sys.executable,'-c',code,str(self.path),str(self.approval),str(intent)])
        try:
            r.wait(lambda:len(c.ledger(self.path)['started'])==1,time.time_ns()//1_000_000+10000,p)
            p.kill();p.wait(5);self.assertEqual(p.returncode,-signal.SIGKILL)
            with self.assertRaisesRegex(RuntimeError,'EVALUATION_ALREADY_SPENT'):c.claim(self.path,self.approval,self.intent,recorded=True)
        finally:
            if p.poll() is None:p.kill();p.wait()
    def test_observer_timeout_has_no_effect_or_resubmission(self):
        with self.assertRaises(r.ObserverExpired):r.wait(lambda:False,time.time_ns()//1_000_000+20)
        self.assertEqual(c.ledger(self.path)['started'],{})
    def test_peer_match_is_actual_exact_sender_route_body(self):
        row=dict(received=':omega!u@host PRIVMSG #synthetic :wrong but permitted')
        self.assertTrue(r.peer_received([row],'wrong but permitted','#synthetic'))
        for body,target in [('preferred answer','#synthetic'),('wrong but permitted','#other')]:self.assertFalse(r.peer_received([row],body,target))
        self.assertFalse(r.peer_received([dict(sent=row['received'])],'wrong but permitted','#synthetic'))
        self.assertFalse(r.peer_received([dict(received=row['received'].replace(':omega!',':peer!'))],'wrong but permitted','#synthetic'))


if __name__=='__main__':unittest.main()
