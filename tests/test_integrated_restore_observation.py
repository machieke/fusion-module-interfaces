"""Read-only application/continuation clone. Native/chain captures are fixtures."""
import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import canonical,ContractError
from fusion.sustained_sessions import SustainedSessionStore
from fusion.chain_continuation import PROFILE
from integration.single_node.integrated_restore_observation import invoke
from tests.test_integrated_chain_continuation import ChainContinuation
from tests.test_phase3_sessions import policy

class RestoredContinuation(unittest.TestCase):
    def setUp(self):
        f=ChainContinuation('test_fixed_graph_exact_native_origin_separate_approval_and_single_submit');f.setUp();self.fixture=f
        self.addCleanup(f.doCleanups);self.addCleanup(f.tearDown)
        f.admit();f.owner.reserve(f.occurrence,'submit')
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);root=Path(self.temp.name)
        self.state=root/'state';self.state.mkdir();self.config=root/'owner.json';cfg=policy();self.scope=f.registration['approved']['scope_ref']
        cfg['templates']['shared']['scope']=self.scope
        store=SustainedSessionStore(self.state/'session-inbox.sqlite',lambda *_:None,cfg,clock=lambda:1000)
        try:self.sid=store.allocate('A','one','shared')['session']
        finally:store.close()
        saved=self.state/'sessions'/self.sid;saved.mkdir(parents=True)
        with sqlite3.connect(saved/'caller.sqlite') as db:f.db.backup(db)
        self.db=saved/'caller.sqlite'
        (self.state/'restore-fence.json').write_bytes(canonical(dict(mode='READ_ONLY_RECONCILIATION',external_effect_authority=False)))
        self.cfg=dict(principals={'operator':dict(credential='fresh-clone-fixture-credential',scopes={self.scope:['sessions.observe','sessions.disclose']})},
            native_sessions=dict(principal='A',database=str(self.state/'session-inbox.sqlite'),allocation=cfg))
        self.config.write_bytes(canonical(self.cfg))
        self.q=dict(profile=PROFILE,id='observation',session=self.sid,occurrence=f.occurrence,operation='observe',body={})
    def call(self,q=None,credential='fresh-clone-fixture-credential'):
        return invoke(self.config,self.state,credential,q or self.q)['value']
    def test_uncertain_submit_retains_spent_budget_no_client_and_fresh_authority(self):
        before=self.db.read_bytes();calls=list(self.fixture.api.calls)
        with patch('fusion.preview_chain.Client',side_effect=AssertionError('network client forbidden')):
            value=self.call();self.assertEqual(value,self.call())
        self.assertTrue(value['restore_fenced']);self.assertFalse(value['execution_authorized'])
        self.assertFalse(value['retained_approval_is_current_authority']);self.assertEqual(value['status'],'needs-reconciliation')
        self.assertEqual(value['submit_reservations'],1);self.assertEqual(value['observations_spent'],0)
        self.assertEqual(value['deadline_ms'],self.fixture.deadline);self.assertEqual(value['origin']['original_deadline_ms'],self.fixture.now-1)
        self.assertEqual(self.db.read_bytes(),before);self.assertEqual(self.fixture.api.calls,calls)
    def test_all_mutations_and_revocation_refuse_even_with_old_approval(self):
        for operation in ('admit','advance','cancel'):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call(dict(self.q,operation=operation))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call(credential='old-credential')
        self.cfg['principals']['operator']['scopes']={};self.config.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call()
    def test_corrupt_captured_native_result_refuses_without_repair(self):
        with sqlite3.connect(self.db) as db:db.execute("UPDATE preview_inspections SET result='{}'")
        before=self.db.read_bytes()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.call()
        self.assertEqual(before,self.db.read_bytes())

if __name__=='__main__':unittest.main()
