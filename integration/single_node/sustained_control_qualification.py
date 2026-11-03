"""Finite operator drill of the actual deployed /3 lifecycle, not a scheduler.

Requires a fresh minimal task namespace initially installed with native workers
explicitly disabled. Admission still works. No SQL edits, deadline replacement,
reservation refund, synthetic completion, or model-runtime activity is used.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,require
from .preview_recovery_qualification import Recovery
from .preview_qualification import Runner
from .reference_ops import Operator

class Control(Recovery):
    def __init__(self,op,values,chart,output):
        import yaml
        self.op,self.values_path,self.chart=op,Path(values),str(chart)
        self.values=yaml.safe_load(self.values_path.read_text())
        require(self.values['preview']['profile']=='omega-single-node-sustained-preview/1','UNSUPPORTED_PROFILE')
        require(all(self.values['components'][r]['config']['nativeEnabled'] is False for r in ('omega-agent','omega-agent-b')),'UNAUTHORIZED')
        self.root=Path(output);self.root.mkdir(parents=True,exist_ok=False)
        self.api=Runner.__new__(Runner);self.api.op=op
        self.end=time.monotonic()+900
        self.report=dict(namespace=op.namespace,status='RUNNING',additional_live_generations=0,
            inputs=[],cases=[],maximum_new_inputs=6,maximum_wall_seconds=900,
            classification='REAL_DEPLOYED_NATIVE_RECORDED_PROPOSALS_WITH_LIFECYCLE_FAULTS')
        self.save()
    def upgrade(self):
        import yaml
        self.values_path.write_text(yaml.safe_dump(self.values,sort_keys=False))
        text=self.op.command(['helm','upgrade','omega',self.chart,'--kubeconfig',self.op.kubeconfig,'--kube-context',self.op.context,
            '--namespace',self.op.namespace,'-f',str(self.values_path),'--wait','--timeout','180s'],timeout=190)
        (self.root/('upgrade-'+str(time.time_ns())+'.log')).write_text(text)
    def submit(self,role,sid,identity,text):
        require(len(self.report['inputs'])<6,'OVERLOADED')
        result=self.api.call(role,'submit',sid,'--identity',identity,'--text',text,'--assignment','synthetic-task')
        self.report['inputs'].append(dict(role=role,accepted=result));self.save();return result
    def wait_until(self,fn,until):
        require(until<=self.end,'OVERLOADED')
        while time.monotonic()<until:
            result=fn()
            if result:return result
            time.sleep(.5)
        require(False,'NOT_AVAILABLE')
    def run(self):
        self.op.owned();api=self.api
        try:
            # Force loss after committed allocation. Original request identity
            # is replayed after replacement, never accepted as a new session.
            self.arm('omega-agent','pause_at','after_session_allocation_commit')
            identity='allocation-reply-loss'
            try:api.call('omega-agent','allocate',None,'--identity',identity,'--template','shared')
            except RuntimeError:pass
            else:require(False,'CONFLICT')
            marker=self.read('omega-agent','pause.json');require(marker and marker['stage']=='after_session_allocation_commit','NOT_AVAILABLE')
            self.report['allocation_replacement']=self.replace(['omega-agent']);self.save()
            allocation=api.call('omega-agent','allocate',None,'--identity',identity,'--template','shared');sid=allocation['session']
            require(api.call('omega-agent','allocate',None,'--identity',identity,'--template','shared')==allocation,'CONFLICT')
            self.report['allocation']=allocation;self.save()
            first=self.submit('omega-agent',sid,'undispatched-expiry','pin expired Must never execute')
            second=self.submit('omega-agent',sid,'cancel-before-start','pin cancelled Must never execute')
            cancel=api.call('omega-agent','cancel',sid,'--identity','cancel-one','--target',second['id'])
            require(api.call('omega-agent','cancel',sid,'--identity','cancel-one','--target',second['id'])==cancel,'CONFLICT')
            self.report['cancel_before_start']=cancel;self.save()
            self.wait_until(lambda:time.time_ns()//1000000>=first['deadline'],min(self.end,time.monotonic()+125))
            api.call('omega-agent','reconcile',sid)
            reconciled=api.call('omega-agent','observe',sid,'--content')
            states={x['id']:x for x in reconciled['inputs']}
            require(states[first['id']]['state']=='expired-before-start' and states[second['id']]['state']=='cancelled-before-start','CONFLICT')
            require(states[first['id']]['deadline']==first['deadline'] and all(x['result'] is None for x in states.values()),'CONFLICT')
            self.report['safe_terminalization']=reconciled;self.save()
            third=self.submit('omega-agent',sid,'eligible-after-expiry','pin recovery Native progress after safe expiry')
            for role in ('omega-agent','omega-agent-b'):self.values['components'][role]['config']['nativeEnabled']=True
            self.values['components']['omega-agent-b']['config']['test']={'pause_at':'after_input_dispatch_commit'}
            self.upgrade()
            until=time.monotonic()+max(0,(third['deadline']-time.time()*1000)/1000)+8
            complete=self.wait_until(lambda:(x if (x:=self.observe('omega-agent',sid,third['id']))['state']=='complete' else None),min(self.end,until))
            require(complete['deadline']==third['deadline'],'CONFLICT');self.report['progress_after_expiry']=complete;self.save()
            unknown=api.call('omega-agent-b','allocate',None,'--identity','uncertain-session','--template','shared')['session']
            started=self.submit('omega-agent-b',unknown,'cancel-after-dispatch','pin uncertain Preserve uncertain input')
            self.wait_until(lambda:self.read('omega-agent-b','pause.json'),min(self.end,time.monotonic()+20))
            cancelled=api.call('omega-agent-b','cancel',unknown,'--identity','cancel-started','--target',started['id'])
            self.report['cancel_after_dispatch']=cancelled;self.save()
            self.report['uncertain_replacement']=self.replace(['omega-agent-b']);self.save()
            blocked=self.submit('omega-agent-b',unknown,'dependent-blocked','pin dependent Must remain fenced')
            # An unrelated active session can finish while B's causal chain is
            # fenced. This is an explicit new input, not recovery by replacement.
            # Re-observing the already completed A input consumes no new work.
            require(self.observe('omega-agent',sid,third['id'])==complete,'CONFLICT')
            api.call('omega-agent-b','reconcile',unknown)
            observed=api.call('omega-agent-b','observe',unknown,'--content')
            states={x['id']:x for x in observed['inputs']}
            require(states[started['id']]['state']=='cancel-requested' and states[blocked['id']]['state']=='accepted','CONFLICT')
            require(states[started['id']]['result'] is None and states[blocked['id']]['result'] is None,'CONFLICT')
            self.report['uncertain_fence']=observed;self.save()
            independent=self.submit('omega-agent',sid,'independent-after-fence','pin independent Safe work in the other agent session')
            until=time.monotonic()+max(0,(independent['deadline']-time.time()*1000)/1000)+8
            result=self.wait_until(lambda:(x if (x:=self.observe('omega-agent',sid,independent['id']))['state']=='complete' else None),min(self.end,until))
            require(result['deadline']==independent['deadline'],'CONFLICT')
            self.report['independent_progress']=result;self.report['current_independent']=api.call('omega-agent','current',sid)
            self.report.update(status='PASS',deadline_renewals=0,refunds=0,synthetic_acknowledgments=0);self.save()
        except BaseException as error:
            self.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-900:]));self.save();raise
        finally:self.op.quiesce();self.report['quiesced']=True;self.report['pvcs_retained']=True;self.save()
        return self.report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=Control(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.output);print(json.dumps(r.run()))
if __name__=='__main__':main()
