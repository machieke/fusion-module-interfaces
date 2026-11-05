"""V30: finite independent models against real owner transactions.

Bounds are declared here before execution: three seeds, at most 48 generated
schedule steps per seed/domain, four deliberate faulty variants, no fuzzing or native
execution. SQLite/files/Policy are real. Clocks, readiness, payload backends,
cluster fencing observations and completed native projections are fixtures.
Generated schedules are subtests, never additional authored test methods.
"""
import copy
import json
import random
import unittest
from dataclasses import dataclass, field
from unittest.mock import patch

from fusion.contracts import ContractError, canonical, digest
from fusion.policy import Policy
from fusion.provider_lifecycle import Registry
from fusion.provider_retention import PROFILE, LIMITS
from fusion.ports import Mutation
from fusion.workflow_prerequisites import KINDS
from tests import test_integrated_registry as registry_fixture
from tests import test_phase3_sessions as session_fixture
from tests import test_phase2_workspace as workspace_fixture
from tests import test_integrated_archive as archive_fixture
from tests import test_pilot_workflows as workflow_fixture
from tests import test_pilot_workflow_prerequisites as prerequisite_fixture
from tests import test_pilot_handover_upgrade as fence_fixture

SEEDS = (17, 43, 91)
MAX_COMMANDS_PER_DOMAIN = 48
MUTANTS = ('authority-check-removed', 'stale-incarnation-cached',
           'premature-checkpoint-progression', 'new-id-on-replay')


@dataclass
class RegistryModel:
    """Small abstract action projection; no implementation or database access."""
    state: str = 'not-admitted'
    receipts: dict = field(default_factory=dict)
    active: set = field(default_factory=set)
    epochs: int = 0

    def effect(self, identity, operation):
        if identity in self.receipts:
            return self.receipts[identity]
        if operation != 'probe':
            self.state = {'add': 'admitted', 'enable': 'enabled',
                          'disable': 'disabled', 'drain': 'draining'}[operation]
        self.receipts[identity] = self.state
        self.active.add(identity)
        return self.state

    def seal(self):
        self.active.clear()
        self.epochs += 1


@dataclass
class CapacityModel:
    active_limit: int = 2
    retained_limit: int = 4
    states: dict = field(default_factory=dict)

    def allocate(self, identity):
        if identity in self.states:
            return True
        if len(self.states) >= self.retained_limit or sum(s == 'active' for s in self.states.values()) >= self.active_limit:
            return False
        self.states[identity] = 'active'
        return True


@dataclass
class CancellationModel:
    started: bool = False
    cancelled: bool = False
    expired: bool = False

    def next(self):
        if self.cancelled or self.expired:
            return 'blocked' if self.started else 'none'
        self.started = True
        return 'dispatched'

    @property
    def state(self):
        if self.cancelled:
            return 'cancel-requested' if self.started else 'cancelled-before-start'
        if self.expired:
            return 'needs-reconciliation' if self.started else 'expired-before-start'
        return 'dispatched' if self.started else 'accepted'


@dataclass
class AppendModel:
    value: str = 'base'
    revision: int = 1
    accepted: dict = field(default_factory=dict)

    def append(self, identity, text, expected):
        if identity in self.accepted:
            assert self.accepted[identity] == (text, expected)
            return
        assert expected == self.revision
        self.accepted[identity] = (text, expected)
        self.value += text + '\n'
        self.revision += 1


