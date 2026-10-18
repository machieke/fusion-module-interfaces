"""Operator-side immutable enrollment through AtomStorage ports only."""
import json
from . import vector_contracts as c
from .contracts import canonical, require
from .ports import Mutation
from .responses import envelope


def checked(atoms, ref, content_type):
    item=atoms.get(ref);envelope(item,ref)
    require(item.content_type == content_type,'NOT_AVAILABLE');return item.bytes


def validate_inputs(atoms, entry):
    value=c.payload(json.loads(checked(atoms,entry['payload'],c.PAYLOAD)),entry['scope'],entry['corpus'])
    require(value['uuid']==entry['uuid'],'CONFLICT')
    vector=c.from_bytes(checked(atoms,entry['vector'],c.VECTOR))
    return value,vector


def enroll(atoms, scope, corpus, embedding, key, value, vector):
    value=c.payload(value,scope,corpus);data=c.vector_bytes(vector);c.model(embedding)
    p=atoms.create(Mutation(scope,key+'-payload'),c.PAYLOAD,canonical(value))['ref']
    v=atoms.create(Mutation(scope,key+'-vector'),c.VECTOR,data)['ref']
    entry=c.enrollment(dict(profile=c.EXTRACTION,scope=scope,corpus=corpus,uuid=value['uuid'],payload=p,vector=v,embedding=embedding),scope,corpus,embedding)
    validate_inputs(atoms,entry)
    return atoms.create(Mutation(scope,key+'-enrollment'),c.ENROLLMENT,canonical(entry))['ref']
