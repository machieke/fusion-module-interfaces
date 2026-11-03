"""Actual installed historical/current endpoints; same closed interface 1.1.0.

The historical wheels are immutable inputs identified by the first SDK report.
This is package/additive-export compatibility, not a fabricated wire-version,
native consumer, DeTTa, numerical-kernel, migration or cluster qualification.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import venv

from fusion.registry import descriptor_wire, selection_token
from tests import test_phase2_sdk as base

ROOT = Path(__file__).resolve().parents[1]

CALL = '''import json,sys
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_read,selection_token
from fusion.ports import Mutation
from phase2_provider.caller import save_and_consume
cfg=json.loads(sys.argv[1])
client=AtomFeedClient(Endpoint(**cfg['endpoint']),cfg['credential'],cfg['principal'],
 cfg['scope'],descriptor_read(cfg['descriptor']),deadline_ms=cfg['deadline_ms'])
value=save_and_consume(client,cfg['scope'],cfg['occurrence'],b'approved stable compatibility payload')
print(json.dumps(dict(value=value,head=client.head(cfg['scope']),
 deadline_ms=client.deadline_ms,selection=selection_token(client.descriptor))))
'''


class InstalledWireCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='fusion-sdk-matrix-')
        cls.root = Path(cls.temporary.name)
        cls.environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
        cls.environment['PYTHONNOUSERSITE'] = '1'
        cls.historical = json.loads((ROOT / 'sdk/qualification.json').read_text())
        old = ROOT / 'sdk/compatibility/0.1.0'
        for name in ('client', 'provider'):
            row = cls.historical['wheel_build'][name]
            assert hashlib.sha256((old / row['file']).read_bytes()).hexdigest() == row['sha256']
        # Preserve this historical 0.1/0.2 test identity using published wheels.
        new = ROOT / 'sdk/compatibility/0.2.0'
        cls.pythons = {}
        for version, source in [('0.1.0', old), ('0.2.0', new)]:
            path = cls.root / ('venv-' + version)
            venv.create(path, with_pip=True)
            python = path / 'bin/python'
            subprocess.run([str(python), '-I', '-m', 'pip', 'install', '--no-index', '--no-deps',
                            *map(str, sorted(source.glob('*.whl')))], cwd=cls.root,
                           env=cls.environment, check=True, capture_output=True)
            cls.pythons[version] = python

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def fresh(self, suffix):
        root = self.root / (self._testMethodName + '-' + suffix)
        root.mkdir()
        base.prepare(root)
        return root

    def config(self, endpoint, occurrence='accepted-before-upgrade'):
        return dict(endpoint=endpoint.__dict__, credential='generated-sdk-credential',
                    principal='reader', scope='generated-sdk', occurrence=occurrence,
                    descriptor=descriptor_wire(base.server.descriptor()),
                    deadline_ms=time.time_ns() // 1_000_000 + 30000)

    def call(self, version, config):
        result = subprocess.run([str(self.pythons[version]), '-I', '-c', CALL, json.dumps(config)],
                                cwd=self.root, env=self.environment, check=True,
                                capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_four_actual_client_provider_package_combinations(self):
        for provider in self.pythons:
            root = self.fresh(provider)
            proc, endpoint = base.start_installed(self.pythons[provider], root, self.environment)
            try:
                for client in self.pythons:
                    with self.subTest(client_package=client, provider_package=provider, interface='1.1.0'):
                        config = self.config(endpoint, 'matrix-' + client + '-' + provider)
                        path = root / ('client-' + client + '.json')
                        path.write_text(json.dumps(config))
                        result = subprocess.run([str(self.pythons[client]), '-I', '-m',
                            'phase2_provider.conformance', '--client-config', str(path)],
                            cwd=root, env=self.environment, check=True, capture_output=True, text=True)
                        self.assertEqual(json.loads(result.stdout)['status'], 'PASS')
                        self.assertEqual(self.call(client, config)['value']['content'],
                                         'approved stable compatibility payload')
            finally:
                proc.terminate()
                proc.wait(timeout=5)

    def test_accepted_identity_and_descriptor_survive_compatible_package_restart(self):
        root = self.fresh('rollout')
        proc, endpoint = base.start_installed(self.pythons['0.1.0'], root, self.environment)
        config = self.config(endpoint)
        try:
            accepted = self.call('0.1.0', config)
        finally:
            proc.kill()
            proc.wait(timeout=5)
        proc, endpoint = base.start_installed(self.pythons['0.2.0'], root, self.environment)
        config['endpoint'] = endpoint.__dict__
        try:
            recovered = self.call('0.1.0', config)
            self.assertEqual(recovered, accepted)
            self.assertEqual(self.call('0.2.0', config), accepted)
            self.assertEqual(accepted['head']['sequence'], 1)
            self.assertEqual(accepted['selection'], selection_token(base.server.descriptor()))
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_refusals_separate_client_preflight_from_actual_wire_binding(self):
        # A stale/unsupported descriptor is never relaxed to execute a request.
        # Resolver checks are labelled preflight; wire tampering is independently
        # refused by both installed endpoints, before any owner mutation.
        code = '''import json,sys,uuid,http.client,ssl
from dataclasses import replace
from fusion.contracts import ContractError,canonical
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_read,selection_token,Requirement,resolve
cfg=json.loads(sys.argv[1]);d=descriptor_read(cfg['descriptor'])
cases=[('major',replace(d,version='2.0.0'),'UNSUPPORTED_VERSION'),
 ('profile',replace(d,profiles=frozenset({'incompatible-numerical-profile/1'})),'UNSUPPORTED_PROFILE'),
 ('privacy',replace(d,privacy='private-local-only'),'NOT_AVAILABLE'),
 ('guarantee',replace(d,guarantees=frozenset()),'NOT_AVAILABLE')]
def refuses(expected,fn):
 try: fn()
 except ContractError as exc: assert exc.code==expected,(expected,exc.code)
 else: raise AssertionError('unsupported contract accepted')
for name,changed,error in cases:
 refuses(error,lambda: AtomFeedClient(Endpoint(**cfg['endpoint']),cfg['credential'],cfg['principal'],
  cfg['scope'],changed,deadline_ms=cfg['deadline_ms']))
required=Requirement('atom.storage','1.0.0','1.2.0','immutable-commit-feed/1',
 frozenset({'head'}),frozenset({'scoped'}),privacy='generated-shareable',features=frozenset({'missing-required-feature'}))
refuses('UNSUPPORTED_PROFILE',lambda: resolve([d],required))
cases.append(('required-feature',replace(d,features=frozenset({'missing-required-feature'})),None))
for name,changed,error in cases:
 q=dict(id=str(uuid.uuid4()),composition='typed-atom-feed-https/1',scope=cfg['scope'],
  interface='atom.storage',selection=selection_token(changed),operation='head',args=[cfg['scope']])
 e=cfg['endpoint'];conn=http.client.HTTPSConnection(e['host'],e['port'],timeout=2,
  context=ssl.create_default_context(cafile=e['ca_file']))
 try:
  conn.request('POST',e['path'],canonical(q),{'Authorization':'Bearer '+cfg['credential']})
  reply=conn.getresponse();value=json.loads(reply.read())
  assert reply.status==400 and value['error']['code']=='UNSUPPORTED_PROFILE',(name,value)
 finally:conn.close()
print(json.dumps(dict(preflight_refusals=5,wire_binding_refusals=5)))
'''
        for provider in self.pythons:
            root = self.fresh(provider)
            proc, endpoint = base.start_installed(self.pythons[provider], root, self.environment)
            try:
                for client, python in self.pythons.items():
                    with self.subTest(client_package=client, provider_package=provider):
                        result = subprocess.run([str(python), '-I', '-c', code, json.dumps(self.config(endpoint))],
                            cwd=root, env=self.environment, check=True, capture_output=True, text=True)
                        self.assertEqual(json.loads(result.stdout),
                                         {'preflight_refusals': 5, 'wire_binding_refusals': 5})
            finally:
                proc.terminate()
                proc.wait(timeout=5)
