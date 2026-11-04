"""Missing volatile configuration must not require native redispatch.

Real configuration and SQLite; fixture certificates, no remote or native work.
The unselected inspection tool deliberately refuses after template recovery.
"""
import json,sqlite3,unittest,uuid
from unittest.mock import patch
from fusion.contracts import canonical,ContractError
from fusion.inspection_continuation import PROFILE
from integration.single_node.integrated_continuation import invoke
from tests import test_integrated_permissions as fixture


class RetainedConfiguration(unittest.TestCase):
    def setUp(self):
        self.f=fixture.CapabilityInspection();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.state/'sessions'/self.f.sid;self.root.mkdir(parents=True)
        with sqlite3.connect(self.root/'caller.sqlite') as db:db.execute('CREATE TABLE retained_fixture(value TEXT)')
        self.q=dict(profile=PROFILE,id='observe-after-restart',operation='observe',session=self.f.sid,
                    occurrence=str(uuid.uuid4()),identity=None)
    def call(self,token=None):return invoke(self.f.path,self.f.state,self.f.run,token or self.f.token,self.q)
    def test_accepted_configuration_recovers_without_application_or_network(self):
        before=(self.root/'caller.sqlite').read_bytes()
        with patch('fusion.preview_transport.invoke',side_effect=AssertionError('no provider request')):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call()
        app=self.f.run/'sessions'/self.f.sid/'application.json'
        self.assertTrue(app.is_file());self.assertEqual(json.loads(app.read_bytes())['session_id'],self.f.sid)
        self.assertEqual(before,(self.root/'caller.sqlite').read_bytes())
        with sqlite3.connect(self.f.cfg['native_sessions']['database']) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM preview_inputs').fetchone()[0],0)
    def test_wrong_authority_cannot_materialize(self):
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.call('wrong-token')
        self.assertFalse((self.f.run/'sessions'/self.f.sid).exists())
    def test_changed_accepted_template_refuses_before_configuration_recovery(self):
        path=self.f.run/'templates'/'shared'/'application.json';v=json.loads(path.read_bytes())
        v['invocation_timeout_ms']+=1;path.write_bytes(canonical(v))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.call()
        self.assertFalse((self.f.run/'sessions'/self.f.sid).exists())


if __name__=='__main__':unittest.main()
