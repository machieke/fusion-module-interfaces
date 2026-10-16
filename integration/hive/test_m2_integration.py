"""Actual authenticated Hive Programs dispatch; real DeTTa and native PLN.

The operator, scenario, transport driver and failure injections are test inputs.
The native app/Supervisor/PeTTa/plugin loader are the pinned runtime, unchanged.
"""
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time

import pytest

from fusion.contracts import canonical, digest
from integration.hive.test_integration import Caller, ROOT
from integration.m2_scenario import run_generated
from tests.m2_support import MemoryHarness, SCOPE


class MemoryCaller(Caller):
    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('HIVE_')}
        env.update(HIVE_PLUGIN_DIRS=str(ROOT / 'integration/hive/episode_program'),
            FUSION_M2_HIVE_CONFIG=str(self.config), HIVE_OFFLINE='1', HIVE_DATA_DIR=str(self.root / 'hive'))
        self.log = open(self.root / 'native.log', 'a')
        self.process = subprocess.Popen([sys.executable, str(ROOT / 'integration/hive/native_caller.py'),
            str(self.root / 'hive')], cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.log, text=True, start_new_session=True)
        assert self.read() == {'ready': True}, (self.root / 'native.log').read_text()
        return self


@pytest.fixture
def setup(tmp_path, request):
    h = MemoryHarness(tmp_path / 'memory', real=True)
    config = {'private_config': str(h.path), 'grants': []}
    path = tmp_path / 'caller.json'; path.write_bytes(canonical(config)); path.chmod(0o600)
    caller = MemoryCaller(tmp_path, path).start()
    request.addfinalizer(caller.kill); request.addfinalizer(h.close)
    swarm = caller.call('POST', '/api/swarms', {'name': 'Generated private M2 integration'})['body']['id']
    config['grants'] = [{'principal': 'user:operator', 'swarm': swarm, 'credential': h.credential, 'scope': SCOPE}]
    path.write_bytes(canonical(config))
    body = {'swarm_id': swarm, 'action': 'record-generated', 'items': [], 'params': {'seed': secrets.randbits(32)},
            'idempotency_key': 'generated-m2-intent'}
    detail = caller.call('GET', '/api/programs/fusion-episode')
    assert detail['code'] == 200 and detail['body']['source'] == 'plugin-dir', detail
    return h, caller, config, path, body


def act(caller, body):
    response = caller.call('POST', '/api/programs/fusion-episode/act', body)
    assert response['code'] == 200, response
    return response['body']


def local_result(h, body):
    identity = digest(canonical(['user:operator', body['swarm_id'], body['idempotency_key']]))
    return run_generated(h.modules, SCOPE, identity, body['params']['seed'])


def test_actual_dispatch_duplicate_and_native_caller_restart(setup):
    h, caller, config, path, body = setup
    result = act(caller, body)
    assert result['status'] == 'done', result
    assert result['detail'] == {'scenario': 'generated-private-m2', 'story_events': 4, 'retained_alternatives': 2,
        'independent_observations': 2, 'native_revision': True, 'ancestor_added_weight': False}
    private = local_result(h, body)
    assert private['story_decisions'][0]['snapshot']['truth'] is None
    assert private['story_decisions'][0]['numerical'] == 'model-inapplicable'
    assert private['story_snapshot']['truth']['strength'] == '0.75'
    assert abs(float(private['revision']['snapshot']['truth']['confidence']) - 2/3) <= 1e-12
    assert act(caller, body) == result
    caller.kill(); caller.start()
    assert act(caller, body) == result
    assert local_result(h, body) == private
    assert h.episodes.pendingEvidence(private['story'], 16) == ()
    assert h.episodes.pendingEvidence(private['independent'], 16) == ()


@pytest.mark.parametrize('stage', ['after_payload_persist', 'after_episode_commit', 'after_formula', 'after_belief_commit'])
def test_actual_caller_kill_boundaries(setup, stage):
    h, caller, config, path, body = setup
    marker = caller.root / 'pause'
    config.update(test_pause_at=stage, test_marker=str(marker)); path.write_bytes(canonical(config))
    caller.send('POST', '/api/programs/fusion-episode/act', body)
    deadline = time.monotonic() + 40
    while not marker.exists() and caller.process.poll() is None and time.monotonic() < deadline: time.sleep(.01)
    assert marker.exists(), (stage, (caller.root / 'native.log').read_text())
    process = caller.process
    caller.kill(); assert process.returncode == -signal.SIGKILL
    del config['test_pause_at']; path.write_bytes(canonical(config))
    caller.start()
    result = act(caller, body)
    assert result['status'] == 'done', result
    private = local_result(h, body)
    assert private['story_snapshot']['revision'] == 4
    assert private['revision']['snapshot']['revision'] == 3
    assert len(private['revision']['snapshot']['observations']) == 2
    assert act(caller, body) == result
    assert local_result(h, body) == private


def test_live_revocation_and_changed_intent_replay(setup):
    h, caller, config, path, body = setup
    assert act(caller, body)['status'] == 'done'
    changed = {**body, 'params': {'seed': (body['params']['seed'] + 1) % (2**32)}}
    response = act(caller, changed)
    assert response['status'] == 'refused' and response['detail']['error']['code'] == 'CONFLICT', response
    h.config['principals']['owner']['credential'] = 'revoked'; h.save()
    response = act(caller, body)
    assert response['status'] == 'refused' and response['detail']['error']['code'] == 'UNAUTHORIZED', response


def test_native_responses_views_and_traces_have_no_private_payloads_or_identifiers(setup):
    h, caller, config, path, body = setup
    response = act(caller, body); assert response['status'] == 'done', response
    private = local_result(h, body)
    view = caller.call('GET', '/api/programs/fusion-episode')
    public = canonical([response, view]) + (caller.root / 'native.log').read_bytes()
    # Actual Hive state/logs may contain action seed and counters, never episode contents.
    for file in (caller.root / 'hive').rglob('*'):
        if file.is_file(): public += file.read_bytes()
    markers = [f"Generated private source report {body['params']['seed']}".encode()]
    for ref in (private['story'], private['independent']):
        for record in h.episodes.readEpisode(ref, 1, 16)['events']:
            markers += [record['evidence']['event_ref']['digest'].encode(), record['event']['payload']['digest'].encode()]
            markers += [root.encode() for root in record['lineage_roots']]
    for marker in markers: assert marker not in public
    assert not (h.root / 'shared').exists()
    # Body-supplied actor/truth/provenance cannot impersonate the trusted native context.
    injected = {**body, 'params': {**body['params'], 'actor': 'owner', 'truth': [1, .99]}}
    refused = caller.call('POST', '/api/programs/fusion-episode/act', injected)
    assert refused['code'] == 400 and refused['body']['error']['code'] == 'identity_in_request', refused
    refused = act(caller, {**body, 'params': {**body['params'], 'truth': [1, .99]}})
    assert refused['status'] == 'refused', refused
    assert local_result(h, body) == private
