"""Build a separate pinned SDK environment; never modifies the S01 Python runtime."""
import argparse
import json
from pathlib import Path
import subprocess

from fusion.contracts import canonical, digest, require
from fusion import neoclaw_contracts as c
from fusion import neoclaw_search_contracts as s

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT/'integration/neoclaw/search-requirements.lock'
PACKAGES = {'ddgs': '9.16.0', 'primp': '2.0.1', 'lxml': '6.1.3', 'click': '8.5.0'}


def build(directory, helper):
    directory, helper = Path(directory).resolve(), Path(helper).resolve()
    require(digest(helper.read_bytes()) == c.PINS['sources']['mettaclaw']['files']['channels/websearch.py'], 'UNSUPPORTED_PROFILE')
    directory.mkdir(parents=True, exist_ok=True)
    sdk = directory/'sdk'
    if not sdk.exists(): subprocess.run(['uv', 'venv', '--python', '3.12.12', str(sdk)], check=True)
    python = sdk/'bin/python'
    subprocess.run(['uv', 'pip', 'sync', '--python', str(python), '--require-hashes', '--only-binary', ':all:', str(LOCK)], check=True)
    # Verify wheel RECORDs as well as recording actual bytes, including extensions.
    code = '''import base64,hashlib,importlib.metadata as m,json,sys
packages=json.loads(sys.argv[1]); files={}
assert sys.version_info[:3]==(3,12,12)
for name,version in packages.items():
 d=m.distribution(name); assert d.version==version
 for file in d.files:
  if file.hash is None: continue
  path=d.locate_file(file).resolve(); data=path.read_bytes()
  assert file.hash.mode=='sha256'
  sha=hashlib.sha256(data).digest()
  assert base64.urlsafe_b64encode(sha).decode().rstrip('=')==file.hash.value
  files[str(path)]=sha.hex()
print(json.dumps(dict(files=files,python_version=sys.version)))
'''
    inventory = json.loads(subprocess.check_output([str(python), '-c', code, json.dumps(PACKAGES)], text=True))
    runtime = dict(profile=s.SDK, python=str(python), python_sha256=digest(python.read_bytes()),
                   helper=str(helper), helper_sha256=digest(helper.read_bytes()),
                   lock_sha256=digest(LOCK.read_bytes()), packages=PACKAGES, **inventory)
    path = directory/'search-runtime.json'
    path.write_bytes(canonical(runtime))
    print(path)
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory'); parser.add_argument('--helper', required=True)
    args = parser.parse_args(); build(args.directory, args.helper)
