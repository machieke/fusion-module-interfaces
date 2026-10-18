"""Local S01 facade: durable caller identity/budget/receipt, independent of placement."""
import json
from pathlib import Path
import sqlite3
import time

from .contracts import ContractError, canonical, decode, digest, label, require
from . import neoclaw_contracts as c
from .neoclaw_transport import binding, json_loads
from .registry import descriptor_read, selection_token


class Caller:
    def __init__(self, config_file, hook=lambda _: None, transport=None, invocation=None):
        self.application_invocation = invocation is not None
        self.config = json.loads(Path(config_file).read_text())
        # Trusted local application context; never populated from tool/model text.
        if invocation is not None:
            c.fields(invocation, 'request_id deadline_ms')
            require(label(invocation['request_id']))
            require(type(invocation['deadline_ms']) is int and invocation['deadline_ms'] > 0)
            self.config.update(invocation)
        require(self.config['scope'] == c.SCOPE and self.config['sharing'] == 'generated-shareable', 'UNAUTHORIZED')
        require(self.config.get('fallback') is False, 'UNSUPPORTED_PROFILE')
        require(label(self.config['principal']))
        self.chosen = c.selected([descriptor_read(x) for x in self.config['catalogue']])
        self.transport = transport or binding(self.config, self.chosen)
        self.hook = hook
        self.db = sqlite3.connect(self.config['database'], timeout=.2)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS caller_requests (
          id TEXT PRIMARY KEY, request TEXT NOT NULL, selections TEXT NOT NULL,
          max_calls INTEGER NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
          receipt TEXT, acknowledged INTEGER NOT NULL DEFAULT 0)''')

    def close(self):
        self.db.close()

    def _request(self, name, operation, body):
        desc = self.chosen[name]
        profile = c.PROFILE if name == 'execution' else 'immutable-bytes/1' if name == 'atom.storage' else 'durable-mailbox/2'
        return dict(message_id=self.config['request_id'], interface_ref=dict(id=name, version=desc.version),
                    profile=profile, selection=selection_token(desc), operation=operation,
                    scope_ref=self.config['scope'], body=body)

    def ensure_route_available(self, request_id=None):
        """Local caller-owner admission check; never acknowledges unrelated delivery."""
        for row in self.db.execute('SELECT id,request FROM caller_requests WHERE acknowledged=0'):
            if json.loads(row['request'])['reply_route'] == self.config['reply_route']:
                require(row['id'] == request_id, 'OVERLOADED')

    def prepare(self, premises):
        config = self.config
        require(label(config['request_id']))
        require(type(config['max_calls']) is int and 1 <= config['max_calls'] <= c.MAX_CALLS)
        request = self._request('execution', 'submit', dict(operation=c.OPERATION, premises=c.premises(premises),
                sharing=config['sharing'], max_attempts=config['max_attempts']))
        request.update(idempotency_key=config['request_id'], correlation_id=config['request_id'],
                       reply_route=config['reply_route'], deadline_ms=config['deadline_ms'])
        c.validate(request, self.chosen)
        encoded = canonical(request).decode()
        selections = canonical({k: selection_token(v) for k, v in self.chosen.items()}).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT * FROM caller_requests WHERE id=?', (config['request_id'],)).fetchone()
            if self.application_invocation and (old is None or not old['acknowledged']):
                self.ensure_route_available(config['request_id'])
            if old:
                require(old['request'] == encoded and old['selections'] == selections and old['max_calls'] == config['max_calls'], 'CONFLICT')
            else:
                require(self.db.execute('SELECT count(*) FROM caller_requests').fetchone()[0] < c.MAX_REQUESTS, 'OVERLOADED')
                self.db.execute('INSERT INTO caller_requests(id,request,selections,max_calls) VALUES(?,?,?,?)',
                                (config['request_id'], encoded, selections, config['max_calls']))
        self.hook('after_request_persist')
        return request

    def _call(self, request):
        # Reserve before I/O. Death after reservation spends that attempt; no refund.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row = self.db.execute('SELECT calls,max_calls FROM caller_requests WHERE id=?', (self.config['request_id'],)).fetchone()
            require(row['calls'] < row['max_calls'], 'NOT_AVAILABLE')
            self.db.execute('UPDATE caller_requests SET calls=calls+1 WHERE id=?', (self.config['request_id'],))
        self.hook('after_call_reservation')
        return self.transport.invoke(request)

    def _retry(self, request, deadline):
        while True:
            try:
                return self._call(request)
            except ContractError as exc:
                row = self.db.execute('SELECT calls,max_calls FROM caller_requests WHERE id=?', (self.config['request_id'],)).fetchone()
                if exc.code not in ('NOT_AVAILABLE', 'OVERLOADED') or row['calls'] >= row['max_calls'] or time.time()*1000 >= deadline:
                    raise
                time.sleep(.05)

    def run(self, premises):
        request = self.prepare(premises)
        deadline = request['deadline_ms']
        accepted = self._retry(request, deadline)
        job = accepted['job_id']
        require(job == c.job_id(self.config['principal'], request), 'NOT_AVAILABLE')
        self.hook('after_submit_reply')
        self.transport.correlations[job] = (request['scope_ref'], request['correlation_id'], request['reply_route'])
        status_request = self._request('execution', 'status', dict(job_id=job))
        while True:
            status = self._retry(status_request, deadline)
            require(status['attempts'] <= request['body']['max_attempts'], 'NOT_AVAILABLE')
            if status['failure_reason'] is not None:
                require(status['execution'] == 'failed' and status['error'] == 'NOT_AVAILABLE'
                        and status['attempts'] == request['body']['max_attempts'], 'NOT_AVAILABLE')
            if status['execution'] != 'queued':
                break
            require(time.time()*1000 < deadline, 'DEADLINE_EXCEEDED')
            time.sleep(.05)
        result, atom = None, None
        if status['execution'] == 'succeeded':
            atom = self._retry(self._request('execution', 'result', dict(job_id=job)), deadline)
            payload = self._retry(self._request('atom.storage', 'get', dict(ref=atom['ref'])), deadline)
            require(payload['content_type'] == 'application/neoclaw-nal-result', 'NOT_AVAILABLE')
            data = decode(payload['bytes'])
            require(len(data) <= c.MAX_BYTES and digest(data) == atom['ref']['digest'], 'NOT_AVAILABLE')
            try:
                result = c.result(json_loads(data), request, self.chosen)
            except (ContractError, ValueError, TypeError):
                raise ContractError('NOT_AVAILABLE') from None
        row = self.db.execute('SELECT receipt FROM caller_requests WHERE id=?', (self.config['request_id'],)).fetchone()
        if row['receipt']:
            receipt = json.loads(row['receipt'])
            require(receipt['job_id'] == job and receipt['result'] == result and receipt['error'] == status['error'], 'NOT_AVAILABLE')
            delivery_id = receipt['delivery_id']
        else:
            poll = self._request('agent.messaging', 'poll', dict(route=request['reply_route']))
            while True:
                delivery = self._retry(poll, deadline)['delivery']
                if delivery is not None:
                    break
                require(time.time()*1000 < deadline, 'DEADLINE_EXCEEDED')
                time.sleep(.05)
            body = delivery['body']
            require(body == dict(job_id=job, correlation_id=request['correlation_id'], causation_id=request['message_id'],
                                 result=atom, error=status['error']), 'NOT_AVAILABLE')
            require(delivery['delivery_id'] == job, 'NOT_AVAILABLE')
            delivery_id = delivery['delivery_id']
            receipt = dict(job_id=job, delivery_id=delivery_id, result=result, error=status['error'])
            with self.db:
                self.db.execute('UPDATE caller_requests SET receipt=? WHERE id=?', (canonical(receipt).decode(), self.config['request_id']))
            self.hook('after_caller_receipt')
        # Always reauthorize acknowledgment on replay, including an already-acked
        # receipt. Receipt commit precedes the mailbox owner's independent ack.
        ack = self._request('agent.messaging', 'ack', dict(route=request['reply_route'], delivery_id=delivery_id))
        ack['idempotency_key'] = 'ack/' + self.config['request_id']
        self._retry(ack, deadline)
        self.hook('after_mailbox_ack')
        with self.db:
            self.db.execute('UPDATE caller_requests SET acknowledged=1 WHERE id=?', (self.config['request_id'],))
        if receipt['error'] is not None:
            raise ContractError(receipt['error'])
        return result['representation']
