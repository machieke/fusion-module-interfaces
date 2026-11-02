"""Quiesced owner export/import for the operator's fenced synthetic drill.

Never used by module consumers. One helper mounts exactly one owner's PVC after
all StatefulSets have zero pods. No Secret, policy, approval or key is archived.
"""
import argparse,fcntl,hashlib,json,os,sqlite3,sys,tarfile,stat
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .configure import write

MAX_TOTAL=512*1024*1024
EXCLUDED={'owner.lock','process.json','native-exit.json','restore-process.json','peer-input','ngircd.pid'}
def safe_name(rel):
 parts=[x.lower() for x in rel.parts]
 require(not rel.is_absolute() and '..' not in rel.parts,'INVALID_ARGUMENT')
 require(not any(x in ('secrets','approval','approvals','.kube','credentials') for x in parts),'UNAUTHORIZED')
 name=parts[-1]
 require(rel.suffix.lower() not in ('.key','.pem','.hex','.crt','.p12','.pfx'),'UNAUTHORIZED')
 require(not any(x in name for x in ('credential','secret','token','approval')) and name not in ('authority.json','policy.json','owner.json','application.json','component.json'),'UNAUTHORIZED')

def synthetic_seal(seal,role):
 require(type(seal) is dict and set(seal) in ({'composition','role','scope'},{'composition','role','scope','backend_layout'}) and seal['role']==role,'CONFLICT')
 require(type(seal['scope']) is str,'UNAUTHORIZED')
 preview=seal['composition']=='omega-single-node-developer-preview/1' and seal['scope'].startswith('synthetic-')
 if 'backend_layout' in seal:
  from fusion.adapters.detta_layout import LAYOUT
  require(preview and role=='fusion-storage' and seal['backend_layout']==LAYOUT,'UNSUPPORTED_PROFILE')
 require(preview or seal['scope'].startswith('generated-') or seal['scope']=='shared-test','UNAUTHORIZED')

def eligible(p,root):
 rel=p.relative_to(root)
 require(not p.is_symlink(),'UNSUPPORTED_PROFILE')
 if not p.is_file():return False
 safe_name(rel)
 return p.name not in EXCLUDED and not p.name.endswith(('.log','.jsonl','-shm','.lock')) and 'hive' not in rel.parts

def export(root,role):
 seal=json.loads((root/'owner-seal.json').read_text());synthetic_seal(seal,role)
 with open(root/'owner.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  _export_locked(root,role,seal)

def _export_locked(root,role,seal):
 # No active owner remains. SQLite's own checkpoint operation includes WAL
 # contents; any busy checkpoint is a failure, never a silent partial archive.
 for p in root.rglob('*'):
  if p.is_file() and not p.is_symlink() and p.suffix in ('.sqlite','.sqlite3','.db'):
   with sqlite3.connect(p) as db:
    result=db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone();require(result[0]==0,'NOT_AVAILABLE')
 files=[p for p in sorted(root.rglob('*')) if eligible(p,root)];require(sum(p.stat().st_size for p in files)<=MAX_TOTAL,'OVERLOADED')
 manifest=dict(schema='synthetic-owner-backup/1',role=role,seal=seal,files={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in files},excluded_authority=True)
 from .diagnostics import inspect
 manifest['owner_checkpoint']=inspect(root)
 manifest['retained_views']={str(p.relative_to(root)):json.loads(p.read_text()) for p in root.rglob('*.json') if p.name in ('setup-view.json','initial-view.json','published.json','chain-identity.json')}
 import io
 with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
  raw=canonical(manifest);item=tarfile.TarInfo('backup-manifest.json');item.size=len(raw);item.mode=0o600;archive.addfile(item,io.BytesIO(raw))
  for p in files:archive.add(p,arcname='state/'+str(p.relative_to(root)),recursive=False)

def restore(root,role,namespace):
 require(namespace.startswith('omega-ref-') and 'omega-demo' not in namespace,'UNAUTHORIZED');require(not (root/'owner-seal.json').exists(),'CONFLICT')
 require({p.name for p in root.iterdir()}<= {'lost+found'},'CONFLICT')
 # Validating an archive completely before extraction bounds paths and content.
 import io
 raw=sys.stdin.buffer.read(MAX_TOTAL+1);require(len(raw)<=MAX_TOTAL,'OVERLOADED')
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
  members=archive.getmembers();require(len(members)<=20000 and sum(x.size for x in members)<=MAX_TOTAL,'OVERLOADED')
  require(len({x.name for x in members})==len(members) and all(x.isfile() for x in members),'INVALID_ARGUMENT')
  manifest=json.load(archive.extractfile('backup-manifest.json'));require(manifest['schema']=='synthetic-owner-backup/1' and manifest['role']==role and manifest['excluded_authority'] is True,'CONFLICT')
  synthetic_seal(manifest['seal'],role)
  require({m.name for m in members}=={'backup-manifest.json'}|{'state/'+f for f in manifest['files']},'CONFLICT')
  require('owner-seal.json' in manifest['files'],'CONFLICT')
  require(json.load(archive.extractfile('state/owner-seal.json'))==manifest['seal'],'CONFLICT')
  for name,desc in manifest['files'].items():
   p=Path(name);safe_name(p)
   content=archive.extractfile('state/'+name).read();require(len(content)==desc['bytes'] and digest(content)==desc['sha256'],'CONFLICT')
  # Marker is written FIRST. A partial extraction must also stay fenced.
  write(root/'restore-fence.json',dict(mode='READ_ONLY_RECONCILIATION',role=role,namespace=namespace,backup_manifest_sha256=digest(canonical(manifest)),original_scope=manifest['seal']['scope'],external_effect_authority=False))
  for name,desc in manifest['files'].items():
   if name=='restore-fence.json':continue
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.extractfile('state/'+name).read());p.chmod(0o600)
 print(json.dumps(dict(role=role,status='RESTORED_FENCED',files=len(manifest['files']),bytes=sum(x['bytes'] for x in manifest['files'].values()))))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=('export','restore'));p.add_argument('--role',required=True);p.add_argument('--namespace');a=p.parse_args()
 if a.action=='export':export(Path('/state'),a.role)
 else:restore(Path('/state'),a.role,a.namespace)
if __name__=='__main__':main()
