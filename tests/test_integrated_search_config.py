"""Trusted fresh configuration; no real provider/runtime calls in this lane."""
import json,unittest
from fusion.contracts import ContractError,canonical
from fusion.search_repair import PROFILE
from fusion.search_maintenance import Ports
from fusion.registry import selection_token
from fusion.search_repair import descriptor
from integration.single_node.preview_secrets import material
from integration.single_node.owner_seal import selected
from tests import test_phase3_composition as fixture


class SearchConfiguration(unittest.TestCase):
    settings=fixture.DynamicConfiguration.settings
    build=fixture.DynamicConfiguration.build
    def setUp(self):
        fixture.DynamicConfiguration.setUp(self)
        self.preview['memory']['maintenance_profile']=PROFILE
        self.preview['sustained']['private_scopes']=True
        for spec in self.preview['agents'].values():spec['private_scope']='synthetic-repair-private-'+spec['principal'].lower()
        (self.root/'fusion-search/secrets/search-operator-token').write_text('generated-maintenance-token-'*2)
    def test_only_operator_has_maintenance_authority_and_owner_seal(self):
        _,cfg,state,run=self.build('fusion-search')
        self.assertEqual(selected(self.settings('fusion-search'))['search_maintenance'],PROFILE)
        for directory in (run,run/'scopes/private-a',run/'scopes/private-b'):
            path=directory/'owner.json';owned=json.loads(path.read_bytes());active=owned['active_memory']
            self.assertEqual(active['maintenance_profile'],PROFILE)
            q=dict(id='00000000-0000-4000-8000-000000000001',profile=PROFILE,scope=active['scope'],selection=selection_token(descriptor()),operation='planRepair',args=[{}])
            for actor in ('A','B'):
                if actor not in owned['principals']:continue
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):Ports(path).invoke(owned['principals'][actor]['credential'],q)
        self.assertFalse(list(state.rglob('*.sqlite')))
    def test_secret_is_search_only_and_unselected_does_not_change_historical_seal(self):
        clients={role:(self.root/role/'secrets/caller-token').read_text() for role in self.roles if role not in self.preview['agents']}
        generated=material(self.preview,self.roles,clients)
        self.assertEqual([role for role,x in generated.items() if 'search-operator-token' in x],['fusion-search'])
        self.preview['memory'].pop('maintenance_profile')
        self.assertNotIn('search_maintenance',selected(self.settings('fusion-search')))
        self.assertFalse(any('search-operator-token' in x for x in material(self.preview,self.roles,clients).values()))

if __name__=='__main__':unittest.main()
