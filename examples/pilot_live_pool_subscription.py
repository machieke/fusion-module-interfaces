"""Finite retained-browser observation supplement; installed operator Python -I.

No runtime implementation change, native submission or generation. A trusted
operator temporarily applies one same-principal credential to an owner-local
policy; this is NOT automatic Secret reload. Every exit restores the selected
Secret key and original owner policy, or explicitly reports failed restoration.
The private prospective plan binds existing session/archive/provider identities.
"""
import argparse,base64,hashlib,json,os,select,subprocess,time,uuid
from pathlib import Path
from fusion.contracts import canonical,require
from integration.single_node.reference_ops import Operator,PYTHON

PROFILE='pilot-live-pool-subscription-qualification/1'
MAX_READS=40

POLICY=r'''
import json,os,sys
from pathlib import Path
q=json.load(sys.stdin);p=Path('/run/fusion/owner.json');backup=Path('/run/fusion/pilot-pool-policy-original.json')
def write(raw):
 t=p.with_suffix('.pilot-pending')
 with t.open('wb') as f:os.chmod(t,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
 t.replace(p)
raw=p.read_bytes();v=json.loads(raw);actor=q['actor']
if q['operation']=='prepare':
 assert not backup.exists() and v['principals'][actor]['credential']==q['old']
 with backup.open('xb') as f:os.chmod(backup,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
 print(json.dumps({'prepared':True,'principal_preserved':True}))
elif q['operation']=='apply':
 original=backup.read_bytes();assert raw==original
 v['principals'][actor]['credential']=q['new'];changed=json.dumps(v,sort_keys=True,separators=(',',':')).encode()
 check=json.loads(changed);check['principals'][actor]['credential']=q['old'];assert check==json.loads(original)
 write(changed);print(json.dumps({'applied':True,'only_selected_credential_changed':True}))
elif q['operation']=='restore':
 if not backup.exists():print(json.dumps({'restored':True,'change_was_not_prepared':True}))
 else:
  original=backup.read_bytes();check=json.loads(raw);assert check['principals'][actor]['credential'] in (q['old'],q['new'])
  check['principals'][actor]['credential']=q['old'];assert check==json.loads(original)
  write(original);assert p.read_bytes()==original;backup.unlink();print(json.dumps({'restored':True,'exact_original_bytes':True}))
else:raise ValueError('UNSUPPORTED_OPERATION')
'''

