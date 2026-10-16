"""C3 SQLite owner: exact integer STI, independent of every cognitive owner."""
from .ports import Mutation, Stimulus
from contextlib import closing
import json
import sqlite3
import time
from . import attention_contracts as c
from .contracts import canonical, digest, require, validate_ref


class AttentionOwner:
    def __init__(self, database, access, parameters=None, *, hook=lambda stage: None, closure=False):
        self.database, self.access, self.hook = str(database), access, hook
        self.parameters = c.detached(parameters or c.DEFAULT_POLICY)
        self.closure = closure
        self.policy = c.policy(self.parameters)
        self.identity = digest(canonical([self.policy, access.selection()]))
        if closure: self.identity = digest(canonical([self.identity, c.CLOSURE_PROFILE]))
        with closing(self._connect()) as db, db:
            db.executescript('CREATE TABLE IF NOT EXISTS meta(identity TEXT); CREATE TABLE IF NOT EXISTS contexts(id TEXT PRIMARY KEY, value TEXT); CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, fingerprint TEXT, value TEXT);')
            prior = db.execute('SELECT identity FROM meta').fetchone()
            if prior: require(prior[0] == self.identity, 'UNSUPPORTED_PROFILE')
            else: db.execute('INSERT INTO meta VALUES(?)', (self.identity,))

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=.5)
        db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA synchronous=FULL')
        return db

    def profile(self): return {'profile': c.CLOSURE_PROFILE if self.closure else c.PROFILE, 'parameters': c.detached(self.parameters), 'policy': self.policy}

    def _load(self, db, scope, context):
        found = db.execute('SELECT value FROM contexts WHERE id=?', (c.context_key(scope, context),)).fetchone()
        return json.loads(found[0]) if found else {'step': 0, 'revision': 0, 'nodes': {}, 'causes': {}}

    def _store(self, db, scope, context, state):
        key = c.context_key(scope, context)
        if not db.execute('SELECT 1 FROM contexts WHERE id=?', (key,)).fetchone():
            require(db.execute('SELECT count(*) FROM contexts').fetchone()[0] < self.parameters['max_contexts'], 'NOT_AVAILABLE')
        db.execute('INSERT OR REPLACE INTO contexts VALUES(?,?)', (key, canonical(state).decode()))

    def _command(self, db, principal, command, body):
        key = digest(canonical([principal, command.scope_ref, command.idempotency_key]))
        fingerprint = digest(canonical(body))
        previous = db.execute('SELECT fingerprint,value FROM commands WHERE id=?', (key,)).fetchone()
        if previous:
            require(previous[0] == fingerprint, 'CONFLICT')
            return key, fingerprint, json.loads(previous[1])
        require(db.execute('SELECT count(*) FROM commands').fetchone()[0] < self.parameters['max_commands'], 'NOT_AVAILABLE')
        return key, fingerprint, None

    @c.boundary
    def submitStimulus(self, request):
        if self.closure:
            c.stimulus(request, self.policy)
            require(request.kind == 'ingress', 'UNSUPPORTED_OPERATION')
        return self._submit(request)

    @c.boundary
    def submitFeedback(self, intent):
        require(self.closure, 'UNSUPPORTED_PROFILE')
        intent = c.feedback_copy(intent, self.policy)
        return self._submit(intent.stimulus, intent.effect_deadline_ms)

    def _submit(self, request, deadline=None):
        body = c.stimulus(request, self.policy)
        request = Stimulus(**{**body, 'command': Mutation(**body['command'])})
        scope = request.command.scope_ref
        operation = 'submitStimulus' if deadline is None else 'submitFeedback'
        principal = self.access.authorize(scope, operation)
        self.access.authorize(scope, request.kind)
        body['principal'] = principal
        if deadline is not None: body['effect_deadline_ms'] = deadline
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            key, fingerprint, replay = self._command(db, principal, request.command, body)
            if replay is not None:
                require('retired' not in replay, 'CONFLICT')
                return replay
            state = self._load(db, scope, request.context)
            semantic = dict(body); del semantic['command']
            cause_fingerprint = digest(canonical([scope, semantic]))
            old = state['causes'].get(request.cause)
            if old:
                require(old['fingerprint'] == cause_fingerprint, 'CONFLICT')
                require('retirement' not in old, 'CONFLICT')
                result = old['receipt']
            else:
                require(deadline is None or time.time()*1000 < deadline, 'DEADLINE_EXCEEDED')
                require(state['step'] == request.expected_step, 'CONFLICT')
                require(len(state['causes']) < self.parameters['max_causes'], 'NOT_AVAILABLE')
                if request.kind == 'feedback':
                    parent = state['causes'].get(request.parent)
                    require(parent is not None and 'receipt' in parent, 'INVALID_ARGUMENT')
                    require(request.generation == parent['receipt']['generation'] + 1, 'INVALID_ARGUMENT')
                    require(parent['receipt']['target'] == request.target, 'INVALID_ARGUMENT')
                require(request.generation <= self.parameters['max_feedback_generation'], 'INVALID_ARGUMENT')
                target = c.target_key(request.target)
                if target not in state['nodes']: require(len(state['nodes']) < self.parameters['max_targets'], 'NOT_AVAILABLE')
                value = state['nodes'].get(target, c.zero(request.target))
                if request.kind == 'feedback':
                    require(request.parent == value['cause'] and request.generation == value['generation'] + 1, 'CONFLICT')
                delta = min(c.units(request.amount), c.units(self.parameters['s_max']) - c.units(value['sti']))
                require(sum(c.units(v['sti']) for v in state['nodes'].values()) + delta <= c.units(self.parameters['budget']), 'CONFLICT')
                # Never erase causal generation with fresh ingress or decay.
                if request.generation > value['generation'] or (request.generation == value['generation'] and (value['cause'] is None or request.cause < value['cause'])):
                    value['generation'], value['cause'] = request.generation, request.cause
                value['sti'] = str(c.units(value['sti']) + delta)
                state['nodes'][target] = value; state['revision'] += 1
                result = {'scope_ref': scope, 'context': request.context, 'policy': self.policy,
                          'target': request.target, 'cause': request.cause, 'generation': request.generation,
                          'kind': request.kind, 'parent': request.parent, 'requested': request.amount,
                          'applied': str(delta), 'saturated': delta < c.units(request.amount),
                          'logical_step': state['step'], 'revision': state['revision']}
                state['causes'][request.cause] = {'fingerprint': cause_fingerprint, 'receipt': result}
                self._store(db, scope, request.context, state)
            self.access.authorize(scope, operation); self.access.authorize(scope, request.kind)
            if old is None: require(deadline is None or time.time()*1000 < deadline, 'DEADLINE_EXCEEDED')
            db.execute('INSERT INTO commands VALUES(?,?,?)', (key, fingerprint, canonical(result).decode()))
        self.hook('after_attention_commit')
        return result

    @c.boundary
    def resolveFeedback(self, intent):
        """Read application or atomically retire; never allocate STI."""
        require(self.closure, 'UNSUPPORTED_PROFILE')
        intent = c.feedback_copy(intent, self.policy); request = intent.stimulus
        scope = request.command.scope_ref
        principal = self.access.authorize(scope, 'resolveFeedback'); self.access.authorize(scope, 'feedback')
        body = c.stimulus(request, self.policy)
        body.update(principal=principal, effect_deadline_ms=intent.effect_deadline_ms)
        semantic = dict(body); del semantic['command']
        cause_fingerprint = digest(canonical([scope, semantic]))
        key = digest(canonical([principal, scope, request.command.idempotency_key]))
        fingerprint = digest(canonical(body))
        result = {'profile': c.RESOLUTION, 'intent_digest': digest(canonical(c.feedback(intent, self.policy))),
                  'outcome': 'pending', 'reason': 'eligible', 'receipt': None, 'retirement': None}
        committed = False
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            command = db.execute('SELECT fingerprint FROM commands WHERE id=?', (key,)).fetchone()
            if command: require(command[0] == fingerprint, 'CONFLICT')
            state = self._load(db, scope, request.context)
            old = state['causes'].get(request.cause)
            if old:
                require(old['fingerprint'] == cause_fingerprint, 'CONFLICT')
                if 'receipt' in old: result.update(outcome='applied', reason=None, receipt=old['receipt'])
                else: result.update(outcome='retired', reason=old['reason'], retirement=old['retirement'])
            else:
                parent = state['causes'].get(request.parent)
                require(parent is not None and 'receipt' in parent, 'INVALID_ARGUMENT')
                require(parent['receipt']['target'] == request.target and
                        request.generation == parent['receipt']['generation'] + 1 and
                        request.generation <= self.parameters['max_feedback_generation'], 'INVALID_ARGUMENT')
                require(request.expected_step <= state['step'], 'CONFLICT')
                node = state['nodes'].get(c.target_key(request.target), c.zero(request.target))
                reason = ('expired' if time.time()*1000 >= intent.effect_deadline_ms else
                          'obsolete-step' if state['step'] != request.expected_step else
                          'obsolete-parent' if node['cause'] != request.parent or node['generation'] + 1 != request.generation else None)
                if reason is not None:
                    require(len(state['causes']) < self.parameters['max_causes'], 'NOT_AVAILABLE')
                    require(command is not None or db.execute('SELECT count(*) FROM commands').fetchone()[0] < self.parameters['max_commands'], 'NOT_AVAILABLE')
                    state['revision'] += 1
                    retirement = {'logical_step': state['step'], 'revision': state['revision']}
                    state['causes'][request.cause] = {'fingerprint': cause_fingerprint, 'retirement': retirement, 'reason': reason}
                    self._store(db, scope, request.context, state)
                    db.execute('INSERT OR IGNORE INTO commands VALUES(?,?,?)',
                               (key, fingerprint, canonical({'retired': True, 'cause': request.cause}).decode()))
                    result.update(outcome='retired', reason=reason, retirement=retirement)
                    committed = True
            self.access.authorize(scope, 'resolveFeedback'); self.access.authorize(scope, 'feedback')
        if committed: self.hook('after_feedback_retirement_commit')
        self.hook('after_feedback_resolution')
        return result

    @c.boundary
    def select(self, scope, context, eligible, limit):
        require(type(eligible) is tuple)
        eligible = tuple(c.detached(eligible))
        c.eligible_refs(scope, context, eligible, limit, self.parameters)
        self.access.authorize(scope, 'select')
        with closing(self._connect()) as db: state = self._load(db, scope, context)
        values = [state['nodes'].get(c.target_key(ref), c.zero(ref)) for ref in eligible]
        return {'scope_ref': scope, 'context': context, 'policy': self.policy,
                'logical_step': state['step'], 'revision': state['revision'],
                'eligible_digest': digest(canonical(eligible)), 'values': values, 'limit': limit,
                'ranked': sorted((v for v in values if c.units(v['sti']) > 0), key=lambda v: (-c.units(v['sti']), c.target_key(v['target'])))[:limit]}

    @c.boundary
    def readAttention(self, target, context):
        target = c.detached(target)
        validate_ref(target, target['scope_ref']); c.identifier(context)
        self.access.authorize(target['scope_ref'], 'readAttention')
        with closing(self._connect()) as db: state = self._load(db, target['scope_ref'], context)
        return {'value': state['nodes'].get(c.target_key(target), c.zero(target)), 'logical_step': state['step'],
                'revision': state['revision'], 'policy': self.policy, 'context': context}

    @c.boundary
    def advance(self, command, context, expected_step, steps):
        c.mutation(command); c.identifier(context); c.integer(expected_step); c.integer(steps, 1, self.parameters['max_advances'])
        scope = command.scope_ref; principal = self.access.authorize(scope, 'advance')
        body = {'operation': 'advance', 'scope': scope, 'context': context, 'expected_step': expected_step, 'steps': steps, 'policy': self.policy}
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            key, fingerprint, replay = self._command(db, principal, command, body)
            if replay is not None: return replay
            state = self._load(db, scope, context); require(state['step'] == expected_step, 'CONFLICT')
            c.integer(state['step'] + steps)
            for value in state['nodes'].values(): value['sti'] = str(max(0, c.units(value['sti']) - steps * c.units(self.parameters['decay'])))
            state['step'] += steps; state['revision'] += 1
            result = {'scope_ref': scope, 'context': context, 'policy': self.policy, 'logical_step': state['step'], 'revision': state['revision']}
            self._store(db, scope, context, state); self.access.authorize(scope, 'advance')
            db.execute('INSERT INTO commands VALUES(?,?,?)', (key, fingerprint, canonical(result).decode()))
        self.hook('after_attention_commit')
        return result
