"""Separate V13 operator supplement; never part of the frozen handover driver.

The original native memory capture selects an authoritative AtomStorage payload.
Only a fresh Attention context is changed. One native-policy baseline and one
reserved adjustment are exercised; no Omega input or model call is admitted.
"""
import argparse,copy,json,math,subprocess,time,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.placement import freeze,verify_installed,files_hash

PROFILE='operator-single-container-suspension/1'
ROLE='fusion-attention'
CTR=['docker','exec','omega-fusion-k3s','ctr','-n','k8s.io']

TEMPLATE=r'''
import json,sqlite3
from contextlib import closing
from pathlib import Path
from fusion.contracts import canonical,require
from fusion.lookup_contracts import identity
from integration.single_node.sustained_runtime import template_files,runtime_digest

def selected_template(owner_file,session):
 identity(session);owner=json.loads(Path(owner_file).read_bytes())['native_sessions']
 require(owner['handover']['generation']==2,'UNAUTHORIZED')
 with closing(sqlite3.connect(Path(owner['database']).resolve().as_uri()+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  row=db.execute('SELECT * FROM sustained_allocations WHERE session=?',(session,)).fetchone()
  saved=db.execute('SELECT principal,scope,state FROM preview_sessions WHERE id=?',(session,)).fetchone()
  require(row is not None and saved is not None and saved['state']=='closed','UNAUTHORIZED')
  require(row['template']=='g2-shared' and row['principal']==saved['principal']==owner['principal'] and saved['scope']==owner['scope'],'UNAUTHORIZED')
  from fusion.pilot_writer_fence import historical
  require(historical(db,session) is None,'UNAUTHORIZED')
  selected=owner['allocation']['templates'].get(row['template'])
  require(selected is not None and canonical(selected).decode()==row['frozen'] and selected['scope']==saved['scope'],'CONFLICT')
  recipe=owner['runtime_templates'][row['template']]
  files=template_files(recipe['directory'])
  require(runtime_digest(files,recipe['ca_file'])==selected['runtime_digest'],'CONFLICT')
 return Path(recipe['directory'])
'''

PORT=TEMPLATE+r'''
import sys
from fusion.contracts import ContractError
from fusion.cognitive_services import Remote,client_configuration
from fusion.preview_atoms import client
from fusion import promotion_contracts as c,vector_contracts as v
q=json.load(sys.stdin)
directory=selected_template('/run/fusion/owner.json',q['session'])
cfg,frozen=client_configuration(directory/'attention-client.json');port=Remote(cfg,'attention')
try:
 if q['operation']=='bind':
  atoms=json.loads((directory/'memory-atoms.json').read_bytes());stored=client(atoms).get(q['payload'])
  require(stored.content_type==v.PAYLOAD,'CONFLICT');payload=v.payload(json.loads(stored.bytes),cfg['scope'],q['corpus'])
  request=c.request(dict(profile=c.PROFILE,selection=port.selection(),principal=frozen['principal'],scope=cfg['scope'],
   context=q['context'],id=q['identity'],kind='adjust',targets=[payload['uuid']],delta=1,deadline_ms=q['deadline_ms'],limit=1))
  result=c.binding(port.call('bind',request),request)
 else:
  bound=c.binding(q['binding']);result=port.call(q['operation'],bound)
  if result is not None:c.receipt(result,bound)
 print(json.dumps(dict(status='PASS',value=result)))
except ContractError as error:print(json.dumps(dict(status='REFUSED',code=error.code)))
'''

DIAGNOSTIC=r'''
import json,sqlite3,sys
from pathlib import Path
from fusion.contracts import canonical,digest,require
q=json.load(sys.stdin);cfg=json.loads(Path('/run/fusion/cognitive-owner.json').read_bytes())
require(q['scope']==cfg['scope'],'UNAUTHORIZED');root=Path(cfg['root']).resolve()
require(root.is_relative_to(Path('/state')),'UNAUTHORIZED')
context=digest(canonical([q['principal'],q['scope'],q['context']]))
with sqlite3.connect((root/'attention.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
 rows=[]
 for identity in q['identities']:
  key=digest(canonical([q['principal'],q['scope'],q['context'],identity]))
  row=db.execute('SELECT value,calls,result FROM bindings WHERE id=? AND context=?',(key,context)).fetchone()
  rows.append(None if row is None else dict(binding=json.loads(row['value']),calls=row['calls'],result=json.loads(row['result']) if row['result'] else None))
 state=db.execute('SELECT revision,water FROM contexts WHERE id=?',(context,)).fetchone();require(state is not None,'NOT_FOUND')
 saved=db.execute('SELECT state FROM history WHERE context=? AND revision=?',(context,state['revision'])).fetchone()
 print(json.dumps(dict(bindings=rows,revision=state['revision'],water=state['water'],state=json.loads(saved[0]))))
'''


