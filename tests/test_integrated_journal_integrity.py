"""Disposable owner snapshots; native answers and payload backend are fixtures."""
import sqlite3,unittest
from fusion.contracts import canonical,digest
from integration.single_node.integrated_journal_integrity import inspect
from tests import test_integrated_continuation as continuation_fixture
from tests import test_phase2_history_relations as relation_fixture
SCOPE=relation_fixture.SCOPE
from fusion.ports import Mutation

class JournalIntegrity(unittest.TestCase):
    def run_check(self,db):
        return inspect(db,{x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")})
    def test_inspection_causal_edge_and_capture_corruption_are_not_repaired(self):
        f=continuation_fixture.Continuations('test_fixed_graph_capture_and_observation_does_not_execute');f.setUp();self.addCleanup(f.doCleanups)
        result=f.replay();db=f.app.db
        with db:
            db.execute('CREATE TABLE app_occurrences(id,deadline,done,result)')
            db.execute('INSERT INTO app_occurrences VALUES(?,?,?,?)',(f.row['id'],f.row['deadline'],1,result))
        self.assertEqual(self.run_check(db)['findings'],[])
        with db:db.execute("UPDATE integrated_inspection_steps SET inputs='{}' WHERE step='result'")
        report=self.run_check(db);self.assertEqual(report['findings'][0]['classification'],'CORRUPT_CONTINUATION_CAPTURE')
        self.assertEqual(report['repair'],'NONE');self.assertFalse(report['effect_replay'])
        self.assertEqual(db.execute("SELECT inputs FROM integrated_inspection_steps WHERE step='result'").fetchone()[0],'{}')
    def test_retained_view_digest_and_missing_binding_are_distinct_from_no_history(self):
        with sqlite3.connect(':memory:') as db:
            db.row_factory=sqlite3.Row;db.executescript('CREATE TABLE app_read_views(id,value);CREATE TABLE app_active_view(view);')
            self.assertEqual(self.run_check(db)['findings'],[])
            value={'snapshot':'fixture'};key=digest(canonical(value));db.execute('INSERT INTO app_read_views VALUES(?,?)',(key,canonical(value).decode()))
            db.execute('INSERT INTO app_active_view VALUES(?)',(key,));self.assertEqual(self.run_check(db)['findings'],[])
            db.execute("UPDATE app_read_views SET value='{}'")
            self.assertEqual(self.run_check(db)['findings'][0]['classification'],'CORRUPT_RETAINED_VIEW')
    def test_relation_receipt_projection_and_retraction_reference_checked(self):
        f=relation_fixture.OwnerFixture();f.setUp();self.addCleanup(f.doCleanups)
        a=f.payload('a');b=f.payload('b');owner=f.relations()
        written=owner.assertRelation(Mutation(SCOPE,'assert'),'requires/1',(('dependent',a),('prerequisite',b)),True)
        owner.retract(Mutation(SCOPE,'retract'),written['ref'],written['asserted_at'])
        with sqlite3.connect(owner.path) as db:
            db.row_factory=sqlite3.Row;value=self.run_check(db)
            self.assertEqual(value['findings'],[]);self.assertEqual(value['checked']['relation_events'],2)
            db.execute("UPDATE preview_relation_intents SET result='{}' WHERE identity=(SELECT identity FROM preview_relation_events WHERE kind='retract')")
            self.assertEqual(self.run_check(db)['findings'][0]['classification'],'INCONSISTENT_RELATION_JOURNAL')

if __name__=='__main__':unittest.main()
