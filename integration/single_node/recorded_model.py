"""Explicit recorded backend for the real ModelInference owner. Zero live mode.

No transport fallback, fixture-selected execution, or generic model launcher.
Recorded outputs follow the pinned adapter's response conversion only.
"""
import json
import os
from pathlib import Path
import sys
from fusion.contracts import canonical,digest,require

BOUNDARY='RECORDED_MODEL_RESPONSE_FIXTURE'


def deny_live(mode):
    require(mode=='recorded','UNAUTHORIZED')
    from fusion.adapters import ollama_completion
    def forbidden(*args,**kwargs):raise PermissionError('LIVE_GENERATION_DISABLED')
    ollama_completion.OllamaCompletion=forbidden
    def audit(event,args):
        if event in ('socket.connect','subprocess.Popen','os.exec','os.posix_spawn'):forbidden()
    sys.addaudithook(audit)
    return dict(mode=mode,real_runtime_startups=0,real_backend_calls=0,live_reservations=0,live_captures=0)


class RecordedBackend:
    def __init__(self,lock):
        raw=Path(lock['path']).read_bytes();require(digest(raw)==lock['sha256'],'CONFLICT')
        self.cfg=json.loads(raw);require(self.cfg['boundary']==BOUNDARY and self.cfg['mode']=='recorded','UNAUTHORIZED')
        require(len(self.cfg['responses'])==2,'INVALID_ARGUMENT')
    def complete(self,accepted):
        from fusion.adapters.ollama_completion import convert
        require(accepted.session==self.cfg['session'] and accepted.slot in (1,2),'UNAUTHORIZED')
        raw=self.cfg['responses'][accepted.slot-1]
        record=dict(boundary=BOUNDARY,id=accepted.id,session=accepted.session,slot=accepted.slot,intent_sha256=digest(canonical(accepted.__dict__)),response=raw,live_generation=False)
        with open(self.cfg['log'],'ab') as f:f.write(canonical(record)+b'\n');f.flush();os.fsync(f.fileno())
        return convert(dict(model=accepted.model,done=True,done_reason='stop',message=dict(role='assistant',content=raw)))
