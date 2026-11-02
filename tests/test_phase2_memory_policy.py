"""Phase2 synthetic-policy unit fixtures; no E5, Chroma, native or cluster claim.

Real authorization, DTO validation, caller binding and owner receipt paths are
exercised. The encoder and physical payload backend are explicit deterministic
fixtures. No generative runtime is contacted and no model is loaded.
"""
import copy
from dataclasses import asdict, replace
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from fusion import append_contracts as w, embedding_contracts as e, vector_contracts as v
from fusion.append_composition import AppendService, Access as AppendAccess, configuration as append_configuration
from fusion.atom_feed import FeedAtomOwner
from fusion.contracts import ContractError, canonical, digest, encode, require
from fusion.embedding_composition import configuration as embedding_configuration
from fusion.embedding_service import EmbeddingService
from fusion.lookup_composition import AtomSession
from fusion.memory_services import ReceiptAuthority, StoragePorts, SOURCE_PROFILE
from fusion.neoclaw_append import MemoryAppend
from fusion.neoclaw_embedding import QueryEmbedding
from fusion.neoclaw_memory import MemoryRead, configuration as read_configuration
from fusion.policy import Policy
from fusion.preview_text import PROFILE as TEXT_PROFILE
from fusion.registry import descriptor_wire, descriptor_read, selection_token
from fusion.vector_composition import ReadService, descriptors as read_descriptors


class FixtureEncoder:
    """Deterministic vector fixture; never imports a numerical runtime."""
    def __init__(self):
        self.calls = 0

    def encode(self, request):
        self.calls += 1
        return e.encoded(asdict(request), [1.] + [0.] * 1023)


class FixturePhysicalStorage:
    """Explicit in-memory physical bytes beneath the real feed owner."""
    def __init__(self):
        self.values = {}

    def put(self, scope, key, data):
        address = digest(canonical([scope, key]))
        require(address not in self.values or self.values[address] == data, 'CONFLICT')
        self.values[address] = data
        return address, dict(provider='phase2-unit-payload-fixture/1', durability='local-files-process-restart',
                             evidence={'classification': 'fixture-receipt-not-a-durability-claim'})

    def get(self, scope, address):
        return self.values[address]


class PolicyFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-memory-policy-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'policy.json'
        self.scope = 'synthetic-policy-tests'
        self.session = str(uuid.uuid4())
        self.catalogue = [replace(d, receipt_providers=frozenset({'phase2-unit-payload-fixture/1'}))
                          for d in w.descriptors()]
        self.append_chosen = w.select(self.catalogue)
        self.text_policy = dict(profile=TEXT_PROFILE, scope=self.scope, principals=['A', 'B'],
                                purposes=['query', 'remember'], max_utf8_bytes=256, revision='policy-1')
        permissions = ['memory.append.write', 'memory.append.disclose', 'atom.storage.create',
                       'atom.storage.get', 'atom.storage.getMany', 'atom.storage.observe',
                       'atom.storage.head', 'atom.storage.readCommits', 'search.build',
                       'search.published', 'search.query', 'search.ready',
                       'embedding.encode', 'embedding.disclose', 'embedding.memory.encode',
                       'embedding.memory.disclose']
        self.cfg = dict(principals={p: dict(credential=p + '-token', scopes={self.scope: permissions[:]}) for p in ('A', 'B')})
        self.cfg['principals']['indexer'] = dict(credential='indexer-token', scopes={self.scope: ['memory.source.observe']})
        self.cfg['embedding'] = dict(database=str(self.root / 'encoder.sqlite'), scope=self.scope,
            sharing=v.PRIVACY, model=v.EMBEDDING, preprocessing=e.PREPROCESSING,
            catalogue=[descriptor_wire(e.descriptor()), descriptor_wire(e.descriptor(e.MEMORY_PROFILE))],
            approved_helper_inputs=['legacy query'], memory_helper_inputs=['legacy memory'])
        self.cfg['memory_append'] = dict(profile=w.PROFILE, session=self.session, scope=self.scope,
            corpus='generated-policy-corpus', model=v.EMBEDDING, sharing=v.PRIVACY,
            session_principal='A', writers=['A', 'B'], inputs={'legacy memory': 'legacy memory'},
            root=str(self.root / 'projection'), catalogue=[descriptor_wire(d) for d in self.catalogue],
            embedding_selection=selection_token(e.descriptor(e.MEMORY_PROFILE)))
        self.cfg['memory_read'] = dict(root=str(self.root / 'projection'), scope=self.scope,
            corpus='generated-policy-corpus', embedding=v.EMBEDDING, sharing=v.PRIVACY,
            readers=['A', 'B'], catalogue=[descriptor_wire(d) for d in read_descriptors(v.EMBEDDING, True)],
            require_ready=True, queries=['legacy query'], query_vectors=[digest(v.vector_bytes([1.] + [0.] * 1023))])
        self.cfg['source_delegation'] = dict(principal='A', session=self.session, scope=self.scope)
        snap = dict(head=dict(source=str(uuid.uuid4()), scope_ref=self.scope, sequence=0, profile='immutable-commit-feed/1'),
                    corpus='generated-policy-corpus', embedding=v.EMBEDDING, index=v.INDEX, profile=v.PROFILE)
        self.snapshot = dict(snap, logical=digest(canonical(snap)), generation=str(uuid.uuid4()))
        self.encoder = FixtureEncoder()
        self.physical = FixturePhysicalStorage()
        self.save()

    def save(self):
        self.path.write_bytes(canonical(self.cfg))

    def opt_in(self):
        for key in ('embedding', 'memory_append', 'memory_read'):
            self.cfg[key]['text_policy'] = copy.deepcopy(self.text_policy)
        self.cfg['source_delegation'] = dict(profile='preview-receipt-delegation/1', principals=['A', 'B'], scope=self.scope)
        self.save()

    def rejects(self, code, fn, *args, **kwargs):
        with self.assertRaises(ContractError) as error:
            fn(*args, **kwargs)
        self.assertEqual(error.exception.code, code)

    def embedding(self):
        service = EmbeddingService(self.path, self.encoder)
        self.addCleanup(service.close)
        return service

    def encode_request(self, text='new approved synthetic query', principal='A', profile=e.PROFILE,
                       operation='encode', attempt=1, occurrence=None):
        accepted = asdict(e.EncodeInput(occurrence or str(uuid.uuid4()), principal, self.scope, text,
            digest(text.encode()), int(time.time() * 1000) + 30000, selection_token(e.descriptor(profile)), profile=profile))
        return dict(interface_ref={'id': e.INTERFACE, 'version': e.VERSION}, operation=operation,
                    intent=accepted, attempt=attempt if operation == 'encode' else 0)

    def accepted(self, content='new approved synthetic memory', principal='A', session=None):
        return w.intent(dict(profile=w.PROFILE, session=session or self.session, occurrence=str(uuid.uuid4()),
            principal=principal, scope=self.scope, corpus='generated-policy-corpus', uuid=str(uuid.uuid4()),
            time='2026-11-02 09:00:00', content=content, helper_input=content, model=v.EMBEDDING,
            vector_sha256=digest(v.vector_bytes([1.] + [0.] * 1023)), deadline_ms=int(time.time() * 1000) + 30000,
            selections={**{n: selection_token(d) for n, d in self.append_chosen.items()},
                        'embedding': selection_token(e.descriptor(e.MEMORY_PROFILE))}))

    def append(self, credential='A-token', policy=None):
        policy = policy or Policy(self.path)
        access = AppendAccess(policy, credential, self.append_chosen['atom.storage'])
        owner = FeedAtomOwner(self.root / 'feed.sqlite', self.physical, access)
        return AppendService(self.path, credential, atoms=AtomSession(owner, access), policy=policy)

    def append_request(self, accepted, operation='authorize'):
        descriptor = self.append_chosen['atom.storage']
        body = {'mode': 'write'} if operation == 'authorize' else dict(role='binding', content_type=w.BINDING,
                    data=encode(w.binding_bytes(accepted)))
        return dict(request_id=accepted['occurrence'], scope=self.scope,
                    interface_ref=dict(id='atom.storage', version=descriptor.version), operation=operation,
                    profile=next(iter(descriptor.profiles)), selection=selection_token(descriptor), intent=accepted, body=body)

    def read_request(self, service, query='new approved synthetic query'):
        descriptor = service.chosen['search']
        return dict(request_id=str(uuid.uuid4()), scope=self.scope,
                    interface_ref=dict(id='search', version=descriptor.version), operation='authorize',
                    profile=v.PROFILE, selection=selection_token(descriptor),
                    body=dict(query=query, snapshot=self.snapshot))


