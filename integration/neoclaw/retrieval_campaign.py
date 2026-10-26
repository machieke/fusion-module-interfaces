"""Trusted-local, four-slot campaign gate. No model imports or network activity.

The plan is immutable; approval is separately supplied by the user/operator.
The ledger only records campaign attempts, never replaces owner results.
"""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from fusion.contracts import canonical, digest

BASELINE = '9816873d5bb605c9c03be5f65baef7410c8cce0f'
ROOT = Path(__file__).resolve().parents[2]


def read(path): return json.loads(Path(path).read_bytes())
def require(ok, message):
    if not ok: raise RuntimeError(message)
def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()
def atomic(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix('.pending')
    with open(tmp, 'wb') as f:
        os.chmod(tmp, 0o600); f.write(canonical(value)); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)
    fd = os.open(path.parent, os.O_RDONLY)
    try: os.fsync(fd)
    finally: os.close(fd)
def normalized_config(path):
    cfg = read(path)
    # The only predeclared activation-time substitution, persisted once.
    if 'model_completion' in cfg: cfg['model_completion']['expires_ms'] = 'AT_AUTHORIZED_ACTIVATION'
    return digest(canonical(cfg))


def plan(path):
    path = Path(path).resolve(); data = path.read_bytes(); value = json.loads(data)
    require(data == canonical(value), 'NONCANONICAL_MANIFEST')
    actual = digest(data)
    require(path.with_suffix('.sha256').read_text().strip() == actual, 'MANIFEST_DIGEST_MISMATCH')
    require(value['schema'] == 'retrieval-grounded-campaign/1', 'CAMPAIGN_SCHEMA')
    require(len(value['sessions']) == 2 and len(value['slots']) == 4, 'CAMPAIGN_LIMITS')
    return value, actual


def inspect(path, *, assets=True):
    value, checksum = plan(path); drift = []
    for name, expected in value['sources'].items():
        try: actual = sha(ROOT/name)
        except OSError: actual = None
        if actual != expected: drift.append(name)
    if assets:
        for item in value['bindings']:
            try: actual = normalized_config(item['path']) if item.get('normalized') else sha(item['path'])
            except (OSError, ValueError): actual = None
            if actual != item['sha256']: drift.append(item['path'])
    return dict(campaign_id=value['campaign_id'], manifest_sha256=checksum, drift=drift,
                state='AWAITING_LIVE_AUTHORIZATION', generative_runtime_availability='NOT_CHECKED')


def approve(path, approval_path, *, recorded=False, assets=True, now_ms=None):
    # Check separate authority BEFORE any backend construction, reservation,
    # readiness or process startup. An enabled flag cannot satisfy this schema.
    value, checksum = plan(path)
    require(value['kind'] == ('recorded-qualification' if recorded else 'live'), 'WRONG_CAMPAIGN_KIND')
    require(approval_path is not None and Path(approval_path).is_file(), 'AWAITING_LIVE_AUTHORIZATION')
    approval = read(approval_path)
    require(approval.get('authority') == ('TEST_ONLY_RECORDED_RESPONSES' if recorded else 'EXPLICIT_USER_APPROVAL'), 'INVALID_AUTHORITY')
    require(approval.get('campaign_id') == value['campaign_id'] and approval.get('manifest_sha256') == checksum, 'APPROVAL_MISMATCH')
    require(approval.get('slots') == [x['name'] for x in value['slots']], 'APPROVAL_SLOT_MISMATCH')
    require(approval.get('max_generations') == 4 and approval.get('user_statement'), 'INVALID_APPROVAL')
    now_ms = now_ms or time.time_ns()//1_000_000
    require(approval['not_before_ms'] <= now_ms < approval['expires_ms'], 'APPROVAL_EXPIRED')
    require(0 < approval['expires_ms'] - approval['not_before_ms'] <= 3600000, 'APPROVAL_WINDOW')
    if recorded:
        from .preparation_guard import verify
        verify(approval['parent_namespace'])
    else:
        require(not os.environ.get('FUSION_PREP_PARENT_NET'), 'LIVE_DISABLED_BY_PREPARATION_GUARD')
    report = inspect(path, assets=assets)
    require(not report['drift'], 'FROZEN_INPUT_DRIFT: '+str(report['drift']))
    if not recorded and assets:
        # Offline asset checks only. Runtime availability is checked later by
        # the original backend, and only after this authority succeeds.
        for item in value['runtime_required_files']:
            require(Path(item['path']).is_file() and sha(item['path']) == item['sha256'], 'REQUIRED_RUNTIME_ASSET: '+item['path'])
    return value, approval


