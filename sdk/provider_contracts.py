"""Generated Go reference-provider contract; maintained Python wire definitions.

The independent provider shares data/schema artifacts, never owner transitions.
"""
import argparse,json,uuid
from pathlib import Path
from fusion.registry import Descriptor,descriptor_wire,selection_token
from fusion.contracts import canonical,digest
from fusion.execution_envelope import PROFILE as ENVELOPE,LIMITS

ROOT=Path(__file__).resolve().parents[1]

from fusion.reference_inspect_contracts import descriptor

def generated():
    selected=descriptor()
    from fusion.execution_envelope import build
    request=dict(message_id='generated-delivery',interface_ref=dict(id='execution',version='1.0.0'),
        operation='submit',scope_ref='synthetic-go-inspect',profile='inspect-atom/2',
        body=dict(operation='inspect_atom',ref=dict(scope_ref='synthetic-go-inspect',
            id='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',revision=1,digest=digest('generated raw payload with snow 雪'.encode()))),
        idempotency_key='generated-occurrence',correlation_id='generated-occurrence',reply_route='inspect-A',deadline_ms=5000)
    identity=canonical(['A','synthetic-go-inspect','execution','submit','generated-occurrence']).decode()
    samples=dict(request=request,envelope=build(request,'A',selected),request_sha256=digest(canonical(request)),
        accepted_job_id=str(uuid.uuid5(uuid.NAMESPACE_URL,identity)),
        result=canonical(dict(digest=request['body']['ref']['digest'],length=len('generated raw payload with snow 雪'.encode()),
            operation='inspect_atom',provider_version='0.1.0')).decode())
    return dict(profile='go-immutable-inspect-contract/1',descriptor=descriptor_wire(selected),selection=selection_token(selected),
        samples=samples,wrapper='synthetic-inspect-placement/1',route='/preview/inspection',completion='/preview/inspection-completion',
        envelope=dict(profile=ENVELOPE,limits=dict(LIMITS)),event_profile='execution-commit-cursor/1',
        operation=dict(name='inspect_atom',result_fields=['digest','length','operation','provider_version'],provider_version='0.1.0'),
        source_files={name:digest((ROOT/name).read_bytes()) for name in ('fusion/contracts.py','fusion/registry.py',
            'fusion/execution_envelope.py','fusion/execution_events.py','fusion/responses.py','fusion/reference_inspect_contracts.py')},
        semantics=dict(acceptance='own-fsync-rename-journal',results='selected-AtomStorage-port',
            completion='existing-Messaging-port',capture='no-recomputation-after-result-capture',
            authority='current-policy-on-every-call-and-worker-phase',payload_limit=4096,legacy_inspect_1=False))

def main():
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');a=p.parse_args()
    file=ROOT/'sdk/go/inspectprovider/contract.json';raw=canonical(generated())+b'\n'
    if a.check:
        if file.read_bytes()!=raw:raise SystemExit('provider contract drift')
    else:file.write_bytes(raw)
if __name__=='__main__':main()
