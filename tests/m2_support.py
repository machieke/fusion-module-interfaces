"""Explicit fixture composition and generated private test records."""
from dataclasses import replace
import json
import os
from pathlib import Path
import secrets
import tempfile

from fusion import memory_contracts as c
from fusion.contracts import canonical, digest
from fusion.ports import Mutation, EvidenceSubmission
from fusion.private import descriptors, OPERATIONS, open_private
from fusion.registry import descriptor_wire
from fusion.adapters.fixture_atoms import FileAtomFixture

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'private-memory'


class GuardOnlyFixture:
    """No formula implementation. Native numerical tests use GuardedRevision."""
    def __init__(self): self.calls = []
    def profile(self): return {'provider': 'guard-only-fixture', 'model': c.MODEL}
    def revise(self, existing, incoming, revision, independence):
        self.calls.append((existing, incoming, revision, independence))
        assert independence is None, 'Fixture cannot execute numerical revision'
        return {'status': 'UNKNOWN', 'detail': 'fixture: independence unspecified', 'proposal': None}


class PortOnly:
    """A consumer cannot inspect a wrapped provider's owner/database attributes."""
    def __init__(self, target, names):
        methods = {name: getattr(target, name) for name in names}
        object.__setattr__(self, '_methods', methods)
        # Python 3.12 runtime Protocol checks use getattr_static. Expose exactly
        # the admitted ports as real attributes while preserving the hostile
        # private-access guard below; dynamic __getattribute__ alone is invisible.
        for name, method in methods.items():
            object.__setattr__(self, name, method)
    def __getattribute__(self, name):
        if name.startswith('__'): return object.__getattribute__(self, name)
        methods = object.__getattribute__(self, '_methods')
        if name in methods: return methods[name]
        raise AssertionError('Foreign private access: ' + name)


def truth(strength='0.75', confidence='0.5'):
    return {'model': c.MODEL, 'strength': strength, 'confidence': confidence, 'evidence_count': None}


class MemoryHarness:
    def __init__(self, root=None, *, real=False, with_revision=True, hook=lambda stage: None):
        self.temp = tempfile.TemporaryDirectory(prefix='fusion-private-m2-') if root is None else None
        self.root = Path(root or self.temp.name); self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / 'private-config.json'
        self.real, self.with_revision, self.hook = real, with_revision, hook
        self.math = GuardOnlyFixture()
        self.credential = 'local-test-' + secrets.token_hex(16)
        providers = descriptors()
        if not real:
            providers = [replace(d, receipt_providers=frozenset({'contract-fixture-files/1'})) for d in providers]
        methods = [name + '.' + op for name, ops in OPERATIONS.items() for op in ops] + ['belief.revision.assume']
        self.config = {'private_root': str(self.root / 'private'), 'shared_roots': [str(self.root / 'shared')],
            'private_scopes': {SCOPE: 'owner'}, 'private_descriptors': [descriptor_wire(d) for d in providers],
            'principals': {'owner': {'credential': self.credential, 'scopes': {SCOPE: methods}}},
            'origins': {SCOPE: {'sensor-a': 'origin-a', 'sensor-b': 'origin-b', 'speaker-a': 'origin-a'}},
            'detta_binary': os.environ.get('M2_DETTA_BINARY', str(ROOT / 'artifacts/detta-build/target/debug/fusion-detta-adapter')),
            'revision_environment': os.environ.get('M2_REVISION_ENV', str(ROOT / 'artifacts/m2/revision-environment.json'))}
        self.save(); self.reopen()

    def save(self):
        self.path.write_bytes(canonical(self.config)); self.path.chmod(0o600)

    def reopen(self):
        fixture = None if self.real else PortOnly(FileAtomFixture(str(self.root / 'private/files'),
            str(self.root / 'private/bytes')), OPERATIONS['atom.storage'])
        self.modules = open_private(self.path, self.credential, SCOPE, with_revision=self.with_revision,
            hook=self.hook, atom_fixture=fixture, math_fixture=None if self.real else self.math)
        self.atoms, self.episodes, self.beliefs = self.modules.atoms, self.modules.episodes, self.modules.beliefs
        return self

    def close(self):
        if self.temp: self.temp.cleanup()

    def claim(self, key='claim', positive=True):
        return self.atoms.create(Mutation(SCOPE, key), 'application/fusion-claim',
            canonical({'predicate': 'available', 'arguments': ['resource'], 'positive': positive}))['ref']

    def episode(self, key='episode'):
        return self.episodes.recordEpisode(Mutation(SCOPE, key), 'sensor-a')['ref']

    def event(self, claim=None, occurrence='observation-a', source='sensor-a', strength='0.75', confidence='0.5',
              provenance=None, relationship='supports', context='generated', numeric=True):
        payload = self.atoms.create(Mutation(SCOPE, 'payload/' + occurrence), 'text/plain',
                                    b'Generated private observation; no automatic truth extraction.')['ref']
        return {'occurrence_id': occurrence, 'kind': 'observation', 'source': source,
            'observed_time': '2026-10-16T00:00:00Z', 'payload': payload, 'causation': [],
            'provenance': provenance or [], 'numerical': None if not numeric else {
                'claim': claim or self.claim(), 'context': context, 'relationship': relationship,
                'truth': None if relationship == 'reports' else truth(strength, confidence), 'ingestion_profile': c.INGESTION}}

    def append(self, episode, event, head=0, key=None):
        return self.episodes.appendEvent(Mutation(SCOPE, key or 'append/' + event['occurrence_id']), episode, head, event)

    def submit(self, claim, evidence=None, support_id=None, key='submit', expected=None, independence=None, context='generated'):
        snapshot = self.beliefs.readBelief(claim, context, None)
        request = EvidenceSubmission(Mutation(SCOPE, key), claim, context, evidence, support_id,
            snapshot['revision'] if expected is None else expected, c.BELIEF_PROFILE,
            snapshot['runtime_selection'], independence)
        return self.beliefs.submitEvidence(request)


def assumption(a, b):
    return {'model_id': 'generated-independent-sensors/v1', 'supports': [a, b], 'status': 'assumption'}


def support_identity(record):
    return 'support/' + digest(canonical(record))
