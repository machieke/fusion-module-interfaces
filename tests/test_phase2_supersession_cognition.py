"""P09 cognitive isolation across actual lifecycle/application transitions.

Real owners: MemoryLifecycle, NalEpisodeOwner, NalBeliefOwner, PromotionOwner,
SessionHistoryOwner and RetractableRelations. Actual SharedMemory.written,
PreviewEvidence.refresh/materialize and NativeRelations presentation compose
their ports. AtomStorage, vector publication, metadata, transport, application
bootstrap and numerical responses are explicit fixtures. No native arithmetic,
Chroma, E5, DeTTa, HTTPS, pod or native-loop integration claim is made.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from fusion import nal_memory_contracts as n, promotion_contracts as p
from fusion import vector_contracts as v, preview_vector_contracts as active
from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.adapters.neoclaw_revision import NativeTruthRevision
from fusion.contracts import canonical, digest, require
from fusion.nal_beliefs import NalBeliefOwner
from fusion.nal_episodes import NalEpisodeOwner
from fusion.ports import Mutation
from fusion.preview_history import SessionHistoryOwner
from fusion.preview_lifecycle import MemoryLifecycle
from fusion.preview_native_cognition import PreviewEvidence
from fusion.preview_native_history import NativeHistory
from fusion.preview_native_memory import SharedMemory
from fusion.preview_native_relations import NativeRelations, SCHEMAS
from fusion.preview_relations import RetractableRelations
from fusion.promotion import PromotionOwner
from fusion.vector_enrollment import enroll


SCOPE = 'synthetic-supersession-cognition'
CORPUS = 'fixture-supersession-corpus'
CONTEXT = 'fixture-memory-context'
CLOCK = 2000000000.


class AuthorityFixture:
    """Single scoped principal; explicitly not a network/policy qualification."""
    def __init__(self, name): self.name = name
    def authorize(self, scope, operation):
        require(scope == SCOPE, 'UNAUTHORIZED')
        return 'A'
    def selection(self): return digest(('fixture-authority/' + self.name).encode())
    def origin(self, scope, source):
        self.authorize(scope, 'appendEvent')
        return 'fixture-root-authority' if source == 'synthetic-observer' else None
    def assumption(self, scope, declaration):
        self.authorize(scope, 'assume')
        require(declaration['model_id'] == 'explicit-fixture-independence', 'UNAUTHORIZED')


class RecordedRevisionFixture(NativeTruthRevision):
    """Existing proposal/validation logic, one authored numerical reply only."""
    def __init__(self): self.calls = []
    def profile(self): return {'classification': 'authored-response-fixture', 'case': 'prior-plus-contrary'}
    def evaluate(self, a, b, deadline_ms):
        require(a == n.stv('1.0', '0.5') and b == n.stv('0.0', '0.5'), 'CONFLICT')
        self.calls.append((copy.deepcopy(a), copy.deepcopy(b), deadline_ms))
        return self.parse('true\n(stv 0.5 0.6666666666666666)\n')


class RecordedPriorityFixture:
    """Closed authored-response table, no replacement promotion arithmetic."""
    def __init__(self): self.calls = []
    def evaluate(self, rows, deadline_ms):
        self.calls.append((copy.deepcopy(rows), deadline_ms))
        table = {(0., 0., CLOCK, 0): 0., (0., 0., CLOCK, 1): 1.,
                 (1., CLOCK, CLOCK, 0): 1.}
        require(all(tuple(row) in table for row in rows), 'INVALID_ARGUMENT')
        return [table[tuple(row)] for row in rows]


class DirectOwnerPort:
    """Fixture transport calls actual public owner operations only."""
    def __init__(self, owner, access):
        self.owner, self.access, self.calls = owner, access, []
        self.frozen = {'fixture': type(owner).__name__}
    def call(self, operation, *args, deadline=None):
        self.calls.append((operation, copy.deepcopy(args), deadline))
        if operation == 'authorize':
            self.access.authorize(SCOPE, args[0]); return {'authorized': True}
        if operation == 'change': return self.owner.change(args[0], args[1], **args[2])
        if operation in ('outgoing', 'incoming'): return self.owner.traverse(operation, *args)
        if operation == 'assertRelation':
            command, schema, roles, directed = args
            return self.owner.assertRelation(command, schema, tuple(tuple(role) for role in roles), directed)
        return getattr(self.owner, operation)(*args)


class PublicationFixture:
    """No retrieval claim: snapshot derives from the real lifecycle membership."""
    frozen = {'fixture': 'authoritative-membership-publication'}
    def __init__(self, lifecycle): self.lifecycle, self.snapshots, self.calls = lifecycle, {}, []
    def call(self, operation, *args, deadline=None):
        self.calls.append((operation, copy.deepcopy(args), deadline))
        if operation == 'current': return self.snapshots.get(canonical(args[0]))
        if operation == 'published': return None
        if operation == 'build':
            source, head, identity, accepted_deadline = args
            require(accepted_deadline == deadline, 'CONFLICT')
            membership = self.lifecycle.activeSet(head)
            snapshot = dict(generation=str(uuid.uuid5(uuid.NAMESPACE_URL, identity)),
                head=source, corpus=CORPUS, embedding=v.FIXTURE, index=v.INDEX,
                profile=active.PROFILE, lifecycle=head, active_digest=digest(canonical(membership)))
            snapshot['logical'] = digest(canonical({k: value for k, value in snapshot.items() if k != 'generation'}))
            active.snapshot(snapshot, SCOPE)
            self.snapshots[canonical(head)] = snapshot
            return snapshot
        require(operation == 'ready', 'UNSUPPORTED_OPERATION')
        active.snapshot(args[0], SCOPE)
        require(self.snapshots[canonical(args[0]['lifecycle'])] == args[0], 'CONFLICT')
        return {'ready': True}


class SupersessionCognitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-supersession-')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.deadline = time.time_ns() // 1000000 + 30000
        self.access = {name: AuthorityFixture(name) for name in
            ('atoms', 'lifecycle', 'episodes', 'beliefs', 'attention', 'history', 'relations')}
        self.atoms = FileFeedFixture(self.root/'fixture-atoms.json', self.access['atoms'])
        self.lifecycle = MemoryLifecycle(self.root/'lifecycle.sqlite', self.atoms,
            self.access['lifecycle'], SCOPE, CORPUS, embedding=v.FIXTURE)
        self.episodes = NalEpisodeOwner(self.root/'episodes.sqlite', self.atoms, self.access['episodes'])
        self.math = RecordedRevisionFixture()
        self.beliefs = NalBeliefOwner(self.root/'beliefs.sqlite', self.atoms, self.episodes,
            self.access['beliefs'], self.math)
        self.priority_math = RecordedPriorityFixture()
        self.priority = PromotionOwner(self.root/'priority.sqlite', self.access['attention'],
            self.priority_math, clock=lambda: CLOCK)
        self.relations = RetractableRelations(self.root/'relations.sqlite', self.atoms,
            self.access['relations'], SCHEMAS)
        self.history_owner = SessionHistoryOwner(self.root/'history.sqlite', self.atoms, self.access['history'])
        self.ports = {'memory.lifecycle': DirectOwnerPort(self.lifecycle, self.access['lifecycle']),
                      'search': PublicationFixture(self.lifecycle)}
        db = sqlite3.connect(self.root/'application-fixture.sqlite'); db.row_factory = sqlite3.Row
        self.addCleanup(db.close)
        db.executescript('''CREATE TABLE app_read_views(id TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE app_active_view(singleton INTEGER PRIMARY KEY,view TEXT NOT NULL);''')
        initial = dict(metadata=dict(records=[], promotion_time=0.), beliefs=[], defaults={})
        db.execute('INSERT INTO app_read_views VALUES(?,?)', ('empty', canonical(initial).decode()))
        db.execute('INSERT INTO app_active_view VALUES(1,?)', ('empty',)); db.commit()
        atom_cfg = self.root/'fixture-atom-client.json'
        atom_cfg.write_bytes(canonical({'fixture': 'FileFeedFixture', 'credential': 'synthetic-unused'}))
        self.write_states = {}
        self.app = SimpleNamespace(db=db, config={'active_memory_configs': {n:n for n in self.ports},
            'memory_atoms_config': str(atom_cfg), 'history_atoms_config': str(atom_cfg)},
            binding={'principal': 'A', 'active_memory': {n:x.frozen for n,x in self.ports.items()},
                'memory_atoms': {'fixture':'FileFeedFixture'}, 'history_atoms': {'fixture':'FileFeedFixture'}},
            preview_config={'scope':SCOPE}, evidence_enabled=True, session=str(uuid.uuid4()), hook=lambda _:None,
            write=SimpleNamespace(settings=lambda: ({'metadata_root':str(self.root/'metadata-fixture')}, None),
                state=lambda row:self.write_states[row['id']]))
        self.app.preview = SimpleNamespace(relations=None)
        self.evidence = PreviewEvidence.__new__(PreviewEvidence)
        self.evidence.app, self.evidence.db = self.app, db
        self.evidence.settings = lambda: {'scope':SCOPE}
        self.evidence.modules = SimpleNamespace(atoms=self.atoms, episodes=self.episodes, beliefs=self.beliefs,
            root=self.root, access={'episodic.memory':self.access['episodes'], 'belief.revision':self.access['beliefs']})
        self.app.evidence = self.evidence
        for target, replacement in (
            ('fusion.preview_native_memory.Client', lambda cfg, name:self.ports[name]),
            ('fusion.preview_native_memory.atoms_client', lambda *args:self.atoms),
            ('fusion.adapters.neoclaw_metadata.collection', lambda *args, **kwargs:None)):
            mock = patch(target, replacement); mock.start(); self.addCleanup(mock.stop)
        self.memory = SharedMemory(self.app); self.app.preview.memory = self.memory
        history = NativeHistory(self.app, DirectOwnerPort(self.history_owner, self.access['history']))
        history.atoms = lambda deadline=None:self.atoms
        self.app.preview.history = history
        self.native_relations = NativeRelations(self.app, DirectOwnerPort(self.relations, self.access['relations']))
        self.app.preview.relations = self.native_relations

    def write(self, identity, content, predecessor=None):
        uid = str(uuid.uuid5(uuid.NAMESPACE_URL, SCOPE+'/'+identity))
        timestamp = '2026-11-02 12:00:00' if predecessor is None else '2026-11-02 12:00:01'
        enrolled = enroll(self.atoms, SCOPE, CORPUS, v.FIXTURE, uid,
            dict(scope=SCOPE, corpus=CORPUS, uuid=uid, time=timestamp, content=content), [1.]+[0.]*1023)
        self.write_states[identity] = dict(uuid=uid, receipts=canonical({'enrollment':{'ref':enrolled}}).decode())
        row = dict(id=identity, deadline=self.deadline,
            premises=canonical({'operation':'update' if predecessor else 'remember'}).decode())
        if predecessor:
            with self.app.db: self.memory.admit(identity, predecessor)
        return row, uid, self.memory.written(row)

    def prior_claim(self, uid, view):
        target = view['handles'][uid]['envelope']['target']; stamp = view['handles'][uid]['time']
        creation = self.atoms.create(Mutation(SCOPE, uid+'/creation'), 'application/neoclaw-fresh-creation',
            canonical(dict(policy=n.PRIOR, memory_uuid=uid, occurrence=uid, time=stamp, **target)))['ref']
        claim = self.atoms.create(Mutation(SCOPE, uid+'/claim'), 'application/fusion-claim',
            canonical(dict(predicate='neoclaw-memory-assessment', arguments=[creation['digest']], positive=True)))['ref']
        prior = self.beliefs.registerPrior(Mutation(SCOPE, uid+'/prior'), claim, CONTEXT, creation, self.deadline)
        return claim, prior

    def seeded_predecessor(self):
        _, uid, view = self.write('predecessor', 'Synthetic predecessor with contrary evidence')
        claim, prior = self.prior_claim(uid, view)
        episode = self.episodes.recordEpisode(Mutation(SCOPE, 'source-episode'), 'synthetic-observer')['ref']
        source_payload = self.atoms.create(Mutation(SCOPE, 'source-payload'), 'application/neoclaw-source',
            canonical(dict(text='Synthetic contrary report', label='contrary-source', source='synthetic-observer',
                observed_time='2026-11-02T12:00:00Z')))['ref']
        source_command = Mutation(SCOPE, 'source')
        source = self.episodes.appendEvent(source_command, episode, 0,
            dict(occurrence_id=self.episodes.occurrenceIdentity(source_command, episode), kind='observation',
                source='synthetic-observer', observed_time='2026-11-02T12:00:00Z', payload=source_payload,
                causation=[], provenance=[], numerical=None, deadline_ms=self.deadline))['evidence']
        assessment_command = Mutation(SCOPE, 'contrary-assessment')
        receipt = self.episodes.appendEvent(assessment_command, episode, 1,
            dict(occurrence_id=self.episodes.occurrenceIdentity(assessment_command, episode), kind='action',
                source='agent', observed_time='2026-11-02T12:00:00Z', payload=source_payload,
                causation=[], provenance=[source], numerical=dict(claim=claim, context=CONTEXT,
                    relationship='contradicts', truth=n.stv('0.0','0.5'), ingestion_profile=n.INGESTION),
                deadline_ms=self.deadline))
        record = self.episodes.readEvidence(receipt['evidence'])
        declaration = dict(model_id='explicit-fixture-independence', supports=[prior['aggregate'],n.contribution(record)], status='assumption')
        request = n.Admission(Mutation(SCOPE, 'admit-contrary'), claim, CONTEXT, receipt['evidence'], None,
            prior['revision'], n.BELIEF_PROFILE, prior['runtime_selection'], declaration,
            work_id=receipt['delivery_id'], deadline_ms=self.deadline, max_evaluations=n.MAX_EVALUATIONS)
        decision = self.beliefs.submitEvidence(request)
        snapshot = decision['snapshot']; self.assertEqual(snapshot['truth'], n.stv('0.5','0.6666666666666666'))
        self.assertEqual(len(self.math.calls), 1)
        # Fixture application acceptance imports a real owner snapshot. The
        # production validation below checks every C1/C2/payload binding.
        view = copy.deepcopy(view)
        view['metadata']['records'][0].update(stv=[.5, .6666666666666666],
            links=[view['handles'][uid]['time'], 'contrary-source'])
        view['beliefs'] = [dict(uuid=uid, claim=claim, context=CONTEXT, revision=snapshot['revision'],
            snapshot_digest=digest(canonical(snapshot)), sources=[dict(ref=source,label='contrary-source')],
            creation_time=view['handles'][uid]['time'])]
        view['defaults'] = {}; view['metadata_seal'] = digest(canonical(view['metadata']))
        self.evidence.materialize(view, self.deadline)
        key = digest(canonical(view))
        with self.app.db:
            self.app.db.execute('INSERT INTO app_read_views VALUES(?,?)', (key,canonical(view).decode()))
            self.app.db.execute('UPDATE app_active_view SET view=?', (key,))
        bound = self.priority.bind(self.priority_request('promote', [uid], 'adjust'))
        adjusted = self.priority.adjust(bound); self.assertEqual(adjusted['value'], 1.)
        history = self.app.preview.history
        history.record('structural-history', 'input-receipt', dict(observed_ms=self.deadline-10000,
            text='Synthetic administrative history'), deadline=self.deadline)
        with self.app.db:
            self.native_relations.admit('predecessor-link', 'link',
                dict(memory=view['handles'][uid]['envelope']['handle'], history=history.handle()))
        linked = json.loads(self.native_relations.replay(dict(id='predecessor-link',result=None,deadline=self.deadline),'link'))
        view = self.memory.prepare('predecessor-with-cognition', self.deadline)
        self.evidence.validate_view(view)
        self.assertEqual(len(view['handles'][uid]['structure']['links']), 1)
        return dict(uid=uid, view=view, view_key=digest(canonical(view)), claim=claim, snapshot=snapshot,
            source=source, evidence=receipt['evidence'], episode=episode, priority=adjusted,
            source_record=self.episodes.readEvidence(source), evidence_record=record,
            episode_view=self.episodes.readEpisode(episode,1,8), relation=linked['relation']['target'])

    def priority_request(self, identity, targets, kind='scores'):
        return p.request(dict(profile=p.PROFILE, selection=self.access['attention'].selection(), principal='A',
            scope=SCOPE, context=CONTEXT, id=identity, kind=kind, targets=targets,
            delta=1 if kind=='adjust' else 0, limit=1 if kind=='adjust' else len(targets), deadline_ms=self.deadline))

    def assert_isolated(self, before, successor, view):
        self.assertEqual(set(view['handles']), {successor})
        self.assertEqual(view['beliefs'], [])
        self.assertEqual(view['defaults'], {successor:n.PRIOR+':not-registered'})
        self.assertEqual(view['metadata']['records'], [dict(uuid=successor,
            links=[view['handles'][successor]['time']], stv=[1.,.5], promotion=0.)])
        self.assertEqual(view['handles'][successor]['structure']['links'], [])
        self.assertEqual(self.beliefs.readBelief(before['claim'], CONTEXT, None), before['snapshot'])
        self.assertEqual(self.episodes.readEpisode(before['episode'],1,8), before['episode_view'])
        self.assertEqual(before['episode_view']['head'], 2)
        self.assertEqual(self.episodes.readEvidence(before['source']), before['source_record'])
        self.assertEqual(self.episodes.readEvidence(before['evidence']), before['evidence_record'])
        self.assertEqual(before['evidence_record']['event']['provenance'], [before['source']])
        self.assertEqual(before['evidence_record']['event']['numerical']['relationship'], 'contradicts')
        self.assertTrue(before['evidence_record']['lineage_roots'])
        self.assertEqual(self.priority.observe(before['priority']['binding']), before['priority'])
        scores = self.priority.scores(self.priority.bind(self.priority_request('after-'+successor,[before['uid'],successor])))
        self.assertEqual(scores['scores'], [dict(target=before['uid'],score=1.),dict(target=successor,score=0.)])
        predecessor_payload = before['view']['handles'][before['uid']]['envelope']['target']['payload']
        successor_payload = view['handles'][successor]['envelope']['target']['payload']
        self.assertEqual(self.relations.outgoing(predecessor_payload,8)['refs'], [before['relation']])
        self.assertEqual(self.relations.outgoing(successor_payload,8)['refs'], [])
        retained = json.loads(self.app.db.execute('SELECT value FROM app_read_views WHERE id=?',(before['view_key'],)).fetchone()[0])
        self.assertEqual(retained, before['view']); self.evidence.validate_view(retained)
        self.assertEqual(len(self.math.calls), 1)

    def test_supersession_starts_labelled_prior_zero_priority_without_copying_cognition(self):
        before = self.seeded_predecessor()
        old_head = before['view']['snapshot']['lifecycle']
        row, successor, view = self.write('successor', 'Synthetic successor with no empirical history',
            before['view']['handles'][before['uid']]['envelope']['handle'])
        self.assert_isolated(before, successor, view)
        self.assertEqual(self.lifecycle.activeSet(old_head)['active'][0]['uuid'], before['uid'])
        self.assertEqual(self.lifecycle.activeSet(self.lifecycle.head())['active'][0]['uuid'], successor)
        result = json.loads(self.app.db.execute('SELECT result FROM preview_memory_receipts WHERE occurrence=?',(row['id'],)).fetchone()[0])
        self.assertEqual(result['status'], 'MEMORY-SUPERSEDED')
        self.assertEqual(result['prior'], 'labelled-compatibility-not-empirical')

    def test_lost_application_response_replays_without_copying_or_revising_predecessor(self):
        before = self.seeded_predecessor()
        row, successor, view = self.write('successor-replay', 'Synthetic successor replay',
            before['view']['handles'][before['uid']]['envelope']['handle'])
        lifecycle_head = self.lifecycle.head()
        self.memory = SharedMemory(self.app); self.app.preview.memory = self.memory
        # Reopening the application adapter observes the independently committed
        # lifecycle receipt/view; it does not reallocate the successor identity.
        self.assertEqual(self.memory.written(row), view)
        self.assertEqual(self.lifecycle.head(), lifecycle_head)
        self.assert_isolated(before, successor, view)
        refreshed = self.memory.prepare('next-input-after-replay', self.deadline)
        self.assert_isolated(before, successor, refreshed)


if __name__ == '__main__': unittest.main()
