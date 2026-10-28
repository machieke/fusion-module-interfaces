"""Closed append ports over existing AtomStorage/feed and Search owners."""
import json
from pathlib import Path
import time

from . import append_contracts as c, vector_contracts as v
from .contracts import canonical,digest,require,decode,encode
from .policy import Policy
from .registry import descriptor_read,selection_token
from .ports import Mutation
from .lookup_composition import AtomSession
from .vector_enrollment import validate_inputs


def configuration(path):
    cfg=json.loads(Path(path).read_text())
    require(cfg['profile']==c.PROFILE and cfg['sharing']==v.PRIVACY and cfg['fallback'] is False,'UNSUPPORTED_PROFILE')
    c.a.identity(cfg['session']);require(cfg['model']==v.EMBEDDING,'UNSUPPORTED_PROFILE')
    require(type(cfg['inputs']) is dict and 1<=len(cfg['inputs'])<=16)
    for raw,helper in cfg['inputs'].items():c.text(raw,helper,cfg['scope'],cfg['corpus'])
    chosen=c.select([descriptor_read(d) for d in cfg['catalogue']])
    frozen={k:cfg[k] for k in ('profile','sharing','principal','scope','corpus','session','model','inputs','placement','metadata_root')}
    frozen['selections']={n:selection_token(d) for n,d in chosen.items()}
    if cfg['placement']=='service-network':
        from .memory_services import freeze_placement
        frozen.update(freeze_placement(cfg, ('atom.storage', 'search')))
        return cfg,chosen,frozen
    if cfg['placement']=='network':
        require('provider_config' not in cfg,'UNSUPPORTED_PROFILE')
        frozen['endpoint']={**cfg['endpoint'],'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
    else:
        require(cfg['placement']=='local','UNSUPPORTED_PROFILE');frozen['provider_config']=cfg['provider_config']
    return cfg,chosen,frozen


class Access:
    def __init__(self,policy,credential,descriptor):
        self.policy,self.credential,self.descriptor=policy,credential,descriptor
        self.principal=policy.authenticate(credential)
    def authorize(self,scope,operation):
        cfg=self.policy.current()['memory_append']
        require(scope==cfg['scope'] and operation in self.descriptor.operations,'UNAUTHORIZED')
        require(self.policy.authenticate(self.credential)==self.principal and self.principal in cfg['writers'],'UNAUTHORIZED')
        require(self.principal==cfg['session_principal'],'UNAUTHORIZED')
        chosen=c.select([descriptor_read(d) for d in cfg['catalogue']])
        require(selection_token(chosen[self.descriptor.interface])==selection_token(self.descriptor),'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal,scope,'memory.append.'+('write' if operation in ('create','build') else 'disclose'))
        self.policy.check(self.principal,scope,self.descriptor.interface+'.'+operation)
        return self.principal


class AppendService:
    def __init__(self,path,credential,hook=lambda _:None,*,atoms=None,policy=None):
        self.policy=policy or Policy(path);self.config=self.policy.current()['memory_append'];self.credential=credential;self.hook=hook
        self.chosen=c.select([descriptor_read(d) for d in self.config['catalogue']])
        self.access={n:Access(self.policy,credential,d) for n,d in self.chosen.items()}
        if atoms is None:
            from .atom_feed import FeedAtomOwner
            from .adapters.detta import DettaStorage
            cfg=self.config;root=Path(cfg['root'])
            owner=FeedAtomOwner(root/'feed.sqlite',DettaStorage(cfg['detta_binary'],str(root/'payloads')),self.access['atom.storage'],hook)
            atoms=AtomSession(owner,self.access['atom.storage'])
        self.atoms=atoms

    def authorize(self,accepted,mode):
        cfg=self.policy.current()['memory_append'];principal=self.policy.authenticate(self.credential)
        require(principal==accepted['principal'] and principal in cfg['writers'],'UNAUTHORIZED')
        require(principal==cfg['session_principal'],'UNAUTHORIZED')
        require(cfg['scope']==accepted['scope'] and cfg['session']==accepted['session'],'UNAUTHORIZED')
        require(cfg['sharing']==v.PRIVACY and cfg['corpus']==accepted['corpus'] and cfg['model']==accepted['model'],'UNSUPPORTED_PROFILE')
        require(accepted['content'] in cfg['inputs'] and cfg['inputs'][accepted['content']]==accepted['helper_input'],'UNAUTHORIZED')
        selected=c.select([descriptor_read(d) for d in cfg['catalogue']])
        require(all(accepted['selections'][n]==selection_token(d) for n,d in selected.items()),'UNSUPPORTED_PROFILE')
        require(accepted['selections']['embedding']==cfg['embedding_selection'],'UNSUPPORTED_PROFILE')
        self.policy.check(principal,accepted['scope'],'memory.append.'+mode)

    def observe(self,accepted,role):
        return self.atoms.observe(Mutation(accepted['scope'],c.key(accepted,role)))

    def bound(self,accepted):
        value=c.observation(self.observe(accepted,'binding'),accepted['scope'],self.chosen['atom.storage'],
                            content_type=c.BINDING,data=c.binding_bytes(accepted))
        require(value['found'],'NOT_AVAILABLE')

    def search(self):
        from .adapters.chroma_vector import ChromaVector
        cfg=self.config
        return ChromaVector(Path(cfg['root'])/'search',self.atoms,self.atoms,self.access['search'],
                            cfg['scope'],cfg['corpus'],cfg['model'],self.hook)

    def invoke(self,request):
        c.request(request,self.chosen)
        accepted=request['intent'];op=request['operation'];body=request['body'];scope=accepted['scope']
        self.authorize(accepted,'disclose')
        if op=='authorize':self.authorize(accepted,body['mode']);value={'authorized':True}
        elif op=='observe':
            if body['role']!='binding':self.bound(accepted)
            value=self.observe(accepted,body['role'])
            if body['role']=='binding' and value['found']:
                require(value['write']['ref']['digest']==digest(c.binding_bytes(accepted)),'CONFLICT')
        elif op=='create':
            self.authorize(accepted,'write');role=body['role'];data=decode(body['data'])
            if role!='binding':self.bound(accepted)
            # Return prior owner acceptance even after expiry; no new mutation then.
            seen=c.observation(self.observe(accepted,role),scope,self.chosen['atom.storage'],content_type=body['content_type'],data=data)
            if seen['found']:value=seen['write']
            else:
                require(time.time_ns()//1_000_000<=accepted['deadline_ms'],'DEADLINE_EXCEEDED')
                if role=='enrollment':
                    p,vector=validate_inputs(self.atoms,json.loads(data))
                    require(p==c.payload(accepted) and digest(v.vector_bytes(vector))==accepted['vector_sha256'],'CONFLICT')
                value=self.atoms.create(Mutation(scope,c.key(accepted,role)),body['content_type'],data)
                self.hook('after_append_'+role+'_acceptance')
        elif op=='get':
            self.bound(accepted)
            require(body['ref']['digest'] in (digest(canonical(c.payload(accepted))),accepted['vector_sha256']),'UNAUTHORIZED')
            item=self.atoms.get(body['ref']);value=dict(ref=item.ref,content_type=item.content_type,data=encode(item.bytes))
        else:
            self.bound(accepted)
            seen=c.observation(self.observe(accepted,'enrollment'),scope,self.chosen['atom.storage'],content_type=v.ENROLLMENT)
            require(seen['found'] and seen['through']==body['through'],'CONFLICT')
            maintenance='remember-'+accepted['occurrence']
            if op=='published':value=self.search().published(scope,body['through'],maintenance)
            else:
                self.authorize(accepted,'write')
                value=self.search().build_named(scope,body['through'],maintenance,accepted['deadline_ms'])
        self.authorize(accepted,'disclose')
        return dict(request_id=request['request_id'],request_digest=digest(canonical(request)),selection=request['selection'],
                    principal=accepted['principal'],value=value)