class DynamicTextPolicy(PolicyFixtures):
    def test_opt_in_embedding_checks_purpose_principal_and_actual_operations(self):
        self.opt_in()
        service = self.embedding()
        for principal, profile in [('A', e.PROFILE), ('B', e.MEMORY_PROFILE)]:
            request = self.encode_request(principal=principal, profile=profile)
            reply = service.invoke(principal + '-token', request)
            self.assertEqual(reply['value']['occurrence'], request['intent']['occurrence'])
        self.assertEqual(self.encoder.calls, 2)
        self.rejects('UNAUTHORIZED', service.invoke, 'B-token', self.encode_request(principal='A'))
        self.rejects('UNAUTHORIZED', service.invoke, 'unknown', self.encode_request())
        self.cfg['embedding']['text_policy']['purposes'] = ['remember']
        self.save()
        self.rejects('UNAUTHORIZED', service.invoke, 'A-token', self.encode_request())
        self.cfg['embedding']['text_policy']['principals'] = ['B']
        self.save()
        self.rejects('UNAUTHORIZED', service.invoke, 'A-token', self.encode_request(profile=e.MEMORY_PROFILE))
        self.assertEqual(self.encoder.calls, 2)

    def test_dynamic_text_validation_and_disclosure_revocation_do_not_evaluate(self):
        self.opt_in()
        service = self.embedding()
        for text in ('', 'x' * 257, 'Ω' * 129, 'line\nnext', 'bad"quote', '_quote_', ':-:-:-:', 'bad\u202einput'):
            self.rejects('INVALID_ARGUMENT', service.invoke, 'A-token', self.encode_request(text=text))
        self.cfg['principals']['A']['scopes'][self.scope].remove('embedding.disclose')
        self.save()
        self.rejects('UNAUTHORIZED', service.invoke, 'A-token', self.encode_request())
        self.assertEqual(self.encoder.calls, 0)

    def test_old_embedding_lists_keep_their_original_text_and_no_new_membership(self):
        service = self.embedding()
        self.rejects('UNAUTHORIZED', service.invoke, 'A-token', self.encode_request())
        self.cfg['embedding']['approved_helper_inputs'].append('legacy "quoted"\ninput')
        self.save()
        self.assertEqual(service.invoke('A-token', self.encode_request(text='legacy "quoted"\ninput'))['value']['dimension'], 1024)
        self.assertNotIn('text_policy', self.cfg['embedding'])
        self.assertEqual(self.encoder.calls, 1)

    def test_embedding_spent_attempt_and_original_intent_survive_reopen(self):
        self.opt_in()
        request = self.encode_request()
        first = self.embedding()
        first.invoke('A-token', request)
        reopened = self.embedding()
        self.rejects('OVERLOADED', reopened.invoke, 'A-token', request)
        changed = copy.deepcopy(request)
        changed['attempt'] = 2
        changed['intent']['text'] = 'different approved text'
        changed['intent']['input_sha256'] = digest(changed['intent']['text'].encode())
        self.rejects('CONFLICT', reopened.invoke, 'A-token', changed)
        self.assertEqual(self.encoder.calls, 1)

    def test_append_new_sessions_are_explicit_but_old_single_session_is_preserved(self):
        legacy = self.append()
        accepted = self.accepted(content='legacy memory')
        legacy.invoke(self.append_request(accepted))
        self.rejects('UNAUTHORIZED', legacy.invoke, self.append_request({**accepted, 'session': str(uuid.uuid4())}))
        self.rejects('UNAUTHORIZED', self.append('B-token').invoke,
                     self.append_request(self.accepted(content='legacy memory', principal='B')))
        self.opt_in()
        current = self.append('B-token')
        dynamic = self.accepted(principal='B', session=str(uuid.uuid4()))
        self.assertTrue(current.invoke(self.append_request(dynamic))['value']['authorized'])
        changed = {**dynamic, 'helper_input': 'different preprocessing'}
        self.rejects('UNAUTHORIZED', current.invoke, self.append_request(changed))
        self.cfg['memory_append']['text_policy']['purposes'] = ['query']
        self.save()
        self.rejects('UNAUTHORIZED', current.invoke, self.append_request(dynamic))

    def test_read_policy_change_is_current_even_for_existing_service_object(self):
        self.opt_in()
        service = ReadService(self.path, 'A-token', atoms=object())
        request = self.read_request(service)
        self.assertTrue(service.invoke(request)['value']['authorized'])
        for field, value in [('principals', ['B']), ('purposes', ['remember']), ('max_utf8_bytes', 2)]:
            self.cfg['memory_read']['text_policy'] = {**self.text_policy, field: value}
            self.save()
            self.rejects('INVALID_ARGUMENT' if field == 'max_utf8_bytes' else 'UNAUTHORIZED', service.invoke, request)
        self.assertEqual(self.encoder.calls, 0)

    def test_old_read_allowlist_and_new_policy_do_not_relax_general_permissions(self):
        legacy = ReadService(self.path, 'A-token', atoms=object())
        legacy.invoke(self.read_request(legacy, 'legacy query'))
        self.rejects('UNAUTHORIZED', legacy.invoke, self.read_request(legacy))
        self.opt_in()
        service = ReadService(self.path, 'A-token', atoms=object())
        self.cfg['principals']['A']['scopes'][self.scope].remove('search.query')
        self.save()
        self.rejects('UNAUTHORIZED', service.invoke, self.read_request(service))

    def test_actual_vector_query_checks_current_policy_before_fixture_projection(self):
        self.opt_in()
        service = ReadService(self.path, 'A-token', atoms=object())
        descriptor = service.chosen['search']
        body = asdict(v.VectorQuery(str(uuid.uuid4()), self.scope, self.snapshot,
                      [1.] + [0.] * 1023, 1, int(time.time() * 1000) + 30000))
        request = dict(request_id=body['request_id'], scope=self.scope,
                       interface_ref=dict(id='search', version=descriptor.version), operation='query',
                       profile=v.PROFILE, selection=selection_token(descriptor), body=body)
        calls = []
        def projected(q):
            calls.append(q)
            return v.result(dict(request_id=q['request_id'], request_digest=digest(canonical(q)),
                snapshot=q['snapshot'], hits=[], top_k=q['k'], exhaustive=False), q)
        with patch.object(service, 'search', return_value=SimpleNamespace(query=projected)):
            service.invoke(request)
            for field, value in [('principals', ['B']), ('purposes', ['remember'])]:
                self.cfg['memory_read']['text_policy'] = {**self.text_policy, field: value}
                self.save()
                self.rejects('UNAUTHORIZED', service.invoke, request)
        self.assertEqual(len(calls), 1)

    def test_existing_read_service_refuses_changed_owner_and_model_binding(self):
        self.opt_in()
        service = ReadService(self.path, 'A-token', atoms=object())
        request = self.read_request(service)
        original = copy.deepcopy(self.cfg)
        for field, value in [('root', '/unapproved-owner'), ('corpus', 'changed'), ('embedding', v.FIXTURE)]:
            self.cfg = copy.deepcopy(original)
            self.cfg['memory_read'][field] = value
            self.save()
            self.rejects('CONFLICT', service.invoke, request)


