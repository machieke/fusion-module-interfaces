"""New closure boundaries: real SIGKILL, labelled deterministic clock injection."""
import json,os,signal,sys,time
from pathlib import Path
from fusion.cognition import open_cognition
from fusion.contracts import canonical
from fusion.ports import Mutation,InferenceRequest,WorkBudget
from fusion.adapters.pln_deduction import DeductionRuntime
config=json.loads(Path(sys.argv[1]).read_text())
def hook(stage):
    if config.get('stage')==stage:
        Path(config['marker']).write_text(stage);os.kill(os.getpid(),signal.SIGSTOP)
original=DeductionRuntime.evaluate
def evaluate(self,*args):
    with open(config['invocations'],'ab') as stream:stream.write(b'native-attempt\n');stream.flush();os.fsync(stream.fileno())
    return original(self,*args)
DeductionRuntime.evaluate=evaluate
modules=open_cognition(config['private_config'],config['credential'],config['scope'],hook=hook)
if config.get('now_ms') is not None:time.time=lambda:config['now_ms']/1000
if config['operation']=='drain':result=modules.relay.drain(config['episode'])
else:
    value=config['request'];request=InferenceRequest(**{**value,'command':Mutation(**value['command']),'budget':WorkBudget(**value['budget'])})
    if config['operation']=='step':result=modules.controller.step(request)
    else:result=modules.controller.reconcile(Mutation(config['scope'],'recover'),request,1)
Path(config['result']).write_bytes(canonical(result))
