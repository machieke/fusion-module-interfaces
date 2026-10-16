"""Mailbox-owned durable acceptance, including a narrow trusted completion port."""
import json
import sqlite3
import uuid

from .contracts import (AtomRef, JSON, MessageAcceptance, MessageAck, MessageDelivery,
                        canonical, digest, require)
from .ports import AtomStorage, Mutation

EVIDENCE = {"backend": "sqlite", "journal_mode": "WAL", "synchronous": "FULL"}


class MessageOwner:
    def __init__(self, database, policy, capacity):
        self._database, self._policy, self._capacity = database, policy, capacity
        db = self._connect()
        try:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
              scope TEXT NOT NULL, route TEXT NOT NULL, body TEXT NOT NULL,
              fingerprint TEXT NOT NULL, acknowledged INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS acknowledgements (
              identity TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, response TEXT NOT NULL);
            """)
        finally:
            db.close()

    def _connect(self):
        db = sqlite3.connect(self._database, timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def _enqueue(self, scope, route, delivery_id, body, intent=None):
        self._policy.route(scope, route)
        semantic = {k: v for k, v in body.items() if k != "causation_id"}
        fingerprint = digest(canonical([scope, route, semantic, intent]))
        db = self._connect()
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute("SELECT fingerprint FROM messages WHERE id=?", (delivery_id,)).fetchone()
                if old:
                    require(old[0] == fingerprint, "CONFLICT")
                else:
                    count = db.execute("SELECT count(*) FROM messages WHERE route=? AND acknowledged=0", (route,)).fetchone()[0]
                    require(count < self._capacity, "OVERLOADED")
                    db.execute("INSERT INTO messages(id,scope,route,body,fingerprint) VALUES(?,?,?,?,?)",
                               (delivery_id, scope, route, canonical(body).decode(), fingerprint))
        finally:
            db.close()
        return {"delivery_id": delivery_id, "acceptance": "process-restart",
                "delivery": "not-observed", "evidence": dict(EVIDENCE),
                "scope_ref": scope, "route": route, "correlation_id": body["correlation_id"]}

    def accept(self, scope_ref: str, route: str, delivery_id: str, completion: JSON) -> JSON:
        """CompletionDelivery: composition grants this port only to execution."""
        return self._enqueue(scope_ref, route, delivery_id, completion)

    def _poll(self, principal, scope, route):
        self._policy.route(scope, route, principal)
        db = self._connect()
        try:
            row = db.execute("SELECT * FROM messages WHERE scope=? AND route=? AND acknowledged=0 ORDER BY seq LIMIT 1", (scope, route)).fetchone()
            return None if row is None else {"scope_ref": scope, "route": route,
                                             "delivery_id": row["id"], "body": json.loads(row["body"]),
                                             "order": row["seq"], "delivery": "observed-unacknowledged"}
        finally:
            db.close()

    def _ack(self, principal, command, route, delivery_id):
        scope = command.scope_ref
        self._policy.route(scope, route, principal)
        key = canonical([principal, scope, command.idempotency_key]).decode()
        fingerprint = digest(canonical([route, delivery_id, command.intent_digest]))
        response = {"delivery_id": delivery_id, "delivery": "acknowledged",
                    "persistence": "process-restart", "evidence": dict(EVIDENCE),
                    "scope_ref": scope, "route": route}
        db = self._connect()
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute("SELECT * FROM acknowledgements WHERE identity=?", (key,)).fetchone()
                if old:
                    require(old["fingerprint"] == fingerprint, "CONFLICT")
                    return json.loads(old["response"])
                exists = db.execute("SELECT 1 FROM messages WHERE id=? AND scope=? AND route=?", (delivery_id, scope, route)).fetchone()
                require(exists is not None, "NOT_FOUND")
                db.execute("UPDATE messages SET acknowledged=1 WHERE id=?", (delivery_id,))
                db.execute("INSERT INTO acknowledgements VALUES(?,?,?)", (key, fingerprint, canonical(response).decode()))
        finally:
            db.close()
        return response


class MessagingSession:
    """Published Messaging port bound to trusted principal and delivery context."""
    def __init__(self, owner, policy, principal, atoms: AtomStorage, message_id):
        self._owner, self._policy, self._principal = owner, policy, principal
        self._atoms, self._message_id = atoms, message_id

    def send(self, command: Mutation, ref: AtomRef, route: str,
             correlation_id: str, reply_route: str) -> MessageAcceptance:
        scope = command.scope_ref
        self._policy.check(self._principal, scope, "agent.messaging.send")
        self._policy.route(scope, reply_route, self._principal)
        require(ref["scope_ref"] == scope, "UNAUTHORIZED")
        self._atoms.get(ref)
        identity = canonical([self._principal, scope, "agent.messaging", "send", command.idempotency_key]).decode()
        return self._owner._enqueue(scope, route, str(uuid.uuid5(uuid.NAMESPACE_URL, identity)),
            {"ref": ref, "correlation_id": correlation_id, "reply_route": reply_route,
             "causation_id": self._message_id}, command.intent_digest)

    def poll(self, scope_ref: str, route: str) -> MessageDelivery | None:
        self._policy.check(self._principal, scope_ref, "agent.messaging.poll")
        return self._owner._poll(self._principal, scope_ref, route)

    def ack(self, command: Mutation, route: str, delivery_id: str) -> MessageAck:
        self._policy.check(self._principal, command.scope_ref, "agent.messaging.ack")
        return self._owner._ack(self._principal, command, route, delivery_id)
