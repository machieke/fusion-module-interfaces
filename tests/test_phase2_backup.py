"""Isolated preview backup fixtures; no provider, cluster or migration claim.

The actual exporter/importer handles each owner's fresh directory separately.
SQLite rows model retained task/context/lifecycle/relation/workspace state;
restoration is observation-only and never replays those effects.
"""
import io
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError, canonical, digest
from fusion.preview_context import WorkingContext
from integration.single_node import backup_payload as backup
from integration.single_node.reference_ops import Operator, PYTHON
from integration.single_node.restore_host import allowed


COMPOSITION = 'omega-single-node-developer-preview/1'
SCOPE = 'synthetic-backup-fixture'


class MaintenanceMountPolicy(unittest.TestCase):
    """Actual helper payload; apply/wait are explicit offline Kubernetes fixtures.

    This checks the requested policy, not kubelet filesystem behavior. With a
    matching volume root, OnRootMismatch avoids recursively widening the
    separately validated workspace directories during a maintenance mount.
    """
    def test_helper_requests_root_matching_policy_for_readwrite_and_readonly_mounts(self):
        operator = Operator('/fixture/never-opened', 'fixture-no-cluster', 'omega-ref-maintenance-fixture')
        image = 'fixture.invalid/caller@sha256:'+'a'*64
        for readonly in (False, True):
            with self.subTest(readonly=readonly):
                events = []
                with patch.object(operator, 'owned', side_effect=lambda: events.append(('owned',))), \
                        patch.object(operator, 'apply', side_effect=lambda value: events.append(('apply', value))), \
                        patch.object(operator, 'k', side_effect=lambda *args: events.append(('wait', args))):
                    name = operator.helper('fusion-execution', image, 'state-fusion-execution-0', readonly=readonly)
                self.assertEqual(name, 'reference-copy-fusion-execution')
                self.assertEqual([event[0] for event in events], ['owned', 'apply', 'wait'])
                pod = events[1][1]
                self.assertEqual(pod['kind'], 'Pod')
                self.assertEqual(pod['metadata']['namespace'], operator.namespace)
                self.assertEqual(pod['spec']['securityContext'], dict(runAsUser=1000,
                    runAsGroup=1000, runAsNonRoot=True, fsGroup=1000, fsGroupChangePolicy='OnRootMismatch'))
                self.assertFalse(pod['spec']['automountServiceAccountToken'])
                self.assertEqual(pod['spec']['restartPolicy'], 'Never')
                self.assertEqual(pod['spec']['volumes'], [dict(name='state',
                    persistentVolumeClaim=dict(claimName='state-fusion-execution-0', readOnly=readonly))])
                self.assertEqual(len(pod['spec']['containers']), 1)
                container = pod['spec']['containers'][0]
                self.assertEqual(container['image'], image)
                self.assertEqual(container['imagePullPolicy'], 'Never')
                self.assertEqual(container['securityContext'], dict(allowPrivilegeEscalation=False,
                    readOnlyRootFilesystem=True, capabilities=dict(drop=['ALL'])))
                self.assertEqual(container['volumeMounts'], [dict(name='state', mountPath='/state', readOnly=readonly)])
                self.assertEqual(container['command'][:2], [PYTHON, '-c'])
                self.assertNotIn('chmod', canonical(pod).decode())
                self.assertNotIn('chown', canonical(pod).decode())
                self.assertEqual(events[2][1], ('wait', '--for=condition=Ready',
                    'pod/reference-copy-fusion-execution', '--timeout=60s'))