def selected_task(op,role=ROLE):
    namespace=op.owned();require(namespace['metadata'].get('labels',{}).get('omega.pilot/task'),'UNAUTHORIZED')
    pod=json.loads(op.k('get','pod',role+'-0','-o','json'))
    workload=json.loads(op.k('get','statefulset',role,'-o','json'))
    require(pod['metadata']['namespace']==op.namespace and pod['spec']['nodeName']=='omega-fusion-k3s','UNAUTHORIZED')
    require(len(pod['spec']['containers'])==len(pod['status']['containerStatuses'])==1,'UNSUPPORTED_PROFILE')
    for obj in (pod,workload):
        require(obj['metadata']['labels'].get('app.kubernetes.io/instance')=='omega' and obj['metadata']['labels'].get('app.kubernetes.io/name')==role,'UNAUTHORIZED')
    require(any(x.get('controller') is True and x['kind']=='StatefulSet' and x['name']==role and x['uid']==workload['metadata']['uid'] for x in pod['metadata']['ownerReferences']),'UNAUTHORIZED')
    container=pod['status']['containerStatuses'][0];cid=container['containerID'].removeprefix('containerd://')
    require(len(cid)==64 and all(c in '0123456789abcdef' for c in cid),'CONFLICT')
    actual=json.loads(op.command(CTR+['containers','info',cid],timeout=10));labels=actual['Labels']
    require(all(labels.get(k)==v for k,v in {'io.kubernetes.pod.namespace':op.namespace,'io.kubernetes.pod.uid':pod['metadata']['uid'],
        'io.kubernetes.pod.name':role+'-0','io.kubernetes.container.name':role}.items()) and actual['Image']==container['image'],'UNAUTHORIZED')
    return dict(namespace_uid=namespace['metadata']['uid'],pod_uid=pod['metadata']['uid'],container_id=cid,
                image=container['imageID'],restart_count=container['restartCount'],role=role)


def task_state(op,cid):
    rows=[line.split() for line in op.command(CTR+['tasks','list'],timeout=10).splitlines()]
    found=[row for row in rows if row and row[0]==cid]
    require(len(found)<=1,'CONFLICT');return found[0][-1] if found else 'ABSENT'


def suspend(op,binding,deadline_ms,*,end,save,clock=time.time_ns,monotonic=time.monotonic,sleep=time.sleep):
    """Resume only the captured CID on every exit; never follow a replacement."""
    require(selected_task(op)==binding,'CONFLICT')
    row=dict(binding=binding,selected_deadline_ms=deadline_ms,status='RUNNING');save(row)
    try:
        op.command(CTR+['tasks','pause',binding['container_id']],timeout=10)
        row['paused_ms']=clock()//1000000;row['state_after_pause']=task_state(op,binding['container_id']);save(row)
        require(row['state_after_pause']=='PAUSED','NOT_AVAILABLE')
        started=monotonic();until=max(started+20,started+max(0,(deadline_ms+2000-row['paused_ms'])/1000))
        require(until<end,'DEADLINE_EXCEEDED')
        row['suspension_observations']=[]
        while monotonic()<until:
            state=task_state(op,binding['container_id'])
            row['suspension_observations'].append(dict(state=state,elapsed_seconds=monotonic()-started));save(row)
            if state!='PAUSED':break
            sleep(min(1,until-monotonic()))
        row['after_wait_ms']=clock()//1000000;row['suspended_seconds']=monotonic()-started
        require(row['after_wait_ms']>deadline_ms and row['suspended_seconds']>=20,'CONFLICT')
        row['state_before_resume']=task_state(op,binding['container_id']);save(row)
    finally:
        try:state=task_state(op,binding['container_id'])
        except BaseException as error:
            state='UNKNOWN';row['cleanup_observation_failure']=type(error).__name__
        row['cleanup_original_state']=state
        if state in ('PAUSED','UNKNOWN'):
            try:
                op.command(CTR+['tasks','resume',binding['container_id']],timeout=10)
                row['original_resumed']=True
            except BaseException as error:
                row['original_resumed']=False;row['resume_failure']=type(error).__name__
        else:row['original_resumed']=False
        row['replacement_targeted']=False;save(row)
    require('resume_failure' not in row,'NOT_AVAILABLE')
    row['status']='PASS';save(row);return row


