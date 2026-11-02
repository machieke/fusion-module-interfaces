"""Fenced-restore example fixtures; no cluster, HTTPS or provider claim.

Actual export/restore, SQLite checkpoint and diagnostics are exercised locally.
Operator orchestration, TLS bytes and HTTP replies below are explicitly authored
fixtures. The selected Helm chart and Secret helper execute offline; neither
kubectl nor OpenSSL is executed by the Secret-helper fixture.
"""
import copy
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from examples import preview_restore_qualification as q
from fusion.contracts import ContractError, canonical, digest
from integration.single_node import backup_payload
from integration.single_node.preview_values import generate
from tests.test_phase2_operator_values import image_manifest_fixture

import yaml


SCOPE = 'synthetic-restore-example-fixture'
CLONE = 'omega-ref-restore-example-clone'
IMAGE = dict(repository='fixture/image', digest='sha256:'+'a'*64, tag='fixture', pullPolicy='Never')
ROOT = Path(__file__).resolve().parents[1]
CHART = Path(os.environ.get('PHASE2_RESTORE_TEST_CHART', ROOT/'deploy/helm/omega-fusion'))


def values():
    roles = list(q.ROUTES) + ['f1r3node']
    return dict(image=IMAGE, components={role: dict(enabled=True, existingSecret=role+'-tls-auth',
        config=dict(nativeEnabled=True, workerEnabled=True, test={'pause_at': 'fixture'})) for role in roles},
        futureLive=dict(enabled=False, activated=False), testFaultsEnabled=True,
        preview=dict(enabled=True, profile=q.COMPOSITION, scope=SCOPE, model_boundary='RECORDED_FIXTURE',
            agents={'omega-agent': {'principal': 'A'}, 'omega-agent-b': {'principal': 'B'}},
            memory={'enabled': True}, tasks={'enabled': True}, cognition={'enabled': True}, inspection={'enabled': True},
            chain=dict(enabled=True, nodeEnabled=True, isolationVerified=True, registration={'fixture': 'old-approval'},
                       public_key='fixture-public', wallet_address='fixture-address')))


class RestoreExampleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def denied(self, code, fn, *args):
        with self.assertRaises(ContractError) as caught:
            fn(*args)
        self.assertEqual(caught.exception.code, code)

    def roundtrip(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'owner-seal.json').write_bytes(canonical(dict(role='omega-agent', scope=SCOPE, composition=q.COMPOSITION)))
        session = source / 'sessions' / '00000000-0000-0000-0000-000000000001'
        session.mkdir(parents=True)
        for path, tables in ((source/'session-inbox.sqlite', ('preview_sessions',)),
                (session/'caller.sqlite', ('preview_native_inputs', 'preview_context_views', 'preview_context_captures',
                    'preview_task_outbox', 'app_model_calls', 'app_occurrences'))):
            with sqlite3.connect(path) as db:
                db.execute('PRAGMA journal_mode=WAL')
                for table in tables:
                    db.execute('CREATE TABLE '+table+'(calls INTEGER, result TEXT)')
                    db.execute('INSERT INTO '+table+' VALUES(3,?)', ('synthetic retained fixture',))
        (source / 'initial-view.json').write_bytes(canonical({'generation': 'fixture-retained-generation', 'head': {'sequence': 7}}))
        output = io.BytesIO()
        with patch.object(backup_payload.sys, 'stdout', SimpleNamespace(buffer=output)):
            backup_payload.export(source, 'omega-agent')
        raw = output.getvalue()
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            manifest = json.load(archive.extractfile('backup-manifest.json'))
        clone = self.root / 'clone'
        clone.mkdir()
        with patch.object(backup_payload.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(raw))), \
                patch.object(backup_payload.sys, 'stdout', io.StringIO()):
            backup_payload.restore(clone, 'omega-agent', CLONE)
        return clone, manifest

    def test_clone_values_disable_execution_and_signing_without_mutating_source(self):
        original = values(); snapshot = copy.deepcopy(original)
        cloned = q.clone_values({}, original)
        self.assertEqual(original, snapshot)
        self.assertEqual(cloned['preview']['scope'], SCOPE)
        self.assertFalse(cloned['components']['f1r3node']['enabled'])
        self.assertTrue(cloned['components']['fusion-commitment']['enabled'])
        self.assertEqual(cloned['preview']['chain'], dict(enabled=False, nodeEnabled=False,
                         isolationVerified=False, registration=None,
                         public_key='fixture-public', wallet_address='fixture-address'))
        self.assertFalse(cloned['testFaultsEnabled'])
        for component in cloned['components'].values():
            self.assertEqual(component['config'], dict(nativeEnabled=False, workerEnabled=False, test={}))

    def chart_values(self):
        manifest = image_manifest_fixture()
        manifest['images'].append(dict(kind='chain', repository='fixture.invalid/fusion-chain',
            local_tag='fixture.invalid/fusion-chain:reference-fixture', manifest_digest='sha256:'+'e'*64))
        selected = generate(manifest, SCOPE, mode='combined', chain=True)
        selected['preview']['chain'].update(nodeEnabled=True, isolationVerified=True,
            public_key='04'+'1'*128, wallet_address='synthetic-public-wallet',
            registration={'fixture': 'source-only-approval'})
        return q.clone_values(yaml.safe_load((CHART/'values.yaml').read_text()), selected)

    def render(self, selected):
        path = self.root/'clone-values.yaml'
        path.write_text(yaml.safe_dump(selected, sort_keys=False))
        return subprocess.run(['helm', 'template', 'omega', str(CHART),
            '-n', CLONE, '-f', str(path)], capture_output=True, text=True, timeout=30)

    def test_real_chart_retains_public_metadata_without_execution_or_chain_workload(self):
        cloned = self.chart_values()
        rendered = self.render(cloned)
        self.assertEqual(rendered.returncode, 0, rendered.stderr)
        documents = [d for d in yaml.safe_load_all(rendered.stdout) if d]
        owners = {d['metadata']['name']:d for d in documents if d['kind']=='StatefulSet'}
        self.assertIn('fusion-commitment', owners)
        self.assertNotIn('f1r3node', owners)
        self.assertFalse(any(d['metadata']['name'].startswith('f1r3node') for d in documents))
        self.assertFalse(any(d['kind']=='Secret' for d in documents))
        for owner in owners.values():
            self.assertEqual(owner['spec']['replicas'], 1)
            self.assertEqual(owner['spec']['persistentVolumeClaimRetentionPolicy'],
                {'whenDeleted':'Retain','whenScaled':'Retain'})
        maps = [json.loads(d['data']['component.json']) for d in documents if d['kind']=='ConfigMap']
        self.assertEqual(len(maps), len(owners))
        expected = dict(enabled=False, nodeEnabled=False, isolationVerified=False,
            registration=None, public_key='04'+'1'*128, wallet_address='synthetic-public-wallet')
        for cfg in maps:
            self.assertEqual(cfg['preview']['chain'], expected)
            self.assertFalse(cfg['native_enabled'])
            self.assertFalse(cfg['worker_enabled'])
            self.assertFalse(cfg['enable_test_faults'])
            self.assertEqual(cfg['test'], {})
            self.assertEqual(cfg['preview']['model_boundary'], 'RECORDED_FIXTURE')
        for forbidden in ('signer.hex', 'validator.hex', 'source-only-approval', 'hostPath:'):
            self.assertNotIn(forbidden, rendered.stdout)

    def test_real_chart_rejects_the_original_missing_public_metadata_defect(self):
        cloned = self.chart_values()
        del cloned['preview']['chain']['public_key']
        del cloned['preview']['chain']['wallet_address']
        rendered = self.render(cloned)
        self.assertNotEqual(rendered.returncode, 0)
        self.assertIn("'/preview/chain'", rendered.stderr)
        self.assertIn('public_key', rendered.stderr)
        self.assertIn('wallet_address', rendered.stderr)

    def test_actual_secret_helper_omits_chain_keys_and_approval_with_public_metadata_retained(self):
        import builtins
        original_import = builtins.__import__
        def no_signing_import(name, *args, **kwargs):
            if name == 'cryptography' or name.startswith('cryptography.'):
                raise AssertionError('Disabled restore must not load signing libraries')
            return original_import(name, *args, **kwargs)
        selected = self.chart_values()
        path = self.root/'clone-values.yaml'; path.write_text(yaml.safe_dump(selected))
        directory = self.root/'fresh-fixture-secrets'
        observed = {}

        def subprocess_fixture(command, **kwargs):
            if command[0] == 'openssl':
                for flag in ('-out', '-keyout'):
                    if flag in command:
                        (Path(kwargs['cwd'])/command[command.index(flag)+1]).write_bytes(b'EXPLICIT TLS FIXTURE')
                return SimpleNamespace(returncode=0)
            self.assertEqual(command[0], 'kubectl')
            self.assertEqual(command[command.index('--context')+1], 'fixture-no-cluster')
            doc = json.loads(kwargs['input'])
            self.assertEqual(doc['metadata']['namespace'], CLONE)
            # Keep names only: never retain or report generated credentials.
            observed[doc['metadata']['name']] = set(doc['data'])
            return SimpleNamespace(returncode=0)

        with patch.object(sys, 'path', list(sys.path)):
            helper = runpy.run_path(str(ROOT/'deploy/single-node/create_secrets.py'), run_name='secret_helper_test')
        args = ['fixture-helper', '--kubeconfig', 'never-opened', '--context', 'fixture-no-cluster',
            '--namespace', CLONE, '--directory', str(directory), '--preview-values', str(path)]
        with patch.object(sys, 'argv', args), patch.object(subprocess, 'run', side_effect=subprocess_fixture), \
                patch.object(os, 'umask'), contextlib.redirect_stdout(io.StringIO()), \
                patch.object(builtins, '__import__', side_effect=no_signing_import):
            helper['main']()
        self.assertIn('fusion-commitment-tls-auth', observed)
        self.assertNotIn('f1r3node-tls-auth', observed)
        for keys in observed.values():
            self.assertFalse({'signer.hex', 'validator.hex', 'commit-observer-A-token',
                'commit-observer-B-token', 'commit-storage-token'} & keys)
        self.assertFalse((directory/'chain-public.json').exists())
        self.assertFalse(list(directory.glob('*.hex')))

    def test_live_profile_private_scope_and_unpinned_image_are_refused(self):
        for field, value, code in (('model_boundary', 'LIVE', 'UNAUTHORIZED'), ('scope', 'private-corpus', 'UNAUTHORIZED')):
            selected = values(); selected['preview'][field] = value
            self.denied(code, q.clone_values, {}, selected)
        selected = values(); selected['image'] = dict(repository='fixture/image', tag='moving')
        self.denied('CONFLICT', q.clone_values, {}, selected)
        selected = values(); selected['futureLive']['enabled'] = True
        self.denied('UNAUTHORIZED', q.clone_values, {}, selected)

    def test_actual_checkpoint_restore_hashes_counters_and_views_match_without_new_files(self):
        clone, manifest = self.roundtrip()
        before = {str(p.relative_to(clone)) for p in clone.rglob('*') if p.is_file()}
        observed = q.verify_owner(clone, 'omega-agent', CLONE, manifest)
        after = {str(p.relative_to(clone)) for p in clone.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(observed['status'], 'MATCH')
        self.assertEqual(observed['retained_views'], 1)
        self.assertEqual(observed['tables']['session-1/caller.sqlite:app_model_calls']['calls_sum'], 3)
        self.assertEqual(observed['extra_files'], ['restore-fence.json'])

    def test_changed_restored_database_or_new_journal_is_refused(self):
        clone, manifest = self.roundtrip()
        with (clone/'session-inbox.sqlite').open('ab') as stream:
            stream.write(b'fixture-corruption')
        self.denied('CONFLICT', q.verify_owner, clone, 'omega-agent', CLONE, manifest)

    def test_only_known_restore_process_extras_are_permitted(self):
        clone, manifest = self.roundtrip()
        (clone/'owner.lock').touch(); (clone/'restore-process.json').write_text('{}')
        self.assertEqual(q.verify_owner(clone, 'omega-agent', CLONE, manifest)['status'], 'MATCH')
        (clone/'new-provider.sqlite').write_bytes(b'new effect')
        self.denied('CONFLICT', q.verify_owner, clone, 'omega-agent', CLONE, manifest)

    def test_wrong_fence_namespace_and_symlink_are_refused(self):
        clone, manifest = self.roundtrip()
        self.denied('CONFLICT', q.verify_owner, clone, 'omega-agent', 'omega-ref-wrong', manifest)
        (clone/'outside').symlink_to(self.root)
        self.denied('UNAUTHORIZED', q.verify_owner, clone, 'omega-agent', CLONE, manifest)

    def test_changed_checkpoint_counters_or_retained_views_are_refused(self):
        clone, manifest = self.roundtrip()
        changed = copy.deepcopy(manifest)
        changed['owner_checkpoint']['tables']['session-inbox.sqlite:preview_sessions']['calls_sum'] = 4
        fence = json.loads((clone/'restore-fence.json').read_text())
        fence['backup_manifest_sha256'] = digest(canonical(changed))
        (clone/'restore-fence.json').write_bytes(canonical(fence))
        self.denied('CONFLICT', q.verify_owner, clone, 'omega-agent', CLONE, changed)

    def test_nonempty_checkpoint_wal_is_refused_even_with_consistent_hash(self):
        clone, manifest = self.roundtrip()
        name = 'session-inbox.sqlite-wal'; raw = b'nonempty fixture WAL'
        (clone/name).write_bytes(raw)
        manifest['files'][name] = dict(bytes=len(raw), sha256=digest(raw))
        fence = json.loads((clone/'restore-fence.json').read_text())
        fence['backup_manifest_sha256'] = digest(canonical(manifest))
        (clone/'restore-fence.json').write_bytes(canonical(fence))
        self.denied('NOT_AVAILABLE', q.verify_owner, clone, 'omega-agent', CLONE, manifest)

    def test_actual_archives_bind_owner_scope_images_and_excluded_chain(self):
        self.roundtrip()
        sources = {'omega-agent': self.root/'source', 'fusion-commitment': self.root/'commitment'}
        sources['fusion-commitment'].mkdir()
        (sources['fusion-commitment']/'owner-seal.json').write_bytes(canonical(dict(
            composition=q.COMPOSITION, role='fusion-commitment', scope=SCOPE)))
        archive_root = self.root/'archives'; archive_root.mkdir()
        manifest = dict(schema='synthetic-quiesced-backup/1', authority_excluded=True, owners={},
            excluded_owners={'f1r3node': dict(original_retained=True, original_quiesced=True)})
        selected = dict(components={role: dict(image=IMAGE) for role in sources}, preview=dict(scope=SCOPE))
        for role, source in sources.items():
            output = io.BytesIO()
            with patch.object(backup_payload.sys, 'stdout', SimpleNamespace(buffer=output)):
                backup_payload.export(source, role)
            raw = output.getvalue(); name = role+'.tar.gz'; (archive_root/name).write_bytes(raw)
            manifest['owners'][role] = dict(file=name, sha256=digest(raw), bytes=len(raw), image=q.image_ref(IMAGE))
        self.assertEqual(set(q.archive_manifests(archive_root, manifest, selected)), set(sources))
        changed = copy.deepcopy(selected); changed['preview']['scope'] = 'synthetic-different'
        self.denied('CONFLICT', q.archive_manifests, archive_root, manifest, changed)
        changed = copy.deepcopy(manifest); changed['excluded_owners'] = {}
        self.denied('CONFLICT', q.archive_manifests, archive_root, changed, selected)
        changed = copy.deepcopy(manifest); changed['owners']['omega-agent']['image'] = 'fixture/image:unpinned'
        self.denied('CONFLICT', q.archive_manifests, archive_root, changed, selected)

    def test_coverage_requires_populated_new_native_and_owner_tables(self):
        tables = {f'fixture.sqlite:{table}': {'rows': 1} for group in q.TABLE_GROUPS.values() for table in group}
        observations = {'fixture': {'after': {'tables': tables}}}
        self.assertEqual(set(q.coverage(observations)), set(q.TABLE_GROUPS))
        tables['fixture.sqlite:workspace_effects']['rows'] = 0
        self.denied('NOT_AVAILABLE', q.coverage, observations)

    def test_tls_probe_authored_replies_require_all_health_and_denials(self):
        clone, _ = self.roundtrip()
        secret = self.root/'fixture-secret'; secret.mkdir()
        (secret/'session-operator-token').write_text('fixture-secret-never-publish')
        calls = []

        class ConnectionFixture:
            def __init__(self, *args, **kwargs): pass
            def request(self, method, path, body=None, headers=None):
                calls.append((method, path, headers)); self.method = method
            def getresponse(self):
                value = dict(role='omega-agent', ready=True, mode=q.MODE) if self.method == 'GET' else {'error': {'code': 'UNAUTHORIZED', 'retryable': False}}
                return SimpleNamespace(status=200, read=lambda _: canonical(value))
            def close(self): pass

        with patch.object(q.http.client, 'HTTPSConnection', ConnectionFixture), \
                patch.object(q.ssl, 'create_default_context', return_value=SimpleNamespace()):
            result = q.tls_checks('omega-agent', CLONE, 8443, clone, secret)
        self.assertEqual(len(calls), 3+len(q.ROUTES['omega-agent']))
        self.assertTrue(all(x[2]['Authorization'] == 'Bearer fixture-secret-never-publish' for x in calls))
        self.assertNotIn('fixture-secret-never-publish', json.dumps(result))


class OrchestrationFixtureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        chart = self.root/'chart'; chart.mkdir(); (chart/'values.yaml').write_text('{}')
        source = self.root/'source.yaml'; source.write_text(json.dumps(values()))
        helper = self.root/'secret_helper.py'; helper.write_text('# explicitly mocked helper\n')
        self.args = SimpleNamespace(kubeconfig='fixture-kubeconfig', context='fixture-context',
            source_namespace='omega-ref-source-fixture', clone_namespace=CLONE, chart=str(chart),
            values=str(source), secret_helper=str(helper), output=str(self.root/'report.json'))
        self.events, self.ops = [], {}
        self.fail_helm = False

    def operators(self):
        owner = self
        tables = {f'fixture.sqlite:{table}': {'rows': 1} for group in q.TABLE_GROUPS.values() for table in group}

        class FixtureOperator:
            def __init__(self, kubeconfig, context, namespace):
                self.kubeconfig, self.context, self.namespace, self.release = kubeconfig, context, namespace, 'omega'
                self.deployed = namespace == owner.args.source_namespace
                self.paused = False; owner.ops[namespace] = self
            def preflight(self): owner.events.append(('preflight', self.namespace))
            def owned(self): return {'metadata': {'uid': 'fixture-namespace'}}
            def create(self): owner.events.append(('create', self.namespace))
            def backup(self, path):
                self.quiesce(); Path(path).mkdir()
                owner.events.append(('backup', self.namespace))
                return dict(schema='synthetic-quiesced-backup/1', authority_excluded=True,
                    consistency='explicit operator fixture', excluded_owners={'f1r3node': {'original_retained': True, 'original_quiesced': True}},
                    owners={role: dict(image=q.image_ref(IMAGE)) for role in q.ROUTES})
            def restore(self, path):
                owner.events.append(('restore', self.namespace)); return dict(status='RESTORED_FENCED', automatic_resume=False)
            def workloads(self):
                roles = list(q.ROUTES) + (['f1r3node'] if self.namespace == owner.args.source_namespace else [])
                return [dict(metadata={'name': role}, spec=dict(replicas=0 if self.paused else 1,
                    template={'spec': {'containers': [{'image': q.image_ref(IMAGE)}]}})) for role in roles]
            def quiesce(self): self.paused = True; owner.events.append(('quiesce', self.namespace))
            def command(self, command, **kwargs):
                if command[0] == 'helm':
                    self.deployed = True; self.paused = False; owner.events.append(('helm', self.namespace))
                    if owner.fail_helm: raise RuntimeError('CREDENTIAL_SUPPRESSION_SENTINEL')
                else:
                    owner.events.append(('secrets', self.namespace))
                    assert '--preview-values' in command
                    clone = json.loads(Path(command[command.index('--preview-values')+1]).read_text())
                    assert clone['preview']['chain']['enabled'] is False
                    owner.secret_directory = Path(command[command.index('--directory')+1])
                    owner.secret_directory.mkdir()
                return ''
            def k(self, *args, **kwargs):
                if args[:2] == ('get', 'namespace'): return ''
                if args[:2] == ('get', 'statefulsets'): return json.dumps({'items': self.workloads() if self.deployed else []})
                if args[:2] == ('get', 'pods'):
                    pods = [] if self.paused else [dict(metadata={'name': r+'-0', 'uid': 'fixture-'+r},
                        spec={'containers': [{'image': q.image_ref(IMAGE)}]},
                        status={'containerStatuses': [{'ready': True, 'imageID': 'fixture-image'}]}) for r in q.ROUTES]
                    return json.dumps({'items': pods})
                if args[:2] == ('get', 'pvc'):
                    return json.dumps({'items': [dict(metadata={'name': 'state-f1r3node-0', 'uid': 'fixture-pvc'}, status={'phase': 'Bound'})]})
                if args[0] == 'exec':
                    assert PYTHON_FIXTURE in args and 'observe_owner' in kwargs['data']
                    return json.dumps({'after': {'tables': tables}, 'owner_state_unchanged': True})
                raise AssertionError(args)
        return FixtureOperator

    def run_fixture(self):
        yaml_fixture = SimpleNamespace(safe_load=json.loads, safe_dump=lambda v, **_: json.dumps(v))
        owner_manifests = {role: {'role': role} for role in q.ROUTES}
        with patch.dict(sys.modules, {'yaml': yaml_fixture}), patch.object(q, 'Operator', self.operators()), \
                patch.object(q, 'archive_manifests', return_value=owner_manifests):
            return q.qualify(self.args)

    def test_order_fresh_secrets_final_quiescence_and_scratch_cleanup(self):
        result = self.run_fixture()
        self.assertEqual(result['status'], 'PASS')
        order = [event[0] for event in self.events]
        self.assertLess(order.index('backup'), order.index('restore'))
        self.assertLess(order.index('restore'), order.index('secrets'))
        self.assertLess(order.index('secrets'), order.index('helm'))
        self.assertTrue(all(x.paused for x in self.ops.values()))
        self.assertFalse(self.secret_directory.exists())
        self.assertEqual(result['chain'], 'NOT_RESTORED')
        self.assertEqual(result['additional_live_generations'], 0)

    def test_helm_failure_still_quiesces_both_and_suppresses_raw_diagnostics(self):
        self.fail_helm = True
        result = self.run_fixture()
        self.assertEqual(result['status'], 'FAILED')
        self.assertTrue(all(x.paused for x in self.ops.values()))
        self.assertNotIn('CREDENTIAL_SUPPRESSION_SENTINEL', Path(self.args.output).read_text())
        self.assertFalse(self.secret_directory.exists())


PYTHON_FIXTURE = '/opt/native/python/bin/python3.12'

if __name__ == '__main__':
    unittest.main()
