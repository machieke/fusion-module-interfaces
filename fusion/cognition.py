"""Trusted M3 composition. New profiles require fresh private owner journals."""
from dataclasses import dataclass
from . import cognition_contracts as c
from . import attention_contracts as a
from . import delivery_contracts as d
from .contracts import ContractError, canonical, digest, require
from .private import open_private
from .ports import AtomStorage, EpisodeJournal, DerivedBeliefRevision, Attention, PLNKernel, InferenceControl
from .policy import Policy
from .registry import Descriptor, Requirement, resolve, descriptor_read, selection_token

OPERATIONS={'belief.revision':('submitEvidence','readBelief','submitDerivation','readDerivation'),
            'attention':('profile','submitStimulus','readAttention','select','advance'),
            'pln.kernel':('profile','applyRule'),'inference.control':('step',)}
PROFILES={'belief.revision':c.BELIEF_PROFILE,'attention':a.PROFILE,'pln.kernel':c.RULE,'inference.control':c.CONTROL}
VERSIONS={'belief.revision':'3.0.0','attention':'2.0.0','pln.kernel':'2.0.0','inference.control':'2.0.0'}
GUARANTEES=frozenset({'scoped','local-only','process-restart','idempotent'})


def contract(name, closure=False):
    operations, profile, version = OPERATIONS[name], PROFILES[name], VERSIONS[name]
    if closure and name == 'attention':
        operations += ('submitFeedback', 'resolveFeedback'); profile = a.CLOSURE_PROFILE; version = '2.1.0'
    if closure and name == 'inference.control':
        operations += ('readProgress', 'reconcile'); profile = c.CLOSURE_CONTROL; version = '2.1.0'
    return operations, profile, version


def descriptors(attention_provider='sqlite', *, closure=False):
    require(attention_provider in ('sqlite','atomic-file-fixture'),'UNSUPPORTED_PROFILE')
    return [Descriptor(('private-'+attention_provider if name=='attention' else 'private-m3')+'-'+name,name,contract(name,closure)[2],'0.3.1' if closure and name in ('attention','inference.control') else '0.3.0',
        frozenset({contract(name,closure)[1]}),frozenset(contract(name,closure)[0]),GUARANTEES,65536,privacy='private-local-only',
        features=frozenset({c.RUNTIME,c.MODEL}) if name in ('pln.kernel','belief.revision') else frozenset())
        for name,operations in OPERATIONS.items()]


def select(catalogue,name, *, closure=False):
    operations,profile,version=contract(name,closure)
    return resolve(catalogue,Requirement(name,version,version[:-1]+'1',profile,frozenset(operations),GUARANTEES,
        privacy='private-local-only',features=frozenset({c.RUNTIME,c.MODEL}) if name in ('pln.kernel','belief.revision') else frozenset()))


class CognitionAccess:
    def __init__(self,policy,credential,descriptor,role=None):
        self.policy,self.credential,self.descriptor,self.role=policy,credential,descriptor,role
        self.principal=policy.authenticate(credential)
    def selection(self):return selection_token(self.descriptor)
    def authorize(self,scope,operation):
        require(operation in self.descriptor.operations or (self.descriptor.interface=='attention' and operation in ('ingress','feedback')) or
                (self.descriptor.interface=='belief.revision' and operation=='assume'),'UNSUPPORTED_OPERATION')
        require(self.policy.authenticate(self.credential)==self.principal,'UNAUTHORIZED')
        current=self.policy.current();require(current.get('private_scopes',{}).get(scope)==self.principal,'UNAUTHORIZED')
        chosen=select([descriptor_read(d) for d in current['cognition_descriptors']],self.descriptor.interface,closure=current.get('delivery_closure')==d.CONFIG)
        require(selection_token(chosen)==self.selection(),'UNSUPPORTED_PROFILE')
        if operation in ('ingress','feedback'):require(operation==self.role,'UNAUTHORIZED')
        self.policy.check(self.principal,scope,self.descriptor.interface+'.'+operation);return self.principal
    def authorizeClosure(self,scope,selections):
        current=self.policy.current()
        require(current.get('delivery_closure')==d.CONFIG,'UNSUPPORTED_PROFILE')
        catalogue=[descriptor_read(x) for x in current['cognition_descriptors']]
        for name,key in [('attention','attention'),('belief.revision','beliefs'),('inference.control','controller')]:
            require(selection_token(select(catalogue,name,closure=True))==selections[key],'UNSUPPORTED_PROFILE')
        require(selection_token(select(catalogue,'pln.kernel',closure=True))==self.closure_kernel_selection,'UNSUPPORTED_PROFILE')
        for operation in ('attention.resolveFeedback','attention.feedback','belief.revision.readBelief'):
            self.policy.check(self.principal,scope,operation)
    def origin(self,scope,source):return self.policy.current().get('origins',{}).get(scope,{}).get(source)


