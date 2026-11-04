"""Compact application captures; persistent file provider/clock are fixtures."""
import json,unittest
from unittest.mock import patch
from fusion.contracts import ContractError,canonical,digest
from fusion.preview_native_history import NativeHistory,REPRESENTATION,read_body,write_body
from fusion.ports import Mutation
from tests import test_phase2_history_projection as fixture
from tests.test_phase2_native_relations import NOW,SCOPE


class CompactHistory(unittest.TestCase):
    setUp=fixture.HistoryProjectionReconstruction.setUp
    reopen=fixture.HistoryProjectionReconstruction.reopen
    atom_client=fixture.HistoryProjectionReconstruction.atom_client
    record=fixture.HistoryProjectionReconstruction.record
    populate=fixture.HistoryProjectionReconstruction.populate
    def selected(self):
        self.app.config.update(history_representation=REPRESENTATION,history_hydration='bounded-history-hydration/1')
        self.history=NativeHistory(self.app,self.port)
    def test_reference_capture_current_context_exact_and_incremental_changed_window(self):
        self.selected();self.populate();first=self.history.context()
        rows=self.db.execute('SELECT intent FROM preview_history_outbox').fetchall()
        self.assertTrue(all(json.loads(r[0])['profile']==REPRESENTATION and 'body' not in json.loads(r[0]) for r in rows))
        # Historical reader renders the same exact owner records. This is read
        # parity, not permission to mutate a compact journal under an old profile.
        self.app.config.pop('history_representation');historical=NativeHistory(self.app,self.port)
        self.assertEqual(historical.context(),first);self.selected()
        with patch.object(self.atoms,'getMany',wraps=self.atoms.getMany) as batch:
            self.assertEqual(self.history.context(),first);self.assertEqual(batch.call_count,0)
            self.record(7);self.assertEqual(self.history.context(),first)
            self.turn=2;later=self.history.context();self.assertNotEqual(later,first)
            self.assertEqual(batch.call_count,1);self.assertEqual(len(batch.call_args.args[0]),1)
        self.assertEqual(self.db.execute('SELECT count(*) FROM preview_history_materializations').fetchone()[0],4)
        self.turn=1;self.assertEqual(self.history.context(),first)

    def test_revocation_corrupt_cache_and_deleted_cache_reconstruction(self):
        self.selected();self.populate();first=self.history.context()
        self.atom_access.denied.add('get')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.history.context()
        self.atom_access.denied.clear();self.history_access.denied.add('readEpisode')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.history.context()
        self.history_access.denied.clear()
        self.db.execute("UPDATE preview_history_materializations SET body='{}'");self.db.commit()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.history.context()
        self.db.execute('DELETE FROM preview_history_materializations');self.db.commit()
        self.assertEqual(self.history.context(),first)
        self.app.binding['principal']='B'
        # The test authority is explicitly per-method only. Binding changes
        # produce distinct keys; production application authority denies B.
        with patch.object(self.atoms,'getMany',wraps=self.atoms.getMany) as batch:
            self.history.context();self.assertEqual(batch.call_count,1)

    def test_capture_commit_interruption_and_outbox_recovery_do_not_mint_events(self):
        self.selected();body=dict(observed_ms=NOW+1,result='synthetic '*1200)
        def interrupt(where):
            if where=='after_history_capture_commit':raise RuntimeError('fixture-interruption')
        self.app.hook=interrupt
        with self.assertRaisesRegex(RuntimeError,'fixture-interruption'):
            self.history.record('capture','tool-result',body,deadline=NOW+120000)
        head=self.atoms.head(SCOPE);self.assertEqual(self.db.execute('SELECT count(*) FROM preview_history_outbox').fetchone()[0],0)
        self.app.hook=lambda _:None
        self.history.record('capture','tool-result',body,deadline=NOW+120000)
        receipt=self.db.execute('SELECT intent,receipt FROM preview_history_outbox').fetchone()
        self.assertLess(len(receipt['intent']),len(canonical(body))//4)
        snapshot=self.history.context();after=self.atoms.head(SCOPE)
        self.history.record('capture','tool-result',body,deadline=NOW+120000)
        self.assertEqual(self.atoms.head(SCOPE),after);self.assertEqual(self.history.context(),snapshot)
        self.assertEqual(json.loads(receipt['receipt'])['head'],1)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            self.history.record('capture','tool-result',dict(body,result='altered'),deadline=NOW+120000)
        self.assertLess(head['sequence'],after['sequence']) # C1 event commits separately.

    def test_missing_dependency_and_nonterminal_nested_capture_fail_closed(self):
        self.selected();body=dict(observed_ms=NOW+1,text='synthetic '*1200)
        self.history.record('large','input-receipt',body,deadline=NOW+120000);self.history.context()
        # Delete a fixture-owned payload to model missing authoritative storage.
        # A hydrated application cache cannot hide loss of a required chunk.
        state=json.loads(self.atom_path.read_bytes())
        root=json.loads(self.db.execute('SELECT intent FROM preview_history_outbox').fetchone()[0])['payload']
        import base64
        manifest=next(json.loads(base64.b64decode(r['bytes'])) for r in state['atoms'] if r['write']['ref']==root)
        victim=manifest['chunks'][0]
        state['atoms']=[r for r in state['atoms'] if r['write']['ref']!=victim]
        self.atom_path.write_bytes(canonical(state))
        with self.assertRaisesRegex(ContractError,'NOT_FOUND'):self.history.context()
        small=write_body(self.atoms,SCOPE,'terminal',canonical(dict(text='ok')))['ref']
        malformed=canonical(dict(profile='omega-session-chunks/1',bytes=13,sha256=digest(b'{}'),chunks=[small]))
        ref=self.atoms.create(Mutation(SCOPE,'nested'),'application/omega-session-chunks-v1',malformed)['ref']
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):read_body(self.atoms,ref,batched=True)

if __name__=='__main__':unittest.main()