class PreviewBackup(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)

    def owner(self, name='source', role='omega-agent', scope=SCOPE,
              composition=COMPOSITION):
        root = self.base / name
        root.mkdir()
        (root / 'owner-seal.json').write_bytes(canonical(dict(
            role=role, scope=scope, composition=composition)))
        return root

    def db(self, root, filename):
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(path)
        self.addCleanup(db.close)
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA wal_autocheckpoint=0')
        return db

    def export(self, root, role='omega-agent'):
        stream = io.BytesIO()
        with patch.object(backup.sys, 'stdout', SimpleNamespace(buffer=stream)):
            backup.export(root, role)
        return stream.getvalue()

    def restore(self, raw, root, role='omega-agent', namespace='omega-ref-backup-fixture'):
        root.mkdir(exist_ok=True)
        output = io.StringIO()
        with patch.object(backup.sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(raw))), \
                patch.object(backup.sys, 'stdout', output):
            backup.restore(root, role, namespace)
        return json.loads(output.getvalue())

    @staticmethod
    def unpack(raw):
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
            return {item.name: archive.extractfile(item).read()
                    for item in archive.getmembers()}

    @staticmethod
    def pack(files):
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, content in files.items():
                item = tarfile.TarInfo(name)
                item.mode = 0o600
                item.size = len(content)
                archive.addfile(item, io.BytesIO(content))
        return stream.getvalue()

    def denied(self, codes, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertIn(caught.exception.code, codes)

    def test_application_wal_context_tasks_and_original_limits_roundtrip(self):
        root = self.owner()
        db = self.db(root, 'sessions/fixture/application.sqlite')
        context = WorkingContext(db, lambda _: None)
        first = context.change('note-1', 'target', 'Synthetic retrieval task', 0)
        context.change('note-2', 'target', 'Retained later note', 1)
        db.executescript('''
            CREATE TABLE app_occurrences(id TEXT PRIMARY KEY, deadline INTEGER,
                attempts INTEGER, done INTEGER, result TEXT);
            CREATE TABLE fixture_tasks(identity TEXT PRIMARY KEY, sender TEXT,
                recipient TEXT, deadline INTEGER, calls INTEGER, state TEXT,
                retained_view TEXT);
        ''')
        retained = {'corpus': 'fixture-corpus', 'generation': 'g1', 'sequence': 7}
        with db:
            db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?,?)',
                       ('accepted-occurrence', 1700000000000, 3, 1, 'captured result'))
            db.execute('INSERT INTO fixture_tasks VALUES(?,?,?,?,?,?,?)',
                       ('task-1', 'A', 'B', 1700000000000, 24, 'captured',
                        canonical(retained).decode()))
        view = root / 'sessions/fixture/setup-view.json'
        view.write_bytes(canonical(retained))
        wal = Path(str(root / 'sessions/fixture/application.sqlite') + '-wal')
        self.assertGreater(wal.stat().st_size, 0)

        raw = self.export(root)
        self.assertEqual(wal.stat().st_size, 0)
        files = self.unpack(raw)
        manifest = json.loads(files['backup-manifest.json'])
        self.assertEqual(manifest['seal']['composition'], COMPOSITION)
        self.assertEqual(manifest['retained_views'],
                         {'sessions/fixture/setup-view.json': retained})
        clone = self.base / 'clone'
        result = self.restore(raw, clone)
        self.assertEqual(result['status'], 'RESTORED_FENCED')
        with sqlite3.connect(clone / 'sessions/fixture/application.sqlite') as restored:
            self.assertEqual(restored.execute('SELECT * FROM app_occurrences').fetchall(),
                             [('accepted-occurrence', 1700000000000, 3, 1, 'captured result')])
            self.assertEqual(restored.execute('SELECT * FROM fixture_tasks').fetchall(),
                             [('task-1', 'A', 'B', 1700000000000, 24, 'captured', canonical(retained).decode())])
            row = restored.execute('SELECT body,digest FROM preview_context_views WHERE revision=1').fetchone()
            self.assertEqual(json.loads(row[0]), first['items'])
            self.assertEqual(row[1], first['digest'])
            self.assertEqual(restored.execute('SELECT count(*) FROM preview_context_receipts').fetchone()[0], 2)
        fence = json.loads((clone / 'restore-fence.json').read_text())
        self.assertEqual(fence, dict(mode='READ_ONLY_RECONCILIATION', role='omega-agent',
            namespace='omega-ref-backup-fixture', backup_manifest_sha256=digest(canonical(manifest)),
            original_scope=SCOPE, external_effect_authority=False))
        self.assertEqual((clone / 'owner-seal.json').read_bytes(), (root / 'owner-seal.json').read_bytes())

    def test_separate_owner_lifecycle_relations_workspace_roundtrip(self):
        fixtures = (
            # These three-column transport fixtures are not owner schemas.
            # Real schema names now invoke the bounded integrity validator;
            # its refusal of the historical pretend relation schema is valid.
            ('fusion-storage', 'memory/lifecycle.sqlite', 'fixture_lifecycle_events',
             [(1, 'logical-memory', 'introduced'), (2, 'logical-memory', 'withdrawn')]),
            ('fusion-relations', 'preview-facets/preview-relations.sqlite', 'fixture_relation_events',
             [(1, 'relation-1', 'assert'), (2, 'relation-1', 'retract')]),
            ('fusion-execution', 'preview-facets/workspace.sqlite', 'fixture_workspace_effects',
             [(1, 'append-1', 'intent-and-effect-committed')]),
        )
        for role, filename, table, rows in fixtures:
            with self.subTest(role=role):
                root = self.owner(role, role=role)
                db = self.db(root, filename)
                db.execute(f'CREATE TABLE {table}(sequence INTEGER, identity TEXT, state TEXT)')
                with db:
                    db.executemany(f'INSERT INTO {table} VALUES(?,?,?)', rows)
                if role == 'fusion-execution':
                    path = root / 'preview-facets/workspace/result.txt'
                    path.parent.mkdir()
                    path.write_text('Synthetic original\nSynthetic append\n')
                raw = self.export(root, role)
                clone = self.base / (role + '-clone')
                self.restore(raw, clone, role)
                with sqlite3.connect(clone / filename) as restored:
                    self.assertEqual(restored.execute(f'SELECT * FROM {table} ORDER BY sequence').fetchall(), rows)
                if role == 'fusion-execution':
                    self.assertEqual((clone / 'preview-facets/workspace/result.txt').read_bytes(), path.read_bytes())

    def test_metadata_sqlite3_wal_is_checkpointed_and_new_layout_seal_retained(self):
        from fusion.adapters.detta_layout import LAYOUT
        root=self.owner(role='fusion-storage')
        seal=json.loads((root/'owner-seal.json').read_bytes());seal['backend_layout']=LAYOUT
        (root/'owner-seal.json').write_bytes(canonical(seal))
        db=self.db(root,'metadata/chroma.sqlite3');db.execute('CREATE TABLE fixture(value TEXT)')
        with db:db.execute('INSERT INTO fixture VALUES(?)',('synthetic metadata',))
        wal=root/'metadata/chroma.sqlite3-wal';self.assertGreater(wal.stat().st_size,0)
        raw=self.export(root,'fusion-storage');self.assertEqual(wal.stat().st_size,0)
        files=self.unpack(raw);self.assertEqual(json.loads(files['backup-manifest.json'])['seal'],seal)
        clone=self.base/'clone';self.restore(raw,clone,'fusion-storage')
        with sqlite3.connect(clone/'metadata/chroma.sqlite3') as restored:
            self.assertEqual(restored.execute('SELECT value FROM fixture').fetchall(),[('synthetic metadata',)])
        self.denied({'UNSUPPORTED_PROFILE'},backup.synthetic_seal,dict(seal,backend_layout='unknown'),'fusion-storage')
        self.denied({'UNSUPPORTED_PROFILE'},backup.synthetic_seal,dict(seal,role='omega-agent'),'omega-agent')

    def test_preview_scope_requires_exact_composition_and_matching_role(self):
        cases = (
            ('private', 'private-A', COMPOSITION, 'omega-agent', 'UNAUTHORIZED'),
            ('arbitrary', SCOPE, 'arbitrary-synthetic-composition/1', 'omega-agent', 'UNAUTHORIZED'),
            ('old', SCOPE, 'neoclaw-separated-services/1', 'omega-agent', 'UNAUTHORIZED'),
            ('wrong-role', SCOPE, COMPOSITION, 'fusion-storage', 'CONFLICT'),
        )
        for name, scope, composition, role, code in cases:
            with self.subTest(name=name):
                root = self.owner(name, scope=scope, composition=composition)
                self.denied({code}, self.export, root, role)

    def test_busy_wal_checkpoint_refuses_export(self):
        root = self.owner()
        db = self.db(root, 'state.sqlite')
        db.execute('CREATE TABLE pending(value INTEGER)')
        with db:
            db.execute('INSERT INTO pending VALUES(1)')
        reader = sqlite3.connect(root / 'state.sqlite')
        self.addCleanup(reader.close)
        reader.execute('BEGIN')
        self.assertEqual(reader.execute('SELECT value FROM pending').fetchone(), (1,))
        with db:
            db.execute('UPDATE pending SET value=2')
        connect = sqlite3.connect
        def no_wait(*args, **kwargs):
            return connect(*args, **{**kwargs, 'timeout': 0})
        # Keep the actual SQLite busy result; shorten only the test's lock wait.
        with patch.object(backup.sqlite3, 'connect', no_wait):
            self.denied({'NOT_AVAILABLE'}, self.export, root)
        self.assertEqual(reader.execute('SELECT value FROM pending').fetchone(), (1,))
        reader.rollback()
        self.assertEqual(reader.execute('SELECT value FROM pending').fetchone(), (2,))

    def test_process_outputs_and_lock_files_are_excluded(self):
        root = self.owner()
        for name in ('process.json', 'native-exit.json', 'worker.log', 'trace.jsonl', 'anything.lock'):
            (root / name).write_text('fixture transient output')
        names = self.unpack(self.export(root))
        self.assertEqual(set(names), {'backup-manifest.json', 'state/owner-seal.json'})

    def test_credentials_keys_and_authority_never_enter_export(self):
        # Either reject an unsafe owner tree or omit authority: silently
        # archiving it while declaring excluded_authority=True is not accepted.
        candidates = ('secrets/token', 'approval/campaign.json', 'signer.hex',
            'tls.key', 'certificate.pem', 'credentials.json', 'authority.json',
            'policy.json', 'caller-token', 'tls.crt')
        for number, name in enumerate(candidates):
            with self.subTest(name=name):
                root = self.owner('authority-' + str(number))
                path = root / name
                path.parent.mkdir(exist_ok=True)
                path.write_text('synthetic-not-a-real-secret')
                try:
                    files = self.unpack(self.export(root))
                except ContractError as error:
                    self.assertEqual(error.code, 'UNAUTHORIZED')
                else:
                    self.assertNotIn('state/' + name, files)
                    self.assertNotIn(name, json.loads(files['backup-manifest.json'])['files'])

    def test_restore_rejects_wrong_role_protected_namespace_and_nonempty_target(self):
        raw = self.export(self.owner())
        self.denied({'CONFLICT'}, self.restore, raw, self.base / 'wrong-role', 'fusion-storage')
        for name in ('omega-demo', 'omega-ref-omega-demo-clone', 'unrelated'):
            self.denied({'UNAUTHORIZED'}, self.restore, raw, self.base / name, namespace=name)
        target = self.base / 'occupied'
        target.mkdir()
        (target / 'keep.txt').write_text('not replaced')
        self.denied({'CONFLICT'}, self.restore, raw, target)
        self.assertEqual((target / 'keep.txt').read_text(), 'not replaced')

    def test_tampered_payload_rejected_before_fence_or_extraction(self):
        files = self.unpack(self.export(self.owner()))
        files['state/owner-seal.json'] += b' '
        clone = self.base / 'tampered'
        self.denied({'CONFLICT'}, self.restore, self.pack(files), clone)
        self.assertEqual(list(clone.iterdir()), [])

    def test_restore_revalidates_authority_paths_in_self_consistent_archive(self):
        original = self.unpack(self.export(self.owner()))
        for number, name in enumerate(('secrets/token', 'authority.json', 'signer.hex')):
            with self.subTest(name=name):
                files = dict(original)
                manifest = json.loads(files['backup-manifest.json'])
                data = b'synthetic-not-a-real-secret'
                manifest['files'][name] = dict(bytes=len(data), sha256=digest(data))
                files['state/' + name] = data
                files['backup-manifest.json'] = canonical(manifest)
                clone = self.base / ('unsafe-restore-' + str(number))
                self.denied({'UNAUTHORIZED', 'CONFLICT', 'INVALID_ARGUMENT'},
                            self.restore, self.pack(files), clone)
                self.assertFalse((clone / name).exists())

    def test_restore_revalidates_scope_composition_and_role(self):
        original = self.unpack(self.export(self.owner()))
        cases = (
            ('private', {'scope': 'private-A'}),
            ('arbitrary-composition', {'composition': 'arbitrary-synthetic/1'}),
            ('wrong-owner', {'role': 'fusion-storage'}),
        )
        for name, changes in cases:
            with self.subTest(name=name):
                files = dict(original)
                manifest = json.loads(files['backup-manifest.json'])
                manifest['seal'].update(changes)
                data = canonical(manifest['seal'])
                files['state/owner-seal.json'] = data
                manifest['files']['owner-seal.json'] = dict(bytes=len(data), sha256=digest(data))
                files['backup-manifest.json'] = canonical(manifest)
                clone = self.base / ('invalid-seal-' + name)
                self.denied({'UNAUTHORIZED', 'CONFLICT'}, self.restore, self.pack(files), clone)
                self.assertEqual(list(clone.iterdir()), [])

    def test_partial_extraction_is_already_fenced(self):
        raw = self.export(self.owner())
        clone = self.base / 'interrupted'
        original = Path.write_bytes
        def interrupted(path, data):
            if path == clone / 'owner-seal.json':
                self.assertTrue((clone / 'restore-fence.json').exists())
                raise OSError('isolated extraction interruption')
            return original(path, data)
        with patch.object(Path, 'write_bytes', interrupted):
            with self.assertRaisesRegex(OSError, 'isolated extraction interruption'):
                self.restore(raw, clone)
        self.assertFalse(json.loads((clone / 'restore-fence.json').read_text())['external_effect_authority'])
        self.denied({'CONFLICT'}, self.restore, raw, clone)

    def test_restored_preview_effects_are_not_authorized(self):
        for role, path, operation in (
            ('omega-agent', '/preview/session', 'submit'),
            ('fusion-messaging', '/preview/tasks', 'send'),
            ('fusion-execution', '/preview/facets', 'append'),
            ('fusion-storage', '/preview/memory', 'supersede'),
            ('fusion-relations', '/preview/facets', 'assertRelation'),
            ('fusion-model', '/preview/model', 'complete'),
            ('fusion-commitment', '/commitment', 'submit'),
        ):
            with self.subTest(role=role, operation=operation):
                self.denied({'UNAUTHORIZED'}, allowed, role, path, dict(operation=operation))


if __name__ == '__main__':
    unittest.main()