CLIENT=r'''
import http.client,json,sys,time,uuid
from pathlib import Path
from fusion import https_pool
from fusion.preview_transport import invoke
from fusion.contracts import canonical,digest,require,ContractError
q=json.loads(sys.stdin.readline());cfg=json.loads(Path('/config/browser.json').read_bytes());target=cfg['users'][q['user']]['targets'][q['role']]
require(target['scope']==q['scope'],'UNAUTHORIZED');ep=target['endpoint'];require(ep['host']==q['role']+'.'+q['namespace']+'.svc.cluster.local' and ep['port']==8443,'CONFLICT');old=q['old'];new=q['new'];sid=q['session'];actor='browser-'+q['user']
require(Path(target['credential_file']).read_text().strip()==new,'CONFLICT')
reads=0;controls=0;pool_reads=0;sub=q['subscription'];expires=None;last=None
physical={'read_requests':0,'control_requests':0};original_request=http.client.HTTPSConnection.request
def counted_request(self,method,url,body=None,headers=None,**kwargs):
 require(method=='POST' and url in ('/preview/session','/preview/subscriptions','/preview/providers'),'UNSUPPORTED_OPERATION')
 parsed=json.loads(body);key='read_requests' if parsed['operation'] in ('binding','observe','read','snapshot','selected','plan','inspect') else 'control_requests'
 physical[key]+=1;require(physical['read_requests']<=29 and physical['control_requests']<=5,'OVERLOADED')
 return original_request(self,method,url,body,headers or {},**kwargs)
http.client.HTTPSConnection.request=counted_request
end=time.time_ns()//1000000+300000

def wire(path,profile,operation,body,token=old,**extra):
 global reads,controls,pool_reads
 read=operation in ('binding','observe','read','snapshot','selected','plan','inspect')
 if read:reads+=1;require(reads<=29,'OVERLOADED')
 else:controls+=1;require(controls<=5,'OVERLOADED')
 request=dict(id=str(uuid.uuid4()),profile=profile,operation=operation,body=body,**extra)
 deadline=min(end,time.time_ns()//1000000+15000)
 if pool_deadline is not None:deadline=min(deadline,pool_deadline)
 result=invoke(dict(endpoint=ep,credential=token),path,request,deadline)
 require(result['id']==request['id'] and result['profile']==profile and result['request_digest']==digest(canonical(request)) and result['actor']==actor,'CONFLICT')
 if path=='/preview/session':require(result['principal']==target['principal'],'UNAUTHORIZED')
 return result['value']
def session(op,body,token=old):return wire('/preview/session','omega-native-sessions/3',op,dict(session=sid,**body),token)
def subscription(op,body,token=old,action=None):return wire('/preview/subscriptions','application-commit-subscription/1',op,body,token,subscription=sub,session=sid,action=action)
def emit(event,**v):print(json.dumps(dict(event=event,**v)),flush=True)
def command(expected):
 value=json.loads(sys.stdin.readline());require(value=={'operation':expected},'CONFLICT')
pool_deadline=None
baseline=session('observe',dict(content=True,after=0));require(baseline['session']==sid and baseline['scope']==q['scope'] and baseline['principal']==target['principal'] and baseline['complete'] and baseline['next_after'] is None and all(x['state']=='complete' for x in baseline['inputs']),'NOT_AVAILABLE')
created=subscription('create',dict(session=sid,lifetime_ms=300000),action=q['identity']+'/create');expires=created['expires_ms'];require(created['subscription']==sub and created['session']==sid and created['created_ms']+300000==expires,'CONFLICT');initial=subscription('read',dict(limit=16))
require(initial['cursor']==0 and initial['subscription']==sub and initial['session']==sid,'CONFLICT');selected=wire('/preview/providers','trusted-provider-lifecycle/2','selected',dict(session=sid))
require(q['provider'] in selected and selected[q['provider']]['record']['scope']==q['scope'],'UNAUTHORIZED')
plan=wire('/preview/providers','trusted-provider-lifecycle/2','plan',dict(provider=q['provider']));require(plan['actions']>0,'NOT_AVAILABLE')
sealed=wire('/preview/providers','trusted-provider-lifecycle/2','seal',dict(provider=q['provider'],identity=q['identity']+'/seal',head=plan['head']))
emit('DISCONNECTED',subscription_created=True,subscription_expires_ms=expires,cursor=0,registry_seal=sealed,read_calls=reads,control_calls=controls)
command('provider-restarted-and-archive-read')
after=subscription('read',dict(limit=16));require(after['cursor']==0 and after['expires_ms']==expires,'CONFLICT')
snapshot=subscription('snapshot',{});require(snapshot['snapshot']['inputs']==baseline['inputs'],'CONFLICT')
if after['gap']:
 subscription('rebase',snapshot['rebase'],action=q['identity']+'/rebase')
else:
 require(after['next']==after['head'],'OVERLOADED');subscription('ack',dict(source=after['source'],cursor=after['next']),action=q['identity']+'/ack')
caught=subscription('read',dict(limit=16));require(caught['events']==[] and caught['cursor']==caught['head'] and caught['expires_ms']==expires,'CONFLICT')
https_pool.configure(dict(https_pool.LIMITS,idle_ms=1000));pool_deadline=min(end,time.time_ns()//1000000+15000)
session('binding',{});pool_reads+=1;require(len(https_pool._entries)==1,'CONFLICT');row=https_pool._entries[0];sock=row['connection'].sock;require(sock is not None,'NOT_AVAILABLE');socket_before=(sock.fileno(),sock.getsockname(),sock.getpeername())
emit('OLD_TOKEN_SOCKET_ESTABLISHED',pool_read_calls=pool_reads,subscription_gap=after['gap'],subscription_caught_up=True,socket_identity=socket_before)
denied=False
for _ in range(16):
 require(time.time_ns()//1000000<pool_deadline,'DEADLINE_EXCEEDED')
 require(row in https_pool._entries and row['connection'].sock is sock,'CONFLICT')
 before_count=row['count']
 try:session('binding',{});pool_reads+=1
 except ContractError as error:
  pool_reads+=1;require(error.code=='UNAUTHORIZED' and row['count']==before_count+1,'CONFLICT');denied=True;break
 time.sleep(.4)
require(denied and row['connection'].sock is None and row not in https_pool._entries,'CONFLICT')
try:subscription('read',dict(limit=16));pool_reads+=1
except ContractError as error:pool_reads+=1;require(error.code=='UNAUTHORIZED','CONFLICT')
else:require(False,'CONFLICT')
session('binding',{},new);pool_reads+=1;new_view=session('observe',dict(content=True,after=0),new);pool_reads+=1;require(new_view['inputs']==baseline['inputs'],'CONFLICT')
current=subscription('read',dict(limit=16),new);pool_reads+=1;require(current['cursor']==caught['cursor'] and current['expires_ms']==expires and current['subscription']==sub,'CONFLICT')
subscription('close',{},new,action=q['identity']+'/close');require(pool_reads<=38,'OVERLOADED')
emit('READY_TO_RESTORE',old_socket_retained_across_policy_change=True,former_token='UNAUTHORIZED',former_subscription_token='UNAUTHORIZED',same_principal_new_token_capture_exact=True,subscription_closed=True,original_subscription_expires_ms=expires,pool_read_calls=pool_reads,read_calls=reads,control_calls=controls)
https_pool.close();https_pool.configure(None);pool_deadline=None
command('original-policy-and-secret-restored')
restored=session('observe',dict(content=True,after=0));require(restored['inputs']==baseline['inputs'],'CONFLICT');pool_reads+=1
require(physical['read_requests']==reads and physical['control_requests']==controls,'CONFLICT')
emit('PASS',physical_http_request_method_calls=physical,server_receipt_count='NOT_INFERRED_FROM_CLIENT_REQUEST',capture_count=len(baseline['inputs']),captures_exact_after_restoration=True,pool_read_calls=pool_reads,read_calls=reads,control_calls=controls,native_submissions=0,additional_live_generations=0)
'''

