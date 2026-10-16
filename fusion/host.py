"""Private stdio binding. Worker entry points are operator-only composition."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import sys

from .composition import catalogue, service
from .contracts import ContractError, canonical, require, validate
from .registry import descriptor_wire, selected_for, selection_token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["rpc", "work", "flush", "describe"])
    parser.add_argument("config")
    parser.add_argument("--pause-at", choices=["after_acceptance", "after_result_persist", "after_completion_commit",
                                              "after_delivery_accept", "after_atom_persist"])
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())

    def hook(stage):
        if stage == args.pause_at:
            require(config.get("test_failpoints") is True, "UNAUTHORIZED")
            Path(config["failpoint_marker"]).write_text(stage)
            os.kill(os.getpid(), signal.SIGSTOP)

    owner = None
    token = None
    try:
        if args.mode == "describe":
            sys.stdout.buffer.write(canonical({"ok": [descriptor_wire(p) for p in catalogue(args.config)]}) + b"\n")
            return
        owner = service(args.config, hook)
        if args.mode == "rpc":
            raw = sys.stdin.buffer.read(100001)
            require(len(raw) <= 100000)
            value = json.loads(raw)
            require(set(value) in ({"credential", "request"}, {"credential", "request", "selection"}))
            if "selection" in value:
                validate(value["request"], check_deadline=False)
                token = selection_token(selected_for(owner.catalogue, value["request"]))
                require(value["selection"] == token, "UNSUPPORTED_PROFILE")
            result = owner.invoke(value["credential"], value["request"])
        else:
            result = getattr(owner, args.mode)()
        reply = {"ok": result}
        if token is not None:
            reply["provider"] = token
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
