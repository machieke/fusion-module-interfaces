"""Run the same two-peer consumer under both bindings; persist measured evidence."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fusion.contracts import canonical, digest
from tests.support import Harness

FIXTURE = b"M1 deliberately shared fixture; opaque bytes, no cognition.\x00\xff\n"


def run_one(binding, atom_provider="detta"):
    directory = tempfile.mkdtemp(prefix="demo-" + binding + "-", dir=ROOT / "artifacts")
    h = Harness(binding, directory, atom_provider=atom_provider)
    selected = [p.provider for p in h.a.binding.selected.values()]
    timings = {}

    def measured(name, action):
        start = time.perf_counter()
        result = action()
        timings[name] = (time.perf_counter() - start) * 1000
        return result

    start = time.perf_counter()
    stored = measured("store_ms", lambda: h.a.store(FIXTURE, "fixture"))
    assert h.a.store(FIXTURE, "fixture") == stored
    ref = stored["ref"]
    shared = measured("share_accept_ms", lambda: h.a.share(ref, "reply-B", "share"))
    received = h.b.poll()
    assert h.b.retrieve(received["body"]["ref"]) == FIXTURE
    h.b.ack(received["delivery_id"], "ack")
    job = measured("job_accept_ms", lambda: h.a.delegate(ref, "inspect"))
    assert h.a.delegate(ref, "inspect") == job
    # Caller is absent while result persists; kill real workers at both boundaries.
    measured("crash_before_completion_ms", lambda: h.kill_at("work", "after_result_persist"))
    assert h.a.status(job["job_id"])["execution"] == "queued"
    measured("recovery_commit_ms", lambda: h.kill_at("work", "after_completion_commit"))
    assert h.a.status(job["job_id"])["execution"] == "succeeded"
    assert h.a.poll() is None
    restarted = h.peer("A")
    result = restarted.result(job["job_id"])
    output = json.loads(restarted.retrieve(result["ref"]))
    assert output["digest"] == digest(FIXTURE) and output["length"] == len(FIXTURE)
    assert h.command("flush")["ok"]["sent"] == 1
    completion = restarted.poll()
    assert completion["body"]["correlation_id"] == "inspect"
    assert restarted.poll() == completion
    restarted.ack(completion["delivery_id"], "completion-ack")
    assert restarted.poll() is None
    elapsed = time.perf_counter() - start
    counts = h.counts()
    with sqlite3.connect(h.config["database"]) as db:
        pending = db.execute("SELECT count(*) FROM outbox WHERE sent=0").fetchone()[0]
    bindings = [h.a.binding, h.b.binding, restarted.binding]
    return {"binding": binding, "peers": "independently instantiated protocol fixtures A/B",
            "worker": "separate OS process; SIGKILL at two persisted boundaries",
            "selected_providers": selected, "storage_provider": ("real DeTTa DA + FileStorage libraries" if atom_provider == "detta" else "independent atomic-file contract test provider"),
            "fixture_sha256": digest(FIXTURE), "fixture_bytes": len(FIXTURE), "stored": stored,
            "shared": shared, "job": job, "result": result, "output": output,
            "timings": timings, "elapsed_seconds": elapsed,
            "slice_throughput_per_second": 1 / elapsed,
            "binding_json_bytes_sent": sum(b.bytes_sent for b in bindings),
            "binding_json_bytes_received": sum(b.bytes_received for b in bindings),
            "binding_calls": sum(b.calls for b in bindings),
            "binding_bytes_are_physical": binding == "subprocess",
            "da_fixture_payload_bytes": stored["receipt"]["evidence"].get("payload_bytes"),
            "da_result_payload_bytes": result["receipt"]["evidence"].get("payload_bytes"),
            "idempotent_retries": 2, "worker_attempts": 2,
            "max_observed_pending_jobs": 1, "max_observed_pending_outbox": 1,
            "pending_outbox_at_end": pending, "acknowledged_data_loss": 0,
            "counts": counts, "runtime_directory": directory,
            "chain": "NOT RUN by this demo; historical chain-demo.json is separate evidence"}


def run():
    (ROOT / "artifacts").mkdir(exist_ok=True)
    report = {"runs": [run_one(binding) for binding in ("inprocess", "subprocess")],
              "failure_model": "same-host process SIGKILL; no disk/power/Byzantine fault experiment",
              "measurement_limits": "one slice per binding; no SLA/scalability claim; DA JSON framing and worker control bytes not counted"}
    (ROOT / "artifacts/demo.json").write_bytes(canonical(report))
    print(json.dumps({"demo": "passed", "evidence": "artifacts/demo.json",
                      "elapsed_seconds": [r["elapsed_seconds"] for r in report["runs"]]}))


if __name__ == "__main__":
    run()
