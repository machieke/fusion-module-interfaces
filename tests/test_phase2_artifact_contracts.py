"""Pure P13 DTO qualification with explicitly synthetic refs and view fixtures.

No retrieval, native agent, AtomStorage provider, inspection, chain, model or
runtime integration is claimed. Text equality to authoritative payload bytes
and task/result correlation are application responsibilities, not this DTO's.
"""
import copy
import json
import unittest
import uuid

from fusion import preview_artifact_contracts as artifact
from fusion import preview_vector_contracts as active, vector_contracts as vector
from fusion.contracts import ContractError, canonical, digest
from fusion.lookup_contracts import make_head
from fusion.preview_lifecycle import PROFILE as LIFECYCLE


SCOPE = 'synthetic-phase2-artifact-tests'


class RetrievalArtifactContractTests(unittest.TestCase):
    def setUp(self):
        view = dict(generation=str(uuid.uuid4()), head=make_head(str(uuid.uuid4()), SCOPE, 3),
            corpus='generated-artifact-corpus', embedding=vector.FIXTURE, index=vector.INDEX,
            profile=active.PROFILE, lifecycle=make_head(str(uuid.uuid4()), SCOPE, 2, LIFECYCLE),
            active_digest='a'*64)
        self.rehash(view)
        self.value = dict(profile=artifact.PROFILE, scope=SCOPE, task=str(uuid.uuid4()),
            query='synthetic archive marker', sender='A', reporter='B',
            result_ref=self.ref('result'), view=view,
            observations=[dict(payload_ref=self.ref('payload-1'), content='The synthetic marker is amber.')])

    @staticmethod
    def ref(name):
        return dict(scope_ref=SCOPE, id='synthetic/'+name, revision=1,
                    digest=digest(('synthetic fixture '+name).encode()))

    @staticmethod
    def rehash(view):
        view['logical'] = digest(canonical({k: value for k, value in view.items()
                                          if k not in ('generation', 'logical')}))

    def error(self, value, code=None, **kwargs):
        with self.assertRaises(ContractError) as caught:
            artifact.record(value, **kwargs)
        if code is not None:
            self.assertEqual(caught.exception.code, code)

    def test_valid_artifact_exact_canonical_replay_and_detached_copy(self):
        original = copy.deepcopy(self.value)
        result = artifact.record(self.value, SCOPE)
        wire = artifact.encode(self.value, SCOPE)
        self.assertEqual(wire, canonical(original))
        self.assertEqual(artifact.encode(json.loads(wire), SCOPE), wire)
        self.assertEqual(self.value, original)
        result['observations'][0]['content'] = 'changed detached return'
        result['view']['head']['sequence'] = 4
        self.assertEqual(self.value, original)

    def test_opposite_agent_directions_and_empty_retrieval(self):
        self.value.update(sender='B', reporter='A', observations=[])
        self.assertEqual(artifact.record(self.value), self.value)

    def test_existing_real_embedding_identity_and_fixture_identity_remain_distinct(self):
        fixture_wire = artifact.encode(self.value)
        self.value['view']['embedding'] = vector.EMBEDDING
        self.rehash(self.value['view'])
        real_identity_wire = artifact.encode(self.value)
        self.assertNotEqual(real_identity_wire, fixture_wire)
        self.assertEqual(artifact.record(self.value)['view']['embedding'], vector.EMBEDDING)
        # Accepting the model identity is a contract test, not an E5 execution.
        self.value['view']['embedding'] = 'unadmitted-model/1'
        self.rehash(self.value['view'])
        self.error(self.value, 'UNSUPPORTED_PROFILE')

    def test_closed_top_level_and_nested_fields(self):
        locations = ((), ('result_ref',), ('view',), ('view', 'head'), ('view', 'lifecycle'),
                     ('observations', 0), ('observations', 0, 'payload_ref'))
        for location in locations:
            for action in ('extra', 'missing'):
                with self.subTest(location=location, action=action):
                    candidate = copy.deepcopy(self.value)
                    item = candidate
                    for part in location:
                        item = item[part]
                    if action == 'extra':
                        item['undeclared'] = 'not admitted'
                    else:
                        item.pop(next(iter(item)))
                    self.error(candidate)

    def test_profile_and_scope_binding(self):
        for scope in ('private-user-memory', 'synthetic-', '', [], {}, None, 1):
            with self.subTest(scope=scope):
                candidate = copy.deepcopy(self.value); candidate['scope'] = scope
                self.error(candidate, 'UNAUTHORIZED')
        self.error(self.value, 'UNAUTHORIZED', scope='synthetic-another')
        for selected in ('synthetic-agent-retrieval-artifact/2', [], {}, None):
            with self.subTest(profile=selected):
                candidate = copy.deepcopy(self.value); candidate['profile'] = selected
                self.error(candidate, 'UNSUPPORTED_PROFILE')

    def test_task_identity_and_agent_identity_validation(self):
        for task in ('not-a-uuid', 'AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA', None, [], {}, 1, True):
            with self.subTest(task=task):
                candidate = copy.deepcopy(self.value); candidate['task'] = task
                self.error(candidate)
        for sender, reporter in (('A', 'A'), ('B', 'B'), ('A', 'C'), ('C', 'A'),
                                 ([], 'B'), ('A', {}), (None, 'B'), ('A', True)):
            with self.subTest(sender=sender, reporter=reporter):
                candidate = copy.deepcopy(self.value); candidate.update(sender=sender, reporter=reporter)
                self.error(candidate, 'UNAUTHORIZED')

    def test_references_are_immutable_and_scope_bound(self):
        for location in (('result_ref',), ('observations', 0, 'payload_ref')):
            for key, value in (('scope_ref', 'synthetic-foreign'), ('scope_ref', 'private-owner'),
                               ('id', ''), ('digest', 'z'*64), ('digest', 'a'*63),
                               ('revision', 2), ('revision', True), ('revision', 1.0)):
                with self.subTest(location=location, key=key, value=value):
                    candidate = copy.deepcopy(self.value); item = candidate
                    for part in location:
                        item = item[part]
                    item[key] = value
                    self.error(candidate)

    def test_duplicate_payload_identity_and_result_alias_are_rejected(self):
        second = copy.deepcopy(self.value['observations'][0])
        for changed_digest in (False, True):
            with self.subTest(changed_digest=changed_digest):
                candidate = copy.deepcopy(self.value)
                candidate['observations'].append(copy.deepcopy(second))
                if changed_digest:
                    candidate['observations'][1]['payload_ref']['digest'] = 'f'*64
                self.error(candidate, 'CONFLICT')
        self.value['observations'][0]['payload_ref'] = copy.deepcopy(self.value['result_ref'])
        self.error(self.value, 'CONFLICT')

    def test_full_retained_view_scope_and_logical_binding(self):
        for name in ('head', 'lifecycle'):
            candidate = copy.deepcopy(self.value)
            candidate['view'][name]['scope_ref'] = 'synthetic-foreign'
            self.rehash(candidate['view'])
            self.error(candidate, 'UNAUTHORIZED')
        candidate = copy.deepcopy(self.value)
        candidate['view']['head']['sequence'] += 1
        self.error(candidate, 'CONFLICT')
        for key, value in (('generation', 'invalid'), ('logical', 'b'*64),
                           ('index', 'other-index/1'), ('profile', vector.PROFILE)):
            with self.subTest(key=key):
                candidate = copy.deepcopy(self.value); candidate['view'][key] = value
                if key != 'logical':
                    self.rehash(candidate['view'])
                self.error(candidate)

    def test_exact_utf8_query_and_content_bounds_without_rewriting(self):
        self.value['query'] = '\u00e9'*256
        self.value['observations'][0]['content'] = '\u03bb'*512
        self.assertEqual(artifact.record(self.value), self.value)
        for field, too_long in (('query', '\u00e9'*257), ('content', '\u03bb'*513)):
            candidate = copy.deepcopy(self.value)
            if field == 'query': candidate[field] = too_long
            else: candidate['observations'][0][field] = too_long
            self.error(candidate)
        for field in ('query', 'content'):
            for invalid in ('', '\ud800', {}, [], 7, True, None):
                with self.subTest(field=field, invalid=repr(invalid)):
                    candidate = copy.deepcopy(self.value)
                    if field == 'query': candidate[field] = invalid
                    else: candidate['observations'][0][field] = invalid
                    self.error(candidate)

    def test_observation_count_and_container_types(self):
        self.value['observations'] = [dict(payload_ref=self.ref(f'payload-{i}'), content='synthetic')
                                      for i in range(3)]
        self.assertEqual(len(artifact.record(self.value)['observations']), 3)
        self.value['observations'].append(dict(payload_ref=self.ref('payload-4'), content='synthetic'))
        self.error(self.value)
        for invalid in ({}, (), None, 'text', [None], [object()]):
            with self.subTest(value=repr(invalid)):
                candidate = copy.deepcopy(self.value); candidate['observations'] = invalid
                self.error(candidate)

    def test_combined_canonical_byte_limit_exactly_4096(self):
        self.value['observations'] = [dict(payload_ref=self.ref(f'payload-{i}'), content='x')
                                      for i in range(3)]
        remaining = artifact.MAX_BYTES - len(canonical(self.value))
        self.assertGreater(remaining, 0)
        for item in self.value['observations']:
            amount = min(remaining, artifact.MAX_CONTENT_BYTES-1)
            item['content'] += 'x'*amount
            remaining -= amount
        self.assertEqual(remaining, 0)
        self.assertEqual(len(artifact.encode(self.value)), artifact.MAX_BYTES)
        self.value['query'] += 'x'
        self.assertEqual(len(canonical(self.value)), artifact.MAX_BYTES+1)
        self.error(self.value, 'OVERLOADED')

    def test_non_plain_objects_subclasses_cycles_and_boolean_heads_are_rejected(self):
        class UnsafeText(str): pass
        class UnsafeDict(dict): pass
        for value in (object(), UnsafeDict(self.value)):
            self.error(value)
        modifications = (('query', UnsafeText('text')), ('task', object()),
                         ('view', object()), ('result_ref', object()))
        for field, value in modifications:
            with self.subTest(field=field):
                candidate = copy.deepcopy(self.value); candidate[field] = value
                self.error(candidate)
        candidate = copy.deepcopy(self.value)
        candidate['observations'][0]['content'] = candidate
        self.error(candidate)
        candidate = copy.deepcopy(self.value)
        candidate['view']['head']['sequence'] = True
        self.error(candidate)
        candidate = copy.deepcopy(self.value)
        candidate['view']['head']['source'] = object()
        self.error(candidate)


if __name__ == '__main__':
    unittest.main()
