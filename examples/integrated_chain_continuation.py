"""Two real native agents -> saved inspection -> separately approved chain graph.

The operator registers the exact observed artifact, then drives the application's
fixed continuation through HTTPS. It never supplies a tool result or submits a
chain deploy directly. Models only propose native commands. Fresh isolated node,
generated unfunded keys, bounded workload, no text-generative runtime activity.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.chain_continuation import PROFILE as CONTINUATION
from fusion.adapters.f1r3_m4 import PROFILE,DESCRIPTOR
from fusion.registry import selection_token
from integration.single_node.reference_ops import Operator,PYTHON
from .sustained_chain_qualification import Qualification
from .integrated_continuation import qualify as native_qualify


class IntegratedChain(Qualification):
    def application(self,operation,body=None):
        q=dict(profile=CONTINUATION,id=str(uuid.uuid4()),session=self.report['session'],
            occurrence=self.report['occurrence'],operation=operation,body=body or {})
        script='''import json,sys
from fusion.contracts import ContractError
from integration.single_node.preview_operator import chain_continuation
try:print(json.dumps({'value':chain_continuation(json.load(sys.stdin))}))
except ContractError as e:print(json.dumps({'error':e.code}))'''
        return json.loads(self.op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',script,data=json.dumps(q),timeout=40))

    def native(self):
        result=native_qualify(self.op,self.root/'native-workflow')
        report=json.loads((self.root/'native-workflow/native/report.json').read_bytes())
        inspection=next(x for x in report['inputs'] if x['command'].startswith('inspect-atom '))
        self.report.update(native_report_sha256=digest((self.root/'native-workflow/report.json').read_bytes()),
            session=inspection['session'],occurrence=inspection['observed']['result']['occurrences'][0],
            inspection=result['inspection'],native_workflow=result,original_inputs=report['inputs'])
        self.save();self.upgrade()  # Same settings restart the quiesced owners.

    def run_graph(self,resume_from=None):
        require(self.values['preview']['chain'].get('continuation')==CONTINUATION,'UNSUPPORTED_PROFILE')
        if resume_from:
            raw=(Path(resume_from)/'report.json').read_bytes();prior=json.loads(raw)
            require(prior.get('status')=='FAIL' and prior['namespace']==self.op.namespace and
                prior.get('submission') is None and prior.get('admission_reply')=={'error':'NOT_AVAILABLE'},'CONFLICT')
            require(self.values['preview']['chain']['registration']==prior['registration'],'CONFLICT')
            self.report.update({k:v for k,v in prior.items() if k not in ('status','failure','quiesced','admission_reply','acceptance_pause')})
            self.report.update(resumed_report_sha256=digest(raw),original_native_inputs_not_repeated=True)
            require(time.time_ns()//1000000<prior['separately_approved_chain_deadline_ms'],'DEADLINE_EXCEEDED')
            self.save();self.upgrade()
            return self.drive_graph(prior['registration'],prior['separately_approved_chain_deadline_ms'])
        self.op.owned();self.native();self.isolation()
        chain=self.values['preview']['chain'];chain.update(nodeEnabled=True,isolationVerified=True);self.upgrade()
        identity=self.wait(lambda:self.read('f1r3node','chain-identity.json'),90)
        inspected=self.report['inspection'];operation='integrated-workflow-'+str(uuid.uuid4());scope=self.values['preview']['scope']
        deadline=time.time_ns()//1000000+1200000
        reg=dict(profile='synthetic-workflow-commitment/1',principal='A',artifact=inspected['artifact'],
            job_id=inspected['job_id'],result=inspected['inspection'],
            approved=dict(scope_ref=scope,result_ref=inspected['inspection']['ref'],
                commitment_digest=inspected['inspection']['ref']['digest'],approval_record='integrated-exact-result/'+operation),
            binding=dict(profile=PROFILE,selection=selection_token(DESCRIPTOR),chain=identity,signer=chain['public_key'],
                limits=dict(phloPrice=1,phloLimit=10000000,validAfterBlockNumber=0),operation=operation,
                protobuf_sha256='ba9b8ebd44e73cabac064ec00e4f93d9a08a8681bcb3bce3eb5dca6366ba23e6',owner_journal='/state/commitments.sqlite',
                authority=dict(purpose='approved-synthetic-agent-artifact',expires_at_ms=deadline,artifact_digest=inspected['artifact']['digest'])))
        self.report.update(registration=reg,approval_basis='Assigned Q13/Q25 generated shareable workflow; exact native result registered only after capture',
            original_deadline_ms=self.report['native_workflow']['accepted_deadline_retained'],
            separately_approved_chain_deadline_ms=deadline,maximum_native_operator_inputs=4,maximum_chain_submissions=1)
        chain['registration']=reg;self.values['testFaultsEnabled']=True
        self.values['components']['omega-agent'].setdefault('config',{})['test']={'pause_at':'after_chain_continuation_acceptance'}
        self.values['components']['fusion-commitment'].setdefault('config',{})['test']={'drop_response_operation':'submit'}
        self.save();self.upgrade();return self.drive_graph(reg,deadline)

    def readback_only(self,previous):
        raw=(Path(previous)/'report.json').read_bytes();prior=json.loads(raw)
        require(prior['namespace']==self.op.namespace and prior['final_continuation']['status']=='finalized' and
            prior['final_continuation']['submit_reservations']==1 and prior['automatic_resubmissions']==0 and
            self.values['preview']['chain']['registration']==prior['registration'],'CONFLICT')
        self.report.update({k:v for k,v in prior.items() if k not in ('status','failure','quiesced','observer_pod','independent_readback')})
        self.report.update(readback_resumed_report_sha256=digest(raw),additional_chain_submit_reservations=0,
            additional_native_inputs=0,readback_only=True)
        self.save();self.upgrade()
        # Caller observation is local retained state; it never calls the chain.
        observed=self.application('observe');require(observed.get('value')==prior['final_continuation'],'CONFLICT')
        self.report['retained_continuation_after_readback_restart']=observed;self.save()

    def drive_graph(self,reg,deadline):
        operation=reg['binding']['operation'];identity=reg['binding']['chain']
        accepted=self.application('admit',dict(identity=operation,deadline_ms=deadline,approval_sha256=digest(canonical(reg))))
        self.report['admission_reply']=accepted;self.save()
        require(accepted=={'error':'NOT_AVAILABLE'},'NOT_AVAILABLE')
        self.report['acceptance_pause']=self.read('omega-agent','pause.json');self.save()
        require(self.report['acceptance_pause'] is not None and self.report['acceptance_pause']['stage']=='after_chain_continuation_acceptance','NOT_AVAILABLE')
        before=self.pods();self.op.k('delete','pod','omega-agent-0','--grace-period=1','--wait=false')
        self.wait(lambda:self.pods().get('omega-agent-0',{}).get('uid') not in (None,before['omega-agent-0']['uid']),45)
        self.op.k('wait','--for=condition=Ready','pod/omega-agent-0','--timeout=120s',timeout=130)
        self.report['acceptance_recovery']=dict(before=before['omega-agent-0'],after=self.pods()['omega-agent-0'],observation=self.application('observe'));self.save()
        accepted=self.report['acceptance_recovery']['observation']['value']
        require(accepted['status']=='accepted' and accepted['submit_reservations']==0 and accepted['deadline_ms']==deadline,'CONFLICT')
        self.report['submission']=self.application('advance');self.save()
        require(self.report['submission']=={'error':'NOT_AVAILABLE'},'NOT_AVAILABLE')
        self.report['response_drop']=self.read('fusion-commitment','response-dropped.json')
        require(self.report['response_drop']['operation']=='submit','NOT_AVAILABLE')
        self.report['uncertain_after_submit']=self.application('observe');self.save()
        require(self.report['uncertain_after_submit']['value']['submit_reservations']==1,'CONFLICT')
        before=self.pods();self.op.k('delete','pod','omega-agent-0','fusion-commitment-0','f1r3node-0','--grace-period=1','--wait=false')
        for role in ('omega-agent','fusion-commitment','f1r3node'):
            self.wait(lambda:self.pods().get(role+'-0',{}).get('uid') not in (None,before[role+'-0']['uid']),45)
            self.op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=120s',timeout=130)
        require(self.wait(lambda:self.read('f1r3node','chain-identity.json'),90)==identity,'CONFLICT')
        self.report['replacement']=dict(before=before,after=self.pods());self.save()
        for _ in range(16):
            observed=self.application('advance');self.report['observations'].append(observed);self.save()
            require('value' in observed,'NOT_AVAILABLE');value=observed['value']
            require(value['deadline_ms']==deadline and value['submit_reservations']==1,'CONFLICT')
            if value['status']=='finalized':break
            time.sleep(1)
        else:raise RuntimeError('CHAIN_OBSERVATION_TIMEOUT')
        self.report.update(saved_intent=value['signed_intent'],final_observation=value['result'],final_continuation=value,
            automatic_resubmissions=0,source_lineage='ACTUAL_NATIVE_A_TO_B_RETRIEVAL_INSPECTION_CAPTURE',node_identity_unchanged=True)
        # The current session's original native receipts/captures remain exact.
        code='import json;from integration.single_node.preview_operator import request;print(json.dumps(request("observe",'+repr(self.report['session'])+',dict(content=True,after=0))))'
        current=json.loads(self.code('omega-agent',code))
        for original in self.report['original_inputs']:
            require(next(x for x in current['inputs'] if x['id']==original['identity'])==original['observed'],'CONFLICT')
        self.report['original_native_captures_and_bounds_exact']=True;self.save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','output','observer'):p.add_argument('--'+name,required=True)
    p.add_argument('--resume-from')
    p.add_argument('--readback-only',action='store_true')
    a=p.parse_args();q=IntegratedChain(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.output)
    try:
        if a.readback_only:require(a.resume_from is not None);q.readback_only(a.resume_from)
        else:q.run_graph(a.resume_from)
        q.independent(a.observer)
    except BaseException as error:
        q.report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[:1024]));raise
    finally:
        q.op.quiesce();q.report['quiesced']=True;q.save()
    print(json.dumps(dict(status=q.report['status'],additional_live_generations=0)))

if __name__=='__main__':main()
