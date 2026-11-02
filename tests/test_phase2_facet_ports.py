"""Closed facet wire dispatch over explicit FileFeedFixture storage.

Requests cross an actual JSON encode/decode boundary, not HTTPS. C1/Relations
and workspace journals are real fresh local owners; AtomStorage and transport
authority are declared fixtures. Internal C1 appendEvent/readEpisode and
Relations history grants are explicit, separate from public facet grants.
No native runtime, model, cluster, private data or production network is used.
"""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, canonical, digest, require
from fusion import lookup_contracts as lookup
from fusion.policy import Policy
from fusion.ports import Mutation
from fusion import preview_ports as p
from fusion.registry import descriptor_wire, selection_token


SCOPE = 'synthetic-facet-wire-tests'
TOKEN_A, TOKEN_B = 'synthetic-agent-a-token', 'synthetic-agent-b-token'
TIME = '2026-11-02T13:00:00Z'


class FixtureAtomAuthority:
    def __init__(self, path, credential): self.policy, self.credential = Policy(path), credential

    def authorize(self, scope, operation):
        principal = self.policy.authenticate(self.credential)
        self.policy.check(principal, scope, 'atom.storage.'+operation)
        return principal


class FacetPorts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-facet-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        public = [name+'.'+op for name, operations in p.OPERATIONS.items() for op in operations]
        internal = ['episodic.memory.appendEvent', 'episodic.memory.readEpisode', 'relations.history']
        atom_methods = ['atom.storage.'+op for op in ('create', 'get', 'getMany', 'head', 'readCommits', 'availability')]
        principals = {principal: dict(credential=token, scopes={SCOPE: public+internal+atom_methods})
            for principal, token in [('A', TOKEN_A), ('B', TOKEN_B)]}
        self.configs, self.paths = {}, {}
        for name, role in p.ROLES.items():
            path = self.root/(role+'.json')
            self.paths[name] = path
            self.configs[name] = dict(composition=p.COMPOSITION, scope=SCOPE,
                root=str(self.root/role), schemas=copy.deepcopy(lookup.SCHEMAS),
                descriptors={key: descriptor_wire(p.descriptor(key)) for key in p.OPERATIONS},
                principals=copy.deepcopy(principals))
            self.save(name)
        self.atom_policy = self.root/'atoms-policy.json'
        self.atom_policy.write_bytes(canonical(dict(principals=principals)))
        self.atom_clients = []
        self.atoms = self.atoms_for('A')

    def save(self, name):
        temporary = self.paths[name].with_suffix('.new')
        temporary.write_bytes(canonical(self.configs[name]))
        temporary.replace(self.paths[name])

    def atoms_for(self, principal):
        require(principal in ('A', 'B'), 'UNAUTHORIZED')
        self.atom_clients.append(principal)
        return FileFeedFixture(self.root/'fixture-atoms.json',
            FixtureAtomAuthority(self.atom_policy, TOKEN_A if principal == 'A' else TOKEN_B))

    def owner(self, name, hook=lambda _: None):
        return p.Ports(self.paths[name], p.ROLES[name], hook, atoms_for=self.atoms_for)

    def request(self, name, operation, *args, **changes):
        wire = [asdict(value) if isinstance(value, Mutation) else value for value in args]
        request = dict(id=str(uuid.uuid4()), composition=p.COMPOSITION, scope=SCOPE, interface=name,
            selection=selection_token(p.descriptor(name)), operation=operation, args=wire)
        request.update(changes)
        return json.loads(canonical(request))

    def call(self, name, operation, *args, credential=TOKEN_A, owner=None, **changes):
        request = self.request(name, operation, *args, **changes)
        result = (owner or self.owner(name)).invoke(credential, request)
        self.assertEqual(set(result), {'id', 'request_digest', 'selection', 'principal', 'value'})
        self.assertEqual(result['id'], request['id'])
        self.assertEqual(result['request_digest'], digest(canonical(request)))
        self.assertEqual(result['selection'], request['selection'])
        self.assertEqual(result['principal'], 'B' if credential == TOKEN_B else 'A')
        return result['value']

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def revoke(self, name, *operations):
        values = self.configs[name]['principals']['A']['scopes'][SCOPE]
        for operation in operations:
            if name+'.'+operation in values: values.remove(name+'.'+operation)
        self.save(name)

    def payload(self, key='payload', data=b'synthetic event content'):
        value = self.atoms.create(Mutation(SCOPE, key), 'text/plain', data)
        self.assertEqual(value['receipt']['provider'], 'contract-fixture-files/1')
        return value['ref']

    def episode(self):
        return self.call('episodic.memory', 'recordEpisode', Mutation(SCOPE, 'episode'), 'native-agent-A')['ref']

    def event(self, episode, number, kind='input-receipt', **kwargs):
        return self.call('episodic.memory', 'appendHistory', Mutation(SCOPE, 'history-'+str(number)),
            episode, number-1, 'history-occurrence-'+str(number), kind, self.payload('body-'+str(number)), [], TIME, **kwargs)

    def assertion(self, key='edge', **kwargs):
        return self.call('relations', 'assertRelation', Mutation(SCOPE, key), 'requires/1',
            (('dependent', self.payload('a', b'a')), ('prerequisite', self.payload('b', b'b'))), True, **kwargs)

    def test_authorize_has_no_effect_and_uses_credential_identity(self):
        before = list(self.atom_clients)
        for name, operation in [('episodic.memory', 'recordEpisode'), ('relations', 'assertRelation'), ('execution.workspace', 'write')]:
            with self.subTest(name=name):
                self.assertEqual(self.call(name, 'authorize', operation), {'authorized': True})
                self.assertEqual(self.call(name, 'authorize', operation, credential=TOKEN_B), {'authorized': True})
                self.assertFalse((self.root/p.ROLES[name]).exists())
                self.error('UNAUTHORIZED', self.call, name, 'authorize', operation, credential='wrong-token')
                self.error('UNAUTHORIZED', self.call, name, 'authorize', operation, scope='synthetic-other')
        self.assertEqual(self.atom_clients, before)

    def test_closed_operation_arity_request_fields_and_role_routing(self):
        owner = self.owner('execution.workspace')
        for operation, args, code in [('shell', ['whoami'], 'UNSUPPORTED_OPERATION'),
            ('read', [], 'INVALID_ARGUMENT'), ('read', ['a.txt', 'extra'], 'INVALID_ARGUMENT'),
            ('authorize', ['authorize'], 'UNSUPPORTED_OPERATION')]:
            with self.subTest(operation=operation):
                self.error(code, owner.invoke, TOKEN_A, self.request('execution.workspace', operation, *args))
        self.error('INVALID_ARGUMENT', owner.invoke, TOKEN_A,
            self.request('execution.workspace', 'read', 'a.txt', principal='B'))
        self.error('UNSUPPORTED_OPERATION', owner.invoke, TOKEN_A,
            self.request('relations', 'authorize', 'assertRelation'))
        self.error('INVALID_ARGUMENT', owner.invoke, TOKEN_A,
            self.request('execution.workspace', 'read', 'a.txt', id='not-a-uuid'))

    def test_malformed_operation_and_interface_types_are_contract_errors(self):
        for key, value in [('interface', []), ('interface', {}), ('operation', []), ('operation', {})]:
            request = self.request('execution.workspace', 'read', 'a.txt')
            request[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ContractError):
                self.owner('execution.workspace').invoke(TOKEN_A, request)

    def test_malformed_authorize_selector_and_relation_role_items_are_contract_errors(self):
        for selector in ([], {}):
            with self.subTest(selector=selector), self.assertRaises(ContractError):
                self.call('execution.workspace', 'authorize', selector)
        for roles in ([1], [None], [{'dependent': 'not-an-ordered-role'}]):
            with self.subTest(roles=roles), self.assertRaises(ContractError):
                self.call('relations', 'assertRelation', Mutation(SCOPE, 'malformed-role'), 'requires/1', roles, True)

    def test_selection_composition_and_current_descriptor_binding(self):
        name = 'execution.workspace'
        self.error('UNSUPPORTED_PROFILE', self.call, name, 'authorize', 'write', selection='stale-selection')
        self.error('UNSUPPORTED_PROFILE', self.call, name, 'authorize', 'write', composition='different/1')
        self.configs[name]['descriptors'][name]['version'] = '2.0.0'
        self.save(name)
        self.error('UNSUPPORTED_PROFILE', self.call, name, 'authorize', 'write')
        self.assertFalse((self.root/p.ROLES[name]).exists())

    def test_history_append_replay_retained_page_and_current_principal(self):
        episode = self.episode()
        first = self.event(episode, 1)
        self.assertEqual(self.event(episode, 1), first)
        self.event(episode, 2, 'model-proposal')
        snapshot = self.call('episodic.memory', 'historySnapshot', episode)
        page = self.call('episodic.memory', 'readHistory', snapshot, 1, 1)
        self.event(episode, 3, 'tool-result')
        next_page = self.call('episodic.memory', 'readHistory', snapshot, page['next_sequence'], 1)
        self.assertEqual([page['events'][0]['kind'], next_page['events'][0]['kind']], ['input-receipt', 'model-proposal'])
        self.assertTrue(next_page['complete'])
        self.assertEqual(next_page['snapshot'], snapshot)
        self.assertEqual(first['evidence']['sequence'], 1)
        self.assertEqual(page['events'][0]['event']['lineage_roots'], [])
        self.assertIsNone(first['delivery_id'])
        self.error('UNAUTHORIZED', self.call, 'episodic.memory', 'historySnapshot', episode, credential=TOKEN_B)

    def test_history_wrong_mutation_scope_and_separate_internal_authority(self):
        episode = self.episode()
        self.error('UNAUTHORIZED', self.call, 'episodic.memory', 'appendHistory',
            Mutation('synthetic-other', 'bad'), episode, 0, 'bad', 'input-receipt', self.payload(), [], TIME)
        self.revoke('episodic.memory', 'appendEvent')
        # Public appendHistory grant alone does not grant the internal C1 append.
        self.assertEqual(self.call('episodic.memory', 'authorize', 'appendHistory'), {'authorized': True})
        self.error('UNAUTHORIZED', self.event, episode, 1)
        self.assertEqual(self.call('episodic.memory', 'historySnapshot', episode)['through'], 0)
        self.revoke('episodic.memory', 'readEpisode')
        self.error('UNAUTHORIZED', self.call, 'episodic.memory', 'historySnapshot', episode)

    def test_history_revocation_blocks_saved_page_and_duplicate_mutation(self):
        episode = self.episode()
        self.event(episode, 1)
        snapshot = self.call('episodic.memory', 'historySnapshot', episode)
        self.revoke('episodic.memory', 'readHistory', 'appendHistory')
        self.error('UNAUTHORIZED', self.call, 'episodic.memory', 'readHistory', snapshot, 1, 1)
        self.error('UNAUTHORIZED', self.event, episode, 1)

    def test_relation_json_roles_assert_retract_read_and_replay(self):
        first = self.assertion()
        self.assertEqual(self.assertion(), first)
        a, b = self.payload('a', b'a'), self.payload('b', b'b')
        self.assertEqual(self.call('relations', 'outgoing', a, 2, None, None)['refs'], [first['ref']])
        self.assertEqual(self.call('relations', 'incoming', b, 2, None, None)['refs'], [first['ref']])
        snapshot = self.call('relations', 'outgoing', a, 2, None, None)['at']
        removed = self.call('relations', 'retract', Mutation(SCOPE, 'unlink'), first['ref'], first['asserted_at'])
        self.assertEqual(self.call('relations', 'retract', Mutation(SCOPE, 'unlink'), first['ref'], first['asserted_at']), removed)
        self.assertFalse(removed['payload_erased'])
        self.assertFalse(removed['evidence_changed'])
        self.error('NOT_FOUND', self.call, 'relations', 'getRelation', first['ref'], False)
        self.assertEqual(self.call('relations', 'getRelation', first['ref'], True)['state'], 'retracted')
        self.assertEqual(self.call('relations', 'outgoing', a, 2, None, None)['refs'], [])
        self.assertEqual(self.call('relations', 'outgoing', a, 2, None, snapshot)['refs'], [first['ref']])
        second = self.assertion('relink')
        self.assertNotEqual(first['ref'], second['ref'])

    def test_relation_schema_roles_scope_and_revocation(self):
        a, b = self.payload('a', b'a'), self.payload('b', b'b')
        self.error('INVALID_ARGUMENT', self.call, 'relations', 'assertRelation', Mutation(SCOPE, 'bad-order'),
            'requires/1', (('prerequisite', a), ('dependent', b)), True)
        self.error('UNAUTHORIZED', self.call, 'relations', 'assertRelation', Mutation(SCOPE, 'foreign'),
            'requires/1', (('dependent', a), ('prerequisite', dict(b, scope_ref='synthetic-other'))), True)
        first = self.assertion()
        self.revoke('relations', 'assertRelation', 'getRelation')
        self.error('UNAUTHORIZED', self.assertion)
        self.error('UNAUTHORIZED', self.call, 'relations', 'getRelation', first['ref'], False)

    def test_workspace_version_write_append_read_and_idempotent_receipts(self):
        name = 'execution.workspace'
        self.assertEqual(self.call(name, 'version', 'note.txt')['revision'], 0)
        one = self.call(name, 'write', 'write-one', 'note.txt', 'generated Ω', 0)
        two = self.call(name, 'append', 'append-two', 'note.txt', 'more', 1)
        self.assertEqual(self.call(name, 'append', 'append-two', 'note.txt', 'more', 1), two)
        current = self.call(name, 'read', 'note.txt')
        self.assertEqual(current['text'], 'generated Ωmore\n')
        self.assertEqual(current['revision'], 2)
        self.assertEqual(self.call(name, 'write', 'write-one', 'note.txt', 'generated Ω', 0), one)
        self.assertEqual(self.call(name, 'read', 'note.txt'), current)
        self.error('CONFLICT', self.call, name, 'write', 'write-one', 'note.txt', 'changed', 0)
        self.error('CONFLICT', self.call, name, 'write', 'stale', 'note.txt', 'changed', 1)

    def test_workspace_paths_links_and_wrong_scope_are_refused(self):
        name = 'execution.workspace'
        for path in ('../escape', '/tmp/escape', 'dir/file', '.hidden', 'nul\x00'):
            with self.subTest(path=path): self.error('INVALID_ARGUMENT', self.call, name, 'read', path)
        self.error('UNAUTHORIZED', self.call, name, 'write', 'other', 'note', 'synthetic', 0, scope='synthetic-other')
        self.call(name, 'version', 'note')
        outside = self.root/'outside-synthetic-file'
        outside.write_text('test-only synthetic content')
        workspace = self.root/p.ROLES[name]/'workspace'
        os.symlink(outside, workspace/'symlink')
        os.link(outside, workspace/'hardlink')
        os.mkfifo(workspace/'fifo')
        for path in ('symlink', 'hardlink', 'fifo'):
            with self.subTest(path=path): self.error('UNAUTHORIZED', self.call, name, 'read', path)

    def test_workspace_revocation_blocks_cached_mutation_and_read(self):
        name = 'execution.workspace'
        self.call(name, 'write', 'one', 'note', 'synthetic', 0)
        self.revoke(name, 'write', 'read', 'version')
        self.error('UNAUTHORIZED', self.call, name, 'write', 'one', 'note', 'synthetic', 0)
        self.error('UNAUTHORIZED', self.call, name, 'read', 'note')
        self.error('UNAUTHORIZED', self.call, name, 'version', 'note')

    def test_workspace_response_loss_after_effect_recovers_without_reappend(self):
        name = 'execution.workspace'
        self.call(name, 'write', 'one', 'note', 'base', 0)
        def interrupt(stage):
            if stage == 'after_workspace_effect': raise RuntimeError('simulated lost owner response')
        with self.assertRaises(RuntimeError):
            self.call(name, 'append', 'two', 'note', 'plus', 1, owner=self.owner(name, interrupt))
        self.error('NOT_AVAILABLE', self.call, name, 'read', 'note')
        receipt = self.call(name, 'append', 'two', 'note', 'plus', 1)
        self.assertEqual(receipt['revision'], 2)
        self.assertEqual(self.call(name, 'read', 'note')['text'], 'baseplus\n')
        self.assertEqual(self.call(name, 'append', 'two', 'note', 'plus', 1), receipt)


if __name__ == '__main__': unittest.main()
