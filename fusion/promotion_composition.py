"""Local-only Attention selection and live policy; no cognitive/embedding dependency."""
import json
from pathlib import Path
import time
from . import promotion_contracts as c
from .contracts import require
from .policy import Policy
from .registry import Descriptor,Requirement,resolve,descriptor_read,selection_token


def descriptor(provider='sqlite'):
    require(provider in ('sqlite','file-fixture'),'UNSUPPORTED_PROFILE')
    return Descriptor('promotion-'+provider,'attention','3.0.0','0.5.0',frozenset({c.PROFILE}),frozenset(c.OPERATIONS),
        frozenset({'process-restart','scoped','idempotent','local-only'}),65536,privacy='private-local-only')

def select(catalogue):
    d=descriptor()
    return resolve(catalogue,Requirement(d.interface,d.version,'3.0.1',c.PROFILE,d.operations,d.guarantees,privacy=d.privacy))

class Access:
    def __init__(self,path,credential):
        self.policy=Policy(path);self.credential=credential;self.principal=self.policy.authenticate(credential)
        self.descriptor=select([descriptor_read(x) for x in self.policy.current()['catalogue']])
    def selection(self):return selection_token(self.descriptor)
    def authorize(self,scope,operation):
        cfg=self.policy.current();require(cfg['profile']==c.PROFILE and cfg['placement']=='local' and cfg['privacy']=='private-local-only','UNSUPPORTED_PROFILE')
        require(self.policy.authenticate(self.credential)==self.principal and cfg['scopes'].get(scope)==self.principal,'UNAUTHORIZED')
        require(operation in c.OPERATIONS,'UNSUPPORTED_OPERATION')
        require(selection_token(select([descriptor_read(x) for x in cfg['catalogue']]))==self.selection(),'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal,scope,'attention.'+operation);return self.principal

def configuration(path):
    cfg=json.loads(Path(path).read_text());require(cfg['placement']=='local','UNSUPPORTED_PROFILE')
    access=Access(cfg['policy'],cfg['credential']);access.authorize(cfg['scope'],'authorize')
    policy=access.policy.current()
    frozen={k:cfg[k] for k in ('placement','scope','context','output')}
    frozen.update(principal=access.principal,selection=access.selection(),profile=c.PROFILE,
        owner=policy['root'],runtime=policy['runtime'],clock=policy.get('clock_fixture','system-epoch-seconds'))
    return cfg,access,frozen

class PortOnly:
    def __init__(self,owner):self.__owner=owner
    def __getattr__(self,name):
        require(name in c.OPERATIONS,'UNSUPPORTED_OPERATION');return getattr(self.__owner,name)

def open_local(path,hook=lambda _:None):
    cfg,access,_=configuration(path);policy=access.policy.current();root=Path(policy['root']).resolve()
    for other in policy['other_roots']:
        other=Path(other).resolve();require(not root.is_relative_to(other) and not other.is_relative_to(root),'UNSUPPORTED_PROFILE')
    root.mkdir(parents=True,exist_ok=True,mode=0o700);root.chmod(0o700)
    require(access.descriptor.provider in ('promotion-sqlite','promotion-file-fixture'),'NOT_AVAILABLE')
    from .adapters.native_promotion import NativePromotion
    math=NativePromotion(policy['runtime']);clock=(lambda:policy['clock_fixture']) if 'clock_fixture' in policy else time.time
    if access.descriptor.provider=='promotion-sqlite':
        from .promotion import PromotionOwner
        owner=PromotionOwner(root/'attention.sqlite',access,math,clock=clock,hook=hook)
    else:
        from .adapters.file_promotion import FilePromotion
        owner=FilePromotion(root/'attention.json',access,math,clock=clock,hook=hook)
    return PortOnly(owner)
