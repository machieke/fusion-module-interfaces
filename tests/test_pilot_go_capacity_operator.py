"""Secret/cluster ports are explicit fixtures; no deployed-provider claim."""
import base64,copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from fusion.contracts import ContractError
from examples import pilot_go_capacity as subject

class CapacityOperator(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.op=Mock(namespace='omega-ref-pilot-capacity-fixture')
        self.secret=dict(apiVersion='v1',kind='Secret',metadata=dict(namespace=self.op.namespace,name='fusion-inspect-go-tls-auth',uid='synthetic-secret',resourceVersion='7'),type='Opaque',data={'ca.crt':base64.b64encode(b'-----BEGIN CERTIFICATE-----\nFIXTURE').decode(),'native-token':base64.b64encode(b'unchanged-fixture').decode()})
        self.writes=[];self.resources={};self.fail=False
        def k(*args,**kw):
            if args[0]=='replace':
                value=json.loads(kw['data']);self.writes.append(value)
                if self.fail:raise RuntimeError('explicit lost Secret response fixture')
                self.secret=value;return 'secret replaced'
            if args[:2]==('get','secret'):return json.dumps(self.secret)
            if args[0]=='get':return json.dumps({'items':self.resources.get(args[1],[])})
            raise AssertionError(args)
        self.op.k.side_effect=k
        self.selection=patch.object(subject,'selected',return_value=({'scope':'synthetic-capacity-fixture'},{},{'manifest_sha256':'a'*64},'b'*64));self.selection.start();self.addCleanup(self.selection.stop)
    def provision(self):return subject.provision(self.op,'plan','artifact','chart',self.root/'private')
    def test_fresh_provision_adds_only_scoped_operator_key(self):
        original=copy.deepcopy(self.secret);result=self.provision()
        self.assertEqual(result['status'],'PROVISIONED');self.assertEqual(len(self.writes),1)
        actual=copy.deepcopy(self.writes[0]);token=actual['data'].pop(subject.KEY)
        self.assertEqual(actual,original);self.assertEqual(len(base64.b64decode(token)),64)
        self.assertEqual((self.root/'private/credential').stat().st_mode&0o777,0o600)
        self.assertNotIn(base64.b64decode(token).decode(),json.dumps(result))
        self.assertEqual(result['permission'],'execution.capacity');self.assertFalse(result['caller_permissions_changed'])
    def test_populated_owner_or_existing_key_refuses_before_write(self):
        for kind,name in [('statefulsets','fusion-inspect-go'),('pods','fusion-inspect-go-0'),('pvc','state-fusion-inspect-go-0')]:
            with self.subTest(kind=kind):
                self.resources={kind:[{'metadata':{'name':name}}]}
                with self.assertRaisesRegex(ContractError,'CONFLICT'):self.provision()
                self.assertFalse(self.writes);self.assertFalse((self.root/'private').exists())
        self.resources={};self.secret['data'][subject.KEY]='ZXhpc3Rpbmc='
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.provision()
        self.assertFalse(self.writes)
    def test_uncertain_secret_update_retains_prepared_identity_without_retry(self):
        self.fail=True
        with self.assertRaisesRegex(RuntimeError,'lost Secret response'):self.provision()
        path=self.root/'private/credential';token=path.read_bytes()
        self.assertEqual(json.loads((path.parent/'receipt.json').read_bytes())['status'],'PREPARED')
        with self.assertRaises(FileExistsError):self.provision()
        self.assertEqual(path.read_bytes(),token);self.assertEqual(len(self.writes),1)
    def test_expired_observer_cannot_start_cluster_or_client_activity(self):
        self.op.reset_mock()
        with self.assertRaisesRegex(ContractError,'INVALID_ARGUMENT'):
            subject.observe(self.op,'plan','artifact','chart','provisioned',self.root/'observation',1)
        self.op.k.assert_not_called();self.op.owned.assert_not_called();self.assertFalse((self.root/'observation').exists())

if __name__=='__main__':unittest.main()
