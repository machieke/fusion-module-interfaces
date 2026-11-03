"""Existing-host import commands are rendered only; no second cluster claim."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

class ExistingK3sImport(unittest.TestCase):
 def test_import_uses_selected_existing_k3s_without_install_or_docker(self):
  path=Path(__file__).resolve().parents[1]/'deploy/single-node/import_workflow_images.py'
  spec=importlib.util.spec_from_file_location('image_import',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);archive=root/'images.tar';archive.write_bytes(b'EXPLICIT_ARCHIVE_FIXTURE')
   m=dict(archive_sha256=module.sha(archive),images=[dict(local_tag='example:fixed',repository='example',manifest_digest='sha256:manifest',configuration_digest='sha256:config')]);manifest=root/'images.json';manifest.write_text(json.dumps(m))
   def output(cmd,**kwargs):
    return 'REF TYPE DIGEST\nexample:fixed type sha256:manifest\n' if cmd[-2:]==['images','ls'] else json.dumps(dict(config=dict(digest='sha256:config'))).encode()
   with patch.object(module.subprocess,'check_output',side_effect=output),patch.object(module.subprocess,'run') as run,patch('sys.argv',['import','--k3s-binary','/usr/local/bin/k3s','--manifest',str(manifest),'--archive',str(archive)]):module.main()
   self.assertEqual(run.call_args_list[0].args[0],['/usr/local/bin/k3s','ctr','--namespace','k8s.io','images','import','-'])
   for call in run.call_args_list:self.assertNotIn('docker',call.args[0]);self.assertNotIn('install',call.args[0])
