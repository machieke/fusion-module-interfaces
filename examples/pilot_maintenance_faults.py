"""Finite real-owner maintenance faults for the synthetic handover drill.

The only writes are existing authenticated owner requests, explicit Helm test
configuration, and a real provider-process SIGKILL. Diagnostics read the owning
pod's retained accounting; they never supply a tool result or modify a journal.
"""
import base64,copy,json,time,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import yaml
from fusion.contracts import require
from integration.single_node.reference_ops import PYTHON
from integration.single_node.preview_recovery_qualification import Recovery


def diagnostic(op):
    result=Recovery.__new__(Recovery);result.op=op;return result


def settings(op,chart,value,path,role,stage,helm):
    selected=copy.deepcopy(value);selected['testFaultsEnabled']=True
    selected['components'].setdefault(role,{}).setdefault('config',{})['test']={} if stage is None else {'pause_at':stage}
    path=Path(path);path.write_text(yaml.safe_dump(selected,sort_keys=False));path.chmod(0o600)
    helm(op,chart,path);return selected


def paused(op,role,stage,deadline):
    probe=diagnostic(op);end=time.monotonic()+max(0,(deadline-time.time_ns()//1000000)/1000)
    while time.monotonic()<end:
        value=probe.read(role,'pause.json')
        if value:
            require(value['stage']==stage,'CONFLICT');return value
        time.sleep(.25)
    require(False,'NOT_AVAILABLE')


def kill(op,role):
    namespace=op.owned();require(namespace['metadata'].get('labels',{}).get('omega.pilot/task'),'UNAUTHORIZED')
    before=json.loads(op.k('get','pod',role+'-0','-o','json'))
    old=before['status']['containerStatuses'][0]['restartCount'];pid=before['metadata']['uid']
    workload=json.loads(op.k('get','statefulset',role,'-o','json'))
    require(before['metadata']['namespace']==op.namespace and
        all(v['metadata']['labels'].get('app.kubernetes.io/instance')=='omega' and v['metadata']['labels'].get('app.kubernetes.io/name')==role for v in (before,workload)) and
        any(x.get('controller') is True and x['kind']=='StatefulSet' and x['name']==role and x['uid']==workload['metadata']['uid'] for x in before['metadata']['ownerReferences']),'UNAUTHORIZED')
    require(before['spec']['nodeName']=='omega-fusion-k3s','UNSUPPORTED_PROFILE')
    container=before['status']['containerStatuses'][0];identity=container['containerID'].removeprefix('containerd://')
    require(len(identity)==64 and all(c in '0123456789abcdef' for c in identity),'CONFLICT')
    # Linux namespace PID1 ignores an in-namespace SIGKILL. Use the pinned
    # single-node runtime administrative port, after binding the actual task.
    command=['docker','exec','omega-fusion-k3s','ctr','-n','k8s.io']
    actual=json.loads(op.command(command+['containers','info',identity]));labels=actual['Labels']
    require(labels['io.kubernetes.pod.namespace']==op.namespace and labels['io.kubernetes.pod.uid']==pid and
        labels['io.kubernetes.pod.name']==role+'-0' and labels['io.kubernetes.container.name']==role and
        actual['Image']==container['image'],'UNAUTHORIZED')
    require(op.owned()['metadata']['uid']==namespace['metadata']['uid'] and
        json.loads(op.k('get','pod',role+'-0','-o','json'))['status']['containerStatuses'][0]['containerID']==container['containerID'],'CONFLICT')
    op.command(command+['tasks','kill','--signal','SIGKILL',identity],timeout=15)
    end=time.monotonic()+100
    while time.monotonic()<end:
        after=json.loads(op.k('get','pod',role+'-0','-o','json'))
        c=after.get('status',{}).get('containerStatuses',[{}])[0]
        if c.get('restartCount',0)>old and c.get('ready'):
            require(after['metadata']['uid']==pid and c['lastState']['terminated']['exitCode']==137,'CONFLICT')
            return dict(namespace_uid=namespace['metadata']['uid'],pod_uid=pid,container_id=identity,image=container['imageID'],
                mechanism='verified-task-owned-containerd-SIGKILL',before_restarts=old,after_restarts=c['restartCount'],exit_code=137)
        time.sleep(.5)
    require(False,'NOT_AVAILABLE')


def unknown_model(op,runner,chart,values,root,helm,record):
    index=runner.allocate('omega-agent','handover-unknown-reservation');sid=runner.ids['omega-agent'][index]
    require(diagnostic(op).read('fusion-model','pause.json') is None,'CONFLICT')
    settings(op,chart,values,root/'model-pause.yaml','fusion-model','after_model_reservation',helm)
    identity='unknown-'+str(uuid.uuid4());command='pin unknown Preserve this interrupted reservation'
    accepted=runner.call('omega-agent','submit',sid,'--identity',identity,'--text',command,'--assignment','synthetic-task')
    record('unknown-accepted',dict(session=sid,identity=identity,accepted=accepted))
    marker=paused(op,'fusion-model','after_model_reservation',accepted['deadline']);record('unknown-reserved-pause',marker)
    before=diagnostic(op).model_accounting(sid)
    require(len(before)==1 and before[0]['reserved']==1 and before[0]['response_sha256'] is None and before[0]['captured_ms'] is None,'CONFLICT')
    record('unknown-original-accounting',before);record('unknown-process-kill',kill(op,'fusion-model'))
    settings(op,chart,values,root/'model-disarmed.yaml','fusion-model',None,helm)
    after=diagnostic(op).model_accounting(sid);require(after==before,'CONFLICT')
    record('unknown-post-kill-accounting',after)
    # Closing admission is not a claim that an admitted external effect did not
    # happen. Neither this procedure nor activation retries its model slot.
    closed=runner.close('omega-agent',index);record('unknown-closed',closed)
    observed=runner.call('omega-agent','observe',sid,'--content')
    row=next(x for x in observed['inputs'] if x['id']==identity)
    require(row['deadline']==accepted['deadline'] and row['accepted']==accepted['accepted'],'CONFLICT')
    record('unknown-input-observation',row)
    return dict(session=sid,identity=identity,accounting=before,original_input=row,
                backend_generation=False,reservation_spent=True,automatic_retry=False)


SEARCH_CALL='''import json,sys
from pathlib import Path
from fusion.preview_memory_services import Client
q=json.load(sys.stdin);cfg=json.loads(Path('/run/fusion/templates/shared/search-active.json').read_bytes())
print(json.dumps(Client(cfg,'search',inline=True).call(q['operation'],*q['args'])))
'''


def search_call(op,operation,*args,timeout=70):
    return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',SEARCH_CALL,
        data=json.dumps(dict(operation=operation,args=args)),timeout=timeout))


