"""Fresh synthetic scope partitions within the existing service owners.

Only trusted configuration selects a directory. A request selects a scope, and
must authenticate in that scope before a port or its journal is constructed.
Each partition uses the existing contracts and owner implementations unchanged.
"""
import copy
import json
from pathlib import Path

from fusion.contracts import require
from fusion.policy import Policy
from .configure import write
from .sustained_runtime import template_files, runtime_digest

PROFILE='synthetic-private-native-scopes/1'
ROLES={'fusion-storage','fusion-search','fusion-embedding','fusion-model',
       'fusion-episodes','fusion-beliefs','fusion-attention','fusion-relations'}


def configure(settings,cfg,state,run):
    p=settings['preview']
    if not p['sustained'].get('private_scopes',False):return cfg
    require(p['sustained']['private_scopes'] is True and p.get('cognition',{}).get('enabled'),'UNSUPPORTED_PROFILE')
    role=settings['role'];routes={}
    for agent,spec in p['agents'].items():
        if role not in ROLES and role!=agent:continue
        scope=spec['private_scope'];label='private-'+spec['principal'].lower()
        shadow=copy.deepcopy(settings);q=shadow['preview']
        q['sustained']['private_scopes']=False;q['scope']=scope
        q['agents']={agent:{k:v for k,v in spec.items() if k!='private_scope'}}
        q['agents'][agent]['facets']=[x for x in spec['facets'] if x!='execution.workspace']
        q['memory']['corpus']+='-'+label
        # No private session can delegate or approve a chain disclosure merely
        # through a command. Shared projection has separate operator authority.
        q['tasks']={'enabled':False};q['inspection']={'enabled':False};q['chain']={'enabled':False}
        q['agents'][agent]['tools']=[x for x in spec['tools'] if x not in ('delegate','inspect-atom','read-file','write-file','append-file','metta')]
        private_state=state/'scopes'/label;private_run=run/'scopes'/label
        shadow.update(state=str(private_state),run=str(private_run))
        from .sustained_configure import configure as selected
        _,owned,_,_=selected(shadow)
        # The historical memory recipe starts with A. A B-only partition must
        # remove that bootstrap grant, including embedding and index metadata.
        for file in private_run.rglob('*.json'):
            value=json.loads(file.read_bytes())
            if type(value.get('principals')) is dict:
                for who in ('A','B'):
                    if who!=spec['principal'] and who in value['principals']:
                        value['principals'][who].get('scopes',{}).pop(scope,None)
                write(file,value)
        if role in ROLES:
            routes[scope]=dict(directory=str(private_run),state=str(private_state))
        if role==agent:
            seed=spec['sessions'][0];files=template_files(private_run/'templates'/'shared')
            def normalize(value):
                if type(value) is str:
                    return value.replace(str(private_run/'sessions'/seed),str(run/'sessions'/seed)).replace(
                        str(private_state/'sessions'/seed),str(state/'sessions'/seed))
                if type(value) is list:return [normalize(x) for x in value]
                if type(value) is dict:return {k:normalize(v) for k,v in value.items()}
                return value
            files=normalize(files)
            files['application.json']['private_diagnostics']='bounded-stages-only/1'
            directory=run/'templates'/'private';directory.mkdir(parents=True,exist_ok=True)
            for name,value in files.items():write(directory/name,value)
            binding=copy.deepcopy(owned['native_sessions']['allocation']['templates']['shared'])
            ca=Path(settings.get('secret_directory','/secrets'))/'ca.crt'
            binding['runtime_digest']=runtime_digest(files,ca)
            cfg['native_sessions']['allocation']['templates']['private']=binding
            cfg['native_sessions']['runtime_templates']['private']=dict(seed_session=seed,directory=str(directory),ca_file=str(ca))
            cfg['principals']['operator']['scopes'][p['scope']].append('sessions.project')
            for actor in ('operator','worker'):
                cfg['principals'][actor]['scopes'][scope]=list(cfg['principals'][actor]['scopes'][p['scope']])
    if routes:cfg['scope_routes']=dict(profile=PROFILE,scopes=routes)
    return cfg


class ScopeRouter:
    """Only the selected scope's existing port may observe its owned records."""
    def __init__(self,path,role,hook=lambda _:None):
        self.path,self.role,self.hook=Path(path),role,hook
        self.search={}

    def selection(self,scope):
        cfg=json.loads(self.path.read_bytes()).get('scope_routes')
        require(cfg is not None and cfg['profile']==PROFILE,'UNSUPPORTED_PROFILE')
        require(type(scope) is str and scope in cfg['scopes'],'UNAUTHORIZED')
        return cfg['scopes'][scope]

    @staticmethod
    def scope(q):
        require(type(q) is dict)
        intent=q.get('intent',{})
        require(type(intent) is dict)
        return q.get('scope',intent.get('scope'))

    def matches(self,q):
        cfg=json.loads(self.path.read_bytes()).get('scope_routes',{})
        scope=self.scope(q)
        return type(scope) is str and scope in cfg.get('scopes',{})

    def invoke(self,path,credential,q,kernel=None):
        scope=self.scope(q);selected=self.selection(scope)
        directory=Path(selected['directory'])
        filename='cognitive-owner.json' if path in ('/reference-cognition','/preview/owner-state') else 'facet-owner.json' if path=='/preview/facets' else 'owner.json'
        config=directory/filename
        require(config.is_file(),'UNSUPPORTED_OPERATION')
        policy=Policy(config);actor=policy.authenticate(credential)
        require(policy.current()['principals'][actor].get('scopes',{}).get(scope),'UNAUTHORIZED')
        # Existing ports perform full method, selection, mixed-scope and result
        # validation again. This outer check prevents metadata/constructor leaks.
        if path=='/preview/owner-state':
            require(self.role=='fusion-attention','UNSUPPORTED_OPERATION')
            from fusion.sustained_observation import invoke
            return invoke(config,credential,q)
        if path=='/reference-cognition':
            from fusion.cognitive_services import Ports
            return Ports(config,self.role,self.hook).invoke(path,credential,q)
        if path=='/preview/facets':
            from fusion.preview_ports import Ports
            return Ports(config,self.role,self.hook).invoke(credential,q)
        if path=='/preview/memory':
            from fusion.preview_memory_services import Ports
            return Ports(config,self.role,self.hook).invoke(credential,q)
        if path=='/preview/model':
            from fusion.preview_model_binding import service
            owner=service(config,self.hook)
            try:return owner.invoke(credential,q)
            finally:owner.close()
        if path=='/s03-encode':
            from fusion.embedding_service import EmbeddingService
            require(self.role=='fusion-embedding','UNSUPPORTED_OPERATION')
            owner=EmbeddingService(config,kernel,self.hook)
            try:return owner.invoke(credential,q)
            finally:owner.close()
        require(path in ('/s03-append','/s03-read','/memory-source','/memory-initial'),'UNSUPPORTED_OPERATION')
        if self.role=='fusion-search':
            require(scope in self.search,'NOT_AVAILABLE')
            return self.search[scope].invoke(path,credential,q)
        require(self.role=='fusion-storage','UNSUPPORTED_OPERATION')
        from fusion.memory_services import StoragePorts
        return StoragePorts(config,self.hook).invoke(path,credential,q)

    def initialize_search(self):
        from .memory_host import SearchHost
        cfg=json.loads(self.path.read_bytes())['scope_routes']
        for scope,selected in cfg['scopes'].items():
            owner=SearchHost(Path(selected['directory'])/'owner.json',self.hook)
            owner.initialize(Path(selected['state']));self.search[scope]=owner
