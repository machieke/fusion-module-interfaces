"""Execution owns jobs/outbox; all atom and completion effects cross declared ports."""
import json
import time
import uuid
from typing import Literal
from .contracts import (AtomRef, AtomWrite, JobAcceptance, JobStatus, ContractError,
                        canonical, digest, require)
from .ports import AtomStorage, CompletionDelivery, Mutation
from .responses import completion_acceptance

EVIDENCE = {"backend": "sqlite", "journal_mode": "WAL", "synchronous": "FULL"}


class ExecutionOwner:
    def __init__(self, db, policy, atoms: AtomStorage, messages: CompletionDelivery, capacity):
        self.db, self.policy, self.atoms, self.messages, self.capacity = db, policy, atoms, messages, capacity

    def submit(self, principal, request, identity):
        scope = request["scope_ref"]
        self.policy.check(principal, scope, "execution.submit")
        require(request["body"]["operation"] == "inspect_atom", "UNSUPPORTED_OPERATION")
        require(request["body"]["ref"]["scope_ref"] == scope, "UNAUTHORIZED")
        self.policy.route(scope, request["reply_route"], principal)
        self.policy.check(principal, scope, "atom.storage.get")
        self.policy.check("worker", scope, "atom.storage.get")
        self.atoms.get(request["body"]["ref"])
        pending = self.db.execute("SELECT count(*) FROM jobs WHERE state='queued'").fetchone()[0]
        pending += self.db.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0]
        require(pending < self.capacity, "OVERLOADED")
        job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
        self.db.execute("INSERT INTO jobs(id,scope,owner,request,state) VALUES(?,?,?,?,?)",
                        (job_id, scope, principal, canonical(request).decode(), "queued"))
        return {"job_id": job_id, "execution": "queued", "acceptance": "process-restart", "evidence": dict(EVIDENCE),
                "scope_ref": scope, "correlation_id": request["correlation_id"], "reply_route": request["reply_route"],
                "completion_delivery": "not-observed", "chain": None}

    def read(self, principal, scope, job_id, result=False):
        self.policy.check(principal, scope, "execution.result" if result else "execution.status")
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
                "scope_ref": scope, "correlation_id": json.loads(row["request"])["correlation_id"],
                "result_persistence": json.loads(row["result"])["receipt"]["durability"] if row["state"] == "succeeded" else None,
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
            data = self.atoms.get(request["body"]["ref"]).bytes
            output = canonical({"digest": digest(data), "length": len(data),
                                "operation": "inspect_atom", "provider_version": "0.1.0"})
            result = self.atoms.create(Mutation(scope, "result/" + job_id), "application/json", output)
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

    def flush(self, hook):
        sent = 0
        for row in self.db.execute("SELECT * FROM outbox WHERE sent=0 ORDER BY rowid").fetchall():
            try:
                accepted = self.messages.accept(row["scope"], row["route"], row["id"], json.loads(row["body"]))
                completion_acceptance(accepted, row["scope"], row["route"], row["id"],
                                      json.loads(row["body"])["correlation_id"])
                hook("after_delivery_accept")
            except ContractError as error:
                if error.code in {"OVERLOADED", "UNAUTHORIZED", "NOT_AVAILABLE"}:
                    continue
                raise
            self.db.execute("UPDATE outbox SET sent=1 WHERE id=?", (row["id"],))
            sent += 1
        return {"sent": sent, "pending": self.db.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0]}



class ExecutionSession:
    """Published DelegatedExecution port bound to an authenticated requester."""
    def __init__(self, owner, principal, message_id):
        self._owner, self._principal, self._message_id = owner, principal, message_id

    def submit(self, command: Mutation, operation: Literal["inspect_atom"], ref: AtomRef,
               correlation_id: str, reply_route: str, deadline_ms: int | None) -> JobAcceptance:
        request = {"scope_ref": command.scope_ref, "body": {"operation": operation, "ref": ref},
                   "correlation_id": correlation_id, "reply_route": reply_route,
                   "message_id": self._message_id}
        if deadline_ms is not None:
            request["deadline_ms"] = deadline_ms
        identity = canonical([self._principal, command.scope_ref, "execution", "submit", command.idempotency_key]).decode()
        return self._owner.submit(self._principal, request, identity)

    def status(self, scope_ref: str, job_id: str) -> JobStatus:
        return self._owner.read(self._principal, scope_ref, job_id)

    def result(self, scope_ref: str, job_id: str) -> AtomWrite:
        return self._owner.read(self._principal, scope_ref, job_id, True)
