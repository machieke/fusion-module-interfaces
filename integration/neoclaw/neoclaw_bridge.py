"""Local MeTTaClaw skill facade. Raw expression text never crosses the provider port."""
import json
import os
from pathlib import Path
import re
import signal

from fusion import neoclaw_contracts as c
from fusion.neoclaw_client import Caller


def failpoint(config, stage):
    if config.get('pause_at') == stage:
        from fusion.contracts import require
        require(config.get('test_failpoints') is True, 'UNAUTHORIZED')
        Path(config['failpoint_marker']).write_text(json.dumps(dict(stage=stage, pid=os.getpid())))
        os.kill(os.getpid(), signal.SIGSTOP)


def recognizes(expression):
    # Invalid arguments to the named function must fail validation, not fall
    # through to unrestricted eval. Other NAL/evaluator calls stay local.
    return bool(re.match(r'^\s*\(\s*Truth_Deduction(?:\s|\))', expression))


def invoke(expression):
    premises = c.parse_expression(expression)
    config_path = os.environ['NEOCLAW_S01_CALLER']
    config = json.loads(Path(config_path).read_text())
    caller = Caller(config_path, lambda stage: failpoint(config, stage))
    try:
        return caller.run(premises)
    finally:
        caller.close()
