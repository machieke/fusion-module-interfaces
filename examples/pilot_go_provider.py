"""Installed two-stage native onboarding of the independent Go inspect owner.

Baseline and replacement use the identical native remember/delegate/inspect/
context consumer. An explicit extra allocation template selects placement.
No owner file is copied, no generative runtime or provider fallback is used.
"""
import argparse,json,time,uuid
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.registry import descriptor_wire,selection_token
from fusion.reference_inspect_contracts import descriptor
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.placement import verify_installed
from examples.integrated_sustained import IntegratedRunner as Runner
from examples.pilot_workflows import await_delegation,close_consumed_sessions


def provider(r,operation,key=None,identity=None,session=None):
    args=['--provider-action',operation]
    if key:args+=['--provider',key]
    if identity:args+=['--identity',identity]
    return r.call('omega-agent','providers',session,*args)


def port_observation(op,sid,job,advertise=False):
    # Configuration and credentials stay inside the caller. This is a read-only
    # contract observer, never Application construction or provider journal I/O.
    script='''import http.client,json,ssl,sys
from pathlib import Path
from fusion.preview_inspect import Client
from fusion.contracts import require
sid,job,advertise=sys.argv[1:]
p=Path('/run/fusion/sessions')/sid/'inspection.json';client=Client(p)
v={'events':client.events(job)}
if advertise=='yes':
 c=client.cfg['ports']['execution'];e=c['endpoint'];context=ssl.create_default_context(cafile=e['ca_file']);context.minimum_version=ssl.TLSVersion.TLSv1_2
 def get(token):
  h=http.client.HTTPSConnection(e['host'],e['port'],context=context,timeout=5)
  try:
   h.request('GET','/descriptor',headers={'Authorization':'Bearer '+token});r=h.getresponse();raw=r.read(65537)
   require(r.status==200 and len(raw)<=65536,'NOT_AVAILABLE');return json.loads(raw)
  finally:h.close()
 v['advertised']=get(c['credential']);v['wrong_credential']=get('explicit-wrong-synthetic-token')
print(json.dumps(v))'''
    return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script,sid,job,'yes' if advertise else 'no',timeout=35))


def next_context(op,sid,inspection):
    # Application-owned captured prompt is exported as hashes/equality evidence;
    # the observation never inserts an expected answer or modifies that prompt.
    script='''import json,sqlite3,sys
from pathlib import Path
from fusion.contracts import digest,require
sid,job,artifact=sys.argv[1:]
p=Path('/state/sessions')/sid/'caller.sqlite'
with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
 accepted=json.loads(db.execute('SELECT intent FROM app_model_calls ORDER BY slot DESC LIMIT 1').fetchone()[0])
 prompt=accepted['native_prompt'];require(' LAST_SKILL_USE_RESULTS: ' in prompt,'NOT_AVAILABLE')
 feedback=prompt.split(' LAST_SKILL_USE_RESULTS: ',1)[1].split(' HISTORY: ',1)[0]
 require(all(x in feedback for x in ('INSPECTED_ARTIFACT',job,artifact)),'NOT_AVAILABLE')
 print(json.dumps({'actual_prompt_sha256':digest(prompt.encode()),'feedback_sha256':digest(feedback.encode()),
  'inspection_job_bound':True,'inspection_artifact_bound':True,'slot':accepted['slot'],'source_id':accepted['source_id'],
  'next_prompt_not_injected':True}))'''
    return json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script,sid,inspection['job_id'],inspection['artifact']['digest'],timeout=35))


def consume(r,index,report,save):
    """The same native commands and application consumer in both placements."""
    sid=r.ids['omega-agent'][index]
    report['memory']=r.object(r.run('remember The synthetic copper beacon is held in chest elm',session=index));save()
    task=r.object(r.run('delegate B synthetic copper beacon location',session=index));report['task']=task;save()
    returned,session=await_delegation(r,sid,task,r.end)
    report.update(delegated_result=returned,consumption_observation=session);save()
    inspection=r.object(r.run('inspect-atom '+task['task'],session=index))
    require(inspection['status']=='INSPECTED_ARTIFACT' and inspection['caller_acknowledged'] is True and inspection['chain']=='NOT_SUBMITTED','NOT_AVAILABLE')
    report['inspection']=inspection;save();return inspection


