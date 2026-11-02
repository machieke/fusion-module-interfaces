"""Single-agent selection, actual configuration/catalogue and offline Helm.

Image metadata, embedding runtime-lock bytes and TLS bytes are explicit fixtures. Secret-role composition,
configuration, catalogue admission and Helm rendering are real. No cluster,
native loop, owner journal, E5/Chroma/DeTTa, model or network service is run.
"""
import copy
import contextlib
import io
import json
from pathlib import Path
import secrets
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

import yaml

from examples import preview_single_agent_values as single
from fusion.contracts import ContractError, canonical
from fusion.preview_application import configuration
from fusion.preview_recorded_model import RecordedProposals
from fusion.preview_tools import SessionAuthority
from integration.single_node.preview_configure import COMPOSITION, configure
from integration.single_node.preview_secrets import material, selection
from integration.single_node.preview_values import generate
from tests.test_phase2_operator_values import image_manifest_fixture


ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'synthetic-single-agent-example'


class SingleAgentValues(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-single-agent-values-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = image_manifest_fixture()

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def values(self, mode='minimal'):
        value = single.generate(self.manifest, SCOPE, mode=mode)
        path = self.root/(mode+'-values.yaml')
        path.write_text(yaml.safe_dump(value, sort_keys=False))
        return value, path

    def test_all_modes_keep_existing_profiles_limits_pins_and_only_a_occurrences(self):
        for mode in ('minimal', 'memory', 'combined'):
            with self.subTest(mode=mode):
                values, path = self.values(mode)
                p = values['preview']
                self.assertEqual(p['profile'], COMPOSITION)
                self.assertEqual(p['model_boundary'], 'RECORDED_FIXTURE')
                self.assertEqual(set(p['agents']), {'omega-agent'})
                agent = p['agents']['omega-agent']
                self.assertEqual(agent['principal'], 'A')
                self.assertEqual(agent['private_scope'], SCOPE+'-private-a')
                self.assertNotEqual(agent['private_scope'], p['scope'])
                self.assertEqual(len(agent['sessions']), 2)
                self.assertEqual(len(p['responses']), 48)
                self.assertEqual(set(p['responses']), {sid+'/'+str(n) for sid in agent['sessions'] for n in range(1,25)})
                self.assertTrue(all(x == {'proposal':'input-command'} for x in p['responses'].values()))
                self.assertFalse(values['components']['omega-agent-b']['enabled'])
                self.assertEqual(p['tasks'], {'enabled':False})
                self.assertEqual(p['inspection'], {'enabled':False})
                self.assertNotIn('delegate', agent['tools'])
                self.assertNotIn('inspect-atom', agent['tools'])
                self.assertNotIn('chain', p)
                self.assertNotIn('futureLive', values)
                self.assertEqual(p['limits'], dict(inputs=24, pending=4, timeout_ms=120000))
                self.assertEqual('remember' in agent['tools'], mode != 'minimal')
                self.assertEqual('support' in agent['tools'], mode == 'combined')
                self.assertIn('metta', agent['tools'])
                self.assertEqual(values['components']['omega-agent']['image']['digest'], self.manifest['images'][1]['manifest_digest'])
                _, roles = selection(path)
                self.assertNotIn('omega-agent-b', roles)
                self.assertIn('fusion-messaging', roles)

    def configure_all(self, mode):
        values, path = self.values(mode)
        preview, roles = selection(path)
        root = self.root/mode
        clients = {role:secrets.token_hex(32) for role in roles if role != 'omega-agent'}
        workers = {role:secrets.token_hex(32) for role in clients}
        credentials = material(preview, roles, clients)
        configured = {}
        for role in roles:
            directory = root/role/'secrets'
            directory.mkdir(parents=True)
            files = {name:b'EXPLICIT TLS BYTES FIXTURE' for name in ('ca.crt', 'tls.crt', 'tls.key')}
            if role == 'omega-agent':
                files.update({name+'-token':value.encode() for name,value in clients.items()})
            else:
                files.update({'caller-token':clients[role].encode(), 'worker-token':workers[role].encode()})
                if role == 'fusion-execution':
                    files.update({name+'-token':workers[name].encode() for name in ('fusion-storage','fusion-messaging')})
            files.update(credentials[role])
            for name, value in files.items():
                (directory/name).write_bytes(value)
            settings = dict(role=role, service_composition=COMPOSITION,
                state=str(root/role/'state'), run=str(root/role/'run'), secret_directory=str(directory),
                https_port=8443, capacity=8, revision='single-agent-fixture', native_enabled=role=='omega-agent',
                worker_enabled=False, enable_test_faults=False, test={}, preview=copy.deepcopy(preview),
                peers={name:name+'.omega-ref-single-fixture.svc.cluster.local' for name in roles})
            original_read = Path.read_bytes

            def fixture_runtime_read(path):
                if str(path) == '/opt/memory-runtime.json':
                    return b'{"boundary":"EXPLICIT_CONFIGURATION_RUNTIME_LOCK_FIXTURE"}'
                return original_read(path)

            with patch.object(Path, 'read_bytes', fixture_runtime_read):
                configured[role] = configure(settings)
        return values, configured

    def test_actual_configuration_and_catalogue_admit_a_without_b_task_or_inspection_dependencies(self):
        for mode in ('minimal','memory','combined'):
            with self.subTest(mode=mode):
                values, configured = self.configure_all(mode)
                _, owner, state, run = configured['omega-agent']
                self.assertEqual(owner['native_sessions']['principal'], 'A')
                for sid in values['preview']['agents']['omega-agent']['sessions']:
                    app = json.loads((run/'sessions'/sid/'application.json').read_text())
                    catalogue = configuration(app['preview'])
                    self.assertEqual(owner['native_sessions']['session_templates'][sid]['catalogue'], catalogue.identity)
                    authority = json.loads(Path(app['preview']['authority_file']).read_text())
                    authority['tools'] = frozenset(authority['tools'])
                    admitted = catalogue.admit([['pin','task','Synthetic solo note']], SessionAuthority(**authority),
                                               'A', time.time_ns()//1000000)
                    self.assertEqual(admitted[0]['arguments'], {'item':'task','note':'Synthetic solo note'})
                    for excluded in ('delegate','inspect-atom'):
                        self.assertNotIn(excluded, catalogue.tools)
                    self.assertNotIn('task_config', app)
                    self.assertNotIn('inspect_config', app)
                    model = json.loads(Path(app['model_config']).read_text())
                    self.assertEqual(model['disclosure']['principals'], ['A'])
                    self.assertTrue(all(who=='A' for who in model['disclosure']['session_principals'].values()))
                    self.assertNotIn('B', model['disclosure']['principals'])
                self.assertEqual(json.loads((run/'private-atoms.json').read_text())['scope'], SCOPE+'-private-a')
                storage = json.loads((configured['fusion-storage'][3]/'cognitive-owner.json').read_text())
                self.assertEqual(storage['allowed_scopes'], [SCOPE, SCOPE+'-private-a'])
                self.assertNotIn('B', storage['actors'])
                for _, cfg, _, _ in configured.values():
                    self.assertNotIn('task_ingress', cfg)
                    self.assertNotIn('tasks', cfg)
                    self.assertNotIn('B', cfg.get('principals',{}))
                model = configured['fusion-model'][1]['model_completion']
                self.assertEqual(set(model['sessions']), set(owner['native_sessions']['session_templates']))
                self.assertEqual(model['runtime_lock']['generative_runtime'], 'FORBIDDEN')
                RecordedProposals(configured['fusion-model'][3]/'owner.json')
                self.assertFalse(list((self.root/mode).rglob('*.sqlite')))
                if mode != 'minimal':
                    self.assertEqual(configured['fusion-storage'][1]['memory_append']['writers'], ['A'])
                    self.assertEqual(configured['fusion-search'][1]['memory_read']['readers'], ['A','indexer'])
                if mode == 'combined':
                    for role in ('fusion-episodes','fusion-beliefs','fusion-attention'):
                        cognitive = json.loads((configured[role][3]/'cognitive-owner.json').read_text())
                        self.assertNotIn('B', cognitive['actors'])

    def test_helm_renders_only_a_with_existing_owner_services_and_single_writer_retention(self):
        for mode in ('minimal','memory','combined'):
            with self.subTest(mode=mode):
                values, path = self.values(mode)
                rendered = subprocess.check_output(['helm','template','omega',
                    str(ROOT/'deploy/helm/omega-fusion'),'-n','omega-ref-single-fixture','-f',str(path)], text=True)
                documents = [doc for doc in yaml.safe_load_all(rendered) if doc]
                owners = {doc['metadata']['name']:doc for doc in documents if doc['kind']=='StatefulSet'}
                self.assertIn('omega-agent', owners)
                self.assertNotIn('omega-agent-b', owners)
                self.assertNotIn('f1r3node', owners)
                self.assertNotIn('fusion-commitment', owners)
                self.assertFalse(any(doc['metadata']['name']=='omega-agent-b' for doc in documents))
                for owner in owners.values():
                    self.assertEqual(owner['spec']['replicas'], 1)
                    self.assertEqual(owner['spec']['persistentVolumeClaimRetentionPolicy'],
                                     {'whenDeleted':'Retain','whenScaled':'Retain'})
                self.assertNotIn('hostPath:', rendered)
                self.assertNotIn('omega-agent-b-tls-auth', rendered)
                maps = [json.loads(doc['data']['component.json']) for doc in documents
                        if doc['kind']=='ConfigMap' and 'component.json' in doc.get('data',{})]
                self.assertTrue(maps)
                self.assertTrue(all(set(cfg['preview']['agents'])=={'omega-agent'} for cfg in maps))
                self.assertEqual('fusion-search' in owners, mode != 'minimal')
                self.assertEqual('fusion-attention' in owners, mode == 'combined')

    def test_example_does_not_change_manifest_or_existing_two_agent_generator(self):
        before = copy.deepcopy(self.manifest)
        single.generate(self.manifest, SCOPE, mode='combined')
        self.assertEqual(self.manifest, before)
        ordinary = generate(self.manifest, SCOPE, mode='combined')
        self.assertEqual(set(ordinary['preview']['agents']), {'omega-agent','omega-agent-b'})
        self.assertTrue(ordinary['preview']['tasks']['enabled'])
        self.assertTrue(ordinary['preview']['inspection']['enabled'])
        self.assertIn('delegate', ordinary['preview']['agents']['omega-agent']['tools'])
        self.assertIn('inspect-atom', ordinary['preview']['agents']['omega-agent']['tools'])

    def test_cli_writes_fresh_values_and_refuses_existing_or_unknown_chain_option(self):
        manifest = self.root/'images.json'
        manifest.write_bytes(canonical(self.manifest))
        output = self.root/'new.yaml'
        args = ['example','--images',str(manifest),'--scope',SCOPE,'--mode','minimal','--output',str(output)]
        with patch('sys.argv', args):
            single.main()
        before = output.read_bytes()
        self.assertEqual(set(yaml.safe_load(before)['preview']['agents']), {'omega-agent'})
        with patch('sys.argv', args):
            self.error('CONFLICT', single.main)
        self.assertEqual(output.read_bytes(), before)
        with patch('sys.argv', args+['--chain']), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                single.main()
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual(output.read_bytes(), before)

    def test_bad_source_scope_or_mode_refuses_without_output(self):
        bad = copy.deepcopy(self.manifest)
        bad['source_export_verification'] = 'FAILED'
        self.error('CONFLICT', single.generate, bad, SCOPE)
        self.error('UNAUTHORIZED', single.generate, self.manifest, 'private-existing-user-memory')
        self.error('INVALID_ARGUMENT', single.generate, self.manifest, SCOPE, mode='live')
        manifest = self.root/'bad-images.json'
        manifest.write_bytes(canonical(bad))
        output = self.root/'never-created.yaml'
        with patch('sys.argv', ['example','--images',str(manifest),'--scope',SCOPE,'--output',str(output)]):
            self.error('CONFLICT', single.main)
        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
