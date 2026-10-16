"""Actual native Hive dispatch; generated inputs, real DeTTa and guarded PLN."""
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import pytest
from fusion.contracts import canonical,digest
from integration.hive.test_integration import Caller,ROOT
from integration.m3_scenario import run_generated
from tests.m3_support import CognitionHarness,SCOPE

class InferenceCaller(Caller):
    def start(self):
        env={k:v for k,v in os.environ.items() if not k.startswith('HIVE_')}
        env.update(HIVE_PLUGIN_DIRS=str(ROOT/'integration/hive/inference_program'),FUSION_M3_HIVE_CONFIG=str(self.config),
            HIVE_OFFLINE='1',HIVE_DATA_DIR=str(self.root/'hive'))
        self.log=open(self.root/'native.log','a')
        self.process=subprocess.Popen([sys.executable,str(ROOT/'integration/hive/native_caller.py'),str(self.root/'hive')],
            cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,start_new_session=True)
        assert self.read()=={'ready':True},(self.root/'native.log').read_text();return self

@pytest.fixture
def setup(tmp_path,request):
    h=CognitionHarness(tmp_path/'private',real=True,provider=getattr(request,'param','sqlite'))
    config={'private_config':str(h.path),'grants':[]};path=tmp_path/'caller.json';path.write_bytes(canonical(config));path.chmod(0o600)
    caller=InferenceCaller(tmp_path,path).start();request.addfinalizer(caller.kill);request.addfinalizer(h.close)
    swarm=caller.call('POST','/api/swarms',{'name':'Generated M3 integration'})['body']['id']
    config['grants']=[{'principal':'user:operator','swarm':swarm,'credential':h.credential,'scope':SCOPE}];path.write_bytes(canonical(config))
    body={'swarm_id':swarm,'action':'infer-generated','items':[],'params':{'seed':secrets.randbits(32),'prefer':'b',
        'deadline_ms':int(time.time()*1000)+300000},'idempotency_key':'generated-m3-intent'}
    detail=caller.call('GET','/api/programs/fusion-inference');assert detail['code']==200 and detail['body']['source']=='plugin-dir',detail
    return h,caller,config,path,body

def act(caller,body):
    response=caller.call('POST','/api/programs/fusion-inference/act',body);assert response['code']==200,response;return response['body']

def local(h,body):
    identity=digest(canonical(['user:operator',body['swarm_id'],body['idempotency_key']]))
    return run_generated(h.modules,SCOPE,identity,body['params']['seed'],body['params']['prefer'],body['params']['deadline_ms'])

@pytest.mark.parametrize('setup',['sqlite','atomic-file-fixture'],indirect=True)
def test_native_inference_replay_restart_and_attention_swap(setup):
    h,caller,config,path,body=setup;response=act(caller,body)
    assert response['status']=='done',response
    counts=response['detail']['counts'];assert counts['reserved']==counts['unique_admissions']==counts['feedback_applied']==1
    result=local(h,body);assert result['result']['results'][0]['task']==result['entries'][1]['task']
    output=h.beliefs.readBelief(result['roles'][1]['pr'],result['context'],None)
    assert output['observations']==[] and len(output['supports'])==1
    assert abs(float(output['truth']['strength'])-.68)<=1e-12 and abs(float(output['truth']['confidence'])-.3136)<=1e-12
    assert h.episodes.readEpisode(result['episode'],1,16)['head']==12
    assert act(caller,body)==response
    caller.kill();caller.start();assert act(caller,body)==response
    fresh={**body,'idempotency_key':'prefer-a','params':{**body['params'],'prefer':'a'}}
    switched=act(caller,fresh);assert switched['status']=='done',switched
    diagnostic=local(h,fresh);assert diagnostic['result']['results'][0]['task']==diagnostic['entries'][0]['task']

@pytest.mark.parametrize('stage',['after_attention_commit','after_attempt_reservation','after_kernel_return','after_derived_commit','after_feedback_commit'])
def test_native_caller_actual_kills_keep_one_attempt_budget(setup,stage):
    h,caller,config,path,body=setup;marker=caller.root/'pause'
    config.update(test_pause_at=stage,test_marker=str(marker));path.write_bytes(canonical(config))
    caller.send('POST','/api/programs/fusion-inference/act',body)
    deadline=time.monotonic()+60
    while not marker.exists() and caller.process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
    assert marker.exists(),(stage,(caller.root/'native.log').read_text())
    process=caller.process;caller.kill();assert process.returncode==-signal.SIGKILL
    del config['test_pause_at'];path.write_bytes(canonical(config));caller.start();response=act(caller,body)
    assert response['status']=='done',response
    counts=response['detail']['counts'];assert counts['reserved']==1
    expected=0 if stage in ('after_attempt_reservation','after_kernel_return') else 1
    assert counts['unique_admissions']==counts['feedback_applied']==expected
    result=local(h,body);snapshot=h.beliefs.readBelief(result['roles'][1]['pr'],result['context'],None)
    assert len(snapshot['supports'])==expected and snapshot['observations']==[]
    assert act(caller,body)==response


def test_native_privacy_current_auth_and_changed_intent(setup):
    h,caller,config,path,body=setup;response=act(caller,body);assert response['status']=='done',response
    result=local(h,body);public=canonical([response,caller.call('GET','/api/programs/fusion-inference')])+(caller.root/'native.log').read_bytes()
    for file in (caller.root/'hive').rglob('*'):
        if file.is_file():public+=file.read_bytes()
    markers=[f"PRIVATE-M3-{body['params']['seed']}".encode(),result['workset']['digest'].encode()]
    for entry in result['entries']:
        markers.append(entry['task']['digest'].encode())
        for b in entry['premises']:markers.extend([b['support_id'].encode(),b['claim']['digest'].encode()])
    for event in h.episodes.readEpisode(result['episode'],1,16)['events']:
        markers.extend([event['event']['payload']['digest'].encode(),event['evidence']['event_ref']['digest'].encode()])
        markers.extend(root.encode() for root in event['lineage_roots'])
    for marker in markers:assert marker not in public
    assert not (h.root/'shared').exists()
    changed={**body,'params':{**body['params'],'prefer':'a'}};refused=act(caller,changed)
    assert refused['status']=='refused' and refused['detail']['error']['code']=='CONFLICT',refused
    h.config['principals']['owner']['credential']='revoked';h.save();refused=act(caller,body)
    assert refused['status']=='refused' and refused['detail']['error']['code']=='UNAUTHORIZED',refused
