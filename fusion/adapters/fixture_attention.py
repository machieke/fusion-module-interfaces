"""Independent atomic-file C3 fixture; shares DTO validation, never transitions."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
from .. import attention_contracts as c
from ..contracts import canonical, digest, require, validate_ref


class FileAttentionFixture:
    def __init__(self, filename, access, parameters=None, *, hook=lambda stage: None):
        self.path, self.access, self.hook = Path(filename), access, hook
        self.parameters = c.detached(parameters or c.DEFAULT_POLICY)
        self.policy = c.policy(self.parameters)
        self.identity = digest(canonical([self.policy, access.selection()]))
        with self._locked() as data:
            require(data['identity'] == self.identity, 'UNSUPPORTED_PROFILE')
            if not self.path.exists(): self._write(data)

    @contextmanager
    def _locked(self):
        with open(str(self.path) + '.lock', 'a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(self.path.read_bytes()) if self.path.exists() else {'identity': self.identity, 'contexts': {}, 'commands': {}}
            yield data

    def _write(self, data):
        fd, name = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream: stream.write(canonical(data)); stream.flush(); os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY)
            try: os.fsync(directory)
            finally: os.close(directory)
        finally:
            if os.path.exists(name): os.unlink(name)

    def profile(self): return {'profile': c.PROFILE, 'parameters': c.detached(self.parameters), 'policy': self.policy}

    @c.boundary
    def submitStimulus(self, request):
        body = c.stimulus(request, self.policy); scope = request.command.scope_ref
        actor = self.access.authorize(scope, 'submitStimulus'); self.access.authorize(scope, request.kind)
        body['principal'] = actor
        command_id = digest(canonical([actor, scope, request.command.idempotency_key]))
        intent = digest(canonical(body))
        causal_body = dict(body); causal_body.pop('command')
        causal_intent = digest(canonical([scope, causal_body]))
        context_id = c.context_key(scope, request.context)
        with self._locked() as data:
            require(data['identity'] == self.identity, 'UNSUPPORTED_PROFILE')
            if command_id in data['commands']:
                saved = data['commands'][command_id]; require(saved['intent'] == intent, 'CONFLICT'); return saved['result']
            require(len(data['commands']) < self.parameters['max_commands'], 'NOT_AVAILABLE')
            if context_id not in data['contexts']:
                require(len(data['contexts']) < self.parameters['max_contexts'], 'NOT_AVAILABLE')
                data['contexts'][context_id] = {'clock': 0, 'watermark': 0, 'targets': [], 'events': {}}
            context = data['contexts'][context_id]
            saved = context['events'].get(request.cause)
            if saved:
                require(saved['intent'] == causal_intent, 'CONFLICT'); result = saved['result']
            else:
                require(context['clock'] == request.expected_step, 'CONFLICT')
                require(len(context['events']) < self.parameters['max_causes'], 'NOT_AVAILABLE')
                require(request.generation <= self.parameters['max_feedback_generation'], 'INVALID_ARGUMENT')
                if request.kind == 'feedback':
                    prior = context['events'].get(request.parent)
                    require(prior is not None and prior['result']['target'] == request.target, 'INVALID_ARGUMENT')
                    require(request.generation == prior['result']['generation'] + 1, 'INVALID_ARGUMENT')
                current = next((x for x in context['targets'] if x['target'] == request.target), None)
                if current is None:
                    require(len(context['targets']) < self.parameters['max_targets'], 'NOT_AVAILABLE')
                    current = c.zero(request.target); context['targets'].append(current)
                if request.kind == 'feedback':
                    require(request.parent == current['cause'] and request.generation == current['generation'] + 1, 'CONFLICT')
                credit = min(int(request.amount), int(self.parameters['s_max']) - int(current['sti']))
                require(sum(int(x['sti']) for x in context['targets']) + credit <= int(self.parameters['budget']), 'CONFLICT')
                current['sti'] = str(int(current['sti']) + credit)
                if (request.generation >= current['generation'] and
                    (request.generation > current['generation'] or current['cause'] is None or request.cause < current['cause'])):
                    current.update(generation=request.generation, cause=request.cause)
                context['watermark'] += 1
                result = dict(scope_ref=scope, context=request.context, policy=self.policy, target=request.target,
                              cause=request.cause, generation=request.generation, kind=request.kind, parent=request.parent,
                              requested=request.amount, applied=str(credit), saturated=credit < int(request.amount),
                              logical_step=context['clock'], revision=context['watermark'])
                context['events'][request.cause] = {'intent': causal_intent, 'result': result}
            data['commands'][command_id] = {'intent': intent, 'result': result}
            self.access.authorize(scope, 'submitStimulus'); self.access.authorize(scope, request.kind)
            self._write(data)
        self.hook('after_attention_commit'); return result

    @c.boundary
    def select(self, scope, context, eligible, limit):
        c.eligible_refs(scope, context, eligible, limit, self.parameters); self.access.authorize(scope, 'select')
        with self._locked() as data:
            require(data['identity'] == self.identity, 'UNSUPPORTED_PROFILE')
            state = data['contexts'].get(c.context_key(scope, context), {'clock': 0, 'watermark': 0, 'targets': []})
            values = [next((v for v in state['targets'] if v['target'] == ref), c.zero(ref)) for ref in eligible]
            positive = [v for v in values if int(v['sti']) != 0]
            positive.sort(key=lambda v: (-int(v['sti']), canonical(v['target']).decode()))
            return dict(scope_ref=scope, context=context, policy=self.policy, logical_step=state['clock'],
                        revision=state['watermark'], eligible_digest=digest(canonical(eligible)), values=values, ranked=positive[:limit], limit=limit)

    @c.boundary
    def readAttention(self, target, context):
        validate_ref(target, target['scope_ref']); c.identifier(context); self.access.authorize(target['scope_ref'], 'readAttention')
        with self._locked() as data:
            require(data['identity'] == self.identity, 'UNSUPPORTED_PROFILE')
            state = data['contexts'].get(c.context_key(target['scope_ref'], context), {'clock': 0, 'watermark': 0, 'targets': []})
            value = next((v for v in state['targets'] if v['target'] == target), c.zero(target))
            return dict(value=value, logical_step=state['clock'], revision=state['watermark'], policy=self.policy, context=context)

    @c.boundary
    def advance(self, command, context, expected_step, steps):
        c.mutation(command); c.identifier(context); c.integer(expected_step); c.integer(steps, 1, self.parameters['max_advances'])
        scope = command.scope_ref; actor = self.access.authorize(scope, 'advance')
        key = digest(canonical([actor, scope, command.idempotency_key]))
        body = dict(operation='advance', scope=scope, context=context, expected_step=expected_step, steps=steps, policy=self.policy)
        fingerprint = digest(canonical(body)); context_id = c.context_key(scope, context)
        with self._locked() as data:
            require(data['identity'] == self.identity, 'UNSUPPORTED_PROFILE')
            if key in data['commands']:
                require(data['commands'][key]['intent'] == fingerprint, 'CONFLICT'); return data['commands'][key]['result']
            require(len(data['commands']) < self.parameters['max_commands'], 'NOT_AVAILABLE')
            if context_id not in data['contexts']:
                require(len(data['contexts']) < self.parameters['max_contexts'], 'NOT_AVAILABLE')
                data['contexts'][context_id] = {'clock': 0, 'watermark': 0, 'targets': [], 'events': {}}
            value = data['contexts'][context_id]; require(value['clock'] == expected_step, 'CONFLICT'); c.integer(value['clock'] + steps)
            for target in value['targets']: target['sti'] = str(max(0, int(target['sti']) - steps * int(self.parameters['decay'])))
            value['clock'] += steps; value['watermark'] += 1
            result = dict(scope_ref=scope, context=context, policy=self.policy, logical_step=value['clock'], revision=value['watermark'])
            data['commands'][key] = {'intent': fingerprint, 'result': result}
            self.access.authorize(scope, 'advance'); self._write(data)
        self.hook('after_attention_commit'); return result
