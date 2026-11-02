"""Finite deployed preview recovery checks using the existing session API.

Each case admits one new synthetic input. Replacements recover that occurrence;
they never renew a deadline, clear a fault marker, or refund a reservation.
Run after the native qualifier, on the same fresh task-owned namespace.
"""
import argparse,json,time,uuid
from pathlib import Path
import yaml
from fusion.contracts import canonical,require
from .reference_ops import Operator,PYTHON
from .preview_qualification import Runner


class Recovery:
    def __init__(self,op,values,chart,output,native):
        self.op,self.values_path,self.chart=op,Path(values),str(chart)
        self.values=yaml.safe_load(self.values_path.read_text())
        self.root=Path(output);self.root.mkdir(parents=True,exist_ok=False)
        self.native=json.loads(Path(native).read_text())
        require(self.native['namespace']==op.namespace and self.native['status']=='PASS','NOT_AVAILABLE')
        self.api=Runner.__new__(Runner);self.api.op=op
        self.ids={r:list(self.native[r]['sessions']) for r in ('omega-agent','omega-agent-b')}
        self.report=dict(namespace=op.namespace,classification='REAL_DEPLOYED_NATIVE_WITH_RECORDED_MODEL',
            additional_live_generations=0,maximum_new_inputs=8,cases=[])
        self.end=time.monotonic()+1800
    def save(self): (self.root/'report.json').write_bytes(canonical(self.report))
    def code(self,role,source):
        return self.op.k('exec','-i',role+'-0','--',PYTHON,'-',data=source,timeout=30)
    def read(self,role,name):
        return json.loads(self.code(role,'from pathlib import Path;p=Path("/state")/'+repr(name)+';print(p.read_text() if p.exists() else "null")'))
    def pod(self,role):
        value=json.loads(self.op.k('get','pod',role+'-0','-o','json'))
        return dict(uid=value['metadata']['uid'],volumes=[x['persistentVolumeClaim']['claimName'] for x in value['spec']['volumes'] if 'persistentVolumeClaim' in x],
            images=[x['imageID'] for x in value['status']['containerStatuses']])
    def accounting(self,role,sid,identity):
        # Operator-only, bounded read-only observation inside this owner's pod.
        # No provider consumer reads a foreign journal and no payload is emitted.
        source="""import json,sqlite3
from pathlib import Path
p=Path('/state/sessions')/SID/'caller.sqlite'
result=[]
if p.exists():
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if {'preview_native_inputs','app_occurrences','preview_dispatch_budget'}<=tables:
   result=[dict(r) for r in db.execute('SELECT o.id,o.turn,o.position,o.deadline,o.done,coalesce(b.attempts,0) AS attempts FROM app_occurrences o JOIN preview_native_inputs i ON i.turn=o.turn LEFT JOIN preview_dispatch_budget b ON b.occurrence=o.id WHERE i.identity=? ORDER BY o.position LIMIT 8',(IDENTITY,))]
print(json.dumps(result))
""".replace('SID',repr(sid)).replace('IDENTITY',repr(identity))
        return json.loads(self.code(role,source))
    def arm(self,role,knob,value):
        marker='pause.json' if knob=='pause_at' else 'response-dropped.json'
        require(self.read(role,marker) is None,'CONFLICT')
        self.values['testFaultsEnabled']=True
        self.values['components'].setdefault(role,{}).setdefault('config',{})['test']={knob:value}
        self.values_path.write_text(yaml.safe_dump(self.values,sort_keys=False))
        self.op.command(['helm','upgrade','omega',self.chart,'--kubeconfig',self.op.kubeconfig,'--kube-context',self.op.context,
            '--namespace',self.op.namespace,'-f',str(self.values_path),'--wait','--timeout','180s'],timeout=190)
        return marker
    def model_accounting(self,sid):
        # Sanitized operator observation, in the model owner's own pod. Response
        # bodies and accepted prompts never leave the owner in this diagnostic.
        source="""import json,sqlite3,hashlib
from pathlib import Path
p=Path('/state/model.sqlite');result=[]
if p.exists():
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  if db.execute("SELECT 1 FROM sqlite_master WHERE name='model_calls'").fetchone():
   for row in db.execute('SELECT id,slot,reserved,captured_ms,response,failure_code FROM model_calls WHERE session=? ORDER BY slot',(SESSION,)):
    item=dict(row);response=item.pop('response');item['response_sha256']=None if response is None else hashlib.sha256(response.encode()).hexdigest();result.append(item)
print(json.dumps(result))
""".replace('SESSION',repr(sid))
        return json.loads(self.code('fusion-model',source))
    def observe(self,role,sid,identity):
        page=self.api.call(role,'observe',sid,'--content')
        while True:
            found=[x for x in page['inputs'] if x['id']==identity]
            if found:return found[0]
            require(page['next_after'] is not None,'NOT_FOUND')
            page=self.api.call(role,'observe',sid,'--content','--after',str(page['next_after']))
    def replace(self,roles):
        before={r:self.pod(r) for r in roles}
        self.op.k('delete','pod',*[r+'-0' for r in roles],'--grace-period=1','--wait=false')
        for role in roles:
            until=time.monotonic()+45
            while time.monotonic()<until:
                try:
                    if self.pod(role)['uid']!=before[role]['uid']:break
                except (RuntimeError,KeyError):pass
                time.sleep(.25)
            self.op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=90s',timeout=100)
        after={r:self.pod(r) for r in roles}
        require(all(after[r]['uid']!=before[r]['uid'] and after[r]['volumes']==before[r]['volumes'] and after[r]['images']==before[r]['images'] for r in roles),'CONFLICT')
        return dict(before=before,after=after)
    def case(self,name,role,session,command,owner,knob,stage):
        require(time.monotonic()<self.end and len(self.report['cases'])<8,'OVERLOADED')
        item=dict(name=name,caller=role,owner=owner,command=command,started_ms=time.time_ns()//1000000)
        self.report['cases'].append(item);self.save()
        try:
            marker=self.arm(owner,knob,stage);sid=self.ids[role][session];identity='recovery-'+str(uuid.uuid4())
            accepted=self.api.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
            item['accepted']=accepted;self.save()
            until=min(self.end,time.monotonic()+max(0,(accepted['deadline']-time.time()*1000)/1000)+8)
            fired=None
            while time.monotonic()<until:
                fired=self.read(owner,marker)
                if fired:break
                time.sleep(.25)
            require(fired is not None,'NOT_AVAILABLE');item['fault_marker']=fired
            item['dispatch_before_replacement']=self.accounting(role,sid,identity);self.save()
            item['model_before_replacement']=self.model_accounting(sid);self.save()
            # The same native application recovers its own durable occurrence.
            # A lost provider reply requires no new input or alternate provider.
            roles=list(dict.fromkeys((owner,role)));item['replacement']=self.replace(roles);self.save()
            while time.monotonic()<until:
                observed=self.observe(role,sid,identity)
                if observed['state']=='complete':break
                time.sleep(1)
            observed=self.observe(role,sid,identity);item['observed']=observed
            after=self.accounting(role,sid,identity);item['dispatch_after_replacement']=after
            item['model_after_replacement']=self.model_accounting(sid)
            for old in item['model_before_replacement']:
                current=next(x for x in item['model_after_replacement'] if x['id']==old['id'])
                require(current['reserved']>=old['reserved'] and current['reserved']<=1,'CONFLICT')
                if old['response_sha256'] is not None:require(current==old,'CONFLICT')
            if name=='model-captured-response':
                require(item['model_before_replacement']==item['model_after_replacement']
                    and item['model_before_replacement'][-1]['response_sha256'] is not None,'CONFLICT')
            for old in item['dispatch_before_replacement']:
                current=next(x for x in after if x['id']==old['id'])
                require(current['deadline']==old['deadline'] and old['attempts']<=current['attempts']<=2,'CONFLICT')
            require(observed['deadline']==accepted['deadline'] and observed['accepted']==accepted['accepted'],'CONFLICT')
            require(observed['state']=='complete','NOT_AVAILABLE')
            duplicate=self.api.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
            require(duplicate['id']==identity and duplicate['deadline']==accepted['deadline'] and duplicate['sequence']==accepted['sequence'] and duplicate['state']=='complete','CONFLICT')
            item.update(duplicate_receipt=duplicate,status='PASS',deadline_renewals=0)
        except Exception as error:
            item.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1024:]))
        finally:item['finished_ms']=time.time_ns()//1000000;self.save()
    def run(self):
        self.op.owned();handles=self.native['returned_handles']
        self.case('native-input-capture','omega-agent-b',0,'pin recovery Preserve the original occurrence',
            'omega-agent-b','pause_at','after_session_input_capture')
        self.case('workspace-effect','omega-agent',1,'append-file scratch.txt Recovery appends this line once',
            'fusion-execution','pause_at','after_workspace_effect')
        self.case('relation-reply-loss','omega-agent',0,'link '+handles['memory']+' '+handles['source'],
            'fusion-relations','drop_response_operation','assertRelation')
        self.case('model-captured-response','omega-agent-b',0,'pin captured Recover the recorded captured proposal',
            'fusion-model','pause_at','after_model_provider_capture')
        self.case('lifecycle-before-publication','omega-agent-b',1,'remember The synthetic recovery marker is in crate hazel',
            'fusion-storage','pause_at','after_lifecycle_commit')
        # Native reads, not an expected provider result injected by the runner,
        # establish the file effect and current memory visibility after recovery.
        self.readback('workspace-single-append','omega-agent',1,'read-file scratch.txt','Recovery appends this line once')
        self.readback('lifecycle-native-read','omega-agent-b',1,'query synthetic recovery marker','crate hazel')
        self.report['status']='PASS' if all(x['status']=='PASS' for x in self.report['cases']) else 'FAILED_REQUIRED_CASE'
        self.save()

    def readback(self,name,role,session,command,expected):
        require(len(self.report['cases'])<8 and time.monotonic()<self.end,'OVERLOADED')
        item=dict(name=name,caller=role,command=command);self.report['cases'].append(item);self.save()
        try:
            sid=self.ids[role][session];identity='readback-'+str(uuid.uuid4())
            accepted=self.api.call(role,'submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
            item['accepted']=accepted;self.save()
            until=min(self.end,time.monotonic()+max(0,(accepted['deadline']-time.time()*1000)/1000)+8)
            while time.monotonic()<until:
                observed=self.observe(role,sid,identity)
                if observed['state']=='complete':break
                time.sleep(1)
            item['observed']=self.observe(role,sid,identity)
            require(item['observed']['state']=='complete','NOT_AVAILABLE')
            require(item['observed']['result']['projection'].count(expected)==1,'CONFLICT')
            item['status']='PASS'
        except Exception as error:item.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1024:]))
        finally:self.save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','output','native'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=Recovery(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.output,a.native);r.run()
    require(r.report['status']=='PASS','NOT_AVAILABLE')
if __name__=='__main__':main()
