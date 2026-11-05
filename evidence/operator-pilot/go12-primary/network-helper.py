"""Finite operator-only faults on two declared task-owned dependency edges.

This supplement never submits work itself. The unchanged native onboarding and
registered recipe drivers retain their caller, provider, and chain budgets.
"""
import argparse,copy,importlib.util,json,threading,time
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,digest,require
from integration.single_node.placement import compile
from integration.single_node.reference_ops import Operator

PAIRS={('fusion-inspect-go','fusion-messaging'),('fusion-commitment','f1r3node')}


def blocked_spec(spec,source,target):
    require((source,target) in PAIRS,'UNAUTHORIZED')
    require(spec['podSelector']=={'matchLabels':{'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':source}}
        and spec['policyTypes']==['Ingress','Egress'],'CONFLICT')
    value=copy.deepcopy(spec);matches=[]
    for index,rule in enumerate(spec['egress']):
        if rule.get('to')==[{'podSelector':{'matchLabels':{'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':target}}}]:
            require(rule['ports']==[{'port':40403 if target=='f1r3node' else 8443,'protocol':'TCP'}],'CONFLICT');matches.append(index)
    require(len(matches)==1,'CONFLICT');del value['egress'][matches[0]]
    # DNS and the independently permitted storage edge must remain byte-exact.
    require(any(x.get('to')==[{'podSelector':{'matchLabels':{'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':'fusion-storage'}}}] for x in value['egress']),'CONFLICT')
    return value


