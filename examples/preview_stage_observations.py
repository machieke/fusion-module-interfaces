"""Summarize existing native bridge timings from two quiesced agent PVCs.

Only recorded diagnostics are read. Helpers mount their selected owner PVC
read-only and run standard-library observation code, never native applications,
replay, providers or a model. Nested method durations are not additive and do
not establish throughput, token counts or service-wide latency benchmarks.
"""
import argparse
import inspect
import json
from pathlib import Path

from fusion.contracts import canonical, digest, require
from integration.single_node.reference_ops import Operator, PYTHON


ROLES = ('omega-agent', 'omega-agent-b')


def parse_timings(raw):
    """Closed diagnostic format; no record bodies escape this function."""
    import hashlib
    import json
    import math
    import re

    if type(raw) is not bytes or len(raw) > 1048576:
        raise ValueError('timing byte limit')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate diagnostic field')
            result[key] = value
        return result

    groups = {}
    records = 0
    for line in raw.decode('utf-8').splitlines():
        if not line or len(line.encode()) > 2048 or records >= 16384:
            raise ValueError('timing record limit')
        item = json.loads(line, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite diagnostic')))
        if type(item) is not dict or set(item) != {'method', 'pid', 'finished_ms', 'elapsed_ms', 'code'}:
            raise ValueError('diagnostic fields')
        if type(item['method']) is not str or re.fullmatch(r'[a-z][a-z0-9_]{0,63}', item['method']) is None:
            raise ValueError('diagnostic method')
        code = item['code']
        if code is not None and (type(code) is not str or re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', code) is None):
            raise ValueError('diagnostic code')
        if type(item['pid']) is not int or not 0 < item['pid'] <= 2**63-1 or \
                type(item['finished_ms']) is not int or not 0 <= item['finished_ms'] <= 2**63-1:
            raise ValueError('diagnostic identity/time')
        elapsed = item['elapsed_ms']
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('diagnostic elapsed time')
        key = item['method'], code
        if key not in groups:
            groups[key] = dict(method=key[0], code=key[1], count=0,
                               min_ms=elapsed, max_ms=elapsed, mean_ms=0.0)
        group = groups[key]
        group['count'] += 1
        group['min_ms'] = min(group['min_ms'], elapsed)
        group['max_ms'] = max(group['max_ms'], elapsed)
        group['mean_ms'] += (elapsed-group['mean_ms'])/group['count']
        records += 1
    ordered = [groups[key] for key in sorted(groups, key=lambda key: (key[0], key[1] or ''))]
    return dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), records=records, by_method_code=ordered)


