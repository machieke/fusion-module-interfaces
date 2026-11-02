"""Bounded operator drill for an authority-free, fenced synthetic preview clone.

Run only with explicit task-owned source/clone namespaces. Reuses Operator's
quiesced backup/restore; no application, model, worker or chain is resumed.
Only the sanitized report survives host scratch cleanup. Both PVC sets remain
retained and both namespaces finish quiesced. This is not failover or migration.
"""
import argparse
import copy
import hashlib
import http.client
import json
import re
import socket
import sqlite3
import ssl
import sys
import tarfile
import tempfile
from pathlib import Path
from unittest.mock import patch

from fusion.contracts import canonical, digest, require
from integration.single_node.reference_ops import Operator, PYTHON


COMPOSITION = 'omega-single-node-developer-preview/1'
MODE = 'READ_ONLY_RECONCILIATION'
MAX_FILES = 20000
MAX_BYTES = 512 * 1024 * 1024
EXTRAS = {'owner.lock', 'restore-fence.json', 'restore-process.json'}
ROUTES = {
    'omega-agent': ('/preview/session', '/preview/task-ingress'),
    'omega-agent-b': ('/preview/session', '/preview/task-ingress'),
    'fusion-execution': ('/s01', '/preview/facets', '/preview/inspection'),
    'fusion-storage': ('/s01', '/reference-cognition', '/preview/memory', '/memory-source', '/memory-initial', '/s03-read', '/s03-append'),
    'fusion-messaging': ('/s01', '/preview/tasks', '/preview/inspection', '/preview/inspection-completion', '/s06-mailbox'),
    'fusion-search': ('/s03-read', '/s03-append', '/preview/memory'),
    'fusion-embedding': ('/s03-encode',),
    'fusion-model': ('/preview/model',),
    'fusion-episodes': ('/preview/facets', '/reference-cognition'),
    'fusion-beliefs': ('/reference-cognition',),
    'fusion-attention': ('/reference-cognition',),
    'fusion-relations': ('/preview/facets', '/reference-cognition'),
    'fusion-exact-search': ('/reference-cognition',),
    'fusion-commitment': ('/preview/commitment',),
}
TABLE_GROUPS = {
    'native_sessions': ('preview_sessions', 'preview_native_inputs'),
    'working_context': ('preview_context_views', 'preview_context_captures'),
    'tasks': ('preview_task_outbox', 'task_ingress'),
    'lifecycle': ('lifecycle_events', 'lifecycle_intents'),
    'relations': ('preview_relation_events', 'preview_relation_intents'),
    'workspace': ('workspace_files', 'workspace_effects'),
}


