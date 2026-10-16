"""M1.1 local gate; fixture-only runs cannot pass real DeTTa, Omega or chain."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.preflight import preflight
from scripts.swap_demo import run

FIXTURE_TESTS = ["tests.test_contract.FixtureInProcessContract", "tests.test_contract.FixtureSubprocessContract",
    "tests.test_contract.Compatibility", "tests.test_m11.FixtureInProcessRecovery", "tests.test_m11.FixtureSubprocessRecovery",
    "tests.test_m11.PortStructure", "tests.test_responses", "tests.test_adapters.ChainObservationTests"]


def main():
    os.chdir(ROOT)
    fixture_only = "--fixture-only" in sys.argv
    manifest = preflight()
    output = ROOT / "artifacts/m1_1"
    if fixture_only:
        (output / "fixture-preflight.json").write_text(json.dumps(manifest, indent=2)+"\n")
    report = {"classification": "fixture/pure only" if fixture_only else "real DeTTa + independent fixture + transport tests",
              "OMEGA": "BLOCKED", "CHAIN": "NOT RUN", "commands": []}
    target = output / ("fixture-verification.json" if fixture_only else "verification.json")
    def execute(args, name):
        started = time.monotonic()
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        (output / (name+".log")).write_text(result.stdout)
        counts = re.search(r"Ran (\d+) tests? in", result.stdout)
        report["commands"].append({"command": args, "returncode": result.returncode,
            "elapsed_seconds": time.monotonic()-started, "tests": int(counts[1]) if counts else None,
            "log": name+".log"})
        target.write_text(json.dumps(report, indent=2)+"\n")
        print(result.stdout)
        return result.returncode
    if not fixture_only:
        if manifest["gates"]["real_detta_prerequisites"]["status"] == "BLOCKED":
            report["status"] = "BLOCKED: missing real DeTTa prerequisites; see preflight.json"
            target.write_text(json.dumps(report, indent=2)+"\n")
            return 2
        code = execute([sys.executable, "scripts/build_detta.py"], "build-detta")
        if code: return code
    args = [sys.executable, "-m", "unittest"]
    args += ["-v", *FIXTURE_TESTS] if fixture_only else ["discover", "-s", "tests", "-v"]
    code = execute(args, "fixture-tests" if fixture_only else "tests")
    if code: return code
    started = time.monotonic()
    demo = run(fixture_only)
    report["demo"] = {"runs": len(demo["runs"]), "elapsed_seconds": time.monotonic()-started, "status": "PASS"}
    report["status"] = "PASS (local selected gates only)"
    target.write_text(json.dumps(report, indent=2)+"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
