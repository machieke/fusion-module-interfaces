"""Run bounded M2 gates and the unchanged M1.2 regression; never skip a real gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fusion.adapters.pln_revision import GuardedRevision, PINS
from fusion.contracts import ContractError

GATES = ('BASELINE', 'CONTRACTS', 'C1', 'C1_INDEPENDENT', 'C2_GUARDS', 'C2_NATIVE',
         'PRIVACY', 'RECOVERY', 'HIVE_M2', 'REPRO', 'SCOPE', 'CHAIN')


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args): return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def verify(environment, output):
    environment, output = environment.resolve(), output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = git('ls-files', '--cached', '--others', '--exclude-standard').splitlines()
    relevant = [p for p in files if p.startswith(('fusion/', 'integration/', 'tests/', 'scripts/', 'adapters/', 'contracts/'))
                or p in ('uv.lock', 'pyproject.toml', 'codex_fusion_m2_episodic_memory_and_pln_revision.md')]
    report = {'source': {'commit': git('rev-parse', 'HEAD'), 'status': git('status', '--porcelain').splitlines(),
                        'files': {p: sha(ROOT / p) for p in relevant}},
              'sources': PINS, 'commands': [], 'gates': {gate: 'NOT_RUN' for gate in GATES},
              'fixture_scope': 'Independent file AtomStorage and guard-only math; generated observations and operator assumptions.',
              'real_scope': 'Local DeTTa files; native pinned Truth_Revision; actual authenticated Hive Programs dispatch.',
              'unrun': ['global empty-cache build', 'historical SWI 10.0.1', 'power-loss/distributed failover',
                        'ECAN', 'inference control', 'chain', 'live migration']}
    unchanged = ['fusion/contracts.py', 'fusion/atoms.py', 'fusion/registry.py', 'fusion/responses.py',
        'fusion/execution.py', 'fusion/messaging.py', 'fusion/bindings.py', 'fusion/adapters/detta.py',
        'adapters/detta/src/main.rs', 'adapters/detta/Cargo.lock', 'contracts/wire.schema.json',
        'contracts/responses.schema.json', 'integration/hive/program/program.py', 'integration/hive/program/plugin.json',
        'integration/hive/test_integration.py', 'integration/hive/native_caller.py', 'integration/hive/sources.json',
        'scripts/build_hive.py', 'scripts/verify_m12.py']
    report['preserved_m1_2_files'] = {path: hashlib.sha256(subprocess.check_output(
        ['git', '-C', str(ROOT), 'show', '4ee5cbe8b84689a5d2432530083738b263142f90:' + path])).hexdigest() == sha(ROOT / path)
        for path in unchanged}
    def save(): (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    save()
    try:
        config = json.loads(environment.read_text())
        env = dict(os.environ, **config)
        env['PYTHONPATH'] = str(ROOT) + os.pathsep + config['HIVE_REPO']
        native = Path(config['VIRTUAL_ENV']) / 'bin/python'
        assert native.is_file() and Path(config['M2_DETTA_BINARY']).is_file()
        report['runtime'] = GuardedRevision(config['M2_REVISION_ENV']).profile()
        report['build'] = json.loads((environment.parent / 'build.json').read_text())
        report['hive_sources'] = json.loads((ROOT / 'integration/hive/sources.json').read_text())
        report['dependency_states'] = {}
        for name, path in {'hive': config['HIVE_REPO'], 'detta': config['DETTA_REPO'],
                           'petta': config['PETTA_PATH']}.items():
            report['dependency_states'][name] = {key: subprocess.check_output(['git', '-C', path, *args], text=True).strip()
                for key, args in [('commit', ['rev-parse', 'HEAD']), ('status', ['status', '--porcelain'])]}
        require_build = report['build']['fresh_destination'] and report['build']['recipe_sha256'] == sha(ROOT / 'scripts/build_m2.py')
        assert require_build, 'unmatched source/build recipe'
        assert all(report['preserved_m1_2_files'].values()), 'M1.2 preservation mismatch'
    except (OSError, KeyError, ValueError, AssertionError, ContractError) as error:
        report['prerequisite'] = {'status': 'BLOCKED', 'reason': str(error), 'environment': str(environment)}
        for gate in ('BASELINE', 'C1', 'C2_NATIVE', 'HIVE_M2', 'REPRO'): report['gates'][gate] = 'BLOCKED'
        save(); return 2

    def execute(name, args, gates, *, junit=False, overrides=None, cwd=ROOT):
        began = time.monotonic()
        result = subprocess.run(list(map(str, args)), cwd=cwd, env=dict(env, **(overrides or {})),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log = output / (name + '.log'); log.write_text(result.stdout)
        item = {'name': name, 'command': list(map(str, args)), 'cwd': str(cwd), 'returncode': result.returncode,
                'seconds': round(time.monotonic()-began, 3), 'log': log.name, 'sha256': sha(log),
                'summaries': re.findall(r'(?:Ran \d+ tests? in [^\n]+|\d+ passed[^\n]*)', result.stdout)}
        if junit:
            suites = list(ET.parse(output / (name + '.xml')).getroot().iter('testsuite'))
            item['tests'] = {key: sum(int(s.get(key, 0)) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
            if item['tests']['skipped']: result.returncode = 1; item['gate_error'] = 'Real tests must not skip'
        report['commands'].append(item)
        for gate in gates: report['gates'][gate] = 'PASS' if result.returncode == 0 else 'FAIL'
        save(); print(name, 'PASS' if result.returncode == 0 else 'FAIL', item.get('tests', item['summaries']), flush=True)
        if result.returncode: raise SystemExit(result.returncode)

    execute('m1_2-regression', ['uv', 'run', '--python', '3.11', '--locked', 'python', 'scripts/verify_m12.py',
            environment.parent / 'native/environment.json'], ['BASELINE'])
    report['baseline_details'] = json.loads((ROOT / 'artifacts/m1_2/verification.json').read_text())
    execute('m2-fixtures', ['uv', 'run', '--python', '3.11', '--locked', 'python', '-m', 'unittest', '-v', 'tests.test_m2'],
            ['CONTRACTS', 'C1_INDEPENDENT'], overrides={'M2_REVISION_ENV': str(output / 'absent-pln'),
                                                     'M2_DETTA_BINARY': str(output / 'absent-detta')})
    reachability = json.loads(Path(config['M2_REVISION_ENV']).read_text())['reachability']
    guard_cases = ['nonfinite_out_of_range_and_wrong_interpretation_rejected', 'scope_identity_and_immutability',
        'duplicate_revision_never_calls_formula', 'disjoint_ids_alone_do_not_justify_revision',
        'common_origin_overrides_independence_assertion', 'declaration_must_bind_exact_support',
        'revision_commutes_and_duplicate_roots_do_not_accumulate', 'zero_weight_is_unknown_and_wrong_claim_fails']
    execute('upstream-revision-guards', [native, '-m', 'unittest', '-v',
        *['tests.test_pln_contracts.PLNContractTests.test_' + case for case in guard_cases]], [],
        cwd=reachability, overrides={'PYTHONPATH': reachability})
    execute('m2-native-revision', [native, '-m', 'unittest', '-v', 'integration.pln.test_revision'], ['C2_GUARDS', 'C2_NATIVE'])
    execute('m2-recovery-privacy', [native, '-m', 'unittest', '-v', 'integration.pln.test_recovery'], ['C1', 'RECOVERY'])
    execute('m2-native-hive', [native, '-m', 'pytest', '-q', 'integration/hive/test_m2_integration.py',
            '--junitxml=' + str(output / 'm2-native-hive.xml')], ['HIVE_M2', 'PRIVACY'], junit=True)
    execute('m2-demo', [native, 'scripts/m2_demo.py', environment, output / 'demo.json'], [])
    report['gates']['REPRO'] = 'PASS: fresh provider build and all supported tests; download caches warm'
    report['gates']['SCOPE'] = 'PASS: C1+C2 only; unchanged M1 wire, original Hive plugin and guarded upstream sources'
    report['gates']['CHAIN'] = 'NOT_RUN'
    save()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('environment', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/m2/final')
    args = parser.parse_args()
    raise SystemExit(verify(args.environment, args.output))
