"""Independent opt-in bindings for the same native ModelAdoption consumer.

Historical recorded selections are unchanged. The real adapter is lazy and its
existing campaign authority is checked before any new acceptance/reservation.
An absent approval never selects recorded proposals as a fallback.
"""
import json
from pathlib import Path
from .contracts import canonical,digest,require
from . import model_contracts as live, preview_model_contracts as recorded
from . import preview_recorded_model as authored
from .registry import descriptor_read,selection_token

PROFILE='omega-preview-model-binding/1'


def contracts(cfg):
    if cfg['profile']==recorded.PROFILE:
        require(cfg.get('binding') in (None,PROFILE),'UNSUPPORTED_PROFILE');return recorded
    require(cfg.get('binding')==PROFILE and cfg['profile']==live.CPU_PROFILE,'UNSUPPORTED_PROFILE')
    return live


def configuration(path):
    cfg=json.loads(Path(path).read_bytes());c=contracts(cfg)
    if c is recorded:return authored.configuration(path)
    require(cfg['fallback'] is False and cfg['placement'] in ('local','network'),'UNSUPPORTED_PROFILE')
    require(cfg['disclosure']['profile']=='synthetic-session-prompt/1','UNSUPPORTED_PROFILE')
    require(cfg['disclosure']['max_prompt_bytes']==live.MAX_PROMPT,'UNSUPPORTED_PROFILE')
    chosen=c.select([descriptor_read(d) for d in cfg['catalogue']],cfg['profile'])
    frozen={k:cfg[k] for k in ('binding','profile','principal','scope','session','placement','disclosure')}
    frozen['selection']=selection_token(chosen)
    if cfg['placement']=='local':frozen['provider_config']=cfg['provider_config']
    else:
        require('provider_config' not in cfg,'UNSUPPORTED_PROFILE')
        frozen['endpoint']={**cfg['endpoint'],'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
    return cfg,chosen,frozen


def boundary(cfg):
    return 'RECORDED_FIXTURE' if contracts(cfg) is recorded else 'LIVE_APPROVAL_REQUIRED'


class GuardedBackend:
    def __init__(self,path):self.path=Path(path)
    def authorize(self,accepted):
        cfg=json.loads(self.path.read_bytes());binding=cfg['model_binding']
        require(binding['profile']==PROFILE and binding['kind']=='approved-pinned-ollama','UNSUPPORTED_PROFILE')
        # Guard missing authority before reading runtime locks, creating a real
        # adapter, opening sockets or accepting/reserving a provider occurrence.
        approval=binding.get('approval')
        require(type(approval) is str and Path(approval).is_file(),'UNAUTHORIZED')
        from integration.single_node.future_live import approve
        plan,_=approve(binding['manifest'],approval)
        require(cfg['model_completion']['runtime_lock']==plan['runtime_lock'],'CONFLICT')
        slot=next((s for s in plan['slots'] if s['id']==accepted['id']),None)
        require(slot is not None and (slot['session'],slot['slot'])==(accepted['session'],accepted['slot']),'UNAUTHORIZED')
        require(cfg['model_completion']['max_calls']==2,'UNAUTHORIZED')
        # Exact configuration/prompt policy is covered by the plan's source and
        # configuration bindings; occurrence IDs never acquire authority alone.
        require(any(Path(x['path'])==self.path for x in plan['bindings']),'UNAUTHORIZED')
        return binding
    def complete(self,accepted):
        from dataclasses import asdict
        binding=self.authorize(asdict(accepted))
        from integration.single_node.future_live import Backend
        return Backend(binding['manifest'],binding['approval']).complete(accepted)


def service(path,hook=lambda _:None):
    cfg=json.loads(Path(path).read_bytes());binding=cfg.get('model_binding')
    if binding is None:return authored.service(path,hook)
    require(binding['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    if binding['kind']=='recorded':
        require(set(binding)=={'profile','kind'},'UNSUPPORTED_PROFILE')
        return authored.service(path,hook)
    require(binding['kind']=='approved-pinned-ollama' and set(binding)=={'profile','kind','manifest','approval'},'UNSUPPORTED_PROFILE')
    backend=GuardedBackend(path)
    from .model_service import ModelService
    return ModelService(path,backend,hook,disclosure=authored.disclosure,contracts=live,execution_authority=backend.authorize)


def inspect_configuration(path):
    """Validate selection and retained seal, without backend activity."""
    from .model_service import inspect_journal
    inspect_journal(path)
    cfg=json.loads(Path(path).read_bytes());binding=cfg.get('model_binding')
    if binding is None or binding.get('kind')=='recorded':authored.RecordedProposals(path);return
    require(binding.get('profile')==PROFILE and binding.get('kind')=='approved-pinned-ollama','UNSUPPORTED_PROFILE')
    require(set(binding)=={'profile','kind','manifest','approval'},'UNSUPPORTED_PROFILE')
    live.select([descriptor_read(d) for d in cfg['model_completion']['catalogue']],live.CPU_PROFILE)


def inspect_partitions(path):
    """Check every configured owner partition before the service becomes ready."""
    path=Path(path);cfg=json.loads(path.read_bytes())
    inspect_configuration(path)
    for partition in cfg.get('scope_routes',{}).get('scopes',{}).values():
        inspect_configuration(Path(partition['directory'])/'owner.json')


class Client:
    def __init__(self,path):
        self.path=path;self.cfg,self.chosen,self.frozen=configuration(path)
        self.contracts=contracts(self.cfg)
    def invoke(self,operation,accepted):
        cfg,_,frozen=configuration(self.path);require(frozen==self.frozen,'CONFLICT');c=self.contracts
        require((accepted['principal'],accepted['scope'],accepted['session'])==(cfg['principal'],cfg['scope'],cfg['session']),'UNAUTHORIZED')
        authored.disclosure(accepted,cfg['disclosure'])
        q=dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation=operation,intent=accepted);c.request(q)
        if cfg['placement']=='local':
            owner=service(cfg['provider_config'])
            try:reply=owner.invoke(cfg['credential'],q)
            finally:owner.close()
        else:
            from .preview_transport import invoke
            reply=invoke(cfg,'/preview/model',q,accepted['deadline_ms'] if operation=='complete' else None)
        from .model_transport import checked
        return checked(q,reply,contracts=c)
