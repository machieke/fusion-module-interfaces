"""Assemble a local immutable reference bundle from tested, exported images.

No registry upload. Credentials, kubeconfig, journals and approvals are excluded
by a positive file list. Large approved model assets are linked locally and
listed by full hash; copying the distribution must dereference that link.
"""
import argparse,json,os,shutil,subprocess,tarfile
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .reference_artifacts import sha
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build',type=Path,required=True);p.add_argument('--offline-model',type=Path,required=True);p.add_argument('--profiles',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 build=a.build.resolve();images=json.loads((build/'images.json').read_text());files=[]
 def register(path,kind):files.append(dict(path=str(path.relative_to(out)),sha256=sha(path),bytes=path.stat().st_size,kind=kind))
 shutil.copyfile(build/'images.json',out/'images.json');register(out/'images.json','verified prebuilt image import manifest')
 # Same-filesystem hard links keep large immutable artifacts single-copy. They
 # are not mutable-state mounts and carry full content hashes in this manifest.
 for source,name,kind in [(build/'images.tar','images.tar','OCI image archive'),(a.offline_model/'model-assets.tar','model-assets.tar','offline model/projector assets')]:
  target=out/name
  try:os.link(source,target)
  except OSError:shutil.copyfile(source,target)
  register(target,kind)
 # Preserve pinned parent configurations as reproducible source-overlay inputs.
 parents={}
 for v in images['images']:
  package=json.loads((build/v['source_package']).read_text());parents[package['parent']]=package['parent_config']
 for tag,pin in parents.items():require(subprocess.check_output(['docker','image','inspect',tag,'--format','{{.Id}}'],text=True).strip()==pin,'CONFLICT')
 parent_archive=out/'parent-images.tar';subprocess.run(['docker','save','-o',str(parent_archive),*sorted(parents)],check=True);register(parent_archive,'pinned build parent image archive')
 image_map={};source_map=None
 for v in images['images']:
  target=out/(v['kind']+'-source.json');shutil.copyfile(build/v['source_package'],target);register(target,'source package')
  package=json.loads(target.read_text());source_map=source_map or package['source'];require(source_map==package['source'],'CONFLICT')
  image_map[v['kind']]=dict(repository=v['repository'],tag=v['local_tag'].rsplit(':',1)[1],manifest=v['manifest_digest'],configuration=v['configuration_digest'],source_package=target.name,source_manifest_sha256=digest(canonical(package['source'])))
 for name,hash_value in source_map.items():require(sha(ROOT/name)==hash_value,'CONFLICT')
 # Declared source only. No artifacts directory or unlisted checkout content.
 source=out/'source.tar.gz'
 with tarfile.open(source,'w:gz') as tar:
  for folder in ('fusion','integration','deploy','tests','docs/reference-distribution'):
   for file in sorted((ROOT/folder).rglob('*')):
    if file.is_file() and '__pycache__' not in file.parts and file.suffix in ('.py','.json','.yaml','.yml','.toml','.metta','.md','.pl','.lock','.txt'):
     require(file.suffix not in ('.key','.pem'),'UNAUTHORIZED');tar.add(file,arcname=str(file.relative_to(ROOT)))
  irc=ROOT/'artifacts/s06/ngircd/sbin/ngircd';require(sha(irc)=='b29b4c31e8f515062f2ed814b01c1774da2b6a1f3e099d6e316e8d3489ff3f74','CONFLICT');tar.add(irc,arcname=str(irc.relative_to(ROOT)))
  license=ROOT/'artifacts/s06/ngircd/share/doc/ngircd/COPYING';tar.add(license,arcname=str(license.relative_to(ROOT)))
  tar.add(ROOT/'scripts/chain_demo.py',arcname='scripts/chain_demo.py')
 register(source,'declared reproducible source')
 subprocess.run(['helm','package',str(ROOT/'deploy/helm/omega-fusion'),'--destination',str(out)],check=True)
 chart=next(out.glob('omega-fusion-*.tgz'));register(chart,'Helm chart')
 allowed={x+'.yaml' for x in ('deterministic','memory','workflow','cognitive','chain')}|{'deterministic.json','generative-image.json'}
 require({x.name for x in a.profiles.iterdir()}==allowed and all(x.is_file() and not x.is_symlink() for x in a.profiles.iterdir()),'CONFLICT')
 shutil.copytree(a.profiles,out/'profiles')
 for file in (out/'profiles').iterdir():register(file,'digest-bound profile')
 for directory in ('offline-model','chain-image','hive-image'):
  dest=out/'asset-evidence'/directory;dest.mkdir(parents=True)
  # Explicit top-level recipes/manifests/licenses only, no raw state/keys.
  parent=a.offline_model if directory=='offline-model' else ROOT/'artifacts/reference-distribution'/directory
  for file in parent.iterdir():
   if file.is_file() and file.suffix in ('.json','.py','.txt'):
    require('secret' not in file.name and 'approval' not in file.name,'UNAUTHORIZED');shutil.copyfile(file,dest/file.name);register(dest/file.name,'offline asset recipe/inventory')
 # Preserve the offline runtime lock's original relative recipe location.
 offline=out/'asset-evidence/offline-model';target=offline/'context/generative/runtime.json';target.parent.mkdir(parents=True);shutil.copyfile(a.offline_model/'context/generative/runtime.json',target);register(target,'offline runtime lock')
 os.link(out/'model-assets.tar',offline/'model-assets.tar');register(offline/'model-assets.tar','same verified model archive for offline preparation')
 manifest=dict(parent_images=parents,parent_archive=parent_archive.name,schema='omega-single-node-distribution/1',baseline=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),tested_source=source_map,images=image_map,files=files,chart=chart.name,source_archive=source.name,profile_directory='profiles',image_archive='images.tar',model_assets_archive='model-assets.tar',live_generation_authorization=0,generative_runtime_availability='NOT_CHECKED',distribution='local archive set; no registry publication',rebuild_prerequisites='Load parent-images.tar before the source-overlay build; exact parent configs are checked. Original dependency/build recipes and asset inventories retain their historical paths and prerequisites. Prebuilt image installation requires no developer tree.',limitations=['single-node local-path persistence','warm container/asset cache in the demonstrated rehearsal','restricted third-party assets remain subject to their original licenses'])
 file=out/'distribution.json';file.write_bytes(canonical(manifest));file.with_suffix('.sha256').write_text(digest(file.read_bytes())+'\n');print(json.dumps(dict(manifest=str(file),sha256=digest(file.read_bytes())),indent=2))
if __name__=='__main__':main()
