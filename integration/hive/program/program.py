"""Programs plugin for verified Hive 34b0fb3. Only generated, shareable bytes.

Hive supplies actor/command; the operator supplies a private credential mapping.
This file owns only caller receipts. All remote effects use validated stdio RPC.
The journal is a single-host boundary record, not episodic memory or a scheduler.
"""
import fcntl
import json
import os
from pathlib import Path
import signal
import sqlite3

from fusion.bindings import Subprocess
from fusion.client import Peer
from fusion.contracts import ContractError, canonical, digest, require
from fusion.registry import descriptor_read, select, selection_token


def describe():
    return {"contract": "0.1", "kinds": [{"id": "sample", "label": "Generated sample", "role": "evidence"}],
            "relations": [], "actions": [{"id": "inspect", "label": "Inspect generated sample",
                "params": {"seed": "integer 0..4294967295; generated data only"}}]}


def view(ctx, focus=None, stage=None):
    # No receipt disclosure through the unauthenticated plugin view context.
    return {"revision": "1", "items": [], "links": []}


def pause(config, stage):
    # Trusted operator configuration only, absent in normal use.
    if config.get("test_pause_at") == stage:
        Path(config["test_marker"]).write_text(stage)
        os.kill(os.getpid(), signal.SIGSTOP)


def pending(identity, record):
    return {"status": "started", "receipt": {"state": "pending", "id": identity},
            "detail": record}


def inspect(ctx, params):
    actor, command = ctx.actor or {}, ctx.command or {}
    require(not ctx.read_only and actor.get("kind") == "person" and actor.get("route") == "operator"
            and actor.get("swarm_id") == ctx.swarm_id, "UNAUTHORIZED")
    key = command.get("idempotency_key")
    require(isinstance(key, str) and 1 <= len(key) <= 120)
    require(set(params) <= {"seed", "base_revision"} and type(params.get("seed")) is int
            and 0 <= params["seed"] <= 4294967295 and params.get("base_revision") is None)
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
    fingerprint = digest(canonical([command["params_digest"], context]))
    data = f"Fusion M1.2 explicitly shareable generated sample {params['seed']}\n".encode()
    path = Path(config["receipts"])
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Serialize only this caller journal, never hold a transaction in another owner.
    with open(str(path) + ".lock", "a") as lock:
        os.chmod(lock.name, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        with sqlite3.connect(path) as db:
            os.chmod(path, 0o600)
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, "
                       "route TEXT NOT NULL, record TEXT NOT NULL, outcome TEXT, acknowledged INTEGER NOT NULL DEFAULT 0)")
            prior = db.execute("SELECT fingerprint,record,outcome,acknowledged FROM receipts WHERE id=?", (identity,)).fetchone()
            if prior:
                require(prior[0] == fingerprint, "CONFLICT")
                record, outcome, acknowledged = json.loads(prior[1]), json.loads(prior[2]) if prior[2] else None, prior[3]
            else:
                # This bounded operation requires a dedicated reply route and one
                # unfinished intent per route. Never discard an unsolicited message.
                require(not db.execute("SELECT 1 FROM receipts WHERE route=? AND acknowledged=0",
                                       (grant["reply_route"],)).fetchone(), "OVERLOADED")
                record, outcome, acknowledged = {"caller": context, "seed": params["seed"], "correlation_id": identity}, None, 0
                db.execute("INSERT INTO receipts(id,fingerprint,route,record) VALUES(?,?,?,?)",
                           (identity, fingerprint, grant["reply_route"], canonical(record).decode()))
                db.commit()
            if "job" not in record:
                stored = peer.store(data, "input/" + identity)
                shared = peer.share(stored["ref"], grant["counterparty"], "share/" + identity)
                job = peer.delegate(stored["ref"], identity)
                pause(config, "after_admission")
                record.update(input=stored, shared=shared, job=job)
                db.execute("UPDATE receipts SET record=? WHERE id=?", (canonical(record).decode(), identity))
                db.commit()
                pause(config, "after_submission")
            # Every replay rechecks current authority; never return a cached outcome
            # solely on possession of an old receipt. Status /2 restores correlation.
            job_id = record["job"]["job_id"]
            status = peer.status(job_id)
            require(status["correlation_id"] == identity, "NOT_AVAILABLE")
            require(peer.retrieve(record["input"]["ref"]) == data, "NOT_AVAILABLE")
            delivery = peer.poll()
            if status["execution"] == "queued":
                return pending(identity, record)
            result, output = None, None
            if status["execution"] == "succeeded":
                result = peer.result(job_id)
                output = json.loads(peer.retrieve(result["ref"]))
                require(output == {"digest": digest(data), "length": len(data), "operation": "inspect_atom",
                                   "provider_version": "0.1.0"}, "NOT_AVAILABLE")
            if outcome is None:
                if delivery is None:
                    return pending(identity, {**record, "execution": status["execution"], "completion": "not-observed"})
                body = delivery["body"]
                require(body.get("job_id") == job_id and body["correlation_id"] == identity
                        and body["result"] == result and body["error"] == status["error"], "NOT_AVAILABLE")
                outcome = {**record, "result": result, "output": output, "error": status["error"],
                           "delivery_id": delivery["delivery_id"]}
                db.execute("UPDATE receipts SET outcome=? WHERE id=?", (canonical(outcome).decode(), identity))
                db.commit()
                pause(config, "after_acceptance")
            else:
                require(outcome["result"] == result and outcome["output"] == output and
                        outcome["error"] == status["error"], "NOT_AVAILABLE")
                if delivery is not None and delivery["delivery_id"] == outcome["delivery_id"]:
                    require(delivery["body"]["job_id"] == job_id and delivery["body"]["correlation_id"] == identity
                            and delivery["body"]["result"] == result and delivery["body"]["error"] == status["error"], "NOT_AVAILABLE")
            # Replays after an ack response was lost use the same ack identity.
            peer.ack(outcome["delivery_id"], "ack/" + identity)
            if not acknowledged:
                db.execute("UPDATE receipts SET acknowledged=1 WHERE id=?", (identity,))
                db.commit()
            return {"status": "error" if outcome["error"] else "done",
                    "receipt": {"state": "committed", "id": identity}, "detail": outcome}


def act(ctx, action, items, params):
    try:
        require(action == "inspect" and not items)
        return inspect(ctx, params)
    except ContractError as error:
        return {"status": "error" if error.wire()["retryable"] else "refused", "detail": {"error": error.wire()}}
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
        return {"status": "error", "detail": {"error": ContractError("NOT_AVAILABLE").wire()}}