@dataclass
class CognitionModules:
    atoms: AtomStorage
    episodes: EpisodeJournal
    beliefs: DerivedBeliefRevision
    attention: Attention
    kernel: PLNKernel
    controller: InferenceControl
    selections: dict
    root: object
    relay: object = None


def open_cognition(config_path,credential,scope,*,hook=lambda stage:None,atom_fixture=None,math_fixture=None,kernel_fixture=None,wrap=lambda p,n:p):
    # M1/M2 composition continues owning C0 and C1; no new shared transport.
    policy=Policy(config_path);config=policy.current();catalogue=[descriptor_read(d) for d in config['cognition_descriptors']]
    require(config.get('delivery_closure') in (None,d.CONFIG),'UNSUPPORTED_PROFILE')
    closure=config.get('delivery_closure')==d.CONFIG
    selected={name:select(catalogue,name,closure=closure) for name in OPERATIONS}
    access={name:CognitionAccess(policy,credential,d) for name,d in selected.items()}
    consumer={'principal':policy.authenticate(credential),'provider':selected['belief.revision'].provider,
              'profile':c.BELIEF_PROFILE,'selection':selection_token(selected['belief.revision'])} if closure else None
    if closure: require(config.get('evidence_consumer')==consumer,'UNSUPPORTED_PROFILE')
    private=open_private(config_path,credential,scope,with_revision=False,hook=hook,atom_fixture=atom_fixture,completion_consumer=consumer)
    if closure: access['inference.control'].closure_kernel_selection=selection_token(selected['pln.kernel'])
    for name,operation in [('belief.revision','readBelief'),('inference.control','step')]:access[name].authorize(scope,operation)
    if math_fixture is None:
        from .adapters.pln_deduction import GuardedRevisionWithAncestry
        math=GuardedRevisionWithAncestry(config['revision_environment'])
    else:math=math_fixture
    if kernel_fixture is None:
        from .adapters.pln_deduction import GuardedDeduction
        kernel=GuardedDeduction(config['deduction_environment'])
    else:kernel=kernel_fixture
    require(config['attention_provider'] in ('sqlite','atomic-file-fixture'),'UNSUPPORTED_PROFILE')
    require(selected['attention'].provider=='private-'+config['attention_provider']+'-attention','UNSUPPORTED_PROFILE')
    if config['attention_provider']=='sqlite':
        from .attention import AttentionOwner
        provider=AttentionOwner;filename='attention.sqlite'
    else:
        from .adapters.fixture_attention import FileAttentionFixture
        provider=FileAttentionFixture;filename='attention.json'
    root=private.root
    ingress=provider(root/filename,CognitionAccess(policy,credential,selected['attention'],'ingress'),config['attention_policy'],hook=hook,closure=closure)
    feedback=provider(root/filename,CognitionAccess(policy,credential,selected['attention'],'feedback'),config['attention_policy'],hook=hook,closure=closure)
    atoms=wrap(private.atoms,('create','get','getMany','availability'))
    episodes=wrap(private.episodes,('recordEpisode','appendEvent','readEpisode','readEvidence','pendingEvidence') if closure else ('recordEpisode','appendEvent','readEpisode','readEvidence','pendingEvidence','acknowledgeEvidence'))
    from .derived_beliefs import DerivedBeliefOwner
    beliefs=DerivedBeliefOwner(root/'derived-beliefs.sqlite',atoms,episodes,access['belief.revision'],math,wrap(kernel,('profile','applyRule')),hook=hook)
    selections={'attention':selection_token(selected['attention']),'beliefs':selection_token(selected['belief.revision']),
                'kernel':digest(canonical(kernel.profile())),'controller':selection_token(selected['inference.control'])}
    from .inference import InferenceOwner
    controller=InferenceOwner(root/'inference.sqlite',atoms,wrap(beliefs,OPERATIONS['belief.revision']),
        wrap(feedback,contract('attention',closure)[0]),access['inference.control'],selections,hook=hook,closure=closure)
    relay=None
    if closure:
        from .evidence_relay import EvidenceRelay
        relay=EvidenceRelay(root/'delivery-relay.sqlite',episodes,wrap(beliefs,OPERATIONS['belief.revision']),hook=hook,
            consumer=consumer,access=access['belief.revision'],acknowledger=wrap(private.completion_episodes,('acknowledgeDelivery',)))
    return CognitionModules(atoms,episodes,beliefs,ingress,kernel,controller,selections,root,relay)