class EdgeFault:
    def __init__(self,op,plan,chart,source,target,directory):
        self.op,self.source,self.target=op,source,target
        self.root=Path(directory);self.root.mkdir(parents=True,exist_ok=False)
        require(plan['namespace']==op.namespace and plan['scope'].startswith('synthetic-'),'UNAUTHORIZED')
        self.expected=next(x['spec'] for x in compile(plan,chart)['objects'] if x['kind']=='NetworkPolicy' and x['metadata']['name']==source+'-ports')
        self.blocked=blocked_spec(self.expected,source,target);self.original=None
        self.report=dict(profile='bounded-task-network-edge-fault/1',namespace=op.namespace,source=source,target=target,
            original_spec_sha256=digest(canonical(self.expected)),blocked_spec_sha256=digest(canonical(self.blocked)),
            status='PREPARED',additional_native_inputs=0,additional_live_generations=0,restore_status='NOT_NEEDED')
        self.save()
    def save(self):(self.root/'report.json').write_bytes(canonical(self.report))
    def get(self):return json.loads(self.op.k('get','networkpolicy',self.source+'-ports','-o','json'))
    def block(self):
        self.op.owned();actual=self.get()
        require(actual['metadata']['namespace']==self.op.namespace and actual['spec']==self.expected,'CONFLICT')
        require(actual['metadata']['annotations']['meta.helm.sh/release-name']=='omega','UNAUTHORIZED')
        self.original=copy.deepcopy(actual);(self.root/'original.json').write_bytes(canonical(actual))
        updated=copy.deepcopy(actual);updated['spec']=self.blocked
        self.report.update(status='APPLYING',restore_status='REQUIRED',blocked_at_ms=time.time_ns()//1000000);self.save()
        self.op.k('replace','-f','-',data=json.dumps(updated))
        after=self.get();require(after['metadata']['uid']==actual['metadata']['uid'] and after['spec']==self.blocked,'CONFLICT')
        self.report.update(status='BLOCKED',policy_uid=after['metadata']['uid']);self.save()
    def restore(self):
        if self.original is None:return
        actual=self.get();require(actual['metadata']['uid']==self.original['metadata']['uid'],'CONFLICT')
        require(actual['spec'] in (self.blocked,self.expected),'CONFLICT')
        if actual['spec']==self.blocked:
            updated=copy.deepcopy(actual);updated['spec']=self.expected
            self.op.k('replace','-f','-',data=json.dumps(updated))
        require(self.get()['spec']==self.expected,'CONFLICT')
        self.report.update(restore_status='RESTORED_EXACT',restored_at_ms=time.time_ns()//1000000);self.save()


def load_capacity(path):
    spec=importlib.util.spec_from_file_location('selected_capacity_observer',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def go_qualify(op,plan_path,artifact,chart,directory,original,authority,capacity_helper):
    from examples import pilot_go_provider as driver
    plan=json.loads(Path(plan_path).read_bytes());root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    capacity=load_capacity(capacity_helper)
    report=dict(profile='go-asymmetric-dependency-qualification/1',status='RUNNING',observations=[],
        helper_sha256=digest(Path(__file__).read_bytes()),capacity_helper_sha256=digest(Path(capacity_helper).read_bytes()),
        original_driver_sha256=digest(Path(driver.__file__).read_bytes()),maximum_capacity_calls=6,maximum_blocked_seconds=75,
        additional_native_inputs=0,additional_live_generations=0,deadlines_extended=False)
    def save():(root/'report.json').write_bytes(canonical(report))
    save();Base=driver.Runner
    class SelectedRunner(Base):
        def run(self,text,*args,**kwargs):
            if not text.startswith('inspect-atom '):return super().run(text,*args,**kwargs)
            require('edge' not in report,'CONFLICT')
            edge=EdgeFault(op,plan,chart,'fusion-inspect-go','fusion-messaging',root/'edge');report['edge']=str(root/'edge/report.json');save()
            done=threading.Event();errors=[]
            def observe():
                try:
                    stop=time.monotonic()+75
                    for index in range(6):
                        if done.is_set() or time.monotonic()>=stop:break
                        deadline=int(time.time()*1000)+min(12000,int((stop-time.monotonic())*1000))
                        try:
                            value=capacity.observe(op,plan_path,artifact,chart,authority,root/('capacity-'+str(index)),deadline)
                            report['observations'].append(value);save();c=value['capacity']
                            if c['closure']['captured']==1 and c['closure']['delivered']==0 and c['worker_phases']['spent']>=2:
                                report['actual_capture_while_delivery_unavailable']=True;save();break
                        except BaseException as error:
                            report['observations'].append(dict(status='FAILED',detail=str(error)[:500]));save()
                        if done.wait(1):break
                except BaseException as error:errors.append(error)
                finally:
                    try:edge.restore()
                    except BaseException as error:errors.append(error)
            try:
                edge.block();time.sleep(2) # bounded propagation before input admission
                worker=threading.Thread(target=observe);worker.start()
                try:result=super().run(text,*args,**kwargs)
                finally:done.set();worker.join(timeout=85)
                require(not worker.is_alive() and not errors and report.get('actual_capture_while_delivery_unavailable') is True,'NOT_AVAILABLE')
                report['same_native_invocation_completed_after_restore']=True;save();return result
            finally:edge.restore()
    try:
        with patch.object(driver,'Runner',SelectedRunner):
            result=driver.qualify(op,plan,artifact,root/'native-onboarding',original=original)
        report.update(status='PASS',native_report_sha256=digest((root/'native-onboarding/report.json').read_bytes()),native_result=result);save()
    except BaseException as error:report.update(status='FAIL',failure=str(error)[-1500:]);save();raise
    return report


def chain_qualify(op,plan_path,values,chart,directory,observer):
    from examples.pilot_recipe_chain import RecipeChain
    plan=json.loads(Path(plan_path).read_bytes());root=Path(directory)
    class SelectedChain(RecipeChain):
        def application(self,operation,body=None):
            if operation!='advance' or 'replacement' not in self.report or 'dependency_outage' in self.report:
                return super().application(operation,body)
            before=super().application('observe')['value']
            # The first post-replacement drive captures the retained signed
            # intent locally; fault the next actual chain observation only.
            if before['signed_intent'] is None:return super().application(operation,body)
            require(before['submit_reservations']==1 and before['result'] is None,'CONFLICT')
            edge=EdgeFault(op,plan,chart,'fusion-commitment','f1r3node',root/'chain-edge')
            self.report['dependency_outage']=dict(before=before,status='RUNNING',additional_submissions=0);self.save()
            try:
                edge.block();time.sleep(2)
                reply=super().application(operation,body);after=super().application('observe')
                self.report['dependency_outage'].update(blocked_reply=reply,after=after);self.save()
                require(after['value']['submit_reservations']==1 and after['value']['deadline_ms']==before['deadline_ms'] and
                    after['value']['observations_spent']==before['observations_spent']+1 and after['value']['status']!='finalized','CONFLICT')
                require(time.time_ns()//1000000<before['deadline_ms'],'DEADLINE_EXCEEDED')
            finally:edge.restore()
            self.report['dependency_outage'].update(status='OBSERVED_AND_RESTORED',edge_report_sha256=digest((root/'chain-edge/report.json').read_bytes()));self.save()
            # Return the actual owner observation. The failed/uncertain remote
            # reply remains separately retained; this is no fabricated receipt.
            return after
    q=SelectedChain(op,values,chart,root)
    try:q.run_graph();q.independent(observer)
    except BaseException as error:q.report.update(status='FAIL',failure=dict(type=type(error).__name__,detail=str(error)[-1500:]));raise
    finally:q.op.quiesce();q.report['quiesced']=True;q.save()
    return q.report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('go','chain'))
    for name in ('kubeconfig','context','namespace','plan','chart','directory'):p.add_argument('--'+name,required=True)
    for name in ('artifact','original','authority','capacity-helper','values','observer'):p.add_argument('--'+name)
    a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace)
    if a.action=='go':
        require(all((a.artifact,a.original,a.authority,a.capacity_helper)),'INVALID_ARGUMENT')
        value=go_qualify(op,a.plan,a.artifact,a.chart,a.directory,a.original,a.authority,a.capacity_helper)
    else:
        require(a.values and a.observer,'INVALID_ARGUMENT');value=chain_qualify(op,a.plan,a.values,a.chart,a.directory,a.observer)
    print(json.dumps(dict(status=value['status'],additional_live_generations=0)))

if __name__=='__main__':main()
