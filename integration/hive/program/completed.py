"""Read-only accessor owned by the original generated-inspect caller.

Its private context format matches the unchanged M1.2 program. It validates the
accepted outcome via the current ports, never another owner's SQL.
"""
import json
import os
from pathlib import Path
import sqlite3
from fusion.bindings import Subprocess
from fusion.client import Peer
from fusion.contracts import canonical, digest, require
from fusion.registry import descriptor_read, select, selection_token


def caller_binding(ctx, key):
    """Caller-owned authority/context shared with the completed-result accessor."""
    actor, command = ctx.actor or {}, ctx.command or {}
    require(not ctx.read_only and actor.get("kind") == "person" and actor.get("route") == "operator"
            and actor.get("swarm_id") == ctx.swarm_id, "UNAUTHORIZED")
    require(isinstance(key, str) and 1 <= len(key) <= 120)
    config = json.loads(Path(os.environ["FUSION_HIVE_CONFIG"]).read_text())
    grants = [g for g in config["grants"] if g["principal"] == actor.get("principal") and g["swarm"] == ctx.swarm_id]
    require(len(grants) == 1, "UNAUTHORIZED")
    grant = grants[0]
    selected = select([descriptor_read(d) for d in config["descriptors"]])
    binding = Subprocess(config["service_config"], grant["credential"], selected=selected)
    peer = Peer(binding, grant["scope"], grant["reply_route"])
    identity = digest(canonical([actor["principal"], ctx.swarm_id, key]))
    context = {"principal": actor["principal"], "swarm": ctx.swarm_id, "scope": grant["scope"],
               "reply_route": grant["reply_route"], "counterparty": grant["counterparty"],
               "service_config": config["service_config"],
               "selection": {k: selection_token(v) for k, v in selected.items()}}
    return config, grant, peer, identity, context


def completed_inspection(ctx, original_command):
    """Read this caller's accepted result and recheck live services. No mutations.

    This is a trusted composition accessor, not a public reference lookup. The
    caller journal is the only SQL read here; remote owners are accessed by ports.
    Private caller context/correlation is deliberately absent from the result.
    """
    config, grant, peer, identity, context = caller_binding(ctx, original_command)
    path = Path(config["receipts"])
    require(path.is_file(), "NOT_FOUND")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        row = db.execute("SELECT outcome,acknowledged FROM receipts WHERE id=?", (identity,)).fetchone()
    require(row is not None and row[0] is not None and row[1] == 1, "NOT_AVAILABLE")
    outcome = json.loads(row[0])
    require(outcome["caller"] == context, "CONFLICT")
    status = peer.status(outcome["job"]["job_id"])
    require(status["execution"] == "succeeded" and status["error"] is None and
            status["correlation_id"] == identity and outcome["error"] is None, "NOT_AVAILABLE")
    data = f"Fusion M1.2 explicitly shareable generated sample {outcome['seed']}\n".encode()
    require(peer.retrieve(outcome["input"]["ref"]) == data, "NOT_AVAILABLE")
    result = peer.result(outcome["job"]["job_id"])
    raw = peer.retrieve(result["ref"])
    require(result == outcome["result"] and digest(raw) == result["ref"]["digest"] and
            json.loads(raw) == outcome["output"] == {"digest": digest(data), "length": len(data),
                "operation": "inspect_atom", "provider_version": "0.1.0"}, "NOT_AVAILABLE")
    return {"seed": outcome["seed"], "input": outcome["input"], "result": result,
            "result_bytes": len(raw), "job_id": outcome["job"]["job_id"],
            "delivery_id": outcome["delivery_id"], "acceptance": "committed", "acknowledged": True}

