"""Fresh finite source capacity; opaque DeTTa payloads remain application-neutral.

Admission, backend storage and feed publication are independent durable facts.
A pending reservation consumes its full bound indefinitely. No refund or GC.
The scope quota is independent of other scopes; unauthorized counts stay hidden.
"""
from contextlib import closing
import json,uuid
from . import lookup_contracts as c
from .contracts import canonical,digest,require,label

from .sustained_feed_contracts import PROFILE,METADATA_RESERVATION,capacity_policy,capacity_result


def usage(owner,db,scope):
    count,charged=db.execute('SELECT count(*),coalesce(sum(charged_bytes),0) FROM feed_reservations WHERE scope=?',(scope,)).fetchone()
    published,payload=db.execute('SELECT count(*),coalesce(sum(json_extract(value,"$.size")),0) FROM feed_atoms WHERE scope=?',(scope,)).fetchone()
    return dict(reserved_records=count,published_records=published,pending_records=count-published,charged_bytes=charged,published_payload_bytes=payload)

def capacity(owner,scope):
    owner.access.authorize(scope,'capacity');policy=owner.capacity_policy
    require(policy is not None,'UNSUPPORTED_PROFILE');require(scope in policy['scopes'],'UNAUTHORIZED')
    with closing(owner.connect()) as db:value=usage(owner,db,scope)
    owner.access.authorize(scope,'capacity')
    return dict(profile=PROFILE,source_profile=owner.profile,scope_ref=scope,source=owner.source,
        limits={k:policy[k] for k in ('records','bytes')},usage=value,
        metadata_reservation_per_record=METADATA_RESERVATION,refunds=False,physical_bytes='NOT_INFERRED')


def create(owner,command,content_type,data):
    c.mutation(command);require(type(data) is bytes and label(content_type));c.integer(len(data),1,c.MAX_BYTES)
    scope=command.scope_ref;policy=owner.capacity_policy
    principal=owner.access.authorize(scope,'create');require(scope in policy['scopes'],'UNAUTHORIZED')
    identity=canonical([principal,scope,command.idempotency_key]).decode();fingerprint=digest(canonical([content_type,digest(data)]))
    with closing(owner.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        old=db.execute('SELECT fingerprint,value FROM feed_atoms WHERE identity=?',(identity,)).fetchone()
        if old:
            require(old[0]==fingerprint,'CONFLICT');owner.access.authorize(scope,'create');return json.loads(old[1])['write']
        reserved=db.execute('SELECT fingerprint,size FROM feed_reservations WHERE identity=?',(identity,)).fetchone()
        if reserved:require(reserved==(fingerprint,len(data)),'CONFLICT')
        else:
            current=usage(owner,db,scope);charge=len(data)+METADATA_RESERVATION
            require(current['reserved_records']<policy['records'] and current['charged_bytes']+charge<=policy['bytes'],'OVERLOADED')
            db.execute('INSERT INTO feed_reservations VALUES(?,?,?,?,?,?)',(identity,fingerprint,scope,len(data),charge,'reserved'))
        owner.access.authorize(scope,'create')
    owner.hook('after_feed_admission_commit')
    payload,receipt=owner.storage.put(scope,identity,data)
    owner.hook('after_feed_backend_acceptance')
    owner.access.authorize(scope,'create')
    atom_id=str(uuid.uuid5(uuid.UUID(owner.source),identity))
    write={'ref':dict(scope_ref=scope,id=atom_id,revision=1,digest=digest(data)),'receipt':receipt}
    value=dict(write=write,content_type=content_type,size=len(data))
    require(len(canonical(value))+len(identity.encode())+len(str(payload).encode())+512<=METADATA_RESERVATION,'OVERLOADED')
    with closing(owner.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');owner.access.authorize(scope,'create')
        old=db.execute('SELECT fingerprint,value FROM feed_atoms WHERE identity=?',(identity,)).fetchone()
        if old:
            require(old[0]==fingerprint,'CONFLICT');return json.loads(old[1])['write']
        seq=db.execute('SELECT coalesce(max(sequence),0)+1 FROM feed_atoms WHERE scope=?',(scope,)).fetchone()[0]
        db.execute('INSERT INTO feed_atoms VALUES(?,?,?,?,?,?)',(scope,seq,identity,fingerprint,canonical(value).decode(),payload))
        db.execute("UPDATE feed_reservations SET state='published' WHERE identity=?",(identity,))
    owner.hook('after_atom_feed_commit');return c.copy(write)
