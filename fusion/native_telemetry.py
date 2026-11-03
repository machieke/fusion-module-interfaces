"""Opt-in bounded monotonic spans. Never carries arguments, results or authority.

The sink is local diagnostic state, not a journal, receipt or work-budget source.
Missing/dropped spans are explicit qualification failures, never tool failures.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import itertools,json,os,re,threading,time,uuid
from pathlib import Path

PROFILE='bounded-native-stage-timing/1'
_sink=None
_stack=ContextVar('native_stage_stack',default=())
_lock=threading.Lock()
_sequence=itertools.count(1)
_process=str(uuid.uuid4())

def configure(config):
    global _sink
    selected=config.get('native_telemetry')
    if selected is None:return
    from .contracts import require
    require(selected=={'profile':PROFILE,'max_bytes':4194304},'UNSUPPORTED_PROFILE')
    directory=Path(config['workdir']);directory.mkdir(parents=True,exist_ok=True)
    require(not directory.is_symlink(),'UNAUTHORIZED')
    _sink=directory/'native-stages.jsonl'
    require(not _sink.is_symlink(),'UNAUTHORIZED')

def _bytes(value):
    if isinstance(value,bytes):return len(value)
    if isinstance(value,str):return len(value.encode())
    try:
        from .contracts import canonical
        return len(canonical(value))
    except (TypeError,ValueError):return None

@contextmanager
def span(name, *, request_bytes=None, started_ns=None):
    if _sink is None:
        yield {};return
    # Labels come from source constants / native method names, never task text.
    if not isinstance(name,str) or re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}',name) is None:
        yield {};return
    parent=_stack.get();ordinal=next(_sequence);token=_stack.set((*parent,ordinal))
    start=time.monotonic_ns() if started_ns is None else started_ns;meter={};error=None
    try:yield meter
    except BaseException as exc:
        from .contracts import ContractError
        error=exc.code if isinstance(exc,ContractError) else 'FAILED'
        raise
    finally:
        end=time.monotonic_ns();_stack.reset(token)
        row=dict(profile=PROFILE,process=_process,pid=os.getpid(),span=ordinal,parent=parent[-1] if parent else None,
            name=name,start_ns=start,duration_ns=end-start,count=1,request_bytes=request_bytes,
            response_bytes=meter.get('response_bytes'),code=error)
        encoded=(json.dumps(row,separators=(',',':'))+'\n').encode()
        try:
            with _lock:
                if (_sink.stat().st_size if _sink.exists() else 0)+len(encoded)<=4194304:
                    with _sink.open('ab') as stream:stream.write(encoded)
                else:
                    # A constant marker makes truncation visible without any
                    # extra per-span retention or payload logging.
                    _sink.with_suffix('.truncated').touch(exist_ok=True)
        except OSError:pass

def traced(name, *, request=None):
    def decorate(function):
        @wraps(function)
        def wrapped(*args,**kwargs):
            if _sink is None:return function(*args,**kwargs)
            size=_bytes(args[request]) if request is not None and len(args)>request else None
            with span(name,request_bytes=size) as meter:
                result=function(*args,**kwargs);meter['response_bytes']=_bytes(result);return result
        return wrapped
    return decorate
