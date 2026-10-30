"""Build/export verified source overlays; never execute image entrypoints."""
import argparse,json,subprocess,sys,tarfile
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .reference_artifacts import sha
ROOT=Path(__file__).resolve().parents[2]
REPOS=dict(base='fusion-single-node',caller='fusion-memory-caller',embedding='fusion-memory-embedding',chain='fusion-reference-chain',hive='fusion-reference-hive',generative='fusion-reference-generative')
def profiles(manifest,destination):
 import yaml
 out=Path(destination);out.mkdir(parents=True,exist_ok=False)
 images={x['kind']:dict(repository=x['repository'],tag=x['local_tag'].rsplit(':',1)[1],digest=x['manifest_digest'],pullPolicy='Never') for x in manifest['images']}
 for profile,source in [('deterministic','values.yaml'),('memory','memory-values.yaml'),('workflow','workflow-values.yaml'),('cognitive','cognitive-values.yaml'),('chain','chain-values.yaml')]:
  value=yaml.safe_load((ROOT/'deploy/single-node'/source).read_text());value['image']=images['chain' if profile=='chain' else 'base'];value['networkPolicy']=dict(enabled=True)
  if profile!='deterministic':value['components']['omega-agent']['image']=images['hive' if profile=='chain' else 'caller']
  if profile in ('memory','workflow','cognitive'):
   value['components']['fusion-search']['image']=images['caller'];value['components']['fusion-embedding']['image']=images['embedding']
  (out/(profile+'.yaml')).write_text(yaml.safe_dump(value,sort_keys=False))
 (out/'deterministic.json').write_bytes(canonical(dict(tag=images['base']['tag'])))
 (out/'generative-image.json').write_bytes(canonical(images['generative']))
def build(destination,tag):
 require(tag.startswith('reference-') and '/' not in tag,'INVALID_ARGUMENT');root=Path(destination).resolve();root.mkdir(parents=True,exist_ok=False);packages={}
 for kind,repo in REPOS.items():
  context=root/('image-'+kind);script='package_workflow.py' if kind in ('base','caller','embedding') else 'package_reference.py'
  subprocess.run([sys.executable,str(ROOT/'deploy/single-node'/script),str(context),'--kind',kind],check=True)
  with (root/(kind+'-build.log')).open('w') as log:subprocess.run(['docker','build','--network=none','-t',repo+':'+tag,str(context)],stdout=log,stderr=subprocess.STDOUT,check=True)
  packages[kind]=json.loads((context/'package.json').read_text())
 require(all(x['source']==packages['base']['source'] for x in packages.values()),'CONFLICT')
 archive=root/'images.tar';subprocess.run(['docker','save','-o',str(archive),*[repo+':'+tag for repo in REPOS.values()]],check=True)
 images=[]
 with tarfile.open(archive) as tar:
  index=json.load(tar.extractfile('index.json'))
  for entry in index['manifests']:
   local=entry['annotations']['io.containerd.image.name'];repo=local.rsplit(':',1)[0];kind=next(k for k,r in REPOS.items() if repo.endswith('/'+r))
   raw=tar.extractfile('blobs/sha256/'+entry['digest'].split(':')[1]).read();require(digest(raw)==entry['digest'][7:],'CONFLICT');manifest=json.loads(raw)
   require(json.loads(subprocess.check_output(['docker','image','inspect',local]))[0]['Id']==manifest['config']['digest'],'CONFLICT')
   # Read the final source overlay from exported layers, not merely the context.
   seen={}
   for layer in reversed(manifest['layers']):
    if len(seen)==len(packages[kind]['source']):break
    stream=tar.extractfile('blobs/sha256/'+layer['digest'].split(':')[1])
    with tarfile.open(fileobj=stream,mode='r|*') as files:
     for member in files:
      name=member.name.lstrip('./').removeprefix('opt/fusion/')
      if name in packages[kind]['source'] and name not in seen and member.isfile():seen[name]=digest(files.extractfile(member).read())
   require(seen==packages[kind]['source'],'CONFLICT')
   images.append(dict(kind=kind,local_tag=local,repository=repo,manifest_digest=entry['digest'],configuration_digest=manifest['config']['digest'],source_package='image-'+kind+'/package.json'))
 result=dict(archive_sha256=sha(archive),archive_bytes=archive.stat().st_size,images=images,source_manifest_sha256=digest(canonical(packages['base']['source'])),source_export_verification='PASS',container_starts=0,generative_runtime_availability='NOT_CHECKED')
 (root/'images.json').write_bytes(canonical(result));profiles(result,root/'profiles');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination');p.add_argument('--tag',required=True);a=p.parse_args();print(json.dumps(build(a.destination,a.tag),indent=2))
