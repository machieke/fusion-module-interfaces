"""Caller-specific reproducible SDK: real Chroma metadata, no E5 libraries/assets."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess

from fusion.contracts import canonical, digest, require
from .memory_build import inventory
from .memory_oracle import HELPER_HASH

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path(__file__).with_name('embedding-caller-requirements.lock')
ABSENT = ('torch', 'sentence_transformers', 'transformers')


def build(directory, helper):
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=True)
    sdk = directory/'venv'
    if not sdk.exists(): subprocess.run(['uv', 'venv', '--python', '3.12.12', str(sdk)], check=True)
    python = sdk/'bin/python'
    subprocess.run(['uv', 'pip', 'sync', '--python', str(python), '--require-hashes', '--only-binary', ':all:', str(LOCK)], check=True)
    helper = Path(helper).resolve(); require(digest(helper.read_bytes()) == HELPER_HASH, 'UNSUPPORTED_PROFILE')
    observed = json.loads(subprocess.check_output([str(python), '-c',
        'import importlib.util,json;print(json.dumps({x:importlib.util.find_spec(x) is None for x in '+repr(ABSENT)+'}))'], text=True))
    require(all(observed.values()), 'UNSUPPORTED_PROFILE')
    runtime = dict(profile='neoclaw-query-caller-no-e5/1', sdk=str(sdk), python=str(python),
        python_sha256=digest(python.read_bytes()), lock_sha256=digest(LOCK.read_bytes()),
        helper=str(helper), helper_sha256=HELPER_HASH, absent=observed, **inventory(python))
    path = directory/'caller-runtime.json'; path.write_bytes(canonical(runtime)); return path


def validate_runtime(path):
    runtime = json.loads(Path(path).read_text())
    require(runtime['profile'] == 'neoclaw-query-caller-no-e5/1' and runtime['lock_sha256'] == digest(LOCK.read_bytes()), 'UNSUPPORTED_PROFILE')
    require(runtime['absent'] == dict.fromkeys(ABSENT, True), 'UNSUPPORTED_PROFILE')
    for file, sha in {**runtime['files'], runtime['python']:runtime['python_sha256'], runtime['helper']:HELPER_HASH}.items():
        require(digest(Path(file).read_bytes()) == sha, 'UNSUPPORTED_PROFILE')
    return runtime


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('directory'); p.add_argument('--helper', required=True)
    args = p.parse_args(); print(build(args.directory, args.helper))
