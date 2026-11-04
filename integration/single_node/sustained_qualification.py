"""Bounded qualification through the existing deployed native input endpoint.

No direct feed generator, answer references passed to a consumer, owner SQL or
model runtime. Each run freezes its workload before accepting the first input.
Failures retain original identities; no automatic re-submit or deadline reset.
"""
import json,time,threading,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fusion.contracts import require
from .preview_qualification import Runner as PreviewRunner
from .sustained_evaluation import freeze,score,DATASETS,stopped_premise


class Runner(PreviewRunner):
    def __init__(self,operator,destination,*,maximum_inputs=72,legacy_crossing_required=True):
        require(type(maximum_inputs) is int and 1<=maximum_inputs<=96,'OVERLOADED')
        require(type(legacy_crossing_required) is bool)
        super().__init__(operator,destination)
        self.maximum_inputs=maximum_inputs
        self.legacy_crossing_required=legacy_crossing_required
        self.lock=threading.RLock();self.end=time.monotonic()+3600
        self.report.update(frozen=freeze(),maximum_operator_inputs=maximum_inputs,source_observations=[],evaluations=[],profile='omega-native-sessions/3')
        self.save()
    def save(self):
        with self.lock:
            target=self.root/'report.json';temporary=target.with_suffix('.pending')
            temporary.write_text(json.dumps(self.report,indent=2)+'\n');temporary.replace(target)
    def allocate(self,role,identity,template='shared'):
        value=self.call(role,'allocate',None,'--identity',identity,'--template',template)
        replay=self.call(role,'allocate',None,'--identity',identity,'--template',template)
        require(value['session']==replay['session'] and value['allocation']==replay['allocation'],'CONFLICT')
        self.ids.setdefault(role,[]).append(value['session'])
        with self.lock:self.report.setdefault('allocations',[]).append(dict(role=role,template=template,value=value,replay_identical=True));self.save()
        return len(self.ids[role])-1
    def run(self,command,role='omega-agent',session=0):
        with self.lock:
            require(self.count<getattr(self,'maximum_inputs',72) and time.monotonic()<self.end,'OVERLOADED');self.count+=1
            sid=self.ids[role][session];identity='sustained-'+str(uuid.uuid4())
            entry=dict(role=role,session=sid,identity=identity,command=command,started_ms=time.time_ns()//1000000)
            self.report['inputs'].append(entry);self.save()
        try:
            accepted=self.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
            with self.lock:entry['accepted']=accepted;self.save()
            until=min(self.end,time.monotonic()+max(0,(accepted['deadline']-time.time()*1000)/1000)+8)
            while True:
                observed=self.call(role,'observe',sid,'--content');row=next(x for x in observed['inputs'] if x['id']==identity)
                if row['state'] in ('complete','expired-before-start','cancelled-before-start','rejected') or time.monotonic()>until:break
                time.sleep(1)
            with self.lock:entry.update(observed=row,finished_ms=time.time_ns()//1000000);self.save()
            print(role,command.split()[0],row['state'],flush=True)
            require(row['state']=='complete','NOT_AVAILABLE');return row['result']['projection']
        except Exception as error:
            with self.lock:entry['failure']=dict(type=type(error).__name__,code=getattr(error,'code',None));self.save()
            raise
    def current(self,role,session):
        value=self.call(role,'current',self.ids[role][session])
        with self.lock:self.report['source_observations'].append(dict(role=role,session=self.ids[role][session],value=value));self.save()
        return value
    def close(self,role,session):
        value=self.call(role,'close',self.ids[role][session],'--identity','close-'+self.ids[role][session]);self.save();return value
    def evaluate(self,projection,case):
        value=score(projection,case)
        with self.lock:self.report['evaluations'].append(value);self.save()
        require(value['task_pass'],'CONFLICT');return value
    def sustained(self):
        # Three consecutive sessions per agent, six legitimate native inputs
        # each. Memory/query/history/task-context all retain their source events.
        # The first memory is discovered by later consumers through Search.
        first=None;crossed_at=None
        for round0 in range(3):
            for role in ('omega-agent','omega-agent-b'):
                index=self.allocate(role,'sustained-round-'+str(round0))
                if first is None:
                    first=self.object(self.run('remember '+DATASETS['new']['fact'],role,index))
                    self.report['first_memory']=first;self.save()
                else:self.run('pin review Observe retained corpus round '+str(round0),role,index)
                self.evaluate(self.run('query '+DATASETS['new']['query'],role,index),DATASETS['new'])
                self.run('episodes current',role,index)
                self.run('pin state Retained sources remain authoritative',role,index)
                self.run('task-context',role,index)
                self.evaluate(self.run('query '+DATASETS['new']['query'],role,index),DATASETS['new'])
                current=self.current(role,index)
                if current['source_head']['sequence']>512 and crossed_at is None:crossed_at=self.count
                self.close(role,index)
        self.report['crossing']=dict(at_input=crossed_at,after_crossing_inputs=0 if crossed_at is None else self.count-crossed_at,source_not_reset=True)
        self.save()
        if self.legacy_crossing_required:require(crossed_at is not None and self.count-crossed_at>=4,'NOT_AVAILABLE')
        # Read the first acknowledged result after the threshold; it keeps the
        # original view even though fresh queries selected later owner heads.
        old=self.call('omega-agent','observe',self.ids['omega-agent'][0],'--content')
        self.report['retained_first_session']=old
        require(old['inputs'][0]['result']['projection']==self.report['inputs'][0]['observed']['result']['projection'],'CONFLICT');self.save()
    def overlap(self):
        indices={role:self.allocate(role,'overlap') for role in ('omega-agent','omega-agent-b')}
        commands={'omega-agent':'remember The synthetic azure badge is in chest cedar','omega-agent-b':'remember The synthetic violet prism is in crate maple'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs={role:pool.submit(self.run,command,role,indices[role]) for role,command in commands.items()}
            values={role:job.result() for role,job in jobs.items()}
        self.report['overlap']=dict(results=values,independent_native_callers=True)
        for role in indices:
            for query,answer in [('synthetic azure badge','chest cedar'),('synthetic violet prism','crate maple')]:
                self.evaluate(self.run('query '+query,role,indices[role]),dict(required=[answer]))
        self.save();return indices

    def handoffs(self,indices):
        # Inbound tasks allocate their own trusted sessions. Observe the actual
        # sender session; never pretend the recipient's seed UUID is its caller.
        for sender,recipient in [('A','B'),('B','A')]:
            role='omega-agent' if sender=='A' else 'omega-agent-b'
            index=indices[role];sid=self.ids[role][index]
            sent=self.object(self.run('delegate '+recipient+' synthetic silver prism storage',role,index))
            until=min(self.end,time.monotonic()+max(0,(sent['deadline']-time.time()*1000)/1000)+8)
            while True:
                observed=self.call(role,'observe',sid,'--content')
                returned=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==sent['deadline']]
                if (returned and returned[0]['state']=='complete') or time.monotonic()>until:break
                time.sleep(1)
            self.report['scenarios'].append(dict(scenario='two-agent-'+sender+'-'+recipient,task=sent,
                observations={role:observed},passed=bool(returned and returned[0]['state']=='complete')));self.save()
            require(returned and returned[0]['state']=='complete','NOT_AVAILABLE')
            if sender=='A':self.report['inspection']=self.object(self.run('inspect-atom '+sent['task'],role,index));self.save()
        # Exact source reuse and contrary assessment are distinct from priority.
        # Handles come from captured native results, never an answer list.
        import re
        index=indices['omega-agent'];memory=self.object(self.report['overlap']['results']['omega-agent'])['memory']['handle']
        page=self.object(self.run('episodes current',session=index))
        source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
        revisions=[self.run(command+' '+memory+' '+source,session=index) for command in ('support','support','contradict')]
        require('REVISION-SUCCESS' in revisions[0] and 'retained-alternative' in revisions[2],'NOT_AVAILABLE')
        before=self.run('query synthetic azure badge',session=index)
        self.run('promote '+memory,session=index)
        after=self.run('query synthetic azure badge',session=index)
        truth=lambda value:re.findall(r"_apostrophe_stv_apostrophe_, ([0-9.e+-]+), ([0-9.e+-]+)",value)
        require(truth(before) and truth(before)==truth(after),'CONFLICT')
        self.report['cognition']=dict(revisions=revisions,before_promotion=before,after_promotion=after,
            displayed_truth_unchanged_by_priority=True,source_reuse_not_independent_evidence=True);self.save()
        # Task-created sessions may remain active with complete retained input.
        # Closing is an explicit operator action, never deletion or forgiveness.
        for role in indices:
            for row in self.call(role,'list'):
                if row['state']=='active':self.call(role,'close',row['session'],'--identity','close-before-private-'+row['session'])

    def private(self):
        from .reference_ops import PYTHON
        for role in ('omega-agent','omega-agent-b'):
            index=self.allocate(role,'private-cognition','private');label='A' if role=='omega-agent' else 'B'
            content='The synthetic private '+label+' canary is in cabinet birch'
            written=self.object(self.run('remember '+content,role,index));handle=written['memory']['handle']
            self.evaluate(self.run('query synthetic private '+label+' canary',role,index),dict(required=['cabinet birch']))
            page=self.object(self.run('episodes current',role,index))
            source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
            self.run('support '+handle+' '+source,role,index);self.run('promote '+handle,role,index)
            self.evaluate(self.run('query synthetic private '+label+' canary',role,index),dict(required=['cabinet birch']))
            current=self.current(role,index)
            self.report.setdefault('private_cases',[]).append(dict(role=role,index=index,current=current,native_steps=6));self.save()
            if role=='omega-agent':
                # Explicit operator diagnostic supplied only synthetic attack
                # guesses. B's selected credential still has no private access.
                req=dict(session=self.ids['omega-agent-b'][0],private_scope=current['scope'],private_ref=written['memory']['target']['payload'],
                    private_snapshot=current['retained']['view']['snapshot'],private_episode=current['history']['episode'],
                    private_context='synthetic-native-assessment',canary='synthetic private A canary')
                self.report['private_denials']=json.loads(self.op.k('exec','-i','omega-agent-b-0','--',PYTHON,'-m',
                    'integration.single_node.sustained_private_checks',data=json.dumps(req),timeout=190));self.save()
                q=dict(profile='operator-approved-synthetic-projection/1',identity='exact-approved-synthetic-projection',session=self.ids[role][index],
                    source=written['memory']['target']['payload'],content='cabinet birch',approval_record='phase3-operator-exact-synthetic-output',recipient_scope=self.report['private_denials']['shared_scope'])
                script='import json,sys;from integration.single_node.preview_operator import projection;print(json.dumps(projection(json.load(sys.stdin))))'
                first=json.loads(self.op.k('exec','-i',role+'-0','--',PYTHON,'-c',script,data=json.dumps(q),timeout=45))
                replay=json.loads(self.op.k('exec','-i',role+'-0','--',PYTHON,'-c',script,data=json.dumps(q),timeout=45))
                require(first==replay,'CONFLICT');self.report['approved_projection']=first;self.save()
            self.close(role,index)

    def counterfactual(self):
        index=self.allocate('omega-agent','counterfactual')
        # Query discovers the original handle in this session; no controller
        # insertion of target references into the consumer's search operation.
        self.evaluate(self.run('query '+DATASETS['new']['query'],session=index),DATASETS['new'])
        current=self.current('omega-agent',index)
        memory=self.report['first_memory']['memory']['handle']
        updated=self.object(self.run('update '+memory+' '+DATASETS['changed']['fact'],session=index))
        self.evaluate(self.run('query '+DATASETS['changed']['query'],session=index),DATASETS['changed'])
        self.evaluate(self.run('query '+DATASETS['absent']['query'],session=index),DATASETS['absent'])
        self.run('pin premise REASSESS after explicit source supersession',session=index)
        context=self.run('task-context',session=index)
        decision=stopped_premise(current['lifecycle']['head'],self.current('omega-agent',index)['lifecycle']['head'],context)
        self.report['premise_reassessment']=decision;self.save();require(decision['task_pass'],'CONFLICT')
        self.close('omega-agent',index)


def qualify(operator,destination):
    runner=Runner(operator,destination)
    try:
        operator.owned();runner.report['preflight']=operator.preflight();runner.save()
        runner.sustained();indices=runner.overlap();runner.handoffs(indices);runner.private();runner.counterfactual();runner.report['status']='PASS'
    except BaseException as error:
        runner.report.update(status='FAILED',error=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:runner.save()
    return dict(status=runner.report['status'],report=str(runner.root/'report.json'),additional_live_generations=0)
