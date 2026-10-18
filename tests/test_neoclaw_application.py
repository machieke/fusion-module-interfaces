"""Fixture storage/kernel unit gates for application identity; not native evidence."""
import json
import sqlite3
import unittest
from pathlib import Path

from fusion.contracts import ContractError, canonical
from fusion import neoclaw_contracts as c
from fusion.neoclaw_application import Application
from fusion.neoclaw_client import Caller
from integration.neoclaw.startup_overlay import adapted_loop, adapted_skill
from tests.neoclaw_support import Harness, COMMAND, PREMISES, GOLDEN

CMD = ['metta', COMMAND[6:]]


class ApplicationContracts(unittest.TestCase):
    def setUp(self):
        self.h = Harness(); self.addCleanup(self.h.close)
        self.path = self.h.caller_root/'app.json'
        self.config = dict(composition='controlled-native-loop/1', caller_config=str(self.h.client_path),
                           turn_limit=128, invocation_timeout_ms=30000)
        self.path.write_bytes(canonical(self.config))
        self.app = Application(self.path)
        self.addCleanup(lambda: self.app.close() if self.app else None)

    def restart(self):
        self.app.close();self.app=None
        self.app=Application(self.path)

    def test_ordered_identity_and_exact_pending_replay_conflict(self):
        indexed=self.app.accept('twice', [CMD,CMD]); self.assertEqual([x[0] for x in indexed], [0,1])
        old=[dict(x) for x in self.app.db.execute('SELECT * FROM app_occurrences ORDER BY position')]
        self.assertNotEqual(old[0]['id'],old[1]['id'])
        self.restart();self.assertEqual(self.app.accept('twice',[CMD,CMD]),indexed)
        self.assertEqual([dict(x) for x in self.app.db.execute('SELECT * FROM app_occurrences ORDER BY position')],old)
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.app.accept('changed',[CMD])
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.app.begin(1,CMD)
        self.app.begin(0,CMD)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            self.app.invoke('(Truth_Deduction (stv 0.1 0.9) (stv 0.7 0.8))')
        self.assertEqual(self.h.counts().get('jobs',0),0)

    def complete_fixture(self):
        self.app.accept(COMMAND,[CMD]);self.app.begin(0,CMD)
        row=self.app.db.execute('SELECT * FROM app_occurrences').fetchone()
        caller=Caller(self.h.client_path, invocation=dict(request_id=row['id'],deadline_ms=row['deadline']))
        try: caller._call(caller.prepare(PREMISES))
        finally: caller.close()
        self.h.drive()  # Explicit FixtureKernel; no numerical claim.
        self.assertEqual(self.app.invoke(COMMAND[6:]),GOLDEN)
        self.app.end(0);self.app.finish('native projection fixture '+GOLDEN)

    def test_new_identical_turn_is_not_replay_and_no_config_rewrite(self):
        before=self.h.client_path.read_bytes();self.complete_fixture()
        old=self.app.db.execute('SELECT id FROM app_occurrences').fetchone()[0]
        self.app.accept(COMMAND,[CMD])
        ids=[x[0] for x in self.app.db.execute('SELECT id FROM app_occurrences')]
        self.assertEqual(len(set(ids)),2);self.assertIn(old,ids)
        self.assertEqual(self.h.client_path.read_bytes(),before)

    def test_restore_requires_current_authority_and_preserves_projection(self):
        self.complete_fixture();self.restart()
        expected='native projection fixture '+GOLDEN
        self.assertEqual(self.app.restore(),expected)
        methods=self.h.config['principals']['A']['scopes'][c.SCOPE]
        methods.remove('atom.storage.get');self.h.save()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'): self.app.restore()
        methods.append('atom.storage.get');self.h.save()
        self.assertEqual(self.app.restore(),expected)
        self.assertEqual(self.h.counts().get('jobs',0),1)

    def test_binding_and_limits_cannot_be_changed_on_restart_or_mid_turn(self):
        self.app.accept(COMMAND,[CMD]);self.app.begin(0,CMD)
        self.h.client['max_calls']=63;self.h.save_client()
        with self.assertRaisesRegex(ContractError,'CONFLICT'): self.app.invoke(COMMAND[6:])
        self.app.close();self.app=None
        with self.assertRaisesRegex(ContractError,'CONFLICT'): Application(self.path)
        self.assertEqual(self.h.counts().get('jobs',0),0)

    def test_invalid_selected_batch_is_rejected_before_any_execution(self):
        for expression in ('(Truth_Deduction (stv 2 1) (stv 1 1))',
                           '(Truth_Deduction (stv $f 1) (stv 1 1))',
                           '(Truth_Deduction (stv 1 1) (stv 1 1) extra)'):
            with self.assertRaises(ContractError): self.app.accept('bad',[CMD,['metta',expression]])
        self.assertIsNone(self.app.pending())
        self.assertEqual(self.h.counts().get('jobs',0),0)

    def test_mixed_pending_batch_cannot_be_replayed(self):
        self.app.accept('mixed',[CMD,['metta','(+ 1 2)']]);self.app.close();self.app=None
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'): Application(self.path)

    def test_exclusive_application_route_and_finite_admission(self):
        with self.assertRaisesRegex(ContractError,'OVERLOADED'): Application(self.path)
        # Application-owned capacity fault fixture; no provider state/answer injection.
        with self.app.db:
            for i in range(c.MAX_REQUESTS):
                self.app.db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?,?,NULL,1)',
                                    (0,i,str(i),canonical(PREMISES).decode(),1))
        with self.assertRaisesRegex(ContractError,'OVERLOADED'): self.app.accept(COMMAND,[CMD])
        self.assertIsNone(self.app.pending())

    def test_startup_overlay_refuses_unknown_source(self):
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'): adapted_skill('(unknown)')
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'): adapted_loop('(unknown)')

    def test_unfinished_unrelated_caller_request_blocks_new_turn(self):
        self.h.submit()
        with self.assertRaisesRegex(ContractError,'OVERLOADED'): self.app.more()
        with self.assertRaisesRegex(ContractError,'OVERLOADED'): self.app.accept(COMMAND,[CMD])
        self.assertIsNone(self.app.pending())
        self.assertEqual(self.h.counts()['jobs'],1)
        self.assertEqual(self.h.counts()['caller_acked'],0)