def sha_file(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while raw := stream.read(1024 * 1024):
            result.update(raw)
    return result.hexdigest()


def merge(base, overrides):
    result = copy.deepcopy(base)
    for key, value in overrides.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else copy.deepcopy(value)
    return result


def image_ref(value):
    require(type(value) is dict and re.fullmatch(r'sha256:[0-9a-f]{64}', value.get('digest', '')) is not None, 'CONFLICT')
    require(type(value.get('repository')) is str and re.fullmatch(r'[a-z0-9][a-z0-9./_-]{0,200}', value['repository']) is not None, 'CONFLICT')
    return value['repository'] + '@' + value['digest']


def clone_values(defaults, source):
    value = merge(defaults, source)
    preview = value.get('preview', {})
    require(preview.get('enabled') is True and preview.get('profile') == COMPOSITION, 'UNSUPPORTED_PROFILE')
    require(preview.get('model_boundary') == 'RECORDED_FIXTURE', 'UNAUTHORIZED')
    require(type(preview.get('scope')) is str and re.fullmatch(r'synthetic-[a-z0-9][a-z0-9-]{0,53}', preview['scope']) is not None, 'UNAUTHORIZED')
    require(set(preview.get('agents', {})) == {'omega-agent', 'omega-agent-b'}, 'UNSUPPORTED_PROFILE')
    for section in ('memory', 'tasks', 'cognition', 'inspection'):
        require(preview.get(section, {}).get('enabled') is True, 'UNSUPPORTED_PROFILE')
    require(not value.get('futureLive', {}).get('enabled') and not value.get('futureLive', {}).get('activated'), 'UNAUTHORIZED')
    value['futureLive'] = dict(enabled=False, activated=False)
    value['testFaultsEnabled'] = False
    value.setdefault('networkPolicy', {})['enabled'] = True
    # With f1r3node excluded, existing Secret generation must also have chain
    # disabled: no fresh signing key or execution authority belongs in a clone.
    # Public identity metadata remains required by the closed chart schema.
    # Retaining it grants no signing, node-start or approval authority.
    chain = preview.setdefault('chain', {})
    chain.update(enabled=False, nodeEnabled=False, isolationVerified=False, registration=None)
    roles = set()
    for role, component in value['components'].items():
        component.setdefault('config', {}).update(nativeEnabled=False, workerEnabled=False, test={})
        if role == 'f1r3node':
            component['enabled'] = False
        if component.get('enabled', True):
            require(role in ROUTES, 'UNSUPPORTED_PROFILE')
            require(component.get('existingSecret') == role + '-tls-auth', 'UNSUPPORTED_PROFILE')
            component['image'] = copy.deepcopy(component.get('image', value['image']))
            image_ref(component['image'])
            component['image']['pullPolicy'] = 'Never'
            roles.add(role)
    require({'omega-agent', 'omega-agent-b', 'fusion-execution', 'fusion-storage', 'fusion-messaging',
             'fusion-search', 'fusion-embedding', 'fusion-model', 'fusion-episodes', 'fusion-beliefs',
             'fusion-attention', 'fusion-relations'} <= roles, 'UNSUPPORTED_PROFILE')
    return value


def archive_manifests(root, manifest, values):
    from integration.single_node.backup_payload import safe_name, synthetic_seal
    require(manifest.get('schema') == 'synthetic-quiesced-backup/1' and manifest.get('authority_excluded') is True, 'CONFLICT')
    roles = {r for r, c in values['components'].items() if c.get('enabled', True)}
    require(roles == set(manifest['owners']) and 'f1r3node' not in roles, 'CONFLICT')
    require(set(manifest.get('excluded_owners', {})) == {'f1r3node'} and
            manifest['excluded_owners']['f1r3node'].get('original_retained') is True and
            manifest['excluded_owners']['f1r3node'].get('original_quiesced') is True and
            'fusion-commitment' in roles, 'CONFLICT')
    observed = {}
    for role, entry in manifest['owners'].items():
        require(entry['file'] == role + '.tar.gz', 'CONFLICT')
        path = Path(root) / entry['file']
        require(path.stat().st_size == entry['bytes'] <= MAX_BYTES and sha_file(path) == entry['sha256'], 'CONFLICT')
        require(entry['image'] == image_ref(values['components'][role]['image']), 'CONFLICT')
        with tarfile.open(path, 'r:gz') as archive:
            members = archive.getmembers()
            require(len(members) <= MAX_FILES and sum(m.size for m in members) <= MAX_BYTES, 'OVERLOADED')
            require(len({m.name for m in members}) == len(members) and all(m.isfile() for m in members), 'CONFLICT')
            item = json.load(archive.extractfile('backup-manifest.json'))
            require(item['schema'] == 'synthetic-owner-backup/1' and item['role'] == role and item['excluded_authority'] is True, 'CONFLICT')
            synthetic_seal(item['seal'], role)
            require({k:v for k,v in item['seal'].items() if k!='backend_layout'} ==
                dict(composition=COMPOSITION, role=role, scope=values['preview']['scope']), 'CONFLICT')
            require('restore-fence.json' not in item['files'], 'CONFLICT')
            require({m.name for m in members} == {'backup-manifest.json'} | {'state/' + n for n in item['files']}, 'CONFLICT')
            for name, description in item['files'].items():
                safe_name(Path(name))
                if name.endswith('-wal'):
                    require(description['bytes'] == 0, 'NOT_AVAILABLE')
            observed[role] = item
    return observed


def normalized_diagnostics(value):
    return {k: v for k, v in value.items() if k not in ('restore_fenced', 'process_rss_bytes')}


def verify_owner(root, role, namespace, manifest):
    """Read this owner's files only; immutable SQLite ignores no uncheckpointed WAL."""
    from integration.single_node.backup_payload import safe_name
    from integration.single_node import diagnostics
    root = Path(root)
    require(role in ROUTES and manifest['role'] == role, 'CONFLICT')
    require(manifest['seal']['composition'] == COMPOSITION and manifest['seal']['scope'].startswith('synthetic-'), 'UNAUTHORIZED')
    fence = json.loads((root / 'restore-fence.json').read_text())
    require(fence == dict(mode=MODE, role=role, namespace=namespace,
        backup_manifest_sha256=digest(canonical(manifest)), original_scope=manifest['seal']['scope'],
        external_effect_authority=False), 'CONFLICT')
    require(json.loads((root / 'owner-seal.json').read_text()) == manifest['seal'], 'CONFLICT')
    files = {}
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'UNAUTHORIZED')
        if path.is_file():
            name = str(path.relative_to(root))
            safe_name(Path(name))
            files[name] = path
            require(len(files) <= MAX_FILES, 'OVERLOADED')
    require(set(files) - set(manifest['files']) <= EXTRAS and set(manifest['files']) <= set(files), 'CONFLICT')
    require(sum(p.stat().st_size for p in files.values()) <= MAX_BYTES, 'OVERLOADED')
    for name, expected in manifest['files'].items():
        require(files[name].stat().st_size == expected['bytes'] and sha_file(files[name]) == expected['sha256'], 'CONFLICT')
        if name.endswith('-wal'):
            require(expected['bytes'] == 0, 'NOT_AVAILABLE')
    actual_views = {name: json.loads((root / name).read_text()) for name in manifest['retained_views']}
    require(actual_views == manifest['retained_views'], 'CONFLICT')
    connect = sqlite3.connect

    def immutable(database, *args, **kwargs):
        require(type(database) is str and database.startswith(root.absolute().as_uri() + '/') and
                database.endswith('?mode=ro') and kwargs.get('uri') is True, 'UNAUTHORIZED')
        return connect(database + '&immutable=1', *args, **kwargs)

    with patch.object(sqlite3, 'connect', side_effect=immutable):
        counters = diagnostics.inspect(root)
    require(counters['restore_fenced'] is True, 'CONFLICT')
    require(normalized_diagnostics(counters) == normalized_diagnostics(manifest['owner_checkpoint']), 'CONFLICT')
    return dict(status='MATCH', manifest_sha256=digest(canonical(manifest)), files=len(manifest['files']),
        bytes=sum(x['bytes'] for x in manifest['files'].values()),
        retained_views=len(actual_views), retained_views_sha256=digest(canonical(actual_views)),
        diagnostic_sha256=digest(canonical(normalized_diagnostics(counters))),
        tables=counters['tables'], extra_files=sorted(set(files) - set(manifest['files'])))


