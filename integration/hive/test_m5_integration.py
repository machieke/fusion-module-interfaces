"""Authenticated native Hive; setup exits before a port-only lookup gets requests."""
from dataclasses import asdict,replace
import json,os,secrets,signal,subprocess,sys,time
from pathlib import Path
import pytest
from fusion.contracts import canonical,digest
from fusion.ports import Mutation
from fusion import lookup_contracts as c
from fusion.lookup_composition import descriptors
from fusion.registry import descriptor_wire
from integration.hive.test_integration import Caller,ROOT
from tests.m5_support import LookupHarness,SCOPE

class LookupCaller(Caller):
    def start(self):
        env={k:v for k,v in os.environ.items() if not k.startswith('HIVE_')}
        env.update(HIVE_PLUGIN_DIRS=str(ROOT/'integration/hive/lookup_program'),FUSION_M5_HIVE_CONFIG=str(self.config),HIVE_OFFLINE='1',HIVE_DATA_DIR=str(self.root/'hive'))
        self.log=open(self.root/'native.log','a')
        self.process=subprocess.Popen([sys.executable,str(ROOT/'integration/hive/native_caller.py'),str(self.root/'hive')],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,start_new_session=True)
        assert self.read()=={'ready':True},(self.root/'native.log').read_text();return self

@pytest.fixture
def setup(tmp_path,request):
    seed=secrets.randbits(32);root=tmp_path/'private-setup'
    subprocess.run([sys.executable,'-m','integration.m5_driver',str(root),'seed','--real','--seed',str(seed)],cwd=ROOT,check=True,capture_output=True)
    h=LookupHarness(root,real=True);oracle=json.loads((root/'oracle.json').read_text());requests=json.loads((root/'requests.json').read_text())
    # Oracle moved outside caller configuration/root. No request carries any answer ref.
    (root/'oracle.json').unlink();(root/'requests.json').unlink()
    config={'private_config':str(h.path),'grants':[]};path=tmp_path/'caller.json';path.write_bytes(canonical(config));path.chmod(0o600)
    caller=LookupCaller(tmp_path,path).start();request.addfinalizer(caller.kill);request.addfinalizer(h.close)
    swarm=caller.call('POST','/api/swarms',{'name':'Generated private lookup'})['body']['id']
    config['grants']=[{'principal':'user:operator','swarm':swarm,'credential':h.credential,'scope':SCOPE,'requests':requests}];path.write_bytes(canonical(config))
    body={'swarm_id':swarm,'action':'lookup','items':[],'params':{'request':'positive'},'idempotency_key':'lookup-start'}
    detail=caller.call('GET','/api/programs/fusion-lookup');assert detail['code']==200 and detail['body']['source']=='plugin-dir',detail
    return h,caller,config,path,body,oracle

def act(caller,body):
    response=caller.call('POST','/api/programs/fusion-lookup/act',body);assert response['code']==200,response;return response['body']
def local(h,config,body):
    q=c.AttributeQuery(**config['grants'][0]['requests'][body['params']['request']])
    identity=digest(canonical(['user:operator',body['swarm_id'],body['idempotency_key']]))
    return h.consumer('hive-lookup').lookup(Mutation(SCOPE,identity),q)

def check(result,oracle):
    assert result['roots']==oracle['order'];assert len(result['documents'])==8
    assert {canonical(e) for e in result['relations']}=={canonical(e) for e in oracle['edges']}
    assert all(result['calls'][op]>0 for op in ('query','outgoing','incoming','getRelation','get','getMany'))
    assert result['calls']['query']==3

