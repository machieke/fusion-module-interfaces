"""Real DeTTa + pinned guarded native deduction; injected faults are labelled."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import time
import unittest
from unittest.mock import patch
from fusion import cognition_contracts as c
from fusion.contracts import ContractError, canonical, digest
from fusion.ports import DerivationSubmission, Mutation
from fusion.adapters.pln_deduction import DeductionRuntime, GuardedDeduction
from tests.m3_support import CognitionHarness, SCOPE
from tests.m2_support import assumption

class NativeDeduction(unittest.TestCase):
    def setUp(self):self.h=CognitionHarness(real=True)
    def tearDown(self):self.h.close()
    def request(self,entry,key='derive',expected=0):
        return DerivationSubmission(Mutation(SCOPE,key),entry['task'],'generated',tuple(entry['premises']),expected,c.BELIEF_PROFILE,
            self.h.modules.selections['kernel'],int(time.time()*1000)+60000)
    def error(self,code,fn,*args):
        with self.assertRaises(ContractError) as error:fn(*args)
        self.assertEqual(error.exception.code,code)

    def test_native_golden_historical_vector_and_duplicate_safe_admission(self):
        entry,roles,episode=self.h.generated();request=self.request(entry)
        result=self.h.beliefs.submitDerivation(request);s=result['snapshot']
        self.assertEqual(result['admission'],'admitted');self.assertAlmostEqual(float(s['truth']['strength']),17/25,delta=1e-12)
        self.assertAlmostEqual(float(s['truth']['confidence']),196/625,delta=1e-12)
        self.assertIsNone(s['truth']['evidence_count']);self.assertEqual(s['observations'],[])
        self.assertEqual(len(s['supports']),1);self.assertEqual(len(s['supports'][0]['evidence_ids']),5)
        self.assertEqual(s['supports'][0]['premises'],entry['premises'])
        self.assertEqual(self.h.episodes.readEpisode(episode,1,16)['head'],5)
        self.h.reopen();self.assertEqual(self.h.beliefs.submitDerivation(request),result)
        with patch.object(DeductionRuntime,'evaluate',side_effect=AssertionError('duplicate must not evaluate')):
            other=self.h.beliefs.submitDerivation(replace(request,command=Mutation(SCOPE,'different-step')))
        self.assertEqual(other['admission'],'duplicate');self.assertEqual(other['snapshot'],s)
        self.assertEqual(self.h.beliefs.readBelief(roles['pr'],'generated',0)['truth'],None)

    def test_native_near_one_branch_and_infeasible_and_zero_guards(self):
        entry,_,_=self.h.generated('near',strengths=['0.5','1','0.5','1','0.5'])
        value=self.h.beliefs.submitDerivation(self.request(entry))
        self.assertAlmostEqual(float(value['snapshot']['truth']['strength']),.5,delta=1e-12)
        self.assertIn('upstream-q>0.9999-uses-r',value['snapshot']['supports'][0]['assumptions'])
        for name,strengths in [('infeasible',['0.9','0.1','0.5','0.8','0.8']),('zero',['0','0.5','0.5','0.8','0.8'])]:
            entry,roles,_=self.h.generated(name,strengths=strengths)
            with patch.object(DeductionRuntime,'evaluate',side_effect=AssertionError('precheck must refuse')):
                result=self.h.beliefs.submitDerivation(self.request(entry,name))
            self.assertEqual(result['state'],'refused');self.assertIsNone(self.h.beliefs.readBelief(roles['pr'],'generated',None)['truth'])

    def test_exact_historical_binding_not_latest_and_missing_support(self):
        entry,roles,episode=self.h.generated()
        event=self.h.event(roles['p'],'new-p',source='sensor-b',strength='0.25')
        receipt=self.h.append(episode,event,5);self.h.submit(roles['p'],receipt['evidence'],key='new-p')
        result=self.h.beliefs.submitDerivation(self.request(entry));self.assertEqual(result['snapshot']['supports'][0]['premises'][0]['revision'],1)
        missing={**entry,'premises':[dict(x) for x in entry['premises']]};missing['premises'][0]['support_id']='missing'
        self.error('NOT_FOUND',self.h.beliefs.submitDerivation,self.request(missing,'missing',expected=1))
        wrong=list(entry['premises']);wrong[0],wrong[1]=wrong[1],wrong[0]
        self.error('INVALID_ARGUMENT',self.h.beliefs.submitDerivation,replace(self.request(entry,'order',1),premises=tuple(wrong)))

    def test_retains_existing_observation_and_does_not_infer_independence(self):
        entry,roles,episode=self.h.generated()
        event=self.h.event(roles['pr'],'prior-output',strength='0.2',source='sensor-b')
        receipt=self.h.append(episode,event,5);prior=self.h.submit(roles['pr'],receipt['evidence'],key='prior-output')
        result=self.h.beliefs.submitDerivation(self.request(entry,expected=1))
        self.assertEqual(result['numerical'],'retained-alternative');self.assertEqual(result['snapshot']['truth'],prior['snapshot']['truth'])
        self.assertEqual(len(result['snapshot']['observations']),1);self.assertEqual(result['snapshot']['alternatives'],[result['logical_id']])

    def test_derive_revise_derive_preserves_ancestry_and_blocks_cycle(self):
        entry,roles,episode=self.h.generated();derived=self.h.beliefs.submitDerivation(self.request(entry))
        event=self.h.event(roles['pr'],'independent-output',source='sensor-b',strength='0.6')
        receipt=self.h.append(episode,event,5);observed=self.h.submit(roles['pr'],receipt['evidence'],key='independent-output')
        revised=self.h.submit(roles['pr'],support_id=observed['support_id'],key='revise-derived',
            independence=assumption(derived['logical_id'],observed['support_id']))
        self.assertEqual(revised['numerical'],'revised')
        aggregate=next(s for s in revised['snapshot']['supports'] if s['id']==revised['snapshot']['aggregate'])
        self.assertTrue(set(map(canonical,derived['snapshot']['supports'][0]['ancestors']))<=set(map(canonical,aggregate['ancestors'])))
        # Reuse P=>R as a premise in P,R,Q => P=>Q; P=>Q is already an ancestor.
        reverse={'p':roles['p'],'q':roles['r'],'r':roles['q'],'pq':roles['pr'],'pr':roles['pq']}
        reverse['qr']=self.h.atoms.create(Mutation(SCOPE,'rq'),'application/fusion-claim',canonical({'predicate':'pln:implication',
            'arguments':[digest(canonical(roles['r'])),digest(canonical(roles['q']))],'positive':True}))['ref']
        rq_event=self.h.event(reverse['qr'],'rq',strength='0.8');receipt=self.h.append(episode,rq_event,6)
        rq=self.h.submit(reverse['qr'],receipt['evidence'],key='rq')
        task=self.h.atoms.create(Mutation(SCOPE,'cycle-task'),'application/fusion-task',canonical({'profile':c.RULE,'context':'generated','roles':reverse}))['ref']
        vector=[entry['premises'][0],entry['premises'][2],entry['premises'][1],
            {'claim':roles['pr'],'context':'generated','revision':revised['snapshot']['revision'],'support_id':aggregate['id']},
            {'claim':reverse['qr'],'context':'generated','revision':1,'support_id':rq['support_id']}]
        with patch.object(DeductionRuntime,'evaluate',side_effect=AssertionError('cycle must not evaluate')):
            result=self.h.beliefs.submitDerivation(self.request({'task':task,'premises':vector},'cycle',1))
        self.assertEqual(result['state'],'refused');self.assertIn('cyclic',result['detail'])

    def test_authorization_and_cas_rechecked_after_kernel(self):
        entry,roles,episode=self.h.generated()
        def hook(stage):
            if stage=='after_kernel_return':
                self.h.config['principals']['owner']['scopes'][SCOPE].remove('belief.revision.submitDerivation');self.h.save()
        self.h.beliefs.hook=hook
        self.error('UNAUTHORIZED',self.h.beliefs.submitDerivation,self.request(entry))
        self.assertEqual(self.h.beliefs.readBelief(roles['pr'],'generated',None)['revision'],0)
        self.h.config['principals']['owner']['scopes'][SCOPE].append('belief.revision.submitDerivation');self.h.save()
        def race(stage):
            if stage=='after_kernel_return':
                event=self.h.event(roles['pr'],'race',source='sensor-b');r=self.h.append(episode,event,5);self.h.submit(roles['pr'],r['evidence'],key='race')
        self.h.beliefs.hook=race
        self.error('CONFLICT',self.h.beliefs.submitDerivation,self.request(entry,'race-derived'))
        self.assertEqual(self.h.beliefs.readBelief(roles['pr'],'generated',None)['revision'],1)

    def test_runtime_drift_wrong_profile_parse_errors_and_native_timeout(self):
        kernel=self.h.modules.kernel;native=DeductionRuntime(kernel.config,kernel.upstream,int(time.time()*1000)+60000)
        self.error('UNSUPPORTED_PROFILE',DeductionRuntime(dict(kernel.config,runtime_profile='revision'),kernel.upstream,None).check)
        self.error('UNSUPPORTED_PROFILE',DeductionRuntime(dict(kernel.config,swipl_sha256='0'*64),kernel.upstream,None).check)
        for output in ('','true','true\n(stv 0.5 0.5)\n(stv 0.5 0.5)','true\n(stv nan 0.5)','true\n(stv 0.5 1)','true\n(stv 0.5 inf)','true\nReachabilityRejected'):
            self.error('NOT_AVAILABLE',native.parse,output)
        path=self.h.root/'drift';subprocess.run(['git','clone','-q','--no-hardlinks',kernel.config['pln'],str(path)],check=True)
        with (path/'lib_pln.metta').open('a') as f:f.write('\n; injected drift\n')
        self.error('UNSUPPORTED_PROFILE',DeductionRuntime(dict(kernel.config,pln=str(path)),kernel.upstream,None).check)
        entry,roles,_=self.h.generated();kernel.timeout=.000001
        self.error('NOT_AVAILABLE',self.h.beliefs.submitDerivation,self.request(entry,'timeout'))
        self.assertIsNone(self.h.beliefs.readBelief(roles['pr'],'generated',None)['truth'])

    def test_two_tasks_one_attempt_selection_feedback_and_swap(self):
        measurements=[]
        for provider in ('sqlite','atomic-file-fixture'):
            if provider!='sqlite':self.h.close();self.h=CognitionHarness(real=True,provider=provider)
            a,roles_a,_=self.h.generated('a');b,roles_b,_=self.h.generated('b')
            self.h.stimulate(a,'10','a');self.h.stimulate(b,'20','b')
            request=self.h.request(self.h.workset([a,b]));result=self.h.controller.step(request)
            self.assertEqual(result['counts']['reserved'],1);self.assertEqual(result['counts']['unique_admissions'],1)
            self.assertEqual(result['counts']['feedback_applied'],1);self.assertEqual(result['results'][0]['task'],b['task'])
            self.assertIsNone(self.h.beliefs.readBelief(roles_a['pr'],'generated',None)['truth'])
            self.assertIsNotNone(self.h.beliefs.readBelief(roles_b['pr'],'generated',None)['truth'])
            self.h.reopen();self.assertEqual(self.h.controller.step(request),result)
            duplicate=self.h.controller.step(replace(request,command=Mutation(SCOPE,'another-step')))
            self.assertEqual(duplicate['counts']['duplicate_admissions'],1);self.assertEqual(duplicate['counts']['feedback_applied'],0)
            self.h.stimulate(a,'30','boost-a');switched=self.h.controller.step(replace(request,command=Mutation(SCOPE,'switch')))
            self.assertEqual(switched['results'][0]['task'],a['task'])
            measurements.append(result['counts'])
        self.assertEqual(*measurements)

    def test_pure_kernel_closed_vectors_and_malformed_proposal_admission(self):
        entry,roles,_=self.h.generated();task=self.h.beliefs._task(entry['task'],'generated')
        resolved=tuple({'binding':b,'support':self.h.beliefs.readBelief(b['claim'],'generated',1)['supports'][0]} for b in entry['premises'])
        kernel=self.h.modules.kernel;deadline=int(time.time()*1000)+60000
        proposal=kernel.applyRule(task,resolved,deadline)
        self.assertIsNone(self.h.beliefs.readBelief(roles['pr'],'generated',None)['truth'])
        for variant in ('model','context','order'):
            altered=c.detached(list(resolved))
            if variant=='model':altered[0]['support']['truth']['model']='unselected-model'
            elif variant=='context':altered[0]['binding']['context']='other'
            else:altered[0],altered[1]=altered[1],altered[0]
            self.error('UNSUPPORTED_PROFILE' if variant=='model' else 'INVALID_ARGUMENT',kernel.applyRule,task,tuple(altered),deadline)
        for key in ('lineage_roots','ancestors','premises'):
            bad=c.detached(proposal);bad['proposal'][key]=[]
            with patch.object(kernel,'applyRule',return_value=bad):
                from tests.m2_support import PortOnly
                self.h.beliefs.kernel=PortOnly(kernel,('profile','applyRule'))
                self.error('NOT_AVAILABLE',self.h.beliefs.submitDerivation,self.request(entry,'malformed-'+key))
        self.assertEqual(self.h.beliefs.readBelief(roles['pr'],'generated',None)['revision'],0)

    def test_native_conditional_refusal_never_admits_fallback(self):
        from fusion.adapters import pln_deduction as adapter
        entry,roles,_=self.h.generated();real_run=adapter.run
        def injected(args,**kwargs):
            if '--silent' in args:
                program=Path(args[args.index('--')+1]).read_text()
                self.assertIn('(if (and (conditional-probability-consistency',program)
                self.assertIn('ReachabilityRejected',program)
                return 'true\nReachabilityRejected\n'
            return real_run(args,**kwargs)
        with patch.object(adapter,'run',side_effect=injected):
            result=self.h.beliefs.submitDerivation(self.request(entry))
        self.assertEqual(result['state'],'refused');self.assertEqual(result['status'],'UNKNOWN')
        self.assertIsNone(self.h.beliefs.readBelief(roles['pr'],'generated',None)['truth'])

    def test_generation_limit_across_new_worksets_steps_and_ingress(self):
        entry,roles,episode=self.h.generated();self.h.stimulate(entry)
        generation=[]
        for index in range(5):
            if index:
                occurrence='next-p-'+str(index)
                event=self.h.event(roles['p'],occurrence,strength='0.5',confidence='0.8')
                receipt=self.h.append(episode,event,4+index);decision=self.h.submit(roles['p'],receipt['evidence'],key=occurrence)
                entry['premises'][0]={'claim':roles['p'],'context':'generated','revision':decision['snapshot']['revision'],'support_id':decision['support_id']}
                self.h.stimulate(entry,'1','ingress-'+str(index))
            workset=self.h.workset([entry],key='workset-'+str(index))
            result=self.h.controller.step(self.h.request(workset,key='step-'+str(index),candidates=1))
            self.assertEqual(result['counts']['unique_admissions'],1)
            self.assertEqual(result['counts']['feedback_applied'],1 if index<3 else 0)
            generation.append(self.h.attention.readAttention(entry['task'],'generated')['value']['generation'])
            self.h.reopen()
        self.assertEqual(generation,[1,2,3,3,3])

    def test_concurrent_clock_advance_keeps_feedback_pending(self):
        entry,roles,_=self.h.generated();self.h.stimulate(entry)
        def hook(stage):
            if stage=='after_derived_commit':self.h.attention.advance(Mutation(SCOPE,'concurrent-clock'),'generated',0,1)
        self.h.beliefs.hook=hook
        request=self.h.request(self.h.workset([entry]),candidates=1)
        result=self.h.controller.step(request)
        self.assertEqual(result['status'],'pending');self.assertEqual(result['reason'],'feedback-unavailable')
        self.assertEqual(result['feedback'][0]['last_error'],'CONFLICT');self.assertEqual(result['counts']['reserved'],1)
        self.h.reopen();self.assertEqual(self.h.controller.step(request),result)
        self.assertEqual(self.h.attention.readAttention(entry['task'],'generated')['value']['sti'],'9')

    def test_private_inference_never_calls_populated_shared_bindings(self):
        import contextlib,io
        from tests.support import Harness
        shared=self.h.root/'shared';public_harness=Harness(binding='inprocess',root=shared)
        control=public_harness.a.store(b'Public generated control','control');public_harness.a.share(control['ref'],'reply-B','control-share')
        before={str(p.relative_to(shared)):p.read_bytes() for p in shared.rglob('*') if p.is_file()}
        output=io.StringIO()
        with patch('fusion.bindings.Subprocess.invoke',side_effect=AssertionError('private shared egress')) as outbound, \
             patch('fusion.bindings.InProcess.invoke',side_effect=AssertionError('private shared egress')) as local, \
             contextlib.redirect_stdout(output),contextlib.redirect_stderr(output):
            entry,roles,_=self.h.generated('PRIVATE-CANARY');self.h.stimulate(entry)
            result=self.h.controller.step(self.h.request(self.h.workset([entry]),candidates=1))
        self.assertEqual(result['counts']['unique_admissions'],1);self.assertEqual(outbound.call_count+local.call_count,0)
        self.assertEqual(before,{str(p.relative_to(shared)):p.read_bytes() for p in shared.rglob('*') if p.is_file()})
        public=output.getvalue().encode()+b''.join(before.values())
        for marker in [b'PRIVATE-CANARY',entry['task']['digest'].encode(),*[b['support_id'].encode() for b in entry['premises']],result['results'][0]['logical_id'].encode()]:
            self.assertNotIn(marker,public)

if __name__=='__main__':unittest.main()
