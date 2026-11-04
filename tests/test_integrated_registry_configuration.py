"""Actual operator configuration and owner ports; fake TLS/health only."""
import copy,json,unittest
from fusion.contracts import canonical,ContractError
from fusion.provider_lifecycle import PROFILE
from fusion.sustained_sessions import PROFILE as SESSIONS
from fusion.preview_session_service import SessionPorts
from integration.single_node.integrated_registry import ROLES,invoke
from tests import test_phase3_composition as fixture

class Composition(unittest.TestCase):
    settings=fixture.DynamicConfiguration.settings
    build=fixture.DynamicConfiguration.build
    def setUp(self):
        fixture.DynamicConfiguration.setUp(self)
        self.preview['sustained']['provider_registry']=dict(profile=PROFILE,pins={role:dict(image='a'*64,source='b'*64) for role in ROLES.values()},readiness_ms=300000)
        self.preview['sustained']['private_scopes']=True
        for role,spec in self.preview['agents'].items():spec['private_scope']=self.scope+'-private-'+spec['principal'].lower()
        _,self.cfg,self.state,self.run=self.build();self.path=self.run/'owner.json';self.token=self.cfg['principals']['operator']['credential']
    def action(self,op,body,token=None):
        return invoke(self.path,token or self.token,dict(id='rpc',profile=PROFILE,operation=op,body=body),probe=lambda _:True)['value']
    def allocate(self,name='a',template='shared'):
        return SessionPorts(self.path).invoke(self.token,dict(id='a',profile=SESSIONS,operation='allocate',body=dict(identity=name,template=template)))['value']
    def test_exact_catalogue_and_current_lifecycle_gate_before_acceptance(self):
        cfg=self.cfg['native_sessions']['provider_registry'];self.assertEqual(set(cfg['templates']),{'shared','private'})
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate()
        for key in cfg['templates']['shared']:
            self.action('add',dict(provider=key,identity=key+'-add'))
            self.action('probe',dict(provider=key,identity=key+'-probe'))
            self.action('enable',dict(provider=key,identity=key+'-enable'))
        first=self.allocate();selection=self.action('selected',dict(session=first['session']))
        self.assertEqual(set(selection),set(cfg['templates']['shared']))
        key=cfg['templates']['shared'][0];self.action('drain',dict(provider=key,identity='drain'))
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate('b')
        self.assertEqual(self.allocate()['session'],first['session'])
        self.assertEqual(self.action('selected',dict(session=first['session'])),selection)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate('private','private')
    def test_model_cannot_self_register_probe_or_leak_private_metadata(self):
        cfg=self.cfg['native_sessions']['provider_registry'];key=cfg['templates']['private'][0]
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.action('inspect',dict(provider=key),self.cfg['principals']['worker']['credential'])
        scope=cfg['records'][key]['scope'];self.cfg['principals']['operator']['scopes'][scope]=[];self.path.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.action('inspect',dict(provider=key))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.action('add',dict(provider='self-announced',identity='arbitrary'))

    def test_compatible_rollover_selects_new_records_only_for_new_allocation(self):
        cfg=self.cfg['native_sessions']['provider_registry']
        for key in cfg['templates']['shared']:
            for operation in ('add','probe','enable'):self.action(operation,dict(provider=key,identity=key+'-'+operation))
        first=self.allocate();original=self.action('selected',dict(session=first['session']))
        self.preview['sustained']['provider_registry']['rollover']=dict(identity='compatible-v2',pins={'fusion-execution':dict(image='c'*64,source='d'*64)})
        _,self.cfg,_,_=self.build()
        current=self.cfg['native_sessions']['provider_registry'];replacement='compatible-v2-shared-fusion-execution'
        self.assertIn(replacement,current['templates']['shared'])
        self.assertNotIn('shared-fusion-execution',current['templates']['shared'])
        self.assertEqual(current['records']['shared-fusion-execution'],cfg['records']['shared-fusion-execution'])
        self.assertEqual(self.action('selected',dict(session=first['session'])),original)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.allocate('next')
        for operation in ('add','probe','enable'):self.action(operation,dict(provider=replacement,identity=replacement+'-'+operation))
        second=self.allocate('next');selected=self.action('selected',dict(session=second['session']))
        self.assertEqual(selected[replacement]['record']['implementation']['image'],'c'*64)
        self.action('drain',dict(provider='shared-fusion-execution',identity='retire-old-drain'))
        self.assertEqual(self.action('selected',dict(session=first['session'])),original)
        self.assertNotEqual(first['session'],second['session'])

    def test_rollover_cannot_rewrite_an_admitted_record_or_exceed_capacity(self):
        key='shared-fusion-execution';self.action('add',dict(provider=key,identity='original'))
        self.preview['sustained']['provider_registry']['pins']['fusion-execution']['source']='f'*64
        self.build()
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.action('inspect',dict(provider=key))
        self.preview['sustained']['provider_registry']['rollover']=dict(identity='bounded',pins={role:dict(image='c'*64,source='d'*64) for role in ROLES.values()})
        # Two templates' complete duplicate sets exceed the existing 32 records.
        with self.assertRaises(ContractError):self.build()

    def test_explicit_retained_catalogue_is_not_regenerated_by_new_caller(self):
        old=self.cfg['native_sessions']['provider_registry']['records']['shared-fusion-messaging']
        # Stand-in for a genuinely earlier catalogue. An exported record keeps
        # its old exact capability metadata, including implementation version.
        earlier=copy.deepcopy(old)
        earlier['capabilities'][0]['implementation_version']='0.1.0'
        self.preview['sustained']['provider_registry']['rollover']=dict(identity='v2',pins={'fusion-execution':dict(image='c'*64,source='d'*64)},retained_records={'shared-fusion-messaging':earlier})
        _,cfg,_,_=self.build()
        self.assertEqual(cfg['native_sessions']['provider_registry']['records']['shared-fusion-messaging'],earlier)
        earlier['implementation']['image']='e'*64
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.build()

if __name__=='__main__':unittest.main()
