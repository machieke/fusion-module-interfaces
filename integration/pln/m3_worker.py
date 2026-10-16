"""Actual kill-test child. Only explicitly configured test hooks stop the process."""
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import sys
from fusion.cognition import open_cognition
from fusion.contracts import canonical
from fusion.ports import InferenceRequest, Mutation, WorkBudget, Stimulus
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
value=config['request']
if config.get('operation')=='stimulus':
    result=modules.attention.submitStimulus(Stimulus(**{**value,'command':Mutation(**value['command'])}))
else:
    request=InferenceRequest(**{**value,'command':Mutation(**value['command']),'budget':WorkBudget(**value['budget'])})
    result=modules.controller.step(request)
Path(config['result']).write_bytes(canonical(result))
