"""Trusted private lookup composition, independent of all cognitive/chain runtimes."""
from dataclasses import dataclass
import os
from pathlib import Path
from . import lookup_contracts as c
from .contracts import canonical,digest,require,label
from .policy import Policy
from .registry import Descriptor,Requirement,resolve,descriptor_read,selection_token
from .responses import atom_write,envelope,availability

OPERATIONS={'atom.storage':('create','get','getMany','availability','head','readCommits'),
            'relations':('assertRelation','getRelation','outgoing','incoming'),
            'search':('query','catchUp','beginRebuild')}
PROFILES={'atom.storage':c.FEED,'relations':c.RELATIONS,'search':c.SEARCH}
VERSIONS={'atom.storage':'1.1.0','relations':'2.0.0','search':'2.0.0'}
GUARANTEES=frozenset({'process-restart','scoped','idempotent','local-only'})

def descriptors(storage='detta',search='sqlite',schemas=None):
    require(storage in ('detta','fixture-files') and search in ('sqlite','atomic-file-fixture'),'UNSUPPORTED_PROFILE')
    schema=c.schemas(schemas or c.SCHEMAS)
    names={'atom.storage':'feed-'+storage,'relations':'relations-sqlite','search':'search-'+search}
    return [Descriptor(names[name],name,VERSIONS[name],'0.5.0',frozenset({PROFILES[name]}),frozenset(ops),GUARANTEES,c.MAX_BYTES,
            privacy='private-local-only',features=frozenset({'schema:'+digest(canonical(schema))}) if name=='relations' else frozenset(),
            receipt_providers=frozenset({'detta-local-rs/1' if storage=='detta' else 'contract-fixture-files/1'})) for name,ops in OPERATIONS.items()]

def select(catalogue,name,schemas):
    return resolve(catalogue,Requirement(name,VERSIONS[name],VERSIONS[name][:-1]+'1',PROFILES[name],frozenset(OPERATIONS[name]),GUARANTEES,
        privacy='private-local-only',features=frozenset({'schema:'+digest(canonical(schemas))}) if name=='relations' else frozenset()))

