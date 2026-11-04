"""Application-owner lifecycle; fake health/clock, real SQLite and SIGKILL.

Network/deployed observations are separate gates. No generative runtime.
"""
import copy,json,multiprocessing,os,signal,tempfile,unittest
from pathlib import Path
from fusion.contracts import canonical,ContractError
from fusion.registry import descriptors,descriptor_wire,selection_token
from fusion.provider_lifecycle import Registry,PROFILE,configuration
from fusion.sustained_sessions import SustainedSessionStore
from tests.test_phase3_sessions import policy


def selection(scope):
    d=descriptors()[0]
    r=dict(scope=scope,endpoint=dict(host='fusion-storage.test.svc.cluster.local',port=8443,ca_sha256='c'*64),
        implementation=dict(image='a'*64,source='b'*64),capabilities=[descriptor_wire(d)],
        requirements=[dict(interface=d.interface,minimum='1.0.0',maximum_exclusive='2.0.0',profile='immutable-bytes/1',
            operations=['get'],guarantees=['scoped'],features=[],privacy=d.privacy,payload_bytes=1)],conformance=[])
    return dict(profile=PROFILE,readiness_ms=500,records={'storage':r},templates={'shared':['storage']})


class Lifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'sessions.sqlite';self.cfg=policy();self.now=[1000];self.denied=set()
        self.scope=self.cfg['templates']['shared']['scope'];self.selected=selection(self.scope)
        self.store=SustainedSessionStore(self.path,lambda *_:None,self.cfg,clock=lambda:self.now[0]);self.addCleanup(self.store.close)
        self.registry=Registry(self.store,self.selected,self.auth)
    def auth(self,scope,op):
        if scope!=self.scope or op in self.denied:raise ContractError('UNAUTHORIZED')
    def setup_provider(self):
        self.registry.act('add','add','storage');self.registry.probe('probe','storage',lambda _:True);self.registry.act('enable','enable','storage')
    def allocate(self,identity='new'):
        return self.store.allocate('A',identity,'shared',admission=self.registry.admit)
    def test_admission_selection_retained_after_disable_and_retirement(self):
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate()
        self.registry.act('add','add','storage')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.registry.act('enable','enable','storage')
        self.registry.probe('probe','storage',lambda _:True);self.registry.act('enable','enable','storage')
        first=self.allocate();frozen=self.registry.selected(first['session'])
        self.registry.act('disable','disable','storage')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate('second')
        self.assertEqual(self.allocate()['session'],first['session'])
        self.registry.act('retire','retire','storage')
        self.assertEqual(self.registry.selected(first['session']),frozen)
        self.assertEqual(self.store.observe('A',first['session'])['session'],first['session'])
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.registry.act('again','enable','storage')
    def test_new_configured_template_selects_replacement_without_rebinding_old(self):
        self.setup_provider();old=self.allocate();bound=self.registry.selected(old['session'])
        changed=copy.deepcopy(self.selected);new=copy.deepcopy(changed['records']['storage'])
        new['endpoint']['host']='replacement.test.svc.cluster.local';new['implementation']['image']='d'*64
        changed['records']['replacement']=new;changed['templates']['replacement']=['replacement']
        self.cfg['templates']['replacement']=copy.deepcopy(self.cfg['templates']['shared']);self.cfg['templates']['replacement']['runtime_digest']='e'*64
        reg=Registry(self.store,changed,self.auth)
        reg.act('new-add','add','replacement');reg.probe('new-probe','replacement',lambda _:True);reg.act('new-enable','enable','replacement')
        result=self.store.allocate('A','second','replacement',admission=reg.admit)
        self.assertEqual(set(reg.selected(result['session'])),{'replacement'})
        self.assertEqual(reg.selected(old['session']),bound)
    def test_probe_expiry_no_renewal_and_current_revocation(self):
        self.setup_provider();self.now[0]=1500
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate()
        self.assertEqual(self.registry.probe('probe','storage',lambda _:self.fail('reprobe'))['valid_until'],1500)
        self.denied.add('providers.inspect')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.registry.inspect('storage')
        self.denied.add('providers.probe')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.registry.probe('probe','storage',lambda _:True)
    def test_requirement_permutation_keeps_admitted_bytes_actions_and_binding(self):
        second=copy.deepcopy(self.selected['records']['storage']['requirements'][0]);second['payload_bytes']=2
        self.selected['records']['storage']['requirements'].append(second)
        self.setup_provider();first=self.allocate();bound=self.registry.selected(first['session'])
        raw=self.store.db.execute('SELECT record FROM integrated_providers').fetchone()[0]
        changed=copy.deepcopy(self.selected);changed['records']['storage']['requirements'].reverse()
        reg=Registry(self.store,changed,self.auth)
        self.assertEqual(reg.inspect('storage')['advertised'],json.loads(raw))
        self.assertEqual(reg.act('add','add','storage')['state'],'admitted')
        reg.probe('probe','storage',lambda _:self.fail('repeat probe'))
        self.assertEqual(reg.selected(first['session']),bound)
        new=self.store.allocate('A','another','shared',admission=reg.admit)
        self.assertEqual(reg.selected(new['session']),bound)
        self.assertEqual(self.store.db.execute('SELECT record FROM integrated_providers').fetchone()[0],raw)
        changed['records']['storage']['requirements'][0]['payload_bytes']=3
        with self.assertRaisesRegex(ContractError,'CONFLICT'):reg.inspect('storage')
    def test_incompatible_pins_privacy_unknown_fields_and_drift(self):
        self.setup_provider()
        for mutate in (lambda r:r['requirements'][0].update(privacy='weaker'),lambda r:r['implementation'].update(image='no'),lambda r:r.update(callback='arbitrary')):
            v=copy.deepcopy(self.selected);mutate(v['records']['storage'])
            with self.assertRaises((ContractError,TypeError)):configuration(v)
        self.selected['records']['storage']['implementation']['image']='d'*64
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.registry.inspect('storage')
    def test_probe_reservation_survives_actual_kill_without_contact_again(self):
        self.registry.act('add','add','storage')
        def child():
            store=SustainedSessionStore(self.path,lambda *_:None,self.cfg,clock=lambda:1000)
            reg=Registry(store,self.selected,lambda *_:None,lambda name:os.kill(os.getpid(),signal.SIGKILL) if name=='after_provider_probe_reservation' else None)
            reg.probe('killed','storage',lambda _:True)
        p=multiprocessing.get_context('fork').Process(target=child);p.start();p.join(5);self.assertEqual(p.exitcode,-9)
        result=self.registry.probe('killed','storage',lambda _:self.fail('probe replay'))
        self.assertEqual(result['status'],'unknown');self.assertEqual(result['valid_until'],1000)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.registry.act('enable','enable','storage')
    def test_racing_disable_serializes_with_allocation_and_no_quota_refund(self):
        self.setup_provider();first=self.allocate();before=self.store.capacity('A')['logical_bytes']
        self.registry.act('drain','drain','storage')
        self.assertGreater(self.store.capacity('A')['logical_bytes'],before)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate('blocked')
        self.assertEqual(self.store.capacity('A')['retained'],1)
        self.now[0]=1501
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.registry.act('retire','retire','storage')
        result=self.registry.act('retire-unavailable','retire','storage','explicit-unavailable')
        self.assertEqual(result['retained_access'],'explicit-unavailable')
        self.assertEqual(self.store.observe('A',first['session'])['state'],'active')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.registry.act('retire-unavailable','retire','storage','required')

if __name__=='__main__':unittest.main()
