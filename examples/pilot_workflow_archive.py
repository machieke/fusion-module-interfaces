"""Seal an actual workflow capture through existing bounded storage maintenance.

This is operator-authorized placement maintenance, not a native tool result or
new observation. The actual next workflow guard reads the activated archive
through the ordinary AtomStorage port and its existing mandatory digest checks.
"""
import json
from fusion.contracts import require
from fusion.workflow_prerequisites import KINDS,condition
from integration.single_node.reference_ops import PYTHON
from examples.integrated_archive import ARCHIVE


def archive(op,workflow,memory):
    payload=memory['memory']['target']['payload'];scope=payload['scope_ref']
    require(op.namespace.startswith('omega-ref-pilot-') and scope.startswith('synthetic-'),'UNAUTHORIZED')
    code=ARCHIVE.replace("Mutation(q['scope'],'archive-native-first-memory')","Mutation(q['scope'],q['identity'])")
    code=code.replace("'hydrated_bytes':len(item.bytes)","'hydrated_bytes':len(item.bytes),'content_type':item.content_type")
    observed=json.loads(op.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',code,
        data=json.dumps(dict(scope=scope,payload=payload,through=memory['source'],identity='workflow-prerequisite-'+workflow)),timeout=75))
    require(observed['hydrated_payload']==payload and observed['sealed']['state']=='sealed'
        and observed['observation']['archive']==observed['sealed'] and observed['source_head_unchanged'] is True
        and payload in [x['ref'] for x in observed['plan']['records']],'CONFLICT')
    guard=condition(dict(id='captured-payload-still-available',kind='snapshot-available',policy=KINDS['snapshot-available'],
        scope=scope,target=dict(ref=payload,content_type=observed['content_type']),predicate=None),scope)
    return guard,dict(observed,guard=guard,placement='SEALED_OWNER_ARCHIVE',hot_deletion=False,
        additional_native_inputs=0,source_capture_unchanged=True)
