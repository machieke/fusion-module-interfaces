"""Local/HTTPS placement of only the existing channel payload/mailbox ports."""
import http.client
import json
from pathlib import Path
import uuid
from . import channel_contracts as c
from .contracts import canonical,digest,require,ContractError,PROFILES,encode,decode
from .registry import descriptor_read
from .neoclaw_transport import Network,json_loads
from .responses import validate_reply,error


def configuration(path):
    cfg=json.loads(Path(path).read_text());c.route_config(cfg)
    require(cfg['fallback'] is False and cfg['placement'] in ('local','network','service-network'),'UNSUPPORTED_PROFILE')
    chosen=c.selected([descriptor_read(x) for x in cfg['catalogue']])
    require('provider_config' not in cfg if cfg['placement'] in ('network','service-network') else 'endpoint' not in cfg,'UNSUPPORTED_PROFILE')
    frozen={k:cfg[k] for k in ('profile','scope','session','bridge','target','ingress_route','egress_route','principal',
                               'role','approved_inputs','approved_outputs','placement')}
    frozen.update(selections=c.selection(chosen))
    if cfg['placement']=='service-network':
        from .channel_services import placement
        frozen.update(placement(cfg))
    elif cfg['placement']=='network':
        frozen.update(endpoint=cfg['endpoint'],ca_sha256=digest(Path(cfg['endpoint']['ca_file']).read_bytes()))
    else:frozen.update(provider_config=str(Path(cfg['provider_config']).resolve()))
    return cfg,chosen,frozen


def checked(request,reply,chosen):
    if type(reply) is dict and set(reply)=={'error'}:
        error(reply['error']);raise ContractError(reply['error']['code'])
    c.fields(reply,'request_id request_digest principal selection reply')
    q=request['invocation']
    require(reply['request_id']==q['message_id'] and reply['request_digest']==digest(canonical(request)) and
            reply['selection']==request['selections'],'NOT_AVAILABLE')
    require(reply['principal']==request['principal'],'UNAUTHORIZED')
    return validate_reply(q,reply['reply'],chosen[q['interface_ref']['id']])


class ChannelNetwork(Network):
    def invoke(self,request):
        c.wire(request,self.chosen)
        conn=http.client.HTTPSConnection(self.endpoint['host'],self.endpoint['port'],timeout=self.timeout,context=self.context)
        try:
            conn.request('POST','/s06-mailbox',body=canonical(request),headers={
                'Authorization':'Bearer '+self.credential,'Content-Type':'application/json'})
            response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE')
            raw=response.read(32769);require(len(raw)<=32768,'NOT_AVAILABLE');reply=json_loads(raw)
        except (OSError,http.client.HTTPException,ValueError):raise ContractError('NOT_AVAILABLE') from None
        finally:conn.close()
        return checked(request,reply,self.chosen)


class Client:
    def __init__(self,path):
        self.path=Path(path);self.cfg,self.chosen,self.frozen=configuration(path)
    def current(self):
        cfg,chosen,frozen=configuration(self.path);require(frozen==self.frozen,'CONFLICT');return cfg
    def invoke(self,family,operation,body,key,deadline=None,correlation=None):
        cfg=self.current();q=dict(message_id=key,interface_ref=dict(id=family,version=self.chosen[family].version),
            operation=operation,scope_ref=cfg['scope'],profile=PROFILES[family],body=body)
        if operation in ('create','send','ack'):q['idempotency_key']=key
        if deadline is not None:q['deadline_ms']=deadline
        if operation=='send':q.update(correlation_id=correlation,reply_route=self.receive_route())
        request=dict(channel_profile=c.PROFILE,selections=c.selection(self.chosen),principal=cfg['principal'],invocation=q)
        c.wire(request,self.chosen)
        if cfg['placement']=='service-network':
            return ChannelNetwork(cfg['endpoints'][family],cfg['service_credentials'][family],self.chosen,service_dns=True).invoke(request)
        if cfg['placement']=='network':return ChannelNetwork(cfg['endpoint'],cfg['credential'],self.chosen).invoke(request)
        from .channel_service import ChannelService
        owner=ChannelService(cfg['provider_config'])
        try:return checked(request,owner.invoke(cfg['credential'],request),self.chosen)
        finally:owner.close()
    def receive_route(self):return self.cfg['egress_route' if self.cfg['role']=='bridge' else 'ingress_route']
    def put(self,value):
        cfg=self.current();c.record(value,cfg)
        return self.invoke('atom.storage','create',dict(content_type=c.CONTENT,bytes=encode(canonical(value)),sharing='non-sensitive-fixture'),
                           'payload/'+value['id'],value['deadline_ms'])
    def get(self,ref):
        value=self.invoke('atom.storage','get',dict(ref=ref),'get/'+ref['id'])
        require(value['content_type']==c.CONTENT,'NOT_AVAILABLE');data=decode(value['bytes']);body=c.record(json.loads(data),self.current())
        require(canonical(body)==data,'NOT_AVAILABLE');return body
    def send(self,value,ref):
        c.record(value,self.current())
        result=self.invoke('agent.messaging','send',dict(ref=ref,route=value['route']),'mail/'+value['id'],value['deadline_ms'],value['id'])
        ident=canonical([self.cfg['principal'],self.cfg['scope'],'agent.messaging','send','mail/'+value['id']]).decode()
        require(result['delivery_id']==str(uuid.uuid5(uuid.NAMESPACE_URL,ident)),'NOT_AVAILABLE');return result
    def poll(self):
        value=self.invoke('agent.messaging','poll',dict(route=self.receive_route()),'poll')['delivery']
        if value is not None:c.delivery(value,self.current(),'egress' if self.cfg['role']=='bridge' else 'ingress')
        return value
    def ack(self,delivery):
        c.delivery(delivery,self.current(),'egress' if self.cfg['role']=='bridge' else 'ingress')
        return self.invoke('agent.messaging','ack',dict(route=self.receive_route(),delivery_id=delivery['delivery_id']),
                           'ack/'+delivery['delivery_id'])
