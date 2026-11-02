"""Offline distribution integrity. Never executes an image or runtime binary."""
import argparse,hashlib,json,tarfile,zipfile
from pathlib import Path
from fusion.contracts import canonical,digest,require

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def verify(path):
 path=Path(path).resolve();raw=path.read_bytes();manifest_checksum=digest(raw);manifest=json.loads(raw);require(raw==canonical(manifest),'CONFLICT');require(path.with_suffix('.sha256').read_text().strip()==manifest_checksum,'CONFLICT')
 require(manifest['schema'] in ('omega-single-node-distribution/1','omega-single-node-preview-distribution/1'),'UNSUPPORTED_PROFILE');checked=[]
 preview=manifest['schema']=='omega-single-node-preview-distribution/1';registered={}
 for item in manifest['files']:
  relative=Path(item['path']);require(not relative.is_absolute() and '..' not in relative.parts,'CONFLICT')
  require(item['path'] not in registered and (path.parent/relative).resolve().is_relative_to(path.parent),'CONFLICT')
  registered[item['path']]=item
  file=path.parent/relative;require(file.is_file() and file.stat().st_size==item['bytes'] and sha(file)==item['sha256'],'CONFLICT');checked.append(dict(path=item['path'],bytes=item['bytes'],sha256=item['sha256']))
 def member(name):
  require(type(name) is str and name in registered,'CONFLICT');return path.parent/name
 for kind,record in manifest['images'].items():
  package=json.loads(member(record['source_package']).read_text());require(record['source_manifest_sha256']==digest(canonical(package['source'])),'CONFLICT')
  require(record['manifest'].startswith('sha256:') and record['configuration'].startswith('sha256:'),'CONFLICT')
  require(manifest['tested_source']==package['source'],'CONFLICT')
 archive_path=member(manifest['image_archive'])
 imported=json.loads(member('images.json').read_bytes());require(imported['archive_sha256']==registered[manifest['image_archive']]['sha256'],'CONFLICT')
 kinds=set(manifest['images']);require(kinds=={r['kind'] for r in imported['images']} and len(kinds)==len(imported['images']),'CONFLICT')
 with tarfile.open(archive_path) as archive:
  for kind,record in manifest['images'].items():
   entry=next(x for x in imported['images'] if x['kind']==kind);require((record['manifest'],record['configuration'])==(entry['manifest_digest'],entry['configuration_digest']),'CONFLICT')
   if preview:require(record['repository']==entry['repository'],'CONFLICT')
   raw=archive.extractfile('blobs/sha256/'+record['manifest'][7:]).read();require(digest(raw)==record['manifest'][7:],'CONFLICT')
   descriptor=json.loads(raw);require(descriptor['config']['digest']==record['configuration'],'CONFLICT')
   config=archive.extractfile('blobs/sha256/'+record['configuration'][7:]).read();require(digest(config)==record['configuration'][7:],'CONFLICT')
 import yaml
 allowed={(r['repository'],r['manifest']) for r in manifest['images'].values()}
 if preview:
  from fusion.preview_deployment_contracts import COMPOSITION
  require(manifest['model_boundary']=='RECORDED_FIXTURE' and type(manifest['live_generation_authorization']) is int and manifest['live_generation_authorization']==0,'UNAUTHORIZED')
  kinds=set(manifest['images']);require({'base','caller','embedding'}<=kinds<= {'base','caller','embedding','chain'},'UNSUPPORTED_PROFILE')
  require(kinds=={r['kind'] for r in imported['images']} and len(kinds)==len(imported['images']),'CONFLICT')
  profiles=manifest['profile_files'];require(type(profiles) is list and 1<=len(profiles)<=4 and len(set(profiles))==len(profiles),'CONFLICT')
  member(manifest['chart'])
 else:profiles=[manifest['profile_directory']+'/'+p+'.yaml' for p in ('deterministic','memory','workflow','cognitive','chain')]
 for profile in profiles:
  values=yaml.safe_load(member(profile).read_text())
  selected=[values['image']]+[v['image'] for v in values.get('components',{}).values() if 'image' in v]
  require(all((v['repository'],v['digest']) in allowed for v in selected),'CONFLICT')
  if preview:
   p=values['preview'];require(p['profile']==COMPOSITION and p['enabled'] is True and p['model_boundary']=='RECORDED_FIXTURE','UNSUPPORTED_PROFILE')
   require(values.get('futureLive') is None and values.get('liveEnabled',False) is False
       and values.get('workflow',{}).get('liveEnabled',False) is False
       and values.get('workflow',{}).get('enabled',False) is False,'UNAUTHORIZED')
   chain=p.get('chain',{});require(not chain or (chain.get('nodeEnabled') is False and chain.get('isolationVerified') is False and chain.get('registration') is None),'UNAUTHORIZED')
 if preview:
  build=json.loads(member(manifest['sdk_build_manifest']).read_text());require(build['schema']=='fusion-preview-sdk-build/1' and build['live_generations']==0,'CONFLICT')
  inventory=json.loads(member(manifest['wheel_inventory']).read_text());wheelroot=Path(manifest['sdk_build_manifest']).parent
  indexed={p['artifact']:p for p in inventory['packages']};require(len(indexed)==len(inventory['packages']),'CONFLICT')
  for filename,entry in indexed.items():require(sha(member(str(wheelroot/filename)))==entry['sha256'],'CONFLICT')
  for kind in ('client','operator','provider'):
   record=build[kind];wheel=member(str(wheelroot/record['file']));require(sha(wheel)==record['sha256']==indexed[record['file']]['sha256'],'CONFLICT')
   with zipfile.ZipFile(wheel) as archive:
    names=[n for n in archive.namelist() if n.endswith('.dist-info/source-manifest.json')];require(len(names)==1,'CONFLICT')
    source=json.loads(archive.read(names[0]));require(source['schema']=='byte-exact-source-wheel/1' and source['sources']==record['sources'],'CONFLICT')
    for target,binding in source['sources'].items():
     raw=archive.read(target);require(len(raw)==binding['bytes'] and digest(raw)==binding['sha256'],'CONFLICT')
     if binding['source'].startswith(('fusion/','integration/')):require(manifest['tested_source'].get(binding['source'])==binding['sha256'],'CONFLICT')
 else:
  model=json.loads(member(manifest['profile_directory']+'/generative-image.json').read_text());require((model['repository'],model['digest']) in allowed,'CONFLICT')
 return dict(status='OFFLINE_VERIFIED',manifest_sha256=manifest_checksum,files=checked,images=manifest['images'],generative_runtime_availability='NOT_CHECKED',additional_live_generations=0)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output');a=p.parse_args();value=verify(a.manifest);raw=json.dumps(value,indent=2)+'\n'
 if a.output:Path(a.output).write_text(raw)
 else:print(raw)
if __name__=='__main__':main()