ARCHIVE=r'''
import json,sys,time
from pathlib import Path
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_read
from fusion.ports import Mutation
from fusion.archive_contracts import PROFILE
from fusion.contracts import require
q=json.load(sys.stdin);cfg=json.loads(Path('/run/fusion/cognitive-owner.json').read_bytes());component=json.loads(Path('/config/component.json').read_bytes())
d=next(descriptor_read(x) for x in cfg['catalogue'] if PROFILE in x['profiles'])
port=AtomFeedClient(Endpoint(component['peers']['fusion-storage'],component['https_port'],'/secrets/ca.crt'),cfg['principals']['archive-operator']['credential'],'archive-operator',q['scope'],d,deadline_ms=q['deadline_ms'],composition=cfg['composition'],feed_profile=cfg['feed_profile'])
receipt=port.observeArchive(Mutation(q['scope'],q['mutation']));require(receipt is not None and receipt['found'] is True and receipt['scope_ref']==q['scope'],'NOT_FOUND');item=port.get(q['payload']);require(item.ref==q['payload'],'CONFLICT')
print(json.dumps(dict(existing_archive_receipt=True,authoritative_payload_verified=True,read_calls=2,archive_mutations=0,cold_path='NOT_INFERRED')))
'''


def validate_plan(v,source):
    require(type(v) is dict and set(v)=={'profile','identity','namespace','role','user','session','scope','provider','archive','source_sha256','runtime_source_sha256','packet_sha256','images','subscription','limits'},'INVALID_ARGUMENT')
    require(v['profile']==PROFILE and v['source_sha256']==source,'CONFLICT')
    require(v['namespace']=='omega-ref-pilot-browser11' and v['role']=='omega-agent' and v['user']=='operator','UNAUTHORIZED')
    require(v['scope'].startswith('synthetic-') and str(uuid.UUID(v['session']))==v['session'],'UNAUTHORIZED')
    require(v['limits']==dict(total_seconds=600,secret_projection_seconds=120,subscription_ms=300000,socket_phase_ms=15000,pool_read_sends=22,subscription_and_registry_read_calls=7,closed_session_list_reads=2,control_calls=5,archive_read_calls=4,total_module_calls=40,provider_replacements=1),'UNSUPPORTED_PROFILE')
    require(v['identity']==v['subscription'] and v['identity'].startswith('post-handover-pool-') and len(v['identity'])<=80,'INVALID_ARGUMENT')
    require(set(v['archive'])=={'scope','payload','mutation'} and v['archive']['scope'].startswith('synthetic-') and v['archive']['payload']['scope_ref']==v['archive']['scope'],'UNAUTHORIZED')
    require(set(v['images'])=={'omega-agent','omega-agent-b','fusion-execution','fusion-storage','fusion-messaging','fusion-embedding','fusion-search','fusion-episodes','fusion-beliefs','fusion-attention','fusion-relations','fusion-model','omega-workbench'} and all('@sha256:' in x for x in v['images'].values()),'INVALID_ARGUMENT')
    return v


