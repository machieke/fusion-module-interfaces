"""Portable wrapper for the pinned two-STV S01 operation, not new arithmetic.

The original request/result fingerprints, named kernel, attempt/deadline
enforcement and journals remain authoritative. Only this wrapper is new.
"""
import json
from . import neoclaw_contracts as c
from .contracts import canonical,require
from .registry import selection_token

PROFILE='bounded-native-nal-envelope/1'


def build(request,principal,chosen):
    require(c.validate(request,chosen)==('execution','submit'),'UNSUPPORTED_OPERATION')
    return dict(profile=PROFILE,task=request['idempotency_key'],correlation=request['correlation_id'],
        scope=request['scope_ref'],initiator=principal,
        operation=dict(interface=request['interface_ref'],profile=c.PROFILE,name=c.OPERATION),
        inputs=dict(premises=c.premises(request['body']['premises'])),
        delegation=dict(service='execution',actor='worker',authority='current-scoped-policy'),
        provider=dict(id=chosen['execution'].provider,selection=selection_token(chosen['execution']),
            kernel=selection_token(chosen['pln.kernel'])),
        disclosure='generated-shareable-two-grounded-stvs',deadline_ms=request['deadline_ms'],
        limits=dict(logical_operations=1,native_attempts=request['body']['max_attempts'],caller_calls=c.MAX_CALLS,
            input_bytes=c.MAX_BYTES,output_bytes=c.MAX_BYTES,completion_routes=1,recursive=False),
        completion=dict(owner=principal,route=request['reply_route'],profile='durable-mailbox/2'),
        guarantee='one-logical-admission-independent-owner-commits')


def check(value,request,principal,chosen):
    require(type(value) is dict and len(canonical(value))<=8192)
    expected=build(request,principal,chosen)
    require(value.get('profile')==PROFILE,'UNSUPPORTED_PROFILE')
    require(value.get('provider')==expected['provider'],'UNSUPPORTED_PROFILE')
    require(value==expected,'CONFLICT')
    return json.loads(canonical(value))


def seal(db,enabled,table):
    require(table in ('jobs','caller_requests'))
    tables={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if enabled:
        require(enabled==PROFILE,'UNSUPPORTED_PROFILE')
        require('integrated_nal_profile' in tables or table not in tables or db.execute('SELECT count(*) FROM '+table).fetchone()[0]==0,'UNSUPPORTED_PROFILE')
        db.execute('CREATE TABLE IF NOT EXISTS integrated_nal_profile(profile TEXT PRIMARY KEY)')
        with db:
            old=db.execute('SELECT profile FROM integrated_nal_profile').fetchone()
            if old:require(old[0]==PROFILE,'UNSUPPORTED_PROFILE')
            else:db.execute('INSERT INTO integrated_nal_profile VALUES(?)',(PROFILE,))
    else:require('integrated_nal_profile' not in tables,'UNSUPPORTED_PROFILE')
