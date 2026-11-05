"""Fixed task-owned outage observations; no native admission or effect replay.

The caller inspects only its own selected configuration/captured inputs. Every
provider read uses a declared authenticated port. No alternate endpoint, clock,
owner database or new result substitutes for an unavailable dependency.
"""
import json,time
from pathlib import Path
from fusion.contracts import require
from integration.single_node.reference_ops import PYTHON

OBSERVE=r'''
import json,sqlite3,sys
from pathlib import Path
from fusion.contracts import ContractError,require
role,sid=sys.argv[1:3]
app=json.loads((Path('/run/fusion/sessions')/sid/'application.json').read_bytes())
dbfile=Path('/state/sessions')/sid/'caller.sqlite'
client_calls=0
try:
 if role=='fusion-embedding':
  from fusion.embedding_composition import configuration,binding
  from fusion import embedding_contracts as c
  with sqlite3.connect(dbfile.as_uri()+'?mode=ro',uri=True) as db:
   db.execute('PRAGMA query_only=ON')
   row=db.execute('SELECT intent FROM app_memory_vectors WHERE result IS NOT NULL ORDER BY rowid LIMIT 1').fetchone()
  require(row is not None,'NOT_AVAILABLE')
  cfg,chosen,_=configuration(app['memory_embedding_config'],c.MEMORY_PROFILE)
  require(cfg['placement']=='service-network','UNSUPPORTED_PROFILE')
  transport=binding(cfg,chosen);client_calls+=1
  value=transport.invoke(dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),
    operation='authorize-disclose',intent=json.loads(row[0]),attempt=0))
  require(value=={'authorized':True},'CONFLICT');operation='authorize-disclose'
 elif role=='fusion-search':
  from fusion.preview_memory_services import Client
  with sqlite3.connect(dbfile.as_uri()+'?mode=ro',uri=True) as db:
   db.execute('PRAGMA query_only=ON')
   row=db.execute('SELECT v.value FROM app_read_views v JOIN app_active_view a ON a.view=v.id WHERE a.singleton=1').fetchone()
  require(row is not None,'NOT_AVAILABLE');snapshot=json.loads(row[0])['snapshot']
  port=Client(app['active_memory_configs']['search'],'search');client_calls+=1
  value=port.call('ready',snapshot)
  operation='ready-exact-retained-view'
 elif role=='fusion-storage':
  from fusion.preview_atoms import client
  cfg=json.loads(Path(app['memory_atoms_config']).read_bytes());port=client(cfg);client_calls+=1;value=port.head(cfg['scope'])
  operation='head'
 elif role=='fusion-messaging':
  from fusion.preview_tasks import Client
  port=Client(app['task_config']);client_calls+=1;value=port.call('authorize');require(value=={'authorized':True},'CONFLICT')
  operation='authorize'
 else:require(False,'UNSUPPORTED_OPERATION')
 print(json.dumps(dict(status='PASS',operation=operation,client_invocations=client_calls,physical_http_sends='NOT_OBSERVED',
                      native_inputs=0,effect_reservations=0,returned_content='NOT_EXPORTED')))
except ContractError as error:
 print(json.dumps(dict(status='REFUSED',code=error.code,client_invocations=client_calls,physical_http_sends='NOT_OBSERVED',
                      native_inputs=0,effect_reservations=0,returned_content='NOT_EXPORTED')))
'''


def probe(r,role,identity):
    return r.call('omega-agent','providers',None,'--provider-action','probe',
                  '--provider','shared-'+role,'--identity',identity)


def retained(r,sid,original):
    page=r.call('omega-agent','observe',sid,'--content')
    found=next(x for x in page['inputs'] if x['id']==original['identity'])
    require(found==original['observed'],'CONFLICT')
    return dict(captured_result_exact=True,accepted_identity_exact=True,deadline_exact=True)


def outages(op,r,fault,sid,original,report,save):
    """At most12 explicit provider reads +8 independent Registry probes."""
    rows=[];report['dependency_outages']=rows;save()
    for role in ('fusion-embedding','fusion-search','fusion-storage','fusion-messaging'):
        require(time.monotonic()<r.end,'DEADLINE_EXCEEDED')
        row=dict(owner=role,status='RUNNING',before=fault.pod(role));rows.append(row);save()
        def observed():
            return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-',role,sid,
                                  data=OBSERVE,timeout=35))
        row['before_port']=observed();require(row['before_port']['status']=='PASS','NOT_AVAILABLE');save()
        stopped=False
        try:
            stopped=True;op.k('scale','statefulset',role,'--replicas=0')
            op.k('wait','--for=delete','pod/'+role+'-0','--timeout=60s',timeout=65)
            row['during_port']=observed();save()
            require(row['during_port'].get('code')=='NOT_AVAILABLE','CONFLICT')
            row['readiness']=probe(r,role,'incident-down-'+role)
            require(row['readiness']['status']!='ready','CONFLICT')
            row['retained_application_result']=retained(r,sid,original);save()
        finally:
            if stopped:
                op.k('scale','statefulset',role,'--replicas=1')
                op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=90s',timeout=100)
                row['after']=fault.pod(role);save()
        require(all(row['before'][key]==row['after'][key] for key in ('images','volumes')),'CONFLICT')
        row['after_port']=observed();require(row['after_port']['status']=='PASS','NOT_AVAILABLE')
        row['recovered_readiness']=probe(r,role,'incident-up-'+role)
        require(row['recovered_readiness']['status']=='ready','NOT_AVAILABLE')
        row.update(status='PASS',fallback=False,observation_only=True,new_work_admission='NOT_ATTEMPTED',
                   unavailable_not_empty=True,client_invocations=3);save()
    return rows


