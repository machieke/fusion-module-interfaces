"""P05 scope authorization with real ports/journals and explicit backend fixtures.

DeTTa is replaced at its byte-storage boundary; its receipt shape is an explicit
fixture, not DeTTa integration evidence. No sockets, native process, cluster,
encoder or model runtime runs. Generated TLS/image metadata are fixtures too.
"""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from fusion import cognitive_services as c
from fusion.contracts import ContractError, canonical, digest
from fusion.ports import Mutation
from fusion.policy import Policy
from fusion.registry import descriptor_wire, selection_token
from fusion.responses import encode, decode
from integration.single_node import preview_values
from tests import test_phase2_cognitive_wiring as wiring
from tests.test_phase2_operator_values import image_manifest_fixture


SHARED = 'synthetic-private-scopes-fixture'
PRIVATE = {who: SHARED+'-private-'+who.lower() for who in ('A', 'B')}


class ByteStorageFixture:
    """In-memory byte boundary; explicitly fake DeTTa-shaped receipts."""
    def __init__(self): self.data, self.calls = {}, []

    def put(self, scope, coordinate, data):
        key = digest(canonical([scope, coordinate])); self.data[(scope, key)] = data
        self.calls.append(('put', scope))
        return key, dict(provider='detta-local-rs/1', durability='local-files-process-restart',
            evidence={'classification': 'FIXTURE_DETTA_RECEIPT_NOT_REAL_PROVIDER'})

    def get(self, scope, key):
        self.calls.append(('get', scope))
        return self.data[(scope, key)]

    def availability(self, scope, key):
        data = self.get(scope, key)
        return dict(available=True, present_shares=1, threshold=1, bytes=None, content_hash=digest(data))


class PrivateScopePortsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-private-ports-')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.path = self.root/'policy.json'
        methods = ['atom.storage.'+op for op in c.OPERATIONS['atom.storage']]
        self.cfg = dict(composition=c.COMPOSITION, privacy=c.PRIVACY, scope=SHARED,
            allowed_scopes=[SHARED, PRIVATE['A'], PRIVATE['B']], root=str(self.root/'owner'),
            storage_layout='preview-shared-feed/1', detta_binary='FORBIDDEN_FIXTURE_BOUNDARY',
            catalogue=[descriptor_wire(d) for d in c.descriptors()],
            actors={'A':'A', 'B':'B', 'delegate-A':'A'}, principals={
                who: dict(credential=who+'-synthetic-fixture-token',
                    scopes={SHARED:list(methods), PRIVATE[who]:list(methods)}) for who in ('A','B')})
        self.cfg['principals']['delegate-A'] = dict(credential='delegated-A-fixture-token',
            scopes={SHARED:['atom.storage.create', 'atom.storage.get', 'atom.storage.getMany']})
        self.save(); self.storage = ByteStorageFixture()
        replacement = patch('fusion.adapters.detta.DettaStorage', return_value=self.storage)
        replacement.start(); self.addCleanup(replacement.stop)
        self.port = c.Ports(self.path, 'fusion-storage')
        self.selected = selection_token(c.catalogue(self.cfg)['atom.storage'])

    def save(self): self.path.write_bytes(canonical(self.cfg))

    def request(self, scope, operation, args):
        return dict(id=str(uuid.uuid4()), composition=c.COMPOSITION, scope=scope,
            interface='atom.storage', selection=self.selected, operation=operation, args=args)

    def invoke(self, who, scope, operation, args):
        q = self.request(scope, operation, args)
        reply = self.port.invoke(c.ROUTE, self.cfg['principals'][who]['credential'], q)
        self.assertEqual((reply['principal'], reply['request_digest'], reply['selection']),
            (self.cfg['actors'][who], digest(canonical(q)), self.selected))
        return reply['value']

    def create(self, who, scope, key='same-occurrence'):
        return self.invoke(who, scope, 'create', [asdict(Mutation(scope, key)),
            'text/plain', {'bytes':encode(('synthetic-'+scope).encode())}])

    def denied(self, code, callback, *args):
        before = list(self.storage.calls)
        with self.assertRaises(ContractError) as got: callback(*args)
        self.assertEqual(got.exception.code, code)
        self.assertEqual(self.storage.calls, before)

    def test_private_owners_can_create_hydrate_observe_and_replay_distinct_scope_records(self):
        refs = []
        for who in ('A','B'):
            scope = PRIVATE[who]; result = self.create(who, scope); ref = result['ref']; refs.append(ref)
            self.assertEqual(self.create(who, scope), result)
            self.assertEqual(decode(self.invoke(who, scope, 'get', [ref])['data']), ('synthetic-'+scope).encode())
            self.assertEqual(self.invoke(who, scope, 'getMany', [[ref]])[0]['ref'], ref)
            self.assertTrue(self.invoke(who, scope, 'availability', [ref])['available'])
            head = self.invoke(who, scope, 'head', [scope]); self.assertEqual(head['sequence'], 1)
            page = self.invoke(who, scope, 'readCommits', [scope, 0, head, 8])
            self.assertEqual([row['ref'] for row in page['records']], [ref])
        self.assertNotEqual(refs[0]['id'], refs[1]['id'])
        self.assertEqual(sum(op == 'put' for op, _ in self.storage.calls), 2)

    def test_private_acceptance_survives_port_reconstruction_without_duplicate_write(self):
        result = self.create('A', PRIVATE['A'])
        self.port = c.Ports(self.path, 'fusion-storage')
        self.assertEqual(self.create('A', PRIVATE['A']), result)
        self.assertEqual(sum(op == 'put' for op, _ in self.storage.calls), 1)

    def test_shared_records_remain_readable_by_both_but_feed_does_not_include_private_atoms(self):
        private = self.create('A', PRIVATE['A'])['ref']; shared = self.create('A', SHARED)['ref']
        self.assertEqual(self.invoke('B', SHARED, 'get', [shared])['ref'], shared)
        head = self.invoke('B', SHARED, 'head', [SHARED])
        page = self.invoke('B', SHARED, 'readCommits', [SHARED, 0, head, 8])
        self.assertEqual(head['sequence'], 1)
        self.assertEqual([entry['ref'] for entry in page['records']], [shared])
        self.assertNotIn(private, [entry['ref'] for entry in page['records']])

    def test_cross_principal_all_atom_methods_are_denied_before_backend_effect(self):
        for owner, other in (('A','B'), ('B','A')):
            scope = PRIVATE[owner]; ref = self.create(owner, scope)['ref']
            head = self.invoke(owner, scope, 'head', [scope])
            calls = [('create', [asdict(Mutation(scope,'foreign-write')), 'text/plain', {'bytes':encode(b'synthetic')}]),
                ('get',[ref]), ('getMany',[[ref]]), ('availability',[ref]),
                ('head',[scope]), ('readCommits',[scope,0,head,8]), ('authorize',['get'])]
            for operation, args in calls:
                with self.subTest(owner=owner, operation=operation):
                    self.denied('UNAUTHORIZED', self.invoke, other, scope, operation, args)

    def test_outer_and_nested_scopes_cannot_be_mixed_even_if_actor_authorized_for_both(self):
        private = self.create('A', PRIVATE['A'])['ref']; shared = self.create('A', SHARED)['ref']
        private_head = self.invoke('A', PRIVATE['A'], 'head', [PRIVATE['A']])
        for operation, args in (
            ('create', [asdict(Mutation(PRIVATE['A'],'nested-write')), 'text/plain', {'bytes':encode(b'synthetic')}]),
            ('get',[private]), ('getMany',[[shared,private]]), ('availability',[private]),
            ('head',[PRIVATE['A']]), ('readCommits',[PRIVATE['A'],0,private_head,8]),
            ('readCommits',[SHARED,0,private_head,8])):
            with self.subTest(operation=operation, args=args):
                self.denied('UNAUTHORIZED', self.invoke, 'A', SHARED, operation, args)

    def test_delegated_shared_actor_does_not_inherit_principal_private_authority(self):
        ref = self.create('A', PRIVATE['A'])['ref']
        self.denied('UNAUTHORIZED', self.invoke, 'delegate-A', PRIVATE['A'], 'get', [ref])
        shared = self.create('A', SHARED)['ref']
        self.assertEqual(self.invoke('delegate-A', SHARED, 'get', [shared])['ref'], shared)
        self.cfg['principals']['A']['scopes'][SHARED].remove('atom.storage.get'); self.save()
        self.denied('UNAUTHORIZED', self.invoke, 'delegate-A', SHARED, 'get', [shared])

    def test_current_revocation_blocks_captured_ref_and_saved_mutation_replay(self):
        ref = self.create('A', PRIVATE['A'])['ref']
        access = c.Access(self.path, self.cfg['principals']['A']['credential'], 'atom.storage')
        self.cfg['principals']['A']['scopes'].pop(PRIVATE['A']); self.save()
        self.denied('UNAUTHORIZED', access.authorize, PRIVATE['A'], 'get')
        self.denied('UNAUTHORIZED', self.invoke, 'A', PRIVATE['A'], 'get', [ref])
        self.denied('UNAUTHORIZED', self.create, 'A', PRIVATE['A'])

    def test_unknown_scope_wrong_credential_and_claimed_principal_do_not_grant_membership(self):
        self.denied('UNSUPPORTED_PROFILE', self.invoke, 'A', 'synthetic-unregistered', 'head', ['synthetic-unregistered'])
        q = self.request(SHARED, 'head', [SHARED])
        self.denied('UNAUTHORIZED', self.port.invoke, c.ROUTE, 'unknown-token', q)
        q['principal'] = 'A'
        self.denied('UNSUPPORTED_OPERATION', self.port.invoke, c.ROUTE, self.cfg['principals']['B']['credential'], q)
        self.cfg['principals']['B']['scopes'].pop(SHARED); self.save()
        self.denied('UNAUTHORIZED', self.invoke, 'B', SHARED, 'head', [SHARED])

    def test_old_single_scope_configuration_does_not_implicitly_activate_private_grants(self):
        del self.cfg['allowed_scopes']; self.save()
        self.assertEqual(self.invoke('A', SHARED, 'head', [SHARED])['sequence'], 0)
        self.denied('UNSUPPORTED_PROFILE', self.invoke, 'A', PRIVATE['A'], 'head', [PRIVATE['A']])

    def test_malformed_scope_allowlists_fail_closed_before_owner(self):
        candidates = (None, {}, SHARED, [], [SHARED,SHARED], [PRIVATE['A']], [SHARED,None],
            [SHARED,PRIVATE['A'],PRIVATE['B'],'synthetic-fourth'], [SHARED,'private-actual'],
            [SHARED,'synthetic-'], [SHARED,'synthetic-bad\nvalue'], [SHARED,'synthetic-path/escape'])
        for scopes in candidates:
            with self.subTest(scopes=scopes):
                self.cfg['allowed_scopes'] = scopes; self.save()
                with patch.object(self.port, 'owner', side_effect=AssertionError('invalid scope opened owner')):
                    self.denied('UNSUPPORTED_PROFILE', self.invoke, 'A', SHARED, 'head', [SHARED])

    def test_allowlist_does_not_enable_other_cognitive_interfaces(self):
        self.denied('UNSUPPORTED_PROFILE', c.scoped_configuration, self.cfg, 'episodic.memory', SHARED)
        self.denied('UNSUPPORTED_PROFILE', c.scoped_configuration, self.cfg, 'attention', PRIVATE['A'])


