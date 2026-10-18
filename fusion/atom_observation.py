"""Backend-independent optional immutable mutation acceptance observation."""
from . import lookup_contracts as c
from .contracts import require
from .responses import atom_write,fields


def observation(value,scope,descriptor):
    fields(value,'found write through content_type size')
    require(type(value['found']) is bool,'NOT_AVAILABLE')
    if not value['found']:
        require(all(value[k] is None for k in ('write','through','content_type','size')),'NOT_AVAILABLE')
    else:
        atom_write(value['write'],scope,descriptor);c.ref(value['write']['ref'],scope);c.head(value['through'],scope)
        require(value['through']['sequence']>0,'NOT_AVAILABLE');c.integer(value['size'],1,c.MAX_BYTES)
        require(type(value['content_type']) is str and 1<=len(value['content_type'])<=80,'NOT_AVAILABLE')
    return c.copy(value)
