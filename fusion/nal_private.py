"""Explicit local S04 composition. No HTTP binding or publication route."""
from dataclasses import dataclass
import os
from pathlib import Path
from . import nal_memory_contracts as c, delivery_contracts as d
from .contracts import canonical,digest,require
from .registry import Descriptor,Requirement,resolve,descriptor_read,selection_token
from .policy import Policy
from .private import PrivateAtoms
from .atoms import AtomOwner
from .nal_episodes import NalEpisodeOwner
from .nal_beliefs import NalBeliefOwner
from .nal_relay import NalEvidenceRelay

OPERATIONS={
    'atom.storage':('create','get','getMany','availability'),
    'episodic.memory':('recordEpisode','appendEvent','readEpisode','readEvidence','pendingEvidence','acknowledgeDelivery','occurrenceIdentity','readOccurrence'),
    'belief.revision':('registerPrior','submitEvidence','readBelief','observeDecision')}


def descriptors():
    return [Descriptor('private-neoclaw-'+name,name,'1.0.0' if name=='atom.storage' else '4.0.0','0.4.0',
        frozenset({profile}),frozenset(OPERATIONS[name]),frozenset({'process-restart','scoped','idempotent','local-only'}),65536,
        privacy='private-local-only',features=frozenset({c.MODEL,c.RUNTIME}) if name=='belief.revision' else frozenset(),
        receipt_providers=frozenset({'detta-local-rs/1'})) for name,profile in
        [('atom.storage','immutable-bytes/1'),('episodic.memory',c.EPISODE_PROFILE),('belief.revision',c.BELIEF_PROFILE)]]


def select(catalogue,name):
    reference=next(x for x in descriptors() if x.interface==name)
    return resolve(catalogue,Requirement(name,reference.version,reference.version[:-1]+'1',next(iter(reference.profiles)),
        reference.operations,reference.guarantees,privacy=reference.privacy,features=reference.features))


class Access:
    def __init__(self,policy,credential,descriptor,*,completion=False):
        self.policy,self.credential,self.descriptor=policy,credential,descriptor
        self.principal=policy.authenticate(credential);self.completion=completion
    def selection(self):return selection_token(self.descriptor)
    def authorize(self,scope,operation):
        current=self.policy.current();require(current['profile']==c.PROFILE,'UNSUPPORTED_PROFILE')
        require(current['placement']=='local' and current['privacy']=='private-local-only','UNSUPPORTED_PROFILE')
        require(operation in self.descriptor.operations or (self.descriptor.interface=='belief.revision' and operation=='assume'),'UNSUPPORTED_OPERATION')
        require(self.policy.authenticate(self.credential)==self.principal,'UNAUTHORIZED')
        require(current['private_scopes'].get(scope)==self.principal,'UNAUTHORIZED')
        chosen=select([descriptor_read(x) for x in current['private_descriptors']],self.descriptor.interface)
        require(selection_token(chosen)==self.selection(),'UNSUPPORTED_PROFILE')
        if operation=='acknowledgeDelivery':require(self.completion,'UNAUTHORIZED')
        self.policy.check(self.principal,scope,self.descriptor.interface+'.'+operation);return self.principal
    def origin(self,scope,source):
        self.authorize(scope,'appendEvent')
        value=self.policy.current().get('origins',{}).get(scope,{}).get(source)
        if value is not None:c.identifier(value)
        return value
    def assumption(self,scope,value):
        self.authorize(scope,'assume');c.independence(value)
        require(value['model_id'] in self.policy.current()['assumptions'],'UNAUTHORIZED')
    def completionConsumer(self,scope):
        self.authorize(scope,'acknowledgeDelivery');value=self.policy.current()['evidence_consumer'];d.consumer(value)
        require(value['principal']==self.principal,'UNAUTHORIZED');return value


@dataclass
class Modules:
    atoms: object
    episodes: object
    beliefs: object
    relay: object
    access: object
    root: Path


def configuration(path,credential,scope):
    policy=Policy(path);cfg=policy.current();catalogue=[descriptor_read(x) for x in cfg['private_descriptors']]
    access={name:Access(policy,credential,select(catalogue,name)) for name in OPERATIONS}
    for name,operation in [('atom.storage','get'),('episodic.memory','readEpisode'),('belief.revision','readBelief')]:access[name].authorize(scope,operation)
    frozen={k:cfg[k] for k in ('profile','placement','privacy','private_root','origins','assumptions','evidence_consumer','runtime','detta_binary')}
    frozen.update(principal=policy.authenticate(credential),scope=scope,selections={n:a.selection() for n,a in access.items()})
    return cfg,access,frozen


def open_local(path,credential,scope,*,hook=lambda _:None,with_revision=True,wrap=lambda obj,names:obj):
    cfg,access,_=configuration(path,credential,scope)
    root=Path(cfg['private_root']).resolve()
    for shared in cfg.get('shared_roots',[]):
        shared=Path(shared).resolve();require(not root.is_relative_to(shared) and not shared.is_relative_to(root),'UNSUPPORTED_PROFILE')
    root.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(root,0o700)
    from .adapters.detta import DettaStorage
    atoms=wrap(PrivateAtoms(AtomOwner(str(root/'atoms.sqlite'),DettaStorage(cfg['detta_binary'],str(root/'payloads'))),access['atom.storage']),OPERATIONS['atom.storage'])
    episodes=wrap(NalEpisodeOwner(root/'episodes.sqlite',atoms,access['episodic.memory'],hook=hook),OPERATIONS['episodic.memory'][:-3]+('occurrenceIdentity','readOccurrence'))
    beliefs=relay=None
    if with_revision:
        from .adapters.neoclaw_revision import NativeTruthRevision
        beliefs=wrap(NalBeliefOwner(root/'beliefs.sqlite',atoms,episodes,access['belief.revision'],NativeTruthRevision(cfg['runtime']),hook=hook),OPERATIONS['belief.revision'])
        consumer=cfg['evidence_consumer'];d.consumer(consumer)
        chosen=access['belief.revision'].descriptor
        require(consumer==dict(principal=access['belief.revision'].principal,provider=chosen.provider,profile=c.BELIEF_PROFILE,selection=selection_token(chosen)),'UNSUPPORTED_PROFILE')
        ack_access=Access(Policy(path),credential,access['episodic.memory'].descriptor,completion=True)
        ack=wrap(NalEpisodeOwner(root/'episodes.sqlite',atoms,ack_access,hook=hook),('acknowledgeDelivery',))
        relay=NalEvidenceRelay(root/'relay.sqlite',episodes,beliefs,hook=hook,consumer=consumer,access=access['belief.revision'],acknowledger=ack)
    return Modules(atoms,episodes,beliefs,relay,access,root)
