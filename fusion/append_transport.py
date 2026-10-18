"""Authenticated synchronous append/maintenance ports; no retries or fallback."""
import http.client
import time
from . import append_contracts as c
from .contracts import canonical,require,ContractError
from .neoclaw_transport import Network,json_loads
from .vector_transport import checked
from .append_composition import AppendService


class AppendNetwork(Network):
    def __init__(self,endpoint,credential,chosen,principal):
        super().__init__(endpoint,credential,chosen);self.principal=principal
    def invoke(self,request):
        c.request(request,self.chosen)
        # Observation may disclose already committed work after the work deadline.
        timeout=3. if request['operation'] not in ('create','build') else max(.1,min(8.,(request['intent']['deadline_ms']-time.time()*1000)/1000))
        conn=http.client.HTTPSConnection(self.endpoint['host'],self.endpoint['port'],timeout=timeout,context=self.context)
        try:
            conn.request('POST','/s03-append',body=canonical(request),headers={
                'Authorization':'Bearer '+self.credential,'Content-Type':'application/json'})
            response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE')
            data=response.read(c.MAX_WIRE_BYTES+1);require(len(data)<=c.MAX_WIRE_BYTES,'NOT_AVAILABLE')
            reply=json_loads(data)
        except (OSError,http.client.HTTPException,ValueError):raise ContractError('NOT_AVAILABLE') from None
        finally:conn.close()
        return checked(request,reply,self.principal)


class AppendLocal:
    def __init__(self,cfg,chosen):self.cfg,self.chosen=cfg,chosen
    def invoke(self,request):
        c.request(request,self.chosen)
        value=AppendService(self.cfg['provider_config'],self.cfg['credential']).invoke(json_loads(canonical(request)))
        return checked(request,value,self.cfg['principal'])


def binding(cfg,chosen):
    require(cfg['fallback'] is False,'UNSUPPORTED_PROFILE')
    if cfg['placement']=='local':return AppendLocal(cfg,chosen)
    require(cfg['placement']=='network' and 'provider_config' not in cfg,'UNSUPPORTED_PROFILE')
    return AppendNetwork(cfg['endpoint'],cfg['credential'],chosen,cfg['principal'])
