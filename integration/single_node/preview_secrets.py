"""Fresh scoped Secret material for the preview; never stored in values."""
import secrets
from pathlib import Path
from fusion.contracts import require


def selection(path):
    import yaml
    value=yaml.safe_load(Path(path).read_text());p=value['preview']
    require(p['enabled'] is True and p['model_boundary']=='RECORDED_FIXTURE','UNAUTHORIZED')
    require(set(p['agents']) <= {'omega-agent','omega-agent-b'} and p['agents']['omega-agent']['principal']=='A','UNSUPPORTED_PROFILE')
    if 'omega-agent-b' in p['agents']:require(p['agents']['omega-agent-b']['principal']=='B','UNSUPPORTED_PROFILE')
    roles=['omega-agent','fusion-execution','fusion-storage','fusion-messaging']
    for role,cfg in value.get('components',{}).items():
        if cfg.get('enabled',True) and role not in roles:roles.append(role)
    require('fusion-model' in roles and set(p['agents'])<=set(roles),'INVALID_ARGUMENT')
    return p,tuple(roles)


def material(p,roles,client):
    result={role:{} for role in roles}
    principals=[a['principal'] for a in p['agents'].values()]
    calls={who:{role:(client[role] if who=='A' else secrets.token_hex(32)) for role in roles if role not in p['agents']} for who in principals}
    atoms={who:secrets.token_hex(32) for who in principals}
    facets={role:{who:secrets.token_hex(32) for who in principals} for role in ('fusion-execution','fusion-episodes','fusion-relations') if role in roles}
    delegated={role:{who:secrets.token_hex(32) for who in principals} for role in ('fusion-episodes','fusion-relations') if role in roles}
    for agent,a in p['agents'].items():
        who=a['principal']
        result[agent].update({role+'-token':v for role,v in calls[who].items()})
        result[agent].update({'atom-'+who+'-token':atoms[who],
            'session-operator-token':secrets.token_hex(32),'session-worker-token':secrets.token_hex(32)})
        for role in facets:result[agent]['facet-'+role+'-token']=facets[role][who]
    for role in calls[principals[0]]:
        for who in principals:result[role]['caller-'+who+'-token']=calls[who][role]
    for who in principals:result['fusion-storage']['cog-caller-'+who+'-token']=atoms[who]
    if p.get('sustained',{}).get('storage_archive'):
        from fusion.archive_contracts import policy
        policy(p['sustained']['storage_archive'])
        result['fusion-storage']['archive-operator-token']=secrets.token_hex(32)
    for role in facets:
        for who in principals:result[role]['facet-caller-'+who+'-token']=facets[role][who]
    for role in delegated:
        for who in principals:
            result[role]['atom-'+who+'-token']=delegated[role][who]
            result['fusion-storage']['delegated-'+role+'-'+who+'-token']=delegated[role][who]
    if p.get('memory',{}).get('enabled'):
        source=secrets.token_hex(32)
        result['fusion-storage']['indexer-token']=source
        result['fusion-search']['storage-source-token']=source
        result['fusion-search']['indexer-token']=secrets.token_hex(32)
        if p['memory'].get('maintenance_profile'):
            from fusion.preview_deployment_contracts import SEARCH_MAINTENANCE_PROFILE as PROFILE
            require(p['memory']['maintenance_profile']==PROFILE,'UNSUPPORTED_PROFILE')
            result['fusion-search']['search-operator-token']=secrets.token_hex(32)
    if p.get('cognition',{}).get('enabled'):
        require({'fusion-episodes','fusion-beliefs','fusion-attention'}<=set(roles),'NOT_AVAILABLE')
        for agent,a in p['agents'].items():
            who=a['principal']
            for role in ('fusion-episodes','fusion-beliefs','fusion-attention'):
                value=secrets.token_hex(32);result[agent]['cognitive-'+role+'-token']=value
                result[role]['cognitive-caller-'+who+'-token']=value
            for role in ('fusion-episodes','fusion-beliefs'):
                value=secrets.token_hex(32);result[role]['cognitive-storage-'+who+'-token']=value
                result['fusion-storage']['cognition-'+role+'-'+who+'-token']=value
            value=secrets.token_hex(32);result['fusion-beliefs']['cognitive-episodes-'+who+'-token']=value
            result['fusion-episodes']['completion-relay-'+who+'-token']=value
    if p.get('tasks',{}).get('enabled'):
        for role,agent in p['agents'].items():
            who=agent['principal'];mailbox=secrets.token_hex(32);storage=secrets.token_hex(32)
            result[role]['task-mailbox-token']=mailbox
            result['fusion-messaging']['task-caller-'+who+'-token']=mailbox
            result['fusion-messaging']['task-storage-'+who+'-token']=storage
            result['fusion-storage']['task-storage-'+who+'-token']=storage
            if p.get('profile')=='omega-single-node-sustained-preview/1':
                binding=secrets.token_hex(32)
                result[role]['task-binding-token']=binding
                result['fusion-messaging']['task-binding-'+who+'-token']=binding
            for target,other in p['agents'].items():
                if target==role:continue
                value=secrets.token_hex(32)
                result[role]['task-wake-'+other['principal']+'-token']=value
                result[target]['task-ingress-'+who+'-token']=value
    if p.get('inspection',{}).get('enabled'):
        for agent,a in p['agents'].items():
            for role in ('fusion-execution','fusion-messaging'):
                value=secrets.token_hex(32);result[agent]['inspect-'+role+'-token']=value
                result[role]['inspect-caller-'+a['principal']+'-token']=value
        value=secrets.token_hex(32);result['fusion-execution']['inspect-storage-token']=value
        result['fusion-storage']['inspect-storage-token']=value
        value=secrets.token_hex(32);result['fusion-execution']['inspect-completion-token']=value
        result['fusion-messaging']['inspect-completion-token']=value
    if p.get('chain',{}).get('enabled'):
        require({'fusion-commitment','f1r3node'}<=set(roles) and p.get('inspection',{}).get('enabled'),'UNSUPPORTED_PROFILE')
        for who in ('A','B'):
            value=secrets.token_hex(32)
            for role in ('fusion-commitment','fusion-execution'):result[role]['commit-observer-'+who+'-token']=value
        value=secrets.token_hex(32)
        for role in ('fusion-commitment','fusion-storage'):result[role]['commit-storage-token']=value
    return {role:{key:value.encode() for key,value in values.items()} for role,values in result.items()}
