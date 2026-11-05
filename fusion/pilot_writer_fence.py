"""Planned synthetic single-writer fencing at the current policy boundary.

The trusted-host authority file is OUTSIDE imported owner state. It must be
mounted read-only independently of owner PVCs, never restored from a snapshot.
Stopping and network-fencing the source are separate required operator gates.
This is not leader election, partition tolerance, or arbitrary backup recovery.
"""
import fcntl
import json
import re
from pathlib import Path
from .contracts import canonical, digest, require, label
from .adapters.chroma_vector import publish

PROFILE = 'planned-synthetic-writer-handover/1'
LIMIT = 64


def hash_value(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'CONFLICT')
    return value


def selection(selected, *, deployed=False):
    require(type(selected) is dict and set(selected) == {'profile', 'authority_file', 'deployment', 'incarnation', 'generation'}, 'UNSUPPORTED_PROFILE')
    require(selected['profile'] == PROFILE and label(selected['deployment']) and label(selected['incarnation']) and
            type(selected['generation']) is int and 1 <= selected['generation'] <= LIMIT + 1, 'UNSUPPORTED_PROFILE')
    require(type(selected['authority_file']) is str and Path(selected['authority_file']).is_absolute(), 'UNAUTHORIZED')
    if deployed: require(selected['authority_file'] == '/writer-authority/current.json', 'UNAUTHORIZED')
    return dict(selected)


def check(policy, method):
    """Current-policy request hook. Old profiles have no implicit new semantics."""
    selected = policy.get('writer_fence')
    if selected is None: return
    selection(selected)
    path = Path(selected['authority_file'])
    # Kubernetes projected Secrets use a ..data symlink. Follow it only inside
    # this separately trusted read-only authority mount, never to an owner PVC.
    require(path.resolve().is_relative_to(path.parent.resolve()) and path.is_file() and path.stat().st_size <= 262144, 'UNAUTHORIZED')
    current = json.loads(path.read_bytes())
    require(current['profile'] == PROFILE and current['synthetic_only'] is True and current['state'] == 'active', 'UNAUTHORIZED')
    require(all(current[k] == selected[k] for k in ('deployment', 'incarnation', 'generation')), 'UNAUTHORIZED')
    require(type(method) is str and method in current['allowed_methods'], 'UNAUTHORIZED')


def startup(settings):
    selected=settings.get('preview',{}).get('pilot',{}).get('writer_fence')
    if selected is not None:
        selection(selected,deployed=True)
        check(dict(writer_fence=selected),'writer.start')


def historical(db,session):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_historical_sessions'").fetchone():return None
    return db.execute('SELECT * FROM pilot_historical_sessions WHERE session=?',(session,)).fetchone()


