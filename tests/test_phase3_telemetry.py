"""Bounded diagnostic spans, with a deterministic clock/payload test boundary."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion import native_telemetry as t
from fusion.contracts import ContractError

class NativeTelemetry(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        prior=t._sink;self.addCleanup(setattr,t,'_sink',prior)
        t._sink=None
    def configure(self):t.configure(dict(workdir=str(self.root),native_telemetry=dict(profile=t.PROFILE,max_bytes=4194304)))
    def test_nested_monotonic_spans_count_bytes_without_text(self):
        self.configure()
        @t.traced('test.child',request=0)
        def inner(text):return text.upper()
        with t.span('test.parent'):self.assertEqual(inner('synthetic-canary-text'),'SYNTHETIC-CANARY-TEXT')
        raw=(self.root/'native-stages.jsonl').read_text();rows=[json.loads(x) for x in raw.splitlines()]
        self.assertNotIn('canary',raw);self.assertEqual(len(rows),2)
        child,parent=rows;self.assertEqual(child['parent'],parent['span'])
        self.assertLessEqual(parent['start_ns'],child['start_ns']);self.assertGreaterEqual(parent['duration_ns'],child['duration_ns'])
        self.assertEqual(child['request_bytes'],len('synthetic-canary-text'))
        self.assertEqual(child['response_bytes'],len('SYNTHETIC-CANARY-TEXT'))
    def test_disabled_sink_does_not_serialize_or_observe_arguments(self):
        class Private:
            def __repr__(self):raise AssertionError('must not inspect')
        @t.traced('test.disabled',request=0)
        def operation(value):return value
        selected=Private();self.assertIs(operation(selected),selected);self.assertFalse(list(self.root.iterdir()))
    def test_errors_cannot_become_success_and_labels_do_not_leak_detail(self):
        self.configure()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
            with t.span('test.error'):raise ContractError('UNAUTHORIZED')
        row=json.loads((self.root/'native-stages.jsonl').read_text());self.assertEqual(row['code'],'UNAUTHORIZED')
    def test_full_file_is_explicitly_truncated_and_does_not_change_work(self):
        self.configure();path=self.root/'native-stages.jsonl';path.write_bytes(b'x'*4194304)
        with t.span('test.full'):result=42
        self.assertEqual(result,42);self.assertEqual(path.stat().st_size,4194304);self.assertTrue(path.with_suffix('.truncated').exists())

if __name__=='__main__':unittest.main()
