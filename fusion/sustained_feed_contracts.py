"""Pure bounded /2 source capacity DTOs, shared by owners and clients."""
from . import lookup_contracts as c
from .contracts import require,label

PROFILE='bounded-feed-capacity/1'
METADATA_RESERVATION=8192

def capacity_policy(value):
    require(type(value) is dict and set(value)=={'profile','records','bytes','scopes'},'UNSUPPORTED_PROFILE')
    require(value['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    c.integer(value['records'],1,c.SUSTAINED_MAX_ATOMS);c.integer(value['bytes'],1,64*1024*1024)
    require(type(value['scopes']) is list and 1<=len(value['scopes'])<=3 and len(set(value['scopes']))==len(value['scopes']))
    require(all(type(x) is str and label(x) and x.startswith('synthetic-') for x in value['scopes']),'UNAUTHORIZED')
    return c.copy(value)


def capacity_result(value,scope):
    require(type(value) is dict and set(value)=={'profile','source_profile','scope_ref','source','limits','usage','metadata_reservation_per_record','refunds','physical_bytes'},'NOT_AVAILABLE')
    require(value['profile']==PROFILE and value['source_profile']==c.SUSTAINED_FEED,'UNSUPPORTED_PROFILE')
    require(value['scope_ref']==scope,'UNAUTHORIZED');c.identity(value['source'])
    require(value['metadata_reservation_per_record']==METADATA_RESERVATION and value['refunds'] is False and value['physical_bytes']=='NOT_INFERRED','NOT_AVAILABLE')
    limits,used=value['limits'],value['usage']
    require(type(limits) is dict and set(limits)=={'records','bytes'},'NOT_AVAILABLE')
    c.integer(limits['records'],1,c.SUSTAINED_MAX_ATOMS);c.integer(limits['bytes'],1,64*1024*1024)
    require(type(used) is dict and set(used)=={'reserved_records','published_records','pending_records','charged_bytes','published_payload_bytes'},'NOT_AVAILABLE')
    c.integer(used['reserved_records'],0,limits['records']);c.integer(used['published_records'],0,used['reserved_records'])
    require(type(used['pending_records']) is int and used['pending_records']==used['reserved_records']-used['published_records'],'NOT_AVAILABLE')
    c.integer(used['charged_bytes'],0,limits['bytes']);c.integer(used['published_payload_bytes'],0,used['charged_bytes'])
    return c.copy(value)

