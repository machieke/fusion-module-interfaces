"""Real authenticated native dispatch. No standalone helper substitutes for act()."""
import copy,json,secrets,signal,time
import pytest
from fusion.contracts import canonical,digest
from fusion.ports import Mutation
from integration.hive.test_m3_integration import InferenceCaller,act,local
from tests.m3_1_support import ClosureHarness,SCOPE

@pytest.fixture
def setup(tmp_path,request):
    h=ClosureHarness(tmp_path/'private',real=True,provider=getattr(request,'param','sqlite'))
    config={'private_config':str(h.path),'grants':[]};path=tmp_path/'caller.json';path.write_bytes(canonical(config));path.chmod(0o600)
    caller=InferenceCaller(tmp_path,path).start();request.addfinalizer(caller.kill);request.addfinalizer(h.close)
    swarm=caller.call('POST','/api/swarms',{'name':'Generated delivery closure'})['body']['id']
    config['grants']=[{'principal':'user:operator','swarm':swarm,'credential':h.credential,'scope':SCOPE}];path.write_bytes(canonical(config))
    body={'swarm_id':swarm,'action':'infer-generated','items':[],'params':{'seed':secrets.randbits(32),'prefer':'b',
        'deadline_ms':int(time.time()*1000)+300000},'idempotency_key':'closure-intent'}
    return h,caller,config,path,body

def reconciliation(body,key='closure'):
    return {**body,'action':'reconcile-generated','params':{'original_command':body['idempotency_key'],'limit':1},'idempotency_key':key}

@pytest.mark.parametrize('setup',['sqlite','atomic-file-fixture'],indirect=True)
def test_native_progress_replay_restart_and_privacy(setup):
    h,caller,config,path,body=setup;response=act(caller,body)
    assert response['status']=='done',response
    detail=response['detail'];assert detail['execution']['status']=='complete'
    assert detail['result_admissions']==1 and detail['evidence']=={'pending':0,'state':'settled'}
    assert detail['feedback']['counts']['applied']==1 and detail['feedback']['state']=='settled'
    result=local(h,body);assert h.episodes.pendingEvidence(result['episode'],16)==()
    assert act(caller,body)==response
    closure=act(caller,reconciliation(body));assert closure['detail']==detail
    caller.kill();caller.start();assert act(caller,reconciliation(body))==closure
    public=canonical([response,closure,caller.call('GET','/api/programs/fusion-inference')])+(caller.root/'native.log').read_bytes()
    for file in (caller.root/'hive').rglob('*'):
        if file.is_file():public+=file.read_bytes()
    markers=[h.credential.encode(),str(h.modules.root).encode(),result['episode']['id'].encode(),result['workset']['digest'].encode(),f"PRIVATE-M3-{body['params']['seed']}".encode()]
    for entry in result['entries']:
        markers.append(entry['task']['digest'].encode())
        for premise in entry['premises']:markers.extend([premise['support_id'].encode(),premise['claim']['digest'].encode()])
    for event in h.episodes.readEpisode(result['episode'],1,16)['events']:
        markers.extend([event['event']['payload']['digest'].encode(),event['evidence']['event_ref']['digest'].encode()])
        markers.extend(root.encode() for root in event['lineage_roots'])
    for marker in markers:assert marker not in public
    assert not (h.root/'shared').exists()
    injected=reconciliation(body,'forged');injected['params']['credential']=h.credential
    rejected=caller.call('POST','/api/programs/fusion-inference/act',injected)
    assert rejected['code']==400 and rejected['body']['error']['code']=='credential_in_request'
    changed=reconciliation(body);changed['params']['limit']=2
    assert act(caller,changed)['detail']['error']['code']=='CONFLICT'
    h.config['principals']['owner']['credential']='revoked';h.save()
    assert act(caller,reconciliation(body))['detail']['error']['code']=='UNAUTHORIZED'

@pytest.mark.parametrize('setup',['sqlite','atomic-file-fixture'],indirect=True)
def test_native_caller_kill_then_stale_feedback_retirement(setup):
    h,caller,config,path,body=setup;marker=caller.root/'pause'
    config.update(test_pause_at='after_derived_commit',test_marker=str(marker));path.write_bytes(canonical(config))
    caller.send('POST','/api/programs/fusion-inference/act',body)
    deadline=time.monotonic()+90
    while not marker.exists() and caller.process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
    assert marker.exists(),(caller.root/'native.log').read_text()
    process=caller.process;caller.kill();assert process.returncode==-signal.SIGKILL
    identity=digest(canonical(['user:operator',body['swarm_id'],body['idempotency_key']]))
    h.attention.advance(Mutation(SCOPE,'controlled-clock'),'inference/'+identity,0,1)
    del config['test_pause_at'];path.write_bytes(canonical(config));caller.start()
    response=act(caller,body);detail=response['detail']
    assert detail['execution']=={'status':'complete','reason':'feedback-unavailable'},response
    assert detail['result_admissions']==1 and detail['evidence']['pending']==0
    assert detail['feedback']['counts']['pending']==1
    settled=act(caller,reconciliation(body));assert settled['detail']['feedback']['counts']['retired']==1,settled
    for key in ('execution','counts','remaining','result_admissions'):assert settled['detail'][key]==detail[key]
    caller.kill();caller.start();assert act(caller,reconciliation(body))==settled
    # Native infer replay keeps the original execution and reports the newer closure observation.
    assert act(caller,body)['detail']==settled['detail']

@pytest.mark.parametrize('stage',['after_evidence_decision_commit','after_evidence_ack_commit'])
def test_native_caller_evidence_kills_resume_same_observations(setup,stage):
    h,caller,config,path,body=setup;marker=caller.root/'pause'
    config.update(test_pause_at=stage,test_marker=str(marker));path.write_bytes(canonical(config))
    caller.send('POST','/api/programs/fusion-inference/act',body)
    deadline=time.monotonic()+90
    while not marker.exists() and caller.process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
    assert marker.exists(),(caller.root/'native.log').read_text()
    process=caller.process;caller.kill();assert process.returncode==-signal.SIGKILL
    del config['test_pause_at'];path.write_bytes(canonical(config));caller.start()
    response=act(caller,body);assert response['detail']['evidence']['pending']==0,response
    result=local(h,body);assert h.episodes.readEpisode(result['episode'],1,16)['head']==12
    assert len(h.modules.relay.decisions(result['episode']))==10
    assert response['detail']['result_admissions']==1

def test_native_completed_execution_with_no_conclusion_is_explicit(setup):
    h,caller,config,path,body=setup
    body['params']['deadline_ms']=1
    response=act(caller,body);detail=response['detail']
    assert response['status']=='done' and detail['execution']=={'status':'complete','reason':'deadline'},response
    assert detail['result_admissions']==0 and detail['counts']['reserved']==0
    assert detail['evidence']=={'pending':0,'state':'settled'} and detail['feedback']['counts']['applied']==0
    closure=act(caller,reconciliation(body));assert closure['detail']==detail