class Handover:
    """Installed operator extension, serialized by the existing trusted host.

    Evidence callbacks must independently observe the actual task-owned cluster;
    booleans supplied by a browser or model are never proof of fencing. Unit tests
    explicitly use fixture observations and cannot establish cluster handover.
    """
    def __init__(self, authority, authorize, observe, *, imported_roots=(), hook=lambda _: None):
        self.path = Path(authority).absolute()
        self.authorize, self.observe, self.hook = authorize, observe, hook
        require(not self.path.is_symlink(), 'UNAUTHORIZED')
        for root in imported_roots:
            require(not self.path.is_relative_to(Path(root).resolve()), 'UNAUTHORIZED')

    def _lock(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = self.path.with_suffix('.lock').open('a')
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close(); require(False, 'OVERLOADED')
        return lock

    def read(self):
        require(self.path.is_file() and self.path.stat().st_size <= 262144, 'NOT_AVAILABLE')
        value = json.loads(self.path.read_bytes())
        require(value['profile'] == PROFILE and value['synthetic_only'] is True, 'UNSUPPORTED_PROFILE')
        return value

    def initialize(self, deployment, incarnation, methods):
        self.authorize('handover.initialize')
        require(label(deployment) and label(incarnation) and type(methods) is list and 1 <= len(methods) <= 128 and
                len(set(methods)) == len(methods) and all(label(x) for x in methods), 'INVALID_ARGUMENT')
        with self._lock():
            require(not self.path.exists(), 'CONFLICT')
            observed = self.observe('initial', deployment)
            require(observed['task_owned'] is True and observed['fresh_synthetic'] is True and observed['writers'] == 1, 'UNAUTHORIZED')
            value = dict(profile=PROFILE, synthetic_only=True, deployment=deployment, incarnation=incarnation,
                         generation=1, state='active', allowed_methods=sorted(methods), history=[], handover=None)
            publish(self.path, value); self.path.chmod(0o600)
            return value

    def plan(self, identity, replacement, incarnation, checkpoint, closure):
        self.authorize('handover.plan')
        require(label(identity) and label(replacement) and label(incarnation), 'INVALID_ARGUMENT')
        hash_value(checkpoint); hash_value(closure)
        with self._lock():
            value = self.read()
            if value['handover'] is not None:
                prior=value['handover']['intent']
                require(all(prior[k]==v for k,v in dict(identity=identity,replacement=replacement,incarnation=incarnation,checkpoint_sha256=checkpoint,closure_sha256=closure).items()),'CONFLICT')
                return value
            require(value['state'] == 'active' and value['handover'] is None and len(value['history']) < LIMIT, 'CONFLICT')
            require(replacement != value['deployment'] and incarnation != value['incarnation'], 'CONFLICT')
            observation = self.observe('drained-current-checkpoint', value['deployment'])
            require(observation['task_owned'] is True and observation['fresh_synthetic'] is True and
                    observation['admission_closed'] is True and observation['writers'] == 0 and
                    observation['unresolved_effects_fenced'] is True and observation['accounting_verified'] is True and
                    observation['checkpoint_sha256'] == checkpoint and observation['closure_sha256'] == closure,
                    'UNAUTHORIZED')
            intent = dict(identity=identity, original=value['deployment'], original_incarnation=value['incarnation'],
                          source_generation=value['generation'], replacement=replacement, incarnation=incarnation,
                          checkpoint_sha256=checkpoint, closure_sha256=closure)
            value['state'] = 'drained'; value['handover'] = dict(intent=intent, retired=None, activation=None)
            publish(self.path, value); self.hook('after_handover_drain'); return value

    def retire(self, identity):
        self.authorize('handover.retire')
        with self._lock():
            value = self.read(); pending = value['handover']
            require(pending is not None and pending['intent']['identity'] == identity, 'CONFLICT')
            if pending['retired'] is not None: return value
            require(value['state'] == 'drained', 'CONFLICT')
            observed = self.observe('retired-original', value['deployment'])
            require(observed['writers'] == 0 and observed['network_fenced'] is True and observed['service_credentials_revoked'] is True and
                    observed['stale_restart_refused'] is True and observed['authority_outside_imported_state'] is True, 'UNAUTHORIZED')
            pending['retired'] = observed; value['state'] = 'retired'; publish(self.path, value)
            self.hook('after_writer_retirement'); return value

    def activate(self, identity):
        self.authorize('handover.activate')
        with self._lock():
            value = self.read(); pending = value['handover']
            if pending is None:
                require(value['state'] == 'active' and value['history'] and value['history'][-1]['intent']['identity'] == identity, 'CONFLICT')
                return value
            require(pending['intent']['identity'] == identity and value['state'] == 'retired' and pending['retired'] is not None, 'UNAUTHORIZED')
            intent = pending['intent']
            # Recheck the source on every activation attempt. An expired or stale
            # observation never gets promoted into a current retirement decision.
            source = self.observe('retired-original', intent['original'])
            require(source['writers'] == 0 and source['network_fenced'] is True and source['service_credentials_revoked'] is True and
                    source['stale_restart_refused'] is True and source['authority_outside_imported_state'] is True, 'UNAUTHORIZED')
            target = self.observe('qualified-replacement', intent['replacement'])
            require(target['task_owned'] is True and target['fresh_synthetic'] is True and target['writers'] == 0 and
                    target['checkpoint_sha256'] == intent['checkpoint_sha256'] and target['closure_sha256'] == intent['closure_sha256'] and
                    target['accounting_verified'] is True and target['historical_effects_observation_only'] is True and
                    target['execution_authority_imported'] is False, 'UNAUTHORIZED')
            pending['activation'] = target; value['history'].append(pending); value['handover'] = None
            value.update(deployment=intent['replacement'], incarnation=intent['incarnation'], generation=value['generation'] + 1, state='active')
            publish(self.path, value); self.hook('after_writer_activation'); return value

    def rollback(self, *_):
        # New code does not turn an older checkpoint into current authority.
        require(False, 'UNSUPPORTED_OPERATION')
