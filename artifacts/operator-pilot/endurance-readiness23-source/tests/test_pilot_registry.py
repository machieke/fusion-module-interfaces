"""Real owner/SQLite; deterministic clock and readiness boundary fixtures."""
import copy,json,multiprocessing,os,signal
from tests.test_integrated_registry import Lifecycle,selection
from fusion.provider_retention import PROFILE,LIMITS
from fusion.provider_lifecycle import Registry,admit_input
from fusion.contracts import canonical,ContractError


class Compact(Lifecycle):
    def setUp(self):
        super().setUp()
        self.selected['profile']=PROFILE;self.selected['limits']=dict(LIMITS)
        self.registry=Registry(self.store,self.selected,self.auth)
    def test_requirement_permutation_keeps_admitted_bytes_actions_and_binding(self):
        second=copy.deepcopy(self.selected['records']['storage']['requirements'][0]);second['payload_bytes']=2
        self.selected['records']['storage']['requirements'].append(second)
        self.setup_provider();session=self.allocate()['session'];before=self.registry.selected(session)
        raw=self.store.db.execute('SELECT record FROM integrated_providers').fetchone()[0]
        changed=copy.deepcopy(self.selected);changed['records']['storage']['requirements'].reverse()
        reg=Registry(self.store,changed,self.auth)
        self.assertEqual(reg.inspect('storage')['advertised'],before['storage']['record'])
        self.assertEqual(reg.act('add','add','storage')['state'],'admitted')
        self.assertEqual(reg.selected(session),before)
        self.assertEqual(self.store.db.execute('SELECT record FROM integrated_providers').fetchone()[0],raw)
        changed['records']['storage']['requirements'][0]['payload_bytes']=3
        with self.assertRaisesRegex(ContractError,'CONFLICT'):reg.inspect('storage')
    def test_seal_exact_binding_receipts_and_replay(self):
        self.setup_provider();session=self.allocate()['session'];before=self.registry.selected(session)
        action=self.registry.act('disable','disable','storage')
        charge=self.registry.headroom()['baseline_equivalent']
        sealed=self.registry.seal('epoch-1','storage')
        self.assertEqual(self.registry.headroom()['baseline_equivalent'],charge)
        self.assertEqual(self.registry.seal('epoch-1','storage'),sealed)
        self.assertEqual(self.registry.act('disable','disable','storage'),action)
        self.assertEqual(self.registry.probe('probe','storage',lambda _:self.fail('reprobe'))['valid_until'],1500)
        self.assertEqual(self.registry.selected(session),before)
        self.assertEqual(self.registry.headroom()['usage']['actions'],4)
        self.assertEqual(self.registry.headroom()['usage']['active_actions'],0)
        self.denied.add('providers.seal')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.registry.seal('epoch-1','storage')
    def test_missing_object_and_corrupt_epoch_refuse(self):
        self.setup_provider();self.allocate();self.registry.seal('first','storage')
        self.store.db.execute("UPDATE pilot_registry_epochs SET body='[]'");self.store.db.commit()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.registry.act('add','add','storage')
        self.store.db.execute('DELETE FROM pilot_registry_objects');self.store.db.commit()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.registry.inspect('storage')
    def test_nonempty_legacy_never_silently_migrates(self):
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):Registry(self.store,selection(self.scope),self.auth)
    def test_same_owner_transaction_publishes_selection(self):
        self.setup_provider();s=self.allocate()['session']
        with self.store.db:
            self.store.db.execute('BEGIN IMMEDIATE');admit_input(self.store.db,s)
        self.registry.act('disable','disable','storage')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):admit_input(self.store.db,s)
    def test_plan_interrupt_replay_retains_unknown_probe_and_budget(self):
        self.setup_provider()
        self.registry.hook=lambda stage: (_ for _ in ()).throw(RuntimeError(stage)) if stage=='after_provider_probe_reservation' else None
        with self.assertRaises(RuntimeError):self.registry.probe('lost','storage',lambda _:self.fail('contact'))
        self.registry.hook=lambda stage: (_ for _ in ()).throw(RuntimeError(stage)) if stage=='after_provider_epoch_plan' else None
        with self.assertRaises(RuntimeError):self.registry.seal('epoch','storage')
        self.registry.hook=lambda _:None;self.registry.seal('epoch','storage')
        self.assertEqual(self.registry.probe('lost','storage',lambda _:self.fail('repeat'))['status'],'unknown')
        self.assertEqual(self.registry.headroom()['usage']['actions'],4)
    def test_finite_retention_boundary_and_control_reserve(self):
        # Fresh registry in a separate owner, not changing an accepted policy.
        self.registry.retention.limits['active_actions']=5
        self.setup_provider();self.registry.probe('fourth','storage',lambda _:True)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):self.registry.probe('refuse','storage',lambda _:True)
        self.registry.act('disable','disable','storage')
        self.registry.seal('make-active-space','storage')
        self.assertEqual(self.registry.inspect('storage')['state'],'disabled')
        self.assertEqual(self.registry.headroom()['usage']['actions'],5)
    def test_equal_workload_metadata_repetition_beyond_legacy_bytes(self):
        # Requirements remain a conjunction, but their admitted order is exact.
        self.selected['records']['storage']['conformance']=['f'*64]*8
        self.registry=Registry(self.store,self.selected,self.auth);self.setup_provider()
        baseline=0
        for n in range(700):
            identity='probe-'+str(n);self.registry.probe(identity,'storage',lambda _:True)
            result=self.registry.retention.action(identity)
            baseline+=len(result['intent'].encode())+len(result['result'].encode())
            if n%32==31:self.registry.seal('epoch-'+str(n),'storage')
        self.assertGreater(baseline,1048576)
        actual=self.registry.headroom()['usage']
        self.assertLess(actual['retained_bytes'],baseline)
        self.assertEqual(actual['actions'],703)
        self.assertEqual(self.registry.probe('probe-0','storage',lambda _:self.fail('repeat'))['valid_until'],1500)