def owned_timings(directory, role, source_root=None):
    """At most two bounded files from this owner's stopped, read-only PVC."""
    import hashlib
    import itertools
    import json
    import os
    from pathlib import Path
    import stat
    import uuid

    assert role in ('omega-agent', 'omega-agent-b')
    root = Path(directory)
    seal_path = root/'owner-seal.json'
    assert not seal_path.is_symlink() and seal_path.stat().st_size <= 4096
    seal = json.loads(seal_path.read_bytes())
    assert seal['role'] == role and seal['composition'] == 'omega-single-node-developer-preview/1'
    assert type(seal['scope']) is str and seal['scope'].startswith('synthetic-')
    sessions = root/'sessions'
    assert sessions.is_dir() and not sessions.is_symlink()
    with os.scandir(sessions) as stream:
        entries = list(itertools.islice(stream, 9))
    assert len(entries) <= 8
    paths, checked_paths = [], []
    for entry in entries:
        assert entry.is_dir(follow_symlinks=False) and str(uuid.UUID(entry.name)) == entry.name
        native = Path(entry.path)/'native'
        assert not native.is_symlink()
        path = native/'bridge-timing.jsonl'
        checked_paths.append(dict(path=str(path.relative_to(root)), native_directory_present=native.is_dir(),
                                  diagnostic_file_present=path.exists() or path.is_symlink()))
        if not path.exists() and not path.is_symlink():
            continue
        assert not path.is_symlink() and stat.S_ISREG(path.stat().st_mode)
        paths.append(path)
    assert len(paths) <= 2
    files, groups = [], {}
    for path in sorted(paths):
        before = path.stat()
        assert before.st_size <= 1048576
        with path.open('rb') as stream:
            raw = stream.read(1048577)
        observed = parse_timings(raw)
        with path.open('rb') as stream:
            repeated = stream.read(1048577)
        after = path.stat()
        assert raw == repeated and before.st_size == after.st_size == len(raw)
        assert before.st_mtime_ns == after.st_mtime_ns
        files.append(dict(path=str(path.relative_to(root)), **observed))
        for item in observed['by_method_code']:
            key = item['method'], item['code']
            if key not in groups:
                groups[key] = dict(item)
            else:
                group = groups[key]
                total = group['count']+item['count']
                group['mean_ms'] += (item['mean_ms']-group['mean_ms'])*(item['count']/total)
                group.update(count=total, min_ms=min(group['min_ms'], item['min_ms']), max_ms=max(group['max_ms'], item['max_ms']))
    total_records = sum(x['records'] for x in files)
    result = dict(role=role, scope=seal['scope'], files=files, total_records=total_records,
        checked_paths=sorted(checked_paths, key=lambda item: item['path']),
        timing_status='OBSERVED' if total_records else 'NOT_OBSERVED',
        absence_reason=None if total_records else 'No retained nonempty bridge timing records at the source-declared paths; historical cause unknown.',
        by_method_code=[groups[key] for key in sorted(groups, key=lambda key: (key[0], key[1] or ''))],
        observed_files_unchanged=True)
    if source_root is not None:
        source = Path(source_root)/'integration/neoclaw/loop_bridge.py'
        result['diagnostic_writer_source_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    return result


def stopped(op):
    namespace = op.owned()
    workloads = op.workloads()
    require(all(item['spec']['replicas'] == 0 for item in workloads), 'UNAUTHORIZED')
    require(not json.loads(op.k('get', 'pods', '-o', 'json'))['items'], 'CONFLICT')
    selected = {}
    for role in ROLES:
        items = [item for item in workloads if item['metadata']['name'] == role]
        require(len(items) == 1, 'NOT_AVAILABLE')
        item = items[0]
        containers = item['spec']['template']['spec']['containers']
        require(len(containers) == 1, 'UNSUPPORTED_PROFILE')
        image = containers[0]['image']
        require('@sha256:' in image and len(image.rsplit('@sha256:', 1)[1]) == 64, 'CONFLICT')
        mount = [value for value in containers[0]['volumeMounts'] if value['mountPath'] == '/state']
        require(len(mount) == 1 and mount[0]['name'] == 'state' and 'subPath' not in mount[0], 'CONFLICT')
        require(any(value['metadata']['name'] == 'state' for value in item['spec']['volumeClaimTemplates']), 'CONFLICT')
        name = 'state-'+role+'-0'
        pvc = json.loads(op.k('get', 'pvc', name, '-o', 'json'))
        require(pvc['metadata']['name'] == name and pvc['metadata']['namespace'] == op.namespace
                and pvc['metadata']['labels']['app.kubernetes.io/instance'] == op.release
                and pvc['metadata']['labels']['app.kubernetes.io/name'] == role, 'UNAUTHORIZED')
        selected[role] = dict(image=image, workload_uid=item['metadata']['uid'],
            pvc=dict(name=name, uid=pvc['metadata']['uid'], spec=pvc['spec']))
    return namespace['metadata']['uid'], selected


def run(op, output):
    output = Path(output)
    report = dict(schema='quiesced-native-stage-observations/1', namespace=op.namespace,
        status='NOT_RUN', classification='EXISTING_DIAGNOSTICS_READ_ONLY', additional_live_generations=0,
        limits=dict(files_per_owner=2, bytes_per_file=1048576), owners={},
        capture_scope='Previously recorded best-effort diagnostics; file caps or process interruption can omit observations.',
        interpretation='Nested durations are nonadditive; observed method wall time includes waits. No token, throughput or service-wide benchmark claim.')
    with output.open('xb') as stream:
        stream.write(canonical(report))
    try:
        namespace_uid, selected = stopped(op)
        report.update(namespace_uid=namespace_uid, selected=selected,
                      observer_sha256=digest(Path(__file__).read_bytes()))
        for role in ROLES:
            require(stopped(op) == (namespace_uid, selected), 'CONFLICT')
            entry = selected[role]
            helper = 'reference-copy-'+role
            try:
                require(op.helper(role, entry['image'], entry['pvc']['name'], readonly=True) == helper, 'CONFLICT')
                pod = json.loads(op.k('get', 'pod', helper, '-o', 'json'))
                spec = pod['spec']
                mounts = spec['containers'][0]['volumeMounts']
                require(len(spec['containers']) == len(spec['volumes']) == 1
                    and spec['containers'][0]['image'] == entry['image']
                    and len(mounts) == 1 and mounts[0]['name'] == 'state'
                    and mounts[0]['mountPath'] == '/state' and mounts[0]['readOnly'] is True
                    and 'subPath' not in mounts[0] and spec['volumes'][0]['name'] == 'state'
                    and spec['volumes'][0]['persistentVolumeClaim'] == {'claimName':entry['pvc']['name'],'readOnly':True}
                    and spec['automountServiceAccountToken'] is False, 'UNAUTHORIZED')
                source = inspect.getsource(parse_timings)+'\n'+inspect.getsource(owned_timings)
                source += '\nimport json\nprint(json.dumps(owned_timings("/state", '+repr(role)+', "/opt/fusion")))\n'
                observed = json.loads(op.k('exec', '-i', helper, '--', PYTHON, '-', data=source, timeout=30))
                require(observed['role'] == role and observed['timing_status'] in ('OBSERVED', 'NOT_OBSERVED'), 'CONFLICT')
                observed['helper_image_ids'] = [x['imageID'] for x in pod['status']['containerStatuses']]
                report['owners'][role] = observed
            finally:
                op.k('delete', 'pod', helper, '--ignore-not-found=true', '--wait=true', '--timeout=60s', timeout=70)
            require(stopped(op) == (namespace_uid, selected), 'CONFLICT')
            output.write_bytes(canonical(report))
        require(len({x['scope'] for x in report['owners'].values()}) == 1, 'CONFLICT')
        observed_count = sum(value['timing_status'] == 'OBSERVED' for value in report['owners'].values())
        timing_status = 'PASS' if observed_count == len(ROLES) else 'PARTIAL' if observed_count else 'NOT_OBSERVED'
        report.update(status=timing_status, timing_gate=timing_status, read_only_ownership_gate='PASS',
                      helpers_deleted=True, original_remains_quiesced=True,
                      pvc_identity_and_spec_unchanged=True, pvc_mounts_read_only=True)
    except Exception as error:
        report.update(status='FAILED', failure=dict(type=type(error).__name__, code=getattr(error, 'code', None)))
        raise
    finally:
        output.write_bytes(canonical(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('kubeconfig', 'context', 'namespace', 'output'):
        parser.add_argument('--'+field, required=True)
    args = parser.parse_args()
    run(Operator(args.kubeconfig, args.context, args.namespace), args.output)


if __name__ == '__main__':
    main()