@pytest.mark.parametrize('repeat',[1,2])
def test_native_discovery_no_answers_restart_lag_rebuild_and_swap(setup,repeat):
    h,caller,config,path,body,oracle=setup
    response=act(caller,body);assert response['status']=='done',response;check(local(h,config,body),oracle)
    assert act(caller,body)==response;caller.kill();h.reopen();caller.start();assert act(caller,body)==response
    empty={**body,'idempotency_key':'no-match','params':{'request':'empty'}}
    assert act(caller,empty)['detail']['roots']==0;assert local(h,config,empty)['documents']==[]
    original=local(h,config,body);ref=h.create('later-record',kind='task',topic='retrieval-demo',label='PRIVATE-LATER-'+secrets.token_hex(8));new_head=h.atoms.head(SCOPE)
    config['grants'][0]['requests']['later']=asdict(h.query(new_head,kind='task',topic='retrieval-demo'));path.write_bytes(canonical(config))
    later={**body,'idempotency_key':'after-lag','params':{'request':'later'}}
    lag=act(caller,later);assert lag['detail']['error']['code']=='NOT_AVAILABLE',lag
    # Pure query never catches up as a side effect.
    assert act(caller,later)==lag;h.drain();assert act(caller,later)['detail']['roots']==6
    discovered=local(h,config,later);assert discovered['roots']==oracle['order']+[ref]
    h.search.beginRebuild(Mutation(SCOPE,'native-rebuild'))
    rebuilt={**later,'idempotency_key':'after-rebuild'};assert act(caller,rebuilt)['detail']['error']['code']=='NOT_AVAILABLE'
    h.search.catchUp(SCOPE,3);caller.kill();h.reopen();h.drain();caller.start()
    assert act(caller,rebuilt)['detail']['roots']==6
    rebuilt_result=local(h,config,rebuilt);assert rebuilt_result['roots']==discovered['roots'];assert rebuilt_result['search_generation']!=discovered['search_generation']
    h.config['lookup_descriptors']=[descriptor_wire(d) for d in descriptors('detta','atomic-file-fixture')];h.save();h.reopen();h.drain()
    swapped={**later,'idempotency_key':'substitute-projection'};assert act(caller,swapped)['detail']['roots']==6
    alternative=local(h,config,swapped)
    for key in ('roots','relations','documents','search_at','relations_at'):assert alternative[key]==discovered[key]
    # Existing journal replays bind provider selection; no live journal migration.
    assert act(caller,body)['detail']['error']['code']=='CONFLICT'
    if os.environ.get('FUSION_M5_EVIDENCE'):
        output=Path(os.environ['FUSION_M5_EVIDENCE']);output.mkdir(parents=True,exist_ok=True)
        (output/('lookup-trace-'+str(repeat)+'.json')).write_bytes(canonical({'fixture':'generated private corpus; oracle held by test only',
          'real':['local DeTTa','native authenticated Hive Programs','SQLite Relations and Search'],
          'substitute':'independent atomic-file Search fixture', 'setup_exited_before_lookup':True,
          'initial':{'roots':len(original['roots']),'relations':len(original['relations']),'payloads':len(original['documents']),'query_pages':original['calls']['query']},
          'lag':{'strict_error':'NOT_AVAILABLE','query_did_not_ingest':True},'catchup':{'roots':6},
          'rebuild':{'generation_changed':True,'same_discovery':True},'substitution':{'same_discovery':True},'restart_replay':'PASS'}))

@pytest.mark.parametrize('provider',['sqlite','atomic-file-fixture'])
@pytest.mark.parametrize('stage',['after_lookup_page','after_lookup_result'])
def test_native_paged_caller_sigkill(setup,provider,stage):
    h,caller,config,path,body,oracle=setup
    if provider!='sqlite':
        h.config['lookup_descriptors']=[descriptor_wire(d) for d in descriptors('detta',provider)];h.save();h.reopen();h.drain()
    marker=caller.root/'paused';config.update(test_pause_at=stage,test_marker=str(marker));path.write_bytes(canonical(config))
    caller.send('POST','/api/programs/fusion-lookup/act',body);deadline=time.monotonic()+60
    while not marker.exists() and caller.process.poll() is None and time.monotonic()<deadline:time.sleep(.02)
    assert marker.exists(),(caller.root/'native.log').read_text()
    process=caller.process;caller.kill();assert process.returncode==-signal.SIGKILL
    del config['test_pause_at'];path.write_bytes(canonical(config));h.reopen();caller.start()
    result=act(caller,body);assert result['status']=='done',result;check(local(h,config,body),oracle);assert act(caller,body)==result

def test_native_authority_privacy_and_request_binding(setup):
    h,caller,config,path,body,oracle=setup;response=act(caller,body);assert response['status']=='done',response
    result=local(h,config,body);public=canonical(response)+(caller.root/'native.log').read_bytes()
    for file in (caller.root/'hive').rglob('*'):
        if file.is_file():public+=file.read_bytes()
    secrets_private=[oracle['canary'],h.credential,str(h.path),'PRIVATE-OTHER-SCOPE','retrieval-demo']
    for document in result['documents']:secrets_private.extend([document['ref']['id'],document['ref']['digest'],document['record'].get('label','UNUSED-PRIVATE')])
    for edge in result['relations']:secrets_private.extend([edge['ref']['id'],edge['ref']['digest']])
    for secret in secrets_private:assert secret.encode() not in public
    assert not (h.root/'shared').exists()
    assert not any((h.modules.root/name).exists() for name in ('beliefs.sqlite','episodes.sqlite','attention.sqlite','inference.sqlite'))
    forged={**body,'params':{'request':'positive','principal':'user:operator'}}
    assert caller.call('POST','/api/programs/fusion-lookup/act',forged)['code']==400
    config['grants'][0]['requests']['positive']=config['grants'][0]['requests']['empty'];path.write_bytes(canonical(config))
    assert act(caller,body)['detail']['error']['code']=='CONFLICT'
    h.config['principals']['owner']['credential']='revoked';h.save()
    assert act(caller,body)['detail']['error']['code']=='UNAUTHORIZED'
