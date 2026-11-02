"""Two concurrent, one-shot shared-source writes through deployed caller SDKs.

Run with ``python -m examples.preview_shared_source_qualification --help``.
This is an operator qualification of the immutable source, not native memory
adoption. It creates two opaque synthetic records and no enrollment or answer.
The report directory is exclusive: interrupted/unknown submissions are retained
and this entrypoint never resumes or resubmits them. No model runtime is used.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import threading
import time
import uuid

from fusion.contracts import canonical, digest, require
from fusion import lookup_contracts as contracts
from integration.single_node.preview_scope_qualification import Qualification as ScopeQualification
from integration.single_node.preview_qualification import Runner
from integration.single_node.reference_ops import Operator, PYTHON


ROLES = ('omega-agent', 'omega-agent-b')
CONTENT_TYPE = 'application/phase2-diagnostic-synthetic'
RPC_MS = 30000
TRANSPORT_SECONDS = 25
POD_SOURCE = r'''
import json,time,re
from pathlib import Path
from fusion.contracts import ContractError,digest,require
from fusion.preview_atoms import client
from fusion.ports import Mutation
cfg=json.loads(Path('/run/fusion/private-atoms.json').read_text())
settings=json.loads(Path('/config/component.json').read_text())
try:
 p=settings['preview'];scope=p['scope'];agent=p['agents'][ROLE]
 require(settings['role']==ROLE and cfg['principal']==agent['principal'],'UNAUTHORIZED')
 require(p.get('enabled') is True and p.get('model_boundary')=='RECORDED_FIXTURE','UNAUTHORIZED')
 require(type(scope) is str and re.fullmatch(r'synthetic-[a-z0-9][a-z0-9-]{0,53}',scope) is not None,'UNAUTHORIZED')
 require(cfg['scope']==agent['private_scope'] and cfg['scope']!=scope,'UNAUTHORIZED')
 require(EXPECTED_SCOPE is None or EXPECTED_SCOPE==scope,'CONFLICT')
 cfg['scope']=scope;cfg['endpoint']['timeout_seconds']=25
 if OP=='binding':
  value=dict(scope=scope,principal=cfg['principal'],endpoint={k:cfg['endpoint'][k] for k in ('host','port','path')})
 else:
  require(type(DEADLINE) is int and 0<DEADLINE-time.time_ns()//1000000<=30000,'DEADLINE_EXCEEDED')
  port=client(cfg,DEADLINE)
  if OP=='create':value=port.create(Mutation(scope,ARGS['occurrence']), 'application/phase2-diagnostic-synthetic',ARGS['payload'].encode())
  elif OP=='head':value=port.head(scope)
  elif OP=='readCommits':value=port.readCommits(scope,ARGS['after'],ARGS['through'],8)
  elif OP=='getMany':value=[dict(ref=x.ref,content_type=x.content_type,size=len(x.bytes),sha256=digest(x.bytes)) for x in port.getMany(tuple(ARGS['refs']))]
  else:raise ContractError('UNSUPPORTED_OPERATION')
 print(json.dumps(dict(value=value)))
except ContractError as error:print(json.dumps(dict(error=error.code)))
'''


def embedded(role, operation, args, scope, deadline):
    require(role in ROLES and operation in ('binding', 'create', 'head', 'readCommits', 'getMany'))
    values = dict(ROLE=role, OP=operation, ARGS=args, EXPECTED_SCOPE=scope, DEADLINE=deadline)
    return '\n'.join(k + '=' + repr(v) for k, v in values.items()) + '\n' + POD_SOURCE


class Qualification:
    def __init__(self, operator, output, images):
        self.op = operator
        self.root = Path(output)
        self.root.mkdir(parents=True, exist_ok=False)
        self.images = json.loads(Path(images).read_text())
        self.helper = ScopeQualification.__new__(ScopeQualification)
        self.helper.op = operator
        self.scope = None
        self.report = dict(schema='preview-shared-source-qualification/1', namespace=operator.namespace,
            status='PREPARING', classification='REAL_DEPLOYED_ATOMSTORAGE_DETTA_HTTPS_WHEN_EXECUTED',
            boundary='TWO_SDK_CALLERS_SHARED_SOURCE_NOT_NATIVE_MEMORY_ADOPTION',
            additional_live_generations=0, application_occurrences_submitted=0,
            enrollment_records_submitted=0, automatic_write_retries=0,
            max_concurrent_rpc=2, rpc_deadline_ms=RPC_MS, transport_timeout_seconds=TRANSPORT_SECONDS,
            deadline_semantics='absolute client observation bound; no provider cancellation or durable budget claim',
            qualifier_source_sha256=digest(Path(__file__).read_bytes()), cases=[], writes=[])
        self.save()

    def save(self):
        # Persist allocated identities before worker submission; never put tokens
        # or caller configuration files in the sanitized report.
        tmp = self.root / 'report.tmp'
        with tmp.open('wb') as stream:
            stream.write(canonical(self.report)); stream.flush(); os.fsync(stream.fileno())
        tmp.replace(self.root / 'report.json')
        fd = os.open(self.root, os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)

    def call(self, role, operation, args=None, *, deadline=None):
        if deadline is None: deadline = time.time_ns() // 1_000_000 + RPC_MS
        source = embedded(role, operation, args or {}, self.scope, deadline)
        value = json.loads(self.op.k('exec', '-i', role + '-0', '--', PYTHON, '-', data=source, timeout=40))
        require(type(value) is dict and set(value) in ({'value'}, {'error'}), 'NOT_AVAILABLE')
        return value

    def read(self, role, operation, args=None):
        result = self.call(role, operation, args)
        self.report['cases'].append(dict(role=role, operation=operation, result=result))
        self.save()
        require('value' in result, result.get('error', 'NOT_AVAILABLE'))
        return result['value']

    def idle(self):
        result = self.helper.idle()
        api = Runner.__new__(Runner); api.op = self.op
        for role in ROLES:
            worker = api.call(role, 'inventory').get('worker')
            require(worker is None or worker.get('status') in ('NATIVE_STOPPED', 'STOPPED', 'PREPARATION_FAILED'), 'CONFLICT')
        return result

    def pins(self):
        manifest = self.images
        require(manifest.get('source_export_verification') == 'PASS' and
                re.fullmatch('[0-9a-f]{64}', manifest.get('source_manifest_sha256', '')) is not None, 'CONFLICT')
        require(type(manifest.get('images')) is list, 'CONFLICT')
        images = {item['kind']: item for item in manifest['images']}
        require(len(images) == len(manifest['images']) and {'base', 'caller'} <= images.keys(), 'CONFLICT')
        pods = {}
        for role in (*ROLES, 'fusion-storage', 'fusion-model'):
            pod = self.helper.pod(role)
            selected = images['caller' if role in ROLES else 'base']
            candidates = {selected[k] for k in ('manifest_digest', 'configuration_digest')}
            require(all(re.fullmatch('sha256:[0-9a-f]{64}', x) is not None for x in candidates), 'CONFLICT')
            require(len(pod['images']) == 1 and any(pod['images'][0].endswith(x) for x in candidates), 'CONFLICT')
            pods[role] = dict(**pod, source_image=dict(repository=selected['repository'], manifest_digest=selected['manifest_digest'],
                configuration_digest=selected['configuration_digest']))
        self.report.update(pods=pods, source_manifest_sha256=manifest['source_manifest_sha256'])
        self.save()

    def snapshot(self, role, through, after=0):
        contracts.head(through, self.scope)
        records = []
        # The feed contract bounds the complete snapshot to 512 records/64 pages.
        for _ in range(contracts.MAX_ATOMS // contracts.PAGE + 1):
            page = self.read(role, 'readCommits', dict(after=after, through=through))
            contracts.commits(page, self.scope, after, through, contracts.PAGE)
            records += page['records']
            if page['complete']: return records
            after = page['next_after']
        require(False, 'OVERLOADED')

    def concurrent_writes(self):
        now = time.time_ns() // 1_000_000
        for role in ROLES:
            occurrence = 'phase2-source-' + str(uuid.uuid4())
            payload = 'Generated opaque source qualification record ' + occurrence
            self.report['writes'].append(dict(role=role, occurrence=occurrence, payload_sha256=digest(payload.encode()),
                payload=payload, content_type=CONTENT_TYPE, deadline_ms=now + RPC_MS,
                status='ALLOCATED_BEFORE_SUBMISSION', submission_attempts=0))
        self.save()
        barrier = threading.Barrier(2)
        def submit(row):
            barrier.wait(timeout=5)
            return self.call(row['role'], 'create', dict(occurrence=row['occurrence'], payload=row['payload']), deadline=row['deadline_ms'])
        # Conservative at-most-one submission intent for each slot. A process
        # kill here remains unknown, even if no request reached the provider.
        for row in self.report['writes']:
            row.update(status='SUBMISSION_INTENT_OUTCOME_UNKNOWN', submission_attempts=1)
        self.save()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(submit, row) for row in self.report['writes']]
            for row, future in zip(self.report['writes'], futures):
                try:
                    result = future.result()
                    row['result'] = result
                    row['status'] = 'CAPTURED_ACCEPTANCE' if 'value' in result else 'FAILED_OR_UNKNOWN'
                except Exception as error:
                    row.update(status='FAILED_OR_UNKNOWN', failure=dict(type=type(error).__name__, code=getattr(error, 'code', None)))
                self.save()
        require(all(row['status'] == 'CAPTURED_ACCEPTANCE' for row in self.report['writes']), 'NOT_AVAILABLE')

    def run(self):
        try:
            self.op.owned(); self.pins()
            self.report.update(idle_before=self.idle(), model_accounting_before=self.helper.models())
            self.save()
            bindings = [self.read(role, 'binding') for role in ROLES]
            require(bindings[0]['scope'] == bindings[1]['scope'] and
                    bindings[0]['principal'] != bindings[1]['principal'] and
                    bindings[0]['endpoint'] == bindings[1]['endpoint'], 'CONFLICT')
            self.scope = bindings[0]['scope']; self.report['scope'] = self.scope
            before = self.read(ROLES[0], 'head'); contracts.head(before, self.scope)
            require(before == self.read(ROLES[1], 'head') and before['sequence'] <= contracts.MAX_ATOMS - 2, 'CONFLICT')
            previous = self.snapshot(ROLES[0], before)
            self.report['before'] = dict(head=before, records=len(previous), snapshot_sha256=digest(canonical(previous)))
            self.save()
            self.concurrent_writes()
            refs = [row['result']['value']['ref'] for row in self.report['writes']]
            for ref, row in zip(refs, self.report['writes']):
                contracts.ref(ref, self.scope); require(ref['digest'] == row['payload_sha256'], 'CONFLICT')
            require(refs[0] != refs[1], 'CONFLICT')
            after = self.read(ROLES[0], 'head')
            require(after == {**before, 'sequence': before['sequence'] + 2} and after == self.read(ROLES[1], 'head'), 'CONFLICT')
            retained = self.snapshot(ROLES[1], before)
            require(retained == previous, 'CONFLICT')
            for role in ROLES:
                tail = self.snapshot(role, after, before['sequence'])
                require(len(tail) == 2 and {canonical(x['ref']) for x in tail} == {canonical(x) for x in refs}, 'CONFLICT')
                require(all(x['content_type'] == CONTENT_TYPE for x in tail), 'CONFLICT')
                values = self.read(role, 'getMany', dict(refs=refs))
                expected = [dict(ref=ref, content_type=CONTENT_TYPE, size=len(row['payload'].encode()), sha256=row['payload_sha256'])
                            for ref, row in zip(refs, self.report['writes'])]
                require(values == expected, 'CONFLICT')
            self.report.update(after=dict(head=after, retained_snapshot_sha256=digest(canonical(retained))),
                idle_after=self.idle(), model_accounting_after=self.helper.models())
            require(self.report['idle_before'] == self.report['idle_after'] and
                    self.report['model_accounting_before'] == self.report['model_accounting_after'], 'CONFLICT')
            self.report.update(status='PASS', classification='REAL_DEPLOYED_ATOMSTORAGE_DETTA_HTTPS')
        except Exception as error:
            self.report.update(status='FAILED', failure=dict(type=type(error).__name__, code=getattr(error, 'code', None)))
            raise
        finally: self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig', 'context', 'namespace', 'output', 'images'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    Qualification(Operator(args.kubeconfig, args.context, args.namespace), args.output, args.images).run()


if __name__ == '__main__': main()
