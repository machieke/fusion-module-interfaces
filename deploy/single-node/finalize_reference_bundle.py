"""Attach reviewed repository documentation/evidence to a verified local bundle.

Runtime source bytes must equal the already exported/tested image source map.
The digest-bearing artifacts.json publication sidecar is deliberately excluded
from its own hashed source archive. No credentials, journals or artifact trees
are selected. This command never builds or starts an image/runtime.
"""
import argparse,hashlib,json,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();root=a.bundle.resolve();manifest=root/'distribution.json';value=json.loads(manifest.read_bytes())
 for name,expected in value['tested_source'].items():
  if sha(ROOT/name)!=expected:raise ValueError('Tested runtime source changed: '+name)
 source=root/value['source_archive'];before=sha(source);selected=[]
 extensions={'.py','.json','.yaml','.yml','.toml','.metta','.md','.pl','.lock','.txt'}
 for folder in ('fusion','integration','deploy','tests','docs/reference-distribution','evidence/reference-distribution'):
  for file in sorted((ROOT/folder).rglob('*')):
   if file.is_file() and not file.is_symlink() and '__pycache__' not in file.parts and file.suffix in extensions:
    if str(file.relative_to(ROOT))=='evidence/reference-distribution/artifacts.json':continue
    if folder=='evidence/reference-distribution' and any(x in file.name.lower() for x in ('credential','private','kubeconfig','secret')):raise ValueError('Evidence filename requires review: '+str(file))
    selected.append(file)
 selected += [ROOT/'.github/workflows/reference.yml',ROOT/'codex_omega_asi_end_to_end_delivery_programme.md',ROOT/'scripts/chain_demo.py',ROOT/'artifacts/s06/ngircd/sbin/ngircd',ROOT/'artifacts/s06/ngircd/share/doc/ngircd/COPYING']
 if sha(selected[-2])!='b29b4c31e8f515062f2ed814b01c1774da2b6a1f3e099d6e316e8d3489ff3f74':raise ValueError('Pinned IRC executable changed')
 temporary=source.with_suffix('.tmp')
 with tarfile.open(temporary,'w:gz') as tar:
  for file in sorted(set(selected)):tar.add(file,arcname=str(file.relative_to(ROOT)))
 temporary.replace(source)
 for item in value['files']:
  if item['path']==value['source_archive']:item.update(sha256=sha(source),bytes=source.stat().st_size)
 value['evidence_publication']=dict(previous_source_archive_sha256=before,runtime_source_unchanged=True,scope='reviewed docs, deployment metadata, tests, CI and sanitized programme evidence; external artifacts.json excluded to avoid circular digest')
 manifest.write_bytes(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode());manifest.with_suffix('.sha256').write_text(sha(manifest)+'\n');print(json.dumps(dict(manifest=str(manifest),sha256=sha(manifest),source_archive_sha256=sha(source)),indent=2))
if __name__=='__main__':main()
