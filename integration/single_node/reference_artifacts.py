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
 base_path=None
 if imported.get('archive_format')=='verified-oci-layer-set/1':
  base_path=member(manifest.get('image_base_archive'))
  base_binding=imported['base_archive']
  require(registered[manifest['image_base_archive']]['sha256']==base_binding['archive_sha256']
      and base_path.stat().st_size==base_binding['archive_bytes'],'CONFLICT')
 else:require(not manifest.get('image_base_archive') and not imported.get('base_archive'),'CONFLICT')
 from .image_layers import Layers
 with Layers(archive_path,base_path) as archive:
  for kind,record in manifest['images'].items():
   entry=next(x for x in imported['images'] if x['kind']==kind);require((record['manifest'],record['configuration'])==(entry['manifest_digest'],entry['configuration_digest']),'CONFLICT')
   if preview:require(record['repository']==entry['repository'],'CONFLICT')
   raw=archive.extractfile('blobs/sha256/'+record['manifest'][7:]).read();require(digest(raw)==record['manifest'][7:],'CONFLICT')
   descriptor=json.loads(raw);require(descriptor['config']['digest']==record['configuration'],'CONFLICT')
   config=archive.extractfile('blobs/sha256/'+record['configuration'][7:]).read();require(digest(config)==record['configuration'][7:],'CONFLICT')
   # Full archives are already bound above. Check every referenced layer's
   # presence and size too: a pinned but incomplete archive is not installable.
   for layer in descriptor.get('layers',[]):
    require(layer['digest'].startswith('sha256:'),'CONFLICT')
    stream=archive.extractfile('blobs/sha256/'+layer['digest'][7:])
    require(stream is not None and stream.seek(0,2)==layer['size'],'CONFLICT');stream.close()
 import yaml
 # Independently implemented reference providers carry their own complete image,
 # binary and starter-kit source binding. Never equate these Go sources with the
 # Python tested_source map or silently merge them into its historical archive.
 references=manifest.get('reference_providers',{});require(type(references) is dict and set(references)<={'inspect-go'},'UNSUPPORTED_PROFILE')
 require(not references or preview,'UNSUPPORTED_PROFILE');reference_images={}
 for kind,relative in references.items():
  from .pilot_provider_image import verify as verify_reference
  def registered_reference(file):
   require(file.resolve().is_relative_to(path.parent),'UNAUTHORIZED')
   member(str(file.resolve().relative_to(path.parent)))
  value=verify_reference(member(relative),registered_reference);require(value['kind']==kind,'CONFLICT')
  reference_images[kind]=dict(value,source_package=str(Path(relative).parent/value['source_package']),reference_manifest=relative)
 all_images={**manifest['images'],**reference_images}
 allowed={(r['repository'],r['manifest']) for r in all_images.values()}
 if preview:
  from fusion.preview_deployment_contracts import COMPOSITION,SUSTAINED_COMPOSITION
  require(manifest['model_boundary']=='RECORDED_FIXTURE' and type(manifest['live_generation_authorization']) is int and manifest['live_generation_authorization']==0,'UNAUTHORIZED')
  kinds=set(manifest['images']);require({'base','caller','embedding'}<=kinds<= {'base','caller','embedding','chain'},'UNSUPPORTED_PROFILE')
  require(kinds=={r['kind'] for r in imported['images']} and len(kinds)==len(imported['images']),'CONFLICT')
  pilot=manifest.get('operator_profile')
  require(pilot in (None,'operator-pilot-package/1'),'UNSUPPORTED_PROFILE')
  profiles=manifest['profile_files'];require(type(profiles) is list and 1<=len(profiles)<=(6 if pilot else 5) and len(set(profiles))==len(profiles),'CONFLICT')
  member(manifest['chart'])
 else:profiles=[manifest['profile_directory']+'/'+p+'.yaml' for p in ('deterministic','memory','workflow','cognitive','chain')]
 for profile in profiles:
  values=yaml.safe_load(member(profile).read_text())
  selected=[values['image']]+[v['image'] for v in values.get('components',{}).values() if 'image' in v]
  if values.get('pilotWorkbench',{}).get('image'):selected.append(values['pilotWorkbench']['image'])
  require(all((v['repository'],v['digest']) in allowed for v in selected),'CONFLICT')
  if preview:
   p=values['preview'];require(p['profile'] in (COMPOSITION,SUSTAINED_COMPOSITION) and p['enabled'] is True and p['model_boundary']=='RECORDED_FIXTURE','UNSUPPORTED_PROFILE')
   if p['profile']==SUSTAINED_COMPOSITION:
    require(type(p.get('sustained')) is dict and not p['sustained'].get('model_binding'),'UNAUTHORIZED')
    for role in ('omega-agent','omega-agent-b'):
     component=values['components'][role];require(component['config']['nativeEnabled'] is False and component['config']['workerEnabled'] is False,'UNAUTHORIZED')
   require(values.get('futureLive') is None and values.get('liveEnabled',False) is False
       and values.get('workflow',{}).get('liveEnabled',False) is False
       and values.get('workflow',{}).get('enabled',False) is False,'UNAUTHORIZED')
   chain=p.get('chain',{});require(not chain or (chain.get('nodeEnabled') is False and chain.get('isolationVerified') is False and chain.get('registration') is None),'UNAUTHORIZED')
 if preview:
  build=json.loads(member(manifest['sdk_build_manifest']).read_text());require(build['schema']=='fusion-preview-sdk-build/1' and build['live_generations']==0,'CONFLICT')
  require(build.get('operator_profile')==manifest.get('operator_profile'),'CONFLICT')
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
 if manifest.get('second_language_client'):
  package=json.loads(member(manifest['second_language_client']).read_bytes())
  require(package['profile']=='fusion-go-artifacts/1' and package['status']=='PASS' and package['additional_live_generations']==0,'CONFLICT')
  require(sha(member('go/omega-client'))==package['binary_sha256'] and sha(member('go/fusion-go-client-source.tar.gz'))==package['archive_sha256'],'CONFLICT')
  require(all(sha(member('sdk/go/'+name))==pin for name,pin in package['source'].items()),'CONFLICT')
 return dict(status='OFFLINE_VERIFIED',manifest_sha256=manifest_checksum,files=checked,images=all_images,generative_runtime_availability='NOT_CHECKED',additional_live_generations=0)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output');a=p.parse_args();value=verify(a.manifest);raw=json.dumps(value,indent=2)+'\n'
 if a.output:Path(a.output).write_text(raw)
 else:print(raw)
if __name__=='__main__':main()
