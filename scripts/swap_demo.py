"""One unchanged workflow × two AtomStorage implementations × two bindings."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.demo import run_one


def run(fixture_only=False):
    providers = ("fixture-files",) if fixture_only else ("detta", "fixture-files")
    report = {"runs": [run_one(binding, provider) for provider in providers
                       for binding in ("inprocess", "subprocess")],
        "failure_model": "same-host SIGKILL; separate atom/mailbox/execution commits; no disk/power/Byzantine fault experiment",
        "classification": {"detta": "real DeTTa DA/FileStorage library integration; local 4+2 shares",
                           "fixture-files": "independent atomic-file AtomStorage test provider; no DA network",
                           "peers": "protocol fixtures", "worker": "real separate OS process, deterministic inspect_atom only",
                           "OMEGA": "BLOCKED: intended runtime source unavailable", "CHAIN": "NOT RUN"},
        "measurement_limits": "One slice per combination; no SLA/scalability claim. Binding counters exclude discovery, worker control and DA child framing; in-process bytes are serialized equivalents."}
    output = ROOT / "artifacts/m1_1"
    output.mkdir(parents=True, exist_ok=True)
    target = output / ("fixture-demo.json" if fixture_only else "swap-demo.json")
    target.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"demo": "PASS", "evidence": str(target),
                      "elapsed_seconds": [r["elapsed_seconds"] for r in report["runs"]]}))
    return report


if __name__ == "__main__":
    run("--fixture-only" in sys.argv)
