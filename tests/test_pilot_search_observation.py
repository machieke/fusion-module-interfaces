"""Real Chroma reopen against a disposable Search copy; vectors are fixtures."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError
from fusion.policy import Policy
from integration.single_node.pilot_search_observation import prepare,inventory


class SearchObservation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.state=self.root/'state';self.run=self.root/'run'
        self.state.mkdir();self.run.mkdir();self.memory=self.state/'memory';self.memory.mkdir()
        (self.state/'restore-fence.json').write_text(json.dumps(dict(mode='READ_ONLY_RECONCILIATION',role='fusion-search',external_effect_authority=False)))
        self.settings=dict(role='fusion-search',preview=dict(pilot=dict(profile='omega-operator-pilot/1')))
        self.config={k:dict(root=str(self.memory)) for k in ('memory_read','memory_append','active_memory')}
        self.config['principals']={'reader':dict(credential='fixture-token',scopes={'synthetic-test':['search.query']})}
        self.config['source']=dict(endpoint='unchanged-authoritative-source')
        self.path=self.run/'owner.json';self.save()
    def tearDown(self):self.tmp.cleanup()
    def save(self):self.path.write_text(json.dumps(self.config))
    def test_real_chroma_read_mutates_only_private_ephemeral_copy(self):
        code='''import chromadb,sys,json
client=chromadb.PersistentClient(path=sys.argv[1]);c=client.get_or_create_collection('synthetic-records')
if sys.argv[2]=='create':c.add(ids=['fixture-id'],embeddings=[[1.0,0.0]],documents=['synthetic fixture'])
else:
 v=c.get(include=['embeddings','documents']);print(json.dumps({'ids':v['ids'],'embeddings':v['embeddings'].tolist(),'documents':v['documents']}))
'''
        original=self.memory/'search'/'fixture-generation'/'index'
        subprocess.run([sys.executable,'-c',code,str(original),'create'],check=True,capture_output=True)
        before=inventory(self.memory);result=prepare(self.settings,self.run,self.state)
        current=json.loads(self.path.read_bytes());target=Path(current['memory_read']['root']);self.assertEqual(inventory(target),before)
        value=json.loads(subprocess.run([sys.executable,'-c',code,str(target/'search'/'fixture-generation'/'index'),'read'],check=True,capture_output=True,text=True).stdout)
        self.assertEqual(value,dict(ids=['fixture-id'],embeddings=[[1.0,0.0]],documents=['synthetic fixture']))
        self.assertEqual(inventory(self.memory),before);self.assertNotEqual(inventory(target),before)
        self.assertFalse(result['imported_checkpoint_changed']);self.assertEqual(result['new_generations'],0)
        for key in ('principals','source'):self.assertEqual(current[key],self.config[key])
        Policy(self.path).check('reader','synthetic-test','search.query')
        current['principals']['reader']['scopes']={};self.path.write_text(json.dumps(current))
        with self.assertRaises(ContractError) as error:Policy(self.path).check('reader','synthetic-test','search.query')
        self.assertEqual(error.exception.code,'UNAUTHORIZED')
    def test_symlink_and_external_root_fail_closed(self):
        (self.memory/'unsafe').symlink_to(self.path)
        with self.assertRaises(ContractError):prepare(self.settings,self.run,self.state)
        self.assertEqual(json.loads(self.path.read_bytes()),self.config)
        (self.memory/'unsafe').unlink()
        for k in ('memory_read','memory_append','active_memory'):self.config[k]['root']=str(self.run/'memory')
        self.save()
        with self.assertRaises(ContractError):prepare(self.settings,self.run,self.state)
    def test_size_refusal_publishes_no_runtime_selection(self):
        (self.memory/'bounded').write_bytes(b'12345')
        with patch('integration.single_node.pilot_search_observation.MAX_BYTES',4):
            with self.assertRaises(ContractError) as error:prepare(self.settings,self.run,self.state)
        self.assertEqual(error.exception.code,'OVERLOADED');self.assertEqual(json.loads(self.path.read_bytes()),self.config)
        self.assertFalse(list(self.run.glob('pilot-search-observation-*')))
    def test_private_partitions_keep_separate_current_authority(self):
        scopes={}
        for name in ('private-a','private-b'):
            directory=self.run/'scopes'/name;directory.mkdir(parents=True);root=self.state/'scopes'/name/'memory';root.mkdir(parents=True)
            (root/'retained.json').write_text(name)
            cfg=copy.deepcopy(self.config)
            for k in ('memory_read','memory_append','active_memory'):cfg[k]['root']=str(root)
            cfg['principals']={name:dict(credential=name,scopes={name:['search.query']})}
            (directory/'owner.json').write_text(json.dumps(cfg));scopes[name]=dict(directory=str(directory),state=str(root.parent))
        self.config['scope_routes']=dict(scopes=scopes);self.save();value=prepare(self.settings,self.run,self.state)
        self.assertEqual(len(value['roots']),3)
        for name,item in scopes.items():
            path=Path(item['directory'])/'owner.json';cfg=json.loads(path.read_bytes())
            self.assertEqual((Path(cfg['memory_read']['root'])/'retained.json').read_text(),name)
            self.assertEqual(set(cfg['principals']),{name});Policy(path).check(name,name,'search.query')
            with self.assertRaises(ContractError):Policy(path).check('reader',name,'search.query')
    def test_only_explicit_pilot_search_restore_selected(self):
        other=copy.deepcopy(self.settings);other['role']='fusion-storage';self.assertIsNone(prepare(other,self.run,self.state))
        self.assertIsNone(prepare(dict(role='fusion-search'),self.run,self.state))
        (self.state/'restore-fence.json').write_text(json.dumps(dict(mode='OTHER',role='fusion-search')))
        with self.assertRaises(ContractError):prepare(self.settings,self.run,self.state)
    def test_owner_and_runtime_traversal_or_symlink_refused(self):
        outside=self.root/'outside';(outside/'memory').mkdir(parents=True)
        for unsafe in (str(self.state)+'/../outside/memory',str(self.state)+'/./memory'):
            for k in ('memory_read','memory_append','active_memory'):self.config[k]['root']=unsafe
            self.save()
            with self.assertRaises(ContractError) as error:prepare(self.settings,self.run,self.state)
            self.assertEqual(error.exception.code,'UNAUTHORIZED')
        for k in ('memory_read','memory_append','active_memory'):self.config[k]['root']=str(self.memory)
        (self.run/'escaped').symlink_to(outside,target_is_directory=True)
        for unsafe in (str(self.run)+'/../outside',str(self.run/'escaped')):
            self.config['scope_routes']=dict(scopes={'bad':dict(directory=unsafe)});self.save()
            with self.assertRaises(ContractError) as error:prepare(self.settings,self.run,self.state)
            self.assertEqual(error.exception.code,'UNAUTHORIZED')
    def test_missing_or_enabled_external_authority_refused(self):
        for value in (None,True):
            fence=dict(mode='READ_ONLY_RECONCILIATION',role='fusion-search')
            if value is not None:fence['external_effect_authority']=value
            (self.state/'restore-fence.json').write_text(json.dumps(fence))
            with self.assertRaises(ContractError) as error:prepare(self.settings,self.run,self.state)
            self.assertEqual(error.exception.code,'UNAUTHORIZED')


if __name__=='__main__':unittest.main()
