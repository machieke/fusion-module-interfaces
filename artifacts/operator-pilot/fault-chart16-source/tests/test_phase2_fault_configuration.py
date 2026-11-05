"""One-shot preview fault wiring over real configuration, fixture TLS bytes.

Reuses only the synthetic setup from cognitive wiring tests. No owner journal,
native process, model, TLS connection or Kubernetes workload is started.
"""
import copy
import json
from pathlib import Path
import unittest
import subprocess
import tempfile

from fusion.contracts import ContractError, canonical
from integration.single_node.preview_configure import COMPOSITION, configure
from tests import test_phase2_cognitive_wiring as fixture_setup


class PreviewFaultConfigurationTests(unittest.TestCase):
    setUp = fixture_setup.CognitiveWiringTests.setUp

    def settings(self, role, test=None, *, enabled=True):
        return dict(role=role, service_composition=COMPOSITION, state=str(self.root/role/'state'),
            run=str(self.root/role/'run'), secret_directory=str(self.root/role/'secrets'),
            https_port=8443, capacity=8, revision='fault-wiring-test', native_enabled=True,
            worker_enabled=False, enable_test_faults=enabled, test=test or {},
            preview=copy.deepcopy(self.preview),
            peers={name: name+'.synthetic-preview.svc.cluster.local' for name in self.roles})

    def test_new_facet_cognitive_and_model_owners_receive_the_common_pause_binding(self):
        stages = {'fusion-episodes': 'after_episode_commit', 'fusion-relations': 'after_relation_commit',
                  'fusion-beliefs': 'after_evidence_decision_commit',
                  'fusion-attention': 'after_priority_commit', 'fusion-model': 'after_model_provider_capture'}
        for role, stage in stages.items():
            with self.subTest(role=role):
                _, cfg, state, run = configure(self.settings(role, {'pause_at': stage}))
                self.assertIs(cfg['test_failpoints'], True)
                self.assertEqual(cfg['pause_at'], stage)
                self.assertEqual(cfg['failpoint_marker'], str(state/'pause.json'))
                self.assertEqual(json.loads((run/'owner.json').read_text()), json.loads(canonical(cfg)))
                self.assertEqual(list(state.iterdir()), [])

    def test_new_owner_faults_refuse_when_opt_in_is_disabled(self):
        for role in ('fusion-episodes', 'fusion-relations', 'fusion-attention', 'fusion-beliefs', 'fusion-model'):
            for fault in ({'pause_at': 'after_committed_fixture_stage'}, {'drop_response_operation': 'complete'}):
                with self.subTest(role=role, fault=list(fault)):
                    with self.assertRaises(ContractError) as caught:
                        configure(self.settings(role, fault, enabled=False))
                    self.assertEqual(caught.exception.code, 'UNAUTHORIZED')
                    self.assertFalse((self.root/role/'run'/'owner.json').exists())
                    self.assertEqual(list((self.root/role/'state').iterdir()), [])

    def test_replacement_retains_durable_marker_and_suppresses_pause_without_changing_limits(self):
        for role in ('fusion-episodes', 'fusion-relations', 'fusion-model', 'fusion-attention', 'omega-agent'):
            with self.subTest(role=role):
                settings = self.settings(role, {'pause_at': 'after_occurrence_bind'})
                _, first, state, _ = configure(settings)
                marker = canonical(dict(stage='after_occurrence_bind', pid=12345))
                (state/'pause.json').write_bytes(marker)
                _, recovered, recovered_state, run = configure(copy.deepcopy(settings))
                self.assertEqual(recovered_state, state)
                self.assertTrue(recovered['test_failpoints'])
                self.assertNotIn('pause_at', recovered)
                self.assertEqual((state/'pause.json').read_bytes(), marker)
                self.assertEqual({k: v for k, v in first.items() if k != 'pause_at'}, recovered)
                if role == 'omega-agent':
                    sid = self.agents[role]['sessions'][0]
                    app = json.loads((run/'sessions'/sid/'application.json').read_text())
                    self.assertNotIn('pause_at', app)
                    self.assertEqual(app['failpoint_marker'], str(state/'pause.json'))
                    self.assertEqual(recovered['native_sessions']['session_templates'][sid]['limits'],
                                     self.preview['limits'])

    def test_empty_fault_selection_does_not_arm_a_barrier(self):
        for role in ('fusion-model', 'fusion-relations'):
            _, cfg, state, _ = configure(self.settings(role, enabled=False))
            self.assertFalse(cfg['test_failpoints'])
            self.assertNotIn('pause_at', cfg)
            self.assertFalse((state/'pause.json').exists())


class PreviewFaultChartTests(unittest.TestCase):
    """Actual offline Helm validation, with no cluster or owner execution."""
    def render(self, test):
        chart = Path(__file__).resolve().parents[1]/'deploy/helm/omega-fusion'
        with tempfile.TemporaryDirectory() as directory:
            values = Path(directory)/'values.json'
            values.write_bytes(canonical(dict(testFaultsEnabled=True,
                components={'omega-agent': {'config': {'test': test}}})))
            return subprocess.run(['helm', 'template', 'omega', str(chart),
                '--namespace', 'omega-ref-preview-fault-schema', '-f', str(values)],
                capture_output=True, text=True, timeout=30)

    def test_exact_deployed_recovery_hooks_render_without_broadening_unknown_operations(self):
        for stage in ('after_session_input_capture', 'after_workspace_effect',
                      'after_lifecycle_commit', 'after_task_payload_capture',
                      'after_application_projection', 'after_feed_backend_acceptance',
                      'after_model_provider_capture'):
            with self.subTest(stage=stage):
                result = self.render({'pause_at': stage})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(stage, result.stdout)
        result = self.render({'drop_response_operation': 'assertRelation'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('assertRelation', result.stdout)

    def test_unknown_fault_stages_and_operations_remain_closed(self):
        for fault in ({'pause_at': 'arbitrary-stage'},
                      {'drop_response_operation': 'arbitrary-execution'}):
            result = self.render(fault)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('value must be one of', result.stderr)


if __name__ == '__main__':
    unittest.main()
