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
        return getattr(_app, method)(*args)
    except Exception as exc:
        # No Python exceptions/provider paths/credentials become native tool output.
        code = exc.code if isinstance(exc, ContractError) else 'NOT_AVAILABLE'
        config = json.loads(Path(os.environ['NEOCLAW_S01_APPLICATION']).read_text())
        Path(config['status_file']).write_text(json.dumps(dict(status='PENDING_OR_FAILED', code=code)))
        os._exit(2)


def start(): return more()
def restore(): return call('restore')
def pending(): return call('pending') is not None
def response(): return call('pending')['response']
def accept(response, commands): return call('accept', response, commands)
def begin(position, command): return call('begin', position, command) is None
def end(position): return call('end', position) is None
def finish(projection): return call('finish', projection) is None
def invoke(expression): return call('invoke', expression)


def more():
    result = call('more')
    if not result:
        Path(_app.config['status_file']).write_text(json.dumps(dict(status='BOUNDED_STOP')))
    return result
