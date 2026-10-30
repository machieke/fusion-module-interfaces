"""Operator-only negative probes against deployed HTTPS, never model evaluation."""
import copy,http.client,json,sqlite3,ssl
from pathlib import Path
from fusion import retrieval_services as s,model_contracts as m
from fusion.contracts import ContractError,canonical


def probe():
    cfg=json.loads(Path('/run/fusion/model-client.json').read_bytes())
    with sqlite3.connect('file:/state/measured.sqlite?mode=ro',uri=True) as db:
        intents=[json.loads(r[0]) for r in db.execute('SELECT intent FROM app_model_calls ORDER BY slot')]
    assert len(intents)==2
    from fusion.neoclaw_retrieval_disclosure import receipt_path
    receipt=json.loads(receipt_path(cfg['disclosure'],intents[0]).read_bytes())
    base=dict(profile=s.POLICY,request=dict(interface_ref=dict(id=m.INTERFACE,version=m.VERSION),operation='observe',intent=intents[0]),receipt=receipt)
    results={}
    def denied(name,config,path,request):
        try:s.rpc(config,path,request)
        except ContractError as e:results[name]=e.code
        else:raise AssertionError(name+' accepted')
    denied('wrong-credential',dict(cfg,credential='wrong-credential-'*4),'/model-disclosure',s.metadata(cfg,intents[0],'observe'))
    for name,field,value in [('wrong-scope','scope','different-scope'),('wrong-recipient','recipient','different-recipient'),('wrong-principal','principal','other'),('wrong-profile','model_profile',m.PROFILE)]:
        meta=s.metadata(cfg,intents[0],'observe');meta[field]=value;denied(name,cfg,'/model-disclosure',meta)
    changed=copy.deepcopy(base);changed['receipt']['intent_sha256']='f'*64;denied('modified-receipt',cfg,'/s07-model-services',changed)
    replay=copy.deepcopy(base);replay['request']['intent']=intents[1];denied('receipt-replayed-to-other-occurrence',cfg,'/s07-model-services',replay)
    endpoint=cfg['endpoint'];connection=http.client.HTTPSConnection(endpoint['host'],endpoint['port'],context=ssl.create_default_context(),timeout=2)
    try:
        connection.request('GET','/health/ready');connection.getresponse();raise AssertionError('untrusted certificate accepted')
    except ssl.SSLCertVerificationError:results['untrusted-certificate']='TLS_VERIFICATION_REFUSED'
    finally:connection.close()
    from fusion.channel_transport import Client
    channel=Client('/run/fusion/channel-client.json')
    with sqlite3.connect('file:/state/measured.sqlite?mode=ro',uri=True) as db:
        ingress=json.loads(db.execute('SELECT envelope FROM app_channel_inputs ORDER BY slot LIMIT 1').fetchone()[0])
    try:channel.put(ingress)
    except ContractError as e:
        assert e.code=='UNAUTHORIZED';results['application-cannot-publish-bridge-input']=e.code
    else:raise AssertionError('wrong channel role admitted')
    return results


def other_principal():
    # A separately authorized credential belongs to THIS model owner only.
    # Read its own journal/Secret, never transfer the credential to another pod.
    from fusion.model_service import ModelService
    cfg=json.loads(Path('/run/fusion/owner.json').read_bytes());settings=json.loads(Path('/config/component.json').read_bytes());intent=json.loads(ModelService.inspect('/run/fusion/owner.json')[0]['intent'])
    policy=cfg['model_completion']['disclosure'];client=dict(principal='M',credential=cfg['principals']['other']['credential'],endpoint=dict(host=settings['peers']['fusion-model'],port=settings['https_port'],ca_file='/secrets/ca.crt'),disclosure=dict(policy,consent_sha256='a'*64,view_sha256='b'*64))
    try:s.rpc(client,'/model-disclosure',s.metadata(client,intent,'observe'))
    except ContractError as e:
        assert e.code=='UNAUTHORIZED';return dict(another_authorized_principal=e.code)
    raise AssertionError('another principal impersonated M')
def delegated_read_only():
    from fusion.channel_transport import ChannelNetwork
    from fusion import channel_contracts as c
    from fusion.contracts import PROFILES,encode
    from fusion.registry import descriptors
    cfg=json.loads(Path('/run/fusion/channel-owner.json').read_bytes());chosen=c.selected(descriptors(atom_provider='detta'))
    request=dict(channel_profile=c.PROFILE,selections=c.selection(chosen),principal='M',invocation=dict(message_id='delegation-negative',interface_ref=dict(id='atom.storage',version=chosen['atom.storage'].version),operation='create',scope_ref=cfg['channel_store']['scope'],profile=PROFILES['atom.storage'],idempotency_key='delegation-negative',body=dict(content_type=c.CONTENT,bytes=encode(b'{}'),sharing='non-sensitive-fixture')))
    try:ChannelNetwork(cfg['source_endpoint'],cfg['source_credentials']['M'],chosen,service_dns=True).invoke(request)
    except ContractError as e:
        assert e.code=='UNAUTHORIZED';return dict(mailbox_read_delegation_cannot_create=e.code)
    raise AssertionError('read delegation created storage payload')

if __name__=='__main__':print(json.dumps(probe()))