def search_cleanup(op,runner,session,chart,values,root,helm,record,resume_after_inert_kill=None):
    # A paused generation holds the Search owner lock. Continuing its explicit
    # fault must use the exact previously captured selection, not a fresh
    # current-owner request that would block behind that lock.
    selected=(runner.report['source_observations'][-1]['value']['retained']['view']['snapshot']
        if resume_after_inert_kill is not None else runner.current('omega-agent',session)['retained']['view']['snapshot'])
    from fusion.preview_vector_contracts import PROFILE as ACTIVE
    require(selected['profile']==ACTIVE,'UNSUPPORTED_PROFILE')
    if resume_after_inert_kill is not None:
        require(set(resume_after_inert_kill)=={'key','deadline_ms','source','lifecycle'} and
            resume_after_inert_kill['source']==selected['head'] and resume_after_inert_kill['lifecycle']==selected['lifecycle'],'CONFLICT')
        key=resume_after_inert_kill['key'];deadline=resume_after_inert_kill['deadline_ms']
        require(time.time_ns()//1000000>deadline and diagnostic(op).read('fusion-search','pause.json')['stage']=='after_index_write','CONFLICT')
        record('search-process-kill',kill(op,'fusion-search'))
        record('search-original-call',dict(outcome='LOST_RESPONSE',continuation='same-expired-reservation-no-resubmission'))
    else:
        require(diagnostic(op).read('fusion-search','pause.json') is None,'CONFLICT')
        settings(op,chart,values,root/'search-pause.yaml','fusion-search','after_index_write',helm)
        key='pilot-unpublished-'+str(uuid.uuid4());deadline=time.time_ns()//1000000+30000
        record('search-build-accepted-input',dict(key=key,deadline_ms=deadline,source=selected['head'],lifecycle=selected['lifecycle']))
        with ThreadPoolExecutor(max_workers=1) as pool:
            call=pool.submit(search_call,op,'build',selected['head'],selected['lifecycle'],key,deadline)
            record('search-unpublished-pause',paused(op,'fusion-search','after_index_write',deadline))
            record('search-process-kill',kill(op,'fusion-search'))
            try:call.result(timeout=70)
            except (RuntimeError,TimeoutError) as error:record('search-original-call',dict(outcome='LOST_RESPONSE',type=type(error).__name__))
            else:require(False,'CONFLICT')
    settings(op,chart,values,root/'search-disarmed.yaml','fusion-search',None,helm)
    require(search_call(op,'published',selected['head'],selected['lifecycle'],key) is None,'CONFLICT')
    # An owner-local, read-only diagnostic identifies the accepted maintenance
    # receipt. The authenticated owner issues its plan and independently checks
    # the exact generation, expiry, authoritative source and retention pins.
    code='''import json,sys
from pathlib import Path
key=json.load(sys.stdin)['key'];cfg=json.loads(Path('/run/fusion/owner.json').read_bytes())
root=Path(cfg['active_memory']['root'])/'active-search';rows=[]
for p in root.glob('*/maintenance.json'):
 v=json.loads(p.read_bytes())
 if v['intent']['key']==key:rows.append({'generation':p.parent.name,'receipt':v})
print(json.dumps(rows))'''
    receipts=json.loads(op.k('exec','-i','fusion-search-0','--',PYTHON,'-c',code,data=json.dumps(dict(key=key))))
    require(len(receipts)==1 and receipts[0]['receipt']['intent']['deadline_ms']==deadline and receipts[0]['receipt']['attempts']==1,'CONFLICT')
    record('search-retained-unpublished-receipt',receipts[0])
    while time.time_ns()//1000000<=deadline:time.sleep(min(.25,max(.001,(deadline-time.time_ns()//1000000)/1000)))
    from fusion.pilot_search_cleanup import PROFILE
    invoke='import json,sys;from integration.single_node.integrated_search_operator import request;print(json.dumps(request(json.load(sys.stdin))))'
    def maintenance(operation,args):
        return json.loads(op.k('exec','-i','fusion-search-0','--',PYTHON,'-c',invoke,data=json.dumps(dict(profile=PROFILE,scope=selected['head']['scope_ref'],operation=operation,args=args)),timeout=70))
    plan=maintenance('planCleanup',[selected['lifecycle'],[receipts[0]['generation']]])
    record('search-cleanup-plan',plan);identity='cleanup-'+key
    result=maintenance('applyCleanup',[selected['lifecycle'],plan,identity]);require(result['state']=='complete' and result['removed_logical_bytes']>0,'CONFLICT')
    require(maintenance('observeCleanup',[selected['lifecycle'],plan,identity])==result,'CONFLICT');record('search-cleanup',result)
    require(search_call(op,'ready',selected)=={'ready':True},'CONFLICT')
    # A new intentional generation consumes its own identity and deadline. It
    # reads the declared immutable feed; the expired reservation is not reset.
    rebuilt=search_call(op,'build',selected['head'],selected['lifecycle'],'pilot-rebuilt-'+str(uuid.uuid4()),time.time_ns()//1000000+60000)
    require(rebuilt['generation']!=receipts[0]['generation'] and rebuilt['head']==selected['head'],'CONFLICT')
    record('search-authoritative-rebuild',dict(snapshot=rebuilt,old_retained_ready=search_call(op,'ready',selected),new_ready=search_call(op,'ready',rebuilt),original_attempts_retained=1))
    return result


def application_cleanup(op,session,record,programme_end):
    from examples.pilot_endurance import cleanup
    # The session-close receipt precedes native-child exit. Reuse the bounded
    # observation wait; the original programme limit is never renewed and the
    # mutating cleanup request is issued only once.
    def progress(stage,value):
        if stage in ('inventory','plan'):record('application-derived-'+stage,value)
    observed=cleanup(op,'omega-agent',session,programme_end,progress=progress)
    require(observed['apply_calls']==1,'NOT_AVAILABLE')
    plan=observed['plan'];result=observed['result'];require(result['state']=='complete','CONFLICT')
    record('application-derived-cleanup',result)
    record('application-derived-cleanup-observations',dict(inventory_observations=observed['inventory_observations'],
        apply_calls=observed['apply_calls'],replay_exact=observed['replay_exact']))
    # Independent source hydration is repeated after removal. No fallback cache
    # is reconstructed by operator-provided text.
    roots=[c['reference'] for c in plan['plan']['candidates'] if c['kind']=='history-materialization']
    code='''import json,sys
from pathlib import Path
from fusion.preview_atoms import client
from fusion.preview_native_history import read_body
from fusion.contracts import canonical,digest
q=json.load(sys.stdin);cfg=json.loads((Path('/run/fusion/sessions')/q['session']/'history-atoms.json').read_bytes());atoms=client(cfg)
print(json.dumps([{'reference':r,'body_sha256':digest(canonical(read_body(atoms,r)))} for r in q['references']]))'''
    remaining=programme_end-time.monotonic();require(remaining>0,'DEADLINE_EXCEEDED')
    result=json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',code,data=json.dumps(dict(session=session,references=roots)),timeout=min(90,remaining)))
    record('history-source-rehydration-after-cleanup',result);return result


def historical_refusals(original,replacement,session):
    source=next(x for x in original.workloads() if x['metadata']['name']=='fusion-model')
    name=next(x['secret']['secretName'] for x in source['spec']['template']['spec']['volumes'] if x['name']=='secrets')
    secret=json.loads(original.k('get','secret',name,'-o','json'))
    stale=base64.b64decode(secret['data']['caller-A-token']).decode().strip()
    export='''import json,sys,sqlite3
from fusion.contracts import require
q=json.load(sys.stdin)
with sqlite3.connect('file:/state/model.sqlite?mode=ro',uri=True) as db:
 db.execute('PRAGMA query_only=ON');rows=db.execute('SELECT intent FROM model_calls WHERE session=?',(q['session'],)).fetchall()
require(len(rows)==1,'CONFLICT');print(rows[0][0])'''
    accepted=json.loads(replacement.k('exec','-i','fusion-model-0','--',PYTHON,'-c',export,data=json.dumps(dict(session=session)),timeout=20))
    code='''import json,sys
from pathlib import Path
from fusion.preview_transport import invoke
from fusion import preview_model_contracts as c
from fusion.model_transport import checked
from fusion.contracts import require,ContractError
q=json.load(sys.stdin);accepted=q['accepted'];client=json.loads(Path('/run/fusion/templates/shared/model.json').read_bytes())
require(accepted['session']==q['session'] and accepted['principal']==client['principal'] and accepted['scope']==client['scope'],'UNAUTHORIZED')
wire=dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation='observe',intent=accepted);c.request(wire)
actual=checked(wire,invoke(client,'/preview/model',wire),contracts=c);require(actual['state']=='unknown' and actual['reserved']==1,'CONFLICT')
result={'old_observation':'unknown','spent_reservations':actual['reserved']}
for label,operation,token in [('stale_credential','observe',q['stale']),('historical_completion','complete',client['credential'])]:
 wire['operation']=operation
 try:invoke(dict(client,credential=token),'/preview/model',wire)
 except ContractError as error:
  require(error.code=='UNAUTHORIZED','CONFLICT');result[label]=error.code
 else:require(False,'CONFLICT')
print(json.dumps(result))'''
    # Owner-local read exports the selected synthetic accepted intent to its
    # original caller. Only that caller originates authenticated module traffic;
    # provider-to-self egress is neither required nor opened for this probe.
    return json.loads(replacement.k('exec','-i','omega-agent-0','--',PYTHON,'-c',code,
        data=json.dumps(dict(session=session,accepted=accepted,stale=stale)),timeout=45))


def retained_payload_readback(op,shared,private):
    """Post-activation observations over current declared storage ports.

    These are historical payload references, not answer refs supplied to a
    native query. The owner/client verifies their exact immutable bytes. The
    private subject is then refused using the other caller's actual credential.
    """
    code='''import json,sys
from pathlib import Path
from fusion.preview_atoms import client
from fusion.contracts import require,digest,ContractError
q=json.load(sys.stdin);result={}
for template,ref in q.items():
 cfg=json.loads((Path('/run/fusion/templates')/template/'history-atoms.json').read_bytes())
 require(cfg['scope']==ref['scope_ref'],'UNAUTHORIZED');item=client(cfg).get(ref)
 require(item.ref==ref and digest(item.bytes)==ref['digest'],'CONFLICT')
 result[template]={'bytes':len(item.bytes),'exact_reference_and_payload':True}
print(json.dumps(result))'''
    positive=json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',code,
        data=json.dumps(dict(shared=shared,private=private)),timeout=65))
    deny='''import json,sys
from pathlib import Path
from fusion.preview_atoms import client
from fusion.contracts import require,ContractError
ref=json.load(sys.stdin);cfg=json.loads(Path('/run/fusion/templates/shared/history-atoms.json').read_bytes());cfg['scope']=ref['scope_ref']
try:client(cfg).get(ref)
except ContractError as error:
 require(error.code=='UNAUTHORIZED','CONFLICT');print(json.dumps({'code':error.code,'private_payload_returned':False}))
else:require(False,'CONFLICT')'''
    refused=json.loads(op.k('exec','-i','omega-agent-b-0','--',PYTHON,'-c',deny,data=json.dumps(private),timeout=35))
    return dict(current_authorized_payloads=positive,other_principal=refused,
                observation='POST_ACTIVATION_DECLARED_AUTHENTICATED_PORTS',new_native_inputs=0)


