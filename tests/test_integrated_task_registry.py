"""Real owner journals and process death, in-process task/feed/TLS fixtures.

Selection is committed with incoming session allocation. Native and pod
qualification remain separate; this lane does not supply native results.
"""
import json,multiprocessing,os,unittest
from fusion.contracts import canonical,ContractError
from fusion.provider_lifecycle import Registry
from tests import test_phase3_tasks as tasks
from tests.test_integrated_registry import selection


class IncomingSelection(unittest.TestCase):
    def setUp(self):
        self.t=tasks.AllocatedTaskRouting();self.t.setUp();self.addCleanup(self.t.doCleanups)
        self.t.setup_routes();self.f=self.t.f;self.path=self.f.configs['B']
        self.cfg=json.loads(self.path.read_bytes());self.selected=selection(tasks.fixture.SCOPE)
        self.cfg['native_sessions']['provider_registry']=self.selected
        self.cfg['principals']['worker']['scopes'][tasks.fixture.SCOPE].append('providers.select')
        self.path.write_bytes(canonical(self.cfg))
    def registry(self,action):
        store=self.t.owner('B')
        try:return action(Registry(store,self.selected,lambda *_:None))
        finally:store.close()
    def enable(self):
        def admit(reg):
            reg.act('add','add','storage');reg.probe('probe','storage',lambda _:True);reg.act('enable','enable','storage')
        self.registry(admit)
    def test_missing_admission_rolls_back_allocation_then_atomic_selection(self):
        task=self.f.task();self.f.send(task)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.f.ingress().drain()
        owner=self.t.owner('B')
        try:self.assertEqual(owner.capacity('B')['retained'],1)
        finally:owner.close()
        self.enable();self.assertEqual(self.f.ingress().drain(),'accepted')
        row=self.f.row();sid=row['session'];bound=self.registry(lambda reg:reg.selected(sid))
        self.assertEqual(set(bound),{'storage'})
        owner=self.t.owner('B')
        try:
            inputs=owner.observe('B',sid,True)['inputs'];self.assertEqual(len(inputs),1)
            self.assertEqual(inputs[0]['deadline'],task['deadline'])
        finally:owner.close()
        self.assertEqual(self.f.ingress().drain(),'empty');self.assertEqual(self.registry(lambda reg:reg.selected(sid)),bound)
    def test_worker_select_revocation_prevents_binding_and_admission(self):
        self.enable();self.f.send(self.f.task())
        self.cfg['principals']['worker']['scopes'][tasks.fixture.SCOPE].remove('providers.select');self.path.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.f.ingress().drain()
        owner=self.t.owner('B')
        try:self.assertEqual(owner.capacity('B')['retained'],1)
        finally:owner.close()
    def test_actual_process_exit_after_acceptance_retains_selection_and_deadline(self):
        self.enable();task=self.f.task();self.f.send(task)
        def child():
            self.f.ingress(hook=lambda stage:os._exit(79) if stage=='after_task_session_acceptance' else None).drain()
        process=multiprocessing.get_context('fork').Process(target=child);process.start();process.join(10)
        if process.is_alive():process.kill();process.join();self.fail('commit boundary not reached')
        self.assertEqual(process.exitcode,79)
        self.assertEqual(self.f.ingress().drain(),'accepted');sid=self.f.row()['session']
        self.assertEqual(set(self.registry(lambda reg:reg.selected(sid))),{'storage'})
        owner=self.t.owner('B')
        try:
            rows=owner.observe('B',sid,True)['inputs'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['deadline'],task['deadline'])
        finally:owner.close()
    def test_historical_unbound_allocation_is_not_silently_rebound(self):
        task=self.f.task();allocation='incoming/'+task['sender']+'/'+task['session']
        owner=self.t.owner('B')
        try:sid=owner.allocate('B',allocation,'shared')['session']
        finally:owner.close()
        self.enable();self.f.send(task)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.f.ingress().drain()
        owner=self.t.owner('B')
        try:
            self.assertEqual(owner.observe('B',sid,True)['inputs'],[])
            self.assertIsNone(owner.db.execute('SELECT selection FROM integrated_provider_bindings WHERE session=?',(sid,)).fetchone())
        finally:owner.close()

if __name__=='__main__':unittest.main()
