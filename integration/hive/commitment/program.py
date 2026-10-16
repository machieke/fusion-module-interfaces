"""Native sibling: one operator-allowlisted completed generated inspection.

Only mapping/progress belongs here. Exact approval is assembled from a validated
caller-owned accessor; the typed local chain session owns its independent journal.
"""
from dataclasses import asdict
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import time

from fusion.adapters.f1r3 import F1R3HTTP
from fusion.adapters.f1r3_m4 import GeneratedCommitments, PROFILE, select_chain
from fusion.adapters.f1r3_signing import signer
from fusion.contracts import ContractError, canonical, digest, require
from fusion.ports import ApprovedCommitment, ConsensusFinality, Mutation
from fusion.registry import descriptor_read, selection_token
from integration.hive.program.completed import completed_inspection
from integration.hive.program.program import pause


def describe():
    return {"contract": "0.1", "kinds": [{"id": "commitment", "label": "Generated commitment", "role": "evidence"}], "relations": [], "actions": [
        {"id": a, "label": a.capitalize() + " approved generated commitment",
         "params": {"original_command": "operator-allowlisted completed inspect command"}} for a in ("commit", "observe")]}


def view(ctx, focus=None, stage=None):
    return {"revision": "1", "items": [], "links": []}


def authority(ctx, original):
    config = json.loads(Path(os.environ["FUSION_HIVE_CONFIG"]).read_text())
    registered = config["commitment"]
    require(registered["original_command"] == original and registered["principal"] == (ctx.actor or {}).get("principal")
            and registered["swarm"] == ctx.swarm_id and type(registered["expires_at_ms"]) is int and
            time.time_ns() // 1000000 < registered["expires_at_ms"], "UNAUTHORIZED")
    selected = select_chain(descriptor_read(registered["descriptor"]))
    result = completed_inspection(ctx, original)
    require(result["seed"] == registered["seed"] and result["result"]["ref"]["scope_ref"] == "shared-test" and
            result["result"]["receipt"]["provider"] == "detta-local-rs/1", "UNAUTHORIZED")
    approved = ApprovedCommitment("shared-test", result["result"]["ref"], result["result"]["ref"]["digest"],
                                  "generated-inspect-policy/1:" + registered["operation"])
    binding = {"profile": PROFILE, "selection": selection_token(selected), "chain": registered["chain"],
        "signer": registered["signer"], "limits": registered["limits"], "operation": registered["operation"],
        "protobuf_sha256": registered["protobuf_sha256"],
        "owner_journal": str(Path(registered["journal"]).resolve()),
        "authority": {k: registered[k] for k in ("principal", "swarm", "original_command", "seed", "expires_at_ms")}}
    return config, registered, result, approved, binding


def invoke(ctx, action, params):
    require(set(params) <= {"original_command", "base_revision"} and params.get("base_revision") is None and
            isinstance(params.get("original_command"), str))
    original = params["original_command"]
    config, registered, result, approved, binding = authority(ctx, original)

    def authorize():
        _, _, current_result, current_approval, current_binding = authority(ctx, original)
        require(current_result == result and current_approval == approved and current_binding == binding, "CONFLICT")

    # Source-generated protobuf, verified by the recipe. Only operator config can
    # name these paths; the native action accepts neither code nor signer inputs.
    def signing(plan):
        require(digest(Path(registered["protobuf"]).read_bytes()) == registered["protobuf_sha256"], "UNSUPPORTED_PROFILE")
        spec = importlib.util.spec_from_file_location("fusion_m4_signing_pb2", registered["protobuf"])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return signer(registered["signer_file"], registered["signer"], module.DeployDataProto)(plan)
    api = F1R3HTTP(registered["endpoint"])
    owner: ConsensusFinality = GeneratedCommitments(api, signing, registered["journal"], approved, binding,
        authorize, lambda stage: pause(config.get("chain_test", {}), stage))
    path = Path(registered["progress"])
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(str(path) + ".lock", "a") as lock:
        os.chmod(lock.name, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        with sqlite3.connect(path) as db:
            os.chmod(path, 0o600)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS progress(operation TEXT PRIMARY KEY, binding TEXT NOT NULL, deploy TEXT, submission TEXT, observation TEXT)")
            fingerprint = canonical({"approved": asdict(approved), "binding": binding}).decode()
            row = db.execute("SELECT binding,deploy,submission,observation FROM progress WHERE operation=?", (registered["operation"],)).fetchone()
            require(row is None or row[0] == fingerprint, "CONFLICT")
            if row is None:
                db.execute("INSERT INTO progress VALUES(?,?,NULL,NULL,NULL)", (registered["operation"], fingerprint))
                db.commit()
            local = {"result": result, "approval": asdict(approved), "operation": registered["operation"],
                     "chain_instance": registered["chain"], "profile": PROFILE}
            try:
                if action == "commit":
                    observation = owner.submit(Mutation(approved.scope_ref, registered["operation"]), approved)
                    db.execute("UPDATE progress SET deploy=?,submission=? WHERE operation=?",
                        (observation.deploy_id, canonical(asdict(observation)).decode(), registered["operation"]))
                    db.commit()
                else:
                    require(row is not None and row[1] is not None, "NOT_AVAILABLE")
                    observation = owner.observe(row[1])
                    pause(config.get("chain_test", {}), "after_observation_before_progress")
                    db.execute("UPDATE progress SET observation=? WHERE operation=?",
                               (canonical(asdict(observation)).decode(), registered["operation"]))
                    db.commit()
                terminal = observation.effect_finality in {"finalized", "rejected"}
                return {"status": "done" if terminal else "started",
                        "receipt": {"state": "committed" if terminal else "pending", "id": registered["operation"]},
                        "detail": {**local, "chain": asdict(observation)}}
            except ContractError as error:
                if error.code != "NOT_AVAILABLE":
                    raise
                return {"status": "started", "receipt": {"state": "unknown", "id": registered["operation"]},
                    "detail": {**local, "chain": {"effect_finality": "not-observed",
                    "deploy_id": row[1] if row else None, "error": error.wire(), "submission": "unknown"}}}


def act(ctx, action, items, params):
    try:
        require(action in {"commit", "observe"} and not items)
        return invoke(ctx, action, params)
    except ContractError as error:
        return {"status": "error" if error.wire()["retryable"] else "refused", "detail": {"error": error.wire()}}
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        return {"status": "error", "detail": {"error": ContractError("NOT_AVAILABLE").wire()}}
