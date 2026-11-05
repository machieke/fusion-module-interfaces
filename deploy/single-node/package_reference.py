"""Source overlay on fully inspected role assets; never starts an image."""
import argparse,json,hashlib,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PARENTS={
 'chain':('fusion-reference-chain:assets-v1','sha256:d5e6da25938c1407bbcc81dd2e297d102fcc4fbcad32c729e7621823f1c326fb'),
 'hive':('fusion-reference-hive:assets-v1','sha256:c6fda1f80d6c55163660ca4f6d47e9b4d46f577fd211480c98d1b7a6b38fdbb9'),
 'generative':('fusion-reference-generative:assets-v1','sha256:0d1ed4fd10229cdf55865acc4a67c24d4642da14accc7a6959254dc7312b551c')}
def main():
 p=argparse.ArgumentParser();p.add_argument('destination',type=Path);p.add_argument('--kind',choices=PARENTS,required=True);p.add_argument('--remediation-directory');p.add_argument('--source-parent-manifest');a=p.parse_args();base,pin=PARENTS[a.kind]
 if a.source_parent_manifest:
  assert not a.remediation_directory
  prior=json.loads(Path(a.source_parent_manifest).read_bytes());assert prior['source_export_verification']=='PASS'
  entry=next(x for x in prior['images'] if x['kind']==a.kind);base,pin=entry['local_tag'],entry['configuration_digest']
 assert subprocess.check_output(['docker','image','inspect',base,'--format','{{.Id}}'],text=True).strip()==pin
 a.destination.mkdir(parents=True,exist_ok=False);source=a.destination/'source';source.mkdir();files={}
 for folder in ('fusion','integration'):
  for file in sorted((ROOT/folder).rglob('*')):
   if file.is_file() and '__pycache__' not in file.parts and file.suffix in ('.py','.json','.metta'):
    rel=file.relative_to(ROOT);dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest);files[str(rel)]=hashlib.sha256(file.read_bytes()).hexdigest()
 from pilot_remediation_layer import prepare
 remediation=prepare(ROOT,a.destination,a.remediation_directory)
 (a.destination/'Dockerfile').write_text(f'FROM {base}\nUSER root\nCOPY source /opt/fusion\nCOPY package.json /opt/fusion-package.json\n{remediation}USER 1000:1000\n')
 (a.destination/'package.json').write_text(json.dumps(dict(parent=base,parent_config=pin,source=files,kind=a.kind),indent=2)+'\n')
if __name__=='__main__':main()
