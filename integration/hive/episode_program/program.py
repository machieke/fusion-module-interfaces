"""Narrow sibling Programs plugin for the verified native Hive 34b0fb3 seam.

Generated scenario only. Actor identity comes from Hive; operator config maps
it to local private authority. No M1 shared-test ingress or private result dump.
"""
import json
import os
from pathlib import Path
import signal
import sqlite3

from fusion.contracts import ContractError, canonical, digest, require
from fusion.private import open_private
from integration.m2_scenario import run_generated


def describe():
    return {'contract': '0.1', 'kinds': [{'id': 'episode', 'label': 'Private generated episode', 'role': 'evidence'}],
        'relations': [], 'actions': [
        {'id': 'record-generated', 'label': 'Record private generated episode',
         'params': {'seed': 'integer 0..4294967295; generated data only'}}]}


def view(ctx, focus=None, stage=None):
    return {'revision': '1', 'items': [], 'links': []}


def act(ctx, action, items, params):
    try:
        actor, command = ctx.actor or {}, ctx.command or {}
        require(not ctx.read_only and actor.get('kind') == 'person' and actor.get('route') == 'operator'
                and actor.get('swarm_id') == ctx.swarm_id, 'UNAUTHORIZED')
        require(action == 'record-generated' and not items)
        require(set(params) <= {'seed', 'base_revision'} and type(params.get('seed')) is int
                and 0 <= params['seed'] <= 4294967295 and params.get('base_revision') is None)
        key = command.get('idempotency_key')
        require(isinstance(key, str) and 1 <= len(key) <= 120)
        config = json.loads(Path(os.environ['FUSION_M2_HIVE_CONFIG']).read_text())
        grants = [g for g in config['grants'] if g['principal'] == actor.get('principal') and g['swarm'] == ctx.swarm_id]
        require(len(grants) == 1, 'UNAUTHORIZED')
        grant = grants[0]
        def hook(stage):
            # Test-only operator input. The public action cannot request a pause.
            if config.get('test_pause_at') == stage:
                Path(config['test_marker']).write_text(stage)
                os.kill(os.getpid(), signal.SIGSTOP)
        modules = open_private(config['private_config'], grant['credential'], grant['scope'], hook=hook)
        identity = digest(canonical([actor['principal'], ctx.swarm_id, key]))
        result = run_generated(modules, grant['scope'], identity, params['seed'], hook=hook)
        return {'status': 'done', 'receipt': {'state': 'committed', 'id': key}, 'detail': {
            'scenario': 'generated-private-m2', 'story_events': len(result['story_snapshot']['observations']),
            'retained_alternatives': len(result['story_snapshot']['alternatives']),
            'independent_observations': len(result['revision']['snapshot']['observations']),
            'native_revision': result['revision']['numerical'] == 'revised',
            'ancestor_added_weight': False}}
    except ContractError as error:
        return {'status': 'error' if error.wire()['retryable'] else 'refused', 'detail': {'error': error.wire()}}
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        return {'status': 'error', 'detail': {'error': ContractError('NOT_AVAILABLE').wire()}}
