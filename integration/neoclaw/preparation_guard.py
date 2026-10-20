"""Generation-disabled test launcher. No production runtime discovery or probes.

Fresh Linux network namespace: host runtimes and public networks are unreachable.
Known generative binaries/assets and service managers are masked before tests.
An owned sentinel proves isolation without contacting any generative endpoint.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

from fusion.contracts import require

BLOCKED_FILES = ('/usr/local/bin/ollama', '/usr/bin/ollama', '/usr/bin/systemctl',
                 '/usr/sbin/service', '/usr/bin/service', '/usr/bin/docker', '/usr/bin/podman')
BLOCKED_DIRS = ('/usr/share/ollama', '/home/purplezky/.ollama',
                '/home/purplezky/work/takopi/ollama')


def verify(parent, sentinel=None):
    require(os.readlink('/proc/self/ns/net') != parent, 'UNAUTHORIZED')
    masked = {}
    for path in BLOCKED_FILES:
        if Path(path).exists():
            require(not os.access(path, os.X_OK), 'UNAUTHORIZED'); masked[path] = 'not executable'
    for path in BLOCKED_DIRS:
        if Path(path).exists():
            require(not any(Path(path).iterdir()), 'UNAUTHORIZED'); masked[path] = 'empty mount'
    if sentinel:
        try:
            with socket.create_connection(('127.0.0.1', sentinel), timeout=.2): pass
        except OSError: pass
        else: require(False, 'UNAUTHORIZED')
    return dict(namespace=os.readlink('/proc/self/ns/net'), parent_namespace=parent,
                owned_parent_sentinel_unreachable=bool(sentinel), masked=masked,
                live_endpoints_contacted=0, additional_live_generations=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inside', action='store_true')
    parser.add_argument('--guard-evidence')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    require(bool(command))
    if args.inside:
        result = verify(os.environ['FUSION_PREP_PARENT_NET'], int(os.environ['FUSION_PREP_SENTINEL']))
        if args.guard_evidence: Path(args.guard_evidence).write_text(json.dumps(result, indent=2)+'\n')
        os.execvpe(command[0], command, os.environ)
    with socket.socket() as sentinel:
        sentinel.bind(('127.0.0.1', 0)); sentinel.listen()
        env = dict(os.environ, FUSION_PREP_PARENT_NET=os.readlink('/proc/self/ns/net'),
                   FUSION_PREP_SENTINEL=str(sentinel.getsockname()[1]),
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1')
        args2 = ['bwrap', '--die-with-parent', '--unshare-net', '--ro-bind', '/', '/',
                 '--bind', '/tmp', '/tmp', '--bind', str(Path.cwd()), str(Path.cwd()),
                 '--dev', '/dev', '--proc', '/proc']
        for path in BLOCKED_FILES:
            if Path(path).exists(): args2 += ['--ro-bind', '/dev/null', path]
        for path in BLOCKED_DIRS:
            if Path(path).exists(): args2 += ['--tmpfs', path]
        args2 += ['--', sys.executable, '-m', __spec__.name, '--inside']
        if args.guard_evidence: args2 += ['--guard-evidence', args.guard_evidence]
        result = subprocess.run(args2+['--', *command], env=env)
        raise SystemExit(result.returncode)


if __name__ == '__main__': main()