def registry_pressure(r,sid,original,report,save):
    """Fill actual finite observation metadata, then seal only exact receipts."""
    from examples.pilot_endurance import registry
    row=dict(status='RUNNING',probes=[],maximum_new_probes=256,epoch_seals=[])
    report['registry_pressure']=row;save();role='omega-agent';provider='shared-fusion-storage'
    row['before']=registry(r,role,'headroom');save()
    for index in range(256):
        require(time.monotonic()<r.end,'DEADLINE_EXCEEDED')
        identity='incident-registry-probe-'+str(index)
        try:value=registry(r,role,'probe',provider,identity)
        except RuntimeError as error:
            require('OVERLOADED' in str(error),'CONFLICT')
            row['refused']=dict(index=index,code='OVERLOADED',identity=identity);save();break
        row['probes'].append(dict(identity=identity,value=value));save()
    require('refused' in row and row['probes'],'NOT_AVAILABLE')
    row['at_refusal']=registry(r,role,'headroom')
    row['retained_application_result']=retained(r,sid,original)
    first=row['probes'][0]
    row['duplicate']=registry(r,role,'probe',provider,first['identity'])
    require(row['duplicate']==first['value'],'CONFLICT');save()
    # One finite exact owner-controlled epoch suffices for one new observation.
    plan=registry(r,role,'plan',provider);row['seal_plan']=plan;save()
    result=registry(r,role,'seal',provider,'incident-registry-seal',plan['head'])
    row['epoch_seals'].append(result);save()
    row['after_seal']=registry(r,role,'headroom')
    row['recovered_probe']=registry(r,role,'probe',provider,'incident-registry-after-seal')
    require(row['recovered_probe']['status']=='ready','NOT_AVAILABLE')
    require(registry(r,role,'probe',provider,first['identity'])==first['value'],'CONFLICT')
    row.update(status='PASS',sealed_receipt_replay_exact=True,deleted_authoritative_facts=0,
               renewed_old_readiness=0,reservation_refunds=0);save()
    return row


def dns_outage(op,r,sid,original,report,save):
    """One bounded DNS attempt while only this caller's DNS egress is removed."""
    role='omega-agent';name=role+'-ports'
    policy=json.loads(op.k('get','networkpolicy',name,'-o','json'))
    require(policy['metadata']['namespace']==op.namespace and op.namespace.startswith('omega-ref-pilot-'),'UNAUTHORIZED')
    prior=policy['spec'];changed=json.loads(json.dumps(policy));removed=[];kept=[]
    for rule in prior.get('egress',[]):
        if any(p.get('port')==53 for p in rule.get('ports',[])):removed.append(rule)
        else:kept.append(rule)
    require(removed and kept,'CONFLICT');changed['spec']['egress']=kept
    row=dict(status='RUNNING',removed_dns_rules=len(removed),other_allow_rules_unchanged=True,
             native_inputs=0,effect_reservations=0);report['dns_outage']=row;save()
    source="""import json,socket,signal\nfrom pathlib import Path\ncfg=json.loads(Path('/run/fusion/templates/shared/atoms.json').read_bytes())\ndef expired(*_):raise TimeoutError('bounded resolver observation')\nsignal.signal(signal.SIGALRM,expired);signal.alarm(8)\ntry:\n socket.getaddrinfo(cfg['endpoint']['host'],cfg['endpoint']['port']);print(json.dumps({'status':'RESOLVED'}))\nexcept (socket.gaierror,TimeoutError):print(json.dumps({'status':'UNAVAILABLE','bounded_seconds':8}))\nfinally:signal.alarm(0)\n"""
    # Resolve the selected AtomStorage config using application composition,
    # never a model-controlled hostname or an invented alternate service.
    source=source.replace("cfg=json.loads(Path('/run/fusion/templates/shared/atoms.json').read_bytes())",
        "app=json.loads((Path('/run/fusion/sessions')/"+repr(sid)+"/'application.json').read_bytes());cfg=json.loads(Path(app['memory_atoms_config']).read_bytes())")
    try:
        op.k('replace','-f','-',data=json.dumps(changed));time.sleep(2)
        row['during']=json.loads(op.k('exec','-i',role+'-0','--',PYTHON,'-',data=source,timeout=15))
        require(row['during']['status']=='UNAVAILABLE','CONFLICT')
        row['during_operator_dns_read']='UNAVAILABLE_UNTIL_DNS_RESTORED';save()
    finally:
        current=json.loads(op.k('get','networkpolicy',name,'-o','json'));current['spec']=prior
        op.k('replace','-f','-',data=json.dumps(current));row['policy_restored']=True;save()
    row['after']=json.loads(op.k('exec','-i',role+'-0','--',PYTHON,'-',data=source,timeout=15))
    require(row['after']['status']=='RESOLVED','NOT_AVAILABLE')
    row['retained_application_result']=retained(r,sid,original);row['status']='PASS';save()

