"""Real native Programs route + clean real DeTTa; fixture counterparty only.

Run explicitly with the pinned native environment. Missing prerequisites are
errors, not silent fixture fallback or skipped real gates.
"""
import json
import os
from pathlib import Path
import selectors
import signal
import sqlite3
import subprocess
import sys
import time

import pytest

from fusion.contracts import canonical
from fusion.registry import descriptor_wire
from tests.support import Harness

ROOT = Path(__file__).resolve().parents[2]


class Caller:
    def __init__(self, root, config):
        self.root, self.config = root, config
        self.process = None

    def start(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("HIVE_")}
        env.update(HIVE_PLUGIN_DIRS=str(ROOT / "integration/hive/program"), FUSION_HIVE_CONFIG=str(self.config),
                   HIVE_OFFLINE="1", HIVE_DATA_DIR=str(self.root / "hive"))
        self.log = open(self.root / "native.log", "a")
        self.process = subprocess.Popen([sys.executable, str(ROOT / "integration/hive/native_caller.py"),
                                        str(self.root / "hive")], cwd=ROOT, env=env,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                       text=True, start_new_session=True)
        assert self.read() == {"ready": True}, (self.root / "native.log").read_text()
        return self

    def send(self, method, path, body=None):
        self.process.stdin.write(json.dumps({"method": method, "path": path, "body": body}) + "\n")
        self.process.stdin.flush()

    def read(self):
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            assert selector.select(60), "native caller timed out; see native.log"
        line = self.process.stdout.readline()
        assert line, (self.root / "native.log").read_text()
        return json.loads(line)

    def call(self, method, path, body=None):
        self.send(method, path, body)
        return self.read()

    def kill(self):
        if self.process is not None:
            # Also stop the actual PeTTa subprocess; a caller kill leaves no orphan.
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait(timeout=10)
            self.process.stdin.close()
            self.process.stdout.close()
            self.log.close()
            self.process = None


@pytest.fixture
def setup(tmp_path, request):
    h = Harness(root=tmp_path / "fusion", atom_provider="detta")
    config = {"service_config": str(h.path), "receipts": str(tmp_path / "receipts.db"),
              "descriptors": [descriptor_wire(d) for d in h.a.binding.selected.values()], "grants": []}
    path = tmp_path / "caller.json"
    path.write_bytes(canonical(config))
    path.chmod(0o600)
    caller = Caller(tmp_path, path).start()
    request.addfinalizer(caller.kill)
    request.addfinalizer(h.close)
    swarm = caller.call("POST", "/api/swarms", {"name": "Generated M1.2 integration"})["body"]["id"]
    config["grants"] = [{"principal": "user:operator", "swarm": swarm, "credential": h.a.binding.credential,
                         "scope": "shared-test", "reply_route": "reply-A", "counterparty": "reply-B"}]
    path.write_bytes(canonical(config))
    body = {"swarm_id": swarm, "action": "inspect", "items": [], "params": {"seed": 12},
            "idempotency_key": "generated-intent-12"}
    detail = caller.call("GET", "/api/programs/fusion-inspect")
    assert detail["code"] == 200 and detail["body"]["source"] == "plugin-dir", detail
    yield h, caller, config, path, body


def act(caller, body):
    response = caller.call("POST", "/api/programs/fusion-inspect/act", body)
    assert response["code"] == 200, response
    return response["body"]


def journal(config):
    with sqlite3.connect(config["receipts"]) as db:
        return db.execute("SELECT record,outcome,acknowledged FROM receipts").fetchall()


def job_count(h):
    path = Path(h.config["database"])
    if not path.exists():
        return 0  # Descriptor/native rejection may happen before any owner opens.
    with sqlite3.connect(path) as db:
        return db.execute("SELECT count(*) FROM jobs").fetchone()[0]


def complete(h, caller, body):
    assert h.command("work")["ok"]["worked"]
    assert h.command("flush")["ok"] == {"sent": 1, "pending": 0}
    result = act(caller, body)
    assert result["status"] == "done", result
    assert result["detail"]["input"]["receipt"]["provider"] == "detta-local-rs/1"
    assert result["detail"]["result"]["receipt"]["provider"] == "detta-local-rs/1"
    return result