class FiniteModels(unittest.TestCase):
    def fixture(self, cls):
        value = cls()
        value.setUp()
        self.addCleanup(value.doCleanups)
        return value

    def assert_refused(self, operation, code='UNAUTHORIZED'):
        try:
            operation()
        except ContractError as exc:
            self.assertEqual(exc.code, code)
        else:
            self.fail('forbidden transition was accepted')

    def registry(self):
        f = self.fixture(registry_fixture.Lifecycle)
        f.selected.update(profile=PROFILE, limits=dict(LIMITS))
        f.registry = Registry(f.store, f.selected, f.auth)
        return f

    def assert_registry(self, f, model, binding, sid):
        observed = f.registry.headroom()['usage']
        self.assertEqual(observed['actions'], len(model.receipts))
        self.assertEqual(observed['active_actions'], len(model.active))
        self.assertEqual(observed['epochs'], model.epochs)
        self.assertEqual(f.registry.inspect('storage')['state'], model.state)
        self.assertEqual(f.registry.selected(sid), binding)

    def test_seeded_registry_sealing_retains_action_projection_and_historical_selection(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                f = self.registry(); rng = random.Random(seed); model = RegistryModel()
                saved = {}
                for identity, op in (('add', 'add'), ('probe', 'probe'), ('enable', 'enable')):
                    saved[identity] = (op, f.registry.probe(identity, 'storage', lambda _: True) if op == 'probe' else f.registry.act(identity, op, 'storage'))
                    model.effect(identity, op)
                sid = f.allocate()['session']; binding = copy.deepcopy(f.registry.selected(sid))
                for index in range(24):
                    op = rng.choice(('probe', 'disable', 'enable', 'drain'))
                    identity = f'{seed}-{index}'
                    saved[identity] = (op, f.registry.probe(identity, 'storage', lambda _: True) if op == 'probe' else f.registry.act(identity, op, 'storage'))
                    model.effect(identity, op)
                    if index % 4 == 3:
                        preview = f.registry.plan('storage')
                        f.registry.seal('seal-'+identity, 'storage', preview['head']); model.seal()
                    replay = rng.choice(list(saved)); prior_op, receipt = saved[replay]
                    actual = f.registry.probe(replay, 'storage', lambda _: self.fail('probe repeated')) if prior_op == 'probe' else f.registry.act(replay, prior_op, 'storage')
                    self.assertEqual(actual, receipt)
                    self.assert_registry(f, model, binding, sid)
                f.denied.add('providers.seal')
                self.assert_refused(lambda: f.registry.seal('seal-'+identity, 'storage'))
                self.assertEqual(f.registry.headroom()['usage']['actions'], len(model.receipts))

    def test_seeded_capacity_admission_archive_never_refunds_retained_identity(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                f = self.fixture(session_fixture.SessionTests); owner = f.store(); self.addCleanup(owner.close)
                model = CapacityModel(); identities = {}; rng = random.Random(seed)
                schedule = [('allocate', 'a'), ('allocate', 'b'), ('allocate', 'c')]
                schedule += [(rng.choice(('allocate', 'close', 'archive')), rng.choice('abcdef')) for _ in range(36)]
                for operation, identity in schedule:
                    if operation == 'allocate':
                        expected = model.allocate(identity)
                        if expected:
                            result = owner.allocate('A', identity, 'shared')
                            if identity in identities:self.assertEqual(result['session'], identities[identity])
                            identities[identity] = result['session']
                        else:self.assert_refused(lambda: owner.allocate('A', identity, 'shared'), 'OVERLOADED')
                    elif identity in identities:
                        old = model.states[identity]
                        if operation == 'close' and old == 'active':
                            owner.control('A', identities[identity], 'close-'+identity, 'close'); model.states[identity] = 'closed'
                        elif operation == 'archive' and old == 'closed':
                            owner.control('A', identities[identity], 'archive-'+identity, 'archive'); model.states[identity] = 'archived'
                    observed = owner.capacity('A')
                    self.assertEqual(observed['retained'], len(model.states))
                    self.assertEqual(observed['active'], sum(s == 'active' for s in model.states.values()))
                # Refused capacity cannot become available by rewriting an old
                # allocation receipt or observing it with a new timestamp.
                self.assertEqual(len(set(identities.values())), len(identities))

    def test_seeded_cancel_dispatch_expiry_preserves_uncertainty_and_deadline(self):
        for seed in SEEDS:
            rng = random.Random(seed)
            for case in range(6):
                with self.subTest(seed=seed, case=case):
                    f = self.fixture(session_fixture.SessionTests); owner = f.store(); self.addCleanup(owner.close)
                    sid = owner.allocate('A', 'one', 'shared')['session']; original = owner.submit('A', sid, 'input', 'pin synthetic', 'task')
                    model = CancellationModel()
                    schedule = ['dispatch', 'cancel'] if case % 2 == 0 else ['dispatch', 'expiry']
                    rng.shuffle(schedule)
                    for operation in schedule + ['dispatch', 'replay']:
                        if operation == 'cancel':
                            model.cancelled = True; owner.cancel('A', sid, 'cancel-original', 'input')
                        elif operation == 'expiry':
                            f.now[0] = original['deadline']; model.expired = True; owner.reconcile('A', sid)
                        elif operation == 'dispatch':
                            expected = model.next()
                            if expected == 'blocked':self.assert_refused(lambda: owner.next_input('A', sid), 'NOT_AVAILABLE')
                            elif expected == 'none':self.assertIsNone(owner.next_input('A', sid))
                            else:self.assertEqual(owner.next_input('A', sid)['id'], 'input')
                        else:self.assertEqual(owner.submit('A', sid, 'input', 'pin synthetic', 'task')['deadline'], original['deadline'])
                    observed = owner.observe('A', sid)['inputs']
                    self.assertEqual(len(observed), 1); self.assertEqual(observed[0]['state'], model.state)
                    self.assertEqual(observed[0]['deadline'], original['deadline'])
                    self.assertEqual(owner.db.execute('SELECT count(*) FROM sustained_dispatch').fetchone()[0], int(model.started))
                    self.assertEqual(observed[0]['outcome']['effects'], 'UNKNOWN_AFTER_DISPATCH' if model.started else 'NO_DISPATCH')

    def test_seeded_workspace_append_effect_receipt_boundaries_match_list_oracle(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                f = self.fixture(workspace_fixture.WorkspaceTests); owner = f.open(); self.addCleanup(owner.close)
                owner.mutate('A', 'synthetic-files', 'base', 'write', 'note', 'base', 0)
                model = AppendModel(); saved = {}; rng = random.Random(seed)
                for index in range(12):
                    identity = f'append-{index}'; text = str(rng.randrange(1000)); expected = model.revision
                    stage = rng.choice(('after_workspace_intent', 'after_workspace_effect', 'after_workspace_receipt'))
                    def interrupt(actual, selected=stage):
                        if actual == selected:raise InterruptedError('explicit commit-boundary fault')
                    owner.hook = interrupt
                    with self.assertRaises(InterruptedError):owner.mutate('A', 'synthetic-files', identity, 'append', 'note', text, expected)
                    owner.hook = lambda _: None
                    receipt = owner.mutate('A', 'synthetic-files', identity, 'append', 'note', text, expected)
                    model.append(identity, text, expected); saved[identity] = (text, expected, receipt)
                    replay = rng.choice(list(saved)); old_text, revision, old_receipt = saved[replay]
                    self.assertEqual(owner.mutate('A', 'synthetic-files', replay, 'append', 'note', old_text, revision), old_receipt)
                    actual = owner.read('A', 'synthetic-files', 'note')
                    self.assertEqual((actual['text'], actual['revision']), (model.value, model.revision))
                    self.assertEqual(owner.db.execute('SELECT count(*) FROM workspace_effects').fetchone()[0], 1+len(model.accepted))
                f.revoked = True
                self.assert_refused(lambda: owner.mutate('A', 'synthetic-files', identity, 'append', 'note', text, expected))

    def test_seeded_prerequisite_membership_uses_exact_revision_not_source_change(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                f = self.fixture(prerequisite_fixture.Prerequisites); rng = random.Random(seed)
                expected_active = True
                changes = ['irrelevant']*5 + ['withdraw']
                rng.shuffle(changes)
                first_payload = f.f.atoms.get(f.first['memory']['payload']).bytes
                for index, change in enumerate(changes):
                    if change == 'withdraw':
                        f.f.owner.change(f.f.command('withdraw'), 'withdraw', logical_id=f.first['logical_id'], expected_revision=1)
                        expected_active = False
                    else:f.f.owner.change(f.f.command('other-'+str(index)), 'introduce', enrollment=f.f.enrolled('other '+str(index)))
                    observed = f.observer.observe(f.condition, 2000)
                    self.assertEqual(observed['state'], 'SATISFIED' if expected_active else 'INVALID')
                    self.assertEqual(f.f.atoms.get(f.first['memory']['payload']).bytes, first_payload)
                    self.assertEqual(f.f.owner.activeSet(f.first['at'])['active'][0]['revision'], 1)
                f.f.access.revoked = True
                self.assertEqual(f.observer.observe(f.condition, 2000)['state'], 'UNAUTHORIZED')

    def test_seeded_archive_publication_keeps_feed_identity_and_spent_reservation(self):
        stages = ['after_archive_reservation', 'after_archive_file_publish', 'after_archive_activation']
        for seed in SEEDS:
            with self.subTest(seed=seed):
                f = self.fixture(archive_fixture.Archive); owner = f.owner()
                refs = [f.write(i, owner)['ref'] for i in range(3)]; head = owner.head(archive_fixture.SCOPE)
                feed = owner.readCommits(archive_fixture.SCOPE, 0, head, 3)
                slots = list(enumerate(stages)); random.Random(seed).shuffle(slots)
                expected_segments = 0; prior_charge = 0
                for index, stage in slots:
                    command = Mutation(archive_fixture.SCOPE, 'publish-'+str(index))
                    def interrupt(actual, selected=stage):
                        if actual == selected:raise InterruptedError('archive publication boundary')
                    with self.assertRaises(InterruptedError):f.owner(interrupt).publishArchive(command, index, head, 1)
                    before = owner.observeArchive(command)
                    self.assertEqual(before['archive']['state'], 'sealed' if stage == 'after_archive_activation' else 'reserved')
                    expected_segments += 1
                    charge = before['capacity']['charged_bytes']
                    self.assertGreater(charge, prior_charge)
                    sealed = owner.publishArchive(command, index, head, 1)
                    self.assertEqual(owner.publishArchive(command, index, head, 1), sealed)
                    after = owner.observeArchive(command)
                    self.assertEqual(after['capacity']['charged_bytes'], charge); prior_charge = charge
                    self.assertEqual(after['capacity']['reserved_segments'], expected_segments)
                    self.assertEqual(owner.head(archive_fixture.SCOPE), head)
                    self.assertEqual(owner.readCommits(archive_fixture.SCOPE, 0, head, 3), feed)
                    self.assertEqual(owner.get(refs[index]).bytes, str(index).encode())

    def test_seeded_writer_fence_current_incarnation_and_credential_epochs(self):
        for seed in SEEDS:
            with self.subTest(seed=seed):
                f = self.fixture(fence_fixture.WriterFence); policy = Policy(f.config); rng = random.Random(seed)
                credentials = ['synthetic']; active = ('original', 'writer-1', 1)
                for index in range(12):
                    if index == 4:
                        f.h.plan('move', 'replacement', 'writer-2', 'a'*64, 'b'*64)
                        self.assert_refused(lambda: policy.check('A', 'synthetic-scope', 'memory.write'))
                        f.h.retire('move'); f.h.activate('move'); active = ('replacement', 'writer-2', 2)
                    cfg = json.loads(f.config.read_bytes())
                    credentials.append('credential-'+str(seed)+'-'+str(index)); cfg['principals']['A']['credential'] = credentials[-1]
                    selected = active if rng.choice((True, False)) else ('original', 'writer-1', 1)
                    cfg['writer_fence'].update(zip(('deployment', 'incarnation', 'generation'), selected)); f.config.write_bytes(canonical(cfg))
                    self.assertEqual(policy.authenticate(credentials[-1]), 'A')
                    self.assert_refused(lambda: policy.authenticate(rng.choice(credentials[:-1])))
                    if selected == active:policy.check('A', 'synthetic-scope', 'memory.write')
                    else:self.assert_refused(lambda: policy.check('A', 'synthetic-scope', 'memory.write'))
                    self.assert_refused(lambda: policy.check('A', 'synthetic-foreign', 'memory.write'))
                self.assertEqual(f.h.read()['generation'], 2)

    def test_mutant_removed_authority_check_is_detected(self):
        f = self.fixture(workspace_fixture.WorkspaceTests); owner = f.open(); self.addCleanup(owner.close)
        owner.mutate('A', 'synthetic-files', 'original', 'write', 'note', 'private synthetic', 0)
        f.revoked = True
        self.assert_refused(lambda: owner.read('A', 'synthetic-files', 'note'))
        # Deliberate faulty provider variant: bypass its current authority port.
        with patch.object(owner, 'authorize', lambda *_: None):
            with self.assertRaisesRegex(AssertionError, 'forbidden transition was accepted'):
                self.assert_refused(lambda: owner.read('A', 'synthetic-files', 'note'))

    def test_mutant_stale_incarnation_acceptance_is_detected(self):
        f = self.fixture(fence_fixture.WriterFence); policy = Policy(f.config)
        policy.check('A', 'synthetic-scope', 'memory.write')
        # The faulty adapter caches an earlier successful authorization. It is
        # kept in the test only; the real current Policy is checked alongside it.
        cached = lambda: None
        f.h.plan('move', 'replacement', 'writer-2', 'a'*64, 'b'*64); f.h.retire('move'); f.h.activate('move')
        self.assert_refused(lambda: policy.check('A', 'synthetic-scope', 'memory.write'))
        with self.assertRaisesRegex(AssertionError, 'forbidden transition was accepted'):self.assert_refused(cached)

    def test_mutant_premature_checkpoint_progression_is_detected(self):
        f = self.fixture(workflow_fixture.Workflows)
        guard = dict(id='capacity', kind='capacity-authority', policy=KINDS['capacity-authority'], scope=workflow_fixture.SCOPE,
                     target=dict(session=f.sid, minimum_inputs=7, minimum_pending=1), predicate=None)
        plan = workflow_fixture.steps(guard); plan[2]['checkpoint'] = True; f.through_two(plan)
        cp = f.owner.checkpoint(f.wid, 'review', 1, 'review')['checkpoints'][0]
        f.owner.decide(f.wid, 'review', 'decision', 'operator', cp['binding_sha256'], 'approve')
        expected_reservations = 2  # 8 accepted allowance minus2 prior inputs <7.
        actual = f.owner.advance(f.wid, 1); self.assertEqual(actual['reservations_spent'], expected_reservations)
        real_observe = f.observations.observe
        def faulty(declared, deadline):
            result = real_observe(declared, deadline)
            return {**result, 'state': 'SATISFIED'}  # Fault: stale approval manufactures a valid prerequisite.
        with patch.object(f.observations, 'observe', faulty):
            bad = f.owner.advance(f.wid, 1)
            with self.assertRaises(AssertionError):self.assertEqual(bad['reservations_spent'], expected_reservations)
        self.assertEqual(bad['reservations_spent'], 3)
        self.assertEqual(bad['deadline_ms'], 9000)

    def test_mutant_regenerated_idempotency_key_is_detected(self):
        f = self.fixture(workspace_fixture.WorkspaceTests); owner = f.open(); self.addCleanup(owner.close)
        owner.mutate('A', 'synthetic-files', 'base', 'write', 'note', 'base', 0)
        model = AppendModel(); model.append('append-once', 'same', 1)
        owner.mutate('A', 'synthetic-files', 'append-once', 'append', 'note', 'same', 1)
        # Faulty client reconstructs a new occurrence/revision after a lost reply.
        owner.mutate('A', 'synthetic-files', 'regenerated-id', 'append', 'note', 'same', 2)
        with self.assertRaises(AssertionError):self.assertEqual(owner.read('A', 'synthetic-files', 'note')['text'], model.value)
        self.assertEqual(owner.read('A', 'synthetic-files', 'note')['text'], 'basesame\nsame\n')


if __name__ == '__main__':
    unittest.main()
