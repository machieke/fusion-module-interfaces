"""Trusted native-loop hooks. Fail closed before history/next model on port errors."""
import json
import os
from pathlib import Path

from fusion.contracts import ContractError
from fusion.neoclaw_application import Application
from integration.neoclaw.neoclaw_bridge import failpoint

_app = None


def call(method, *args):
    global _app
    try:
        if _app is None:
            path = os.environ['NEOCLAW_S01_APPLICATION']
            config = json.loads(Path(path).read_text())
            _app = Application(path, lambda stage: failpoint(config, stage))
        result=getattr(_app, method)(*args)
        if method=='begin' and _app.append_enabled and _app.is_memory():
            from integration.neoclaw.append_bootstrap import select_view
            select_view(_app)
        return result
    except Exception as exc:
        # No Python exceptions/provider paths/credentials become native tool output.
        code = exc.code if isinstance(exc, ContractError) else 'NOT_AVAILABLE'
        config = json.loads(Path(os.environ['NEOCLAW_S01_APPLICATION']).read_text())
        status = dict(status='PENDING_OR_FAILED', code=code)
        if _app is not None and hasattr(_app,'write') and _app.is_append():
            status['append']=_app.write.partial()
        from fusion.adapters.neoclaw_search import SearchFailure
        if isinstance(exc, SearchFailure): status['failure_reason'] = exc.reason
        Path(config['status_file']).write_text(json.dumps(status))
        os._exit(2)


def start():
    result = more()
    if _app.embedding_enabled:
        import time, resource
        Path(_app.config['workdir'],'embedding-ready.json').write_text(json.dumps(dict(
            ready_unix_ms=time.time()*1000, peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
    if _app.two_operations:
        import importlib.util
        from fusion.contracts import require
        available = importlib.util.find_spec('ddgs') is not None
        require(not available, 'UNSUPPORTED_PROFILE')
        Path(_app.config['workdir'], 'caller-boundary.json').write_text(json.dumps(dict(
            search_sdk_importable=available,
            denied_paths_visible=[str(p) for p in _app.config.get('denied_paths', []) if Path(p).exists() and any(Path(p).iterdir())])))
    return result
def restore(): return call('restore')
def pending(): return call('pending') is not None
def response(): return call('pending')['response']
def accept(response, commands): return call('accept', response, commands)
def begin(position, command): return call('begin', position, command) is None
def end(position): return call('end', position) is None
def finish(projection): return call('finish', projection) is None
def invoke(expression): return call('invoke', expression)
def search(query): return call('search', query)


def more():
    result = call('more')
    if not result:
        Path(_app.config['status_file']).write_text(json.dumps(dict(status='BOUNDED_STOP')))
    return result

# S03 synchronous reads share application occurrence and context handoff only.
def read_captured(): return call('read_captured')
def read_replay(): return call('read_replay')
def read_candidates(vector, k): return call('read_candidates', vector, k)
def read_clock(observed): return call('read_clock', observed)
def capture_native(value): return call('capture_native', value)
def encode_query(text): return call('encode_query', text)
def remember_time(value): return call('remember_time',value)
def append_memory(content,vector,timestamp):return call('append_memory',content,vector,timestamp)
def creation_link(key,timestamp):return call('creation_link',key,timestamp)

# S04 local-only source/assessment path; shared lifecycle above.
def input_message():return call('input_message')
def source(text):return call('source',text)
def revise(target,source,sign):
    from fusion.contracts import require
    require(type(sign) is int and sign in (0,1),'INVALID_ARGUMENT')
    return call('revise',target,source,sign==1)
