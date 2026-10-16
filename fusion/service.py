"""Module owners behind declared ports. All concrete providers enter by injection."""
from __future__ import annotations

import hmac
import json
from pathlib import Path
import sqlite3
import time
import uuid

from .contracts import (ContractError, Storage, canonical, decode, digest, encode,
                        require, validate, MUTATIONS)

SCHEMA = """
CREATE TABLE IF NOT EXISTS mutations (
  identity TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS atoms (
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, digest TEXT NOT NULL,
  content_type TEXT NOT NULL, payload_id TEXT NOT NULL, receipt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS jobs (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, scope TEXT NOT NULL,
  owner TEXT NOT NULL, request TEXT NOT NULL, state TEXT NOT NULL,
  result TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY, scope TEXT NOT NULL, route TEXT NOT NULL,
  body TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS messages (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL, scope TEXT NOT NULL,
  route TEXT NOT NULL, body TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0);
"""


class Policy:
    """Live server-side registered requirements, explicitly a local test policy."""
    def __init__(self, path: str):
        self.path = Path(path)

    def current(self):
        return json.loads(self.path.read_text())

    def authenticate(self, credential: str) -> str:
        require(isinstance(credential, str) and credential.isascii() and 1 <= len(credential) <= 256, "UNAUTHORIZED")
        for principal, record in self.current()["principals"].items():
            if hmac.compare_digest(credential, record["credential"]):
                return principal
        raise ContractError("UNAUTHORIZED")

    def check(self, principal: str, scope: str, method: str):
        methods = self.current()["principals"].get(principal, {}).get("scopes", {}).get(scope, [])
        require(method in methods, "UNAUTHORIZED")

    def route(self, scope: str, route: str, owner: str | None = None):
        registered = self.current()["routes"].get(route)
        require(registered is not None and registered["scope"] == scope, "UNAUTHORIZED")
        if owner is not None:
            require(registered["owner"] == owner, "UNAUTHORIZED")
        self.check(registered["owner"], scope, "agent.messaging.poll")


class AtomOwner:
    def __init__(self, db, storage: Storage):
        self.db, self.storage = db, storage

    def create(self, scope, coordinate, content_type, data):
        atom_id = str(uuid.uuid5(uuid.NAMESPACE_URL, coordinate))
        payload_id, receipt = self.storage.put(scope, coordinate, data)
        ref = {"scope_ref": scope, "id": atom_id, "revision": 1, "digest": digest(data)}
        self.db.execute("INSERT INTO atoms VALUES (?,?,?,?,?,?)",
                        (atom_id, scope, ref["digest"], content_type, payload_id,
                         canonical(receipt).decode()))
        return {"ref": ref, "receipt": receipt}

    def row(self, scope, ref):
        require(ref["scope_ref"] == scope, "UNAUTHORIZED")
        row = self.db.execute("SELECT * FROM atoms WHERE id=? AND scope=?", (ref["id"], scope)).fetchone()
        require(row is not None, "NOT_FOUND")
        require(ref["revision"] == 1 and ref["digest"] == row["digest"], "CONFLICT")
        return row

    def get(self, scope, ref):
        row = self.row(scope, ref)
        try:
            data = self.storage.get(scope, row["payload_id"])
        except ContractError as error:
            if error.code == "NOT_FOUND":
                raise ContractError("NOT_AVAILABLE") from None
            raise
        require(digest(data) == row["digest"], "NOT_AVAILABLE")
        return {"ref": ref, "content_type": row["content_type"], "bytes": encode(data)}

    def availability(self, scope, ref):
        row = self.row(scope, ref)
        try:
            return self.storage.availability(scope, row["payload_id"])
        except ContractError as error:
            if error.code == "NOT_FOUND":
                raise ContractError("NOT_AVAILABLE") from None
            raise


