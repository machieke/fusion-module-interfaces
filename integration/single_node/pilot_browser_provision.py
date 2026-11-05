"""Private synthetic browser provisioning data for the existing installer.

The caller writes returned secrets to its task-owned referenced Kubernetes
Secrets and private bootstrap files. Nothing is installed or printed here.
One explicitly selected scope per agent/user avoids ambient multi-scope reads.
"""
from hashlib import sha256
import re
import secrets
from fusion.contracts import require
from .pilot_browser_sessions import PROFILE


def provision(namespace,users,agents,*,cleanup=False,session_seconds=1800,credentials=None):
    require(type(namespace) is str and namespace.startswith('omega-ref-') and namespace!='omega-ref-live01','UNAUTHORIZED')
    require(type(users) is dict and 1<=len(users)<=16 and type(agents) is dict and 1<=len(agents)<=2)
    require(type(cleanup) is bool and type(session_seconds) is int and 30<=session_seconds<=3600)
    cfg=dict(profile=PROFILE,namespace=namespace,users={});owner_credentials={};bootstrap={}
    def token(role,key):
        if credentials is None:return secrets.token_urlsafe(32)
        value=credentials.get(role,{}).get(key)
        require(type(value) is str and 32<=len(value)<=256 and value.isascii(),'UNAUTHORIZED')
        return value
    for user,record in users.items():
        require(re.fullmatch('[a-z][a-z0-9-]{0,31}',user) and set(record)=={'role','scopes','credential_key'})
        require(record['role'] in ('viewer','developer','operator') and type(record['scopes']) is list)
        require(re.fullmatch('browser-[a-z0-9-]+-token',record['credential_key']))
        targets={}
        for role,agent in agents.items():
            require(role in ('omega-agent','omega-agent-b') and set(agent)=={'principal','scopes'} and agent['principal'] in ('A','B'))
            scopes=set(record['scopes'])&set(agent['scopes']);require(len(scopes)<=1,'UNSUPPORTED_PROFILE')
            if not scopes:continue
            scope=next(iter(scopes));require(scope.startswith('synthetic-'),'UNAUTHORIZED')
            owner_credentials.setdefault(role,{})[record['credential_key']]=token(role,record['credential_key'])
            target=dict(principal=agent['principal'],scope=scope,
                endpoint=dict(host=role+'.'+namespace+'.svc.cluster.local',port=8443,ca_file='/tls/ca.crt'),
                credential_file='/credentials/'+role+'/'+record['credential_key'])
            if cleanup and record['role']=='operator':
                key='browser-'+user+'-search-token';owner_credentials.setdefault('fusion-search',{}).setdefault(key,token('fusion-search',key))
                target['search_maintenance']=dict(profile='expired-unpublished-search-reclamation/1',
                    endpoint=dict(host='fusion-search.'+namespace+'.svc.cluster.local',port=8443,ca_file='/tls/ca.crt'),
                    credential_file='/credentials/fusion-search/'+key)
            targets[role]=target
        require(targets,'UNAUTHORIZED');bootstrap[user]=secrets.token_urlsafe(32)
        cfg['users'][user]=dict(bootstrap_sha256=sha256(bootstrap[user].encode()).hexdigest(),revision=1,
            role=record['role'],enabled=True,session_seconds=session_seconds,targets=targets)
    return dict(profile=PROFILE,gateway_configuration=cfg,owner_credentials=owner_credentials,bootstrap=bootstrap,
        required_secret_keys={role:sorted(values) for role,values in owner_credentials.items()},
        publication='PRIVATE_SECRET_OUTPUT_DO_NOT_PRINT_OR_COMMIT')
