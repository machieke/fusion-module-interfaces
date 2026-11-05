"""Bounded Search-owned disposable copies for pilot restore observation.

Pinned Chroma opens write lock rows and index allocation metadata even for a
ready/read operation. The restored durable checkpoint must stay byte exact.
Only the existing Search owner's read surface uses these ephemeral copies;
the current owner policy and authenticated source ports are unchanged.
"""
import hashlib,json,os,shutil,stat,tempfile
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .configure import write

PROFILE='copy-backed-restored-search-observation/1'
MAX_FILES,MAX_BYTES,MAX_ROOTS=8192,64*1024*1024,3


def normalized(value,root=None):
    path=Path(value)
    require(path.is_absolute() and str(path)==os.fspath(value) and '..' not in path.parts,'UNAUTHORIZED')
    try:resolved=path.resolve(strict=True)
    except OSError:require(False,'NOT_AVAILABLE')
    require(resolved==path and (root is None or path.is_relative_to(root)),'UNAUTHORIZED')
    return path


def inventory(root):
    root=Path(root);require(root.is_dir() and not root.is_symlink(),'UNAUTHORIZED')
    files={};size=0
    for directory,dirs,names in os.walk(root,followlinks=False):
        base=Path(directory)
        for name in dirs:require(not (base/name).is_symlink(),'UNAUTHORIZED')
        for name in names:
            path=base/name;info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'UNAUTHORIZED')
            size+=info.st_size;require(len(files)<MAX_FILES and size<=MAX_BYTES,'OVERLOADED')
            with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
            files[path.relative_to(root).as_posix()]=dict(bytes=info.st_size,sha256=sha)
    return files


def prepare(settings,run,state):
    if settings['role']!='fusion-search' or settings.get('preview',{}).get('pilot',{}).get('profile')!='omega-operator-pilot/1':return None
    state,run=normalized(state),normalized(run)
    fence=json.loads(normalized(state/'restore-fence.json',state).read_bytes())
    require(fence.get('mode')=='READ_ONLY_RECONCILIATION' and fence.get('role')=='fusion-search' and
        fence.get('external_effect_authority') is False,'UNAUTHORIZED')
    primary=normalized(run/'owner.json',run);cfg=json.loads(primary.read_bytes());paths=[primary]
    for selected in cfg.get('scope_routes',{}).get('scopes',{}).values():
        directory=normalized(selected['directory'],run)
        paths.append(normalized(directory/'owner.json',run))
    require(1<=len(paths)<=MAX_ROOTS and len(paths)==len(set(paths)),'OVERLOADED')
    selections=[];total_files=total_bytes=0
    for path in paths:
        current=json.loads(path.read_bytes());roots={current[k]['root'] for k in ('memory_read','memory_append','active_memory')}
        require(len(roots)==1,'CONFLICT');source=normalized(next(iter(roots)),state)
        require(source.name=='memory','UNAUTHORIZED')
        cursor=source
        while cursor!=state:
            require(not cursor.is_symlink(),'UNAUTHORIZED');cursor=cursor.parent
        before=inventory(source);total_files+=len(before);total_bytes+=sum(x['bytes'] for x in before.values())
        require(total_files<=MAX_FILES and total_bytes<=MAX_BYTES,'OVERLOADED')
        selections.append((path,current,source,before))
    destination=Path(tempfile.mkdtemp(prefix='pilot-search-observation-',dir=run));destination.chmod(0o700)
    try:
        observations=[];pending=[]
        for index,(path,current,source,before) in enumerate(selections):
            target=destination/str(index);target.mkdir(mode=0o700)
            for name in before:
                original=source/name;copy=target/name;copy.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                fd=os.open(original,os.O_RDONLY|os.O_NOFOLLOW)
                with os.fdopen(fd,'rb') as incoming,copy.open('xb') as outgoing:
                    info=os.fstat(incoming.fileno());require(stat.S_ISREG(info.st_mode) and info.st_nlink==1,'UNAUTHORIZED')
                    require(info.st_size==before[name]['bytes'],'CONFLICT');remaining=info.st_size
                    while remaining:
                        block=incoming.read(min(65536,remaining));require(block,'CONFLICT');outgoing.write(block);remaining-=len(block)
                    require(not incoming.read(1),'CONFLICT')
                copy.chmod(0o600)
            require(inventory(source)==before and inventory(target)==before,'CONFLICT')
            for field in ('memory_read','memory_append','active_memory'):current[field]['root']=str(target)
            pending.append((path,current));observations.append(dict(files=len(before),bytes=sum(x['bytes'] for x in before.values()),source_head=digest(canonical(before))))
        # Startup is still unavailable: all selections are validated before any
        # current runtime policy path is published. No authority is cloned.
        for path,current in pending:write(path,current)
        result=dict(profile=PROFILE,roots=observations,files=total_files,bytes=total_bytes,
            imported_checkpoint_changed=False,new_generations=0,new_admissions=0,scope='same Search owner only')
        write(run/'pilot-search-observation.json',result);return result
    except BaseException:
        shutil.rmtree(destination);raise