HEAD_READ=r'''
import json,sys
from pathlib import Path
from fusion.contracts import ContractError
from fusion.preview_atoms import client
app=json.loads((Path('/run/fusion/sessions')/sys.argv[1]/'application.json').read_bytes())
cfg=json.loads(Path(app['memory_atoms_config']).read_bytes())
port=client(cfg,int(sys.argv[2]))
try:print(json.dumps(dict(status='PASS',value=port.head(cfg['scope']))))
except ContractError as error:print(json.dumps(dict(status='REFUSED',code=error.code)))
'''


def reply_reads(op,r,fault,sid,original,report,save):
    """Two real-owner read faults; no work admission, mutation or model call."""
    from concurrent.futures import ThreadPoolExecutor
    import yaml
    rows=[];report['reply_read_faults']=rows;save()
    for mode in ('partial-body','delay'):
        require(time.monotonic()<r.end,'DEADLINE_EXCEEDED')
        identity='pilot-head-'+mode;now=time.time_ns()//1000000
        deadline=now+min(120000,max(0,int((r.end-time.monotonic())*1000)))
        require(deadline>now,'DEADLINE_EXCEEDED')
        selection=dict(profile='deployment-reply-fault/1',identity=identity,path='/reference-cognition',
                       operation='head',mode=mode,delay_ms=5000 if mode=='delay' else 0,
                       observer_deadline_ms=deadline)
        row=dict(mode=mode,status='RUNNING',selection=selection,observer_deadline_ms=deadline,
                 native_inputs=0,effect_reservations=0,physical_http_sends='NOT_OBSERVED')
        rows.append(row);save()
        def read():
            require(time.monotonic()<r.end and time.time_ns()//1000000<deadline,'DEADLINE_EXCEEDED')
            return json.loads(op.k('exec','-i','omega-agent-0','--',PYTHON,'-',sid,str(deadline),
                                  data=HEAD_READ,timeout=30))
        row['before']=read();require(row['before']['status']=='PASS','NOT_AVAILABLE');save()
        marker='reply-fault-'+identity+'.json';require(fault.read('fusion-storage',marker) is None,'CONFLICT')
        fault.values['testFaultsEnabled']=True
        fault.values['components']['fusion-storage'].setdefault('config',{})['test']={'reply_fault':selection}
        fault.values_path.write_text(yaml.safe_dump(fault.values,sort_keys=False))
        op.command(['helm','upgrade','omega',fault.chart,'--kubeconfig',op.kubeconfig,'--kube-context',op.context,
                    '--namespace',op.namespace,'-f',str(fault.values_path),'--wait','--timeout','180s'],timeout=190)
        if mode=='partial-body':
            row['fault_reply']=read();row['marker']=fault.read('fusion-storage',marker);save()
        else:
            with ThreadPoolExecutor(max_workers=1) as pool:
                response=pool.submit(read)
                until=min(r.end,time.monotonic()+10);fired=None
                while time.monotonic()<until:
                    fired=fault.read('fusion-storage',marker)
                    if fired:break
                    time.sleep(.1)
                require(fired is not None,'NOT_AVAILABLE');row['marker']=fired;save()
                row['replacement']=fault.replace(['fusion-storage']);save()
                row['fault_reply']=response.result();save()
        require(row['marker'] is not None and row['fault_reply']['status']=='REFUSED'
                and row['fault_reply']['code']=='NOT_AVAILABLE','CONFLICT')
        # The durable one-shot claim remains selected. A separate explicit read
        # observes original owner state without re-injecting or replaying work.
        row['after']=read();require(row['after']==row['before'],'CONFLICT')
        require(fault.read('fusion-storage',marker)==row['marker'],'CONFLICT')
        row['retained_application_result']=retained(r,sid,original)
        row['retirement']=fault.disarm('fusion-storage')
        row.update(status='PASS',client_invocations=3,one_shot_claim_retained=True,
                   retries_automatic=0,deadline_renewals=0);save()
    return rows
