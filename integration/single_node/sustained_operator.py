"""Current authenticated session observations, without reading provider stores."""
import json
from pathlib import Path
from fusion.contracts import require
from fusion.policy import Policy


def inventory(owner,run,state):
    from .preview_operator import request
    policy=Policy(owner);full=policy.current();cfg=full['native_sessions']
    require(cfg['profile']=='omega-native-sessions/3','UNSUPPORTED_PROFILE')
    actor=policy.authenticate(full['principals']['operator']['credential'])
    require(actor=='operator','UNAUTHORIZED')
    for template in cfg['allocation']['templates'].values():
        policy.check(actor,template['scope'],'sessions.observe')
    rows=request('list',None,{},owner=owner)
    status=Path(state)/'worker-status.json'
    return dict(profile=cfg['profile'],principal=cfg['principal'],scope=cfg['scope'],
        sessions={r['session']:r for r in rows},templates=cfg['allocation']['templates'],capacity=request('capacity',None,{},owner=owner),
        assignments=cfg['assignments'],worker=json.loads(status.read_bytes()) if status.exists() else None,
        model_boundary=sorted(set(t['binding']['model_boundary'] for t in cfg['allocation']['templates'].values())),additional_live_generations=0,
        restore_fenced=(Path(state)/'restore-fence.json').exists(),observation='CURRENT_APPLICATION_OWNER',retained_provider_views='NOT_REFRESHED')
