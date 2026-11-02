"""Light preview wiring checks, without cluster, native or model execution.

Credential material/configuration and SQLite session/model owners are real.
TLS files and subprocesses are explicit fixtures; no socket or TLS handshake
is claimed, and model authorization tests never reserve or call a backend.
"""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import uuid

from fusion import preview_model_contracts as mc
from fusion.contracts import ContractError, canonical
from fusion.model_service import ModelService
from fusion.policy import Policy
from fusion.preview_recorded_model import disclosure, service
from fusion.preview_session_service import SessionPorts
from fusion.preview_sessions import PROFILE
from fusion.registry import selection_token
from integration.single_node.preview_configure import COMPOSITION, configure
from integration.single_node.preview_host import NativeSupervisor
from integration.single_node.preview_secrets import material


class PreviewWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-wiring-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.roles = ('omega-agent', 'fusion-execution', 'fusion-storage', 'fusion-messaging',
                      'omega-agent-b', 'fusion-model', 'fusion-episodes', 'fusion-relations')
        self.agents = {role: dict(principal=principal, sessions=[str(uuid.uuid4())],
            tools=['pin', 'episodes', 'read-file'], facets=['episodic.memory', 'execution.workspace'])
            for role, principal in [('omega-agent', 'A'), ('omega-agent-b', 'B')]}
        self.preview = dict(enabled=True, profile=COMPOSITION, scope='synthetic-preview-wiring',
            model_boundary='RECORDED_FIXTURE', authority_expires_ms=int(time.time()*1000)+120000,
            policy_revision='synthetic-policy-1', agents=self.agents, assignments=['notes'],
            limits=dict(inputs=8, pending=4, timeout_ms=30000), responses={
                agent['sessions'][0]+'/1': 'pin task Synthetic text' for agent in self.agents.values()})
        clients = {role: secrets.token_hex(32) for role in self.roles[1:]}
        workers = {role: secrets.token_hex(32) for role in self.roles[1:]}
        self.material = material(self.preview, self.roles, clients)
        for role in self.roles:
            directory = self.root/role/'secrets'
            directory.mkdir(parents=True)
            values = {name: b'fixture-not-a-TLS-certificate' for name in ('ca.crt', 'tls.crt', 'tls.key')}
            if role == 'omega-agent':
                values.update({name+'-token': value.encode() for name, value in clients.items()})
            else:
                values.update({'caller-token': clients[role].encode(), 'worker-token': workers[role].encode()})
                if role == 'fusion-execution':
                    values.update({name+'-token': workers[name].encode() for name in ('fusion-storage', 'fusion-messaging')})
            values.update(self.material[role])
            for name, value in values.items(): (directory/name).write_bytes(value)
        self.configured = {}

    def role(self, role):
        if role not in self.configured:
            settings = dict(role=role, service_composition=COMPOSITION,
                state=str(self.root/role/'state'), run=str(self.root/role/'run'),
                secret_directory=str(self.root/role/'secrets'), https_port=8443, capacity=8,
                revision='wiring-fixture', native_enabled=True, worker_enabled=False,
                enable_test_faults=False, test={},
                peers={name: name+'.synthetic-preview.svc.cluster.local' for name in self.roles},
                preview=copy.deepcopy(self.preview))
            self.configured[role] = configure(settings)
        return self.configured[role]

    def document(self, role, name):
        return json.loads((self.role(role)[3]/name).read_text())

    def call_session(self, operation, *, role='omega-agent', actor='operator', **body):
        _, cfg, _, run = self.role(role)
        sid = self.agents[role]['sessions'][0]
        return SessionPorts(run/'owner.json').invoke(cfg['principals'][actor]['credential'],
            dict(id=str(uuid.uuid4()), profile=PROFILE, operation=operation,
                 body=dict(session=sid, **body)))['value']

    def test_generated_peer_credentials_match_server_and_do_not_alias_principals(self):
        for role, agent in self.agents.items():
            sid, principal = agent['sessions'][0], agent['principal']
            caller = self.document(role, 'sessions/'+sid+'/caller.json')
            for interface, target in [('execution', 'fusion-execution'), ('atom.storage', 'fusion-storage'),
                                      ('agent.messaging', 'fusion-messaging')]:
                provider_path = self.role(target)[3]/'owner.json'
                self.assertEqual(Policy(provider_path).authenticate(caller['service_credentials'][interface]), principal)
                self.assertEqual(caller['endpoints'][interface]['host'], target+'.synthetic-preview.svc.cluster.local')
            model = self.document(role, 'sessions/'+sid+'/model.json')
            self.assertEqual(Policy(self.role('fusion-model')[3]/'owner.json').authenticate(model['credential']), principal)
        for target in ('fusion-execution', 'fusion-storage', 'fusion-messaging', 'fusion-model'):
            cfg = self.role(target)[1]
            self.assertNotEqual(cfg['principals']['A']['credential'], cfg['principals']['B']['credential'])

    def test_facets_use_narrow_delegated_storage_tokens_and_explicit_actor_mapping(self):
        storage = self.document('fusion-storage', 'cognitive-owner.json')
        storage_policy = Policy(self.role('fusion-storage')[3]/'cognitive-owner.json')
        for target in ('fusion-episodes', 'fusion-relations'):
            facet = self.document(target, 'facet-owner.json')
            for role, agent in self.agents.items():
                principal = agent['principal']
                client = facet['atom_clients'][principal]
                actor = storage_policy.authenticate(client['credential'])
                self.assertEqual(actor, 'facet-'+target+'-'+principal)
                self.assertEqual(storage['actors'][actor], principal)
                self.assertEqual(set(storage['principals'][actor]['scopes'][self.preview['scope']]),
                                 {'atom.storage.create', 'atom.storage.get', 'atom.storage.getMany'})
                self.assertNotEqual(client['credential'], self.material[role]['atom-'+principal+'-token'].decode())
                with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
                    storage_policy.check(actor, self.preview['scope'], 'atom.storage.readCommits')
                self.assertEqual(Policy(self.role(target)[3]/'facet-owner.json').authenticate(
                    self.material[role]['facet-'+target+'-token'].decode()), principal)

    def test_owner_mutable_paths_and_agent_session_paths_stay_under_own_state(self):
        for role in self.roles:
            _, cfg, state, run = self.role(role)
            for key in ('database', 'atoms_database', 'messages_database', 'da_root'):
                if key in cfg: self.assertTrue(Path(cfg[key]).is_relative_to(state), (role, key))
            for filename in ('facet-owner.json', 'cognitive-owner.json'):
                if (run/filename).exists():
                    self.assertTrue(Path(json.loads((run/filename).read_text())['root']).is_relative_to(state))
            if role in self.agents:
                self.assertTrue(Path(cfg['native_sessions']['database']).is_relative_to(state))
                for sid in self.agents[role]['sessions']:
                    app = self.document(role, 'sessions/'+sid+'/application.json')
                    self.assertNotIn('model_fixture', app)
                    self.assertTrue(Path(app['workdir']).is_relative_to(state))
                    self.assertTrue(Path(app['status_file']).is_relative_to(state))
                    self.assertFalse(Path(app['workdir']).exists())

    def test_model_authority_is_bound_to_the_principal_owning_the_selected_session(self):
        _, _, state, run = self.role('fusion-model')
        path = run/'owner.json'
        owner = service(path)
        self.addCleanup(owner.close)
        raw = 'Synthetic command catalogue:-:-:-:Synthetic operator input'
        a_session = self.agents['omega-agent']['sessions'][0]
        b_session = self.agents['omega-agent-b']['sessions'][0]
        accepted = asdict(mc.CompletionInput(id=str(uuid.uuid4()), session=a_session, slot=1,
            source_id=str(uuid.uuid4()), principal='A', scope=self.preview['scope'],
            selection=selection_token(mc.descriptor()), native_prompt=raw, messages=mc.messages(raw),
            deadline_ms=int(time.time()*1000)+20000, profile=mc.PROFILE, model=mc.MODEL,
            model_digest=mc.MODEL_DIGEST, transform=mc.TRANSFORM, limits=dict(mc.LIMITS)))
        def authorize(value):
            return owner.invoke(self.material['omega-agent']['fusion-model-token'].decode(),
                dict(interface_ref=dict(id=mc.INTERFACE, version=mc.VERSION), operation='authorize', intent=value))
        self.assertEqual(authorize(accepted)['value'], {'authorized': True})
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
            authorize(dict(accepted, session=b_session))
        self.assertEqual(ModelService.inspect(path), [])  # No acceptance, reservation or generation.
        cfg = json.loads(path.read_text())
        cfg['model_completion']['disclosure']['session_principals'][b_session] = 'A'
        path.write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError, 'CONFLICT'): authorize(accepted)

    def test_two_principals_cannot_omit_session_ownership_but_one_principal_profile_survives(self):
        raw = 'Synthetic input'
        policy = dict(profile='synthetic-recorded-prompt/1', scope=self.preview['scope'],
                      principals=['A'], max_prompt_bytes=mc.MAX_PROMPT)
        accepted = dict(native_prompt=raw, scope=self.preview['scope'], principal='A',
                        session=self.agents['omega-agent']['sessions'][0])
        disclosure(accepted, policy)
        policy['principals'].append('B')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): disclosure(accepted, policy)

    def test_duplicate_cross_agent_session_selection_is_rejected_before_owners_start(self):
        self.preview['agents']['omega-agent-b']['sessions'] = self.preview['agents']['omega-agent']['sessions'][:]
        with self.assertRaises(ContractError): self.role('fusion-model')
        self.assertFalse((self.root/'fusion-model/state/model.sqlite').exists())

    def test_supervisor_serializes_children_and_does_not_retry_failed_child(self):
        _, _, state, run = self.role('omega-agent')
        sid = self.agents['omega-agent']['sessions'][0]
        host = NativeSupervisor(run/'owner.json', state, run)
        child = Mock(pid=4242)
        child.poll.return_value = None
        with patch('integration.single_node.preview_host.subprocess.Popen', return_value=child) as launch:
            host.wake(sid); host.wake(sid)
            self.assertEqual(host.pending, [sid])
            host.tick(); host.tick()
            self.assertEqual(launch.call_count, 1)
            args, options = launch.call_args
            self.assertEqual(args[0][1:3], ['-m', 'integration.neoclaw.native_loop'])
            self.assertTrue(options['start_new_session'])
            self.assertEqual(Path(args[0][-1]), run/'sessions'/sid/'application.json')
            child.poll.return_value = 9
            host.tick(); host.tick()
            self.assertEqual(launch.call_count, 1)
            status = json.loads((state/'worker-status.json').read_text())
            self.assertEqual((status['exit_code'], status['automatic_retry']), (9, False))
            self.assertIsNone(host.child)
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): host.wake(str(uuid.uuid4()))

    def test_restart_reconstructs_wakeup_from_durable_acceptance_without_retiming(self):
        self.call_session('create')
        receipt = self.call_session('submit', identity='stable-input', text='Synthetic note', assignment='notes')
        _, _, state, run = self.role('omega-agent')
        host = NativeSupervisor(run/'owner.json', state, run)
        with patch('integration.single_node.preview_host.subprocess.Popen') as launch:
            host.recover(); host.recover()
            self.assertEqual(host.pending, self.agents['omega-agent']['sessions'])
            launch.assert_not_called()
        replay = self.call_session('submit', identity='stable-input', text='Synthetic note', assignment='notes')
        self.assertEqual(replay, receipt)
        observed = self.call_session('next', actor='worker')
        self.assertEqual(observed['deadline'], receipt['deadline'])
        self.assertEqual(self.call_session('observe', content=False)['inputs'][0]['state'], 'accepted')

    def test_supervisor_shutdown_uses_process_group_and_rejects_new_wakes(self):
        _, _, state, run = self.role('omega-agent')
        sid = self.agents['omega-agent']['sessions'][0]
        host = NativeSupervisor(run/'owner.json', state, run)
        host.child = Mock(pid=4242)
        host.child.poll.return_value = None
        host.child.wait.side_effect = [subprocess.TimeoutExpired('fixture-child', 25), 137]
        host.log = Mock()
        log = host.log
        with patch('integration.single_node.preview_host.os.killpg') as kill:
            host.stop()
        self.assertEqual([args.args for args in kill.call_args_list], [(4242, signal.SIGTERM), (4242, signal.SIGKILL)])
        self.assertEqual([args.kwargs for args in host.child.wait.call_args_list], [{'timeout': 25}, {'timeout': 2}])
        log.close.assert_called_once()
        self.assertIsNone(host.log)
        with self.assertRaisesRegex(ContractError, 'NOT_AVAILABLE'): host.wake(sid)

    def test_failed_wakeup_returns_the_durable_acceptance_receipt(self):
        self.call_session('create')
        _, cfg, state, run = self.role('omega-agent')
        sid = self.agents['omega-agent']['sessions'][0]
        host = NativeSupervisor(run/'owner.json', state, run)
        host.stop()
        request = dict(id='late-submit', profile=PROFILE, operation='submit', body=dict(
            session=sid, identity='shutdown-race', text='Synthetic accepted input', assignment='notes'))
        reply = SessionPorts(run/'owner.json', host.wake).invoke(cfg['principals']['operator']['credential'], request)
        self.assertEqual(reply['value']['worker'], 'NOT_AVAILABLE')
        self.assertTrue(reply['value']['acceptance_retained'])
        self.assertEqual(self.call_session('observe', content=False)['inputs'][0]['id'], 'shutdown-race')


if __name__ == '__main__': unittest.main()