def packet_refusal(original,replacement,task):
    service=json.loads(replacement.k('get','service','fusion-model','-o','json'))
    address=service['spec']['clusterIP'];port=next(x['port'] for x in service['spec']['ports'])
    # The same known-running target first accepts a connection from its current
    # namespace. The retired namespace probe has no PVC, credentials or work.
    positive='import socket,sys;s=socket.create_connection((sys.argv[1],int(sys.argv[2])),2);s.close();print("REACHABLE")'
    require(replacement.k('exec','omega-agent-0','--',PYTHON,'-c',positive,address,str(port)).strip()=='REACHABLE','NOT_AVAILABLE')
    image=next(x for x in original.workloads() if x['metadata']['name']=='omega-agent')['spec']['template']['spec']['containers'][0]['image']
    name='pilot-retired-network-'+str(uuid.uuid4())[:8]
    code='''import socket,json,sys
try:
 s=socket.create_connection((sys.argv[1],int(sys.argv[2])),3);s.close();print(json.dumps({'blocked':False}));sys.exit(2)
except OSError as e:
 print(json.dumps({'blocked':True,'error_type':type(e).__name__,'errno':e.errno}))'''
    pod=dict(apiVersion='v1',kind='Pod',metadata=dict(name=name,namespace=original.namespace,labels={'omega.pilot/task':task}),spec=dict(restartPolicy='Never',automountServiceAccountToken=False,
        securityContext=dict(runAsNonRoot=True,runAsUser=10001,runAsGroup=10001,seccompProfile=dict(type='RuntimeDefault')),
        containers=[dict(name='probe',image=image,imagePullPolicy='Never',command=[PYTHON,'-c',code,address,str(port)],
            resources=dict(requests=dict(cpu='10m',memory='32Mi'),limits=dict(cpu='100m',memory='64Mi')),
            securityContext=dict(allowPrivilegeEscalation=False,capabilities=dict(drop=['ALL']),readOnlyRootFilesystem=True))]))
    try:
        original.apply(pod);end=time.monotonic()+35;observations=[];uid=None
        while time.monotonic()<end:
            observed=json.loads(original.k('get','pod',name,'-o','json',timeout=min(5,max(.1,end-time.monotonic()))))
            require(observed['metadata']['namespace']==original.namespace and observed['metadata']['labels'].get('omega.pilot/task')==task,'UNAUTHORIZED')
            if uid is None:uid=observed['metadata']['uid']
            require(observed['metadata']['uid']==uid,'CONFLICT')
            phase=observed.get('status',{}).get('phase');observations.append(phase)
            if phase in ('Succeeded','Failed'):break
            time.sleep(min(.25,max(0,end-time.monotonic())))
        require(observations and observations[-1]=='Succeeded','NOT_AVAILABLE')
        result=json.loads(original.k('logs',name));require(result['blocked'] is True,'UNAUTHORIZED')
        return dict(target_service='fusion-model',positive_current_namespace='REACHABLE',retired_namespace=result,phase_observations=observations,
            policy='EXACT_DENY_ALL',interpretation='current retirement boundary; no attribution to a single network rule')
    finally:original.k('delete','pod',name,'--ignore-not-found','--wait=true')
