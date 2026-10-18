"""Typed synchronous reads over the existing authenticated loopback HTTPS binding."""
import http.client
from pathlib import Path
import json
from .contracts import canonical,digest,require,ContractError
from .neoclaw_transport import Network,json_loads
from .vector_composition import ReadService,validate_request
from .responses import error


class ReadNetwork(Network):
    def __init__(self,endpoint,credential,chosen,principal):
        super().__init__(endpoint,credential,chosen,timeout=1.)
        self.principal=principal

    def invoke(self,request):
        validate_request(request,self.chosen)
        conn=http.client.HTTPSConnection(self.endpoint['host'],self.endpoint['port'],timeout=self.timeout,context=self.context)
        try:
            conn.request('POST','/s03-read',body=canonical(request),headers={'Authorization':'Bearer '+self.credential,'Content-Type':'application/json'})
            response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE')
            raw=response.read(98305);require(len(raw)<=98304,'NOT_AVAILABLE');reply=json_loads(raw)
        except (OSError,http.client.HTTPException,ValueError):raise ContractError('NOT_AVAILABLE') from None
        finally:conn.close()
        return checked(request,reply,self.principal)


def checked(request,reply,principal):
    if type(reply) is dict and set(reply)=={'error'}:
        error(reply['error']);raise ContractError(reply['error']['code'])
    require(type(reply) is dict and set(reply)=={'request_id','request_digest','selection','principal','value'},'NOT_AVAILABLE')
    require(reply['request_id']==request['request_id'] and reply['request_digest']==digest(canonical(request)) and reply['selection']==request['selection'],'NOT_AVAILABLE')
    require(reply['principal']==principal,'UNAUTHORIZED')
    return reply['value']


class ReadLocal:
    def __init__(self,path,credential,chosen,principal):self.path,self.credential,self.chosen,self.principal=path,credential,chosen,principal
    def invoke(self,request):
        validate_request(request,self.chosen)
        return checked(request,ReadService(self.path,self.credential).invoke(json_loads(canonical(request))),self.principal)


def binding(config,chosen):
    require(config['fallback'] is False,'UNSUPPORTED_PROFILE')
    if config['placement']=='local':return ReadLocal(config['provider_config'],config['credential'],chosen,config['principal'])
    require(config['placement']=='network' and 'provider_config' not in config,'UNSUPPORTED_PROFILE')
    return ReadNetwork(config['endpoint'],config['credential'],chosen,config['principal'])
