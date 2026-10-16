import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import time

from fusion.bindings import InProcess, Subprocess
from fusion.client import Peer
from fusion.composition import service
from fusion.contracts import canonical, OPERATIONS

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "artifacts/detta-build/target/debug/fusion-detta-adapter"


class Harness:
    def __init__(self, binding="subprocess", root=None, capacity=8, atom_provider="detta"):
        self.temp = tempfile.TemporaryDirectory(prefix="fusion-m1-") if root is None else None
        self.root = Path(self.temp.name if self.temp else root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        self.path = self.root / "config.json"
        all_methods = [f"{name}.{op}" for name, ops in OPERATIONS.items() for op in sorted(ops)]
        self.config = {"database": str(self.root / "journal.db"), "da_root": str(self.root / "da"),
                       "atoms_database": str(self.root / "atoms.db"), "messages_database": str(self.root / "mailbox.db"),
                       "atom_records": str(self.root / "records"), "atom_provider": atom_provider,
                       "detta_binary": str(BINARY), "capacity": capacity, "test_failpoints": True,
                       "failpoint_marker": str(self.root / "failpoint"), "principals": {},
                       "routes": {f"reply-{p}": {"scope": "shared-test", "owner": p} for p in ("A", "B")}}
        for name in ("A", "B", "outsider", "worker"):
            self.config["principals"][name] = {"credential": secrets.token_hex(24),
                "scopes": {"elsewhere" if name == "outsider" else "shared-test": all_methods if name != "worker" else
                           ["atom.storage.get", "atom.storage.create"]}}
        self.save()
        self.binding = binding
        self.a, self.b, self.outsider = (self.peer(p) for p in ("A", "B", "outsider"))

    def save(self):
        self.path.write_bytes(canonical(self.config))
        self.path.chmod(0o600)

    def peer(self, principal):
        credential = self.config["principals"][principal]["credential"]
        binding = (InProcess(lambda: service(self.path), credential) if self.binding == "inprocess"
                   else Subprocess(self.path, credential))
        return Peer(binding, "shared-test", f"reply-{principal}")

    def command(self, mode):
        run = subprocess.run([sys.executable, "-m", "fusion.host", mode, str(self.path)],
                             capture_output=True, check=True, timeout=30)
        return json.loads(run.stdout)

    def kill_at(self, mode, stage, request=None):
        marker = Path(self.config["failpoint_marker"])
        marker.unlink(missing_ok=True)
        process = subprocess.Popen([sys.executable, "-m", "fusion.host", mode, str(self.path), "--pause-at", stage],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            if request is not None:
                process.stdin.write(canonical({"credential": self.config["principals"]["A"]["credential"], "request": request}))
            process.stdin.close()
            deadline = time.monotonic() + 20
            while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                time.sleep(.01)
            if not marker.exists():
                raise AssertionError(f"failpoint {stage} not reached, exit={process.poll()}")
            process.kill()
            process.wait(timeout=5)
            assert process.returncode == -9
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()
            process.stderr.close()

    def close(self):
        if self.temp:
            self.temp.cleanup()

    def counts(self):
        with sqlite3.connect(self.config["database"]) as db:
            counts = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("jobs", "outbox")}
            assert db.execute("SELECT name FROM sqlite_master WHERE name IN ('atoms','messages')").fetchall() == []
        with sqlite3.connect(self.config["messages_database"]) as db:
            counts["messages"] = db.execute("SELECT count(*) FROM messages").fetchone()[0]
        if self.config["atom_provider"] == "detta":
            with sqlite3.connect(self.config["atoms_database"]) as db:
                counts["atoms"] = db.execute("SELECT count(*) FROM atoms").fetchone()[0]
        else:
            counts["atoms"] = len(list(Path(self.config["atom_records"]).glob("*.json")))
        return counts
