"""Bounded native MeTTaClaw command entry: original parser -> eval -> real skill.

Loads the pinned upstream helper/utils/skills/NAL files; does not start the LLM,
channels, Chroma, wake loop or private memory. Adaptation changes only the metta
skill's named-function seam in a generated copy, never the upstream checkout.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from fusion.contracts import digest, require
from fusion import neoclaw_contracts as c

ROOT = Path(__file__).resolve().parents[2]
from .startup_overlay import adapted_skill


def run(runtime_file, command, caller_config=None, denied_paths=(), search_recording=None, search_runtime=None):
    from fusion.adapters.neoclaw_nal import NativeTruthDeduction
    runtime = NativeTruthDeduction(runtime_file).runtime
    omega, petta = Path(runtime['mettaclaw']), Path(runtime['petta'])
    for file in ('src/helper.py', 'src/skills.metta', 'src/skills.pl', 'src/utils.metta', 'lib_nal.metta'):
        require(digest((omega / file).read_bytes()) == c.PINS['sources']['mettaclaw']['files'][file], 'UNSUPPORTED_PROFILE')
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'LANG', 'LC_ALL', 'TMPDIR')}
    env.update(runtime['environment'])
    if search_recording is not None:
        # Original search compatibility oracle only: external SDK response fixture.
        # This is not the adapted application or a network-provider substitute.
        from fusion.adapters.neoclaw_search import NativeWebSearch
        require(caller_config is None, 'UNSUPPORTED_PROFILE')
        sdk = NativeWebSearch(dict(runtime=str(search_runtime), boundary='recorded-response',
                                  recording=str(search_recording), audit='/dev/null')).runtime
        site = Path(sdk['python']).parent.parent/'lib/python3.12/site-packages'
        env['PYTHONPATH'] = str(site)+os.pathsep+env.get('PYTHONPATH', '')
        env['NEOCLAW_SEARCH_ORIGINAL_SITE'] = str(site)
        env['NEOCLAW_SEARCH_ORIGINAL_HELPER'] = str(Path(sdk['helper']).parent)
        env['NEOCLAW_SEARCH_ORIGINAL_RECORDING'] = str(Path(search_recording).resolve())
    with tempfile.TemporaryDirectory(prefix='neoclaw-command-') as directory:
        directory = Path(directory)
        capture = directory / 'result.json'
        env['NEOCLAW_S01_CAPTURE'] = str(capture)
        skills = omega / 'src/skills.metta'
        if caller_config:
            env['NEOCLAW_S01_CALLER'] = str(Path(caller_config).resolve())
            original = skills.read_text()
            skills = directory / 'skills.metta'
            skills.write_text(adapted_skill(original))
        lines = ['!(import! &self (library lib_import))', '!(import! &self (library lib_patrick))']
        imports = [omega/'src/helper.py', omega/'src/utils.metta', skills, omega/'lib_nal.metta', ROOT/'integration/neoclaw/neoclaw_capture.py']
        if search_recording is not None:
            imports += [ROOT/'integration/neoclaw/search_original_fixture.py', omega/'channels/websearch.py', omega/'src/channels.metta']
        if caller_config:
            imports.append(ROOT/'integration/neoclaw/neoclaw_bridge.py')
        lines += ['!(import! &self ' + json.dumps(str(p)) + ')' for p in imports]
        # The command path uses the actual upstream parser and skill implementation;
        # only the outer single-command driver/capture replaces model ingress.
        lines += ['!(let $parsed (py-call (helper.balance_parentheses ' + json.dumps(command) + ')) '
                  '(let $commands (sread $parsed) (let $result (collapse (let $command (superpose $commands) (eval $command))) '
                  '(py-call (neoclaw_capture.record $result)))))']
        entry = directory/'command.metta'
        entry.write_text('\n'.join(lines) + '\n')
        goal = "asserta(library_path('" + str(omega).replace("'", "''") + "'))"
        args = [runtime['swipl'], '-q', '-s', str(petta/'src/main.pl'), '-g', goal, '--', str(entry), '--silent']
        if denied_paths:
            # Test isolation: the worker's files and old private Omega checkout are
            # masked, while TCP loopback remains available. No stdio substitution.
            args = ['bwrap', '--die-with-parent', '--ro-bind', '/', '/', '--bind', '/tmp', '/tmp', '--proc', '/proc', '--dev', '/dev',
                    *[v for p in denied_paths for v in ('--tmpfs', str(Path(p).resolve()))], '--', *args]
        process = subprocess.run(args, cwd=directory, env=env, text=True, capture_output=True, timeout=40)
        result = json.loads(capture.read_text()) if capture.exists() else None
        return dict(exit_code=process.returncode, values=result, stdout=process.stdout, stderr=process.stderr,
                    command=command, adapted=bool(caller_config), skill_sha256=digest(skills.read_bytes()),
                    denied_paths=list(map(str, denied_paths)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime')
    parser.add_argument('command')
    parser.add_argument('--caller-config')
    parser.add_argument('--deny-path', action='append', default=[])
    args = parser.parse_args()
    print(json.dumps(run(args.runtime, args.command, args.caller_config, args.deny_path), indent=2))
