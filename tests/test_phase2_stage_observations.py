"""Stage diagnostics fixtures: local files and authored operator responses only.

No cluster, container, native runtime, provider or generative call is exercised.
"""
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from examples import preview_stage_observations as q
from fusion.contracts import ContractError, canonical, digest


def entry(**updates):
    return dict(dict(method='model_complete', pid=32, finished_ms=1793650000000, elapsed_ms=4.0, code=None), **updates)


def lines(*records):
    return b''.join(json.dumps(record, separators=(',', ':')).encode()+b'\n' for record in records)


class StageObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def owner(self, role='omega-agent', samples=None):
        path = self.root/role; path.mkdir()
        (path/'owner-seal.json').write_bytes(canonical(dict(role=role, scope='synthetic-stage-fixture',
            composition='omega-single-node-developer-preview/1')))
        for raw in samples or [lines(entry(elapsed_ms=2), entry(elapsed_ms=6))]:
            native = path/'sessions'/str(uuid.uuid4())/'native'; native.mkdir(parents=True)
            (native/'bridge-timing.jsonl').write_bytes(raw)
        return path

    def test_closed_timings_group_success_and_error_separately(self):
        raw = lines(entry(elapsed_ms=1), entry(elapsed_ms=7), entry(elapsed_ms=12, code='UNAUTHORIZED'),
                    entry(method='restore', elapsed_ms=0))
        observed = q.parse_timings(raw)
        self.assertEqual((observed['sha256'], observed['bytes'], observed['records']), (digest(raw), len(raw), 4))
        self.assertEqual(observed['by_method_code'], [
            dict(method='model_complete', code=None, count=2, min_ms=1, max_ms=7, mean_ms=4.0),
            dict(method='model_complete', code='UNAUTHORIZED', count=1, min_ms=12, max_ms=12, mean_ms=12.0),
            dict(method='restore', code=None, count=1, min_ms=0, max_ms=0, mean_ms=0.0)])
        self.assertNotIn('pid', json.dumps(observed)); self.assertNotIn('finished_ms', json.dumps(observed))

    def test_extra_missing_duplicate_and_nonobject_fields_are_refused(self):
        missing = entry(); missing.pop('code')
        duplicate = lines(entry()).replace(b'"pid":32', b'"pid":32,"pid":33')
        for raw in (lines(entry(arguments='private input must never publish')), lines(missing), duplicate, b'[]\n'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                q.parse_timings(raw)

    def test_invalid_types_names_and_nonfinite_or_negative_elapsed_are_refused(self):
        updates = [('method', 'tool with payload'), ('method', 'a'*65), ('method', None), ('code', 'secret-data'),
            ('code', False), ('pid', True), ('pid', 0), ('finished_ms', -1), ('finished_ms', 1.5),
            ('elapsed_ms', True), ('elapsed_ms', -0.1), ('elapsed_ms', float('nan')),
            ('elapsed_ms', float('inf')), ('elapsed_ms', '-5')]
        for field, value in updates:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                q.parse_timings(lines(entry(**{field: value})))

    def test_byte_line_and_malformed_json_bounds(self):
        for raw in (b' '*1048577, b' '*2049+b'\n', b'\n', b'{"method":', b'\xff'):
            with self.subTest(size=len(raw)), self.assertRaises((ValueError, UnicodeDecodeError)):
                q.parse_timings(raw)
        self.assertEqual(q.parse_timings(b'')['records'], 0)

    def test_finite_large_durations_do_not_overflow_the_mean(self):
        result = q.parse_timings(lines(entry(elapsed_ms=1e308), entry(elapsed_ms=1e308)))
        self.assertEqual(result['by_method_code'][0]['mean_ms'], 1e308)

    def test_owner_two_files_aggregate_without_rewriting_or_raw_log_output(self):
        path = self.owner(samples=[lines(entry(elapsed_ms=1)), lines(entry(elapsed_ms=5), entry(elapsed_ms=9))])
        before = {str(p): digest(p.read_bytes()) for p in path.rglob('*') if p.is_file()}
        result = q.owned_timings(path, 'omega-agent')
        self.assertEqual(len(result['files']), 2); self.assertEqual(result['total_records'], 3)
        self.assertEqual(result['by_method_code'][0]['mean_ms'], 5)
        self.assertTrue(result['observed_files_unchanged'])
        self.assertEqual(before, {str(p): digest(p.read_bytes()) for p in path.rglob('*') if p.is_file()})
        self.assertNotIn('finished_ms', json.dumps(result)); self.assertNotIn('pid', json.dumps(result))

    def test_embedded_helper_is_standalone_and_binds_writer_source_hash(self):
        path = self.owner()
        source = self.root/'source'/'integration'/'neoclaw'/'loop_bridge.py'
        source.parent.mkdir(parents=True); source.write_text('# Explicit diagnostic source fixture\n')
        namespace = {}
        exec(inspect.getsource(q.parse_timings)+'\n'+inspect.getsource(q.owned_timings), namespace)
        observed = namespace['owned_timings'](path, 'omega-agent', self.root/'source')
        self.assertEqual(observed['diagnostic_writer_source_sha256'], digest(source.read_bytes()))
        self.assertEqual(observed['total_records'], 2)

    def test_third_file_and_oversized_file_refused(self):
        path = self.owner(samples=[lines(entry())]*3)
        with self.assertRaises(AssertionError): q.owned_timings(path, 'omega-agent')
        first, *rest = list(path.glob('sessions/*/native/bridge-timing.jsonl'))
        for item in rest: item.unlink()
        first.write_bytes(b' '*1048577)
        with self.assertRaises(AssertionError): q.owned_timings(path, 'omega-agent')

    def test_absent_or_empty_diagnostic_is_not_observed_not_an_invented_timing(self):
        path = self.owner()
        log = next(path.glob('sessions/*/native/bridge-timing.jsonl'))
        log.unlink()
        absent = q.owned_timings(path, 'omega-agent')
        self.assertEqual(absent['timing_status'], 'NOT_OBSERVED')
        self.assertEqual(absent['files'], []); self.assertEqual(absent['by_method_code'], [])
        self.assertEqual(absent['total_records'], 0)
        self.assertTrue(absent['checked_paths'][0]['native_directory_present'])
        self.assertFalse(absent['checked_paths'][0]['diagnostic_file_present'])
        self.assertIn('historical cause unknown', absent['absence_reason'])
        log.write_bytes(b'')
        empty = q.owned_timings(path, 'omega-agent')
        self.assertEqual(empty['timing_status'], 'NOT_OBSERVED')
        self.assertEqual(empty['files'][0]['bytes'], 0)

    def test_actual_best_effort_writer_can_omit_diagnostics_without_native_activity(self):
        # Source behavior only: a lightweight stand-in application, no launcher,
        # application constructor, journal, provider, or native runtime call.
        from integration.neoclaw import loop_bridge
        absent_parent = self.root/'never-created'
        app = SimpleNamespace(preview_config={'fixture': True},
            config={'workdir': str(absent_parent), 'preparation_diagnostics': False})
        with patch.object(loop_bridge, '_app', app):
            loop_bridge._timing('restore', 0)
            self.assertFalse(absent_parent.exists())
            app.config['preparation_diagnostics'] = True
            loop_bridge._timing('restore', 0)  # open raises OSError, deliberately ignored.
            self.assertFalse(absent_parent.exists())

    def test_symlink_log_foreign_role_and_private_seal_refused(self):
        path = self.owner()
        log = next(path.glob('sessions/*/native/bridge-timing.jsonl'))
        external = self.root/'private.jsonl'; external.write_bytes(lines(entry()))
        original = log.read_bytes(); log.unlink(); log.symlink_to(external)
        with self.assertRaises(AssertionError): q.owned_timings(path, 'omega-agent')
        log.unlink(); log.write_bytes(original)
        with self.assertRaises(AssertionError): q.owned_timings(path, 'fusion-storage')
        with self.assertRaises(AssertionError): q.owned_timings(path, 'omega-agent-b')
        seal = json.loads((path/'owner-seal.json').read_text()); seal['scope'] = 'private-memory'
        (path/'owner-seal.json').write_bytes(canonical(seal))
        with self.assertRaises(AssertionError): q.owned_timings(path, 'omega-agent')

    def operator(self):
        owner = self
        image = 'fixture/caller@sha256:'+'a'*64
        roots = {role: self.owner(role) for role in q.ROLES}

        class FixtureOperator:
            namespace, release = 'omega-ref-stages-fixture', 'omega'
            def __init__(self):
                self.active = None; self.deleted = []; self.created = []; self.writer = False
                self.replica = 0; self.fail_read = False; self.fail_helper = False; self.change_pvc = False
                self.version = 1
            def owned(self): return {'metadata': {'uid': 'fixture-namespace'}}
            def workloads(self):
                return [dict(metadata=dict(name=role, uid='fixture-'+role), spec=dict(replicas=self.replica,
                    template={'spec': {'containers': [dict(image=image, volumeMounts=[dict(name='state', mountPath='/state')])]}},
                    volumeClaimTemplates=[{'metadata': {'name': 'state'}}])) for role in q.ROLES]
            def helper(self, role, selected_image, pvc, readonly=False):
                owner.assertIsNone(self.active); owner.assertTrue(readonly)
                owner.assertEqual(selected_image, image); owner.assertEqual(pvc, 'state-'+role+'-0')
                self.created.append(role); self.active = 'reference-copy-'+role
                if self.fail_helper: raise RuntimeError('explicit helper-readiness fixture failure')
                return self.active
            def k(self, *args, **kwargs):
                if args[:2] == ('get', 'pods'):
                    return json.dumps({'items': [{'metadata': {'name': 'fixture-existing'}}] if self.active or self.writer else []})
                if args[:2] == ('get', 'pvc'):
                    role = args[2][len('state-'):-2]
                    return json.dumps(dict(metadata=dict(name=args[2], namespace=self.namespace, uid='pvc-'+role,
                        labels={'app.kubernetes.io/instance': self.release, 'app.kubernetes.io/name': role}),
                        spec=dict(accessModes=['ReadWriteOnce'], fixture_version=self.version)))
                if args[:2] == ('get', 'pod'):
                    role = self.active[len('reference-copy-'):]
                    return json.dumps(dict(spec=dict(automountServiceAccountToken=False,
                        containers=[dict(image=image, volumeMounts=[dict(name='state', mountPath='/state', readOnly=True)])],
                        volumes=[dict(name='state', persistentVolumeClaim=dict(claimName='state-'+role+'-0', readOnly=True))]),
                        status={'containerStatuses': [{'imageID': image}]}))
                if args[0] == 'exec':
                    owner.assertEqual(args[3:], ('--', q.PYTHON, '-'))
                    owner.assertIn('print(json.dumps(owned_timings(', kwargs['data'])
                    if self.fail_read: raise RuntimeError('synthetic diagnostic read fixture failure')
                    role = self.active[len('reference-copy-'):]
                    if self.change_pvc: self.version += 1
                    return json.dumps(q.owned_timings(roots[role], role))
                if args[:2] == ('delete', 'pod'):
                    owner.assertEqual(args[2], self.active); self.deleted.append(self.active); self.active = None
                    return ''
                raise AssertionError(args)
        return FixtureOperator()

    def test_helpers_serial_readonly_deleted_and_fresh_report_has_only_summaries(self):
        op = self.operator(); output = self.root/'report.json'
        report = q.run(op, output)
        self.assertEqual(report['status'], 'PASS'); self.assertEqual(op.created, list(q.ROLES))
        self.assertEqual(op.deleted, ['reference-copy-'+role for role in q.ROLES])
        self.assertTrue(report['pvc_identity_and_spec_unchanged']); self.assertIsNone(op.active)
        self.assertEqual(json.loads(output.read_bytes()), report)
        self.assertIn('nonadditive', report['interpretation'])
        self.assertEqual(report['additional_live_generations'], 0)
        with self.assertRaises(FileExistsError): q.run(op, output)
        self.assertEqual(op.created, list(q.ROLES))

    def test_running_workload_or_remaining_pod_refused_before_helper_creation(self):
        op = self.operator(); op.replica = 1
        with self.assertRaises(ContractError): q.run(op, self.root/'replicas.json')
        op.replica = 0; op.writer = True
        with self.assertRaises(ContractError): q.run(op, self.root/'pod.json')
        self.assertEqual(op.created, [])

    def test_absent_diagnostics_keep_readonly_gate_separate_from_timing_gate(self):
        op = self.operator()
        for role in q.ROLES:
            next((self.root/role).glob('sessions/*/native/bridge-timing.jsonl')).unlink()
        report = q.run(op, self.root/'not-observed.json')
        self.assertEqual(report['status'], 'NOT_OBSERVED')
        self.assertEqual(report['timing_gate'], 'NOT_OBSERVED')
        self.assertEqual(report['read_only_ownership_gate'], 'PASS')
        self.assertTrue(report['helpers_deleted']); self.assertIsNone(op.active)
        self.assertTrue(all(value['by_method_code'] == [] for value in report['owners'].values()))

    def test_one_owner_without_timings_is_partial_and_never_whole_gate_pass(self):
        op = self.operator()
        next((self.root/'omega-agent-b').glob('sessions/*/native/bridge-timing.jsonl')).unlink()
        report = q.run(op, self.root/'partial.json')
        self.assertEqual(report['status'], 'PARTIAL')
        self.assertEqual(report['timing_gate'], 'PARTIAL')
        self.assertEqual(report['owners']['omega-agent-b']['timing_status'], 'NOT_OBSERVED')
        self.assertEqual(report['read_only_ownership_gate'], 'PASS')

    def test_helper_is_deleted_after_observation_or_readiness_failure(self):
        op = self.operator(); op.fail_read = True
        with self.assertRaises(RuntimeError): q.run(op, self.root/'read-failure.json')
        self.assertIsNone(op.active); self.assertEqual(len(op.deleted), 1)
        op.fail_read = False; op.fail_helper = True
        with self.assertRaises(RuntimeError): q.run(op, self.root/'helper-failure.json')
        self.assertIsNone(op.active); self.assertEqual(len(op.deleted), 2)
        report = json.loads((self.root/'read-failure.json').read_bytes())
        self.assertNotIn('fixture failure', json.dumps(report)); self.assertEqual(report['status'], 'FAILED')

    def test_pvc_identity_or_spec_change_is_refused_after_cleanup(self):
        op = self.operator(); op.change_pvc = True
        with self.assertRaises(ContractError): q.run(op, self.root/'changed-pvc.json')
        self.assertIsNone(op.active); self.assertEqual(len(op.deleted), 1)


if __name__ == '__main__':
    unittest.main()
