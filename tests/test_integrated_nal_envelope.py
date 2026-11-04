"""Real local owners/wire validation; declared numerical and payload fixtures."""
import copy,json,unittest
from fusion.contracts import ContractError,canonical
from fusion import nal_envelope as e
from fusion.neoclaw_client import Caller
from tests.neoclaw_support import Harness,PREMISES


class NalEnvelope(unittest.TestCase):
    def setUp(self):
        self.h=Harness();self.addCleanup(self.h.close)
        self.h.config['portable_execution']=e.PROFILE;self.h.save()
        self.h.client['portable_execution']=e.PROFILE;self.h.save_client()
        self.caller=self.h.caller();self.addCleanup(self.caller.close)
        self.request=self.caller.prepare(PREMISES)
        self.wire=dict(request=self.request,envelope=e.build(self.request,'A',self.caller.chosen))
    def error(self,code,fn,*args):
        with self.assertRaises(ContractError) as caught:fn(*args)
        self.assertEqual(caught.exception.code,code)
    def send(self,wire):
        s=self.h.service()
        try:return s.invoke_enveloped(self.h.client['credential'],wire)
        finally:s.close()
    def test_binding_before_submission_and_original_result_profile(self):
        rows=self.caller.db.execute('SELECT envelope FROM integrated_execution_envelopes').fetchall();self.assertEqual(len(rows),1)
        accepted=self.caller._call(self.request)
        self.assertEqual(self.caller._call(self.request),accepted)
        s=self.h.service()
        try:
            s.work();value=s.invoke(self.h.client['credential'],self.caller._request('execution','result',dict(job_id=accepted['job_id'])))
            data=s.atoms_for('A').get(value['ref']).bytes
        finally:s.close()
        self.assertEqual(json.loads(data)['profile'],'neoclaw-nal-truth-deduction/1')
        self.assertEqual(json.loads(data)['premises'],PREMISES)
    def test_extra_code_wrong_delegation_provider_and_profile_reject(self):
        for field,value in [('inputs',dict(premises=PREMISES,code='arbitrary')),
            ('delegation',dict(service='execution',actor='other',authority='current-scoped-policy')),
            ('task','different-task'),('limits',dict(self.wire['envelope']['limits'],native_attempts=999))]:
            wire=copy.deepcopy(self.wire);wire['envelope'][field]=value
            self.error('CONFLICT',self.send,wire)
        wire=copy.deepcopy(self.wire);wire['envelope']['provider']['kernel']='0'*64
        self.error('UNSUPPORTED_PROFILE',self.send,wire)
        self.assertEqual(self.h.counts()['jobs'],0)
    def test_envelope_cannot_be_dropped_or_changed_after_acceptance(self):
        self.send(self.wire);s=self.h.service()
        try:self.error('UNSUPPORTED_PROFILE',s.invoke,self.h.client['credential'],self.request)
        finally:s.close()
        wire=copy.deepcopy(self.wire);wire['request']['deadline_ms']+=1
        wire['envelope']=e.build(wire['request'],'A',self.caller.chosen)
        self.error('CONFLICT',self.send,wire)
    def test_current_revocation_and_unsafe_downgrade_refuse(self):
        self.send(self.wire)
        self.h.config['principals']['A']['scopes'][self.h.client['scope']].remove('execution.submit');self.h.save()
        self.error('UNAUTHORIZED',self.send,self.wire)
        self.h.config.pop('portable_execution');self.h.save()
        self.error('UNSUPPORTED_PROFILE',self.h.service)
    def test_legacy_populated_provider_cannot_silently_adopt(self):
        h=Harness();self.addCleanup(h.close);h.submit();h.config['portable_execution']=e.PROFILE;h.save()
        self.error('UNSUPPORTED_PROFILE',h.service)
