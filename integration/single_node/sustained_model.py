"""Trusted configuration of existing recorded or inactive pinned-real binding."""
import json
from fusion import model_contracts as c
from fusion.contracts import require
from fusion.preview_model_binding import PROFILE
from fusion.registry import descriptor_wire
from .configure import write


def configure(settings,cfg,state,run):
    p=settings['preview'];binding=p['sustained'].get('model_binding',dict(profile=PROFILE,kind='recorded'))
    require(binding.get('profile')==PROFILE and binding.get('kind') in ('recorded','approved-pinned-ollama'),'UNSUPPORTED_PROFILE')
    if binding['kind']=='recorded':
        require(set(binding)=={'profile','kind'},'UNSUPPORTED_PROFILE')
        if settings['role']=='fusion-model':cfg['model_binding']=binding
        return cfg
    require(set(binding)=={'profile','kind','manifest','approval','runtime_lock'},'UNSUPPORTED_PROFILE')
    require(not p['sustained'].get('private_scopes') and p['limits']['inputs']<=c.MAX_SESSION_CALLS,'UNSUPPORTED_PROFILE')
    require(binding['manifest']=='/config/live-plan.json' and binding['approval']=='/approvals/approval.json','UNSUPPORTED_PROFILE')
    require(type(binding['runtime_lock']) is dict and set(binding['runtime_lock'])=={'path','sha256'},'UNSUPPORTED_PROFILE')
    require(binding['runtime_lock']['path'].startswith('/opt/generative/'),'UNSUPPORTED_PROFILE')
    c.hash_value(binding['runtime_lock']['sha256'])
    # This selection mounts no runtime, starts no process, and grants no calls.
    # A future approved, source-bound installation must supply those inputs.
    if settings['role']=='fusion-model':
        cfg['model_binding']={k:v for k,v in binding.items() if k!='runtime_lock'}
        m=cfg['model_completion'];m['max_calls']=2
        m['catalogue']=[descriptor_wire(c.descriptor(c.CPU_PROFILE))]
        m['runtime_lock']=binding['runtime_lock'];m['disclosure']['max_prompt_bytes']=c.MAX_PROMPT
        m.pop('session_proposals',None);m.pop('recorded_proposals',None)
    if settings['role'] in p['agents']:
        seed=p['agents'][settings['role']]['sessions'][0];file=run/'sessions'/seed/'model.json'
        client=json.loads(file.read_bytes());client.update(binding=PROFILE,profile=c.CPU_PROFILE,
            catalogue=[descriptor_wire(c.descriptor(c.CPU_PROFILE))])
        client['disclosure']['max_prompt_bytes']=c.MAX_PROMPT;write(file,client)
    return cfg
