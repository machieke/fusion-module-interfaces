"""Pure bounded observation adapter; execution owns attempts and captured bytes."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from ..contracts import ContractError, canonical, digest, require
from .. import neoclaw_contracts as c
from .. import neoclaw_search_contracts as s
from ..neoclaw_transport import json_loads

ROOT = Path(__file__).resolve().parents[2]


class SearchFailure(ContractError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(s.FAILURES[reason])


class NativeWebSearch:
    def __init__(self, config):
        self.config = config
        require(config['boundary'] in ('live', 'recorded-response'), 'UNSUPPORTED_PROFILE')
        require(set(config) == {'runtime', 'boundary', 'audit'} |
                ({'recording'} if config['boundary'] == 'recorded-response' else set()), 'UNSUPPORTED_PROFILE')
        self.runtime = json.loads(Path(config['runtime']).read_text())
        runtime = self.runtime
        require(runtime['profile'] == s.SDK and runtime['packages'] ==
                {'ddgs': '9.16.0', 'primp': '2.0.1', 'lxml': '6.1.3', 'click': '8.5.0'}, 'UNSUPPORTED_PROFILE')
        require(runtime['lock_sha256'] == digest((ROOT/'integration/neoclaw/search-requirements.lock').read_bytes()), 'UNSUPPORTED_PROFILE')
        require(runtime['helper_sha256'] == c.PINS['sources']['mettaclaw']['files']['channels/websearch.py'], 'UNSUPPORTED_PROFILE')
        for path, expected in {**runtime['files'], runtime['helper']: runtime['helper_sha256'],
                               runtime['python']: runtime['python_sha256']}.items():
            require(digest(Path(path).read_bytes()) == expected, 'UNSUPPORTED_PROFILE')

    def observe(self, arguments, deadline_ms):
        arguments = s.arguments(arguments)
        remaining = min(10., (deadline_ms-time.time()*1000)/1000)
        require(remaining > 0, 'DEADLINE_EXCEEDED')
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'PYTHONPATH': str(ROOT), 'PYTHONDONTWRITEBYTECODE': '1'}
        process = subprocess.Popen([self.runtime['python'], '-m', 'integration.neoclaw.search_worker'],
            cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            start_new_session=True)
        try:
            raw, _ = process.communicate(canonical(dict(config=self.config, runtime=dict(helper=self.runtime['helper']),
                                                       arguments=arguments, parent=os.getpid())), timeout=remaining)
            if process.returncode != 0: raise SearchFailure('upstream-unavailable')
            if len(raw) > s.MAX_BYTES: raise SearchFailure('invalid-output')
            value = json_loads(raw)
            if set(value) == {'error'} and value['error'] in s.FAILURES: raise SearchFailure(value['error'])
            if set(value) != {'ok'}: raise SearchFailure('invalid-output')
            return value['ok']
        except subprocess.TimeoutExpired:
            raise SearchFailure('upstream-timeout') from None
        finally:
            # Only this owned process group; never terminate unrelated runtimes.
            if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
