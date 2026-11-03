"""Real bounded archive restore; generated empty file records, no owner runtime."""
import io,json,tarfile,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion.contracts import canonical,digest,ContractError
from integration.single_node.backup_payload import restore

class BackupCapacity(unittest.TestCase):
 def archive(self,composition):
  seal=dict(role='fusion-storage',scope='synthetic-capacity-restore',composition=composition)
  files={'owner-seal.json':canonical(seal)}
  files.update({'records/'+str(i):b'' for i in range(20000)})
  manifest=dict(schema='synthetic-owner-backup/1',role='fusion-storage',seal=seal,excluded_authority=True,
    files={name:dict(bytes=len(raw),sha256=digest(raw)) for name,raw in files.items()})
  stream=io.BytesIO()
  with tarfile.open(fileobj=stream,mode='w:gz') as archive:
   for name,raw in [('backup-manifest.json',canonical(manifest))]+[('state/'+name,raw) for name,raw in files.items()]:
    item=tarfile.TarInfo(name);item.size=len(raw);archive.addfile(item,io.BytesIO(raw))
  return stream.getvalue()
 def test_new_profile_restores_more_files_with_fence_old_profile_stays_bounded(self):
  for profile in ('omega-single-node-developer-preview/1','omega-single-node-sustained-preview/1'):
   with self.subTest(profile=profile),tempfile.TemporaryDirectory() as temporary:
    root=Path(temporary)
    with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(self.archive(profile)))),patch('sys.stdout',io.StringIO()):
     if profile.endswith('sustained-preview/1'):
      restore(root,'fusion-storage','omega-ref-synthetic-clone')
      self.assertEqual(len(list((root/'records').iterdir())),20000)
      self.assertFalse(json.loads((root/'restore-fence.json').read_bytes())['external_effect_authority'])
     else:
      with self.assertRaisesRegex(ContractError,'OVERLOADED'):restore(root,'fusion-storage','omega-ref-synthetic-clone')
      self.assertEqual(list(root.iterdir()),[])

class CheckpointSnapshot(unittest.TestCase):
 def test_interrupted_wal_writes_export_after_all_readers_close(self):
  import subprocess,sys,sqlite3,gc
  from integration.single_node.backup_payload import export
  from integration.single_node import diagnostics
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)/'owner';root.mkdir();clone=Path(td)/'clone';clone.mkdir()
   seal=dict(role='omega-agent',scope='synthetic-wal-snapshot',composition='omega-single-node-sustained-preview/1');(root/'owner-seal.json').write_bytes(canonical(seal))
   code="""import sqlite3,sys,os
from pathlib import Path
connections=[]
for name in ('caller.sqlite','cognitive/relay-A.sqlite','cognitive/relay-B.sqlite'):
 p=Path(sys.argv[1])/name;p.parent.mkdir(exist_ok=True);c=sqlite3.connect(p);c.execute('PRAGMA journal_mode=WAL');c.execute('PRAGMA wal_autocheckpoint=0');c.execute('CREATE TABLE retained(id INTEGER, reserved INTEGER, result TEXT)');c.execute('INSERT INTO retained VALUES(1,3,?)',('captured-original',));c.commit();connections.append(c)
os._exit(0)
"""
   subprocess.run([sys.executable,'-c',code,str(root)],check=True)
   self.assertEqual(len(list(root.rglob('*-wal'))),3)
   original=diagnostics.inspect
   def observe(path):gc.collect();return original(path)
   output=io.BytesIO()
   with patch.object(diagnostics,'inspect',side_effect=observe),patch('sys.stdout',SimpleNamespace(buffer=output)):export(root,'omega-agent')
   with tarfile.open(fileobj=io.BytesIO(output.getvalue()),mode='r:gz') as archive:
    manifest=json.load(archive.extractfile('backup-manifest.json'))
    for name,desc in manifest['files'].items():self.assertEqual(digest(archive.extractfile('state/'+name).read()),desc['sha256'])
   with patch('sys.stdin',SimpleNamespace(buffer=io.BytesIO(output.getvalue()))),patch('sys.stdout',io.StringIO()):restore(clone,'omega-agent','omega-ref-wal-observer')
   for p in clone.rglob('*.sqlite'):
    with sqlite3.connect(p) as db:self.assertEqual(db.execute('SELECT * FROM retained').fetchall(),[(1,3,'captured-original')])
