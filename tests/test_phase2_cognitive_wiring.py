"""Generated cognitive configuration and authorization, without owner execution.

Secret material and configuration functions are real. TLS certificate bytes and
completion DTOs are labelled fixtures. No native kernel, model, socket, storage
provider, database owner, cluster or numerical evaluation is instantiated.
"""
import copy
import json
from pathlib import Path
import secrets
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

from fusion import cognitive_services as c, delivery_contracts as delivery
from fusion import nal_memory_contracts as numerical
from fusion.contracts import ContractError, canonical, digest
from fusion.nal_episodes import NalEpisodeOwner
from fusion.policy import Policy
from fusion.ports import Mutation
from fusion.registry import selection_token
from integration.single_node.preview_cognitive_configure import NAMES
from integration.single_node.preview_configure import COMPOSITION, configure
from integration.single_node.preview_secrets import material


class CognitiveWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-cognitive-wiring-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roles = ('omega-agent', 'fusion-execution', 'fusion-storage', 'fusion-messaging',
            'omega-agent-b', 'fusion-model', 'fusion-episodes', 'fusion-relations', 'fusion-search',
            'fusion-embedding', 'fusion-beliefs', 'fusion-attention')
        self.agents = {role: dict(principal=who, sessions=[str(uuid.uuid4())],
            tools=['remember', 'query', 'episodes', 'support', 'contradict', 'promote', 'demote'],
            facets=['episodic.memory']) for role, who in [('omega-agent', 'A'), ('omega-agent-b', 'B')]}
        self.scope = 'synthetic-cognitive-wiring'
        self.preview = dict(enabled=True, profile=COMPOSITION, scope=self.scope,
            model_boundary='RECORDED_FIXTURE', authority_expires_ms=int(time.time()*1000)+120000,
            policy_revision='synthetic-cognitive-policy-1', agents=self.agents, assignments=['synthetic-assessment'],
            limits=dict(inputs=8, pending=4, timeout_ms=30000),
            responses={agent['sessions'][0]+'/1': 'episodes current' for agent in self.agents.values()},
            memory=dict(enabled=True, corpus='synthetic-cognitive-corpus'),
            cognition=dict(enabled=True, attention_provider='sqlite'))
        clients = {role: secrets.token_hex(32) for role in self.roles[1:]}
        workers = {role: secrets.token_hex(32) for role in self.roles[1:]}
        self.material = material(self.preview, self.roles, clients)
        for role in self.roles:
            secret = self.root/role/'secrets'; secret.mkdir(parents=True)
            values = {name: b'fixture-not-a-TLS-certificate' for name in ('ca.crt', 'tls.crt', 'tls.key')}
            if role == 'omega-agent': values.update({name+'-token': value.encode() for name, value in clients.items()})
            else:
                values.update({'caller-token': clients[role].encode(), 'worker-token': workers[role].encode()})
                if role == 'fusion-execution':
                    values.update({name+'-token': workers[name].encode() for name in ('fusion-storage', 'fusion-messaging')})
            values.update(self.material[role])
            for name, value in values.items(): (secret/name).write_bytes(value)
        self.configured = {}

    def role(self, role):
        if role not in self.configured:
            settings = dict(role=role, service_composition=COMPOSITION, state=str(self.root/role/'state'),
                run=str(self.root/role/'run'), secret_directory=str(self.root/role/'secrets'), https_port=8443,
                capacity=8, revision='cognitive-wiring-test', native_enabled=True, worker_enabled=False,
                enable_test_faults=False, test={}, preview=copy.deepcopy(self.preview),
                peers={name: name+'.synthetic-preview.svc.cluster.local' for name in self.roles})
            self.configured[role] = configure(settings)
        return self.configured[role]

    def owner_path(self, role): return self.role(role)[3]/'cognitive-owner.json'
    def owner(self, role): return json.loads(self.owner_path(role).read_text())

    def client_path(self, agent='omega-agent-b', kind='evidence'):
        _, _, _, run = self.role(agent)
        return run/'sessions'/self.agents[agent]['sessions'][0]/(kind+'-client.json')

    def rejects(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_generated_a_b_cognitive_ports_authenticate_their_actual_principal(self):
        for agent, spec in self.agents.items():
            client, _ = c.client_configuration(self.client_path(agent))
            self.assertEqual((client['principal'], client['session']), (spec['principal'], spec['sessions'][0]))
            for name, port in client['ports'].items():
                role = c.ROLES[name]
                access = c.Access(self.owner_path(role), port['credential'], name)
                self.assertEqual(access.principal, spec['principal'])
                self.assertEqual(port['endpoint']['host'], role+'.synthetic-preview.svc.cluster.local')
                self.assertEqual(access.authorize(self.scope, c.OPERATIONS[name][0]), spec['principal'])
                self.rejects('UNSUPPORTED_PROFILE', access.authorize, 'synthetic-private-other', c.OPERATIONS[name][0])

    def test_b_delegated_atom_credentials_preserve_principal_and_narrow_operations(self):
        path = self.owner_path('fusion-storage')
        cfg = self.owner('fusion-storage')
        for source in ('fusion-episodes', 'fusion-beliefs'):
            provider = self.owner(source)
            credential = provider['ports_by_principal']['B']['atom.storage']['credential']
            actor = 'cognition-'+source+'-B'
            self.assertEqual(Policy(path).authenticate(credential), actor)
            self.assertEqual(cfg['actors'][actor], 'B')
            access = c.Access(path, credential, 'atom.storage')
            self.assertEqual(access.authorize(self.scope, 'create'), 'B')
            self.rejects('UNAUTHORIZED', access.authorize, self.scope, 'readCommits')
            self.assertNotEqual(credential, provider['ports_by_principal']['A']['atom.storage']['credential'])
            self.assertNotEqual(credential, self.material['omega-agent-b']['atom-B-token'].decode())

    def test_b_relay_is_bound_to_b_consumer_and_cannot_acknowledge_a_completion(self):
        cfg = self.owner('fusion-episodes')
        credential = self.owner('fusion-beliefs')['ports_by_principal']['B']['episodic.memory']['credential']
        access = c.Access(self.owner_path('fusion-episodes'), credential, 'episodic.memory')
        self.assertEqual((access.identity, access.principal), ('completion-relay-B', 'B'))
        self.assertEqual(access.completionConsumer(self.scope)['principal'], 'B')
        ref = dict(scope_ref=self.scope, id='synthetic-claim', revision=1, digest='a'*64)
        evidence = dict(episode=dict(scope_ref=self.scope, id='synthetic-A-episode'), occurrence_id='synthetic-A-evidence',
                        sequence=1, event_ref=dict(ref, id='synthetic-event'))
        consumer = c.consumer(cfg, 'A')
        request_key = 'synthetic-A-decision'
        completed = dict(profile=delivery.COMPLETION, state='committed', scope_ref=self.scope,
            delivery_id=digest(canonical(evidence)), evidence=evidence, claim=ref, context='synthetic-context',
            consumer=consumer, request_key=request_key, request_digest='b'*64,
            decision_id=digest(canonical(['A', self.scope, request_key])), decision_digest='c'*64)
        delivery.completion(completed)
        # Exercise the real C1 pre-journal barrier. The DTO is not an assertion
        # that a delivery/decision exists; no owner state is opened or written.
        owner = NalEpisodeOwner.__new__(NalEpisodeOwner)
        owner.c, owner.access = numerical, access
        owner._connect = Mock(side_effect=AssertionError('owner journal must remain unopened'))
        self.rejects('UNSUPPORTED_PROFILE', owner.acknowledgeDelivery, Mutation(self.scope, 'synthetic-ack'), completed)
        owner._connect.assert_not_called()
        # A rewritten B-consumer DTO still cannot change C1 episode ownership.
        # This is the real ownership check over a declared read-result fixture;
        # no SQL database or acceptance transition is created for this test.
        read_result = Mock()
        read_result.execute.return_value.fetchone.return_value = {'owner': 'A'}
        self.rejects('UNAUTHORIZED', owner._episode, read_result, evidence['episode'], access.principal)
        direct = c.Access(self.owner_path('fusion-episodes'), self.material['omega-agent-b']['cognitive-fusion-episodes-token'].decode(), 'episodic.memory')
        self.rejects('UNAUTHORIZED', direct.authorize, self.scope, 'acknowledgeDelivery')

    def test_relay_and_storage_delegation_recheck_current_principal_permission(self):
        for role, interface, credential, operation, principal in (
            ('fusion-episodes', 'episodic.memory', self.owner('fusion-beliefs')['ports_by_principal']['B']['episodic.memory']['credential'], 'readEvidence', 'B'),
            ('fusion-storage', 'atom.storage', self.owner('fusion-episodes')['ports_by_principal']['B']['atom.storage']['credential'], 'get', 'B')):
            path = self.owner_path(role)
            access = c.Access(path, credential, interface)
            self.assertEqual(access.authorize(self.scope, operation), principal)
            cfg = json.loads(path.read_text())
            cfg['principals'][principal]['scopes'][self.scope].remove(interface+'.'+operation)
            path.write_bytes(canonical(cfg))
            self.rejects('UNAUTHORIZED', access.authorize, self.scope, operation)

    def test_real_relay_decision_read_checks_owned_episode_and_current_read_permission(self):
        from fusion.nal_relay import NalEvidenceRelay
        episode_path = self.owner_path('fusion-episodes')
        caller = c.Access(episode_path, self.material['omega-agent-b']['cognitive-fusion-episodes-token'].decode(), 'episodic.memory')
        database = self.root/'episode-read.sqlite'
        # The actual empty C1 journal and relay execute; no payload or numerical
        # provider is required by this bounded audit. Poison the unused ports.
        atoms = Mock(side_effect=AssertionError('no payload read for empty episode'))
        episodes = NalEpisodeOwner(database, atoms, caller)
        episode = episodes.recordEpisode(Mutation(self.scope, 'B-empty'), 'synthetic-source')['ref']
        beliefs_cfg = self.owner('fusion-beliefs')
        credential = beliefs_cfg['ports_by_principal']['B']['episodic.memory']['credential']
        delegated = c.Access(episode_path, credential, 'episodic.memory')
        episodes = NalEpisodeOwner(database, atoms, delegated)
        access = c.Access(self.owner_path('fusion-beliefs'), self.material['omega-agent-b']['cognitive-fusion-beliefs-token'].decode(), 'belief.revision')
        beliefs = Mock()
        relay = NalEvidenceRelay(self.root/'relay-read.sqlite', episodes, beliefs,
            consumer=c.consumer(beliefs_cfg, 'B'), access=access, acknowledger=episodes)
        self.assertEqual(relay.decisions(episode), ())
        beliefs.assert_not_called()
        self.rejects('UNAUTHORIZED', delegated.authorize, self.scope, 'appendEvent')
        cfg = json.loads(episode_path.read_text())
        cfg['principals']['B']['scopes'][self.scope].remove('episodic.memory.readEpisode')
        episode_path.write_bytes(canonical(cfg))
        self.rejects('UNAUTHORIZED', relay.decisions, episode)

    def test_readonly_authorize_port_binds_b_and_does_not_create_owner(self):
        role, name = 'fusion-beliefs', 'belief.revision'
        path = self.owner_path(role)
        credential = self.material['omega-agent-b']['cognitive-fusion-beliefs-token'].decode()
        selected = c.catalogue(self.owner(role))[name]
        q = dict(id=str(uuid.uuid4()), composition=c.COMPOSITION, scope=self.scope, interface=name,
                 selection=selection_token(selected), operation='authorize', args=['readBelief'])
        port = c.Ports(path, role)
        with patch.object(port, 'owner', side_effect=AssertionError('authorization must not instantiate owner')) as owner:
            result = port.invoke(c.ROUTE, credential, q)
            self.assertEqual((result['principal'], result['value']), ('B', 'B'))
            self.assertEqual(result['request_digest'], digest(canonical(q)))
            self.rejects('UNAUTHORIZED', port.invoke, c.ROUTE, 'wrong-synthetic-token', q)
        owner.assert_not_called()

    def test_authenticated_b_selects_only_b_delegation_before_readonly_owner_dispatch(self):
        role, name = 'fusion-beliefs', 'belief.revision'
        path = self.owner_path(role)
        provider = self.owner(role)
        selected = c.catalogue(provider)[name]
        q = dict(id=str(uuid.uuid4()), composition=c.COMPOSITION, scope=self.scope, interface=name,
            selection=selection_token(selected), operation='readBelief', args=[
                dict(scope_ref=self.scope, id='synthetic-claim', revision=1, digest='a'*64),
                'synthetic-context', 0])
        port = c.Ports(path, role)
        read_owner = Mock()
        read_owner.readBelief.return_value = {'boundary': 'READ_RESULT_FIXTURE'}
        with patch.object(port, 'owner', return_value=read_owner) as factory:
            result = port.invoke(c.ROUTE, self.material['omega-agent-b']['cognitive-fusion-beliefs-token'].decode(), q)
        dispatched_cfg, access, dispatched_interface = factory.call_args.args
        self.assertEqual((dispatched_cfg['principal'], access.principal, dispatched_interface), ('B', 'B', name))
        self.assertEqual(dispatched_cfg['ports'], provider['ports_by_principal']['B'])
        self.assertNotEqual(dispatched_cfg['ports'], provider['ports_by_principal']['A'])
        self.assertEqual(result['principal'], 'B')
        self.assertEqual(result['value'], {'boundary': 'READ_RESULT_FIXTURE'})

    def test_selected_client_modules_do_not_expose_relations_or_exact_search(self):
        path = self.client_path()
        cfg, frozen = c.client_configuration(path)
        self.assertEqual(set(cfg['selected_interfaces']), set(NAMES))
        self.assertEqual(set(cfg['ports']), set(NAMES))
        self.assertNotIn('relations', cfg['ports'])
        self.assertNotIn('search', cfg['ports'])
        with patch('fusion.cognitive_services.Connection', return_value=Mock()) as connections:
            modules = c.modules(path, self.root/'not-created')
        self.assertEqual(set(modules.access), set(NAMES))
        self.assertEqual(connections.call_count, len(NAMES))
        self.assertTrue(all(call.kwargs['principal'] == 'B' for call in connections.call_args_list))
        self.assertFalse((self.root/'not-created').exists())
        cfg['ports']['relations'] = copy.deepcopy(cfg['ports']['episodic.memory'])
        path.write_bytes(canonical(cfg))
        self.rejects('UNSUPPORTED_PROFILE', c.client_configuration, path)

    def test_generated_configs_keep_owner_paths_and_live_generation_disabled(self):
        for role in ('fusion-storage', 'fusion-episodes', 'fusion-beliefs', 'fusion-attention'):
            cfg = self.owner(role)
            state = self.role(role)[2]
            self.assertTrue(Path(cfg['root']).is_relative_to(state))
            self.assertFalse(Path(cfg['root']).exists())
            for ports in cfg.get('ports_by_principal', {}).values():
                for port in ports.values(): self.assertEqual(set(port), {'endpoint', 'credential'})
            for other in self.roles:
                if other != role:
                    self.assertNotIn(str(self.root/other/'state'), canonical(cfg).decode())
        for agent in self.agents:
            cfg, frozen = c.client_configuration(self.client_path(agent, 'attention'))
            self.assertTrue(Path(cfg['output']).is_relative_to(self.role(agent)[2]))
            self.assertNotIn('root', cfg)
            self.assertNotIn('runtime', cfg)
            sid = self.agents[agent]['sessions'][0]
            app = json.loads((self.role(agent)[3]/'sessions'/sid/'application.json').read_text())
            self.assertNotIn('model_fixture', app)
            self.assertEqual(app['preview']['base'], c.APPLICATION)
        model = self.role('fusion-model')[1]['model_completion']
        self.assertEqual(model['runtime_lock']['generative_runtime'], 'FORBIDDEN')
        self.assertFalse(Path(model['database']).exists())

    def test_attention_provider_selection_changes_explicit_config_without_kernel_execution(self):
        self.preview['cognition']['attention_provider'] = 'file-fixture'
        for role in ('fusion-storage', 'fusion-episodes', 'fusion-beliefs', 'fusion-attention'):
            cfg = self.owner(role)
            self.assertEqual(cfg['attention_provider'], 'file-fixture')
            selected = c.catalogue(cfg)['attention']
            self.assertEqual(selected.provider, 'synthetic-attention-file-fixture')
            for agent in self.agents:
                client, frozen = c.client_configuration(self.client_path(agent))
                self.assertEqual(frozen['selections']['attention'], selection_token(selected))
                name = next(name for name in NAMES if c.ROLES[name] == role)
                access = c.Access(self.owner_path(role), client['ports'][name]['credential'], name)
                self.assertEqual(access.authorize(self.scope, c.OPERATIONS[name][0]), self.agents[agent]['principal'])

    def test_storage_rejects_catalogue_with_missing_or_mismatched_provider_discriminator(self):
        self.preview['cognition']['attention_provider'] = 'file-fixture'
        cfg = self.owner('fusion-storage')
        for label in (None, 'sqlite'):
            changed = copy.deepcopy(cfg)
            if label is None: changed.pop('attention_provider')
            else: changed['attention_provider'] = label
            self.rejects('UNSUPPORTED_PROFILE', c.catalogue, changed)


if __name__ == '__main__': unittest.main()
