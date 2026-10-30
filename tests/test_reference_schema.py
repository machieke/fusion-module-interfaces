"""Network-free schema checks for every supported configuration family."""
import copy,json,unittest
from pathlib import Path
import jsonschema,yaml
class Schema(unittest.TestCase):
 def test_supported_profiles_and_closed_live_selection(self):
  root=Path(__file__).resolve().parents[1];schema=json.loads((root/'deploy/helm/omega-fusion/values.schema.json').read_text());default=yaml.safe_load((root/'deploy/helm/omega-fusion/values.yaml').read_text())
  def merge(a,b):
   a=copy.deepcopy(a)
   for k,v in b.items():a[k]=merge(a.get(k,{}),v) if isinstance(v,dict) else v
   return a
  for name in ('values','memory-values','workflow-values','cognitive-values','chain-values'):
   v=merge(default,yaml.safe_load((root/('deploy/single-node/'+name+'.yaml')).read_text()));jsonschema.Draft7Validator(schema).validate(v)
  v=merge(default,yaml.safe_load((root/'deploy/single-node/workflow-values.yaml').read_text()));v['workflow'].update(mode='live',responses=[])
  with self.assertRaises(jsonschema.ValidationError):jsonschema.Draft7Validator(schema).validate(v)
  v['futureLive']['enabled']=True;jsonschema.Draft7Validator(schema).validate(v)
  v['futureLive']['activated']=True
  with self.assertRaises(jsonschema.ValidationError):jsonschema.Draft7Validator(schema).validate(v)
  v['workflow'].update(liveEnabled=True,phase='measured');jsonschema.Draft7Validator(schema).validate(v)
  v['workflow']['responses']=['injected reply']
  with self.assertRaises(jsonschema.ValidationError):jsonschema.Draft7Validator(schema).validate(v)

class ArtifactIdentity(unittest.TestCase):
 def test_distribution_digest_is_not_the_last_oci_descriptor(self):
  import io,json,tarfile,tempfile,hashlib
  from pathlib import Path
  from fusion.contracts import canonical,ContractError
  from integration.single_node.reference_artifacts import verify
  sha=lambda b:hashlib.sha256(b).hexdigest()
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);(root/'profiles').mkdir();config=canonical(dict(architecture='amd64'));oci=canonical(dict(config=dict(digest='sha256:'+sha(config))))
   with tarfile.open(root/'images.tar','w') as tar:
    for raw in (config,oci):
     info=tarfile.TarInfo('blobs/sha256/'+sha(raw));info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
   image=dict(repository='fixture-only',digest='sha256:'+sha(oci));package=dict(source={});(root/'source.json').write_bytes(canonical(package))
   for name in ('deterministic','memory','workflow','cognitive','chain'):(root/'profiles'/(name+'.yaml')).write_text(json.dumps(dict(image=image)))
   (root/'profiles/generative-image.json').write_text(json.dumps(image))
   imported=dict(archive_sha256=sha((root/'images.tar').read_bytes()),images=[dict(kind='fixture',manifest_digest='sha256:'+sha(oci),configuration_digest='sha256:'+sha(config))]);(root/'images.json').write_bytes(canonical(imported))
   files=[dict(path=str(f.relative_to(root)),bytes=f.stat().st_size,sha256=sha(f.read_bytes())) for f in root.rglob('*') if f.is_file()]
   manifest=dict(schema='omega-single-node-distribution/1',files=files,images=dict(fixture=dict(source_package='source.json',source_manifest_sha256=sha(canonical({})),manifest='sha256:'+sha(oci),configuration='sha256:'+sha(config),repository='fixture-only')),tested_source={},image_archive='images.tar',profile_directory='profiles')
   path=root/'distribution.json';path.write_bytes(canonical(manifest));checksum=sha(path.read_bytes());path.with_suffix('.sha256').write_text(checksum+'\n')
   self.assertNotEqual(checksum,sha(oci));self.assertEqual(verify(path)['manifest_sha256'],checksum)
   (root/'profiles/memory.yaml').write_text('{}')
   with self.assertRaises(ContractError):verify(path)

if __name__=='__main__':unittest.main()
