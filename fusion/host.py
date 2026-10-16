"""Private stdio binding. Worker entry points are operator-only composition."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys

from .composition import service
from .contracts import ContractError, canonical, require


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["rpc", "work", "flush"])
    parser.add_argument("config")
    parser.add_argument("--pause-at", choices=["after_acceptance", "after_result_persist", "after_completion_commit"])
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())

    def hook(stage):
        if stage == args.pause_at:
            require(config.get("test_failpoints") is True, "UNAUTHORIZED")
            Path(config["failpoint_marker"]).write_text(stage)
            os.kill(os.getpid(), signal.SIGSTOP)

    owner = None
    try:
        owner = service(args.config, hook)
        if args.mode == "rpc":
            raw = sys.stdin.buffer.read(100001)
            require(len(raw) <= 100000)
            value = json.loads(raw)
            require(set(value) == {"credential", "request"})
            result = owner.invoke(value["credential"], value["request"])
        else:
            result = getattr(owner, args.mode)()
        reply = {"ok": result}
    except ContractError as exc:
        reply = {"error": exc.wire()}
    except (ValueError, TypeError, KeyError):
        reply = {"error": ContractError("INVALID_ARGUMENT").wire()}
    except (sqlite3.Error, OSError) as exc:
        reply = {"error": ContractError("OVERLOADED" if "locked" in str(exc) else "NOT_AVAILABLE").wire()}
    finally:
        if owner is not None:
            owner.close()
    sys.stdout.buffer.write(canonical(reply) + b"\n")


if __name__ == "__main__":
    main()
