"""Independent AtomStorage CONTRACT TEST PROVIDER. No DA or chain integration.

Atomic files plus flock support the declared single-host process-restart profile.
This class has no AtomOwner inheritance, SQLite tables, or private owner helpers.
"""
import fcntl
import json
import os
from pathlib import Path
import tempfile
import uuid

from ..contracts import AtomRef, AtomWrite, JSON, ContractError, canonical, digest, require
from ..ports import AtomEnvelope, Mutation


class FileAtomFixture:
    def __init__(self, records: str, payloads: str):
        self._records, self._payloads = Path(records), Path(payloads)
        self._records.mkdir(parents=True, exist_ok=True)
        self._payloads.mkdir(parents=True, exist_ok=True)

    def __getattr__(self, name):
        if name in {"row", "db", "storage", "enqueue", "execute"}:
            raise AssertionError("Foreign implementation access: " + name)
        raise AttributeError(name)

    @staticmethod
    def _persist(path, data):
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def create(self, command: Mutation, content_type: str, data: bytes) -> AtomWrite:
        identity = digest(canonical([command.scope_ref, command.idempotency_key]))
        atom_id = str(uuid.uuid5(uuid.NAMESPACE_OID, identity))
        path = self._records / (atom_id + ".json")
        fingerprint = digest(canonical([content_type, digest(data), command.intent_digest]))
        with (self._records / ".lock").open("a+b") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ContractError("OVERLOADED") from None
            if path.exists():
                record = json.loads(path.read_bytes())
                require(record["fingerprint"] == fingerprint, "CONFLICT")
                return record["write"]
            write = {"ref": {"scope_ref": command.scope_ref, "id": atom_id,
                             "revision": 1, "digest": digest(data)},
                     "receipt": {"provider": "contract-fixture-files/1",
                                 "durability": "local-files-process-restart",
                                 "evidence": {"classification": "contract-test-provider",
                                              "persistence": "fsync-atomic-files"}}}
            self._persist(self._payloads / atom_id, data)
            self._persist(path, canonical({"write": write, "fingerprint": fingerprint,
                                           "content_type": content_type}))
            return write

    def _record(self, ref):
        # Public opaque IDs must never become caller-controlled filesystem paths.
        try:
            parsed = uuid.UUID(ref["id"])
        except (ValueError, TypeError, AttributeError):
            raise ContractError("NOT_FOUND") from None
        require(str(parsed) == ref["id"], "NOT_FOUND")
        path = self._records / (ref["id"] + ".json")
        require(path.exists(), "NOT_FOUND")
        record = json.loads(path.read_bytes())
        require(ref["scope_ref"] == record["write"]["ref"]["scope_ref"], "NOT_FOUND")
        require(ref == record["write"]["ref"], "CONFLICT")
        return record

    def get(self, ref: AtomRef) -> AtomEnvelope:
        record = self._record(ref)
        try:
            data = (self._payloads / ref["id"]).read_bytes()
        except FileNotFoundError:
            raise ContractError("NOT_AVAILABLE") from None
        require(digest(data) == ref["digest"], "NOT_AVAILABLE")
        return AtomEnvelope(ref, record["content_type"], data)

    def getMany(self, refs: tuple[AtomRef, ...]) -> tuple[AtomEnvelope, ...]:
        return tuple(self.get(ref) for ref in refs)

    def availability(self, ref: AtomRef) -> JSON:
        self._record(ref)
        # The common availability observation is independent of erasure coding.
        present = (self._payloads / ref["id"]).exists()
        if present:
            self.get(ref)
        return {"available": present, "present_shares": int(present), "threshold": 1,
                "bytes": None, "content_hash": ref["digest"]}
