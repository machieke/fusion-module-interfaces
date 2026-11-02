"""Pure catalogue/SDK adversarial checks; no owner, socket, runtime or journal.

Provider substitutions are descriptor fixtures, not independent runtime-provider
evidence. SDK TLS construction/transport are mocked explicitly. Native command
execution is outside this suite; it checks pre-dispatch whole-batch admission.
"""
import copy
from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from examples.phase2_provider.server import descriptor as feed_descriptor
from fusion import append_contracts as append, embedding_contracts as embedding
from fusion import preview_handles as handles, vector_contracts as vector
from fusion.contracts import ContractError, canonical, digest
from fusion.preview_application import APPLICATION, configuration
from fusion.preview_client import AtomFeedClient, Endpoint, strict_json
from fusion.preview_memory_services import descriptor as memory_descriptor
from fusion.preview_ports import descriptor as facet_descriptor
from fusion.preview_tools import Catalogue, SessionAuthority, context_tools, lifecycle_tools, workspace_tools
from fusion.registry import descriptor_wire, selection_token
from fusion.vector_composition import descriptors as read_descriptors


class CatalogueAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.scope = 'synthetic-catalogue-adversarial'
        self.provider = facet_descriptor('execution.workspace')
        self.workspace = workspace_tools()
        self.authority = SessionAuthority('A', self.scope,
            frozenset({'pin', 'read-file', 'write-file', 'append-file', 'update', 'forget'}), 'policy-1', 5000)

    def rejects(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def catalogue(self, providers=None, tools=None):
        tools = self.workspace if tools is None else tools
        return Catalogue(tools, {t.tool_id for t in tools}, [self.provider] if providers is None else providers)

    def lifecycle(self):
        providers = [*append.descriptors(), *read_descriptors(vector.EMBEDDING, True),
            embedding.descriptor(), embedding.descriptor(embedding.MEMORY_PROFILE),
            memory_descriptor('search'), memory_descriptor('memory.lifecycle')]
        return self.catalogue(providers, lifecycle_tools())

    def test_compatible_patch_selection_is_order_independent_and_minor_ceiling_is_exclusive(self):
        patch_provider = replace(self.provider, provider='fixture-compatible', version='1.0.9')
        too_new = replace(self.provider, provider='fixture-too-new', version='1.1.0')
        for providers in ([self.provider, too_new, patch_provider], [patch_provider, self.provider, too_new]):
            with self.subTest(order=[p.provider for p in providers]):
                selected = self.catalogue(providers)
                self.assertEqual(selected.selections['write-file'], [patch_provider])
        for version in ('0.9.9', '1.1.0', '2.0.0'):
            with self.subTest(version=version):
                self.rejects('UNSUPPORTED_VERSION', self.catalogue, [replace(self.provider, version=version)])

    def test_higher_version_with_wrong_profile_does_not_displace_compatible_provider(self):
        incompatible = replace(self.provider, version='1.0.9', profiles=frozenset({'arbitrary-shell/1'}))
        selected = self.catalogue([incompatible, self.provider])
        self.assertEqual(selected.selections['read-file'], [self.provider])
        self.rejects('UNSUPPORTED_PROFILE', self.catalogue, [incompatible])

    def test_provider_claims_do_not_substitute_for_required_operation_feature_or_privacy(self):
        for provider, code in (
            (replace(self.provider, operations=self.provider.operations-{'append'}), 'UNSUPPORTED_OPERATION'),
            (replace(self.provider, features=frozenset()), 'UNSUPPORTED_PROFILE'),
            (replace(self.provider, guarantees=self.provider.guarantees-{'idempotent'}), 'NOT_AVAILABLE'),
            (replace(self.provider, privacy='private-local-only'), 'NOT_AVAILABLE'),
        ):
            with self.subTest(code=code, provider=provider): self.rejects(code, self.catalogue, [provider])

    def test_independent_descriptor_replacement_requires_new_catalogue_binding(self):
        original = self.catalogue()
        alternative = replace(self.provider, provider='fixture-independent-workspace', implementation_version='7.0.0')
        changed = self.catalogue([alternative])
        self.assertNotEqual(original.identity, changed.identity)
        self.assertEqual(changed.binding()['tools']['read-file']['providers'], [selection_token(alternative)])
        self.rejects('CONFLICT', changed.admit, [['read-file', 'note.txt']], self.authority, 'A', 1000, original.identity)
        admitted = changed.admit([['read-file', 'note.txt']], self.authority, 'A', 1000, changed.identity)
        self.assertEqual(admitted[0]['selection'], changed.identity)
        self.assertEqual(admitted[0]['scope'], self.scope)

    def test_selected_catalogue_and_binding_are_independent_of_configuration_order(self):
        first = self.catalogue(tools=(*context_tools(), *self.workspace))
        second = self.catalogue(tools=tuple(reversed((*context_tools(), *self.workspace))))
        self.assertEqual(first.binding(), second.binding())
        self.assertEqual(first.identity, second.identity)
        detached = first.binding()
        detached['tools']['write-file']['providers'].append('forged')
        self.assertEqual(first.identity, second.identity)

    def test_provider_operations_cannot_register_native_vocabulary_or_grant_authority(self):
        provider = replace(self.provider, operations=self.provider.operations|{'shell', 'send'})
        cfg = dict(profile=APPLICATION, base='controlled-native-loop/1', authority_file='/not-opened',
                   tools=['read-file'], scope=self.scope, providers=[descriptor_wire(provider)])
        cat = configuration(cfg)
        self.assertEqual(set(cat.tools), {'read-file'})
        self.rejects('UNSUPPORTED_OPERATION', cat.admit, [['shell', 'id']], self.authority, 'A', 1000)
        self.rejects('UNSUPPORTED_OPERATION', configuration, dict(cfg, tools=['shell']))
        denied = replace(self.authority, tools=frozenset())
        self.assertEqual(cat.skills(denied, 'A', 1000), [])
        self.rejects('UNAUTHORIZED', cat.admit, [['read-file', 'note.txt']], denied, 'A', 1000)

    def test_whole_batch_rejects_later_path_attack_without_returning_partial_admission(self):
        cat = self.catalogue(tools=(*context_tools(), *self.workspace))
        original = [['pin', 'goal', 'Synthetic task'], ['write-file', '../private.key', 'synthetic']]
        untouched = copy.deepcopy(original)
        self.rejects('INVALID_ARGUMENT', cat.admit, original, self.authority, 'A', 1000)
        self.assertEqual(original, untouched)
        for path in ('/etc/passwd', 'file:///secret', 'a/b', 'a\\b', '.hidden', 'note.txt\x00suffix'):
            with self.subTest(path=path):
                self.rejects('INVALID_ARGUMENT', cat.admit,
                    [['write-file', 'valid.txt', 'synthetic'], ['read-file', path]], self.authority, 'A', 1000)

    def test_authority_revocation_expiry_principal_and_private_scope_block_full_batch(self):
        cat = self.catalogue()
        commands = [['read-file', 'note.txt'], ['write-file', 'note.txt', 'Synthetic']]
        for authority, principal, now in ((replace(self.authority, revoked=True), 'A', 1000),
            (self.authority, 'B', 1000), (self.authority, 'A', 5000),
            (replace(self.authority, scope='private-personal-memory'), 'A', 1000)):
            with self.subTest(principal=principal, now=now, authority=authority):
                self.rejects('UNAUTHORIZED', cat.admit, commands, authority, principal, now)

    def test_lifecycle_tool_schema_rejects_nonmemory_handle_in_entire_batch(self):
        cat = self.lifecycle()
        other = handles.make('episode', self.scope, 'A', {'scope_ref': self.scope, 'id': 'episode-1'})['handle']
        payload = dict(scope_ref=self.scope, id='payload', revision=1, digest='a'*64)
        memory = handles.make('memory', self.scope, 'A', {'payload': payload, 'enrollment': dict(payload, id='enrollment')})['handle']
        self.assertEqual(cat.admit([['forget', memory]], self.authority, 'A', 1000)[0]['arguments']['target'], memory)
        for command in (['forget', other], ['update', other, 'Synthetic replacement']):
            with self.subTest(operation=command[0]):
                self.rejects('INVALID_ARGUMENT', cat.admit, [['forget', memory], command], self.authority, 'A', 1000)

    def test_forged_handle_kind_cannot_be_reinterpreted_as_valid_target_envelope(self):
        atom = dict(scope_ref=self.scope, id='opaque-atom', revision=1, digest='a'*64)
        memory = handles.make('memory', self.scope, 'A', dict(payload=atom, enrollment=dict(atom, id='enrollment')))
        # It is syntactically a valid UUIDv5 but not the relation target's name.
        forged = dict(memory, kind='relation', target=atom, handle=memory['handle'].replace(':memory:', ':relation:'))
        handles.parse(forged['handle'], 'relation')
        self.rejects('CONFLICT', handles.envelope, forged, kind='relation', scope=self.scope, principal='A')
        event = dict(episode={'scope_ref': 'private-personal-memory', 'id': 'private'}, occurrence_id='one',
                     sequence=1, event_ref=atom)
        self.rejects('UNAUTHORIZED', handles.make, 'event', self.scope, 'A', event)


class SDKAdversarialPureTests(unittest.TestCase):
    def rejects(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def client(self, descriptor=None):
        with patch('fusion.preview_client.ssl.create_default_context', return_value=Mock()) as tls:
            client = AtomFeedClient(Endpoint('fixture.invalid', 8443, '/not-read/fixture-ca.crt'),
                'synthetic-sdk-token', 'A', 'synthetic-sdk-adversarial', descriptor or feed_descriptor(), deadline_ms=2**62)
        tls.assert_called_once()
        return client

    def test_getmany_rejects_any_foreign_scope_before_any_transport(self):
        client = self.client()
        public = dict(scope_ref=client.scope, id='public', revision=1, digest='a'*64)
        private = dict(public, scope_ref='private-personal-memory', id='private')
        with patch.object(client, '_invoke') as transport:
            self.rejects('UNAUTHORIZED', client.getMany, (public, private))
        transport.assert_not_called()

    def test_feed_foreign_scope_ref_is_rejected_as_malformed_provider_result(self):
        client = self.client()
        through = dict(source='11111111-1111-4111-8111-111111111111', scope_ref=client.scope,
                       sequence=1, profile='immutable-commit-feed/1')
        value = dict(through=through, after=0, next_after=1, complete=True, records=[dict(sequence=1,
            ref=dict(scope_ref='private-personal-memory', id='private', revision=1, digest='a'*64),
            content_type='application/synthetic', size=1)])
        with patch.object(client, '_invoke', return_value=value):
            self.rejects('NOT_AVAILABLE', client.readCommits, client.scope, 0, through, 1)

    def test_strict_json_rejects_overflowing_numeric_literals_at_every_depth(self):
        for wire in (b'1e999', b'-1e999', b'{"usage":1e999}', b'{"data":[{"score":-1e999}]}'):
            with self.subTest(wire=wire): self.rejects('NOT_AVAILABLE', strict_json, wire)
        self.assertEqual(strict_json(b'{"score":1e3}'), {'score': 1000.0})

    def test_nested_duplicate_scope_or_selection_cannot_shadow_valid_values(self):
        for wire in (b'{"value":{"scope_ref":"synthetic-a","scope_ref":"private-b"}}',
                     b'{"value":[{"selection":"trusted","selection":"forged"}]}'):
            with self.subTest(wire=wire): self.rejects('NOT_AVAILABLE', strict_json, wire)
        data = {'value': {'scope_ref': 'synthetic-sdk-adversarial', 'text': 'Synthetic'}}
        self.assertEqual(digest(canonical(strict_json(canonical(data)))), digest(canonical(data)))


if __name__ == '__main__': unittest.main()
