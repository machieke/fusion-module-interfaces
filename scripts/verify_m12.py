"""Execute the supported fresh-source gates; no chain fallback or cognitive work."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.preflight import preflight, sha


def main(environment):
    environment = environment.resolve()
    native = environment.parent / "venv/bin/python"
    env = dict(os.environ, **json.loads(environment.read_text()))
    # Do not let a copied environment file silently import another Fusion tree.
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env["HIVE_REPO"]])
    os.environ.update({k: env[k] for k in ("HIVE_REPO", "DETTA_REPO")})
    output = ROOT / "artifacts/m1_2"
    output.mkdir(parents=True, exist_ok=True)
    env["FUSION_HIVE_EVIDENCE"] = str(output)
    pins = json.loads((ROOT / "integration/hive/sources.json").read_text())
    manifest = preflight()
    (output / "preflight.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report = {"source": manifest["repository"], "commands": [],
              "native_build": json.loads((environment.parent / "build.json").read_text()),
              "source_pins": pins, "locks": {p: sha(ROOT / p) for p in
                  ("uv.lock", "adapters/detta/Cargo.lock", "integration/hive/requirements.lock",
                   "integration/hive/build-constraints.txt", "integration/hive/sources.json")},
              "cache": "Warm uv/Python/Cargo download caches allowed. No copied target, venv or native build. Empty-cache build NOT_RUN.",
              "gates": {name: "NOT_RUN" for name in ("FIXTURE_REPRO", "DETTA_REPRO", "HIVE_SOURCE", "HIVE_ENTRYPOINT",
                  "HIVE_DETTA", "HIVE_RECOVERY", "HIVE_REPRO", "CHAIN")}}
    target = output / "verification.json"

    def save():
        target.write_text(json.dumps(report, indent=2) + "\n")

    def execute(name, args, cwd=ROOT, override=None, junit=False):
        began = time.monotonic()
        command_env = dict(env, **(override or {}))
        run = subprocess.run(list(map(str, args)), cwd=cwd, env=command_env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True)
        log = output / (name + ".log")
        log.write_text(run.stdout)
        item = {"name": name, "command": list(map(str, args)), "cwd": str(cwd),
                "environment_overrides": override or {}, "returncode": run.returncode,
                "seconds": round(time.monotonic() - began, 3), "log": log.name, "sha256": sha(log)}
        if junit:
            xml = output / (name + ".xml")
            if xml.exists():
                suites = list(ET.parse(xml).getroot().iter("testsuite"))
                item["tests"] = {k: sum(int(s.get(k, 0)) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
        else:
            item["test_summaries"] = re.findall(r"(?:Ran \d+ tests? in [^\n]+|test result:[^\n]+)", run.stdout)
        report["commands"].append(item)
        save()
        print(name, "PASS" if run.returncode == 0 else "FAIL", item.get("tests", item.get("test_summaries")), flush=True)
        if run.returncode:
            report["failed_command"] = name
            failed_gate = {"fixture": "FIXTURE_REPRO", "detta": "DETTA_REPRO", "upstream-detta": "DETTA_REPRO",
                           "native-baseline": "HIVE_ENTRYPOINT", "hive-integration": "HIVE_RECOVERY"}[name]
            report["gates"][failed_gate] = "FAIL: " + name
            save()
            raise SystemExit(run.returncode)

    save()
    if report["native_build"]["requirements_sha256"] != report["locks"]["integration/hive/requirements.lock"]:
        report["gates"]["HIVE_REPRO"] = "BLOCKED: native dependency lock differs from build record"
        save()
        raise SystemExit(2)
    for name, var in (("omegahive", "HIVE_REPO"), ("secured-contract-spaces", "DETTA_REPO")):
        source = manifest["dependencies"][name]
        if source.get("commit") != pins["repositories"][name]["commit"] or source.get("worktree_status"):
            report["gates"]["HIVE_SOURCE" if name == "omegahive" else "DETTA_REPRO"] = "BLOCKED: exact clean source required"
            save()
            raise SystemExit(2)
    report["gates"]["HIVE_SOURCE"] = "PASS: verified native pin, not a dispatch pass"
    execute("fixture", ["uv", "run", "--python", "3.11", "--locked", "python", "scripts/verify_m11.py", "--fixture-only"],
            override={"DETTA_REPO": str(output / "absent-detta"), "HIVE_REPO": str(output / "absent-hive"), "PYTHONPATH": str(ROOT)})
    report["gates"]["FIXTURE_REPRO"] = "PASS"
    execute("detta", ["uv", "run", "--python", "3.11", "--locked", "python", "scripts/verify_m11.py"])
    execute("upstream-detta", ["cargo", "test", "--offline", "--locked", "-p", "detta-da", "-p", "detta-storage", "--lib"],
            cwd=env["DETTA_REPO"])
    report["gates"]["DETTA_REPRO"] = "PASS"
    native_tests = Path(env["HIVE_REPO"]) / "hive/tests"
    execute("native-baseline", [native, "-m", "pytest", "-q", *[native_tests / f for f in
        ("test_programs_api.py", "test_program_actions.py", "test_program_confirm.py")],
        "--junitxml=" + str(output / "native-baseline.xml")], junit=True)
    execute("hive-integration", [native, "-m", "pytest", "-q", "integration/hive/test_integration.py",
                                "--junitxml=" + str(output / "hive-integration.xml")], junit=True)
    for name in ("HIVE_ENTRYPOINT", "HIVE_DETTA", "HIVE_RECOVERY", "HIVE_REPRO"):
        report["gates"][name] = "PASS"
    report["gates"]["SCOPE"] = "M1.2 only; real native dispatch; generated input; fixture counterparty; no LLM invocation or chain"
    save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("environment", type=Path)
    main(parser.parse_args().environment)
