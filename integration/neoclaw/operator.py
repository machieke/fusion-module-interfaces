"""Bounded trusted work/flush process for S01; never exposed through HTTPS."""
import argparse
import json
import os
from pathlib import Path
import time

from fusion.contracts import ContractError, require
from fusion.neoclaw import NalService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    parser.add_argument('--ready', required=True)
    parser.add_argument('--seconds', type=int, default=60)
    args = parser.parse_args()
    require(1 <= args.seconds <= 300)
    deadline = time.monotonic()+args.seconds
    service = NalService(args.config)
    service.close()
    Path(args.ready).write_text(json.dumps(dict(pid=os.getpid(), seconds=args.seconds)))
    while time.monotonic() < deadline:
        service = NalService(args.config)
        try:
            service.work()
            service.flush()
        except ContractError as exc:
            if exc.code != 'OVERLOADED': raise
        finally:
            service.close()
        time.sleep(.03)


if __name__ == '__main__': main()
