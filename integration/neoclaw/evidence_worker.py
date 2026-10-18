"""Test-only real process-kill boundary for the existing S04 owner composition."""
import argparse
import json
import os
from pathlib import Path
import signal
from fusion import nal_memory_contracts as c
from fusion.contracts import ContractError,canonical
from tests.nal_support import Harness


def main():
    p=argparse.ArgumentParser();p.add_argument('root');p.add_argument('request');p.add_argument('--pause');a=p.parse_args()
    root=Path(a.root)
    def hook(stage):
        if stage==a.pause:
            (root/'paused.json').write_bytes(canonical(dict(stage=stage,pid=os.getpid())))
            os.kill(os.getpid(),signal.SIGSTOP)
    h=Harness(root,hook=hook)
    try:
        request=c.request(json.loads(Path(a.request).read_text()))
        try:result=dict(decision=h.beliefs.submitEvidence(request))
        except ContractError as e:result=dict(error=e.code)
        (root/'worker-result.json').write_bytes(canonical(result))
    finally:h.close()


if __name__=='__main__':main()
