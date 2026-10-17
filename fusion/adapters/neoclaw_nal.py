"""Pure S01 provider: run the pinned original MeTTa truth function, never Python math."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from ..contracts import ContractError, digest, require
from .. import neoclaw_contracts as c


class NativeTruthDeduction:
    def __init__(self, runtime_file):
        self.runtime_file = Path(runtime_file).resolve()
        self.runtime = json.loads(self.runtime_file.read_text())
        build = json.loads((self.runtime_file.parent / 'build.json').read_text())
        binary = Path(self.runtime['swipl']).resolve()
        require(build['source_pins'] == c.PINS, 'UNSUPPORTED_PROFILE')
        require(digest(self.runtime_file.read_bytes()) == build['runtime_sha256'], 'UNSUPPORTED_PROFILE')
        require(digest(binary.read_bytes()) == build['binary_sha256'], 'UNSUPPORTED_PROFILE')
        require(digest(Path(self.runtime['python']).resolve().read_bytes()) == build['python_binary_sha256'], 'UNSUPPORTED_PROFILE')
        for file, sha in build['native_libraries'].items():
            require(digest((self.runtime_file.parent / file).read_bytes()) == sha, 'UNSUPPORTED_PROFILE')
        for name in ('mettaclaw', 'PeTTa'):
            path = Path(self.runtime['mettaclaw' if name == 'mettaclaw' else 'petta'])
            for file, sha in c.PINS['sources'][name]['files'].items():
                require(digest((path / file).read_bytes()) == sha, 'UNSUPPORTED_PROFILE')
        self.env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR')}
        self.env.update(self.runtime['environment'])

    def applyTruth(self, premises, deadline_ms):
        value = c.premises(premises)
        remaining = deadline_ms / 1000 - time.time()
        require(remaining > 0, 'DEADLINE_EXCEEDED')
        with tempfile.TemporaryDirectory(prefix='neoclaw-kernel-') as directory:
            path = Path(directory) / 'deduction.metta'
            source = Path(self.runtime['mettaclaw']) / 'lib_nal.metta'
            path.write_text('!(import! &self ' + json.dumps(str(source)) + ')\n!'
                            + c.expression(value) + '\n')
            try:
                run = subprocess.run([self.runtime['swipl'], '-q', '-s',
                    str(Path(self.runtime['petta']) / 'src/main.pl'), '--', str(path), '--silent'],
                    cwd=directory, env=self.env, capture_output=True, text=True, timeout=min(5, remaining))
            except subprocess.TimeoutExpired:
                raise ContractError('DEADLINE_EXCEEDED' if time.time()*1000 >= deadline_ms else 'NOT_AVAILABLE') from None
            except OSError:
                raise ContractError('NOT_AVAILABLE') from None
        require(run.returncode == 0 and len(run.stdout) <= 8192, 'NOT_AVAILABLE')
        lines = run.stdout.strip().splitlines()
        require(len(lines) == 2 and lines[0] == 'true', 'NOT_AVAILABLE')
        representation = lines[1]
        truth = c.native_truth(representation)
        require(time.time()*1000 < deadline_ms, 'DEADLINE_EXCEEDED')
        return dict(representation=representation, truth=truth)