class MessageOwner:
    def __init__(self, db, policy, capacity):
        self.db, self.policy, self.capacity = db, policy, capacity

    def enqueue(self, scope, route, delivery_id, body):
        self.policy.route(scope, route)
        if self.db.execute("SELECT 1 FROM messages WHERE id=?", (delivery_id,)).fetchone():
            return
        count = self.db.execute("SELECT count(*) FROM messages WHERE route=? AND acknowledged=0",
                                (route,)).fetchone()[0]
        require(count < self.capacity, "OVERLOADED")
        self.db.execute("INSERT INTO messages(id,scope,route,body) VALUES(?,?,?,?)",
                        (delivery_id, scope, route, canonical(body).decode()))

    def poll(self, principal, scope, route):
        self.policy.route(scope, route, principal)
        row = self.db.execute("SELECT * FROM messages WHERE scope=? AND route=? AND acknowledged=0 ORDER BY seq LIMIT 1",
                              (scope, route)).fetchone()
        if row is None:
            return {"delivery": None}
        return {"delivery": {"delivery_id": row["id"], "body": json.loads(row["body"]),
                             "order": row["seq"], "delivery": "observed-unacknowledged"}}

    def ack(self, principal, scope, route, delivery_id):
        self.policy.route(scope, route, principal)
        row = self.db.execute("SELECT 1 FROM messages WHERE id=? AND scope=? AND route=?",
                              (delivery_id, scope, route)).fetchone()
        require(row is not None, "NOT_FOUND")
        self.db.execute("UPDATE messages SET acknowledged=1 WHERE id=?", (delivery_id,))
        return {"delivery_id": delivery_id, "delivery": "acknowledged", "persistence": "sqlite-full"}


class ExecutionOwner:
    def __init__(self, db, policy, atoms, messages, capacity):
        self.db, self.policy, self.atoms, self.messages, self.capacity = db, policy, atoms, messages, capacity

    def submit(self, principal, request, identity):
        scope = request["scope_ref"]
        self.policy.route(scope, request["reply_route"], principal)
        self.policy.check(principal, scope, "atom.storage.get")
        self.policy.check("worker", scope, "atom.storage.get")
        self.atoms.row(scope, request["body"]["ref"])
        pending = self.db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0]
        pending += self.db.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0]
        require(pending < self.capacity, "OVERLOADED")
        job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
        self.db.execute("INSERT INTO jobs(id,scope,owner,request,state) VALUES(?,?,?,?,?)",
                        (job_id, scope, principal, canonical(request).decode(), "queued"))
        return {"job_id": job_id, "execution": "queued", "acceptance": "sqlite-full",
                "completion_delivery": "not-observed", "chain": None}

    def read(self, principal, scope, job_id, result=False):
        row = self.db.execute("SELECT * FROM jobs WHERE id=? AND scope=? AND owner=?",
                              (job_id, scope, principal)).fetchone()
        require(row is not None, "NOT_FOUND")
        if result:
            if row["error"]:
                raise ContractError(row["error"])
            require(row["state"] == "succeeded", "NOT_AVAILABLE")
            return json.loads(row["result"])
        outbox = self.db.execute("SELECT sent FROM outbox WHERE id=?", (job_id,)).fetchone()
        return {"job_id": job_id, "execution": row["state"], "error": row["error"],
                "result_persistence": "local-files-process-restart" if row["state"] == "succeeded" else None,
                "completion_delivery": "mailbox-accepted" if outbox and outbox[0] else "not-observed",
                "chain": None}

    def work_one(self, hook):
        row = self.db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY seq LIMIT 1").fetchone()
        if row is None:
            return {"worked": False}
        request = json.loads(row["request"])
        scope, job_id, error, result = row["scope"], row["id"], None, None
        try:
            self.policy.check(row["owner"], scope, "execution.submit")
            self.policy.check(row["owner"], scope, "atom.storage.get")
            self.policy.check("worker", scope, "atom.storage.get")
            self.policy.check("worker", scope, "atom.storage.create")
            self.policy.route(scope, request["reply_route"], row["owner"])
            if request.get("deadline_ms", 2**63) <= time.time_ns() // 1_000_000:
                raise ContractError("DEADLINE_EXCEEDED")
            data = decode(self.atoms.get(scope, request["body"]["ref"])["bytes"])
            output = canonical({"digest": digest(data), "length": len(data),
                                "operation": "inspect_atom", "provider_version": "0.1.0"})
            result = self.atoms.create(scope, "result/" + job_id, "application/json", output)
            hook("after_result_persist")
        except ContractError as exc:
            if exc.code in {"NOT_AVAILABLE", "OVERLOADED"}:
                raise
            error = exc.code
        self.db.execute("UPDATE jobs SET state=?,result=?,error=? WHERE id=?",
                        ("failed" if error else "succeeded", canonical(result).decode() if result else None,
                         error, job_id))
        completion = {"job_id": job_id, "correlation_id": request["correlation_id"],
                      "causation_id": request["message_id"], "result": result, "error": error}
        self.db.execute("INSERT INTO outbox(id,scope,route,body) VALUES(?,?,?,?)",
                        (job_id, scope, request["reply_route"], canonical(completion).decode()))
        return {"worked": True, "job_id": job_id, "execution": "failed" if error else "succeeded"}

    def flush(self):
        sent = 0
        for row in self.db.execute("SELECT * FROM outbox WHERE sent=0 ORDER BY rowid").fetchall():
            try:
                self.messages.enqueue(row["scope"], row["route"], row["id"], json.loads(row["body"]))
            except ContractError as error:
                if error.code in {"OVERLOADED", "UNAUTHORIZED"}:
                    continue
                raise
            self.db.execute("UPDATE outbox SET sent=1 WHERE id=?", (row["id"],))
            sent += 1
        return {"sent": sent, "pending": self.db.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0]}