@contextlib.contextmanager
def locked(root):
    root = Path(root); root.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(root/'operator.lock', 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX); yield root


def ledger(path):
    value, checksum = plan(path); root = Path(value['execution_root'])
    state = read(root/'ledger.json')
    require(state['manifest_sha256'] == checksum and state['campaign_id'] == value['campaign_id'], 'LEDGER_IDENTITY')
    claims = {p.stem:read(p) for p in (root/'claims').glob('*.json')}
    # Claims are write-once fsynced records. The ledger is a projection, never
    # a counter whose reset grants authority. A crash may leave a claim ahead
    # of its projection; reconcile monotonically, never erase a claim.
    require(set(state['started']) <= set(claims), 'LEDGER_ROLLBACK_OR_TAMPER')
    for key, old in state['started'].items(): require(old == claims[key], 'LEDGER_TAMPER')
    require(set(claims) <= {x['id'] for x in value['slots']}, 'UNPLANNED_SLOT')
    state['started'] = claims
    return state


def claim(path, approval_path, accepted, *, recorded):
    value, _ = approve(path, approval_path, recorded=recorded, assets=False)
    expected = [x for x in value['slots'] if x['id'] == accepted['id']]
    require(len(expected) == 1, 'UNPLANNED_SLOT'); slot = expected[0]
    require((slot['session'],slot['slot']) == (accepted['session'],accepted['slot']), 'SLOT_MISMATCH')
    with locked(value['execution_root']) as root:
        state = ledger(path)
        require(accepted['id'] not in state['started'], 'EVALUATION_ALREADY_SPENT')
        record = dict(id=accepted['id'], name=slot['name'], intent_sha256=digest(canonical(accepted)),
                      deadline_ms=accepted['deadline_ms'], observed_ms=time.time_ns()//1_000_000,
                      boundary='RECORDED_RESPONSE' if recorded else 'REAL_BACKEND_INVOCATION')
        claim_path = root/'claims'/(accepted['id']+'.json'); claim_path.parent.mkdir(exist_ok=True, mode=0o700)
        require(not claim_path.exists(), 'EVALUATION_ALREADY_SPENT')
        atomic(claim_path, record); state['started'][accepted['id']] = record; atomic(root/'ledger.json', state)


def initialize(path):
    value, checksum = plan(path); root = Path(value['execution_root'])
    require(not (root/'ledger.json').exists(), 'EXISTING_EXECUTION_STATE')
    atomic(root/'ledger.json', dict(campaign_id=value['campaign_id'],manifest_sha256=checksum,
        started={}, sessions={}, authorized_live_generations=0, reserved_live_generations=0,
        observed_generative_backend_calls=0, captured_live_responses=0))


def sources():
    # Execution-affecting Python, native overlays and versioned locks. Exact
    # worktree identities; later documentation commits do not rewrite tests.
    paths = list((ROOT/'fusion').rglob('*.py'))+list((ROOT/'integration/neoclaw').glob('*.py'))
    paths += list((ROOT/'integration/neoclaw').glob('*.json'))+[ROOT/'tests/neoclaw_support.py']
    paths += list((ROOT/'tests').glob('test_retrieval_runner*.py'))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
