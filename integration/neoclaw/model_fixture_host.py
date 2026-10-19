"""TEST ONLY: recorded model responses behind the real X01 owner and TLS route.

This entrypoint is never selected by the supported composition. It supplies no
tool results; actual S01 work must complete before the second prompt is received.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from fusion.adapters.ollama_completion import convert
from fusion.contracts import require
from .model_composition import EXPRESSION,OUTPUT

RECORDED=None


class RecordedBackend:
    def __init__(self,lock):pass
    def complete(self,accepted):
        if RECORDED is not None:text=RECORDED
        elif accepted.slot==1:text='metta '+EXPRESSION
        else:
            from tests.neoclaw_support import GOLDEN
            feedback=accepted.native_prompt.split(' LAST_SKILL_USE_RESULTS: ')[1].split(' HISTORY: ')[0]
            require(GOLDEN in feedback,'NOT_AVAILABLE')
            text='send '+OUTPUT
        return convert(dict(model=accepted.model,done=True,done_reason='stop',message=dict(role='assistant',content=text)))


def main():
    global RECORDED
    p=argparse.ArgumentParser();p.add_argument('config');p.add_argument('--port',type=int,required=True);p.add_argument('--ready',required=True);a=p.parse_args()
    cfg=json.loads(Path(a.config).read_text());denied=cfg.get('memory_read',{}).get('denied_paths',[])
    if denied and os.environ.get('S07_FIXTURE_ISOLATED')!='1':
        env=dict(os.environ,S07_FIXTURE_ISOLATED='1')
        cmd=['bwrap','--die-with-parent','--ro-bind','/','/','--bind','/tmp','/tmp','--proc','/proc','--dev','/dev',
             *[v for path in denied for v in ('--tmpfs',str(Path(path).resolve()))],'--',sys.executable,
             '-m','integration.neoclaw.model_fixture_host',*sys.argv[1:]]
        os.execvpe(cmd[0],cmd,env)
    import fusion.adapters.ollama_completion as backend
    RECORDED=cfg.get('test_recorded_model_response')
    backend.OllamaCompletion=RecordedBackend
    from .host import serve
    serve(a.config,a.port,a.ready)


if __name__=='__main__':main()
