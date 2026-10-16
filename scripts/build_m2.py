"""Fresh M2 provider build. No sibling edits or copied native/target/venv outputs.

Uses the unchanged M1.2 Hive recipe, then pinned public Reachability/PLN and a
fresh DeTTa adapter target. Download caches may be warm; empty-cache is separate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_hive import build as build_native
from fusion.adapters.pln_revision import PINS, verify_source, GuardedRevision
from fusion import memory_contracts as c


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def build(destination):
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError('M2 build requires an empty destination')
    started = time.monotonic()
    destination.mkdir(parents=True, exist_ok=True)
    native_env, python = build_native(destination / 'native')
    paths = {}
    for name in ('reachability', 'pln'):
        source = destination / 'sources' / name; source.mkdir(parents=True)
        pin = PINS['sources'][name]
        run(['git', 'init', '-q', source])
        run(['git', '-C', source, 'remote', 'add', 'origin', pin['url']])
        run(['git', '-C', source, 'fetch', '--depth', '1', 'origin', pin['commit']])
        run(['git', '-C', source, 'checkout', '--detach', pin['commit']])
        verify_source(name, source)
        paths[name] = str(source)
    swipl = destination / 'native/swipl/bin/swipl'
    revision = dict(paths, petta=native_env['PETTA_PATH'], swipl=str(swipl),
        swipl_sha256=hashlib.sha256(swipl.resolve().read_bytes()).hexdigest(), runtime_profile=c.RUNTIME,
        environment={'LD_LIBRARY_PATH': native_env['LD_LIBRARY_PATH']})
    revision_path = destination / 'revision-environment.json'
    revision_path.write_text(json.dumps(revision, indent=2) + '\n')
    profile = GuardedRevision(revision_path).profile()
    target = destination / 'detta'; (target / 'src').mkdir(parents=True)
    shutil.copyfile(ROOT / 'adapters/detta/src/main.rs', target / 'src/main.rs')
    shutil.copyfile(ROOT / 'adapters/detta/Cargo.lock', target / 'Cargo.lock')
    manifest = '[package]\nname="fusion-detta-adapter"\nversion="0.1.0"\nedition="2021"\n[dependencies]\n'
    for name in ('detta-da', 'detta-storage'):
        manifest += name + ' = { path = ' + json.dumps(str(Path(native_env['DETTA_REPO']) / 'crates' / name)) + ' }\n'
    manifest += 'serde = { version="1.0", features=["derive"] }\nserde_json="1.0"\n'
    (target / 'Cargo.toml').write_text(manifest)
    run(['cargo', 'build', '--locked', '--manifest-path', target / 'Cargo.toml'])
    env = dict(native_env, M2_REVISION_ENV=str(revision_path),
               M2_DETTA_BINARY=str(target / 'target/debug/fusion-detta-adapter'))
    (destination / 'environment.json').write_text(json.dumps(env, indent=2) + '\n')
    (destination / 'build.json').write_text(json.dumps({'fresh_destination': True, 'seconds': round(time.monotonic()-started, 3),
        'source_pins': PINS, 'revision_profile': profile, 'native_build': json.loads((destination / 'native/build.json').read_text()),
        'recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'cache': 'Warm Git/Python/Cargo download caches allowed. Fresh native objects, venv and DeTTa target. Empty-cache NOT_RUN.'}, indent=2) + '\n')
    print('M2 fresh build complete:', destination / 'environment.json', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    build(parser.parse_args().destination)
