"""M4 required real-chain gates, preserving failures/timeouts/missing inputs.

Build with build_m4.py first. This host process checks namespace isolation while
its child runs the actual node and authenticated native integration tests.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fusion.adapters.f1r3_m4 import SOURCE, PROFILE

GATES = ('BASELINE', 'CHAIN_SOURCE_BUILD', 'NATIVE_HIVE_DA', 'APPROVAL_BINDING', 'REAL_CHAIN_EFFECT',
         'RECOVERY', 'PRIVACY_ISOLATION', 'REPRO_READBACK', 'DEMO_HANDOFF', 'SCOPE')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def verify(build, output, development=False, node_source=None, node_binary=None):
    build, output = build.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    paths = git('ls-files', '--cached', '--others', '--exclude-standard').splitlines()
    source = {'commit': git('rev-parse', 'HEAD'), 'status': git('status', '--porcelain').splitlines(),
        'files': {p: sha(ROOT / p) for p in paths if p.startswith(('fusion/', 'integration/', 'scripts/', 'tests/', 'adapters/', 'contracts/'))
                  or p in ('pyproject.toml', 'uv.lock', 'codex_fusion_m4_hive_da_chain_commitment.md')}}
    report = {'source': source, 'requested_ancestor': '985d2f34ea8df8c5d93582e4ed6fe5cbe1843074',
        'starting_descendant': '8491c4900a5ccab872073e62b1024e3b731aeaf9',
        'development': development, 'profile': PROFILE, 'gates': {g: 'NOT_RUN' for g in GATES}, 'commands': [],
        'missing_prerequisites': [], 'executed_failures': [], 'observation_timeouts': [],
        'classifications': {'real': ['authenticated native Hive ASGI/Programs/Supervisor/PeTTa', 'local real DeTTa',
            'unchanged pinned F1R3node single validator in route-free network namespace', 'independent SQLite owner journals'],
            'fixtures': ['generated shareable input, operator grants, test genesis/key', 'reference-message counterparty',
                'transport/malformed-response cases in test_m4_chain', 'deterministic pauses and SIGKILL'],
            'not_run': ['public networks', 'multi-validator safety', 'empty global caches', 'power loss/distributed failover',
                        'live journal migration', 'production security/economics']}}
    def save(): (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    def command(name, args, env=None, **kw):
        began = time.monotonic()
        with open(output / (name + '.log'), 'w') as log:
            result = subprocess.run(list(map(str, args)), cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, **kw)
        item = {'name': name, 'command': [str(a).replace(str(ROOT), '<FUSION>') for a in args],
            'returncode': result.returncode, 'seconds': round(time.monotonic()-began, 3), 'log_sha256': sha(output / (name + '.log'))}
        report['commands'].append(item); save()
        return result.returncode
    save()
    try:
        assert development or not source['status'], 'Final verification requires a clean committed checkout'
        environment = build / 'providers/environment.json'
        config = json.loads(environment.read_text())
        native = Path(config['VIRTUAL_ENV']) / 'bin/python'
        if not native.is_file(): raise FileNotFoundError('Pinned native Python missing')
        repo = node_source.resolve() if node_source else build / 'chain/source'
        binary = node_binary.resolve() if node_binary else build / 'chain/target/debug/node'
        if not binary.is_file(): raise FileNotFoundError('Pinned real node binary missing')
        assert subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip() == SOURCE
        assert not subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True).strip(), 'Node source dirty'
        if not development:
            chain_build = json.loads((build / 'chain/build.json').read_text())
            assert chain_build['returncode'] == 0 and chain_build['fresh_destination']
            assert chain_build['binary_sha256'] == sha(binary) and chain_build['recipe_sha256'] == sha(ROOT / 'scripts/build_chain.py')
            report['chain_build'] = chain_build
        report['node_binary_sha256'] = sha(binary)
        report['source_pins'] = {name: json.loads((ROOT / path).read_text()) for name, path in
            [('chain', 'integration/chain/sources.json'), ('hive', 'integration/hive/sources.json'), ('pln', 'integration/pln/deduction-sources.json')]}
        if not all(shutil.which(t) for t in ('unshare', 'ip', 'ss')): raise FileNotFoundError('unshare/ip/ss required for OS isolation')
        probe = subprocess.run(['unshare', '--user', '--map-root-user', '--net', 'sh', '-c', 'ip link set lo up'], capture_output=True)
        if probe.returncode: raise PermissionError('Unprivileged route-free network namespace unavailable')
    except (FileNotFoundError, PermissionError) as error:
        report['missing_prerequisites'].append({'type': type(error).__name__, 'reason': str(error).replace(str(ROOT), '<FUSION>')})
        for gate in GATES: report['gates'][gate] = 'BLOCKED'
        save(); return 2
    except (AssertionError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        report['executed_failures'].append({'stage': 'input-validation', 'reason': str(error)})
        report['gates']['CHAIN_SOURCE_BUILD'] = 'FAIL'; save(); return 1
    env = dict(os.environ, **config)
    env.update(PYTHONPATH=str(ROOT) + os.pathsep + config['HIVE_REPO'], M4_HOST_NETNS=os.readlink('/proc/self/ns/net'),
        M4_NODE_SOURCE=str(repo), M4_NODE_BINARY=str(binary), M4_OUTPUT=str(output), M4_SOCKET_CHALLENGE=str(output / 'socket-challenge.json'))
    baseline = None
    if not development:
        baseline_log = open(output / 'baseline.log', 'w')
        baseline_started = time.monotonic()
        baseline_args = ['uv', 'run', '--python', '3.11', '--locked', 'python', 'scripts/verify_m3_1.py', str(environment), '--output', str(output / 'baseline')]
        baseline = subprocess.Popen(baseline_args, cwd=ROOT, stdout=baseline_log, stderr=subprocess.STDOUT)
    fixture_code = command('chain-fixtures', ['uv', 'run', '--python', '3.11', '--locked', 'python', '-m', 'unittest', '-v', 'tests.test_m4_chain'])
    native_args = ['unshare', '--user', '--map-root-user', '--net', str(native), '-m', 'pytest', '-vv', '--tb=short',
        'integration/chain/test_m4.py', '--basetemp=' + str(output / 'private-tests'), '--junitxml=' + str(output / 'native.xml')]
    began = time.monotonic(); host_checks = None
    with open(output / 'native.log', 'w') as log:
        process = subprocess.Popen(native_args, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        while process.poll() is None:
            challenge = output / 'socket-challenge.json'
            if challenge.exists() and host_checks is None:
                ports = json.loads(challenge.read_text())['ports']; host_checks = []
                for port in ports:
                    with socket.socket() as sock:
                        sock.settimeout(.5)
                        host_checks.append({'port': port, 'host_connect_errno': sock.connect_ex(('127.0.0.1', port))})
                (output / 'host-isolation.json').write_text(json.dumps({'node_ready_inside': True, 'checks': host_checks,
                    'status': 'PASS' if all(x['host_connect_errno'] == 111 for x in host_checks) else 'FAIL'}, indent=2) + '\n')
            time.sleep(.5)
    report['commands'].append({'name': 'real-native-chain', 'returncode': process.returncode,
        'seconds': round(time.monotonic()-began, 3), 'log_sha256': sha(output / 'native.log'),
        'command': ['unshare --user --map-root-user --net <NATIVE_PYTHON> -m pytest integration/chain/test_m4.py']})
    cases = []
    if (output / 'native.xml').exists():
        for case in ET.parse(output / 'native.xml').getroot().iter('testcase'):
            error = next((x for x in case if x.tag in ('failure', 'error', 'skipped')), None)
            state = 'PASS' if error is None else 'NOT_RUN' if error.tag == 'skipped' else (
                'OBSERVATION_TIMEOUT' if 'OBSERVATION_TIMEOUT:' in (error.text or '') else 'FAIL')
            item = {'name': case.get('name'), 'status': state, 'seconds': float(case.get('time'))}
            cases.append(item)
            if state == 'OBSERVATION_TIMEOUT': report['observation_timeouts'].append(item)
            elif state == 'FAIL': report['executed_failures'].append(item)
    report['native_cases'] = cases
    def case_gate(prefixes):
        chosen = [c['status'] for c in cases if any(c['name'].startswith(p) for p in prefixes)]
        return 'FAIL' if 'FAIL' in chosen else 'OBSERVATION_TIMEOUT' if 'OBSERVATION_TIMEOUT' in chosen else (
            'PASS' if chosen and all(s == 'PASS' for s in chosen) else 'NOT_RUN')
    happy = case_gate(['test_same_artifact'])
    for gate in ('NATIVE_HIVE_DA', 'REAL_CHAIN_EFFECT', 'DEMO_HANDOFF'): report['gates'][gate] = happy
    report['gates']['APPROVAL_BINDING'] = case_gate(['test_native_live_authority']) if fixture_code == 0 else 'FAIL'
    report['gates']['RECOVERY'] = case_gate(['test_native_caller_dies', 'test_real_adapter_kill', 'test_native_observation_kill', 'test_same_artifact'])
    if (output / 'isolation.json').exists() and host_checks:
        report['gates']['CHAIN_SOURCE_BUILD'] = 'PASS'
        report['gates']['PRIVACY_ISOLATION'] = happy if all(c['host_connect_errno'] == 111 for c in host_checks) else 'FAIL'
    else:
        report['gates']['CHAIN_SOURCE_BUILD'] = case_gate(['test_same_artifact'])
    if not development: report['gates']['REPRO_READBACK'] = happy
    # The source diff is evidence; cognition, original plugin, DA and legacy adapter must remain unchanged.
    protected = ['fusion/ports.py', 'fusion/atoms.py', 'fusion/execution.py', 'fusion/messaging.py', 'fusion/private.py',
        'fusion/episodes.py', 'fusion/beliefs.py', 'fusion/attention.py', 'fusion/inference.py', 'fusion/adapters/f1r3.py',
        'fusion/adapters/pln_revision.py', 'fusion/adapters/pln_deduction.py', 'integration/hive/program/program.py',
        'integration/hive/program/plugin.json', 'integration/hive/sources.json', 'integration/hive/test_integration.py']
    report['protected_changes'] = git('diff', report['requested_ancestor'], '--', *protected).splitlines()
    report['gates']['SCOPE'] = 'PASS' if not report['protected_changes'] else 'FAIL'
    save()
    if baseline is not None:
        code = baseline.wait(); baseline_log.close()
        report['commands'].append({'name': 'm1-through-m3_1-regression', 'returncode': code,
            'seconds': round(time.monotonic()-baseline_started, 3), 'log_sha256': sha(output / 'baseline.log')})
        report['gates']['BASELINE'] = 'PASS' if code == 0 else 'FAIL'
        baseline_report = output / 'baseline/verification.json'
        if baseline_report.exists():
            previous = json.loads(baseline_report.read_text())
            report['baseline'] = {'source': previous['source'], 'gates': previous['gates'],
                'commands': [{k: c[k] for k in ('name', 'returncode', 'seconds', 'tests') if k in c} for c in previous['commands']]}
            if previous.get('prerequisite', {}).get('status') == 'BLOCKED':
                report['gates']['BASELINE'] = 'BLOCKED'
                report['missing_prerequisites'].append({'stage': 'baseline', 'reason': previous['prerequisite']['reason']})
        if code and report['gates']['BASELINE'] != 'BLOCKED':
            report['executed_failures'].append({'stage': 'baseline', 'returncode': code})
    report['source']['end_commit'] = git('rev-parse', 'HEAD')
    report['source']['end_runtime_matches_start'] = all((ROOT / p).is_file() and sha(ROOT / p) == value
        for p, value in source['files'].items())
    if not development and (not report['source']['end_runtime_matches_start'] or git('status', '--porcelain') or
                            report['source']['end_commit'] != source['commit']):
        report['gates']['BASELINE'] = 'FAIL'
        report['executed_failures'].append({'stage': 'source-changed-during-verification'})
    report['result'] = 'PASS' if all(s == 'PASS' for s in report['gates'].values()) else 'INCOMPLETE'
    save()
    return 0 if report['result'] == 'PASS' or (development and process.returncode == 0 and fixture_code == 0) else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--development', action='store_true', help='dirty checkout allowed; BASELINE/REPRO cannot pass')
    parser.add_argument('--node-source', type=Path); parser.add_argument('--node-binary', type=Path)
    args = parser.parse_args()
    if (args.node_source or args.node_binary) and not args.development: parser.error('custom node paths require --development')
    raise SystemExit(verify(args.build, args.output, args.development, args.node_source, args.node_binary))
