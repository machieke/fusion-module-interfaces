"""Pure optional AtomStorage archive DTOs; no backend or journal imports."""
import uuid
from .contracts import canonical,require
from . import lookup_contracts as c

PROFILE='owner-sealed-payload-archive/1'
SEGMENT_BYTES=262144
RESERVATION_BYTES=2*SEGMENT_BYTES+4096
OPERATIONS=frozenset({'planArchive','publishArchive','observeArchive'})
DEFAULT=dict(profile=PROFILE,segments=64,bytes=16*1024*1024,records=16)

def policy(value):
    require(type(value) is dict and set(value)==set(DEFAULT) and value['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    c.integer(value['segments'],1,256);c.integer(value['bytes'],RESERVATION_BYTES,64*1024*1024);c.integer(value['records'],1,16)
    return c.copy(value)

def records(value,scope,after,through,limit):
    require(type(value) is list and 1<=len(value)<=limit,'NOT_AVAILABLE')
    for index,row in enumerate(value):
        require(type(row) is dict and set(row)=={'sequence','ref','size'},'NOT_AVAILABLE')
        require(row['sequence']==after+index+1 and row['sequence']<=through['sequence'],'NOT_AVAILABLE')
        c.ref(row['ref'],scope);c.integer(row['size'],1,c.MAX_BYTES)

def plan(value,scope,after,through,limit):
    require(type(value) is dict and set(value)=={'profile','source','scope_ref','after','through','records','maximum_charge_bytes','hot_deletion','source_head_unchanged','admission_reserved'},'NOT_AVAILABLE')
    require(value['profile']==PROFILE and value['scope_ref']==scope and value['source']==through['source'] and value['after']==after and value['through']==through,'NOT_AVAILABLE')
    require(value['maximum_charge_bytes']==RESERVATION_BYTES and value['hot_deletion'] is False and value['source_head_unchanged'] is True and value['admission_reserved'] is False,'NOT_AVAILABLE')
    records(value['records'],scope,after,through,limit);return value

def status(value,command,principal,feed_profile):
    require(type(value) is dict and set(value)=={'profile','id','scope_ref','intent','intent_sha256','state','manifest_sha256','sealed_bytes','charged_bytes','hot_deletion','source_head_unchanged','effect_budget_refund'},'NOT_AVAILABLE')
    require(value['profile']==PROFILE and value['scope_ref']==command.scope_ref and value['state'] in ('reserved','sealed'),'NOT_AVAILABLE')
    intent=value['intent'];require(type(intent) is dict and set(intent)=={'profile','source','scope_ref','after','through','limit','records'},'NOT_AVAILABLE')
    require(intent['profile']==PROFILE and intent['scope_ref']==command.scope_ref,'NOT_AVAILABLE')
    c.head(intent['through'],command.scope_ref,feed_profile);require(intent['source']==intent['through']['source'],'NOT_AVAILABLE')
    c.integer(intent['after'],0,intent['through']['sequence']);c.integer(intent['limit'],1,16)
    records(intent['records'],command.scope_ref,intent['after'],intent['through'],intent['limit'])
    expected=str(uuid.uuid5(uuid.UUID(intent['source']),'sealed-archive/'+canonical([principal,command.scope_ref,command.idempotency_key]).decode()))
    require(value['id']==expected and value['charged_bytes']==RESERVATION_BYTES and value['hot_deletion'] is False and value['source_head_unchanged'] is True and value['effect_budget_refund'] is False,'NOT_AVAILABLE')
    import re
    require(type(value['intent_sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['intent_sha256']),'NOT_AVAILABLE')
    if value['state']=='sealed':
        require(type(value['manifest_sha256']) is str and re.fullmatch('[0-9a-f]{64}',value['manifest_sha256']),'NOT_AVAILABLE')
        c.integer(value['sealed_bytes'],1,SEGMENT_BYTES)
    else:require(value['manifest_sha256'] is None and value['sealed_bytes'] is None,'NOT_AVAILABLE')
    return value

def observation(value,command,principal,feed_profile):
    require(type(value) is dict and set(value)=={'profile','scope_ref','found','archive','capacity'} and value['profile']==PROFILE and value['scope_ref']==command.scope_ref and type(value['found']) is bool,'NOT_AVAILABLE')
    if value['found']:status(value['archive'],command,principal,feed_profile)
    else:require(value['archive'] is None,'NOT_AVAILABLE')
    cap=value['capacity'];require(type(cap) is dict and set(cap)=={'limits','reserved_segments','charged_bytes','sealed_segments','refunds'} and cap['refunds'] is False,'NOT_AVAILABLE')
    limits=policy(cap['limits']);c.integer(cap['reserved_segments'],0,limits['segments']);c.integer(cap['sealed_segments'],0,cap['reserved_segments'])
    c.integer(cap['charged_bytes'],0,limits['bytes']);require(cap['charged_bytes']==cap['reserved_segments']*RESERVATION_BYTES,'NOT_AVAILABLE')
    return value
