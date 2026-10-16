"""Atom metadata owner and trusted caller-bound facade for the AtomStorage port."""
import json
import sqlite3
import uuid
from dataclasses import replace

from .contracts import AtomRef, AtomWrite, JSON, Storage, ContractError, canonical, digest, require
from .ports import AtomEnvelope, AtomStorage, Mutation


class AtomOwner:
    """Real opaque-storage-backed implementation with an independent journal."""
    def __init__(self, database: str, storage: Storage):
        self._database, self._storage = database, storage
        db = self._connect()
        try:
            db.execute("""CREATE TABLE IF NOT EXISTS atoms (
              id TEXT PRIMARY KEY, scope TEXT NOT NULL, digest TEXT NOT NULL,
              content_type TEXT NOT NULL, payload_id TEXT NOT NULL, receipt TEXT NOT NULL,
              identity TEXT UNIQUE NOT NULL, fingerprint TEXT NOT NULL)""")
        finally:
            db.close()

    def _connect(self):
        db = sqlite3.connect(self._database, timeout=.2)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    @staticmethod
    def _write(row) -> AtomWrite:
        return {"ref": {"scope_ref": row["scope"], "id": row["id"], "revision": 1,
                        "digest": row["digest"]}, "receipt": json.loads(row["receipt"])}

    def create(self, command: Mutation, content_type: str, data: bytes) -> AtomWrite:
        identity = canonical([command.scope_ref, command.idempotency_key]).decode()
        fingerprint = digest(canonical([content_type, digest(data), command.intent_digest]))
        db = self._connect()
        try:
            with db:
                db.execute("BEGIN IMMEDIATE")
                old = db.execute("SELECT * FROM atoms WHERE identity=?", (identity,)).fetchone()
                if old:
                    require(old["fingerprint"] == fingerprint, "CONFLICT")
                    return self._write(old)
                atom_id = str(uuid.uuid5(uuid.NAMESPACE_URL, identity))
                payload_id, receipt = self._storage.put(command.scope_ref, identity, data)
                db.execute("INSERT INTO atoms VALUES(?,?,?,?,?,?,?,?)",
                           (atom_id, command.scope_ref, digest(data), content_type, payload_id,
                            canonical(receipt).decode(), identity, fingerprint))
                return {"ref": {"scope_ref": command.scope_ref, "id": atom_id, "revision": 1,
                                "digest": digest(data)}, "receipt": receipt}
        finally:
            db.close()

    def _row(self, ref):
        db = self._connect()
        try:
            row = db.execute("SELECT * FROM atoms WHERE id=? AND scope=?",
                             (ref["id"], ref["scope_ref"])).fetchone()
            require(row is not None, "NOT_FOUND")
            require(ref == self._write(row)["ref"], "CONFLICT")
            return row
        finally:
            db.close()

    def get(self, ref: AtomRef) -> AtomEnvelope:
        row = self._row(ref)
        try:
            data = self._storage.get(ref["scope_ref"], row["payload_id"])
        except ContractError as exc:
            if exc.code == "NOT_FOUND":
                raise ContractError("NOT_AVAILABLE") from None
            raise
        require(digest(data) == ref["digest"], "NOT_AVAILABLE")
        return AtomEnvelope(ref, row["content_type"], data)

    def getMany(self, refs: tuple[AtomRef, ...]) -> tuple[AtomEnvelope, ...]:
        return tuple(self.get(ref) for ref in refs)

    def availability(self, ref: AtomRef) -> JSON:
        row = self._row(ref)
        try:
            return self._storage.availability(ref["scope_ref"], row["payload_id"])
        except ContractError as exc:
            if exc.code == "NOT_FOUND":
                raise ContractError("NOT_AVAILABLE") from None
            raise


class AuthorizedAtoms:
    """Composition binds a principal; neither wire callers nor execution choose it."""
    def __init__(self, provider: AtomStorage, policy, principal: str, descriptor):
        self._provider, self._policy, self._principal = provider, policy, principal
        self._descriptor = descriptor

    def create(self, command: Mutation, content_type: str, data: bytes) -> AtomWrite:
        from .responses import atom_write
        self._policy.check(self._principal, command.scope_ref, "atom.storage.create")
        owned = replace(command, idempotency_key=digest(canonical(
            [self._principal, command.scope_ref, command.idempotency_key])))
        result = self._provider.create(owned, content_type, data)
        atom_write(result, command.scope_ref, self._descriptor)
        require(result["ref"]["digest"] == digest(data), "NOT_AVAILABLE")
        return result

    def get(self, ref: AtomRef) -> AtomEnvelope:
        from .responses import envelope
        self._policy.check(self._principal, ref["scope_ref"], "atom.storage.get")
        result = self._provider.get(ref)
        envelope(result, ref)
        return result

    def getMany(self, refs: tuple[AtomRef, ...]) -> tuple[AtomEnvelope, ...]:
        from .responses import envelope
        for ref in refs:
            self._policy.check(self._principal, ref["scope_ref"], "atom.storage.getMany")
            self._policy.check(self._principal, ref["scope_ref"], "atom.storage.get")
        result = self._provider.getMany(refs)
        require(isinstance(result, tuple) and len(result) == len(refs), "NOT_AVAILABLE")
        for item, ref in zip(result, refs):
            envelope(item, ref)
        return result

    def availability(self, ref: AtomRef) -> JSON:
        from .responses import availability
        self._policy.check(self._principal, ref["scope_ref"], "atom.storage.availability")
        self._policy.check(self._principal, ref["scope_ref"], "atom.storage.get")
        result = self._provider.availability(ref)
        availability(result)
        require(result["content_hash"] == ref["digest"], "NOT_AVAILABLE")
        return result