def tls_checks(role, namespace, port, root=Path('/state'), secrets=Path('/secrets')):
    """Owner-local HTTPS with DNS SAN verification; no pod-to-pod claim here."""
    require(role in ROUTES and (root / 'restore-fence.json').is_file(), 'UNAUTHORIZED')
    hostname = role + '.' + namespace + '.svc.cluster.local'
    context = ssl.create_default_context(cafile=str(secrets / 'ca.crt'))
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    key = 'session-operator-token' if role.startswith('omega-agent') else 'caller-A-token'
    if not (secrets / key).is_file():
        key = 'caller-token'
    token = (secrets / key).read_text().strip()
    require(token and '\n' not in token and '\r' not in token, 'UNAUTHORIZED')

    class Connection(http.client.HTTPSConnection):
        def connect(self):
            raw = socket.create_connection(('127.0.0.1', port), timeout=3)
            self.sock = context.wrap_socket(raw, server_hostname=hostname)

    def request(method, path):
        connection = Connection(hostname, port, timeout=3, context=context)
        try:
            headers = {'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'}
            connection.request(method, path, body=b'{}' if method == 'POST' else None, headers=headers)
            response = connection.getresponse()
            raw = response.read(8193)
            require(response.status == 200 and len(raw) <= 8192, 'NOT_AVAILABLE')
            return json.loads(raw)
        finally:
            connection.close()

    health = {}
    for name in ('startup', 'ready', 'live'):
        value = request('GET', '/health/' + name)
        require(value == dict(role=role, ready=True, mode=MODE), 'NOT_AVAILABLE')
        health[name] = 'PASS'
    denied = {}
    for path in ROUTES[role]:
        value = request('POST', path)
        require(value == {'error': {'code': 'UNAUTHORIZED', 'retryable': False}}, 'UNAUTHORIZED')
        denied[path] = 'UNAUTHORIZED'
    return dict(health=health, posts=denied, transport='owner-local HTTPS with original image Python and DNS SAN validation')


