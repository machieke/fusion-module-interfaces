"""Real read-only restored SQLite; authorization/configuration are synthetic."""
import copy,json,tempfile,unittest
from pathlib import Path
from fusion.contracts import canonical,ContractError
from fusion.sustained_sessions import SustainedSessionStore,PROFILE
from fusion.sustained_restore import Ports
from tests.test_phase3_sessions import policy


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.allocation=policy();self.scope=self.allocation['templates']['shared']['scope']
        self.db=self.root/'inbox.sqlite';store=SustainedSessionStore(self.db,lambda *x:None,self.allocation,clock=lambda:1000)
        try:
            self.sid=store.allocate('A','original','shared')['session']
            store.submit('A',self.sid,'one','synthetic pinned note','task');store.next_input('A',self.sid)
            store.complete('A',self.sid,'one',dict(turn=1,projection='actual saved fixture projection',occurrences=['known-effect']))
            store.submit('A',self.sid,'uncertain','fixture external effect','task');store.next_input('A',self.sid)
            store.cancel('A',self.sid,'cancel-request','uncertain')
        finally:store.close()
        fresh=copy.deepcopy(self.allocation);fresh['templates']['shared']['runtime_digest']='b'*64
        self.path=self.root/'owner.json'
        self.cfg=dict(principals={'operator':dict(credential='new-synthetic-clone-authority',scopes={self.scope:['sessions.'+op for op in ('observe','disclose','list','capacity')]})},
            native_sessions=dict(profile=PROFILE,principal='A',database=str(self.db),allocation=fresh))
        self.path.write_bytes(canonical(self.cfg));self.ports=Ports(self.path)
    def call(self,op,body=None,token='new-synthetic-clone-authority'):
        return self.ports.invoke(token,dict(id='read',profile=PROFILE,operation=op,body=body or {}))['value']
    def test_original_binding_captured_results_and_unknown_effect_are_preserved(self):
        before=self.db.read_bytes()
        v=self.call('observe',dict(session=self.sid,content=True))
        self.assertTrue(v['restore_fenced']);self.assertFalse(v['execution_authorized'])
        self.assertEqual(v['allocation']['frozen']['runtime_digest'],'a'*64)
        self.assertEqual(v['inputs'][0]['result']['occurrences'],['known-effect'])
        self.assertEqual(v['inputs'][1]['state'],'cancel-requested')
        self.assertEqual(v['inputs'][1]['deadline'],1100)
        self.assertEqual(self.db.read_bytes(),before)
        capacity=self.call('capacity');self.assertTrue(capacity['capacity_is_not_execution_credit'])
        self.assertEqual(capacity['pending'],1)
    def test_no_effect_operation_or_old_credentials_can_activate_clone(self):
        for op in ('allocate','next','permit','submit','complete','reconcile','resume','cancel'):
            with self.subTest(op=op),self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call(op)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call('list',token='original-authority')
        self.cfg['principals']['operator']['scopes']={};self.path.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call('observe',dict(session=self.sid,content=True))
    def test_restore_owner_mismatch_fails_before_release(self):
        self.cfg['native_sessions']['allocation']['owner']='00000000-0000-0000-0000-000000000000';self.path.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.call('list')

if __name__=='__main__':unittest.main()
