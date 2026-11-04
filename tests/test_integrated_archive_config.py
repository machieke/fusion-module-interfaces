"""Real trusted configuration/policy; endpoints/TLS and native assets uncalled."""
import json,unittest
from fusion import archive_contracts as a,cognitive_services as c
from fusion.contracts import ContractError
from integration.single_node.preview_secrets import material
from tests import test_phase3_composition as fixture

class ArchiveConfiguration(unittest.TestCase):
    settings=fixture.DynamicConfiguration.settings
    build=fixture.DynamicConfiguration.build
    def setUp(self):
        fixture.DynamicConfiguration.setUp(self)
        self.preview['sustained'].update(storage_archive=dict(a.DEFAULT),private_scopes=True)
        for role,spec in self.preview['agents'].items():spec['private_scope']='synthetic-private-'+spec['principal'].lower()
        (self.root/'fusion-storage/secrets/archive-operator-token').write_text('generated-archive-operator-token-'*2)
    def test_all_storage_protocols_select_same_owner_and_agents_gain_no_archive_authority(self):
        _,cfg,state,run=self.build('fusion-storage')
        for directory in (run,run/'scopes/private-a',run/'scopes/private-b'):
            owner=json.loads((directory/'owner.json').read_bytes());cog=json.loads((directory/'cognitive-owner.json').read_bytes())
            self.assertEqual(owner['memory_read']['archive'],a.DEFAULT)
            self.assertEqual(owner['memory_append']['archive'],a.DEFAULT)
            self.assertEqual(cog['archive'],a.DEFAULT)
            token=cog['principals']['archive-operator']['credential'];scope=cog['scope']
            access=c.Access(directory/'cognitive-owner.json',token,'atom.storage')
            new=c.descriptors(feed_profile=cog['feed_profile'],archive=True)[-1]
            from fusion.registry import selection_token
            selected=c.Access(directory/'cognitive-owner.json',token,'atom.storage',selection_token(new))
            self.assertEqual(selected.authorize(scope,'publishArchive'),'archive-operator')
            self.assertEqual(access.descriptor.version,'1.0.0')
            for actor in ('A','B'):
                if actor in cog['principals']:
                    actor_access=c.Access(directory/'cognitive-owner.json',cog['principals'][actor]['credential'],'atom.storage',selection_token(new))
                    with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):actor_access.authorize(scope,'publishArchive')
        self.assertFalse(list(state.rglob('*.sqlite')))
    def test_secret_reference_is_storage_only_and_absent_when_unselected(self):
        clients={role:(self.root/role/'secrets/caller-token').read_text() for role in self.roles if role not in self.preview['agents']}
        generated=material(self.preview,self.roles,clients)
        self.assertEqual([role for role,value in generated.items() if 'archive-operator-token' in value],['fusion-storage'])
        self.preview['sustained'].pop('storage_archive')
        self.assertFalse(any('archive-operator-token' in value for value in material(self.preview,self.roles,clients).values()))

if __name__=='__main__':unittest.main()
