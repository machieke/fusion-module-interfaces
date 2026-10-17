"""Test/CLI output capture after native parsing, eval and the real metta handler."""
import json
import os
from pathlib import Path


def record(value):
    Path(os.environ['NEOCLAW_S01_CAPTURE']).write_text(json.dumps(value, default=str) + '\n')
    return True
