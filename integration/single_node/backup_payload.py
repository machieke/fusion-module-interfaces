"""Quiesced owner export/import for the operator's fenced synthetic drill.

Never used by module consumers. One helper mounts exactly one owner's PVC after
all StatefulSets have zero pods. No Secret, policy, approval or key is archived.
"""
import argparse,fcntl,hashlib,json,os,sqlite3,sys,tarfile,stat
from contextlib import closing
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
 required={'composition','role','scope'};optional={'backend_layout','resident_worker','history_representation','storage_archive','provider_registry','execution_envelope','nal_execution_envelope','search_maintenance','chain_continuation'}
 require(type(seal) is dict and required<=set(seal)<=required|optional and seal['role']==role,'CONFLICT')
 require(type(seal['scope']) is str,'UNAUTHORIZED')
 preview=seal['composition'] in ('omega-single-node-developer-preview/1','omega-single-node-sustained-preview/1') and seal['scope'].startswith('synthetic-')
 if 'backend_layout' in seal:
  from fusion.adapters.detta_layout import LAYOUT
  require(preview and role=='fusion-storage' and seal['backend_layout']==LAYOUT,'UNSUPPORTED_PROFILE')
 if any(k in seal for k in ('resident_worker','history_representation','provider_registry')):
  require(seal['composition']=='omega-single-node-sustained-preview/1' and role in ('omega-agent','omega-agent-b'),'UNSUPPORTED_PROFILE')
 if 'resident_worker' in seal:
  from fusion.resident_workers import selection
  selection(seal['resident_worker'])
 if 'history_representation' in seal:require(seal['history_representation']=='immutable-administrative-captures/1','UNSUPPORTED_PROFILE')
 if 'provider_registry' in seal:require(seal['provider_registry'] in ('trusted-provider-lifecycle/1','trusted-provider-lifecycle/2'),'UNSUPPORTED_PROFILE')
 if 'chain_continuation' in seal:
  from fusion.chain_continuation import PROFILE
  require(preview and role in ('omega-agent','omega-agent-b') and seal['chain_continuation']==PROFILE,'UNSUPPORTED_PROFILE')
 if 'execution_envelope' in seal:
  require(preview and role in ('omega-agent','omega-agent-b','fusion-execution','fusion-messaging') and seal['execution_envelope']=='bounded-inspect-envelope/1','UNSUPPORTED_PROFILE')
 if 'nal_execution_envelope' in seal:
  require(preview and role in ('omega-agent','omega-agent-b','fusion-execution') and seal['nal_execution_envelope']=='bounded-native-nal-envelope/1','UNSUPPORTED_PROFILE')
 if 'search_maintenance' in seal:
  require(preview and role=='fusion-search' and seal['search_maintenance']=='bounded-derived-search-repair/1','UNSUPPORTED_PROFILE')
 if 'storage_archive' in seal:
  require(seal['composition']=='omega-single-node-sustained-preview/1' and role=='fusion-storage' and 'backend_layout' in seal,'UNSUPPORTED_PROFILE')
  from fusion.archive_contracts import policy
  policy(seal['storage_archive'])
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
   with closing(sqlite3.connect(p)) as db:
    result=db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone();require(result[0]==0,'NOT_AVAILABLE')
 # Finish and close diagnostic readers before freezing the archive file set.
 # SQLite's transaction context manager alone does not close a connection;
 # deferred finalization could otherwise remove a WAL after it was listed.
 from .diagnostics import inspect
 checkpoint=inspect(root)
 from .integrated_integrity import archive_dependencies,summary
 dependencies=archive_dependencies(root);require(dependencies['status']=='PASS','CONFLICT')
 files=[p for p in sorted(root.rglob('*')) if eligible(p,root)];require(sum(p.stat().st_size for p in files)<=MAX_TOTAL,'OVERLOADED')
 manifest=dict(schema='synthetic-owner-backup/1',role=role,seal=seal,files={str(p.relative_to(root)):dict(bytes=p.stat().st_size,sha256=digest(p.read_bytes())) for p in files},excluded_authority=True)
 manifest['owner_checkpoint']=checkpoint
 manifest['archive_dependencies']=dependencies['dependencies'];manifest['integrity']=summary(dependencies)
 # A bounded, private inventory of this exclusively mounted owner's files and
 # row commitments. It does not inspect foreign databases or invent external
 # reference closure. Existing operator RBAC and exclusive owner lock authorize
 # this export; the inventory is never an application consumer endpoint.
 from .pilot_dependencies import inventory
 manifest['dependency_inventory']=inventory(root,role,manifest['files'],lambda *_:None)
 if role=='fusion-execution':
  from fusion.preview_workspace import root_handover_observation
  transformed=root_handover_observation(root/'preview-facets'/'workspace',root/'preview-facets'/'workspace.sqlite')
  if transformed is not None:manifest['workspace_root_reattestation']=transformed
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
  members=archive.getmembers();require(len(members)<=150000 and sum(x.size for x in members)<=MAX_TOTAL,'OVERLOADED')
  require(len({x.name for x in members})==len(members) and all(x.isfile() for x in members),'INVALID_ARGUMENT')
  manifest=json.load(archive.extractfile('backup-manifest.json'));require(manifest['schema']=='synthetic-owner-backup/1' and manifest['role']==role and manifest['excluded_authority'] is True,'CONFLICT')
  synthetic_seal(manifest['seal'],role)
  maximum_files=150000 if manifest['seal']['composition']=='omega-single-node-sustained-preview/1' else 20000
  require(len(members)<=maximum_files,'OVERLOADED')
  require({m.name for m in members}=={'backup-manifest.json'}|{'state/'+f for f in manifest['files']},'CONFLICT')
  require('owner-seal.json' in manifest['files'],'CONFLICT')
  require(json.load(archive.extractfile('state/owner-seal.json'))==manifest['seal'],'CONFLICT')
  for name,desc in manifest['files'].items():
   p=Path(name);safe_name(p)
   content=archive.extractfile('state/'+name).read();require(len(content)==desc['bytes'] and digest(content)==desc['sha256'],'CONFLICT')
  if 'storage_archive' in manifest['seal']:
   require(type(manifest.get('archive_dependencies')) is dict and manifest.get('integrity',{}).get('status')=='PASS','CONFLICT')
  for name,entry in manifest.get('archive_dependencies',{}).items():
   require(name in manifest['files'] and entry['database'] in manifest['files'],'CONFLICT')
   require(manifest['files'][name]=={k:entry[k] for k in ('bytes','sha256')},'CONFLICT')
  # Marker is written FIRST. A partial extraction must also stay fenced.
  write(root/'restore-fence.json',dict(mode='READ_ONLY_RECONCILIATION',role=role,namespace=namespace,backup_manifest_sha256=digest(canonical(manifest)),original_scope=manifest['seal']['scope'],external_effect_authority=False))
  for name,desc in manifest['files'].items():
   if name=='restore-fence.json':continue
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(archive.extractfile('state/'+name).read());p.chmod(0o600)
  if 'archive_dependencies' in manifest:
   from .integrated_integrity import archive_dependencies
   checked=archive_dependencies(root)
   require(checked['status']=='PASS' and checked['dependencies']==manifest['archive_dependencies'],'CONFLICT')
 print(json.dumps(dict(role=role,status='RESTORED_FENCED',files=len(manifest['files']),bytes=sum(x['bytes'] for x in manifest['files'].values()))))
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=('export','restore'));p.add_argument('--role',required=True);p.add_argument('--namespace');a=p.parse_args()
 if a.action=='export':export(Path('/state'),a.role)
 else:restore(Path('/state'),a.role,a.namespace)
if __name__=='__main__':main()
