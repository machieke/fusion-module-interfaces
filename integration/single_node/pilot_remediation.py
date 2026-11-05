"""Offline image-build-only installation of a reviewed finite leaf wheel set.

Never runs a native interpreter/model/provider. Historical locks remain intact;
new runtime inventories record both their historical basis and this exact
remediation layer. No core numerical, parser, Chroma, model or E5 source changes.
"""
import json,os,subprocess,sys
from pathlib import Path
from fusion.contracts import canonical,digest,require

LOCK=Path(__file__).resolve().parents[1]/'neoclaw/pilot-leaf-remediation.json'
ALLOWED={'certifi','filelock','httpcore2','httpx2','idna','pip','requests','urllib3'}


def check_dependencies(manager,interpreter,env):
    # Inspect installed METADATA, without importing providers or contacting an
    # index. --no-deps installation is not evidence of dependency compatibility.
    result=subprocess.run([manager,'-m','pip','--python',interpreter,'check'],env=env,text=True,capture_output=True)
    if result.stdout:print(result.stdout,end='',flush=True)
    if result.stderr:print(result.stderr,end='',file=sys.stderr,flush=True)
    result.check_returncode()


def apply(directory):
    directory=Path(directory);lock=json.loads(LOCK.read_bytes())
    require(lock['profile']=='compatible-sdk-leaf-remediation/1','UNSUPPORTED_PROFILE')
    rows=lock['packages'];require({x['name'] for x in rows}==ALLOWED and len(rows)==len(ALLOWED),'UNSUPPORTED_PROFILE')
    wheels={}
    for row in rows:
        path=directory/row['filename'];require(path.name==row['filename'] and not path.is_symlink() and digest(path.read_bytes())==row['sha256'],'CONFLICT')
        wheels[row['name']]=str(path)
    native='/opt/native/python/bin/python3.12';env={**os.environ,'PIP_DISABLE_PIP_VERSION_CHECK':'1','PIP_NO_INDEX':'1','PYTHONDONTWRITEBYTECODE':'1'}
    runtime=Path('/opt/memory-runtime.json');before=json.loads(runtime.read_bytes()) if runtime.is_file() else None
    old_digest=digest(runtime.read_bytes()) if before else None
    if before:
        Path('/opt/pilot-prior-memory-runtime.json').write_bytes(runtime.read_bytes())
        # Validate the actual selected source before altering its leaf packages.
        for path,sha in before['files'].items():require(digest(Path(path).read_bytes())==sha,'CONFLICT')
        subprocess.run([native,'-m','pip','--python',before['python'],'install','--no-index','--no-deps','--no-cache-dir','--no-compile','--upgrade',*[wheels[n] for n in sorted(ALLOWED-{'pip'})]],env=env,check=True)
        check_dependencies(native,before['python'],env)
        from integration.neoclaw.memory_build import inventory
        after=inventory(before['python'])
        def leaf_path(path):
            parts=Path(path).parts
            return any(part in ALLOWED or any(part.startswith(name.replace('-','_')+'-') and part.endswith('.dist-info') for name in ALLOWED) for part in parts)
        for path,sha in before['files'].items():
            if not leaf_path(path):require(after['files'].get(path)==sha,'CONFLICT')
        for name,version in before['packages'].items():
            if name.lower().replace('_','-') not in ALLOWED:require(after['packages'].get(name)==version,'CONFLICT')
        result={**before,**after,'remediation':dict(profile=lock['profile'],lock_sha256=digest(LOCK.read_bytes()),prior_runtime_sha256=old_digest,changed_packages={r['name']:r['version'] for r in rows if r['name']!='pip'},historical_lock_preserved=before['lock_sha256'])}
        runtime.write_bytes(canonical(result))
    # The immutable image's packaged interpreter carries PEP 668 metadata.
    # This exception applies only to its explicit build layer, never the host.
    subprocess.run([native,'-m','pip','install','--break-system-packages','--no-index','--no-deps','--no-cache-dir','--no-compile','--upgrade',wheels['pip']],env=env,check=True)
    check_dependencies(native,native,env)
    Path('/opt/pilot-remediation.json').write_bytes(canonical(dict(profile=lock['profile'],lock_sha256=digest(LOCK.read_bytes()),wheels={r['name']:r['sha256'] for r in rows},prior_runtime_sha256=old_digest,runtime_sha256=digest(runtime.read_bytes()) if before else None)))


if __name__=='__main__':
    require(len(sys.argv)==2,'INVALID_ARGUMENT');apply(sys.argv[1])
