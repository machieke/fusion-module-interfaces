"""P03 extracted-install and same-host HTTPS fixture-provider qualification.

No native-consumer/DeTTa/cluster/live-model claim is made by this suite.
"""
from dataclasses import replace
from http.server import ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
import venv
import zipfile

from fusion import lookup_contracts as c
from fusion.contracts import ContractError, canonical, digest
from fusion.ports import Mutation
from fusion.preview_client import AtomFeedClient, Endpoint, retry_classification, strict_json
from fusion.registry import descriptor_wire
from examples.phase2_provider import server
from examples.phase2_provider.conformance import run_contract_cases
from examples.phase2_provider.caller import save_and_consume

ROOT = Path(__file__).resolve().parents[1]


class InstalledKit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='fusion-sdk-extracted-')
        cls.root = Path(cls.temporary.name)
        subprocess.run([sys.executable, str(ROOT / 'sdk/build.py'), '--output', str(cls.root / 'wheels')],
                       check=True, capture_output=True)
        venv.create(cls.root / 'venv', with_pip=True)
        cls.python = cls.root / 'venv/bin/python'
        cls.environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
        cls.environment['PYTHONNOUSERSITE'] = '1'
        subprocess.run([str(cls.python), '-m', 'pip', 'install', '--no-index', '--no-deps',
                        *map(str, sorted((cls.root / 'wheels').glob('*.whl')))],
                       cwd=cls.root, env=cls.environment, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_installed_imports_are_independent_and_sources_exact(self):
        code = '''import importlib.util,json,sys
from pathlib import Path
from importlib.metadata import distribution
from fusion.preview_client import AtomFeedClient
from fusion.adapters.fixture_feed import FileFeedFixture
for name in ('chromadb','torch','transformers','fusion.neoclaw_application','fusion.atom_feed','fusion.adapters.detta'):
    assert importlib.util.find_spec(name) is None, name
assert not any(x in sys.modules for x in ('chromadb','torch','transformers'))
import hashlib
for name in ('fusion-module-client','fusion-file-feed-example'):
    d=distribution(name)
    manifest=json.loads(d.read_text('source-manifest.json'))
    for target,row in manifest['sources'].items():
        assert hashlib.sha256(Path(d.locate_file(target)).read_bytes()).hexdigest()==row['sha256']
print(json.dumps({'imports':'PASS','source_manifest':'PASS'}))
'''
        result = subprocess.run([str(self.python), '-I', '-c', code], cwd=self.root,
                                env=self.environment, check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), {'imports': 'PASS', 'source_manifest': 'PASS'})
        manifest = json.loads((self.root / 'wheels/build-manifest.json').read_text())
        for wheel in ('client', 'provider'):
            for target, row in manifest[wheel]['sources'].items():
                self.assertEqual(digest((ROOT / row['source']).read_bytes()), row['sha256'])

    def test_wheel_build_is_reproducible_and_has_no_secret_inputs(self):
        destination = self.root / 'second'
        subprocess.run([sys.executable, str(ROOT / 'sdk/build.py'), '--output', str(destination)],
                       check=True, capture_output=True)
        for source in (self.root / 'wheels').glob('*.whl'):
            self.assertEqual(source.read_bytes(), (destination / source.name).read_bytes())
            with zipfile.ZipFile(source) as archive:
                self.assertFalse(any(x.endswith(('.pem', '.key', '.sqlite')) for x in archive.namelist()))

    def test_extracted_https_provider_consumer_and_process_kill_recovery(self):
        root = self.root / ('network-' + str(uuid.uuid4()))
        root.mkdir()
        prepare(root)
        proc, endpoint = start_installed(self.python, root, self.environment)
        deadline = int(time.time() * 1000) + 30000
        cfg = dict(endpoint=endpoint.__dict__, credential='generated-sdk-credential', principal='reader',
                   scope='generated-sdk', descriptor=descriptor_wire(server.descriptor()), deadline_ms=deadline)
        config = root / 'client.json'
        config.write_text(json.dumps(cfg))
        try:
            result = subprocess.run([str(self.python), '-I', '-m', 'phase2_provider.conformance',
                                     '--client-config', str(config)], cwd=root, env=self.environment,
                                    check=True, capture_output=True, text=True)
            report = json.loads(result.stdout)
            self.assertEqual(report['status'], 'PASS')
            client = AtomFeedClient(endpoint, cfg['credential'], cfg['principal'], cfg['scope'],
                                    server.descriptor(), deadline_ms=deadline)
            result = save_and_consume(client, cfg['scope'], 'persist-before-kill', b'synthetic durable result')
            proc.kill()
            proc.wait(timeout=5)
            proc, endpoint = start_installed(self.python, root, self.environment)
            client = AtomFeedClient(endpoint, cfg['credential'], cfg['principal'], cfg['scope'],
                                    server.descriptor(), deadline_ms=deadline)
            self.assertEqual(save_and_consume(client, cfg['scope'], 'persist-before-kill',
                                             b'synthetic durable result'), result)
            self.assertEqual(client.get(report['ref']).bytes,
                             b'approved synthetic independent-provider conformance')
        finally:
            proc.terminate()
            proc.wait(timeout=5)