def observe_owner(role, namespace, manifest):
    root = Path('/state')
    config = json.loads(Path('/config/component.json').read_text())
    require(config['role'] == role and config['preview']['scope'] == manifest['seal']['scope'], 'CONFLICT')
    require(config['native_enabled'] is False and config['worker_enabled'] is False and
            config['test'] == {} and config['enable_test_faults'] is False, 'UNAUTHORIZED')
    require(config['preview']['chain']['enabled'] is False and config['preview']['chain']['nodeEnabled'] is False
            and config['preview']['chain']['isolationVerified'] is False and config['preview']['chain']['registration'] is None, 'UNAUTHORIZED')
    process = json.loads((root / 'restore-process.json').read_text())
    require(process['role'] == role and process['mode'] == MODE and process['effect_authority'] is False, 'UNAUTHORIZED')
    require(not any(Path('/secrets').glob('*.hex')), 'UNAUTHORIZED')
    before = verify_owner(root, role, namespace, manifest)
    probes = tls_checks(role, namespace, config['https_port'])
    after = verify_owner(root, role, namespace, manifest)
    require(before == after, 'CONFLICT')
    return dict(before=before, after=after, tls=probes, owner_state_unchanged=True)


def coverage(observations):
    table_rows = {}
    for role, observed in observations.items():
        for path, counters in observed['after']['tables'].items():
            table_rows.setdefault(path.rsplit(':', 1)[1], []).append(dict(role=role, table=path, rows=counters['rows']))
    result = {}
    for group, tables in TABLE_GROUPS.items():
        result[group] = {table: table_rows.get(table, []) for table in tables}
        require(all(any(x['rows'] > 0 for x in result[group][table]) for table in tables), 'NOT_AVAILABLE')
    return result


def stopped(op):
    workloads = op.workloads()
    require(all(x['spec']['replicas'] == 0 for x in workloads), 'UNAUTHORIZED')
    require(not json.loads(op.k('get', 'pods', '-o', 'json'))['items'], 'NOT_AVAILABLE')
    return dict(status='QUIESCED', roles=sorted(x['metadata']['name'] for x in workloads))


def retained_pvcs(op):
    return [dict(name=x['metadata']['name'], uid=x['metadata']['uid'], phase=x['status']['phase'])
            for x in json.loads(op.k('get', 'pvc', '-l', 'app.kubernetes.io/instance=omega', '-o', 'json'))['items']]


