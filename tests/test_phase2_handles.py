"""Pure P05 DTO tests; no owner, storage, native-runtime or authority claim."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

from fusion.contracts import ContractError
from fusion import preview_handles as h


class StableHandleContracts(unittest.TestCase):
    def setUp(self):
        self.scope = 'synthetic-shared-preview'
        self.payload = dict(scope_ref=self.scope, id='opaque-payload', revision=1, digest='a' * 64)
        self.enrollment = dict(scope_ref=self.scope, id='opaque-enrollment', revision=1, digest='b' * 64)
        self.episode = dict(scope_ref=self.scope, id='opaque-c1-episode')
        self.evidence = dict(episode=self.episode, occurrence_id='native/input-1', sequence=1,
                             event_ref=dict(scope_ref=self.scope, id='opaque-event', revision=1, digest='c' * 64))
        self.targets = {
            'memory': dict(enrollment=self.enrollment, payload=self.payload),
            'episode': self.episode,
            'event': self.evidence,
            'relation': dict(scope_ref=self.scope, id='opaque-relation', revision=1, digest='d' * 64),
            'task': dict(session='11111111-1111-4111-8111-111111111111', id='task-1'),
            'result': dict(occurrence='native/command-1', payload=self.payload),
        }

    def rejects(self, code, fn, *args, **kwargs):
        with self.assertRaises(ContractError) as error:
            fn(*args, **kwargs)
        self.assertEqual(error.exception.code, code)

    def test_every_kind_roundtrips_exact_typed_target(self):
        seen = set()
        for kind, target in self.targets.items():
            with self.subTest(kind=kind):
                value = h.make(kind, self.scope, 'agent-a', target)
                self.assertEqual(h.envelope(value, kind=kind, scope=self.scope, principal='agent-a'), value)
                self.assertEqual(h.parse(value['handle']).kind, kind)
                self.assertEqual(uuid.UUID(h.parse(value['handle']).identity).version, 5)
                self.assertEqual(value['target'], target)
                seen.add(value['handle'])
        self.assertEqual(len(seen), 6)

    def test_public_profile_namespace_and_identity_test_vector(self):
        self.assertEqual(str(h.NAMESPACE), 'e5c27b65-0f7e-5b71-b411-b43cdeed1c2f')
        self.assertEqual(h.derive('episode', self.scope, self.episode),
                         'oh1:episode:9fbc9f17-ed31-56e6-97c0-868836f57920')

    def test_shared_identity_excludes_recipient_but_envelope_binds_recipient(self):
        first = h.make('memory', self.scope, 'agent-a', self.targets['memory'])
        second = h.make('memory', self.scope, 'agent-b', self.targets['memory'])
        self.assertEqual(first['handle'], second['handle'])
        self.assertNotEqual(first, second)
        self.rejects('UNAUTHORIZED', h.envelope, first, principal='agent-b')
        # This DTO is not authority: callers can construct another recipient
        # binding, and the owner must still authenticate the actual operation.
        self.assertEqual(h.envelope(second, principal='agent-b'), second)

    def test_memory_revision_and_scope_are_identity_inputs(self):
        first = h.derive('memory', self.scope, self.targets['memory'])
        changed = copy.deepcopy(self.targets['memory'])
        changed['payload']['digest'] = 'e' * 64
        self.assertNotEqual(first, h.derive('memory', self.scope, changed))
        changed = copy.deepcopy(self.targets['memory'])
        for item in changed.values():
            item['scope_ref'] = 'synthetic-other'
        self.assertNotEqual(first, h.derive('memory', 'synthetic-other', changed))
        self.rejects('UNAUTHORIZED', h.derive, 'memory', self.scope, changed)

    def test_canonical_key_order_is_irrelevant_and_all_nested_fields_bind(self):
        first = h.make('event', self.scope, 'agent-a', self.evidence)
        reverse = {key: self.evidence[key] for key in reversed(self.evidence)}
        self.assertEqual(h.derive('event', self.scope, reverse), first['handle'])
        for field, replacement in [('occurrence_id', 'native/input-2'), ('sequence', 2)]:
            changed = {**self.evidence, field: replacement}
            self.assertNotEqual(h.derive('event', self.scope, changed), first['handle'])
            self.rejects('CONFLICT', h.envelope, {**first, 'target': changed})

    def test_no_timestamp_uuid_nickname_hash_or_selector_alias(self):
        valid = h.derive('episode', self.scope, self.episode)
        for value in ('2026-11-02 09:00:00', '2026-11-02T09:00:00Z', 'agent-a',
                      str(uuid.uuid4()), 'a' * 64, 'current', valid + '@1:1'):
            with self.subTest(value=value):
                self.rejects('INVALID_ARGUMENT', h.parse, value)

    def test_wrong_type_and_malformed_uuid_refuse(self):
        valid = h.derive('memory', self.scope, self.targets['memory'])
        self.rejects('INVALID_ARGUMENT', h.parse, valid, 'episode')
        self.rejects('INVALID_ARGUMENT', h.parse, valid, [])
        for value in (valid.upper(), valid.replace('oh1:', 'oh2:'), valid.replace(':memory:', ':unknown:'),
                      'oh1:memory:' + str(uuid.uuid4()), 'oh1:memory:00000000-0000-0000-0000-000000000000',
                      'oh1:memory:------------------------------------', ' ' + valid, valid + ' ', None, {}):
            with self.subTest(value=value):
                self.rejects('INVALID_ARGUMENT', h.parse, value)

    def test_episode_and_event_cannot_be_cast_to_atomref(self):
        for value in (self.episode, self.evidence):
            self.rejects('INVALID_ARGUMENT', h.target, 'relation', value, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'episode', self.payload, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'event', self.episode, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'memory', dict(enrollment=self.episode, payload=self.payload), self.scope)

    def test_nested_scope_and_ref_shapes_are_checked(self):
        for kind, target in self.targets.items():
            if kind == 'task':
                continue
            changed = copy.deepcopy(target)
            if kind in ('memory', 'result'):
                changed['payload']['scope_ref'] = 'synthetic-private'
            elif kind == 'event':
                changed['event_ref']['scope_ref'] = 'synthetic-private'
            else:
                changed['scope_ref'] = 'synthetic-private'
            self.rejects('UNAUTHORIZED', h.target, kind, changed, self.scope)
        for revision in (True, 0, 2):
            self.rejects('INVALID_ARGUMENT', h.target, 'relation', {**self.payload, 'revision': revision}, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'relation', {**self.payload, 'digest': 'A' * 64}, self.scope)

    def test_event_sequence_and_occurrence_remain_exact(self):
        for sequence in (0, True, 257):
            self.rejects('INVALID_ARGUMENT', h.target, 'event', {**self.evidence, 'sequence': sequence}, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'event', {**self.evidence, 'occurrence_id': ''}, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'event', {**self.evidence, 'observed_time': '2026-11-02'}, self.scope)

    def test_task_and_result_have_closed_application_targets(self):
        for value in ({'session': 'not-a-uuid', 'id': 'task-1'},
                      {**self.targets['task'], 'role': 'administrator'},
                      {**self.targets['task'], 'session': '{11111111-1111-4111-8111-111111111111}'}):
            self.rejects('INVALID_ARGUMENT', h.target, 'task', value, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'result', {**self.targets['result'], 'deadline': 0}, self.scope)
        self.rejects('INVALID_ARGUMENT', h.target, 'result', {**self.targets['result'], 'occurrence': ''}, self.scope)

    def test_envelope_refuses_extra_permissions_profile_and_wrong_binding(self):
        value = h.make('memory', self.scope, 'agent-a', self.targets['memory'])
        self.rejects('INVALID_ARGUMENT', h.envelope, {**value, 'authorized': True})
        self.rejects('UNSUPPORTED_PROFILE', h.envelope, {**value, 'profile': 'legacy/1'})
        self.rejects('INVALID_ARGUMENT', h.envelope, value, kind='event')
        self.rejects('UNAUTHORIZED', h.envelope, value, scope='synthetic-other')
        self.rejects('INVALID_ARGUMENT', h.make, 'memory', self.scope, 'claimed admin', self.targets['memory'])
        other = h.make('memory', self.scope, 'agent-a', dict(enrollment=self.payload, payload=self.enrollment))
        self.rejects('CONFLICT', h.envelope, {**value, 'handle': other['handle']})

    def test_returned_values_do_not_alias_caller_mutable_inputs(self):
        source = copy.deepcopy(self.targets['memory'])
        value = h.make('memory', self.scope, 'agent-a', source)
        source['payload']['digest'] = 'f' * 64
        self.assertEqual(value['target']['payload']['digest'], 'a' * 64)
        checked = h.envelope(value)
        checked['target']['enrollment']['digest'] = 'e' * 64
        self.assertEqual(value['target']['enrollment']['digest'], 'b' * 64)

    def test_import_has_no_provider_or_owner_runtime_dependency(self):
        code = '''import json,sys
import fusion.preview_handles
for name in ('fusion.episodes','fusion.atom_feed','fusion.preview_history','fusion.preview_lifecycle',
             'fusion.relations','fusion.neoclaw_application','torch','chromadb','transformers'):
    assert name not in sys.modules,name
print(json.dumps({'pure_contract_import':'PASS'}))
'''
        result = subprocess.run([sys.executable, '-c', code], cwd=Path(__file__).resolve().parents[1],
                                check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), {'pure_contract_import': 'PASS'})


if __name__ == '__main__':
    unittest.main()
