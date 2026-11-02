"""Bounded native preview qualification through the operator session API.

Recorded proposals may echo these operator inputs; all tool results, handles,
views and task replies come from the two native applications. No provider SQL,
expected-answer injection, model runtime, retiming or implicit resubmission.
"""
import argparse,json,time,uuid,re
from pathlib import Path
from fusion.contracts import require
from .reference_ops import Operator,PYTHON


class Runner:
    def __init__(self,operator,destination):
        self.op=operator;self.root=Path(destination);self.root.mkdir(parents=True,exist_ok=False)
        self.report=dict(classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',additional_live_generations=0,
            namespace=operator.namespace,inputs=[],scenarios=[],maximum_operator_inputs=32,maximum_observer_overrun_seconds=8)
        self.ids={};self.count=0;self.end=time.monotonic()+1800
    def save(self):
        (self.root/'report.json').write_text(json.dumps(self.report,indent=2)+'\n')
    def call(self,role,operation,sid=None,*args):
        command=[PYTHON,'-m','integration.single_node.preview_operator',operation]
        if sid:command+=['--session',sid]
        return json.loads(self.op.k('exec',role+'-0','--',*command,*args,timeout=35))
    def setup(self):
        self.op.owned();self.report['preflight']=self.op.preflight()
        for role in ('omega-agent','omega-agent-b'):
            inventory=self.call(role,'inventory');self.ids[role]=list(inventory['sessions'])
            self.report[role]=inventory
            for sid in self.ids[role]:self.call(role,'create',sid)
        self.save()
    @staticmethod
    def object(projection):
        text=projection.replace('_quote_','"')
        return json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
    def run(self,command,role='omega-agent',session=0):
        require(self.count<32 and time.monotonic()<self.end,'OVERLOADED');self.count+=1;sid=self.ids[role][session]
        identity='qualification-'+str(uuid.uuid4())
        entry=dict(role=role,session=sid,identity=identity,command=command,started_ms=time.time_ns()//1_000_000)
        self.report['inputs'].append(entry);self.save()
        accepted=self.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
        entry['accepted']=accepted;self.save();until=min(self.end,time.monotonic()+max(0,(accepted['deadline']-time.time()*1000)/1000)+8)
        while True:
            observed=self.call(role,'observe',sid,'--content');row=next(x for x in observed['inputs'] if x['id']==identity)
            if row['state']=='complete' or time.monotonic()>until:break
            time.sleep(1)
        entry.update(observed=row,finished_ms=time.time_ns()//1_000_000);self.save()
        print(role,command.split()[0],row['state'],flush=True)
        require(row['state']=='complete','NOT_AVAILABLE');return row['result']['projection']
    def handoff(self,sender,recipient):
        role='omega-agent' if sender=='A' else 'omega-agent-b';sid=self.ids[role][0]
        projection=self.object(self.run('delegate '+recipient+' synthetic silver prism storage',role))
        end=min(self.end,time.monotonic()+max(0,(projection['deadline']-time.time()*1000)/1000)+8)
        while True:
            observations={r:self.call(r,'observe',self.ids[r][0],'--content') for r in self.ids}
            returned=[x for x in observations[role]['inputs'] if x['assignment']=='delegated-result' and x['deadline']==projection['deadline']]
            if (returned and returned[0]['state']=='complete') or time.monotonic()>end:break
            time.sleep(1)
        value=dict(scenario='two-agent-'+sender+'-'+recipient,task=projection,observations=observations,
            passed=bool(returned and returned[0]['state']=='complete'))
        self.report['scenarios'].append(value);self.save();require(value['passed'],'NOT_AVAILABLE')
        return projection['task']
    def combined(self):
        self.run('pin role Ready for one bounded shared retrieval','omega-agent-b')
        memory=self.object(self.run('remember The synthetic silver prism is stored in crate orchid'))['memory']['handle']
        # Exercise shared retrieval immediately after its authoritative memory
        # publication. Later cognition uses the same sessions and retained task
        # result; no scenario changes an already accepted task deadline.
        first=self.handoff('A','B');self.handoff('B','A')
        page=self.object(self.run('episodes current'))
        source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
        relation=self.object(self.run('link '+memory+' '+source))['relation']['handle']
        self.report['returned_handles']=dict(memory=memory,source=source,relation=relation);self.save()
        revisions=[]
        for command in ['support '+memory+' '+source,'support '+memory+' '+source,'contradict '+memory+' '+source]:
            revisions.append(self.run(command))
        require('REVISION-SUCCESS' in revisions[0] and 'retained-alternative' in revisions[2],'NOT_AVAILABLE')
        before=self.run('query synthetic silver prism storage')
        self.run('promote '+memory)
        after=self.run('query synthetic silver prism storage')
        truth=lambda value:re.findall(r'_apostrophe_stv_apostrophe_, ([0-9.e+-]+), ([0-9.e+-]+)',value)
        require(truth(before) and truth(before)==truth(after) and 'crate orchid' in before and 'crate orchid' in after,'NOT_AVAILABLE')
        self.report['cognition']=dict(revisions=revisions,before_promotion=before,after_promotion=after,
            displayed_truth_unchanged_by_priority=True)
        self.run('pin evidence Track source reuse without adding independent weight')
        inspected=self.object(self.run('inspect-atom '+first))
        self.report['inspection']=inspected;self.save()
        self.run('unlink '+relation)
        return inspected
    def workspace(self):
        for command in ['write-file scratch.txt Synthetic bounded note','append-file scratch.txt Observed second line','read-file scratch.txt']:
            self.run(command,session=1)
        self.report['scenarios'].append(dict(scenario='workspace-native',passed=True));self.save()
    def lifecycle(self):
        # A distinct memory avoids withdrawing the shared workflow artifact's
        # source. The historical task result and its original view stay intact.
        memory=self.object(self.run('remember The synthetic bronze cube is stored in crate lilac'))['memory']['handle']
        updated=self.object(self.run('update '+memory+' The synthetic bronze cube is stored in crate saffron'))
        self.report['supersession']=updated;self.save()
        visible=self.run('query synthetic bronze cube storage')
        require('crate saffron' in visible and 'crate lilac' not in visible,'NOT_AVAILABLE')
        new=updated['memory']['handle'];self.run('forget '+new)
        withdrawn=self.run('query synthetic bronze cube storage')
        require('crate saffron' not in withdrawn and 'crate lilac' not in withdrawn,'NOT_AVAILABLE')
        self.report['scenarios'].append(dict(scenario='native-lifecycle',passed=True,physical_erasure=False,
            superseded_query=visible,withdrawn_query=withdrawn));self.save()

    def recovery_setup(self):
        memory=self.object(self.run('remember The synthetic silver prism is stored in crate orchid'))['memory']['handle']
        page=self.object(self.run('episodes current'))
        source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
        relation=self.object(self.run('link '+memory+' '+source))['relation']['handle']
        self.run('unlink '+relation)
        self.report['returned_handles']=dict(memory=memory,source=source,relation=relation)
        self.workspace();self.save()

    def attention_replacement(self):
        memory=self.object(self.run('remember The synthetic copper token is stored in crate alder'))['memory']['handle']
        before=self.run('query synthetic copper token storage')
        self.run('promote '+memory);promoted=self.run('query synthetic copper token storage')
        self.run('demote '+memory);demoted=self.run('query synthetic copper token storage')
        truth=lambda value:re.findall(r'_apostrophe_stv_apostrophe_, ([0-9.e+-]+), ([0-9.e+-]+)',value)
        require(all('crate alder' in value for value in (before,promoted,demoted)),'NOT_AVAILABLE')
        require(truth(before) and truth(before)==truth(promoted)==truth(demoted),'CONFLICT')
        self.report['scenarios'].append(dict(scenario='native-attention-replacement',passed=True,
            before=before,promoted=promoted,demoted=demoted,displayed_truth_unchanged_by_priority=True))
        self.save()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kubeconfig',required=True);p.add_argument('--context',required=True)
    p.add_argument('--namespace',required=True);p.add_argument('--output',required=True)
    p.add_argument('--mode',choices=('combined','recovery-setup','attention-replacement'),default='combined');a=p.parse_args()
    r=Runner(Operator(a.kubeconfig,a.context,a.namespace),a.output)
    r.report['mode']=a.mode
    try:
        r.setup()
        if a.mode=='combined':r.combined();r.workspace();r.lifecycle()
        elif a.mode=='recovery-setup':r.recovery_setup()
        else:r.attention_replacement()
        r.report['status']='PASS'
    except Exception as error:
        r.report['status']='FAILED';r.report['failure']=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[:1024]);raise
    finally:r.save()

if __name__=='__main__':main()
