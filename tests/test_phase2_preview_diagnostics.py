"""Actual read-only preview counters over explicit fresh SQLite row fixtures.

Rows are schema fixtures, not native workflow evidence. No provider, application,
model or cluster runs. Sensitive markers are generated test strings only.
"""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from fusion.contracts import canonical
from integration.single_node import diagnostics


COMPOSITION = 'omega-single-node-developer-preview/1'
SESSIONS = ('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
            'cccccccc-cccc-4ccc-8ccc-cccccccccccc')
PRIVATE = 'SENSITIVE_SYNTHETIC_CONTENT_FIXTURE'


class PreviewDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-diagnostics-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base/'owner'; self.root.mkdir()
        (self.root/'owner-seal.json').write_bytes(canonical(dict(role='omega-agent',
            composition=COMPOSITION, scope='synthetic-private-scope-marker')))

    def rows(self, path, tables):
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path) as db:
            for table in tables:
                db.execute('CREATE TABLE "'+table+'" (id TEXT, payload TEXT, result TEXT, receipt TEXT, '
                           'done INTEGER, attempts INTEGER, calls INTEGER, failure_code TEXT)')
                db.executemany('INSERT INTO "'+table+'" VALUES(?,?,?,?,?,?,?,?)', [
                    ('private-occurrence-identity', PRIVATE, PRIVATE, PRIVATE, 1, 3, 4, 'UNAUTHORIZED'),
                    ('private-second-identity', PRIVATE, None, None, 0, 1, 2, 'PRIVATE_FAILURE_DETAIL')])

    def assert_private(self, value):
        raw = json.dumps(value)+diagnostics.metrics(value)
        for forbidden in (*SESSIONS, PRIVATE, 'private-occurrence-identity', 'private-second-identity',
                          'PRIVATE_FAILURE_DETAIL', 'synthetic-private-scope-marker'):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(value['live_generation_activity'], 'NOT_INFERRED_FROM_DIAGNOSTICS')

    def test_known_uuid_sessions_are_numeric_labels_with_correct_counts_and_no_mutation(self):
        for session in SESSIONS[:2]:
            self.rows(self.root/'sessions'/session/'caller.sqlite', diagnostics.SESSION_TABLES)
        before = {str(path.relative_to(self.root)): path.read_bytes() for path in self.root.rglob('*') if path.is_file()}
        value = diagnostics.inspect(self.root)
        self.assertEqual(len(value['tables']), 2*len(diagnostics.SESSION_TABLES))
        for number in (1, 2):
            for table in diagnostics.SESSION_TABLES:
                observed = value['tables'][f'session-{number}/caller.sqlite:{table}']
                self.assertEqual(observed['rows'], 2)
                self.assertEqual(observed['done_sum'], 1)
                self.assertEqual(observed['attempts_sum'], 4)
                self.assertEqual(observed['calls_sum'], 6)
                self.assertEqual(observed['result_captured'], 1)
                self.assertEqual(observed['receipt_captured'], 1)
                self.assertEqual(observed['failure_UNAUTHORIZED'], 1)
                self.assertEqual(observed['failure_NOT_AVAILABLE'], 0)
        self.assertEqual({str(path.relative_to(self.root)): path.read_bytes()
                          for path in self.root.rglob('*') if path.is_file()}, before)
        self.assert_private(value)

    def test_preview_owner_files_use_declared_tables_only_and_never_raw_values(self):
        for filename, tables in diagnostics.PREVIEW_FILES.items():
            self.rows(self.root/filename, [*tables, 'unpublished_private_table'])
        value = diagnostics.inspect(self.root)
        expected = {filename+':'+table for filename, tables in diagnostics.PREVIEW_FILES.items() for table in tables}
        self.assertEqual(set(value['tables']), expected)
        self.assertTrue(all(item['rows'] == 2 for item in value['tables'].values()))
        self.assert_private(value)

    def test_excess_sessions_report_capacity_and_only_two_known_directories_are_observed(self):
        for session in SESSIONS:
            self.rows(self.root/'sessions'/session/'caller.sqlite', ['preview_task_outbox'])
        value = diagnostics.inspect(self.root)
        self.assertEqual(value['session_capacity'], 'EXCEEDED')
        self.assertEqual(set(value['tables']), {'session-1/caller.sqlite:preview_task_outbox',
                                               'session-2/caller.sqlite:preview_task_outbox'})
        expected_files = len(diagnostics.FILES)+len(diagnostics.PREVIEW_FILES)+2
        self.assertEqual(value['limits']['max_database_files'], expected_files)
        self.assert_private(value)

    def test_symlink_and_unknown_session_directories_do_not_open_foreign_owner_state(self):
        outside = self.base/'not-this-owner'
        self.rows(outside/'caller.sqlite', ['preview_task_outbox'])
        sessions = self.root/'sessions'; sessions.mkdir()
        (sessions/SESSIONS[0]).symlink_to(outside, target_is_directory=True)
        self.rows(sessions/'not-a-session-uuid'/'caller.sqlite', ['preview_task_outbox'])
        value = diagnostics.inspect(self.root)
        self.assertEqual(value['tables'], {})
        self.assertNotIn('session_capacity', value)
        self.assert_private(value)

    def test_preview_paths_are_not_inferred_for_unchanged_historical_composition(self):
        self.rows(self.root/'sessions'/SESSIONS[0]/'caller.sqlite', ['preview_task_outbox'])
        self.rows(self.root/'session-inbox.sqlite', ['preview_inputs'])
        (self.root/'owner-seal.json').write_bytes(canonical(dict(role='omega-agent',
            composition='neoclaw-separated-services/1', scope='synthetic-private-scope-marker')))
        value = diagnostics.inspect(self.root)
        self.assertEqual(value['tables'], {})
        self.assertEqual(value['limits']['max_database_files'], len(diagnostics.FILES))
        self.assert_private(value)


if __name__ == '__main__':
    unittest.main()