def freeze_plan(handover,values,images,chart):
    raw=Path(handover).read_bytes();report=json.loads(raw);require(report['status']=='PASS' and report['writer_generation']==2,'NOT_AVAILABLE')
    root=Path(handover).parent;native=json.loads((root/'replacement-native/report.json').read_bytes())
    require(len(native['inputs'])==4 and all(x['observed']['state']=='complete' for x in native['inputs']),'CONFLICT')
    session=native['inputs'][0]['session'];text=next(x['value'] for x in report['steps'] if x['step']=='new-memory').replace('_quote_','"')
    memory=json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
    return dict(profile=PROFILE,namespace=report['replacement'],context='synthetic-suspension-'+str(uuid.uuid4()),
        identity='suspension-'+str(uuid.uuid4()),session=session,payload=memory['memory']['target']['payload'],corpus=memory['snapshot']['corpus'],
        handover=str(Path(handover).resolve()),handover_sha256=digest(raw),values=str(Path(values).resolve()),values_sha256=digest(Path(values).read_bytes()),
        images=str(Path(images).resolve()),images_sha256=digest(Path(images).read_bytes()),chart=str(Path(chart).resolve()),chart_sha256=files_hash(chart),
        source_manifest_sha256=json.loads(Path(images).read_bytes())['source_manifest_sha256'],helper_sha256=digest(Path(__file__).read_bytes()),
        maximum_seconds=300,cleanup_reserved_seconds=75,operation_deadline_ms=15000,minimum_suspension_seconds=20,
        maximum_new_omega_inputs=0,additional_live_generations=0,model_calls=0,maximum_adjust_invocations=3,
        baseline='actual native-policy adjustment through existing Attention port',old_plan_changed=False)


