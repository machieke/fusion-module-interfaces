"""Supervised resident native encoder. Readiness is separate from admitted work."""
import atexit
from dataclasses import asdict
import fcntl
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time

from .. import embedding_contracts as c
from ..contracts import ContractError, canonical, require
from ..neoclaw_transport import json_loads

ROOT = Path(__file__).resolve().parents[2]


class NativeE5:
    def __init__(self, config_path):
        config_path = Path(config_path).resolve()
        cfg = json.loads(config_path.read_text())['embedding']
        runtime = json.loads(Path(cfg['runtime']).read_text())
        self.lock = open(cfg['database']+'.resident.lock', 'a')
        try: fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.lock.close(); raise ContractError('OVERLOADED') from None
        env = dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1',
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
        self.diagnostics = open(Path(cfg['database']).with_suffix('.diagnostics.log'), 'ab')
        os.chmod(self.diagnostics.name, 0o600)
        self.process = subprocess.Popen([runtime['python'], '-m', 'integration.neoclaw.embedding_worker',
            str(config_path), str(os.getpid())], cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.diagnostics, start_new_session=True, bufsize=0)
        self.selector = selectors.DefaultSelector(); self.selector.register(self.process.stdout, selectors.EVENT_READ)
        try:
            self.readiness = self.read(45.)
            require(self.readiness['ready'] is True and self.readiness['model'] == c.v.EMBEDDING, 'NOT_AVAILABLE')
        except BaseException:
            self.close(); raise
        atexit.register(self.close)

    def read(self, seconds):
        end, data = time.monotonic()+seconds, b''
        while b'\n' not in data:
            require(time.monotonic() < end, 'DEADLINE_EXCEEDED')
            require(self.selector.select(max(0, end-time.monotonic())), 'DEADLINE_EXCEEDED')
            chunk = os.read(self.process.stdout.fileno(), 8192)
            require(chunk, 'NOT_AVAILABLE'); data += chunk
            require(len(data) <= c.MAX_WIRE_BYTES, 'NOT_AVAILABLE')
        require(data.endswith(b'\n') and data.count(b'\n') == 1, 'NOT_AVAILABLE')
        return json_loads(data)

    def encode(self, request: c.EncodeInput):
        accepted = c.intent(asdict(request))
        remaining = min(5., (accepted['deadline_ms']-time.time()*1000)/1000)
        require(remaining > 0, 'DEADLINE_EXCEEDED')
        try:
            require(self.process.poll() is None, 'NOT_AVAILABLE')
            self.process.stdin.write(canonical(accepted)+b'\n'); self.process.stdin.flush()
            return c.result(self.read(remaining), accepted)
        except (BrokenPipeError, OSError):
            self.close(); raise ContractError('NOT_AVAILABLE') from None
        except BaseException:
            self.close(); raise

    def close(self):
        if self.process.poll() is None: os.killpg(self.process.pid, signal.SIGKILL)
        self.process.wait(timeout=5)
        self.process.stdin.close(); self.process.stdout.close(); self.selector.close(); self.lock.close(); self.diagnostics.close()
