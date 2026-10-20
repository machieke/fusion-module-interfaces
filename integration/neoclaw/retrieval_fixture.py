"""Explicit authored response backend for preparation ONLY; never a fallback.

The isolated actor can read its two authored commands and accepted prompt, not
the corpus, evaluator, retrieval state or application journals.
"""
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

from fusion.contracts import canonical, digest, require
from fusion.adapters.ollama_completion import convert
from .preparation_guard import verify


def lock_config(lock):
    raw = Path(lock['path']).read_bytes()
    require(digest(raw) == lock['sha256'], 'CONFLICT')
    cfg = json.loads(raw)
    require(cfg['boundary'] == 'AUTHORED_MODEL_RESPONSE_FIXTURE', 'UNSUPPORTED_PROFILE')
    verify(cfg['parent_namespace'])
    return cfg


class AuthoredBackend:
    port = 11434  # Historical Client binding only; no socket is opened.

    def __init__(self, lock):
        self.lock = lock
        self.cfg = lock_config(lock)

    def complete(self, accepted):
        cmd = ['bwrap', '--die-with-parent', '--unshare-net', '--ro-bind', '/', '/',
               '--bind', self.cfg['root'], self.cfg['root'], '--dev', '/dev', '--proc', '/proc']
        for path in self.cfg['denied_paths']:
            cmd += ['--tmpfs', path]
        # No inherited file descriptors other than serialized input/output.
        result = subprocess.run([*cmd, '--', self.cfg['python'], '-m', 'integration.neoclaw.retrieval_fixture', 'evaluate', self.lock['path']],
                                input=canonical(asdict(accepted)), capture_output=True, timeout=5)
        require(result.returncode == 0, 'NOT_AVAILABLE')
        return json.loads(result.stdout)


def install(lock):
    lock_config(lock)
    import fusion.adapters.ollama_completion as adapter
    adapter.OllamaCompletion = AuthoredBackend


def main():
    mode, path = sys.argv[1:3]; cfg = json.loads(Path(path).read_bytes())
    if mode == 'evaluate':
        verify(cfg['parent_namespace'])
        for path in cfg['denied_paths']:
            require(not Path(path).exists() or not any(Path(path).iterdir()), 'UNAUTHORIZED')
        accepted = json.loads(sys.stdin.buffer.read())
        require(accepted['slot'] in (1, 2), 'INVALID_ARGUMENT')
        text = cfg['responses'][accepted['slot'] - 1]
        with open(Path(cfg['root'])/'evaluations.jsonl', 'ab') as stream:
            stream.write(canonical(dict(boundary=cfg['boundary'], intent=accepted, response=text,
                                        denied_paths=cfg['denied_paths']))+b'\n')
            stream.flush(); os.fsync(stream.fileno())
        print(canonical(convert(dict(model=accepted['model'], done=True, done_reason='stop',
                                     message=dict(role='assistant', content=text)))).decode())
    else:
        require(mode == 'serve', 'INVALID_ARGUMENT')
        policy = cfg
        lock = policy['model_completion']['runtime_lock']; fixture = lock_config(lock)
        if os.environ.get('FUSION_RETRIEVAL_HOST_ISOLATED') != '1':
            cmd = ['bwrap', '--die-with-parent', '--ro-bind', '/', '/', '--bind', fixture['root'], fixture['root'],
                   '--proc', '/proc', '--dev', '/dev']
            for denied in fixture['denied_paths']: cmd += ['--tmpfs', denied]
            os.execvpe('bwrap', [*cmd, '--', sys.executable, '-m', __spec__.name, *sys.argv[1:]],
                       dict(os.environ, FUSION_RETRIEVAL_HOST_ISOLATED='1'))
        install(lock)
        from .host import serve
        serve(path, int(sys.argv[3]), sys.argv[4])


if __name__ == '__main__': main()
