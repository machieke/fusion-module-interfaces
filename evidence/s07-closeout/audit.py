"""Offline S07 evidence reconciliation. Reads public files; never imports runtime code.

Run from the repository root with Python 3.11+. Git reads are the only child
commands. Outputs are review evidence, not newly executed integration results.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/s07-closeout'
PUB = '4981788b4d8069a2b2264e65197f9886b74f1f5f'
PARENT = '3fc1af31f2d64583fe4c873b6b656dad2d6b1275'
PACKET = 'docs/omega-adoption/mettaclaw-neoclaw/'


def guard(event, args):
    if event in ('socket.connect', 'socket.bind', 'os.system'):
        raise RuntimeError('Offline review forbids network and shell effects')
    if event == 'subprocess.Popen':
        assert args[0] == 'git' and args[1][1] in ('show', 'diff', 'status', 'rev-parse', 'ls-files')


sys.addaudithook(guard)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def published(path):
    return git('show', PUB + ':' + path)


assert git('rev-parse', 'HEAD').decode().strip() == PUB
old = read('evidence/s07/source-state.json')
assert all(sha(published(p)) == h for p, h in old['files'].items())
assert read('evidence/s07/final-audit.json')['source_state_sha256'] == sha((ROOT / 'evidence/s07/source-state.json').read_bytes())
changed = git('diff', '--name-only', PARENT, PUB).decode().splitlines()
assert set(changed) == set(old['files']) | {'evidence/s07/source-state.json', 'evidence/s07/final-audit.json'}

# Resolve every historical hash to actual bytes, without changing a historical manifest.
archives = {}
for f in sorted((ROOT / 'evidence/s07').rglob('*')):
    if f.is_file():
        archives.setdefault(sha(f.read_bytes()), f.relative_to(ROOT).as_posix())


def resolve(path, expected):
    f = ROOT / path
    if f.is_file() and sha(f.read_bytes()) == expected:
        return path, f.read_bytes()
    if expected in archives:
        p = archives[expected]
        return p, (ROOT / p).read_bytes()
    for commit in (PUB, PARENT):
        data = git('show', commit + ':' + path)
        if sha(data) == expected:
            return commit + ':' + path, data
    raise AssertionError((path, expected))


versions = ['test-source', 'cpu-test-source', 'cpu-live-source', 'isolated-test-source',
            'cache-counter-test-source', 'remaining-live-source']
relationships = []
for name in versions:
    manifest = read('evidence/s07/' + name + '.json')
    rows = []
    for p, h in manifest['files'].items():
        where, data = resolve(p, h)
        assert sha(data) == h
        current = sha(published(p))
        rows.append(dict(path=p, tested_sha256=h, resolved_at=where, publication_sha256=current,
                         identical_to_publication=h == current))
    relationships.append(dict(manifest='evidence/s07/' + name + '.json', entries=len(rows),
        manifest_sha256=sha((ROOT / ('evidence/s07/' + name + '.json')).read_bytes()),
        changed_since_manifest=[r['path'] for r in rows if not r['identical_to_publication']], files=rows))

# Enumerate every successive source change. Category 1 includes test behavior;
# executable rehearsal configuration is category 2, never silently documentation.
stages = []
for left, right in zip(versions, versions[1:]):
    a = read('evidence/s07/' + left + '.json')['files']
    b = read('evidence/s07/' + right + '.json')['files']
    delta = []
    for p in sorted(a.keys() | b.keys()):
        if a.get(p) != b.get(p):
            category = 2 if p.endswith(('model-sources.json', 'model_run.py', 'isolated-ollama-launch.py')) else 1
            delta.append(dict(path=p, before=a.get(p), after=b.get(p), category=category))
    stages.append(dict(before=left, after=right, changes=delta))

latest = read('evidence/s07/remaining-live-source.json')['files']
lock_path = 'integration/neoclaw/model-sources.json'
where, old_lock = resolve(lock_path, latest[lock_path])
lock = read(lock_path)
fields = []


def field_diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(a.keys() | b.keys()):
            if a.get(k) != b.get(k):
                field_diff(a.get(k), b.get(k), path + '/' + k)
    else:
        fields.append(dict(path=path, before=a, after=b,
            category=2 if path.startswith(('/selected_profile', '/input_deadline_ms', '/isolated_runtime')) else 3))


field_diff(json.loads(old_lock), lock)
runtime_locks = {}
for f in sorted((ROOT / 'evidence/s07').glob('live-*/**/ollama-runtime.json')):
    x = json.loads(f.read_text())
    assert x['binary'] == lock['runtime']['binary']
    assert x['version'] == lock['runtime']['version']
    assert x['model_digest'] == lock['model']['manifest_digest']
    assert sha(Path(x['native_source']).read_bytes()) == lock['native']['sha256']
    runtime_locks[f.relative_to(ROOT).as_posix()] = dict(sha256=sha(f.read_bytes()), value=x)
assert runtime_locks
loaded = read('evidence/s07/isolated-runtime/loaded-runner.json')[0]
inventory = read('evidence/s07/ollama-runner-files.json')
matches = {p: h for p, h in loaded['loaded_runtime_files'].items()
           if inventory['files'].get(p, {}).get('sha256') == h}
assert len(matches) == 7 and len(loaded['loaded_runtime_files']) == 8
assert loaded['sha256'] == loaded['loaded_runtime_files'][loaded['executable']]
assert read('evidence/s07/isolated-runtime/listener-proof.json')['running_executable_sha256'] == lock['runtime']['binary_sha256']
launch = read('evidence/s07/isolated-runtime/launch.json')
assert launch['binary_sha256'] == lock['runtime']['binary_sha256']
assert launch['model_manifest'] == lock['model']['manifest_digest']
assert launch['selected_environment']['OLLAMA_HOST'] == '127.0.0.1:48173'
assert launch['selected_environment']['OLLAMA_NO_CLOUD'] == 'true'
assert read('evidence/s07/isolated-runtime/cleanup.json')['listener_closed'] is True
assert (ROOT / 'evidence/s07/pre-live/test-source.json').read_bytes() == (ROOT / 'evidence/s07/test-source.json').read_bytes()
constants = ('PROFILE', 'MODEL', 'MODEL_DIGEST', 'TRANSFORM', 'OPTIONS', 'LIMITS')


def selected_constants(data):
    values = {}
    for node in ast.parse(data).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in constants:
                    values[target.id] = ast.dump(node.value)
                elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                    for key, value in zip(target.elts, node.value.elts):
                        if isinstance(key, ast.Name) and key.id in constants:
                            values[key.id] = ast.dump(value)
    assert set(values) == set(constants)
    return values


old_contract_hash = read('evidence/s07/test-source.json')['files']['fusion/model_contracts.py']
_, old_contract = resolve('fusion/model_contracts.py', old_contract_hash)
assert selected_constants(old_contract) == selected_constants((ROOT / 'fusion/model_contracts.py').read_bytes())
for p in latest:
    if p.endswith('.py'):
        ast.parse((ROOT / p).read_text(), filename=p)

save('source-review.json', dict(publication=PUB, parent=PARENT, branch='master',
    historical_test_identity='S06 parent plus the original versioned working-tree hashes; publication is not a rerun',
    published_changed_files={p: sha(published(p)) for p in changed},
    historical_delivery_hashes_verified=len(old['files']), versioned_relationships=relationships,
    successive_changes=stages, post_live_changes=[dict(path=lock_path, snapshot=where,
        before_sha256=sha(old_lock), after_sha256=sha((ROOT / lock_path).read_bytes()), fields=fields)],
    executable_runtime_locks=runtime_locks, loaded_files_matches=matches,
    newly_observed_loaded_files={p: h for p, h in loaded['loaded_runtime_files'].items() if p not in matches},
    pre_live_test_source_identical_to_test_source=True,
    unchanged_original_constants=list(constants),
    runtime_lock_conclusion='model-sources.json is not read by executable consumers; generated ollama-runtime.json is hash-checked, frozen in owner seal and consumed by OllamaCompletion. Source ledger selected_profile/input_deadline/isolated_runtime are reproduction metadata, so classified separately from result reporting.',
    static_python_files_parsed=sum(p.endswith('.py') for p in latest), additional_live_generations=0))

# Derive call accounting from separate owner/application exports, not aggregate totals.
sessions = ['live-01', 'live-04/1', 'live-05/1', 'live-06/1', 'live-06/2', 'live-06/3', 'live-06/4']
calls, summaries, ids = [], [], set()
expected_output = 'Synthetic S07 reply: native calculation observed.'
for session in sessions:
    prefix = 'evidence/s07/' + session + '/'
    providers = read(prefix + 'provider-calls.json')
    applications = {r['id']: r for r in read(prefix + 'application-calls.json')}
    assert set(applications) == {p['id'] for p in providers}
    for p in providers:
        assert p['id'] not in ids and p['reserved'] == 1
        ids.add(p['id'])
        a = applications[p['id']]
        assert a['intent'] == p['intent'] and a['slot'] == p['slot']
        intent = json.loads(p['intent'])
        assert intent['id'] == p['id'] and intent['session'] == p['session']
        assert intent['profile'] == ('neoclaw-ollama-qwen38-text/1' if session == 'live-01' else lock['selected_profile'])
        response = json.loads(p['response']) if p['response'] else None
        if response is not None:
            captured = json.loads(a['result'])
            assert captured['response'] == response and captured['captured_ms'] == p['captured_ms']
            assert captured['intent_sha256'] == sha(p['intent'].encode()) and captured['id'] == p['id']
            assert captured['reserved'] == 1 and captured['late'] is False
            assert p['captured_ms'] <= intent['deadline_ms'] and a['calls'] <= 8
        else:
            assert a['result'] is None and a['admission'] is None
        row = dict(number=len(calls)+1, source=prefix, id=p['id'], session=p['session'], slot=p['slot'],
            source_id=intent['source_id'], intent_sha256=sha(p['intent'].encode()),
            profile=intent['profile'], deadline_ms=intent['deadline_ms'], reserved=p['reserved'],
            capture=bool(response), admission=a['admission'], failure_code=p['failure_code'],
            proposal=json.loads(a['proposal']) if a['proposal'] else None,
            application_rpc_reservations=a['calls'], durations_ns=response['durations_ns'] if response else None,
            usage=response['usage'] if response else None)
        calls.append(row)
    result_path = ROOT / (prefix + 'result.json')
    result = json.loads(result_path.read_text()) if result_path.exists() else {}
    complete = result.get('classification') == 'REAL_OLLAMA_GENERATION'
    peer_observed = False
    if complete:
        assert result['provider_calls'] == providers
        assert result['model_calls'] == list(applications.values())
        peer_observed = any(' :' + expected_output in x.get('received', '') for x in result['traffic'])
        assert peer_observed and read(prefix + 'status.json') == {'status': 'BOUNDED_STOP'}
        outgoing = read(prefix + 'bridge-egress.json')
        assert len(outgoing) == 1 and outgoing[0]['reserved'] == 1 and outgoing[0]['outcome'] == 'socket-write-returned'
        accept = read(prefix + 'app_channel_outputs.json')
        assert len(accept) == 1 and accept[0]['send_calls'] == 1 and accept[0]['acceptance'] is not None
    first = next(iter(applications.values()))
    second = list(applications.values())[1] if len(applications) == 2 else None
    feedback = ''
    if second:
        prompt = json.loads(second['intent'])['native_prompt']
        feedback = prompt.split(' LAST_SKILL_USE_RESULTS: ', 1)[1].split(' HISTORY: ', 1)[0]
    deduction = bool(feedback) and first['admission'] == 'authorized' and '(stv 0.5599999999999999 0.4032)' in feedback
    if deduction:
        assert json.loads(first['proposal']) == [['metta', '(Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))']]
        turns = ROOT / (prefix + 'app_turns.json')
        if turns.exists():
            assert read(prefix + 'app_turns.json')[0]['projection'] == feedback
            occurrence = read(prefix + 'app_occurrences.json')[0]
            assert occurrence['done'] == 1 and occurrence['result'] == '(stv 0.5599999999999999 0.4032)'
        else:
            assert '(stv 0.5599999999999999 0.4032)' in (ROOT / (prefix + 'native.log')).read_text()
    recovery = None
    if (ROOT / (prefix + 'recovery-before.json')).exists():
        before = read(prefix + 'recovery-before.json')
        assert len(before) == 1
        for key in ('id', 'intent', 'result'):
            assert before[0][key] == applications[before[0]['id']][key]
        recovery = read(prefix + 'recovery.json')
        assert recovery['signal'] == 'SIGKILL' and recovery['regenerations'] == 0
        assert recovery['captured_rows_retained'] == 1 and recovery['exact_prompt_identity_deadline_result_retained']
        if complete:
            assert result['recovered_after_sigkill'] and result['recovery_before'] == before
    model, mailbox = ('local', 'local')
    if session.startswith('live-06/'):
        plan = read('evidence/s07/live-06/plan.json')['cases'][int(session[-1])-1]
        model, mailbox = plan[:2]
    if complete:
        assert (result['model_placement'], result['mailbox_placement']) == (model, mailbox)
    summaries.append(dict(source=prefix, model_placement=model, mailbox_placement=mailbox,
        calls=len(providers), captures=sum(p['response'] is not None for p in providers),
        complete_workflow=complete, peer_observed=peer_observed, native_deduction=deduction,
        feedback_in_next_prompt=bool(feedback), recovery=recovery,
        native_status=read(prefix + 'status.json')))

totals = dict(spent_reservations=sum(c['reserved'] for c in calls), captures=sum(c['capture'] for c in calls),
    uncaptured=sum(not c['capture'] for c in calls), authorized_batches=sum(c['admission'] == 'authorized' for c in calls),
    rejected_batches=sum((c['admission'] or '').startswith('rejected:') for c in calls),
    native_deductions=sum(s['native_deduction'] for s in summaries),
    peer_observed_replies=sum(s['peer_observed'] for s in summaries),
    complete_workflows=sum(s['complete_workflow'] for s in summaries),
    captured_result_sigkill_recoveries=sum(s['recovery'] is not None for s in summaries))
assert totals == dict(spent_reservations=12,captures=10,uncaptured=2,authorized_batches=8,
    rejected_batches=2,native_deductions=5,peer_observed_replies=3,complete_workflows=3,captured_result_sigkill_recoveries=2)
durations = {}
for key in ('total', 'load', 'prompt', 'generation'):
    values = [c['durations_ns'][key]/1e9 for c in calls if c['capture']]
    durations[key] = dict(n=len(values),min_seconds=min(values),median_seconds=statistics.median(values),max_seconds=max(values))
usage = {k: sum(c['usage'][k] for c in calls if c['capture']) for k in ('input_tokens','output_tokens')}
assert usage == dict(input_tokens=3220,output_tokens=216)
reported = read('evidence/s07/live-summary.json')
assert {c['id'] for c in reported['calls']} == ids
assert reported['spent_generation_reservations'] == totals['spent_reservations']
assert reported['measured_capture_seconds'] == {k.replace('_seconds',''): v for k,v in durations['total'].items() if k != 'n'}
save('accounting.json', dict(publication=PUB, units='Reservations, captures, batches, methods, scenarios and workflows are separate units.',
    totals=totals, approved_calls=12, remaining_calls=0, additional_live_generations=0,
    calls=calls, sessions=summaries, durations=durations, captured_usage=usage, unknown_usage_calls=2,
    application_channel_time='Not independently measured end-to-end; backend total is not application or channel latency.',
    zero_generation_phases=['live-02 load-only timeout','live-03 interrupted readiness wait'],
    failure_identity_limit='live-04 rejected raw payload was not retained; cache-counter attribution remains inference.',
    recovery_limit='Public exports omit context_view; runtime assertion and recovery.json attest it, while id/intent/result bytes can be independently compared here.'))

# Historical passing methods are derived from retained logs; no test is rerun here.
verification = read('evidence/s07/verification.json')
union = set()
runs = []
for run in verification['runs']:
    data = (ROOT / 'evidence/s07' / run['log']).read_bytes()
    assert sha(data) == verification['logs'][run['log']]['sha256']
    methods = re.findall(r'^test_\S+ \(([^)]+)\) \.\.\. ok$', data.decode(), re.M)
    assert len(methods) == run['passed'], (run['log'], len(methods), run['passed'])
    union.update(methods)
    runs.append(dict(log='evidence/s07/'+run['log'],source='evidence/s07/'+run.get('source','test-source.json'),
        command=run['command'],passing_methods=methods,passing_method_executions=len(methods),
        loader_errors=run.get('loader_errors',0),seconds=run['seconds']))
assert union == set(verification['passing_methods'])
new = [p for p in union if p.startswith(('tests.test_model.', 'tests.test_model_oracle.',
        'tests.test_model_network.', 'integration.neoclaw.test_model_'))]
assert len(union) == 149 and len(new) == 30
save('test-map.json', dict(publication=PUB, recorded_final_runs=runs,
    distinct_passing_methods=149,new_s07_methods=30,selected_historical_methods=119,
    run_count=len(runs),passing_method_executions=sum(r['passing_method_executions'] for r in runs),
    native_model_fixture_methods=6,provider_fixture_sigkill_stages_in_one_method=4,
    real_native_sigkill_trials=2,complete_real_workflows=3,
    note='Method source equality does not imply all dependencies were unchanged. See source-review and closeout narrative. Historical baseline/development runs are additional records, not added to this ten-run final-series count.'))
# Final review checks: additive ledger data, untouched runtime/history, valid links,
# and exact commit-ready scope. This changes no publication or historical result.
for p in ('coverage.json', 'mapping-ledger.json'):
    current = read(PACKET + p)
    assert current.pop('closeout_review')['additional_live_generations'] == 0
    assert current == json.loads(published(PACKET + p))
ledger = read(PACKET + 'mapping-ledger.json')
coverage = read(PACKET + 'coverage.json')
assert len(ledger['rows']) == 105 and len(ledger['operation_adoptions']) == 8
assert len(coverage['modules']) == coverage['bounded_family_denominator'] == 15
assert coverage['operation_adoptions']['native_user_commands'] == 9
assert {r['mapping_gap'] for r in coverage['extension_adoptions']['interfaces']} == {'X01', 'X02'}
assert not git('diff', PUB, '--', 'fusion', 'integration', 'tests', 'evidence/s07').strip()
assert not git('diff', '--cached', '--name-only').strip()
assert all(sha((ROOT / p).read_bytes()) == sha(published(p)) for p in latest)
offline = read('evidence/s07-closeout/offline-checks.json')
assert offline['status'] == 'PASS' and offline['methods_run'] == 20
assert offline['network_namespace_isolated'] and offline['network_guard_probed']
assert offline['forbidden_network_or_exec_attempts_during_tests'] == []
assert offline['ADDITIONAL_LIVE_GENERATIONS'] == 0 and not offline['real_native_stack_started']
assert all(sha((ROOT / p).read_bytes()) == h for p,h in offline['sources'].items())
assert set(offline['passing_methods']) <= union
modified_docs = ['docs/module-interfaces/runbook.md', PACKET+'README.md', PACKET+'remote-placement.md']
new_docs = [PACKET+'s07-closeout.md', PACKET+'s07-next-workload.md']
link_count = 0
for p in modified_docs + new_docs:
    for target in re.findall(r'\]\(([^)]+)\)', (ROOT / p).read_text()):
        if '://' in target:
            continue
        filename, _, anchor = target.partition('#')
        dest = ((ROOT / p).parent / filename).resolve() if filename else ROOT / p
        if dest == OUT / 'review-state.json':
            continue  # generated below; no recursive hash
        assert dest.is_file(), (p, target)
        if anchor and dest.suffix == '.md':
            headings = [re.sub(r'[^\w\- ]', '', line.lstrip('# ').strip().lower()).replace(' ', '-')
                        for line in dest.read_text().splitlines() if line.startswith('#')]
            assert anchor in headings, (p, target, headings)
        link_count += 1
subprocess.check_call(['git','diff','--check'], cwd=ROOT)
checks = dict(status='PASS', publication=PUB, published_files=len(changed), historical_hashes=len(old['files']),
    versioned_manifest_entries=sum(r['entries'] for r in relationships), totals=totals,
    historical_methods=len(union), historical_final_runs=len(runs),
    final_runtime_manifest_entries_unchanged=len(latest), final_python_files_parsed=sum(p.endswith('.py') for p in latest),
    offline_methods=20, offline_subcase_observations=offline['subcase_observations'],
    original_ledger_data_unchanged=True, historical_evidence_unchanged=True,
    markdown_links_checked=link_count, diff_check='PASS', ADDITIONAL_LIVE_GENERATIONS=0)
save('checks.json', checks)
allowed_modified = set(modified_docs + [PACKET+'coverage.json', PACKET+'mapping-ledger.json'])
actual_modified = set(git('diff','--name-only').decode().splitlines())
assert actual_modified == allowed_modified, actual_modified
new_paths = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
assert all(p in new_docs or p == 'codex_neoclaw_s07_closeout_and_coverage_review.md'
           or p.startswith('evidence/s07-closeout/') for p in new_paths)
paths = sorted(actual_modified | set(new_paths) | {'evidence/s07-closeout/review-state.json'})
files = {p:dict(sha256=sha((ROOT/p).read_bytes()),bytes=(ROOT/p).stat().st_size,
               kind='modified' if p in actual_modified else 'new')
         for p in paths if p != 'evidence/s07-closeout/review-state.json'}
save('review-state.json', dict(schema='s07-closeout-review/1',status='READY_FOR_REVIEW',
    starting_head=PUB, current_head=PUB, parent=PARENT, branch=git('rev-parse','--abbrev-ref','HEAD').decode().strip(),
    starting_worktree=['?? codex_neoclaw_s07_closeout_and_coverage_review.md'],
    publication='S07 was already published; this review remains uncommitted and unstaged',
    commit_performed=False,push_performed=False,live_generation_authorization=0,ADDITIONAL_LIVE_GENERATIONS=0,
    gates={name:'PASS' for name in ('SOURCE_CLOSURE','CAMPAIGN_ACCOUNTING','EVIDENCE_UNITS',
        'COVERAGE_CURRENT','NEXT_WORKLOAD_READY','NO_NEW_GENERATION')},
    next_workload_gate_meaning='Specification ready with explicit pending decisions; NOT_IMPLEMENTED / NOT_RUN / LIVE_AUTHORIZATION_ZERO',
    executed_checks=[
        'PYTHONDONTWRITEBYTECODE=1 artifacts/s03/venv/bin/python evidence/s07-closeout/audit.py',
        'S07_REVIEW_PARENT_NET=$(readlink /proc/self/ns/net) bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --setenv PYTHONDONTWRITEBYTECODE 1 --setenv HF_HUB_OFFLINE 1 --chdir /home/purplezky/work/takopi/fusion-module-interfaces artifacts/s03/venv/bin/python evidence/s07-closeout/offline_checks.py > evidence/s07-closeout/offline-checks.json 2> evidence/s07-closeout/offline-checks.log',
        'git diff --check'],
    checks='evidence/s07-closeout/checks.json',
    exact_commit_ready_change_list=paths,files=files,
    manifest_self_exclusion='review-state.json is listed but excluded from its own hash map; all other review delivery bytes are hashed.',
    unresolved_facts=[
        'Exact rejected live-04 API field: raw response not retained; cache-counter cause remains inference.',
        'Public before/after exports omit context_view; executed assertion/recovery record, not independent exported-field comparison.',
        'Original S06 baseline peer-observation failure cause was not established.',
        'Uncaptured final token usage and independent end-to-end channel timing are unknown.',
        'No independent runtime rebuild or cold clean-cache reproduction.',
        'No combined populated-memory real-model workflow; next workload needs separate authority and disclosure/output decisions.'
    ]))
print(json.dumps(checks))