def qualify(op,plan,directory):
    require(plan['profile']==PROFILE and plan['namespace']==op.namespace,'UNAUTHORIZED')
    for name in ('values','images','handover'):require(digest(Path(plan[name]).read_bytes())==plan[name+'_sha256'],'CONFLICT')
    require(digest(Path(__file__).read_bytes())==plan['helper_sha256'],'CONFLICT')
    require(files_hash(plan['chart'])==plan['chart_sha256'],'CONFLICT')
    require((plan['maximum_seconds'],plan['cleanup_reserved_seconds'],plan['operation_deadline_ms'],
        plan['minimum_suspension_seconds'],plan['maximum_new_omega_inputs'],plan['additional_live_generations'])==(300,75,15000,20,0,0),'UNSUPPORTED_PROFILE')
    root=Path(directory);root.mkdir(mode=0o700,parents=True,exist_ok=False);end=time.monotonic()+300;work_end=end-75
    report=dict(profile=PROFILE,status='RUNNING',plan=plan,started_ms=time.time_ns()//1000000,steps=[],additional_live_generations=0)
    def save():
        path=root/'report.json';path.write_bytes(canonical(report));path.chmod(0o600)
    def note(name,value):report['steps'].append(dict(step=name,value=value));save();return value
    def remaining(maximum,cleanup=False):
        value=min(maximum,(end if cleanup else work_end)-time.monotonic());require(value>1,'DEADLINE_EXCEEDED');return value
    observing=False
    def port(operation,**args):
        q=dict(session=plan['session'],operation=operation,**args)
        return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',PORT,data=json.dumps(q),timeout=remaining(25,observing)))
    def diagnostic(bound):
        q={k:bound['request'][k] for k in ('scope','principal','context')};q['identities']=[plan['identity']+'-baseline',plan['identity']]
        return json.loads(op.k('exec','-i',ROLE+'-0','--',PYTHON,'-c',DIAGNOSTIC,data=json.dumps(q),timeout=remaining(20,observing)))
    values=yaml.safe_load(Path(plan['values']).read_bytes());selected=copy.deepcopy(values);changed=False
    def helm(path,cleanup=False):
        budget=remaining(70,cleanup);return op.command(['helm','upgrade','omega',plan['chart'],'--kubeconfig',op.kubeconfig,'--kube-context',op.context,
            '--namespace',op.namespace,'-f',str(path),'--wait','--timeout',str(max(1,math.floor(budget)-5))+'s'],timeout=budget)
    def marker():
        return json.loads(op.k('exec',ROLE+'-0','--',PYTHON,'-c','from pathlib import Path;p=Path("/state/pause.json");print(p.read_text() if p.exists() else "null")',timeout=remaining(10)))
    save()
    try:
        note('installed',verify_installed(freeze(plan['chart'],op.namespace,values,json.loads(Path(plan['images']).read_bytes())),op))
        require(marker() is None,'CONFLICT');require(not selected['components'][ROLE].get('config',{}).get('test'),'CONFLICT')
        common={k:plan[k] for k in ('context','payload','corpus')}
        baseline=note('baseline-bind',port('bind',identity=plan['identity']+'-baseline',deadline_ms=time.time_ns()//1000000+15000,**common))
        require(baseline['status']=='PASS','NOT_AVAILABLE')
        result=note('baseline-native-adjust',port('adjust',binding=baseline['value']));require(result['status']=='PASS' and result['value']['value']==1.,'CONFLICT')
        selected['testFaultsEnabled']=True;selected['components'][ROLE].setdefault('config',{})['test']={'pause_at':'after_priority_reservation'}
        armed=root/'armed-values.yaml';armed.write_text(yaml.safe_dump(selected,sort_keys=False));armed.chmod(0o600);changed=True;helm(armed)
        bound=note('suspended-bind',port('bind',identity=plan['identity'],deadline_ms=time.time_ns()//1000000+15000,**common));require(bound['status']=='PASS','NOT_AVAILABLE');bound=bound['value']
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending=pool.submit(port,'adjust',binding=bound)
            observed=None;until=min(work_end,time.monotonic()+10)
            while time.monotonic()<until:
                observed=marker()
                if observed:break
                time.sleep(.1)
            require(observed and observed['stage']=='after_priority_reservation','NOT_AVAILABLE');note('reservation-marker',observed)
            before=note('reserved-owner-state',diagnostic(bound));require(before['bindings'][1]['calls']==1 and before['bindings'][1]['result'] is None,'CONFLICT')
            current=selected_task(op)
            suspend(op,current,bound['request']['deadline_ms'],end=work_end,save=lambda value:(report.update(suspension=copy.deepcopy(value)),save()))
            try:note('interrupted-adjust-reply',pending.result(timeout=remaining(25)))
            except (RuntimeError,subprocess.TimeoutExpired) as error:note('interrupted-adjust-reply',dict(status='TRANSPORT_UNAVAILABLE',type=type(error).__name__))
        # The existing barrier never resumes computation. Retire its process,
        # keeping the marker, reservation and original binding on its own PVC.
        helm(plan['values'],cleanup=True);changed=False;observing=True
        after=note('owner-state-after-restart',diagnostic(bound));require(after==before,'CONFLICT')
        observed=note('same-binding-observe',port('observe',binding=bound));require(observed==dict(status='PASS',value=None),'CONFLICT')
        refused=note('expired-same-binding-adjust',port('adjust',binding=bound));require(refused==dict(status='REFUSED',code='DEADLINE_EXCEEDED'),'CONFLICT')
        require(diagnostic(bound)==before,'CONFLICT');note('baseline-retained',port('observe',binding=baseline['value']))
        require(report['steps'][-1]['value']==result,'CONFLICT');require(time.monotonic()<end,'DEADLINE_EXCEEDED')
        report.update(status='PASS',new_omega_inputs=0,spent_evaluations=1,new_evaluations_after_expiry=0,deadline_renewals=0,reservation_refunds=0)
    except BaseException as error:report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:
        if changed:
            try:helm(plan['values'],cleanup=True);report['original_configuration_restored']=True
            except BaseException as error:report['configuration_restore_failure']=dict(type=type(error).__name__,detail=str(error)[-500:])
        else:report['original_configuration_restored']=True
        report['finished_ms']=time.time_ns()//1000000;save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['freeze','run'])
    for name in ('handover','values','images','chart','output','plan','directory','kubeconfig','context','namespace'):p.add_argument('--'+name)
    a=p.parse_args()
    if a.action=='freeze':
        value=freeze_plan(a.handover,a.values,a.images,a.chart);path=Path(a.output)
        with path.open('x') as f:f.write(json.dumps(value,sort_keys=True,indent=2)+'\n')
        path.chmod(0o600);print(json.dumps(dict(status='FROZEN_NOT_EXECUTED',sha256=digest(path.read_bytes()))))
    else:
        value=qualify(Operator(a.kubeconfig,a.context,a.namespace),json.loads(Path(a.plan).read_bytes()),a.directory)
        print(json.dumps(dict(status=value['status'],additional_live_generations=0)))

if __name__=='__main__':main()