class PrivateScopeConfigurationTests(unittest.TestCase):
    def setUp(self):
        # Reuse only the existing role-separated setup helper, not its test run.
        self.fixture = wiring.CognitiveWiringTests(methodName='runTest')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        for agent in self.fixture.agents.values():
            agent['private_scope'] = self.fixture.scope+'-private-'+agent['principal'].lower()

    def test_values_generate_one_shared_and_two_distinct_private_scopes(self):
        for mode in ('minimal','memory','combined'):
            value = preview_values.generate(image_manifest_fixture(), SHARED, mode=mode, inputs=2, sessions=1)
            p = value['preview']; scopes = [p['scope']]
            for agent in p['agents'].values():
                self.assertEqual(agent['private_scope'], SHARED+'-private-'+agent['principal'].lower())
                scopes.append(agent['private_scope'])
            self.assertEqual(len(set(scopes)), 3)
            self.assertEqual(p['model_boundary'], 'RECORDED_FIXTURE')

    def test_generated_owner_grants_only_shared_and_own_private_with_delegates_shared_only(self):
        f = self.fixture; cfg = f.owner('fusion-storage'); shared = f.scope
        self.assertEqual(set(cfg['allowed_scopes']), {shared, *[a['private_scope'] for a in f.agents.values()]})
        for role, agent in f.agents.items():
            who = agent['principal']; expected = {shared,agent['private_scope']}
            self.assertEqual(set(cfg['principals'][who]['scopes']), expected)
            for actor, represented in cfg['actors'].items():
                if actor != represented: self.assertEqual(set(cfg['principals'][actor]['scopes']), {shared})
            run = f.role(role)[3]; client = json.loads((run/'private-atoms.json').read_text())
            self.assertEqual((client['scope'],client['principal']), (agent['private_scope'],who))
            self.assertEqual(Policy(f.owner_path('fusion-storage')).authenticate(client['credential']), who)
            self.assertEqual(client['endpoint']['host'], 'fusion-storage.synthetic-preview.svc.cluster.local')
            self.assertNotIn('root', client); self.assertNotIn('database', client)
            access = c.Access(f.owner_path('fusion-storage'),client['credential'],'atom.storage')
            self.assertEqual(access.authorize(agent['private_scope'],'create'),who)

    def test_native_shared_history_and_cognition_remain_explicitly_shared(self):
        f = self.fixture
        for role, agent in f.agents.items():
            run = f.role(role)[3]; session = run/'sessions'/agent['sessions'][0]
            for name in ('history-atoms.json','memory-atoms.json','evidence-client.json','episodic.memory.json'):
                value = json.loads((session/name).read_text())
                self.assertEqual(value['scope'], f.scope, name)
            app = json.loads((session/'application.json').read_text())
            self.assertEqual(app['preview']['scope'], f.scope)
        self.assertEqual(f.owner('fusion-episodes')['scope'], f.scope)
        self.assertNotIn('allowed_scopes', f.owner('fusion-episodes'))

    def test_c1_owner_denies_other_principal_but_shared_atom_bytes_are_not_private(self):
        from fusion.adapters.fixture_feed import FileFeedFixture
        from fusion.preview_history import SessionHistoryOwner
        from fusion.preview_ports import Access
        f = self.fixture; storage_path = f.owner_path('fusion-storage')
        facet_path = f.role('fusion-episodes')[3]/'facet-owner.json'
        atom_path = f.root/'explicit-history-atom-fixture.json'
        journal = f.root/'explicit-history-owner.sqlite'
        owners, atoms = {}, {}
        for role, agent in f.agents.items():
            who = agent['principal']
            access = Access(facet_path, f.material[role]['facet-fusion-episodes-token'].decode(), 'episodic.memory')
            atom_access = c.Access(storage_path, f.material[role]['atom-'+who+'-token'].decode(), 'atom.storage')
            atoms[who] = FileFeedFixture(atom_path, atom_access)
            owners[who] = SessionHistoryOwner(journal, atoms[who], access)
        episode = owners['A'].recordEpisode(Mutation(f.scope,'owned-A-history'),'synthetic-history')['ref']
        raw = b'Explicitly shared synthetic administrative history body'
        payload = atoms['A'].create(Mutation(f.scope,'shared-history-data'),'text/plain',raw)['ref']
        receipt = owners['A'].appendHistory(Mutation(f.scope,'shared-history-event'),episode,0,
            'synthetic-history-occurrence','input-receipt',payload,[],'2026-11-02T00:00:00Z')
        snapshot = owners['A'].historySnapshot(episode)
        for method, args in ((owners['B'].historySnapshot,[episode]),
                (owners['B'].readHistory,[snapshot,1,1]),
                (owners['B'].readEvidence,[receipt['evidence']])):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'): method(*args)
        # C1 ownership is not a payload confidentiality claim for shared scopes.
        self.assertEqual(atoms['B'].get(payload).bytes, raw)
        head = atoms['B'].head(f.scope)
        page = atoms['B'].readCommits(f.scope,0,head,8)
        self.assertIn(payload,[entry['ref'] for entry in page['records']])

    def test_generated_private_scope_configuration_rejects_missing_duplicate_and_malformed(self):
        original = copy.deepcopy(self.fixture.preview)
        for bad in ('missing', 'same-as-shared', 'same-as-A', 'private-user-memory', None, ['synthetic-list']):
            with self.subTest(bad=bad):
                f = self.fixture; f.preview = copy.deepcopy(original); f.configured.clear()
                target = f.preview['agents']['omega-agent-b']
                if bad == 'missing': del target['private_scope']
                elif bad == 'same-as-shared': target['private_scope'] = f.scope
                elif bad == 'same-as-A': target['private_scope'] = f.preview['agents']['omega-agent']['private_scope']
                else: target['private_scope'] = bad
                with self.assertRaises(ContractError): f.role('fusion-storage')


if __name__ == '__main__': unittest.main()
