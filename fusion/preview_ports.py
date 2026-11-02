"""Closed synthetic preview facets over existing owners and declared atom ports.

No foreign SQL, model-selected endpoints, dynamic function resolution or code
execution. Each facet keeps its own journal and independent commits.
"""
from dataclasses import asdict
import json
from pathlib import Path
import uuid
from .contracts import canonical, digest, require
from .policy import Policy
from .ports import Mutation
from .registry import Descriptor, descriptor_read, selection_token
from .preview_history import PROFILE as HISTORY
from .preview_relations import PROFILE as RELATIONS
from .preview_workspace import PROFILE as WORKSPACE

COMPOSITION = 'synthetic-preview-facets/1'
ROUTE = '/preview/facets'
OPERATIONS = {
    'episodic.memory': {'authorize':1, 'recordEpisode':2, 'appendHistory':8, 'historySnapshot':1, 'readHistory':3},
    'relations': {'authorize':1, 'assertRelation':4, 'getRelation':2, 'retract':3, 'outgoing':4, 'incoming':4},
    'execution.workspace': {'authorize':1, 'read':1, 'version':1, 'write':4, 'append':4},
}
PROFILES = {'episodic.memory':HISTORY, 'relations':RELATIONS, 'execution.workspace':WORKSPACE}
ROLES = {'episodic.memory':'fusion-episodes','relations':'fusion-relations','execution.workspace':'fusion-execution'}


def descriptor(name):
    require(name in OPERATIONS, 'UNSUPPORTED_OPERATION')
    return Descriptor('preview-'+name, name, '1.0.0', '1.0.0', frozenset({PROFILES[name]}),
        frozenset(OPERATIONS[name]), frozenset({'scoped','idempotent','process-restart'}),131072,
        privacy='generated-shareable',features=frozenset({COMPOSITION}))