class LookupAccess:
    def __init__(self,policy,credential,descriptor,schemas):
        self.policy,self.credential,self.descriptor,self.schemas=policy,credential,descriptor,c.copy(schemas)
        self.principal=policy.authenticate(credential)
    def selection(self):return selection_token(self.descriptor)
    def authorize(self,scope,operation):
        require(label(scope) and operation in self.descriptor.operations,'UNSUPPORTED_OPERATION')
        require(self.policy.authenticate(self.credential)==self.principal,'UNAUTHORIZED')
        config=self.policy.current();require(config.get('lookup_scopes',{}).get(scope)==self.principal,'UNAUTHORIZED')
        require(c.schemas(config['relation_schemas'])==self.schemas,'UNSUPPORTED_PROFILE')
        selected=select([descriptor_read(d) for d in config['lookup_descriptors']],self.descriptor.interface,self.schemas)
        require(selection_token(selected)==self.selection(),'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal,scope,self.descriptor.interface+'.'+operation);return self.principal

class AtomSession:
    def __init__(self,provider,access):self.provider,self.access=provider,access
    def create(self,command,content_type,data):
        c.mutation(command);self.access.authorize(command.scope_ref,'create')
        require(label(content_type) and type(data) is bytes);c.integer(len(data),1,c.MAX_BYTES)
        value=self.provider.create(command,content_type,data);atom_write(value,command.scope_ref,self.access.descriptor)
        require(value['ref']['digest']==digest(data),'NOT_AVAILABLE');self.access.authorize(command.scope_ref,'create');return c.copy(value)
    def get(self,ref):
        ref=c.ref(ref,c.scope_of(ref));self.access.authorize(ref['scope_ref'],'get')
        result=self.provider.get(ref);envelope(result,ref);require(len(result.bytes)<=c.MAX_BYTES,'NOT_AVAILABLE');self.access.authorize(ref['scope_ref'],'get');return result
    def getMany(self,refs):
        require(type(refs) is tuple and 1<=len(refs)<=8)
        refs=tuple(c.ref(r,c.scope_of(r)) for r in refs)
        for r in refs:self.access.authorize(r['scope_ref'],'getMany');self.access.authorize(r['scope_ref'],'get')
        result=self.provider.getMany(refs);require(type(result) is tuple and len(result)==len(refs),'NOT_AVAILABLE')
        for item,r in zip(result,refs):envelope(item,r);require(len(item.bytes)<=c.MAX_BYTES,'NOT_AVAILABLE');self.access.authorize(r['scope_ref'],'getMany');self.access.authorize(r['scope_ref'],'get')
        return result
    def availability(self,ref):
        ref=c.ref(ref,c.scope_of(ref));self.access.authorize(ref['scope_ref'],'availability');self.access.authorize(ref['scope_ref'],'get')
        result=self.provider.availability(ref);availability(result);require(result['content_hash']==ref['digest'],'NOT_AVAILABLE')
        self.access.authorize(ref['scope_ref'],'availability');return c.copy(result)
    def head(self,scope):
        self.access.authorize(scope,'head');value=c.head(self.provider.head(scope),scope);self.access.authorize(scope,'head');return value
    def observe(self,command):
        # Optional descriptor capability; old sessions cannot invoke it implicitly.
        c.mutation(command);self.access.authorize(command.scope_ref,'observe')
        value=self.provider.observe(command)
        from .atom_observation import observation
        value=observation(value,command.scope_ref,self.access.descriptor)
        self.access.authorize(command.scope_ref,'observe');return value
    def readCommits(self,scope,after,through,limit):
        self.access.authorize(scope,'readCommits');through=c.head(through,scope);c.integer(after,0,through['sequence']);c.integer(limit,1,c.PAGE)
        value=c.commits(self.provider.readCommits(scope,after,through,limit),scope,after,through,limit)
        self.access.authorize(scope,'readCommits');return value

@dataclass
class LookupModules:
    atoms: object
    relations: object
    search: object
    access: object
    root: Path
    selections: dict

def open_lookup(config_path,credential,scope,*,hook=lambda stage:None,wrap=lambda provider,names:provider):
    policy=Policy(config_path);config=policy.current();schemas=c.schemas(config['relation_schemas'])
    catalogue=[descriptor_read(d) for d in config['lookup_descriptors']]
    chosen={name:select(catalogue,name,schemas) for name in OPERATIONS}
    access={name:LookupAccess(policy,credential,descriptor,schemas) for name,descriptor in chosen.items()}
    # All data in this slice is private; caller grants do not imply module permissions.
    require(config.get('lookup_scopes',{}).get(scope)==policy.authenticate(credential),'UNAUTHORIZED')
    root=Path(config['lookup_root']).resolve()
    for location in config.get('shared_roots',[]):
        shared=Path(location).resolve();require(not root.is_relative_to(shared) and not shared.is_relative_to(root),'UNSUPPORTED_PROFILE')
    root.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(root,0o700)
    if chosen['atom.storage'].provider=='feed-detta':
        from .atom_feed import FeedAtomOwner
        from .adapters.detta import DettaStorage
        provider=FeedAtomOwner(root/'feed.sqlite',DettaStorage(config['detta_binary'],str(root/'payloads')),access['atom.storage'],hook)
    elif chosen['atom.storage'].provider=='feed-fixture-files':
        from .adapters.fixture_feed import FileFeedFixture
        provider=FileFeedFixture(root/'feed-fixture.json',access['atom.storage'],hook)
    else:require(False,'UNSUPPORTED_PROFILE')
    atoms=wrap(AtomSession(wrap(provider,OPERATIONS['atom.storage']),access['atom.storage']),OPERATIONS['atom.storage'])
    require(chosen['relations'].provider=='relations-sqlite','UNSUPPORTED_PROFILE')
    from .relations import RelationOwner
    relations=wrap(RelationOwner(root/'relations.sqlite',atoms,access['relations'],schemas,hook),OPERATIONS['relations'])
    suffix=digest(scope.encode())
    if chosen['search'].provider=='search-sqlite':
        from .search import SearchOwner
        projection=SearchOwner(root/('search-'+suffix+'.sqlite'),atoms,atoms,access['search'],scope,hook)
    elif chosen['search'].provider=='search-atomic-file-fixture':
        from .adapters.fixture_search import FileSearchFixture
        projection=FileSearchFixture(root/('search-'+suffix+'.json'),atoms,atoms,access['search'],scope,hook)
    else:require(False,'UNSUPPORTED_PROFILE')
    return LookupModules(atoms,relations,wrap(projection,OPERATIONS['search']),access,root,{n:selection_token(d) for n,d in chosen.items()})
