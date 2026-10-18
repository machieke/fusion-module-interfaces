"""Disposable generated S01 fixtures; real runtime/network/DeTTa are explicit."""
import concurrent.futures
import json
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time

from fusion import neoclaw_contracts as c
from fusion.contracts import canonical, ContractError
from fusion.neoclaw import NalService
from fusion.neoclaw_client import Caller
from fusion.neoclaw_transport import binding
from fusion.registry import descriptor_wire

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get('S01_RUNTIME', ROOT/'artifacts/s01/native-02/runtime.json'))
DETTA = Path(os.environ.get('S01_DETTA', ROOT/'artifacts/detta-build/target/debug/fusion-detta-adapter'))
COMMAND = 'metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))'
PREMISES = c.parse_expression(COMMAND[len('metta '):])
GOLDEN = '(stv 0.5599999999999999 0.4032)'


class FixtureKernel:
    """Not mathematical evidence; response/failure and journal unit tests only."""
    def applyTruth(self, premises, deadline_ms):
        return dict(representation=GOLDEN, truth=c.native_truth(GOLDEN))


class Harness:
    def __init__(self, real=False, capacity=8):
        self.temp = tempfile.TemporaryDirectory(prefix='fusion-s01-')
        self.root = Path(self.temp.name)
        self.server_root, self.caller_root = self.root/'provider', self.root/'caller'
        self.server_root.mkdir(mode=0o700)
        self.caller_root.mkdir(mode=0o700)
        self.config_path, self.client_path = self.server_root/'config.json', self.caller_root/'config.json'
        methods = ['execution.submit', 'execution.status', 'execution.result', 'atom.storage.get',
                   'atom.storage.create', 'agent.messaging.poll', 'agent.messaging.ack']
        self.config = dict(profile=c.PROFILE, sharing='generated-shareable', capacity=capacity,
            database=str(self.server_root/'execution.db'), atoms_database=str(self.server_root/'atoms.db'),
            messages_database=str(self.server_root/'mailbox.db'), da_root=str(self.server_root/'da'),
            atom_records=str(self.server_root/'records'), atom_provider='detta' if real else 'fixture-files',
            detta_binary=str(DETTA), runtime=str(RUNTIME), principals={},
            routes={f'reply-{p}': dict(scope=c.SCOPE, owner=p) for p in ('A', 'B')},
            test_failpoints=True, failpoint_marker=str(self.server_root/'failpoint.json'))
        for name in ('A', 'B', 'outsider', 'worker'):
            self.config['principals'][name] = dict(credential=secrets.token_hex(24), scopes={
                'elsewhere' if name == 'outsider' else c.SCOPE: methods if name != 'worker' else ['atom.storage.get', 'atom.storage.create']})
        self.save()
        self.server = None
        self.server_log = None
        self.port = None
        self.real = real
        self.client = self.client_config()
        self.save_client()

    def save(self):
        # Atomic policy replacement: readers never see a partial JSON document.
        pending = self.config_path.with_suffix('.new')
        pending.write_bytes(canonical(self.config)); pending.chmod(0o600); pending.replace(self.config_path)

    def client_config(self, key='command-1', placement='local', principal='A'):
        value = dict(database=str(self.caller_root/'caller.db'), scope=c.SCOPE, request_id=key,
            principal=principal,
            sharing='generated-shareable', reply_route='reply-'+principal, deadline_ms=int(time.time()*1000)+30000,
            max_calls=64, max_attempts=3, fallback=False, placement=placement,
            credential=self.config['principals'][principal]['credential'],
            catalogue=[descriptor_wire(x) for x in c.catalogue(self.config['atom_provider'])],
            test_failpoints=True, failpoint_marker=str(self.caller_root/'failpoint.json'))
        if placement == 'local':value['provider_config'] = str(self.config_path)
        else:value['endpoint'] = dict(host='127.0.0.1', port=self.port, ca_file=str(self.caller_root/'ca.pem'))
        return value

    def save_client(self):
        self.client_path.write_bytes(canonical(self.client)); self.client_path.chmod(0o600)

    def caller(self, transport=None):
        return Caller(self.client_path, transport=transport)

    def submit(self, premises=PREMISES):
        caller = self.caller()
        try:
            request = caller.prepare(premises)
            return request, caller._call(request)
        finally:caller.close()

    def service(self, hook=lambda _: None):
        return NalService(self.config_path, hook, None if self.real else FixtureKernel())

    def drive(self):
        service = self.service()
        try:return service.work(), service.flush()
        finally:service.close()

    def start_server(self):
        if not (self.server_root/'server.pem').exists():
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', str(self.server_root/'server.key'), '-out', str(self.server_root/'server.pem'),
                '-days', '1', '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'],
                check=True, capture_output=True)
            (self.server_root/'server.key').chmod(0o600)
            (self.caller_root/'ca.pem').write_bytes((self.server_root/'server.pem').read_bytes())
        self.config.update(tls_certificate=str(self.server_root/'server.pem'), tls_key=str(self.server_root/'server.key'))
        self.save()
        ready = self.server_root/'ready.json'; ready.unlink(missing_ok=True)
        self.server_log = open(self.server_root/'server.log', 'a')
        self.server = subprocess.Popen([sys.executable, '-m', 'integration.neoclaw.host', 'serve', str(self.config_path),
            '--port', str(self.port or 0), '--ready', str(ready)], cwd=ROOT, stdout=self.server_log, stderr=self.server_log)
        self.wait_file(ready, self.server, seconds=50 if self.config.get('embedding') else 12)
        self.port = json.loads(ready.read_text())['port']

    def stop_server(self, kill=False):
        if self.server is not None:
            if self.server.poll() is None:
                self.server.kill() if kill else self.server.terminate()
            self.server.wait(timeout=5)
            self.server = None
        if self.server_log:
            self.server_log.close(); self.server_log = None

    def network(self, key='command-1'):
        self.start_server()
        self.client = self.client_config(key, 'network'); self.save_client()

    def start_native(self, command=COMMAND, original=False):
        args = [sys.executable, '-m', 'integration.neoclaw.native_command', str(RUNTIME), command]
        if not original:
            args += ['--caller-config', str(self.client_path)]
        if self.client['placement'] == 'network' and not original:
            args += ['--deny-path', str(self.server_root), '--deny-path', str(Path.home()/'work/takopi/mettaclaw')]
        return subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def finish_native(self, process, drive=True):
        try:
            until = time.monotonic()+35
            while process.poll() is None and time.monotonic() < until:
                if drive:
                    try:self.drive()
                    except ContractError as exc:
                        if exc.code != 'OVERLOADED':raise
                time.sleep(.03)
            stdout, stderr = process.communicate(timeout=3)
            assert process.returncode == 0, (stdout, stderr)
            return json.loads(stdout)
        finally:
            if process.poll() is None:process.kill();process.wait()

    def native(self, command=COMMAND, original=False):
        return self.finish_native(self.start_native(command, original), drive=not original)

    def wait_file(self, path, process=None, seconds=12):
        until = time.monotonic()+seconds
        while not Path(path).exists() and time.monotonic() < until:
            if process is not None and process.poll() is not None:break
            time.sleep(.02)
        assert Path(path).exists(), ('missing failpoint/ready', path, None if process is None else process.poll())

    def worker(self, mode='work', stage=None):
        args = [sys.executable, '-m', 'integration.neoclaw.host', mode, str(self.config_path)]
        if stage:args += ['--pause-at', stage]
        return subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def kill_worker(self, stage, mode='work'):
        marker = Path(self.config['failpoint_marker']); marker.unlink(missing_ok=True)
        process = self.worker(mode, stage)
        try:
            self.wait_file(marker, process)
            process.kill();process.wait(timeout=5)
            assert process.returncode == -signal.SIGKILL
            return json.loads(marker.read_text())
        finally:
            if process.poll() is None:process.kill();process.wait()
            process.stdout.close();process.stderr.close()

    def counts(self):
        result = {}
        if Path(self.config['database']).exists():
            with sqlite3.connect(self.config['database']) as db:
                for name in ('jobs', 'outbox'):
                    result[name] = db.execute('SELECT count(*) FROM '+name).fetchone()[0]
                result['attempts'] = db.execute('SELECT coalesce(sum(attempts),0) FROM s01_work').fetchone()[0]
        if Path(self.config['messages_database']).exists():
            with sqlite3.connect(self.config['messages_database']) as db:
                result['messages'] = db.execute('SELECT count(*) FROM messages').fetchone()[0]
                result['unacked'] = db.execute('SELECT count(*) FROM messages WHERE acknowledged=0').fetchone()[0]
        if Path(self.client['database']).exists():
            with sqlite3.connect(self.client['database']) as db:
                # Schema creation and intent persistence are distinct native
                # startup moments; an observer may see the empty SQLite file.
                if not db.execute("SELECT 1 FROM sqlite_master WHERE name='caller_requests'").fetchone():
                    return result
                result['caller_requests'] = db.execute('SELECT count(*) FROM caller_requests').fetchone()[0]
                result['caller_completed'] = db.execute('SELECT count(*) FROM caller_requests WHERE receipt IS NOT NULL').fetchone()[0]
                result['caller_acked'] = db.execute('SELECT count(*) FROM caller_requests WHERE acknowledged=1').fetchone()[0]
                result['caller_calls'] = db.execute('SELECT coalesce(sum(calls),0) FROM caller_requests').fetchone()[0]
        return result

    def close(self):
        self.stop_server()
        self.temp.cleanup()
