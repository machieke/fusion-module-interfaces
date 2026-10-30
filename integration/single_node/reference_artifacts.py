"""Offline distribution integrity. Never executes an image or runtime binary."""
import argparse,hashlib,json,tarfile
from pathlib import Path
from fusion.contracts import canonical,digest,require

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def verify(path):
 path=Path(path).resolve();raw=path.read_bytes();manifest_checksum=digest(raw);manifest=json.loads(raw);require(raw==canonical(manifest),'CONFLICT');require(path.with_suffix('.sha256').read_text().strip()==manifest_checksum,'CONFLICT')
 require(manifest['schema']=='omega-single-node-distribution/1','UNSUPPORTED_PROFILE');checked=[]
 for item in manifest['files']:
  relative=Path(item['path']);require(not relative.is_absolute() and '..' not in relative.parts,'CONFLICT')
  file=path.parent/relative;require(file.is_file() and file.stat().st_size==item['bytes'] and sha(file)==item['sha256'],'CONFLICT');checked.append(dict(path=item['path'],bytes=item['bytes'],sha256=item['sha256']))
 for kind,record in manifest['images'].items():
  package=json.loads((path.parent/record['source_package']).read_text());require(record['source_manifest_sha256']==digest(canonical(package['source'])),'CONFLICT')
  require(record['manifest'].startswith('sha256:') and record['configuration'].startswith('sha256:'),'CONFLICT')
  require(manifest['tested_source']==package['source'],'CONFLICT')
 imported=json.loads((path.parent/'images.json').read_bytes());require(imported['archive_sha256']==next(x['sha256'] for x in manifest['files'] if x['path']==manifest['image_archive']),'CONFLICT')
 with tarfile.open(path.parent/manifest['image_archive']) as archive:
  for kind,record in manifest['images'].items():
   entry=next(x for x in imported['images'] if x['kind']==kind);require((record['manifest'],record['configuration'])==(entry['manifest_digest'],entry['configuration_digest']),'CONFLICT')
   raw=archive.extractfile('blobs/sha256/'+record['manifest'][7:]).read();require(digest(raw)==record['manifest'][7:],'CONFLICT')
   descriptor=json.loads(raw);require(descriptor['config']['digest']==record['configuration'],'CONFLICT')
   config=archive.extractfile('blobs/sha256/'+record['configuration'][7:]).read();require(digest(config)==record['configuration'][7:],'CONFLICT')
 import yaml
 allowed={(r['repository'],r['manifest']) for r in manifest['images'].values()}
 for profile in ('deterministic','memory','workflow','cognitive','chain'):
  values=yaml.safe_load((path.parent/manifest['profile_directory']/(profile+'.yaml')).read_text())
  selected=[values['image']]+[v['image'] for v in values.get('components',{}).values() if 'image' in v]
  require(all((v['repository'],v['digest']) in allowed for v in selected),'CONFLICT')
 model=json.loads((path.parent/manifest['profile_directory']/'generative-image.json').read_text());require((model['repository'],model['digest']) in allowed,'CONFLICT')
 return dict(status='OFFLINE_VERIFIED',manifest_sha256=manifest_checksum,files=checked,images=manifest['images'],generative_runtime_availability='NOT_CHECKED',additional_live_generations=0)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('manifest');p.add_argument('--output');a=p.parse_args();value=verify(a.manifest);raw=json.dumps(value,indent=2)+'\n'
 if a.output:Path(a.output).write_text(raw)
 else:print(raw)
if __name__=='__main__':main()
