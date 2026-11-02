"""Real operator backup/restore control flow over explicit kubectl fixtures.

Pod/PVC objects and archive bytes are fixtures. No Kubernetes connection, chain
node, native application, provider, archive extraction or migration is claimed.
Only fresh temporary backup files are written by the actual operator methods.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError, canonical, digest
from integration.single_node import reference_ops as ops


ROLES = ('f1r3node', 'fusion-storage', 'fusion-commitment', 'omega-agent-b',
         'fusion-messaging', 'irc-peer', 'fusion-channel-bridge', 'omega-agent')
EXCLUDED_REASON = 'node-local cryptographic state excluded; no node restore or failover claim'


class KubectlArchiveFixture:
    """Command-boundary fixture with stateful pod deletion and helper mounts."""
    def __init__(self, namespace, *, source=True):
        self.namespace = namespace
        self.uid = 'fixture-namespace-'+namespace
        self.events = []
        self.items = [dict(metadata=dict(name=role, uid='fixture-'+role, annotations={
            'meta.helm.sh/release-name': 'omega', 'meta.helm.sh/release-namespace': namespace}),
            spec=dict(replicas=1, template=dict(metadata=dict(labels={'app.kubernetes.io/instance': 'omega'}),
                spec=dict(containers=[dict(image='fixture.invalid/'+role+'@sha256:'+'a'*64)]))))
            for role in ROLES] if source else []
        self.pvcs = [dict(metadata=dict(name='state-'+role+'-0', uid='original-pvc-'+role),
            spec=dict(accessModes=['ReadWriteOnce'], resources={'requests': {'storage': '1Gi'}},
                      storageClassName='fixture-local-path', volumeMode='Filesystem',
                      volumeName='original-volume-'+role)) for role in ROLES] if source else []
        self.pods = [dict(metadata={'name': role+'-0'}) for role in ROLES] if source else []
        self.helpers = {}
        self.applied = []
        self.retain_writer = False
        self.wait_failure = False
        self.export_failure = None

    @staticmethod
    def archive(role):
        return canonical(dict(boundary='ARCHIVE_BYTES_FIXTURE', role=role,
                              retained_identity='synthetic-occurrence', spent_attempts=2))

    def k(self, *args, **kwargs):
        self.events.append((args, copy.deepcopy(kwargs)))
        if args[:2] == ('get', 'namespace'):
            return json.dumps(dict(metadata=dict(uid=self.uid, labels={ops.LABEL: ops.OWNER})))
        if args[:2] == ('get', 'statefulsets'):
            return json.dumps(dict(items=self.items))
        if args[:2] == ('get', 'pods'):
            return json.dumps(dict(items=self.pods))
        if args[:2] == ('get', 'pvc'):
            return json.dumps(dict(items=self.pvcs))
        if args[:2] == ('scale', 'statefulset'):
            if args[3:] != ('--replicas=0',):
                raise AssertionError('The fixture never authorizes automatic resume')
            next(item for item in self.items if item['metadata']['name'] == args[2])['spec']['replicas'] = 0
            return ''
        if args[:3] == ('wait', '--for=delete', 'pod'):
            if not self.retain_writer:
                self.pods = []
            if self.wait_failure:
                raise RuntimeError('fixture bounded deletion observer failure')
            return ''
        if args == ('apply', '-f', '-'):
            value = json.loads(kwargs['data']); self.applied.append(value)
            if value['kind'] == 'Pod':
                if self.pods or any(item['spec']['replicas'] for item in self.items):
                    raise AssertionError('A helper was admitted before every source writer stopped')
                self.helpers[value['metadata']['name']] = value
            elif value['kind'] == 'PersistentVolumeClaim':
                self.pvcs.append(copy.deepcopy(value))
            else:
                raise AssertionError('Unexpected applied kind '+value['kind'])
            return ''
        if args[:2] == ('wait', '--for=condition=Ready'):
            if args[2].split('/', 1)[1] not in self.helpers:
                raise AssertionError('Waiting on an unadmitted fixture helper')
            return ''
        if args[0] == 'exec':
            restoring = args[1] == '-i'
            helper = args[2] if restoring else args[1]
            if helper not in self.helpers:
                raise AssertionError('Export/import without an admitted helper')
            role = args[args.index('--role')+1]
            if role == 'f1r3node':
                raise AssertionError('Cryptographic node archive must never be requested')
            if restoring:
                if kwargs['data'] != self.archive(role):
                    raise AssertionError('Restore changed fixture archive bytes')
                return canonical(dict(role=role, status='RESTORED_FENCED', boundary='IMPORT_RESULT_FIXTURE'))
            if role == self.export_failure:
                raise RuntimeError('fixture export interruption')
            return self.archive(role)
        if args[:2] == ('delete', 'pod'):
            del self.helpers[args[2]]
            return ''
        raise AssertionError('Unexpected fixture command '+repr(args))

    def operator(self):
        operator = ops.Operator('/fixture/not-read', 'fixture-context', self.namespace)
        operator.k = self.k
        return operator


class OperatorBackupBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-backup-boundary-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = KubectlArchiveFixture('omega-ref-source-fixture')
        self.operator = self.source.operator()
        self.destination = self.root/'backup'

    def backup(self):
        return self.operator.backup(self.destination)

    def assert_no_node_mount_or_export(self, fixture):
        for value in fixture.applied:
            self.assertNotEqual(value['metadata']['name'], 'state-f1r3node-0')
            if value['kind'] == 'Pod':
                volumes = value['spec']['volumes']
                self.assertEqual(len(volumes), 1)
                self.assertNotEqual(volumes[0]['persistentVolumeClaim']['claimName'], 'state-f1r3node-0')
                self.assertNotIn('hostPath', volumes[0])
        for args, _ in fixture.events:
            if args[0] == 'exec':
                self.assertNotIn('f1r3node', args)
            self.assertFalse(args[:2] == ('delete', 'pvc'))
        self.assertNotIn('reference-copy-f1r3node', fixture.helpers)

    def test_all_workloads_quiesce_before_export_and_node_pvc_is_never_mounted(self):
        original_pvcs = copy.deepcopy(self.source.pvcs)
        manifest = self.backup()
        self.assertEqual(set(manifest['before']['workloads']), set(ROLES))
        scales = [(index, args[2]) for index, (args, _) in enumerate(self.source.events)
                  if args[:2] == ('scale', 'statefulset')]
        self.assertEqual(len(scales), len(ROLES))
        self.assertEqual({role for _, role in scales}, set(ROLES))
        self.assertEqual([role for _, role in scales[:4]],
                         ['omega-agent', 'omega-agent-b', 'fusion-channel-bridge', 'irc-peer'])
        first_mount = next(index for index, (args, _) in enumerate(self.source.events)
                           if args == ('apply', '-f', '-'))
        self.assertTrue(all(index < first_mount for index, _ in scales))
        self.assertTrue(any(index < first_mount and args[:3] == ('wait', '--for=delete', 'pod')
                            for index, (args, _) in enumerate(self.source.events)))
        self.assertEqual(self.source.pods, [])
        self.assertTrue(all(item['spec']['replicas'] == 0 for item in self.source.items))
        self.assertEqual(self.source.pvcs, original_pvcs)
        self.assertEqual(self.source.helpers, {})
        self.assert_no_node_mount_or_export(self.source)

    def test_manifest_precisely_excludes_node_and_archives_ordinary_owners(self):
        manifest = self.backup()
        expected_image = manifest['before']['workloads']['f1r3node']['image']
        self.assertEqual(manifest['excluded_owners'], {'f1r3node': dict(image=expected_image,
            pvc='state-f1r3node-0', reason=EXCLUDED_REASON, original_retained=True, original_quiesced=True)})
        self.assertEqual(set(manifest['owners']), set(ROLES)-{'f1r3node'})
        self.assertTrue(manifest['authority_excluded'])
        self.assertTrue(manifest['original_remains_quiesced'])
        self.assertIn('not a distributed transaction', manifest['consistency'])
        self.assertFalse((self.destination/'f1r3node.tar.gz').exists())
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o700)
        for role, entry in manifest['owners'].items():
            path = self.destination/entry['file']
            self.assertEqual(path.read_bytes(), self.source.archive(role))
            self.assertEqual(entry['sha256'], digest(path.read_bytes()))
            self.assertEqual(entry['bytes'], len(path.read_bytes()))
            self.assertEqual(entry['image'], manifest['before']['workloads'][role]['image'])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        caller_image = manifest['before']['workloads']['omega-agent']['image']
        self.assertEqual(manifest['maintenance_image'], caller_image)
        for pod in self.source.applied:
            self.assertEqual(pod['spec']['containers'][0]['image'], caller_image)
        raw = (self.destination/'manifest.json').read_bytes()
        self.assertEqual(raw, canonical(manifest))
        self.assertEqual((self.destination/'manifest.sha256').read_text(), digest(raw)+'\n')

    def test_remaining_writer_or_failed_stop_prevents_every_mount_and_export(self):
        for failed_wait in (False, True):
            with self.subTest(failed_wait=failed_wait):
                fixture = KubectlArchiveFixture('omega-ref-stop-fixture')
                fixture.retain_writer = True; fixture.wait_failure = failed_wait
                destination = self.root/('failed-'+str(failed_wait))
                error = RuntimeError if failed_wait else ContractError
                with self.assertRaises(error): fixture.operator().backup(destination)
                self.assertEqual(fixture.applied, [])
                self.assertFalse(any(args[0] == 'exec' for args, _ in fixture.events))
                self.assertFalse((destination/'manifest.json').exists())

    def test_export_interruption_cleans_helper_and_preserves_stopped_originals(self):
        self.source.export_failure = 'fusion-commitment'
        with self.assertRaisesRegex(RuntimeError, 'fixture export interruption'):
            self.backup()
        self.assertEqual(self.source.helpers, {})
        self.assertTrue(all(item['spec']['replicas'] == 0 for item in self.source.items))
        self.assertFalse((self.destination/'manifest.json').exists())
        self.assert_no_node_mount_or_export(self.source)

    def test_restore_creates_only_included_owner_pvcs_and_stays_fenced(self):
        manifest = self.backup()
        clone = KubectlArchiveFixture('omega-ref-clone-fixture', source=False)
        target = clone.operator()
        with patch.object(ops, 'Operator', return_value=self.operator) as original:
            result = target.restore(self.destination)
        original.assert_called_once_with(target.kubeconfig, target.context,
                                         self.source.namespace, target.release)
        self.assertEqual(result['status'], 'RESTORED_FENCED')
        self.assertFalse(result['automatic_resume'])
        self.assertEqual({item['role'] for item in result['roles']}, set(manifest['owners']))
        self.assertEqual(result['backup_sha256'], digest(canonical(manifest)))
        self.assertEqual({item['metadata']['name'] for item in clone.pvcs},
                         {'state-'+role+'-0' for role in manifest['owners']})
        for pvc in clone.pvcs:
            self.assertNotIn('volumeName', pvc['spec'])
            self.assertEqual(pvc['metadata']['namespace'], clone.namespace)
        self.assertEqual(clone.helpers, {})
        self.assertFalse(any(args[0] == 'scale' for args, _ in clone.events))
        self.assert_no_node_mount_or_export(clone)

    def test_excluded_node_is_still_part_of_original_writer_fencing(self):
        self.backup()
        node = next(item for item in self.source.items if item['metadata']['name'] == 'f1r3node')
        node['spec']['replicas'] = 1
        clone = KubectlArchiveFixture('omega-ref-refused-clone', source=False)
        target = clone.operator()
        with patch.object(ops, 'Operator', return_value=self.operator):
            with self.assertRaises(ContractError) as error: target.restore(self.destination)
        self.assertEqual(error.exception.code, 'UNAUTHORIZED')
        self.assertEqual(clone.applied, [])

    def test_first_archive_tampering_prevents_restore_mounts(self):
        manifest = self.backup()
        first_role = sorted(manifest['owners'])[0]
        first_archive = self.destination/manifest['owners'][first_role]['file']
        first_archive.write_bytes(b'tampered archive fixture')
        clone = KubectlArchiveFixture('omega-ref-tampered-clone', source=False)
        target = clone.operator()
        with patch.object(ops, 'Operator', return_value=self.operator):
            with self.assertRaises(ContractError) as error: target.restore(self.destination)
        self.assertEqual(error.exception.code, 'CONFLICT')
        self.assertEqual(clone.applied, [])

    def test_manifest_digest_tampering_prevents_restore_operator_activity(self):
        self.backup()
        path = self.destination/'manifest.json'
        path.write_bytes(path.read_bytes()+b' ')
        clone = KubectlArchiveFixture('omega-ref-tampered-manifest', source=False)
        target = clone.operator()
        with patch.object(ops, 'Operator') as original:
            with self.assertRaises(ContractError) as error: target.restore(self.destination)
        self.assertEqual(error.exception.code, 'CONFLICT')
        self.assertEqual(clone.events, [])
        original.assert_not_called()


if __name__ == '__main__':
    unittest.main()
