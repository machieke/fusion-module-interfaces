"""Closed data-only handoff to the existing inspect_atom executor.

This opt-in envelope does not change inspect_atom's mathematics or the /2
execution contract. Transport delivery IDs are outside logical task identity.
The existing owner still commits jobs, results and completion independently.
"""
import json,time
from .contracts import canonical, digest, require, validate
from .registry import selection_token

PROFILE = 'bounded-inspect-envelope/1'
LIMITS = dict(logical_operations=1, caller_calls=32, input_bytes=65536,
              output_bytes=4096, completion_routes=1, recursive=False)


def build(request, principal, selected):
    name, operation = validate(request, check_deadline=False)
    require((name, operation) == ('execution', 'submit'), 'UNSUPPORTED_OPERATION')
    require(request['body']['operation'] == 'inspect_atom', 'UNSUPPORTED_OPERATION')
    require(type(request.get('deadline_ms')) is int, 'INVALID_ARGUMENT')
    return dict(profile=PROFILE, task=request['idempotency_key'],
        correlation=request['correlation_id'], scope=request['scope_ref'],
        operation=dict(interface=request['interface_ref'], profile=request['profile'], name='inspect_atom'),
        inputs=dict(ref=request['body']['ref']), initiator=principal,
        delegation=dict(service='execution', actor='worker', authority='current-scoped-policy'),
        provider=dict(id=selected.provider, selection=selection_token(selected)),
        disclosure='approved-synthetic-agent-artifact', deadline_ms=request['deadline_ms'],
        limits=dict(LIMITS), completion=dict(owner=principal, route=request['reply_route'], profile='durable-mailbox/2'),
        guarantee='one-logical-admission-independent-owner-commits')


def check(value, request, principal, selected):
    require(type(value) is dict and len(canonical(value)) <= 8192)
    expected = build(request, principal, selected)
    require(value.get('profile') == PROFILE, 'UNSUPPORTED_PROFILE')
    require(value.get('provider') == expected['provider'], 'UNSUPPORTED_PROFILE')
    require(value == expected, 'CONFLICT')
    return json.loads(canonical(value))


def bind(db, value, request, hook):
    """Durable intent binding BEFORE delegated acceptance; no provider effect.

    Stable task identity also binds all semantic fields in the original request.
    Thus a changed delivery ID can replay, but a changed deadline, input or
    delegation conflicts even if the earlier submission reply was lost.
    """
    db.execute('CREATE TABLE IF NOT EXISTS integrated_execution_envelopes('
               'identity TEXT PRIMARY KEY, envelope TEXT NOT NULL, request_digest TEXT NOT NULL)')
    identity = canonical([value['initiator'], value['scope'], value['task']]).decode()
    semantic = {k:v for k,v in request.items() if k not in ('message_id','causation_id','extensions')}
    encoded, fingerprint = canonical(value).decode(), digest(canonical(semantic))
    with db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT envelope,request_digest FROM integrated_execution_envelopes WHERE identity=?',(identity,)).fetchone()
        if old:
            require(tuple(old) == (encoded,fingerprint), 'CONFLICT')
        else:
            require(time.time_ns()//1_000_000<value['deadline_ms'],'DEADLINE_EXCEEDED')
            require(db.execute('SELECT count(*) FROM integrated_execution_envelopes').fetchone()[0]<128,'OVERLOADED')
            db.execute('INSERT INTO integrated_execution_envelopes VALUES(?,?,?)',(identity,encoded,fingerprint))
    hook('after_execution_envelope_bind')
