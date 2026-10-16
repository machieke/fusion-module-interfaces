"""Real isolated F1R3node + native Hive + real DeTTa; generated policy/counterparty.

Run through verify_m4. Deterministic pauses/SIGKILL are injected faults, not providers.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import secrets
import signal
import sqlite3
import subprocess
import sys
import time
import uuid
import pytest
from fusion.adapters.f1r3_m4 import DESCRIPTOR, PROFILE
from fusion.contracts import canonical, digest
from fusion.ports import Mutation
from fusion.registry import descriptor_wire
from integration.chain.runtime import Node
from integration.hive.test_integration import Caller, ROOT, act as inspect_act, complete, journal
from tests import support
from tests.m2_support import MemoryHarness, SCOPE


class ChainCaller(Caller):
    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('HIVE_')}
        env.update(HIVE_PLUGIN_DIRS=os.pathsep.join(str(ROOT / 'integration/hive' / p) for p in ('program', 'commitment')),
            FUSION_HIVE_CONFIG=str(self.config), HIVE_OFFLINE='1', HIVE_DATA_DIR=str(self.root / 'hive'))
        self.log = open(self.root / 'native.log', 'a')
        self.process = subprocess.Popen([sys.executable, str(ROOT / 'integration/hive/native_caller.py'), str(self.root / 'hive')],
            cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log, text=True, start_new_session=True)
        assert self.read() == {'ready': True}, (self.root / 'native.log').read_text()
        return self


@pytest.fixture(scope='session')
def node(request):
    output = Path(os.environ['M4_OUTPUT'])
    real = Node(output / 'private-node', os.environ['M4_NODE_SOURCE'], os.environ['M4_NODE_BINARY'])
    request.addfinalizer(real.stop)
    startup = real.start()
    (output / 'isolation.json').write_bytes(canonical({**real.isolation, 'startup_seconds': startup}) + b'\n')
    return real


@pytest.fixture
def setup(tmp_path, request, node):
    support.BINARY = Path(os.environ['M2_DETTA_BINARY'])
    h = support.Harness(root=tmp_path / 'fusion', atom_provider='detta')
    path = tmp_path / 'caller.json'
    config = {'service_config': str(h.path), 'receipts': str(tmp_path / 'inspect.db'),
              'descriptors': [descriptor_wire(d) for d in h.a.binding.selected.values()], 'grants': []}
    path.write_bytes(canonical(config)); path.chmod(0o600)
    caller = ChainCaller(tmp_path, path).start()
    request.addfinalizer(caller.kill); request.addfinalizer(h.close)
    swarm = caller.call('POST', '/api/swarms', {'name': 'Explicitly shareable M4 generated workflow'})['body']['id']
    config['grants'] = [{'principal': 'user:operator', 'swarm': swarm, 'credential': h.a.binding.credential,
        'scope': 'shared-test', 'reply_route': 'reply-A', 'counterparty': 'reply-B'}]
    operation = 'generated-m4-' + str(uuid.uuid4())
    config['commitment'] = {'original_command': operation, 'principal': 'user:operator', 'swarm': swarm,
        'seed': 12, 'expires_at_ms': time.time_ns() // 1000000 + 3600000,
        'operation': operation, 'chain': node.identity, 'endpoint': node.api.endpoint, 'signer': node.public,
        'signer_file': str(node.secret_file), 'protobuf': str(node.directory / 'signing_pb2.py'),
        'protobuf_sha256': digest((node.directory / 'signing_pb2.py').read_bytes()),
        'descriptor': descriptor_wire(DESCRIPTOR), 'limits': {'phloPrice': 1, 'phloLimit': 10000000, 'validAfterBlockNumber': 0},
        'journal': str(tmp_path / 'chain.db'), 'progress': str(tmp_path / 'chain-progress.db')}
    path.write_bytes(canonical(config))
    body = {'swarm_id': swarm, 'action': 'inspect', 'items': [], 'params': {'seed': 12}, 'idempotency_key': operation}
    assert caller.call('GET', '/api/programs/fusion-commitment')['body']['source'] == 'plugin-dir'
    return h, caller, config, path, body, node


def chain_body(body, action):
    return {'swarm_id': body['swarm_id'], 'action': action, 'items': [],
            'params': {'original_command': body['idempotency_key']}}


def chain_act(caller, body, action):
    response = caller.call('POST', '/api/programs/fusion-commitment/act', chain_body(body, action))
    assert response['code'] == 200, response
    return response['body']


def accepted(setup):
    h, caller, config, path, body, node = setup
    began = time.monotonic()
    assert inspect_act(caller, body)['status'] == 'started'
    shared = h.b.poll()  # Fixture counterparty; no second native agent is claimed.
    assert b'explicitly shareable generated sample' in h.b.retrieve(shared['body']['ref'])
    result = complete(h, caller, body)
    assert journal(config)[0][2] == 1 and h.a.poll() is None
    return result, round(time.monotonic() - began, 3)


def intent(config):
    with sqlite3.connect(config['commitment']['journal']) as db:
        rows = db.execute('SELECT plan,signed,read_name,receipt FROM m4_intent').fetchall()
        assert len(rows) == 1
        return {'plan': json.loads(rows[0][0]), 'signed': json.loads(rows[0][1]), 'read_name': rows[0][2],
                'receipt': json.loads(rows[0][3]) if rows[0][3] else None}


def finalized(caller, body, node):
    began = time.monotonic()
    node.propose()
    samples, inclusion_seconds = [], None
    for _ in range(120):
        current = chain_act(caller, body, 'observe')
        samples.append(current)
        observation = current.get('detail', {}).get('chain', {})
        if observation.get('inclusion_block') and inclusion_seconds is None:
            inclusion_seconds = round(time.monotonic() - began, 3)
        if observation.get('effect_finality') == 'finalized':
            return current, {'inclusion_first_observed_seconds': inclusion_seconds,
                'finality_first_observed_seconds': round(time.monotonic() - began, 3), 'observation_calls': len(samples)}
        assert observation.get('effect_finality') != 'rejected', current
        if time.monotonic() - began >= 180:
            break
        time.sleep(.5)
    raise TimeoutError('OBSERVATION_TIMEOUT: deploy-effect finality, max 120 calls / 180 seconds')


def pause_kill(caller, path, config, body, stage, chain=True):
    marker = caller.root / (stage + '.marker')
    fault = {'test_pause_at': stage, 'test_marker': str(marker)}
    if chain: config['chain_test'] = fault
    else: config.update(fault)
    path.write_bytes(canonical(config))
    caller.send('POST', '/api/programs/' + ('fusion-commitment' if chain else 'fusion-inspect') + '/act', body)
    deadline = time.monotonic() + 45
    while not marker.exists() and caller.process.poll() is None and time.monotonic() < deadline:
        time.sleep(.02)
    assert marker.exists(), (stage, (caller.root / 'native.log').read_text())
    process = caller.process
    caller.kill()
    assert process.returncode == -signal.SIGKILL
    config.pop('chain_test', None); config.pop('test_pause_at', None); config.pop('test_marker', None)
    path.write_bytes(canonical(config)); caller.start()


def node_finalized(node, signature):
    node.propose()
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        observed = node.api.observe(signature)
        if observed.effect_finality == 'finalized': return observed
        assert observed.effect_finality != 'rejected', observed
        time.sleep(.5)
    raise TimeoutError('OBSERVATION_TIMEOUT: node finality before native recovery, 120 seconds')


def recovery_record(stage, setup, signed, seconds, **extra):
    h, caller, config, path, body, node = setup
    after = intent(config)
    record = {'stage': stage, 'fault': 'actual native caller/adapter SIGKILL', 'exit': -9,
        'operation': config['commitment']['operation'], 'deploy_id': signed['signature'],
        'signed_bytes_before': digest(canonical(signed)), 'signed_bytes_after': digest(canonical(after['signed'])),
        'timestamp_before': signed['data']['timestamp'], 'timestamp_after': after['signed']['data']['timestamp'],
        'counts': h.counts(), 'recovery_seconds': round(seconds, 3), **extra}
    assert record['signed_bytes_before'] == record['signed_bytes_after']
    (Path(os.environ['M4_OUTPUT']) / ('recovery-' + stage + '.json')).write_bytes(canonical(record) + b'\n')


def test_same_artifact_node_restart_outage_readonly_and_privacy(setup):
    h, caller, config, path, body, node = setup
    memory = MemoryHarness(caller.root / 'private-cognition', real=True)
    canary = 'PRIVATE-M4-' + secrets.token_hex(16)
    payload = memory.atoms.create(Mutation(SCOPE, 'canary'), 'text/plain', canary.encode())['ref']
    episode = memory.episode()
    event = memory.event(numeric=False); event['payload'] = payload
    memory.append(episode, event)
    private_events = memory.episodes.readEpisode(episode, 1, 16)
    markers = [canary, digest(canary.encode()), payload['digest'], episode['id'], digest(canonical(episode))]
    for entry in private_events['events']:
        markers.append(entry['evidence']['event_ref']['digest']); markers.extend(entry['lineage_roots'])
    result, offchain_seconds = accepted(setup)
    began = time.monotonic()
    submission = chain_act(caller, body, 'commit')
    assert submission['status'] == 'started', submission
    submit_seconds = round(time.monotonic() - began, 3)
    saved = intent(config)
    final, timing = finalized(caller, body, node)
    assert final['detail']['approval']['result_ref'] == result['detail']['result']['ref']
    assert final['detail']['chain']['evidence']['value']['digest'] == digest(h.a.retrieve(result['detail']['result']['ref']))
    assert chain_act(caller, body, 'commit')['detail']['chain'] == submission['detail']['chain']
    caller.kill(); caller.start()
    assert chain_act(caller, body, 'observe')['status'] == 'done'
    node.stop(kill=True)
    unavailable = chain_act(caller, body, 'observe')
    assert unavailable['status'] == 'started' and unavailable['detail']['result']['acknowledged'] is True
    assert unavailable['detail']['chain']['effect_finality'] == 'not-observed'
    assert h.counts() == {'jobs': 1, 'outbox': 1, 'messages': 2, 'atoms': 2}
    restart_seconds = node.start()
    again = chain_act(caller, body, 'observe')
    assert again['status'] == 'done' and again['detail']['chain']['deploy_id'] == saved['signed']['signature']
    assert intent(config)['signed'] == saved['signed']
    output = Path(os.environ['M4_OUTPUT'])
    trace = {'classification': 'real native Hive, real DeTTa, real isolated F1R3node; generated inputs; fixture counterparty',
        'command': body['idempotency_key'], 'operation': config['commitment']['operation'],
        'input': final['detail']['result']['input'], 'result': final['detail']['result'],
        'approved': final['detail']['approval'], 'profile': PROFILE, 'chain_instance': node.identity,
        'signed': saved['signed'], 'read_name': saved['read_name'], 'submission': submission['detail']['chain'],
        'final_observation': final['detail']['chain'], 'restart_observation': again['detail']['chain'],
        'outage': unavailable['detail']['chain'], 'counts': h.counts(),
        'timing': {'storage_worker_acceptance_seconds': offchain_seconds, 'signing_and_submission_seconds': submit_seconds,
                   'signing_seconds': submission['detail']['chain']['evidence']['signing_seconds'],
                   'submission_rpc_seconds': submission['detail']['chain']['evidence']['submission_rpc_seconds'],
                   **timing, 'same_genesis_restart_seconds': restart_seconds},
        'bytes': {'input': len(h.a.retrieve(result['detail']['input']['ref'])),
                  'result': len(h.a.retrieve(result['detail']['result']['ref'])), 'signed_request': len(canonical(saved['signed']))}}
    trace_path = output / 'same-artifact.json'; trace_path.write_bytes(canonical(trace) + b'\n')
    read_credential = secrets.token_hex(24)
    h.config['principals']['m4-reader'] = {'credential': read_credential, 'scopes': {'shared-test': ['atom.storage.get']}}; h.save()
    access = caller.root / 'read-access.json'
    access.write_bytes(canonical({'service_config': str(h.path), 'read_credential': read_credential, 'endpoint': node.api.endpoint})); access.chmod(0o600)
    hidden = node.secret_file.with_suffix('.hidden'); node.secret_file.rename(hidden)
    try:
        readback = subprocess.run([sys.executable, str(ROOT / 'scripts/readback_m4.py'), str(access), str(trace_path)],
            check=True, capture_output=True, text=True, timeout=30)
        assert chain_act(caller, body, 'observe')['status'] == 'done'
    finally:
        hidden.rename(node.secret_file)
    readonly = json.loads(readback.stdout)
    (output / 'readback.json').write_bytes(canonical(readonly) + b'\n')
    public = canonical([trace, readonly, final, again, unavailable]) + (caller.root / 'native.log').read_bytes()
    for marker in [*markers, str(memory.path), str(node.secret_file), node.secret_file.read_text(), h.a.binding.credential, read_credential]:
        assert marker.encode() not in public
    assert str(caller.root).encode() not in canonical([trace, readonly, final, again, unavailable])
    (output / 'privacy.json').write_bytes(canonical({'status': 'PASS', 'private_owner': 'real private episodes and payloads / real DeTTa',
        'canary_checks': len(markers), 'no_private_values_or_identifying_derivatives_exported': True,
        'no_keys_credentials_or_private_paths_in_public_trace': True}) + b'\n')


def test_native_caller_dies_after_acceptance_before_chain(setup):
    h, caller, config, path, body, node = setup
    assert inspect_act(caller, body)['status'] == 'started'
    h.command('work'); h.command('flush')
    pause_kill(caller, path, config, body, 'after_acceptance', chain=False)
    began = time.monotonic()
    before = journal(config)[0]
    assert before[1] is not None and before[2] == 0
    result = inspect_act(caller, body)
    assert result['status'] == 'done' and result['detail'] == json.loads(before[1])
    assert chain_act(caller, body, 'commit')['status'] == 'started'
    final, _ = finalized(caller, body, node)
    assert final['detail']['approval']['result_ref'] == result['detail']['result']['ref']
    assert h.counts() == {'jobs': 1, 'outbox': 1, 'messages': 2, 'atoms': 2}
    recovery_record('after_acceptance', setup, intent(config)['signed'], time.monotonic() - began,
                    result_ref=result['detail']['result']['ref'], accepted_before_kill=True, acknowledgment_recovered=True)


@pytest.mark.parametrize('stage', ['after_signed_intent', 'after_node_submission'])
def test_real_adapter_kill_and_lost_submission_response(setup, stage):
    h, caller, config, path, body, node = setup
    accepted(setup)
    pause_kill(caller, path, config, chain_body(body, 'commit'), stage)
    saved = intent(config)
    assert saved['receipt'] is None
    if stage == 'after_node_submission':
        # Force the uncertain deploy to be finalized before its response is recovered.
        node_finalized(node, saved['signed']['signature'])
    began = time.monotonic()
    secret = node.secret_file.with_suffix('.hidden'); node.secret_file.rename(secret)
    try:
        result = chain_act(caller, body, 'commit')
        assert result['detail']['chain']['deploy_id'] == saved['signed']['signature'], result
        final, _ = finalized(caller, body, node)
    finally:
        secret.rename(node.secret_file)
    assert final['status'] == 'done' and intent(config)['signed'] == saved['signed']
    assert h.counts() == {'jobs': 1, 'outbox': 1, 'messages': 2, 'atoms': 2}
    recovery_record(stage, setup, saved['signed'], time.monotonic() - began,
                    signer_unavailable_during_replay=True, effect_finality=final['detail']['chain']['effect_finality'])


def test_native_observation_kill_before_caller_progress(setup):
    h, caller, config, path, body, node = setup
    accepted(setup)
    assert chain_act(caller, body, 'commit')['status'] == 'started'
    saved = intent(config)['signed']
    node_finalized(node, saved['signature'])
    # This is the first native observation: no test edits or resets any owner state.
    pause_kill(caller, path, config, chain_body(body, 'observe'), 'after_observation_before_progress')
    with sqlite3.connect(config['commitment']['progress']) as db:
        assert db.execute('SELECT observation FROM progress').fetchone()[0] is None
    began = time.monotonic()
    again = chain_act(caller, body, 'observe')
    assert again['status'] == 'done' and again['detail']['chain']['deploy_id'] == saved['signature']
    assert intent(config)['signed'] == saved and h.counts()['jobs'] == 1
    recovery_record('after_observation_before_progress', setup, saved, time.monotonic() - began,
                    effect_finality=again['detail']['chain']['effect_finality'], progress_was_uncommitted=True)


def test_native_live_authority_binding_and_refused_exports(setup):
    h, caller, config, path, body, node = setup
    accepted(setup)
    before = deepcopy(config)
    assert chain_act(caller, body, 'commit')['status'] == 'started'
    signed = intent(config)['signed']
    for params in ({'original_command': body['idempotency_key'], 'digest': 'a' * 64},
                   {'original_command': body['idempotency_key'], 'payload': 'private'},
                   {'original_command': body['idempotency_key'], 'approval_record': 'invented'},
                   {'original_command': 'another-command'}):
        request = {**chain_body(body, 'commit'), 'params': params}
        response = caller.call('POST', '/api/programs/fusion-commitment/act', request)
        assert response['code'] == 400 or response['body']['status'] == 'refused', response
    for field, value, code in (('expires_at_ms', 1, 'UNAUTHORIZED'), ('principal', 'another', 'UNAUTHORIZED'),
        ('seed', 13, 'UNAUTHORIZED'), ('journal', str(caller.root / 'different-chain.db'), 'CONFLICT'),
        ('chain', {**node.identity, 'genesis': 'f' * 64}, 'CONFLICT'),
        ('descriptor', {**descriptor_wire(DESCRIPTOR), 'implementation_version': '9.0.0'}, 'UNSUPPORTED_PROFILE')):
        config['commitment'][field] = value; path.write_bytes(canonical(config))
        response = chain_act(caller, body, 'commit')
        assert response['status'] == 'refused' and response['detail']['error']['code'] == code, response
        config = deepcopy(before)
    path.write_bytes(canonical(config))
    h.config['principals']['A']['scopes'] = {}; h.save()
    for action in ('commit', 'observe'):
        response = chain_act(caller, body, action)
        assert response['status'] == 'refused' and response['detail']['error']['code'] == 'UNAUTHORIZED', response
    assert intent(config)['signed'] == signed and h.counts()['jobs'] == 1
