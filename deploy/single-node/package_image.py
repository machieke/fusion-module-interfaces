"""Create a clean image context from pinned S01 build products, not a workspace mount.

Prerequisites: scripts/build_s01.py DEST and scripts/build_detta.py products.
Exact selected bytes, upstream pins and shared-library closure are recorded.
No private journal, credential, local model asset or arbitrary source tree is copied.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def package(destination,runtime,detta):
    import sys
    sys.path.insert(0,str(ROOT))
    from fusion.adapters.neoclaw_nal import NativeTruthDeduction
    from fusion import neoclaw_contracts as c
    validated=NativeTruthDeduction(runtime)  # Pin validation only, no computation.
    old=validated.runtime;build=json.loads((runtime.parent/'build.json').read_text())
    destination.mkdir(parents=True,exist_ok=False);native=destination/'native';native.mkdir()
    python=Path(old['python']).resolve().parent.parent
    shutil.copytree(python,native/'python',symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    prefix=runtime.parent/'swipl'
    shutil.copytree(prefix,native/'swipl',symlinks=True)
    for name,key in (('mettaclaw','mettaclaw'),('PeTTa','petta')):
        for file,want in c.PINS['sources'][name]['files'].items():
            source=Path(old[key])/file;assert sha(source)==want
            target=native/'sources'/name/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    # These are redistributable runtime libraries from the recorded build host.
    # The base image supplies glibc/loader. Preserve all other required bytes.
    excluded={'libc.so.6','libm.so.6','libdl.so.2','libpthread.so.0','librt.so.1','libutil.so.1','libresolv.so.2'}
    deps=native/'deps';deps.mkdir();closure={}
    candidates=[Path(old['swipl']).resolve(),detta,Path(old['python']).resolve()]
    candidates += [p for base in (prefix,python) for p in base.rglob('*') if p.is_file() and '.so' in p.name]
    for binary in candidates:
        result=subprocess.run(['ldd',str(binary)],capture_output=True,text=True)
        for name,lib in re.findall(r'^\s*(\S+)\s+=>\s+(/\S+)',result.stdout,re.M):
            path=Path(lib).resolve()
            if name in excluded or path.is_relative_to(prefix) or path.is_relative_to(python):continue
            checksum=sha(path)
            if name in closure:assert closure[name]==checksum,(name,path)
            else:shutil.copyfile(path,deps/name);closure[name]=checksum
    shutil.copyfile(detta,native/'fusion-detta-adapter');(native/'fusion-detta-adapter').chmod(0o755)
    environment=dict(PYTHONHOME='/opt/native/python',PYTHONPATH='/opt/fusion',PYTHONDONTWRITEBYTECODE='1',
        LD_LIBRARY_PATH='/opt/native/python/lib:/opt/native/swipl/lib/swipl/lib/x86_64-linux:/opt/native/deps',
        SWI_HOME_DIR='/opt/native/swipl/lib/swipl')
    relocated=dict(swipl='/opt/native/swipl/bin/swipl',python='/opt/native/python/bin/python3.12',
        petta='/opt/native/sources/PeTTa',mettaclaw='/opt/native/sources/mettaclaw',environment=environment)
    (native/'runtime.json').write_text(json.dumps(relocated,indent=2)+'\n')
    shutil.copyfile(runtime.parent/'build.json',native/'original-build.json')
    build['runtime_sha256']=sha(native/'runtime.json')
    (native/'build.json').write_text(json.dumps(build,indent=2)+'\n')
    source=destination/'source';sources={}
    for folder in ('fusion','integration'):
        for file in sorted((ROOT/folder).rglob('*')):
            if not file.is_file() or file.suffix not in ('.py','.json','.metta','.pl') or '__pycache__' in file.parts:continue
            rel=file.relative_to(ROOT);target=source/rel;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(file,target);sources[str(rel)]=sha(file)
    shutil.copyfile(ROOT/'deploy/single-node/Dockerfile',destination/'Dockerfile')
    record=dict(recipe='deploy/single-node/package_image.py',recipe_sha256=sha(__file__),
        fusion_commit=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
        sources=sources,native_source_pins={k:v['commit'] for k,v in c.PINS['sources'].items()},
        original_runtime_sha256=sha(runtime),relocated_runtime_sha256=sha(native/'runtime.json'),
        swipl_binary_sha256=build['binary_sha256'],python_binary_sha256=build['python_binary_sha256'],
        detta_binary_sha256=sha(detta),system_library_closure=closure,
        dockerfile_sha256=sha(destination/'Dockerfile'),
        closure_scope='Pinned existing native build products; paths relocated, numerical source/binary profiles unchanged. No bit-reproducible compiler-build claim.')
    (destination/'package.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(context=str(destination),sources=len(sources),shared_libraries=len(closure),detta_sha256=sha(detta))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    parser.add_argument('--runtime',type=Path,default=ROOT/'artifacts/s01/native-02/runtime.json')
    parser.add_argument('--detta',type=Path,default=ROOT/'artifacts/detta-build/target/debug/fusion-detta-adapter')
    args=parser.parse_args();package(args.destination.resolve(),args.runtime.resolve(),args.detta.resolve())