def prepare(root):
    subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                    '-keyout', str(root / 'key.pem'), '-out', str(root / 'cert.pem'),
                    '-days', '1', '-subj', '/CN=127.0.0.1',
                    '-addext', 'subjectAltName=IP:127.0.0.1'], check=True, capture_output=True)
    config = {'composition': 'typed-atom-feed-https/1', 'privacy': 'generated-shareable',
              'synthetic_scopes': ['generated-sdk'], 'root': str(root / 'state'),
              'tls_certificate': str(root / 'cert.pem'), 'tls_key': str(root / 'key.pem'),
              'principals': {'reader': {'credential': 'generated-sdk-credential',
                  'scopes': {'generated-sdk': ['atom.storage.' + op for op in server.OPERATIONS]}}}}
    (root / 'config.json').write_text(json.dumps(config))
    return config


def start_installed(python, root, environment):
    ready = root / 'ready.json'
    ready.unlink(missing_ok=True)
    proc = subprocess.Popen([str(python), '-I', '-m', 'phase2_provider.server', '--config', str(root / 'config.json'),
                             '--port', '0', '--ready-file', str(ready)], cwd=root, env=environment,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.monotonic() + 5
    while not ready.exists() and proc.poll() is None and time.monotonic() < end:
        time.sleep(.02)
    if not ready.exists():
        proc.kill()
        proc.wait()
        raise AssertionError('Extracted provider did not become ready')
    value = json.loads(ready.read_text())
    return proc, Endpoint('127.0.0.1', value['port'], str(root / 'cert.pem'))


class HTTPSBoundaries(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='fusion-sdk-https-')
        self.root = Path(self.temporary.name)
        self.config = prepare(self.root)
        self.ports = server.Ports(self.root / 'config.json')
        self.reply_filter = lambda value: value
        original = server.handler(self.ports)
        owner = self
        class Handler(original):
            def reply(self, status, value):
                value = owner.reply_filter(value)
                if value is None:
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                super().reply(status, value)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(self.root / 'cert.pem'), str(self.root / 'key.pem'))
        self.server.socket = context.wrap_socket(self.server.socket, server_side=True)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval': .02}, daemon=True)
        self.thread.start()
        self.endpoint = Endpoint('127.0.0.1', self.server.server_port, str(self.root / 'cert.pem'))
        self.client = self.make_client()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.temporary.cleanup()

    def make_client(self, **changes):
        kwargs = dict(endpoint=self.endpoint, credential='generated-sdk-credential', principal='reader',
                      scope='generated-sdk', descriptor=server.descriptor(), deadline_ms=int(time.time() * 1000) + 10000)
        kwargs.update(changes)
        return AtomFeedClient(**kwargs)

    def assert_code(self, code, call):
        with self.assertRaises(ContractError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def test_shared_conformance_cases(self):
        self.assertEqual(run_contract_cases(self.client, 'generated-sdk')['status'], 'PASS')

    def test_identical_adapted_caller_under_local_and_https_composition(self):
        access = server.Access(self.root / 'config.json', 'generated-sdk-credential')
        local = server.FileFeedFixture(self.root / 'independent-local.json', access)
        for atoms in (local, self.client):
            result = save_and_consume(atoms, 'generated-sdk', 'identical-business-logic', b'approved caller input')
            self.assertEqual(result['content'], 'approved caller input')
            self.assertEqual(save_and_consume(atoms, 'generated-sdk', 'identical-business-logic',
                                             b'approved caller input'), result)

    def test_live_revocation_and_wrong_credentials(self):
        self.assert_code('UNAUTHORIZED', lambda: self.make_client(credential='wrong').head('generated-sdk'))
        self.client.head('generated-sdk')
        self.config['principals']['reader']['scopes'] = {}
        (self.root / 'config.json').write_text(json.dumps(self.config))
        self.assert_code('UNAUTHORIZED', lambda: self.client.head('generated-sdk'))

    def test_descriptor_profile_version_and_guarantee_refusals(self):
        self.assert_code('UNSUPPORTED_VERSION', lambda: self.make_client(descriptor=replace(server.descriptor(), version='2.0.0')))
        self.assert_code('UNSUPPORTED_PROFILE', lambda: self.make_client(descriptor=replace(server.descriptor(), profiles=frozenset({'wrong/1'}))))
        self.assert_code('NOT_AVAILABLE', lambda: self.make_client(descriptor=replace(server.descriptor(), guarantees=frozenset())))
        different = self.make_client(descriptor=replace(server.descriptor(), implementation_version='0.2.0'))
        self.assert_code('UNSUPPORTED_PROFILE', lambda: different.head('generated-sdk'))
        self.assert_code('UNSUPPORTED_PROFILE', lambda: self.make_client(composition='unknown/1').head('generated-sdk'))

    def test_reply_principal_request_selection_and_payload_binding(self):
        for field, replacement in [('principal', 'other'), ('id', str(uuid.uuid4())), ('selection', '0' * 64), ('request_digest', '0' * 64)]:
            self.reply_filter = lambda value, f=field, r=replacement: {**value, f: r}
            self.assert_code('NOT_AVAILABLE', lambda: self.client.head('generated-sdk'))
        self.reply_filter = lambda value: value
        ref = self.client.create(Mutation('generated-sdk', 'malformed-result'), 'application/synthetic', b'good')['ref']
        self.reply_filter = lambda value: {**value, 'value': {**value['value'], 'data': 'YmFk'}}
        self.assert_code('NOT_AVAILABLE', lambda: self.client.get(ref))

    def test_lost_write_response_is_unknown_and_same_identity_replays(self):
        command = Mutation('generated-sdk', 'uncertain-reply')
        self.reply_filter = lambda value: None
        self.assert_code('NOT_AVAILABLE', lambda: self.client.create(command, 'application/synthetic', b'captured'))
        self.assertEqual(retry_classification('create', 'NOT_AVAILABLE'), 'unknown-effect-observe-or-replay-same-mutation')
        self.reply_filter = lambda value: value
        self.assertEqual(self.client.head('generated-sdk')['sequence'], 1)
        result = self.client.create(command, 'application/synthetic', b'captured')
        self.assertEqual(self.client.head('generated-sdk')['sequence'], 1)
        self.assertEqual(self.client.get(result['ref']).bytes, b'captured')

    def test_original_deadline_and_no_implicit_retry(self):
        self.assert_code('DEADLINE_EXCEEDED', lambda: self.make_client(deadline_ms=1).head('generated-sdk'))
        self.assertEqual(self.client.head('generated-sdk')['sequence'], 0)
        for code in ('UNAUTHORIZED', 'CONFLICT', 'UNSUPPORTED_PROFILE', 'DEADLINE_EXCEEDED'):
            self.assertEqual(retry_classification('create', code), 'stop')

    def test_strict_input_and_bounded_batch(self):
        for raw in (b'{"a":1,"a":2}', b'{"x":NaN}', b'[' * 70 + b'0' + b']' * 70):
            self.assert_code('NOT_AVAILABLE', lambda raw=raw: strict_json(raw))
        self.assert_code('INVALID_ARGUMENT', lambda: self.client.getMany(tuple()))
        self.assert_code('INVALID_ARGUMENT', lambda: self.client.create(Mutation('generated-sdk', 'bad'), 'application/synthetic', b'x' * 4097))
        self.assert_code('UNSUPPORTED_OPERATION', lambda: self.client._invoke('__import__', []))
        self.assert_code('UNSUPPORTED_PROFILE', lambda: self.make_client(
            descriptor=replace(server.descriptor(), privacy='private-local-only'), privacy='private-local-only'))

    def test_untrusted_certificate_is_refused(self):
        other = self.root / 'other'
        other.mkdir()
        prepare(other)
        client = self.make_client(endpoint=replace(self.endpoint, ca_file=str(other / 'cert.pem')))
        self.assert_code('NOT_AVAILABLE', lambda: client.head('generated-sdk'))


if __name__ == '__main__':
    unittest.main()