class FrozenClientPolicy(PolicyFixtures):
    def test_all_three_callers_freeze_policy_and_refuse_changed_bindings(self):
        self.opt_in()
        policy = copy.deepcopy(self.text_policy)
        configurations = {
            'embedding': dict(profile=e.PROFILE, sharing=v.PRIVACY, fallback=False, model=v.EMBEDDING,
                preprocessing=e.PREPROCESSING, principal='A', scope=self.scope, inputs={}, placement='local',
                provider_config='not-opened-by-this-test', catalogue=[descriptor_wire(e.descriptor())], text_policy=policy),
            'append': dict(self.cfg['memory_append'], principal='A', inputs={}, placement='local', fallback=False,
                metadata_root='not-opened-by-this-test', provider_config='not-opened-by-this-test'),
            'read': dict(principal='A', scope=self.scope, sharing=v.PRIVACY, profile=v.PROFILE,
                embedding=v.EMBEDDING, snapshot=self.snapshot, queries=[], metadata_seal='0' * 64,
                native_config={'recall': 2, 'similarity': 4, 'inflation': 4},
                catalogue=self.cfg['memory_read']['catalogue'], require_ready=True, text_policy=policy),
        }
        for kind, configuration in configurations.items():
            with self.subTest(kind=kind):
                path = self.root / (kind + '-client.json')
                path.write_bytes(canonical(configuration))
                loader = {'embedding': embedding_configuration, 'append': append_configuration, 'read': read_configuration}[kind]
                _, _, frozen = loader(path)
                self.assertEqual(frozen['text_policy'], self.text_policy)
                if kind == 'embedding':
                    caller = QueryEmbedding.__new__(QueryEmbedding)
                    caller.app = SimpleNamespace(config={'embedding_config': str(path)}, binding={'query_embedding': frozen})
                elif kind == 'append':
                    caller = MemoryAppend.__new__(MemoryAppend)
                    caller.app = SimpleNamespace(config={'memory_append_config': str(path)}, binding={'memory_append': frozen})
                else:
                    caller = MemoryRead.__new__(MemoryRead)
                    caller.app = SimpleNamespace(config={'memory_read_config': str(path)}, binding={'memory': frozen}, append_enabled=False)
                caller.settings()
                configuration['text_policy'] = {**policy, 'revision': 'policy-2'}
                path.write_bytes(canonical(configuration))
                self.rejects('CONFLICT', caller.settings)

    def test_old_empty_lists_remain_refused_without_explicit_opt_in(self):
        cfg = dict(profile=e.PROFILE, sharing=v.PRIVACY, fallback=False, model=v.EMBEDDING,
                   preprocessing=e.PREPROCESSING, principal='A', scope=self.scope, inputs={},
                   placement='local', provider_config='never-opened', catalogue=[descriptor_wire(e.descriptor())])
        path = self.root / 'empty-client.json'
        path.write_bytes(canonical(cfg))
        self.rejects('INVALID_ARGUMENT', embedding_configuration, path)
        cfg['text_policy'] = copy.deepcopy(self.text_policy)
        path.write_bytes(canonical(cfg))
        embedding_configuration(path)
        cfg['text_policy']['scope'] = 'private-memory'
        path.write_bytes(canonical(cfg))
        self.rejects('UNSUPPORTED_PROFILE', embedding_configuration, path)


