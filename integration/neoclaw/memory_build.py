"""Fresh-target S03 CPU SDK/model/helper recipe; reuses independent S01/DeTTa builds."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
from fusion.contracts import canonical,digest,require

ROOT=Path(__file__).resolve().parents[2]
LOCK=ROOT/'integration/neoclaw/memory-requirements.lock'
MODEL=ROOT/'integration/neoclaw/memory-model.json'
HELPER_COMMIT='218484875d5d1bfb217a9a03d3983dc1ed9d406c'


def inventory(python):
    code='''import importlib.metadata as m,json,hashlib,base64,sys
files={};packages={}
for d in m.distributions():
 packages[d.metadata['Name']]=d.version
 for f in d.files or []:
  if f.hash is None or f.hash.mode!='sha256':continue
  path=d.locate_file(f).resolve();data=path.read_bytes();sha=hashlib.sha256(data).digest()
  assert base64.urlsafe_b64encode(sha).decode().rstrip('=')==f.hash.value
  files[str(path)]=sha.hex()
print(json.dumps(dict(packages=packages,files=files,python_version=sys.version)))
'''
    return json.loads(subprocess.check_output([str(python),'-c',code],text=True))


def build(directory,model_cache=None):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    sdk=directory/'venv'
    if not sdk.exists():subprocess.run(['uv','venv','--python','3.12.12',str(sdk)],check=True)
    python=sdk/'bin/python'
    subprocess.run(['uv','pip','sync','--python',str(python),'--require-hashes','--only-binary',':all:',
        '--extra-index-url','https://download.pytorch.org/whl/cpu',str(LOCK)],check=True)
    spec=json.loads(MODEL.read_text());model=directory/'model';model.mkdir(exist_ok=True)
    for name,sha in spec['files'].items():
        path=model/name;path.parent.mkdir(parents=True,exist_ok=True)
        if not path.exists() or digest(path.read_bytes())!=sha:
            temporary=path.with_suffix('.download')
            if model_cache:
                import shutil
                shutil.copyfile(Path(model_cache)/name,temporary)
            else:urllib.request.urlretrieve('https://huggingface.co/'+spec['model']+'/resolve/'+spec['revision']+'/'+name,temporary)
            require(digest(temporary.read_bytes())==sha,'NOT_AVAILABLE');temporary.replace(path)
    helper=directory/'sources/petta_lib_chromadb'
    if not helper.exists():
        helper.parent.mkdir(exist_ok=True)
        subprocess.run(['git','clone','--no-checkout','https://github.com/patham9/petta_lib_chromadb.git',str(helper)],check=True)
        subprocess.run(['git','-C',str(helper),'checkout','--detach',HELPER_COMMIT],check=True)
    require(subprocess.check_output(['git','-C',str(helper),'rev-parse','HEAD'],text=True).strip()==HELPER_COMMIT,'UNSUPPORTED_PROFILE')
    runtime=dict(sdk=str(sdk),python=str(python),python_sha256=digest(python.read_bytes()),lock_sha256=digest(LOCK.read_bytes()),
        model=str(model),model_spec=spec,helper=str(helper/'lib_chromadb.py'),helper_sha256=digest((helper/'lib_chromadb.py').read_bytes()),**inventory(python))
    path=directory/'memory-runtime.json';path.write_bytes(canonical(runtime));return path


def validate_runtime(path):
    runtime=json.loads(Path(path).read_text())
    require(runtime['lock_sha256']==digest(LOCK.read_bytes()) and runtime['model_spec']==json.loads(MODEL.read_text()),'UNSUPPORTED_PROFILE')
    require(digest(Path(runtime['python']).read_bytes())==runtime['python_sha256'],'UNSUPPORTED_PROFILE')
    require(digest(Path(runtime['helper']).read_bytes())==runtime['helper_sha256']=='461b78f92234b58e1090e66c332d627a063e201751d8247459d82a18e7afd36d','UNSUPPORTED_PROFILE')
    for file,sha in runtime['files'].items():require(digest(Path(file).read_bytes())==sha,'UNSUPPORTED_PROFILE')
    return runtime


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory');p.add_argument('--model-cache');args=p.parse_args()
    print(build(args.directory,args.model_cache))
if __name__=='__main__':main()
