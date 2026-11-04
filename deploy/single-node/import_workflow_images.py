"""Verify/import the recorded image archive and register its digest references."""
import argparse,hashlib,json,subprocess,tarfile
from pathlib import Path

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def combined_stream(base,overlay,target):
 # Keep this import recipe stdlib-only, including direct execution outside an
 # installed SDK. Both complete file hashes were checked before this stream.
 with tarfile.open(base) as prior,tarfile.open(overlay) as current,tarfile.open(fileobj=target,mode='w|') as output:
  names={m.name for m in current.getmembers()}
  for member in prior:
   if member.isfile() and member.name.startswith('blobs/sha256/') and member.name not in names:
    output.addfile(member,prior.extractfile(member))
  for member in current:
   if member.isfile():output.addfile(member,current.extractfile(member))

def main():
 p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--container');mode.add_argument('--k3s-binary',help='Existing local k3s executable; does not install or alter a cluster');p.add_argument('--manifest',required=True);p.add_argument('--archive');p.add_argument('--base-archive');p.add_argument('--register-only',action='store_true');a=p.parse_args()
 manifest=json.loads(Path(a.manifest).read_bytes())
 base=['docker','exec',a.container,'ctr','--address','/run/k3s/containerd/containerd.sock','--namespace','k8s.io'] if a.container else [a.k3s_binary,'ctr','--namespace','k8s.io']
 if not a.register_only:
  assert a.archive and sha(a.archive)==manifest['archive_sha256'],'ARCHIVE_HASH_MISMATCH'
  command=(['docker','exec','-i',a.container,*base[3:]] if a.container else base)+['images','import','-']
  if manifest.get('archive_format')=='verified-oci-layer-set/1':
   binding=manifest['base_archive']
   assert a.base_archive and Path(a.base_archive).stat().st_size==binding['archive_bytes'] and sha(a.base_archive)==binding['archive_sha256'],'BASE_ARCHIVE_HASH_MISMATCH'
   process=subprocess.Popen(command,stdin=subprocess.PIPE)
   try:
    combined_stream(a.base_archive,a.archive,process.stdin);process.stdin.close()
    assert process.wait()==0,'IMAGE_IMPORT_FAILED'
   except BaseException:
    process.kill();process.wait();raise
  else:
   assert not a.base_archive and not manifest.get('base_archive'),'UNEXPECTED_BASE_ARCHIVE'
   with open(a.archive,'rb') as stream:subprocess.run(command,stdin=stream,check=True)
 for value in manifest['images']:
  listed=subprocess.check_output([*base,'images','ls'],text=True)
  tagged=[line.split() for line in listed.splitlines() if line.split() and line.split()[0]==value['local_tag']]
  assert len(tagged)==1 and tagged[0][2]==value['manifest_digest'],'IMAGE_TAG_DIGEST_MISMATCH'
  descriptor=json.loads(subprocess.check_output([*base,'content','get',value['manifest_digest']]))
  assert descriptor['config']['digest']==value['configuration_digest'],'IMAGE_CONFIG_MISMATCH'
  # The complete digest is the immutable destination. --force is idempotent for
  # this verified digest; a bare tag is never treated as proof of image identity.
  subprocess.run([*base,'images','tag','--force',value['local_tag'],value['repository']+'@'+value['manifest_digest']],check=True)
 print('Verified image configs and registered immutable digest references.')
if __name__=='__main__':main()