class ReceiptDelegation(PolicyFixtures):
    def source_request(self, accepted, role='binding'):
        return dict(request_id=str(uuid.uuid4()), profile=SOURCE_PROFILE, scope=self.scope,
                    selection=selection_token(self.append_chosen['atom.storage']), operation='observe',
                    body=dict(intent=accepted, role=role))

    def source(self, request, credential='indexer-token'):
        # Exercise real StoragePorts/AppendService/delegated authority/feed owner.
        # Only physical payload bytes are substituted; no DeTTa process starts.
        def injected(path, token, hook=lambda _: None, *, policy=None):
            return self.append(token, policy)
        with patch('fusion.memory_services.AppendService', side_effect=injected):
            return StoragePorts(self.path).invoke('/memory-source', credential, request)

    def test_legacy_delegation_keeps_exact_session_principal_and_scope(self):
        accepted = self.accepted(content='legacy memory')
        self.append().invoke(self.append_request(accepted, 'create'))
        self.assertTrue(self.source(self.source_request(accepted))['value']['found'])
        for field, value in [('session', str(uuid.uuid4())), ('principal', 'B'), ('scope', 'synthetic-other')]:
            changed = {**accepted, field: value}
            self.rejects('UNAUTHORIZED', self.source, self.source_request(changed))
        self.cfg['source_delegation']['session'] = str(uuid.uuid4())
        self.save()
        self.rejects('UNAUTHORIZED', self.source, self.source_request(accepted))

    def test_dynamic_delegation_observes_exact_bound_session_without_cross_principal_leak(self):
        self.opt_in()
        accepted = self.accepted(principal='B', session=str(uuid.uuid4()))
        self.append('B-token').invoke(self.append_request(accepted, 'create'))
        reply = self.source(self.source_request(accepted))
        self.assertEqual(reply['principal'], 'indexer')
        self.assertTrue(reply['value']['found'])
        self.rejects('CONFLICT', self.source, self.source_request({**accepted, 'session': str(uuid.uuid4())}))
        # Another allowed caller has an independent principal-scoped acceptance.
        self.assertFalse(self.source(self.source_request({**accepted, 'principal': 'A'}))['value']['found'])
        for credential in ('B-token', 'wrong'):
            self.rejects('UNAUTHORIZED', self.source, self.source_request(accepted), credential)
        self.rejects('UNAUTHORIZED', self.source, {**self.source_request(accepted), 'scope': 'synthetic-other'})

    def test_delegation_is_read_only_and_checks_both_current_grants(self):
        self.opt_in()
        accepted = self.accepted()
        self.append().invoke(self.append_request(accepted, 'create'))
        delegated = ReceiptAuthority(Policy(self.path), 'indexer-token', accepted)
        self.rejects('UNAUTHORIZED', delegated.check, 'A', self.scope, 'atom.storage.create')
        self.rejects('UNAUTHORIZED', delegated.check, 'B', self.scope, 'atom.storage.observe')
        original = copy.deepcopy(self.cfg)
        for principal, permission in [('A', 'memory.append.disclose'), ('A', 'atom.storage.observe'),
                                       ('indexer', 'memory.source.observe')]:
            self.cfg = copy.deepcopy(original)
            self.cfg['principals'][principal]['scopes'][self.scope].remove(permission)
            self.save()
            self.rejects('UNAUTHORIZED', self.source, self.source_request(accepted))
        self.cfg = copy.deepcopy(original)
        self.cfg['source_delegation']['principals'] = ['A']
        self.save()
        self.rejects('UNAUTHORIZED', self.source, self.source_request(accepted))

    def test_receipt_capability_cannot_expand_to_another_generally_authorized_scope(self):
        self.opt_in()
        accepted = self.accepted()
        other = 'synthetic-other-policy-tests'
        self.cfg['principals']['A']['scopes'][other] = ['memory.append.disclose', 'atom.storage.observe']
        self.cfg['principals']['indexer']['scopes'][other] = ['memory.source.observe']
        self.save()
        delegated = ReceiptAuthority(Policy(self.path), 'indexer-token', accepted)
        self.rejects('UNAUTHORIZED', delegated.check, 'A', other, 'atom.storage.observe')


if __name__ == '__main__':
    unittest.main()