class Access:
    def __init__(self, path, credential, name):
        self.policy, self.credential, self.name = Policy(path),credential,name
        self.principal = self.policy.authenticate(credential)
        self.selected = descriptor(name)

    def selection(self): return selection_token(self.selected)

    def authorize(self, scope, operation):
        cfg = self.policy.current()
        require(cfg['composition'] == COMPOSITION and scope == cfg['scope'] and scope.startswith('synthetic-'), 'UNAUTHORIZED')
        require(self.policy.authenticate(self.credential) == self.principal, 'UNAUTHORIZED')
        require(descriptor_read(cfg['descriptors'][self.name]) == self.selected, 'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal,scope,self.name+'.'+operation)
        return self.principal


class Ports:
    def __init__(self, path, role, hook=lambda _: None, *, atoms_for=None):
        self.path,self.role,self.hook,self.atoms_for = Path(path),role,hook,atoms_for

    def invoke(self, credential, q):
        require(type(q) is dict and set(q)=={'id','composition','scope','interface','selection','operation','args'})
        from .lookup_contracts import identity
        identity(q['id']); require(q['composition']==COMPOSITION and len(canonical(q))<=131072,'UNSUPPORTED_PROFILE')
        name,op,args = q['interface'],q['operation'],q['args']
        require(type(name) is str and type(op) is str)
        require(name in ROLES and ROLES[name]==self.role and op in OPERATIONS[name], 'UNSUPPORTED_OPERATION')
        require(type(args) is list and len(args)==OPERATIONS[name][op])
        access=Access(self.path,credential,name); cfg=access.policy.current()
        require(q['selection']==access.selection(),'UNSUPPORTED_PROFILE')
        if op=='authorize':
            require(type(args[0]) is str)
            require(args[0] in OPERATIONS[name] and args[0]!='authorize','UNSUPPORTED_OPERATION')
            access.authorize(q['scope'],args[0])
            return dict(id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],
                        principal=access.principal,value={'authorized':True})
        access.authorize(q['scope'],op)
        root=Path(cfg['root']); root.mkdir(parents=True,exist_ok=True)
        if name=='execution.workspace':
            from .preview_workspace import Workspace
            def authorize(principal,scope,permission):
                require(principal==access.principal,'UNAUTHORIZED')
                access.authorize(scope,permission.split('.',1)[1])
            owner=Workspace(root/'workspace',root/'workspace.sqlite',authorize,scope=cfg['scope'],hook=self.hook)
            try:
                if op=='read': value=owner.read(access.principal,q['scope'],*args)
                elif op=='version': value=owner.version(access.principal,q['scope'],*args)
                else:
                    key,path,text,revision=args
                    value=owner.mutate(access.principal,q['scope'],key,op,path,text,revision)
            finally: owner.close()
        else:
            if self.atoms_for: atoms=self.atoms_for(access.principal)
            else:
                from .preview_atoms import client
                atoms=client(cfg['atom_clients'][access.principal])
            args=list(args)
            if op in ('recordEpisode','appendHistory','assertRelation','retract'):
                require(type(args[0]) is dict and set(args[0])=={'scope_ref','idempotency_key','intent_digest'})
                args[0]=Mutation(**args[0]); require(args[0].scope_ref==q['scope'],'UNAUTHORIZED')
            if name=='episodic.memory':
                from .preview_history import SessionHistoryOwner
                owner=SessionHistoryOwner(root/'session-history.sqlite',atoms,access,hook=self.hook)
                if op=='recordEpisode':value=owner.recordEpisode(*args)
                elif op=='appendHistory':value=owner.appendHistory(*args)
                elif op=='historySnapshot':value=owner.historySnapshot(*args)
                else:value=owner.readHistory(*args)
            else:
                from .preview_relations import RetractableRelations
                owner=RetractableRelations(root/'preview-relations.sqlite',atoms,access,cfg['schemas'],self.hook)
                if op=='assertRelation':
                    require(type(args[2]) is list)
                    require(all(type(role) is list and len(role)==2 for role in args[2]))
                    args[2]=tuple(tuple(role) for role in args[2])
                    value=owner.assertRelation(*args)
                elif op=='getRelation':value=owner.getRelation(*args)
                elif op=='retract':value=owner.retract(*args)
                else:value=owner.traverse(op,*args)
        access.authorize(q['scope'],op)
        result=dict(id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],principal=access.principal,value=value)
        require(len(canonical(result))<=131072,'OVERLOADED')
        return result


class Client:
    def __init__(self, path, name):
        self.path,self.name=Path(path),name
        self.cfg,self.frozen=self.current()

    def current(self):
        cfg=json.loads(self.path.read_text())
        require(cfg['composition']==COMPOSITION and cfg['placement'] in ('local','network') and cfg['fallback'] is False,'UNSUPPORTED_PROFILE')
        require(descriptor_read(cfg['descriptors'][self.name])==descriptor(self.name),'UNSUPPORTED_PROFILE')
        frozen={k:v for k,v in cfg.items() if k!='credential'}
        if cfg['placement']=='network': frozen={**frozen,'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
        return cfg,frozen

    def call(self,op,*args,deadline=None):
        cfg,frozen=self.current(); require(frozen==self.frozen,'CONFLICT')
        require(op in OPERATIONS[self.name] and len(args)==OPERATIONS[self.name][op],'UNSUPPORTED_OPERATION')
        wire=[asdict(a) if isinstance(a,Mutation) else a for a in args]
        q=dict(id=str(uuid.uuid4()),composition=COMPOSITION,scope=cfg['scope'],interface=self.name,
               selection=selection_token(descriptor(self.name)),operation=op,args=wire)
        if cfg['placement']=='local':
            value=Ports(cfg['provider_config'],ROLES[self.name]).invoke(cfg['credential'],q)
        else:
            from .preview_transport import invoke
            value=invoke(cfg,ROUTE,q,deadline=deadline)
        require(type(value) is dict and set(value)=={'id','request_digest','selection','principal','value'},'NOT_AVAILABLE')
        require((value['id'],value['request_digest'],value['selection'],value['principal'])==
                (q['id'],digest(canonical(q)),q['selection'],cfg['principal']),'NOT_AVAILABLE')
        return value['value']
