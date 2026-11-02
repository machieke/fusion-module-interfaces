"""Opt-in native-bridge timing diagnostics with an explicit application fixture.

No Application owner is constructed; no native runtime, provider, model, cluster
or command executes. The real bridge wrapper delegates to a fixture method.
"""
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from integration.neoclaw import loop_bridge as bridge


class BridgeTimingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-timing-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root/'bridge-timing.jsonl'
        self.app = SimpleNamespace(preview_config={'scope': 'synthetic-timing-fixture'},
            config={'workdir': str(self.root), 'preparation_diagnostics': True})
        selected = patch.object(bridge, '_app', self.app)
        selected.start(); self.addCleanup(selected.stop)

    def test_requires_application_preview_and_explicit_diagnostics_opt_in(self):
        for preview, selected in ((None, True), ({}, True), ({'scope': 'synthetic-test'}, False),
                                  ({'scope': 'synthetic-test'}, None)):
            with self.subTest(preview=preview, selected=selected):
                self.app.preview_config = preview
                self.app.config['preparation_diagnostics'] = selected
                bridge._timing('preview_execute', time.monotonic())
                self.assertFalse(self.path.exists())
        with patch.object(bridge, '_app', None):
            bridge._timing('preview_execute', time.monotonic())
        self.assertFalse(self.path.exists())

    def test_real_call_logs_only_bounded_timing_fields_without_arguments_or_result(self):
        argument = ['ARGUMENT_FIXTURE_MARKER', {'private': 'not-loggable'}]
        result = {'response': 'RESULT_FIXTURE_MARKER'}
        self.app.preview_execute = lambda value: result if value == argument else None
        with patch.object(bridge, 'Application', side_effect=AssertionError('No real application allowed')):
            self.assertIs(bridge.call('preview_execute', argument), result)
        raw = self.path.read_text()
        value = json.loads(raw)
        self.assertEqual(set(value), {'method', 'pid', 'finished_ms', 'elapsed_ms', 'code'})
        self.assertEqual(value['method'], 'preview_execute')
        self.assertIsNone(value['code'])
        self.assertGreaterEqual(value['elapsed_ms'], 0)
        self.assertNotIn('ARGUMENT_FIXTURE_MARKER', raw)
        self.assertNotIn('RESULT_FIXTURE_MARKER', raw)
        self.assertNotIn('not-loggable', raw)
        self.assertLess(len(raw.encode()), 512)
        bridge._timing('preview_execute', time.monotonic(), 'UNAUTHORIZED')
        self.assertEqual(json.loads(self.path.read_text().splitlines()[1])['code'], 'UNAUTHORIZED')

    def test_size_threshold_prevents_further_observation_appends(self):
        self.path.write_bytes(b'x'*1048576)
        original = self.path.read_bytes()
        bridge._timing('preview_execute', time.monotonic())
        self.assertEqual(self.path.read_bytes(), original)

    def test_open_failure_does_not_change_successful_application_result(self):
        result = {'response': 'fixture-only'}
        self.app.preview_execute = lambda _: result
        with patch.object(Path, 'open', side_effect=PermissionError('fixture denied diagnostic open')):
            self.assertIs(bridge.call('preview_execute', []), result)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
