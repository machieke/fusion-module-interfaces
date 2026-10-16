"""Wire admission and replay; concrete owners are supplied by composition."""
import json
import sqlite3
import time
from typing import Callable

from .contracts import (ContractError, canonical, decode, digest, encode, require,
                        validate, MUTATIONS, LEGACY_PROFILES)
from .ports import AtomStorage, DelegatedExecution, Messaging, Mutation

SCHEMA = """
CREATE TABLE IF NOT EXISTS mutations (
  identity TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, scope TEXT NOT NULL,
  owner TEXT NOT NULL, request TEXT NOT NULL, state TEXT NOT NULL,
  result TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, route TEXT NOT NULL,
  body TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0);
"""


def legacy_receipt(request, result):
    """Explicit /1 local-profile encoder; /2 never inherits SQLite as a contract."""
    if request["profile"] not in LEGACY_PROFILES.values():
        return result
    result = dict(result)
    for key in ("scope_ref", "correlation_id", "route", "reply_route"):
        result.pop(key, None)
    if isinstance(result.get("delivery"), dict):
        result["delivery"] = {k: v for k, v in result["delivery"].items() if k not in {"scope_ref", "route"}}
    if "evidence" in result:
        result.pop("evidence")
        for name in ("acceptance", "persistence"):
            if name in result:
                result[name] = "sqlite-full"
    return result


class Service:
    def __init__(self, db, policy, atoms_for: Callable[[str], AtomStorage],
                 messaging_for: Callable[[str, str], Messaging],
                 execution_for: Callable[[str, str], DelegatedExecution],
                 worker, catalogue, hook=lambda _: None):
        self.db, self.policy, self.hook = db, policy, hook
        self.atoms_for, self.messaging_for, self.execution_for = atoms_for, messaging_for, execution_for
        self.worker, self.catalogue = worker, catalogue

    def close(self):
        self.db.close()

    def invoke(self, credential, request):
        principal = self.policy.authenticate(credential)
        name, op = validate(request, check_deadline=False)
        scope, body = request["scope_ref"], request["body"]
        self.policy.check(principal, scope, name + "." + op)
        if "reply_route" in request:
            self.policy.route(scope, request["reply_route"], principal)
        if name == "agent.messaging":
            self.policy.route(scope, body["route"], None if op == "send" else principal)
        if op in {"get", "getMany", "availability", "send"}:
            self.policy.check(principal, scope, "atom.storage.get")
        identity = canonical([principal, scope, name, op, request.get("idempotency_key")]).decode()
        semantic = {k: v for k, v in request.items() if k not in {"message_id", "extensions", "causation_id"}}
        fingerprint = digest(canonical(semantic))
        command = Mutation(scope, request.get("idempotency_key", "read"), fingerprint)
        try:
            with self.db:
                self.db.execute("BEGIN IMMEDIATE")
                if op in MUTATIONS:
                    old = self.db.execute("SELECT * FROM mutations WHERE identity=?", (identity,)).fetchone()
                    if old:
                        require(old["fingerprint"] == fingerprint, "CONFLICT")
                        return json.loads(old["response"])
                require(time.time_ns() // 1_000_000 < request.get("deadline_ms", 2**63), "DEADLINE_EXCEEDED")
                if name == "atom.storage":
                    atoms = self.atoms_for(principal)
                    if op == "create":
                        result = atoms.create(command, body["content_type"], decode(body["bytes"]))
                        self.hook("after_atom_persist")
                    elif op == "getMany":
                        result = {"atoms": [self._envelope(x) for x in atoms.getMany(tuple(body["refs"]))]}
                    elif op == "get":
                        result = self._envelope(atoms.get(body["ref"]))
                    else:
                        result = atoms.availability(body["ref"])
                elif name == "agent.messaging":
                    messages = self.messaging_for(principal, request["message_id"])
                    if op == "send":
                        result = messages.send(command, body["ref"], body["route"],
                                               request["correlation_id"], request["reply_route"])
                    elif op == "poll":
                        result = {"delivery": messages.poll(scope, body["route"])}
                    else:
                        result = messages.ack(command, body["route"], body["delivery_id"])
                else:
                    execution = self.execution_for(principal, request["message_id"])
                    if op == "submit":
                        result = execution.submit(command, body["operation"], body["ref"], request["correlation_id"],
                                                  request["reply_route"], request.get("deadline_ms"))
                    else:
                        result = getattr(execution, op)(scope, body["job_id"])
                result = legacy_receipt(request, result)
                if op in MUTATIONS:
                    self.db.execute("INSERT INTO mutations VALUES(?,?,?)", (identity, fingerprint, canonical(result).decode()))
            self.hook("after_acceptance")
            return result
        except sqlite3.OperationalError as error:
            raise ContractError("OVERLOADED" if "locked" in str(error) else "NOT_AVAILABLE") from None
        except OSError:
            raise ContractError("NOT_AVAILABLE") from None

    @staticmethod
    def _envelope(value):
        return {"ref": value.ref, "content_type": value.content_type, "bytes": encode(value.bytes)}

    def work(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            result = self.worker.work_one(self.hook)
        self.hook("after_completion_commit")
        return result

    def flush(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return self.worker.flush(self.hook)
