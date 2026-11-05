"""Pure publication-source qualification. No assembly/network/provider processes."""
import ast,copy,hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

def deny(event,args):
 if event in ('socket.connect','socket.bind','subprocess.Popen','os.system','os.posix_spawn'):raise AssertionError('NETWORK_OR_PROCESS_DENIED')
sys.addaudithook(deny)
from fusion.contracts import ContractError
B=Path('/data/fusion-operator-pilot-release/evidence-assembly');PACKET=Path('/data/fusion-operator-pilot-release/distribution21');BASE=B/'packet18-preparation01/evidence.json'
s=importlib.util.spec_from_file_location('guard07',B/'assemble-final21.guarded25-v07.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
D=m.load(PACKET/'distribution.json');INDEX={x['sha256']:x['path'] for x in D['files']};SELECTED=m.load(PACKET/'evidence/operator-pilot/selected-test-counts-chain25.json')
AUDITS={Path(x['path']).parent.name:m.load(PACKET/INDEX[x['sha256']]) for x in SELECTED['primary_audits'] if Path(x['path']).parent.name in m.NEW_AUDITS}
MISSING={k:{name:pin for name,pin in v['sources'].items() if pin not in INDEX} for k,v in AUDITS.items()}

class HistoricalAuditSources(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir='/data/fusion-operator-pilot-release/tmp');self.root=Path(self.tmp.name);self.base=self.root/'evidence.json';self.source=self.root/'sources/a.py';self.source.parent.mkdir();self.source.write_bytes(b'approved historical source\n');self.pin=m.sha(self.source)
  self.row=dict(id='approved',path='sources/a.py',visibility='approved-public',sha256=self.pin,bytes=self.source.stat().st_size)
 def tearDown(self):self.tmp.cleanup()
 def invoke(self,row=None,phase='historical',pin=None):
  self.base.write_text(json.dumps(dict(artifacts=[row or self.row])))
  with patch.object(m,'BASE_EVIDENCE',m.sha(self.base)):return m.historical_audit_source(self.base,pin or self.pin,phase)
 def test_actual_thirty_three_historical_sources_exact(self):
  self.assertEqual(len(MISSING['authored-publication02']),33)
  rows=m.load(BASE)['artifacts']
  for name,pin in MISSING['authored-publication02'].items():
   with self.subTest(name=name):
    p=m.historical_audit_source(BASE,pin,'historical');matching=[x for x in rows if x['visibility']=='approved-public' and x['sha256']==pin and (BASE.parent/x['path']).resolve()==p]
    self.assertTrue(matching);self.assertEqual(m.sha(p),pin);self.assertEqual(p.stat().st_size,matching[0]['bytes'])
 def test_other_eight_audits_need_no_base_fallback(self):
  self.assertEqual(len(MISSING),9)
  self.assertTrue(all(not v for k,v in MISSING.items() if k!='authored-publication02'))
 def test_actual_historical_pin_refused_for_candidate_or_ordinary_lookup(self):
  pin=next(iter(MISSING['authored-publication02'].values()))
  for phase in ('candidate','artifact-only',None,'historical '):
   with self.subTest(phase=phase),self.assertRaises(ContractError):m.historical_audit_source(BASE,pin,phase)
 def test_registered_public_exact_bytes_accept(self):self.assertEqual(self.invoke(),self.source)
 def test_private_or_unregistered_bytes_do_not_authorize_fallback(self):
  for row in [dict(self.row,visibility='unavailable-private'),dict(self.row,sha256='0'*64)]:
   with self.subTest(row=row),self.assertRaises(ContractError):self.invoke(row)
 def test_registered_size_mismatch_and_bool_size_refuse(self):
  for size in (self.row['bytes']+1,True,-1):
   with self.subTest(size=size),self.assertRaises(ContractError):self.invoke(dict(self.row,bytes=size))
 def test_registered_digest_content_mismatch_refuses(self):
  self.source.write_bytes(b'altered historical source\n')
  with self.assertRaises(ContractError):self.invoke()
 def test_parent_and_absolute_escape_refuse(self):
  for path in ('../outside.py',str(self.source)):
   with self.subTest(path=path),self.assertRaises(ContractError):self.invoke(dict(self.row,path=path))
 def test_symlink_file_and_ancestor_refuse_even_inside_root(self):
  link=self.root/'alias.py';link.symlink_to(self.source)
  with self.assertRaises(ContractError):self.invoke(dict(self.row,path='alias.py'))
  alias=self.root/'alias';alias.symlink_to(self.source.parent,target_is_directory=True)
  with self.assertRaises(ContractError):self.invoke(dict(self.row,path='alias/a.py'))
 def test_symlink_ancestor_outside_refuses(self):
  with tempfile.TemporaryDirectory(dir='/data/fusion-operator-pilot-release/tmp') as td:
   outside=Path(td);(outside/'a.py').write_bytes(self.source.read_bytes());(self.root/'outside').symlink_to(outside,target_is_directory=True)
   with self.assertRaises(ContractError):self.invoke(dict(self.row,path='outside/a.py'))
 def test_nonregular_or_missing_source_refuses(self):
  self.source.unlink();self.source.mkdir()
  with self.assertRaises(ContractError):self.invoke()
  self.source.rmdir()
  with self.assertRaises(ContractError):self.invoke()
 def test_changed_or_symlinked_base_manifest_refuses(self):
  self.base.write_text(json.dumps(dict(artifacts=[self.row])));pin=m.sha(self.base)
  self.base.write_bytes(self.base.read_bytes()+b'\n')
  with patch.object(m,'BASE_EVIDENCE',pin),self.assertRaises(ContractError):m.historical_audit_source(self.base,self.pin,'historical')
  link=self.root/'linked.json';link.symlink_to(self.base)
  with patch.object(m,'BASE_EVIDENCE',m.sha(self.base)),self.assertRaises(ContractError):m.historical_audit_source(link,self.pin,'historical')
 def test_missing_base_or_invalid_pin_refuses(self):
  with self.assertRaises(ContractError):m.historical_audit_source(self.base,self.pin,'historical')
  with self.assertRaises(ContractError):self.invoke(pin='invalid')
 def test_exact_lookup_prefers_final_packet_and_candidate_never_uses_base(self):
  outer=next(x for x in ast.parse(Path(m.__file__).read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='assemble')
  node=next(x for x in outer.body if isinstance(x,ast.FunctionDef) and x.name=='by_digest')
  calls=[]
  def source(name):calls.append(name);return Path('/packet')/name
  env=dict(ev=m.ev,digest_index={self.pin:['candidate/a.py']},final_source=source,historical_audit_source=m.historical_audit_source,base=BASE)
  exec(compile(ast.Module(body=[node],type_ignores=[]),'<exact-nested-digest-lookup>','exec'),env)
  self.assertEqual(env['by_digest'](self.pin,phase='candidate'),Path('/packet/candidate/a.py'));self.assertEqual(calls,['candidate/a.py'])
  pin=next(iter(MISSING['authored-publication02'].values()))
  with self.assertRaises(ContractError):env['by_digest'](pin,phase='candidate')
  with self.assertRaises(ContractError):env['by_digest'](pin)
  self.assertEqual(m.sha(env['by_digest'](pin,phase='historical')),pin)
 def test_only_approved_delta_and_original_failed_artifacts_preserved(self):
  d=m.load(B/'final21-v07-approved-delta.json');old=Path(d['old']['path']).read_text()
  self.assertEqual(m.sha(d['old']['path']),d['old']['sha256']);self.assertEqual(m.sha(m.__file__),d['new']['sha256'])
  for a,z in d['replacements']:self.assertEqual(old.count(a),1);old=old.replace(a,z)
  self.assertEqual(old,Path(m.__file__).read_text())
  self.assertTrue((B/'final21-detached11').is_dir());self.assertIn('NOT_AVAILABLE',(B/'final21-assembly11.log').read_text())
 def test_network_and_process_audit_denial_precedes_import(self):
  for event in ('socket.connect','socket.bind','subprocess.Popen','os.system','os.posix_spawn'):
   with self.subTest(event=event),self.assertRaisesRegex(AssertionError,'NETWORK_OR_PROCESS_DENIED'):sys.audit(event,None)

if __name__=='__main__':unittest.main(verbosity=2)
