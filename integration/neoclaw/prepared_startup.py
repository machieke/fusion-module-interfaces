"""Opt-in verified, session-local immutable overlay preparation.

Every launcher still checks the pinned native executable/libraries and packaged
Python sources. The cache saves overlay construction, not current authority or
model readiness. The native process receives a read-only mount of the published
entry. No private payload, provider token or live authorization is cached.
"""
import json,os,shutil,tempfile
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.adapters.neoclaw_nal import NativeTruthDeduction
from fusion.native_telemetry import span
from integration.single_node.sustained_runtime import public_config

PROFILE='verified-native-preparation/1'
ROOT=Path(__file__).resolve().parents[2]


def source_map(root=ROOT):
    result={}
    for name in ('fusion','integration'):
        base=root/name;require(base.is_dir() and not base.is_symlink(),'UNSUPPORTED_PROFILE')
        for path in sorted(base.rglob('*')):
            if '__pycache__' in path.parts:continue
            require(not path.is_symlink(),'UNSUPPORTED_PROFILE')
            if path.is_file() and path.suffix in ('.py','.json','.metta'):
                result[str(path.relative_to(root))]=digest(path.read_bytes())
    return result


def files(directory):
    result={}
    for p in sorted(directory.rglob('*')):
        require(not p.is_symlink(),'CONFLICT')
        if p.is_file() and p!=directory/'prepared.json':
            require(p.stat().st_size<=1048576,'OVERLOADED')
            result[str(p.relative_to(directory))]=digest(p.read_bytes())
    require(1<=len(result)<=64,'OVERLOADED');return result


def verified(directory,key):
    require(directory.is_dir() and not directory.is_symlink(),'CONFLICT')
    path=directory/'prepared.json';require(path.is_file() and not path.is_symlink(),'CONFLICT')
    value=json.loads(path.read_bytes())
    require(set(value)=={'profile','key','files','command','environment'} and value['profile']==PROFILE and value['key']==key,'CONFLICT')
    require(files(directory)==value['files'],'CONFLICT')
    for p in (directory,*directory.rglob('*')):require(p.stat().st_mode & 0o222 == 0,'CONFLICT')
    return value


def prepare(config_file,builder):
    config_file=Path(config_file).resolve();config=json.loads(config_file.read_bytes());selected=config['native_preparation']
    require(type(selected) is dict and set(selected)=={'profile','package_file','immutability'} and selected['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    require(selected['immutability'] in ('native-readonly-mount','readonly-package'),'UNSUPPORTED_PROFILE')
    mounted=selected['immutability']=='native-readonly-mount'
    if mounted:require(shutil.which('bwrap') is not None,'NOT_AVAILABLE')
    with span('native.preparation_verify'):
        runtime=NativeTruthDeduction(config['runtime']).runtime
        package=Path(selected['package_file']);require(package.is_file() and not package.is_symlink(),'UNSUPPORTED_PROFILE')
        pinned=json.loads(package.read_bytes())['source'];require(source_map(ROOT)==pinned,'UNSUPPORTED_PROFILE')
        if not mounted:
            # Deployment packages are enforced read-only by Kubernetes. Cache
            # files remain derived owner-local data, hash-checked on every use.
            # This is not a claim that chmod defeats a malicious same-UID host.
            for path in (ROOT,package,Path(config['runtime']),Path(runtime['swipl']).resolve(),Path(runtime['python']).resolve(),Path(runtime['mettaclaw']),Path(runtime['petta'])):
                require(os.statvfs(path).f_flag & os.ST_RDONLY,'UNSUPPORTED_PROFILE')
        dependencies={}
        for name,path in config.items():
            if name.endswith('_config') and type(path) is str:
                p=Path(path);require(p.is_file() and not p.is_symlink(),'CONFLICT')
                dependencies[name]=digest(canonical(public_config(json.loads(p.read_bytes()))))
        if 'memory_native_config' in config:
            from .memory_oracle import HELPER,HELPER_HASH
            native=json.loads(Path(config['memory_native_config']).read_bytes())
            require(digest(Path(native.get('helper',HELPER)).read_bytes())==HELPER_HASH,'UNSUPPORTED_PROFILE')
        selection={k:v for k,v in config.items() if k not in ('pause_at','test_failpoints')}
        identity=dict(profile=PROFILE,source=digest(canonical(pinned)),runtime=digest(Path(config['runtime']).read_bytes()),
            build=digest((Path(config['runtime']).parent/'build.json').read_bytes()),configuration=public_config(selection),
            config_file=str(config_file),dependencies=dependencies,
            inherited_environment={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','TMPDIR')})
        key=digest(canonical(identity))
    work=Path(config['workdir']).resolve();work.mkdir(parents=True,exist_ok=True,mode=0o700)
    cache=work/'prepared';require(not cache.is_symlink(),'CONFLICT');cache.mkdir(exist_ok=True,mode=0o700)
    target=cache/key
    with span('native.preparation_reuse' if target.exists() else 'native.preparation_publish'):
        if not target.exists():
            require(len(list(cache.iterdir()))<16,'OVERLOADED')
            stage=Path(tempfile.mkdtemp(prefix='.pending-',dir=cache))
            # A crash leaves an explicitly incomplete, never selected directory.
            command,environment,_=builder(config_file,overlay_directory=stage)
            for path in stage.rglob('*'):
                require(not path.is_symlink(),'CONFLICT')
                if path.is_file():path.write_bytes(path.read_bytes().replace(str(stage).encode(),str(target).encode()))
            command=[x.replace(str(stage),str(target)) for x in command]
            startup=stage/'startup.json';manifest=json.loads(startup.read_bytes())
            manifest['overlay_hashes']={name:digest((stage/name).read_bytes()) for name in manifest['overlay_hashes']}
            startup.write_bytes(canonical(manifest))
            value=dict(profile=PROFILE,key=key,files=files(stage),command=command,environment=environment)
            (stage/'prepared.json').write_bytes(canonical(value))
            for p in stage.rglob('*'):
                if p.is_file():
                    with p.open('rb') as stream:os.fsync(stream.fileno())
                    p.chmod(0o444)
            for p in sorted((x for x in stage.rglob('*') if x.is_dir()),reverse=True):p.chmod(0o555)
            stage.chmod(0o555);os.rename(stage,target)
            fd=os.open(cache,os.O_DIRECTORY)
            try:os.fsync(fd)
            finally:os.close(fd)
        value=verified(target,key)
    command=value['command'];environment=value['environment']
    if mounted and command[0]=='bwrap':
        separator=command.index('--');command=command[:separator]+['--ro-bind',str(target),str(target)]+command[separator:]
    elif mounted:
        command=['bwrap','--die-with-parent','--bind','/','/','--proc','/proc','--dev','/dev','--ro-bind',str(target),str(target),'--',*command]
    (work/'repos/mettaclaw/memory').mkdir(parents=True,exist_ok=True)
    # Compatibility diagnostic copy only. Native imports the verified entry.
    (work/'startup.json').write_bytes((target/'startup.json').read_bytes())
    (work/'preparation-observation.json').write_bytes(canonical(dict(profile=PROFILE,key=key,immutability=selected['immutability'],readonly_native_mount=mounted,authorization_cached=False)))
    return command,environment,work