def qualify(args):
    import yaml
    source = Operator(args.kubeconfig, args.context, args.source_namespace)
    clone = Operator(args.kubeconfig, args.context, args.clone_namespace)
    require(source.namespace != clone.namespace and all(re.fullmatch(r'omega-ref-[a-z0-9][a-z0-9-]{0,51}', n)
            for n in (source.namespace, clone.namespace)), 'UNAUTHORIZED')
    output = Path(args.output).resolve()
    require(not output.exists(), 'CONFLICT')
    chart, values_path, helper = Path(args.chart).resolve(), Path(args.values).resolve(), Path(args.secret_helper).resolve()
    require(chart.is_dir() and values_path.is_file() and helper.is_file(), 'NOT_AVAILABLE')
    values = clone_values(yaml.safe_load((chart / 'values.yaml').read_text()), yaml.safe_load(values_path.read_text()))
    output.parent.mkdir(parents=True, exist_ok=True)
    report = dict(schema='preview-fenced-restore-qualification/1', status='RUNNING',
        source_namespace=source.namespace, clone_namespace=clone.namespace,
        example_sha256=sha_file(__file__), source_values_sha256=sha_file(values_path),
        clone_values_sha256=digest(canonical(values)), secret_helper_sha256=sha_file(helper),
        additional_live_generations=0, chain='NOT_RESTORED', automatic_resume=False,
        classification='OPERATOR_FENCED_RESTORE_ONLY', owners={}, cleanup={})
    backup_started = clone_created = False
    scratch_root = None

    def save():
        output.write_bytes(canonical(report))

    try:
        source.preflight(); source.owned()
        require(not clone.k('get', 'namespace', clone.namespace, '--ignore-not-found', '-o', 'name').strip(), 'CONFLICT')
        selected_roles = {r for r, c in values['components'].items() if c.get('enabled', True)} | {'f1r3node'}
        original_workloads = source.workloads()
        require({x['metadata']['name'] for x in original_workloads} == selected_roles, 'CONFLICT')
        for workload in original_workloads:
            role = workload['metadata']['name']
            selected_image = values['components'][role].get('image', values['image'])
            require(workload['spec']['template']['spec']['containers'][0]['image'] == image_ref(selected_image), 'CONFLICT')
        with tempfile.TemporaryDirectory(prefix='preview-restore-private-') as scratch:
            scratch = Path(scratch)
            scratch_root = scratch
            backup_started = True
            manifest = source.backup(scratch / 'backup')
            owner_manifests = archive_manifests(scratch / 'backup', manifest, values)
            report['backup'] = dict(manifest_sha256=digest(canonical(manifest)), roles=sorted(owner_manifests),
                authority_excluded=True, chain=manifest.get('excluded_owners', {}).get('f1r3node'),
                consistency=manifest['consistency'])
            stopped(source); save()
            clone.create(); clone_created = True
            restored = clone.restore(scratch / 'backup')
            require(restored['status'] == 'RESTORED_FENCED' and not restored['automatic_resume'], 'CONFLICT')
            report['restore'] = restored
            clone_path = scratch / 'clone-values.yaml'
            clone_path.write_text(yaml.safe_dump(values, sort_keys=False))
            command = ([sys.executable, str(helper)] if helper.suffix == '.py' else [str(helper)])
            clone.command(command + ['--kubeconfig', clone.kubeconfig, '--context', clone.context,
                '--namespace', clone.namespace, '--directory', str(scratch / 'fresh-secrets'),
                '--preview-values', str(clone_path)], timeout=180)
            clone.command(['helm', 'upgrade', '--install', clone.release, str(chart), '--kubeconfig', clone.kubeconfig,
                '--kube-context', clone.context, '--namespace', clone.namespace, '-f', str(clone_path),
                '--wait', '--timeout', '180s'], timeout=200)
            pods = json.loads(clone.k('get', 'pods', '-l', 'app.kubernetes.io/instance=omega', '-o', 'json'))['items']
            require({p['metadata']['name'] for p in pods} == {r + '-0' for r in owner_manifests}, 'CONFLICT')
            report['pods'] = {}
            for pod in pods:
                role = pod['metadata']['name'][:-2]
                require(pod['spec']['containers'][0]['image'] == manifest['owners'][role]['image'], 'CONFLICT')
                statuses = pod['status'].get('containerStatuses', [])
                require(len(statuses) == 1 and statuses[0]['ready'] and statuses[0].get('imageID'), 'NOT_AVAILABLE')
                report['pods'][role] = dict(uid=pod['metadata']['uid'], image=pod['spec']['containers'][0]['image'], image_id=statuses[0]['imageID'])
            example = Path(__file__).read_text()
            for role, owner_manifest in sorted(owner_manifests.items()):
                code = "import json\nnamespace={'__name__':'fenced_owner_probe'}\nexec(compile(" + repr(example) + ",'<fenced-owner-probe>','exec'),namespace)\nprint(json.dumps(namespace['observe_owner'](" + repr(role) + ',' + repr(clone.namespace) + ',' + repr(owner_manifest) + ")))\n"
                raw = clone.k('exec', '-i', role + '-0', '--', PYTHON, '-', data=code, timeout=90)
                report['owners'][role] = json.loads(raw)
                save()
            report['coverage'] = coverage(report['owners'])
            report['no_new_effects'] = dict(basis='All archived owner file hashes and exact diagnostic counters unchanged before and after denial probes',
                model_reservations='UNCHANGED', workspace_effects='UNCHANGED', task_publications='UNCHANGED',
                retained_views='UNCHANGED', chain_submissions='UNCHANGED', deadlines_and_spent_budgets='UNCHANGED')
            report['status'] = 'PASS'
    except Exception as error:
        # Never publish subprocess stderr, commands, token material or payloads.
        report.update(status='FAILED', failure=dict(type=type(error).__name__, code=getattr(error, 'code', None)))
    finally:
        if clone_created:
            try:
                items = json.loads(clone.k('get', 'statefulsets', '-o', 'json'))['items']
                if items:
                    clone.quiesce(); report['cleanup']['clone'] = stopped(clone)
                else:
                    require(not json.loads(clone.k('get', 'pods', '-o', 'json'))['items'], 'NOT_AVAILABLE')
                    report['cleanup']['clone'] = dict(status='QUIESCED', roles=[])
                report['cleanup']['clone_pvcs'] = retained_pvcs(clone)
            except Exception as error:
                report['status'] = 'FAILED'; report['cleanup']['clone'] = dict(status='NOT_PROVEN', type=type(error).__name__, code=getattr(error, 'code', None))
        if backup_started:
            try:
                source.quiesce(); report['cleanup']['source'] = stopped(source)
                report['cleanup']['source_pvcs'] = retained_pvcs(source)
                if report.get('backup', {}).get('chain'):
                    require(any(x['name'] == 'state-f1r3node-0' for x in report['cleanup']['source_pvcs']), 'NOT_AVAILABLE')
            except Exception as error:
                report['status'] = 'FAILED'; report['cleanup']['source'] = dict(status='NOT_PROVEN', type=type(error).__name__, code=getattr(error, 'code', None))
        report['cleanup']['host_backup_and_secret_scratch'] = ('NOT_CREATED' if scratch_root is None
            else 'NOT_REMOVED' if scratch_root.exists() else 'REMOVED')
        if report['cleanup']['host_backup_and_secret_scratch'] == 'NOT_REMOVED':
            report['status'] = 'FAILED'
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig', 'context', 'source-namespace', 'clone-namespace', 'values', 'chart', 'secret-helper', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    try:
        result = qualify(args)
    except Exception as error:
        print(json.dumps(dict(status='FAILED_BEFORE_REPORT', failure=dict(type=type(error).__name__,
            code=getattr(error, 'code', None)), additional_live_generations=0)))
        raise SystemExit(1) from None
    print(json.dumps(dict(status=result['status'], report=str(Path(args.output).resolve()),
                         chain='NOT_RESTORED', additional_live_generations=0)))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