class Service:
    def __init__(self, database: str, storage: Storage, policy: Policy, capacity=8, hook=lambda _: None):
        self.db = sqlite3.connect(database, timeout=0.2)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript(SCHEMA)
        self.policy, self.hook = policy, hook
        self.atoms = AtomOwner(self.db, storage)
        self.messages = MessageOwner(self.db, policy, capacity)
        self.execution = ExecutionOwner(self.db, policy, self.atoms, self.messages, capacity)

    def close(self):
        self.db.close()

    def invoke(self, credential, request):
        principal = self.policy.authenticate(credential)
        name, op = validate(request, check_deadline=False)
        scope = request["scope_ref"]
        self.policy.check(principal, scope, name + "." + op)
        body = request["body"]
        if "reply_route" in request:
            self.policy.route(scope, request["reply_route"], principal)
        if op in {"get", "getMany", "availability", "send"}:
            self.policy.check(principal, scope, "atom.storage.get")
        identity = canonical([principal, scope, name, op, request.get("idempotency_key")]).decode()
        semantic = {k: v for k, v in request.items() if k not in {"message_id", "extensions", "causation_id"}}
        fingerprint = digest(canonical(semantic))
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
                    if op == "create":
                        result = self.atoms.create(scope, identity, body["content_type"], decode(body["bytes"]))
                    elif op == "getMany":
                        result = {"atoms": [self.atoms.get(scope, ref) for ref in body["refs"]]}
                    else:
                        result = getattr(self.atoms, op)(scope, body["ref"])
                elif name == "agent.messaging":
                    if op == "send":
                        self.atoms.row(scope, body["ref"])
                        delivery_id = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
                        self.messages.enqueue(scope, body["route"], delivery_id,
                                              {"ref": body["ref"], "correlation_id": request["correlation_id"],
                                               "reply_route": request["reply_route"], "causation_id": request["message_id"]})
                        result = {"delivery_id": delivery_id, "acceptance": "sqlite-full", "delivery": "not-observed"}
                    elif op == "poll":
                        result = self.messages.poll(principal, scope, body["route"])
                    else:
                        result = self.messages.ack(principal, scope, body["route"], body["delivery_id"])
                elif op == "submit":
                    result = self.execution.submit(principal, request, identity)
                else:
                    result = self.execution.read(principal, scope, body["job_id"], op == "result")
                if op in MUTATIONS:
                    self.db.execute("INSERT INTO mutations VALUES(?,?,?)", (identity, fingerprint, canonical(result).decode()))
            self.hook("after_acceptance")
            return result
        except sqlite3.OperationalError as error:
            raise ContractError("OVERLOADED" if "locked" in str(error) else "NOT_AVAILABLE") from None

    def work(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            result = self.execution.work_one(self.hook)
        self.hook("after_completion_commit")
        return result

    def flush(self):
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            return self.execution.flush()
