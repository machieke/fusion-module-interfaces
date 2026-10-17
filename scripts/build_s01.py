"""Build the isolated S01 native command runtime from exact public source pins.

Only SWI's Prolog-to-Python Janus bridge is needed. No LLM/Chroma/channel SDK,
provider credential, global installation, or existing Fusion PLN runtime changes.
Requires Linux native build tools/libraries as recorded in build.json.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((ROOT / 'integration/neoclaw/sources.json').read_text())


def run(args, **kwargs):
    print('+', ' '.join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def build(destination):
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError('S01 requires an empty destination; existing work is never reset')
    start = time.monotonic()
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0')
    sources = destination / 'sources'
    sources.mkdir()
    for name, pin in PINS['sources'].items():
        path = sources / name
        run(['git', 'init', path], env=env)
        run(['git', '-C', path, 'remote', 'add', 'origin', pin['url']], env=env)
        run(['git', '-C', path, 'fetch', '--depth', '1', 'origin', pin['commit']], env=env)
        run(['git', '-C', path, 'checkout', '--detach', pin['commit']], env=env)
        for filename, expected in pin.get('files', {}).items():
            if hashlib.sha256((path / filename).read_bytes()).hexdigest() != expected:
                raise RuntimeError('Pinned source hash mismatch: ' + name + '/' + filename)
    swisrc = sources / 'swipl'
    run(['git', '-C', swisrc, 'submodule', 'update', '--init', '--depth', '1',
         *['packages/' + m for m in PINS['swipl_modules']]], env=env)
    venv = destination / 'venv'
    run(['uv', 'venv', '--python', PINS['python'], venv], env=env)
    python = venv / 'bin/python'
    base = subprocess.check_output([str(python), '-c', 'import sys; print(sys.base_prefix)'], text=True).strip()
    prefix, builddir = destination / 'swipl', destination / 'swipl-build'
    run(['cmake', '-S', swisrc, '-B', builddir, '-G', 'Ninja', '-DCMAKE_BUILD_TYPE=Release',
         '-DSWIPL_PACKAGES_X=OFF', '-DSWIPL_PACKAGES_JAVA=OFF', '-DSWIPL_PACKAGES_ODBC=OFF',
         '-DSWIPL_PACKAGES_QT=OFF', '-DINSTALL_DOCUMENTATION=OFF', '-DBUILD_TESTING=OFF',
         f'-DCMAKE_INSTALL_PREFIX={prefix}', f'-DPython_EXECUTABLE={base}/bin/python3.12',
         f'-DPython_ROOT_DIR={base}', f'-DPython3_EXECUTABLE={base}/bin/python3.12',
         f'-DPython3_ROOT_DIR={base}'], env=env)
    run(['ninja', '-C', builddir, '-j4'], env=env)
    if not (builddir / 'packages/swipy/janus.so').exists():
        raise RuntimeError('Native Janus was not built')
    run(['ninja', '-C', builddir, 'install'], env=env)
    env.update(PATH=f'{prefix}/bin:' + env['PATH'], LD_LIBRARY_PATH=f'{base}/lib', PYTHONHOME=base,
               VIRTUAL_ENV=str(venv), PYTHONPATH=str(ROOT), PYTHONDONTWRITEBYTECODE='1')
    binary = prefix / 'bin/swipl'
    version = subprocess.check_output([str(binary), '--version'], env=env, text=True).strip()
    if 'version 10.0.1 ' not in version:
        raise RuntimeError(version)
    bridge = subprocess.check_output([str(binary), '-q', '-g',
        'use_module(library(janus)),py_call(operator:add(20,22),X),writeln(X),halt'], env=env, text=True)
    if bridge.strip() != '42':
        raise RuntimeError('Native Prolog-to-Python bridge failed')
    runtime = dict(swipl=str(binary), petta=str(sources / 'PeTTa'),
                   mettaclaw=str(sources / 'mettaclaw'), python=str(python),
                   environment={k: env[k] for k in ('LD_LIBRARY_PATH', 'PYTHONHOME', 'VIRTUAL_ENV', 'PYTHONPATH', 'PYTHONDONTWRITEBYTECODE')})
    (destination / 'runtime.json').write_text(json.dumps(runtime, indent=2) + '\n')
    report = dict(source_pins=PINS, seconds=round(time.monotonic() - start, 3),
                  recipe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  runtime_sha256=hashlib.sha256((destination/'runtime.json').read_bytes()).hexdigest(),
                  native_libraries={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in prefix.rglob('*') if p.is_file() and '.so' in p.name},
                  python_binary_sha256=hashlib.sha256(python.resolve().read_bytes()).hexdigest(),
                  system=Path('/etc/os-release').read_text(),
                  checks=dict(swipl=version, prolog_to_python=42),
                  submodules=subprocess.check_output(['git', '-C', str(swisrc), 'submodule', 'status'], text=True).splitlines(),
                  tools={name: subprocess.check_output(command, text=True).strip() for name, command in
                         {'cmake': ['cmake', '--version'], 'ninja': ['ninja', '--version'],
                          'cc': ['cc', '--version'], 'python': [str(python), '--version'], 'uv': ['uv', '--version']}.items()},
                  binary_sha256=hashlib.sha256(binary.resolve().read_bytes()).hexdigest(),
                  cache='Fresh native objects/venv; Git and uv interpreter download caches may be warm. No empty-global-cache claim.')
    (destination / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    return runtime


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    print(json.dumps(build(parser.parse_args().destination), indent=2))
