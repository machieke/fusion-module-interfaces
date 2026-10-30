"""Verify/import the recorded image archive and register its digest references."""
import argparse,hashlib,json,subprocess
from pathlib import Path

def sha(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()

def main():
 p=argparse.ArgumentParser();p.add_argument('--container',required=True);p.add_argument('--manifest',required=True);p.add_argument('--archive');p.add_argument('--register-only',action='store_true');a=p.parse_args()
 manifest=json.loads(Path(a.manifest).read_bytes())
 base=['docker','exec',a.container,'ctr','--address','/run/k3s/containerd/containerd.sock','--namespace','k8s.io']
 if not a.register_only:
  assert a.archive and sha(a.archive)==manifest['archive_sha256'],'ARCHIVE_HASH_MISMATCH'
  with open(a.archive,'rb') as stream:subprocess.run(['docker','exec','-i',a.container,*base[3:],'images','import','-'],stdin=stream,check=True)
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