def receive(process,deadline):
    left=deadline-time.monotonic();require(left>0,'DEADLINE_EXCEEDED')
    ready,_,_=select.select([process.stdout],[],[],left);require(bool(ready),'DEADLINE_EXCEEDED')
    line=process.stdout.readline();require(line and len(line)<=131072,'NOT_AVAILABLE');return json.loads(line)


def run(op,plan,output):
    source=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();validate_plan(plan,source)
    out=Path(output);require(not out.exists(),'CONFLICT');out.mkdir(mode=0o700,parents=True)
    (out/'plan.json').write_bytes(canonical(plan));os.chmod(out/'plan.json',0o600)
    report=dict(profile=PROFILE,status='RUNNING',source_sha256=source,plan_sha256=hashlib.sha256(canonical(plan)).hexdigest(),events=[],restoration={},additional_live_generations=0,manual_live_policy_application=True,automatic_secret_reload=False)
    def save():
        p=out/'report.json';p.write_bytes(canonical(report));os.chmod(p,0o600)
    save();start=time.monotonic();end=start+600;client=None;old=None;new=None;secret_changed=False;policy_prepared=False;restored=False;resumed=False;error_stream=None;initial_secret_data=None;initial_configmaps=None
    def owner(operation):
        return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-c',POLICY,data=json.dumps(dict(operation=operation,actor='browser-'+plan['user'],old=old,new=new)),timeout=15))
    def secret(value):
        current=json.loads(op.k('get','secret','omega-agent-tls-auth','-o','json'))['data']
        require(set(current)==set(initial_secret_data) and all(current[k]==v for k,v in initial_secret_data.items() if k!=key),'CONFLICT')
        require(base64.b64decode(current[key]).decode() in (old,new),'CONFLICT')
        op.k('patch','secret','omega-agent-tls-auth','--type','merge','--patch-file','/dev/stdin',data=json.dumps(dict(data={key:base64.b64encode(value.encode()).decode()})),timeout=15)
    def projection(value):
        until=min(end,time.monotonic()+120)
        code="import json,sys;from pathlib import Path;q=json.load(sys.stdin);print(json.dumps({'matches':Path(q['path']).read_text().strip()==q['expected']}))"
        while time.monotonic()<until:
            both=[]
            for target,path in [('omega-agent-0','/secrets/'+key),('deployment/omega-workbench','/credentials/omega-agent/'+key)]:
                q=json.loads(op.k('exec','-i',target,'--',PYTHON,'-c',code,data=json.dumps(dict(path=path,expected=value)),timeout=10));both.append(q['matches'])
            if all(both):return dict(projected=True,owner_and_gateway=True)
            time.sleep(1)
        require(False,'DEADLINE_EXCEEDED')
    def restore():
        nonlocal restored
        if policy_prepared:report['restoration']['policy']=owner('restore');save()
        if secret_changed:
            secret(old);actual=json.loads(op.k('get','secret','omega-agent-tls-auth','-o','json'))['data']
            require(actual==initial_secret_data,'CONFLICT');report['restoration']['secret_control_plane_exact_material']=True;save()
        restored=True
    try:
        op.owned();owners=op.workloads();gateways=op.stateless_workloads();workloads={x['metadata']['name']:x for x in [*owners,*gateways]}
        require(all(workloads[k]['spec']['template']['spec']['containers'][0]['image']==v for k,v in plan['images'].items()),'CONFLICT')
        require(len(owners)==12 and len(gateways)==1 and all(x['spec']['replicas']==0 for x in workloads.values()),'CONFLICT')
        require(not json.loads(op.k('get','pods','-o','json'))['items'],'CONFLICT')
        initial_configmaps={x['metadata']['name']:x['data'] for x in json.loads(op.k('get','configmaps','-o','json'))['items']}
        resumed=True
        for name in workloads:op.k('scale','deployment' if name=='omega-workbench' else 'statefulset',name,'--replicas=1')
        op.k('wait','--for=condition=Ready','pod','-l','app.kubernetes.io/instance=omega','--timeout=120s',timeout=125)
        rows=[]
        for role in ('omega-agent','omega-agent-b'):
            rows+=json.loads(op.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.preview_operator','list'))
        require(len(rows)==10 and all(x['state']=='closed' for x in rows),'CONFLICT')
        report['preflight']=dict(closed_sessions=10,session_list_read_calls=2,original_execution_window_extended=False);save()
        state=json.loads(op.k('get','secret','omega-agent-tls-auth','-o','json'));initial_secret_data=state['data'];key='browser-'+plan['user']+'-token';old=base64.b64decode(state['data'][key]).decode();new=__import__('secrets').token_urlsafe(32)
        policy_prepared=True;report['owner_policy_prepared']=owner('prepare');secret_changed=True;secret(new);report['temporary_secret_projection']=projection(new);save()
        args=['kubectl','--kubeconfig',op.kubeconfig,'--context',op.context,'-n',op.namespace,'exec','-i','deployment/omega-workbench','--',PYTHON,'-u','-c',CLIENT]
        error_stream=(out/'client-stderr.log').open('w');os.chmod(out/'client-stderr.log',0o600)
        client=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=error_stream,text=True,bufsize=1)
        client.stdin.write(json.dumps(dict(plan,old=old,new=new))+'\n');client.stdin.flush()
        event=receive(client,min(end,time.monotonic()+30));report['events'].append(event);save();require(event['event']=='DISCONNECTED','CONFLICT')
        sub_end=time.monotonic()+max(0,(event['subscription_expires_ms']-time.time()*1000)/1000)
        archive=dict(plan['archive'],deadline_ms=min(event['subscription_expires_ms'],time.time_ns()//1000000+30000))
        report['archive_before']=json.loads(op.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',ARCHIVE,data=json.dumps(archive),timeout=35));save()
        before=json.loads(op.k('get','pod','fusion-storage-0','-o','json'));op.k('delete','pod','fusion-storage-0','--wait=true','--timeout=60s',timeout=65);op.k('wait','--for=condition=Ready','pod/fusion-storage-0','--timeout=60s',timeout=65)
        after=json.loads(op.k('get','pod','fusion-storage-0','-o','json'));require(before['metadata']['uid']!=after['metadata']['uid'] and before['spec']['containers'][0]['image']==after['spec']['containers'][0]['image'] and before['spec']['volumes']==after['spec']['volumes'],'CONFLICT');report['provider_replacement']=dict(uid_changed=True,image_and_volumes_exact=True);save()
        archive['deadline_ms']=min(event['subscription_expires_ms'],time.time_ns()//1000000+30000);report['archive_after']=json.loads(op.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',ARCHIVE,data=json.dumps(archive),timeout=35));save()
        client.stdin.write('{"operation":"provider-restarted-and-archive-read"}\n');client.stdin.flush();event=receive(client,min(end,sub_end,time.monotonic()+30));report['events'].append(event);save();require(event['event']=='OLD_TOKEN_SOCKET_ESTABLISHED','CONFLICT')
        report['manual_owner_policy_apply']=owner('apply');save()
        event=receive(client,min(end,sub_end,time.monotonic()+15));report['events'].append(event);save();require(event['event']=='READY_TO_RESTORE','CONFLICT')
        restore();client.stdin.write('{"operation":"original-policy-and-secret-restored"}\n');client.stdin.flush();event=receive(client,min(end,time.monotonic()+15));report['events'].append(event);save();require(event['event']=='PASS' and event['pool_read_calls']<=22 and event['read_calls']+event['control_calls']+6<=40,'CONFLICT')
        client.wait(timeout=5);require(client.returncode==0,'NOT_AVAILABLE');report['restoration']['secret_projection']=projection(old);report.update(status='PASS',elapsed_seconds=time.monotonic()-start,native_submissions=0,deadline_renewals=0,reservation_refunds=0)
    except BaseException as error:
        report.update(status='FAILED_RETAINED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:
        if not restored:
            try:restore()
            except BaseException as error:report['restoration']['failure']=dict(type=type(error).__name__,code=getattr(error,'code',None))
        if client is not None and client.poll() is None:
            client.terminate()
            try:client.wait(timeout=3)
            except subprocess.TimeoutExpired:client.kill();client.wait(timeout=3)
        if error_stream is not None:error_stream.close()
        if resumed:
            try:
                op.quiesce();pods=json.loads(op.k('get','pods','-o','json'))['items'];pvcs=json.loads(op.k('get','pvc','-o','json'))['items']
                require(not pods and len(pvcs)==12,'CONFLICT')
                current_configmaps={x['metadata']['name']:x['data'] for x in json.loads(op.k('get','configmaps','-o','json'))['items']}
                require(current_configmaps==initial_configmaps,'CONFLICT');report['quiescence']=dict(remaining_pods=0,retained_owner_pvcs=12,configmap_contents_exact=True)
            except BaseException as error:
                report['status']='FAILED_RETAINED';report['quiescence_failure']=dict(type=type(error).__name__,code=getattr(error,'code',None));save();raise
        report['elapsed_seconds_including_quiescence']=time.monotonic()-start
        if report['elapsed_seconds_including_quiescence']>600:report['window_exceeded']=True;report['status']='FAILED_RETAINED'
        save()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','namespace','plan','output'):parser.add_argument('--'+name,required=True)
    parser.add_argument('--context',default='default');a=parser.parse_args();plan=json.loads(Path(a.plan).read_bytes());require(plan['namespace']==a.namespace,'CONFLICT')
    result=run(Operator(a.kubeconfig,a.context,a.namespace),plan,a.output)
    print(json.dumps(dict(status=result['status'],additional_live_generations=0,private_report_retained=True)))
if __name__=='__main__':main()