def test_native_dispatch_real_detta_trace_and_replay(setup):
    h, caller, config, path, body = setup
    queued = act(caller, body)
    assert queued["status"] == "started", queued
    shared = h.b.poll()  # Explicit fixture counterparty, real mailbox/AtomStorage.
    assert shared["body"]["ref"] == queued["detail"]["input"]["ref"]
    assert b"explicitly shareable generated sample 12" in h.b.retrieve(shared["body"]["ref"])
    result = complete(h, caller, body)
    assert act(caller, body) == result
    caller.kill()
    caller.start()
    assert act(caller, body) == result
    assert h.a.poll() is None
    assert h.counts() == {"jobs": 1, "outbox": 1, "messages": 2, "atoms": 2}
    assert len(journal(config)) == 1 and journal(config)[0][2] == 1
    # Generated trace excludes credentials and machine-local configuration paths.
    trace = json.loads(canonical(result))
    trace["detail"]["caller"].pop("service_config")
    output = Path(os.environ.get("FUSION_HIVE_EVIDENCE", ROOT / "artifacts/m1_2"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "hive-trace.json").write_bytes(canonical(trace) + b"\n")


@pytest.mark.parametrize("stage", ["after_admission", "after_submission", "after_acceptance"])
def test_actual_caller_sigkill_recovery(setup, stage):
    h, caller, config, path, body = setup
    if stage == "after_acceptance":
        assert act(caller, body)["status"] == "started"
        h.command("work")
        h.command("flush")
    marker = caller.root / "caller-stop"
    config.update(test_pause_at=stage, test_marker=str(marker))
    path.write_bytes(canonical(config))
    caller.send("POST", "/api/programs/fusion-inspect/act", body)
    deadline = time.monotonic() + 30
    while not marker.exists() and caller.process.poll() is None and time.monotonic() < deadline:
        time.sleep(.01)
    assert marker.exists(), (caller.root / "native.log").read_text()
    caller.kill()
    before = journal(config)
    assert h.counts()["jobs"] == 1
    if stage == "after_acceptance":
        assert before[0][1] is not None and before[0][2] == 0
        unacked = h.a.poll()
        assert unacked is not None
    config.pop("test_pause_at")
    path.write_bytes(canonical(config))
    caller.start()
    if stage == "after_acceptance":
        result = act(caller, body)
        assert result["detail"] == json.loads(before[0][1])
    else:
        replay = act(caller, body)
        assert replay["status"] == "started", replay
        result = complete(h, caller, body)
    assert result["status"] == "done", result
    assert act(caller, body) == result
    assert h.a.poll() is None
    assert len(journal(config)) == 1 and journal(config)[0][2] == 1
    assert h.counts() == {"jobs": 1, "outbox": 1, "messages": 2, "atoms": 2}


def test_worker_sigkill_independent_result_commit(setup):
    h, caller, config, path, body = setup
    admitted = act(caller, body)
    job = admitted["detail"]["job"]["job_id"]
    h.kill_at("work", "after_result_persist")
    assert h.counts() == {"jobs": 1, "outbox": 0, "messages": 1, "atoms": 2}
    assert h.a.status(job)["execution"] == "queued"
    caller.kill()
    caller.start()
    assert act(caller, body)["status"] == "started"
    result = complete(h, caller, body)
    assert result["detail"]["job"]["job_id"] == job
    assert h.counts()["atoms"] == 2


def test_full_reply_route_retains_outbox(setup):
    h, caller, config, path, body = setup
    h.config["capacity"] = 1
    h.save()
    admitted = act(caller, body)
    h.b.share(admitted["detail"]["input"]["ref"], "reply-A", "fixture-fill")
    h.command("work")
    assert h.command("flush")["ok"] == {"sent": 0, "pending": 1}
    refused = act(caller, body)
    assert refused["detail"]["error"]["code"] == "NOT_AVAILABLE"
    assert journal(config)[0][1] is None
    blocker = h.a.poll()
    h.a.ack(blocker["delivery_id"], "fixture-drain")
    assert h.command("flush")["ok"] == {"sent": 1, "pending": 0}
    assert act(caller, body)["status"] == "done"


def test_worker_revocation_becomes_explicit_failed_completion(setup):
    h, caller, config, path, body = setup
    assert act(caller, body)["status"] == "started"
    h.config["principals"]["worker"]["scopes"]["shared-test"].remove("atom.storage.create")
    h.save()
    assert h.command("work")["ok"]["execution"] == "failed"
    assert h.command("flush")["ok"]["sent"] == 1
    result = act(caller, body)
    assert result["status"] == "error" and result["detail"]["error"] == "UNAUTHORIZED"
    assert result["detail"]["result"] is None and result["detail"]["output"] is None
    assert act(caller, body) == result
    assert h.counts()["atoms"] == 1 and journal(config)[0][2] == 1


@pytest.mark.parametrize("failure", ["wrong-scope", "revoked", "profile", "provider", "identity", "changed-input"])
def test_native_path_fails_closed(setup, failure):
    h, caller, config, path, body = setup
    expected = "UNAUTHORIZED"
    if failure in {"revoked", "changed-input"}:
        assert act(caller, body)["status"] == "started"
        if failure == "revoked":
            complete(h, caller, body)
            h.config["principals"]["A"]["scopes"] = {}
            h.save()
        else:
            body["params"]["seed"] = 13
            expected = "CONFLICT"
    elif failure == "wrong-scope":
        config["grants"][0]["scope"] = "elsewhere"
    elif failure == "profile":
        config["descriptors"][0]["profiles"] = ["unavailable/1"]
        expected = "UNSUPPORTED_PROFILE"
    elif failure == "provider":
        config["descriptors"][0]["implementation_version"] = "9.0.0"
        expected = "UNSUPPORTED_PROFILE"
    elif failure == "identity":
        body["params"]["principal"] = "user:operator"
        response = caller.call("POST", "/api/programs/fusion-inspect/act", body)
        assert response["code"] == 400 and response["body"]["error"]["code"] == "identity_in_request", response
        assert job_count(h) == 0
        return
    path.write_bytes(canonical(config))
    response = act(caller, body)
    assert response["status"] == "refused" and response["detail"]["error"]["code"] == expected, response
    assert job_count(h) == (1 if failure in {"revoked", "changed-input"} else 0)