def qualify(op,plan,artifact,directory,*,original=None):
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    r=Runner(op,root/'native',maximum_inputs=4);r.end=time.monotonic()+900
    stage='replacement' if original else 'baseline';template='go-shared' if original else 'shared'
    report=dict(status='RUNNING',stage=stage,template=template,classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',
        model='RECORDED_COMMAND_PROPOSALS',additional_live_generations=0,
        consumer_source_sha256=digest(Path(__file__).read_bytes()),same_native_business_logic='consume',
        provider_placement='single-node pod-to-pod authenticated HTTPS',state_migration=False,chain='NOT_REQUESTED',
        writer_handover_profile='UNSUPPORTED_NOT_ADVERTISED_BY_GO')
    def save():r.save();(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        report['preflight']=verify_installed(plan,op,{'inspect-go':artifact});report['images']={x['metadata']['name']:x['spec']['template']['spec']['containers'][0]['image'] for x in op.workloads()};save()
        if original:
            previous=Path(original);before=json.loads((previous/'report.json').read_bytes())
            prior=json.loads((previous/'native/report.json').read_bytes())
            require(before['status']=='PASS' and before['stage']=='baseline' and prior['namespace']==op.namespace,'CONFLICT')
            old=before['session'];frozen=before['selected'];old_view=r.call('omega-agent','observe',old,'--content')
            require(provider(r,'selected',session=old)==frozen,'CONFLICT')
            for row in prior['inputs']:require(next(x for x in old_view['inputs'] if x['id']==row['identity'])==row['observed'],'CONFLICT')
            report.update(original_report_sha256=digest((previous/'report.json').read_bytes()),retained_before=old_view,old_selection=frozen);save()
            try:r.call('omega-agent','allocate',None,'--identity','unadmitted-go-'+str(uuid.uuid4()),'--template',template)
            except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['unadmitted_replacement_refused']=True
            else:require(False,'CONFLICT')
        # B's independent application Registry requires explicit trusted admission
        # before its unchanged ingress can allocate a delegated-task session.
        r.admit_selection('omega-agent-b','recipient-'+str(uuid.uuid4()))
        index=r.allocate('omega-agent',stage+'-'+str(uuid.uuid4()),template);sid=r.ids['omega-agent'][index]
        report.update(session=sid,selected=provider(r,'selected',session=sid));save()
        if original:
            require('go-shared-fusion-inspect-go' in report['selected'],'CONFLICT')
            selected=report['selected']['go-shared-fusion-inspect-go']['record']
            require(any(canonical(x)==canonical(descriptor_wire(descriptor())) for x in selected['capabilities']),'CONFLICT')
            report['draining_original']=provider(r,'drain','shared-fusion-execution','go-onboarding-drain-original')
            report['retired_original']=provider(r,'retire','shared-fusion-execution','go-onboarding-retire-original')
            try:r.call('omega-agent','submit',old,'--identity','old-selection-refused-new-work','--text','task-context','--assignment','synthetic-task')
            except RuntimeError as error:require('NOT_AVAILABLE' in str(error),'CONFLICT');report['old_new_input_refused']=True
            else:require(False,'CONFLICT')
            require(r.call('omega-agent','observe',old,'--content')['inputs']==old_view['inputs'],'CONFLICT');save()
        inspection=consume(r,index,report,save)
        entry=r.report['inputs'][-1];occurrence=entry['observed']['result']['occurrences'][0]
        continuation=r.call('omega-agent','continuation',sid,'--occurrence',occurrence)
        require(continuation['status']=='return-ready' and continuation['native_consumption']['turn_captured'],'NOT_AVAILABLE')
        report['continuation']=continuation
        observed=port_observation(op,sid,inspection['job_id'],bool(original));report['provider_observation']=observed;save()
        if original:
            require(observed['advertised']['selection']==selection_token(descriptor()) and
                canonical(observed['advertised']['descriptor'])==canonical(descriptor_wire(descriptor())),'CONFLICT')
            require(observed['wrong_credential']['error']['code']=='UNAUTHORIZED','CONFLICT')
            old_pod=json.loads(op.k('get','pod','fusion-inspect-go-0','-o','json'))['metadata']['uid']
            op.k('delete','pod','fusion-inspect-go-0','--wait=true',timeout=70)
            op.k('wait','--for=condition=Ready','pod/fusion-inspect-go-0','--timeout=90s',timeout=100)
            new_pod=json.loads(op.k('get','pod','fusion-inspect-go-0','-o','json'))['metadata']['uid'];require(old_pod!=new_pod,'CONFLICT')
            after=port_observation(op,sid,inspection['job_id'],True);require(after==observed,'CONFLICT')
            report['provider_replacement']=dict(old_pod=old_pod,new_pod=new_pod,original_events_and_descriptor_exact=True,after=after);save()
        r.run('task-context',session=index);report['next_context']=next_context(op,sid,inspection)
        duplicate=r.call('omega-agent','submit',sid,'--identity',entry['identity'],'--text',entry['command'],'--assignment','synthetic-task')
        require(duplicate['state']=='complete' and duplicate['deadline']==entry['accepted']['deadline'] and duplicate['accepted']==entry['accepted']['accepted'],'CONFLICT')
        require(r.call('omega-agent','continuation',sid,'--occurrence',occurrence)==continuation,'CONFLICT')
        report.update(duplicate_receipt=duplicate,capture_replayed_without_new_native_work=True,deadline_renewals=0,reservation_refunds=0)
        if original:
            old_after=r.call('omega-agent','observe',old,'--content');require(old_after['inputs']==old_view['inputs'],'CONFLICT')
            require(provider(r,'selected',session=old)==frozen,'CONFLICT');report['retained_after']=old_after
            report['closures']=close_consumed_sessions(r,sid,'go-onboarding-'+sid)
            report['old_closed']=r.call('omega-agent','close',old,'--identity','go-close-original-'+old)
        else:
            # Keep the original sender active so later refusal is attributable
            # to Registry drain, not a closed session. Only its consumed B task
            # is explicitly closed; no capacity or spent effect is refunded.
            report['recipient_closures']=[]
            for item in r.call('omega-agent-b','list'):
                if item['state']!='active':continue
                value=r.call('omega-agent-b','observe',item['session'],'--content')
                if value['allocation']['allocation_id']=='incoming/A/'+sid:
                    require(all(x['state']=='complete' for x in value['inputs']),'NOT_AVAILABLE')
                    report['recipient_closures'].append(dict(observation=value,receipt=r.call('omega-agent-b','close',item['session'],'--identity','go-baseline-close-recipient')))
        report.update(status='PASS',native_operator_inputs=r.count,native_report_sha256=digest((r.root/'report.json').read_bytes()));save()
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1500:]));raise
    finally:save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','plan','artifact','directory'):p.add_argument('--'+name,required=True)
    p.add_argument('--original');a=p.parse_args()
    result=qualify(Operator(a.kubeconfig,a.context,a.namespace),json.loads(Path(a.plan).read_bytes()),a.artifact,a.directory,original=a.original)
    print(json.dumps(dict(status=result['status'],stage=result['stage'],additional_live_generations=0)))

if __name__=='__main__':main()
