"""Verified relocation of existing S03/S03.1 SDKs into role-specific images.

Run after package_image.py. The source/SDK/model bytes are pinned and checked;
only filesystem prefixes, venv launch paths and runtime manifest hashes change.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from fusion.contracts import canonical,digest,require


def package(base,destination,kind,runtime):
    if kind=='embedding':
        from integration.neoclaw.memory_build import validate_runtime
    else:
        from integration.neoclaw.embedding_caller_build import validate_runtime
    old=validate_runtime(runtime);destination.mkdir(parents=True,exist_ok=False)
    sdk=destination/'sdk';shutil.copytree(old['sdk'],sdk,symlinks=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ('python','python3','python3.12'):
        path=sdk/'bin'/name
        if path.exists() or path.is_symlink():path.unlink()
        path.symlink_to('/opt/native/python/bin/python3.12')
    (sdk/'pyvenv.cfg').write_text('home = /opt/native/python/bin\ninclude-system-site-packages = false\nversion = 3.12.12\n')
    helper=destination/'helper';helper.mkdir();shutil.copyfile(old['helper'],helper/'lib_chromadb.py')
    new={**old,'sdk':'/opt/sdk','python':'/opt/sdk/bin/python','helper':'/opt/helper/lib_chromadb.py',
         'files':{p.replace(old['sdk'],'/opt/sdk',1):sha for p,sha in old['files'].items()}}
    # Inventory includes script bytes; keep them unchanged (runtime never uses
    # their old shebangs). Python's venv entrypoint is the separately pinned ELF.
    for file,sha in old['files'].items():
        path=sdk/Path(file).relative_to(old['sdk']);require(digest(path.read_bytes())==sha,'CONFLICT')
    if kind=='embedding':
        model=destination/'model';model.mkdir()
        for file,sha in old['model_spec']['files'].items():
            source=Path(old['model'])/file;require(digest(source.read_bytes())==sha,'CONFLICT')
            target=model/file;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
        new['model']='/opt/model'
    (destination/'runtime.json').write_bytes(canonical(new))
    dockerfile=f'''FROM {base}
USER root
COPY sdk /opt/sdk
COPY helper /opt/helper
COPY runtime.json /opt/memory-runtime.json
'''+('COPY model /opt/model\n' if kind=='embedding' else '')+'''ENV PYTHONPATH=/opt/fusion:/opt/sdk/lib/python3.12/site-packages
USER 1000:1000
'''
    (destination/'Dockerfile').write_text(dockerfile)
    (destination/'package.json').write_bytes(canonical(dict(kind=kind,base=base,
        original_runtime_sha256=digest(runtime.read_bytes()),runtime_sha256=digest(canonical(new)),
        recipe_sha256=digest(Path(__file__).read_bytes()),files=len(new['files']),packages=new['packages'],
        model_spec=new.get('model_spec'),absent=new.get('absent'))))
    print(str(destination))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination',type=Path);p.add_argument('--base',required=True)
    p.add_argument('--kind',choices=['caller','embedding'],required=True);p.add_argument('--runtime',type=Path,required=True)
    a=p.parse_args();package(a.base,a.destination,a.kind,a.runtime)
