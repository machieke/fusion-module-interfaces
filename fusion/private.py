"""Trusted private local composition; never a shared-wire or publication binding."""
from dataclasses import dataclass
import json
import os
from pathlib import Path

from .atoms import AtomOwner, AuthorizedAtoms
from .contracts import ContractError, canonical, label, require, validate_ref
from .memory_contracts import EPISODE_PROFILE, BELIEF_PROFILE, MODEL, RUNTIME, mutation
from .policy import Policy
from .ports import AtomStorage, Mutation, EpisodicMemory, BeliefRevision
from .registry import Descriptor, Requirement, descriptor_read, descriptor_wire, resolve, selection_token

OPERATIONS = {
    'atom.storage': ('create', 'get', 'getMany', 'availability'),
    'episodic.memory': ('recordEpisode', 'appendEvent', 'readEpisode', 'readEvidence',
                        'pendingEvidence', 'acknowledgeEvidence'),
    'belief.revision': ('submitEvidence', 'readBelief'),
}
PROFILES = {'atom.storage': 'immutable-bytes/1', 'episodic.memory': EPISODE_PROFILE,
            'belief.revision': BELIEF_PROFILE}


def descriptors():
    result = []
    for name, operations in OPERATIONS.items():
        result.append(Descriptor('private-local-' + name, name,
            '1.0.0' if name == 'atom.storage' else '2.0.0', '0.2.0',
            frozenset({PROFILES[name]}), frozenset(operations),
            frozenset({'process-restart', 'scoped', 'idempotent', 'local-only'}),
            65536, privacy='private-local-only',
            features=frozenset({MODEL, RUNTIME}) if name == 'belief.revision' else frozenset(),
            receipt_providers=frozenset({'detta-local-rs/1'})))
    return result


def select(catalogue, name):
    version = '1.0.0' if name == 'atom.storage' else '2.0.0'
    return resolve(catalogue, Requirement(name, version, version[:-1] + '1', PROFILES[name],
        frozenset(OPERATIONS[name]), frozenset({'process-restart', 'scoped', 'idempotent', 'local-only'}),
        privacy='private-local-only',
        features=frozenset({MODEL, RUNTIME}) if name == 'belief.revision' else frozenset()))


class PrivateAccess:
    def __init__(self, policy, credential, descriptor):
        self.policy, self.credential, self.descriptor = policy, credential, descriptor
        self.principal = policy.authenticate(credential)

    def selection(self):
        return selection_token(self.descriptor)

    def authorize(self, scope, operation):
        require(label(scope) and (operation in self.descriptor.operations or
                (self.descriptor.interface == 'belief.revision' and operation == 'assume')), 'UNSUPPORTED_OPERATION')
        require(self.policy.authenticate(self.credential) == self.principal, 'UNAUTHORIZED')
        current = self.policy.current()
        require(current.get('private_scopes', {}).get(scope) == self.principal, 'UNAUTHORIZED')
        try:
            chosen = select([descriptor_read(d) for d in current['private_descriptors']], self.descriptor.interface)
        except (KeyError, TypeError, ValueError):
            raise ContractError('UNSUPPORTED_PROFILE') from None
        require(selection_token(chosen) == self.selection(), 'UNSUPPORTED_PROFILE')
        self.policy.check(self.principal, scope, self.descriptor.interface + '.' + operation)
        return self.principal

    def origin(self, scope, source):
        value = self.policy.current().get('origins', {}).get(scope, {}).get(source)
        require(value is None or label(value), 'UNSUPPORTED_PROFILE')
        return value


class PrivateAtoms:
    """Validates local input and reauthenticates before the existing atom facade."""
    def __init__(self, provider: AtomStorage, access: PrivateAccess):
        self.access = access
        self.port = AuthorizedAtoms(provider, access.policy, access.principal, access.descriptor)

    def create(self, command: Mutation, content_type: str, data: bytes):
        mutation(command)
        self.access.authorize(command.scope_ref, 'create')
        require(label(content_type) and type(data) is bytes and 0 < len(data) <= 65536)
        return self.port.create(command, content_type, data)

    def get(self, ref):
        validate_ref(ref, ref.get('scope_ref') if type(ref) is dict else '')
        self.access.authorize(ref['scope_ref'], 'get')
        return self.port.get(ref)

    def getMany(self, refs):
        require(type(refs) is tuple and 1 <= len(refs) <= 16)
        for ref in refs:
            validate_ref(ref, ref.get('scope_ref') if type(ref) is dict else '')
            self.access.authorize(ref['scope_ref'], 'getMany')
        return self.port.getMany(refs)

    def availability(self, ref):
        validate_ref(ref, ref.get('scope_ref') if type(ref) is dict else '')
        self.access.authorize(ref['scope_ref'], 'availability')
        return self.port.availability(ref)


@dataclass
class PrivateModules:
    atoms: AtomStorage
    episodes: EpisodicMemory
    beliefs: BeliefRevision | None
    root: Path


def open_private(config_path, credential, scope, *, with_revision=True, hook=lambda stage: None,
                 atom_fixture=None, math_fixture=None):
    """Concrete choices occur here only. Fixture arguments are explicit test seams."""
    policy = Policy(config_path)
    config = policy.current()
    catalogue = [descriptor_read(d) for d in config['private_descriptors']]
    accesses = {name: PrivateAccess(policy, credential, select(catalogue, name)) for name in OPERATIONS}
    accesses['episodic.memory'].authorize(scope, 'readEpisode')
    root = Path(config['private_root']).resolve()
    for path in config.get('shared_roots', []):
        shared = Path(path).resolve()
        require(not root.is_relative_to(shared) and not shared.is_relative_to(root), 'UNSUPPORTED_PROFILE')
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(root, 0o700)
    if atom_fixture is None:
        from .adapters.detta import DettaStorage
        provider = AtomOwner(str(root / 'atoms.sqlite'), DettaStorage(config['detta_binary'], str(root / 'payloads')))
    else:
        provider = atom_fixture
    require(isinstance(provider, AtomStorage), 'UNSUPPORTED_PROFILE')
    atoms = PrivateAtoms(provider, accesses['atom.storage'])
    from .episodes import EpisodeOwner
    episodes = EpisodeOwner(root / 'episodes.sqlite', atoms, accesses['episodic.memory'], hook=hook)
    beliefs = None
    if with_revision:
        from .beliefs import BeliefOwner
        if math_fixture is None:
            from .adapters.pln_revision import GuardedRevision
            math_provider = GuardedRevision(config['revision_environment'])
        else:
            math_provider = math_fixture
        beliefs = BeliefOwner(root / 'beliefs.sqlite', atoms, episodes, accesses['belief.revision'],
                              math_provider, hook=hook)
    return PrivateModules(atoms, episodes, beliefs, root)
