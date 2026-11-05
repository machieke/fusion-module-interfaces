"""Real Registry/session policy composition; explicit TLS/native/readiness fixtures.

This exercises the Registry-enabled boundary omitted by the initial browser
fixture. No Kubernetes, native backend or generative runtime is contacted.
"""
import copy
import unittest
from fusion.contracts import canonical,ContractError
from fusion.policy import Policy
from fusion.provider_lifecycle import Registry
from fusion.provider_retention import PROFILE,LIMITS
from fusion.sustained_sessions import SustainedSessionStore
from tests import test_pilot_browser as browser_fixture
from tests import test_integrated_registry as registry_fixture


class RegistryBrowser(unittest.TestCase):
    def setUp(self):
        self.f=browser_fixture.BrowserTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.selection=registry_fixture.selection(self.f.scope)
        self.selection.update(profile=PROFILE,limits=dict(LIMITS),readiness_ms=300000)
        private=copy.deepcopy(self.selection['records']['storage']);private['scope']='synthetic-private-canary'
        self.selection['records']['private-storage']=private
        self.selection['templates']['private']=['private-storage']
        self.f.cfg['native_sessions']['provider_registry']=self.selection
        self.f.path.write_bytes(canonical(self.f.cfg))
        store=SustainedSessionStore(self.f.cfg['native_sessions']['database'],lambda *_:None,self.f.cfg['native_sessions']['allocation'])
        try:
            registry=Registry(store,self.selection,lambda *_:None)
            for key in self.selection['records']:
                registry.act('fixture-add-'+key,'add',key)
                registry.probe('fixture-probe-'+key,key,lambda _:True)
                registry.act('fixture-enable-'+key,'enable',key)
        finally:store.close()

    def registry(self,user):
        policy=Policy(self.f.path);credential=self.f.cfg['principals']['browser-'+user]['credential']
        def auth(scope,operation):
            self.assertEqual(policy.authenticate(credential),'browser-'+user)
            policy.check('browser-'+user,scope,operation)
        store=SustainedSessionStore(self.f.cfg['native_sessions']['database'],lambda *_:None,self.f.cfg['native_sessions']['allocation'])
        self.addCleanup(store.close)
        return Registry(store,self.selection,auth)

    def test_scoped_developer_allocates_and_reads_real_registry_then_revocation_refuses(self):
        sid=self.f.allocate('registry-enabled')
        with self.f.workbench.as_user('alice'):
            caps=self.f.workbench.capabilities(dict(role='omega-agent',session=sid,commands=[['pin','note','Synthetic registry selection']]))
            self.assertTrue(caps['preflight']['admissible'])
            self.assertEqual(set(caps['provider_lifecycle']),{'storage'})
        reg=self.registry('alice');self.assertEqual(reg.inspect('storage')['state'],'enabled')
        for action in (lambda:reg.inspect('private-storage'),lambda:reg.seal('forbidden-seal','storage'),lambda:reg.act('forbidden-disable','disable','storage')):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):action()
        self.f.cfg['principals']['browser-alice']['scopes'][self.f.scope].remove('providers.select')
        self.f.path.write_bytes(canonical(self.f.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.f.allocate('new-after-revocation')
        self.assertEqual(self.f.allocate('registry-enabled'),sid)
        self.f.cfg['principals']['browser-alice']['scopes'][self.f.scope].remove('providers.inspect')
        self.f.path.write_bytes(canonical(self.f.cfg))
        with self.f.workbench.as_user('alice'),self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
            self.f.workbench.capabilities(dict(role='omega-agent',session=sid))

    def test_viewer_cannot_select_operator_can_seal_only_its_scope(self):
        viewer=self.registry('bob');self.assertEqual(viewer.inspect('private-storage')['state'],'enabled')
        for key in ('storage','private-storage'):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):viewer._record(key,'select')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):viewer.inspect('storage')
        operator=self.registry('operator');self.assertEqual(operator._record('storage','select')[0]['scope'],self.f.scope)
        plan=operator.plan('storage');sealed=operator.seal('operator-exact-seal','storage',plan['head'])
        self.assertEqual(sealed['state'],'sealed')
        self.assertEqual(operator.seal('operator-exact-seal','storage',plan['head']),sealed)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):operator.plan('private-storage')
