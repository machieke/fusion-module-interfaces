"""Identify available bytes/prerequisites; fingerprints are never source archives."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.discovery import collect, git, REPOSITORIES

INITIAL_COMMIT = "6d879650f56046925f85f034d5fb9eda54cd16e1"
BASELINE = ROOT / "docs/module-interfaces/evidence/m1_1/baseline"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def command(args, cwd=None):
    try:
        run = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=20)
        return {"command": args, "returncode": run.returncode, "output": (run.stdout+run.stderr).strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": args, "returncode": None, "output": type(exc).__name__}


def preflight():
    sources = collect()
    baseline = json.loads((BASELINE / "discovery.json").read_text())
    matches = {name: all(value.get(k) == baseline["sources"].get(name, {}).get(k)
                        for k in ("commit", "tracked_diff_sha256", "source_sha256", "worktree_status"))
               for name, value in sources["sources"].items()}
    files = git(ROOT, "ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
    code = {rel: sha(ROOT / rel) for rel in files if rel and Path(rel).parts[0] in
            {"fusion", "scripts", "tests", "contracts", "adapters"} and (ROOT / rel).is_file()}
    tools = {name: command(args) for name, args in {
        "python": [sys.executable, "--version"], "uv": ["uv", "--version"],
        "cargo": ["cargo", "--version"], "rustc": ["rustc", "--version"],
        "installed_rust": ["rustup", "toolchain", "list"]}.items()}
    chain_toolchain = REPOSITORIES["f1r3node-rust"] / "rust-toolchain.toml"
    if chain_toolchain.is_file():
        channel = tomllib.loads(chain_toolchain.read_text())["toolchain"]["channel"]
        tools["chain_rustc"] = (command(["rustc", "+"+channel, "--version"])
            if channel in tools["installed_rust"]["output"] else {"required": channel, "status": "MISSING"})
    detta = REPOSITORIES["secured-contract-spaces"]
    missing = [str(detta / p) for p in ("crates/detta-da/Cargo.toml", "crates/detta-storage/Cargo.toml")
               if not (detta / p).is_file()]
    if tools["cargo"]["returncode"] != 0: missing.append("cargo in PATH")
    dependencies = {}
    for name, source in sources["sources"].items():
        path = Path(source["path"])
        dependencies[name] = {**source, "matches_initial_baseline": matches[name],
            "additional_build_sha256": {p: sha(path / p) for p in ("Cargo.lock", "rust-toolchain.toml", "rust-toolchain") if (path / p).is_file()},
            "obtainability": "working-tree-only; patches are not supplied" if source.get("worktree_status") else "commit recorded; remote retrieval not tested"}
    omega = ROOT.parent / "omegahive"
    intended = omega / "hive"
    report = {"recorded_utc": datetime.now(timezone.utc).isoformat(),
        "repository": {"path": str(ROOT), "initial_commit": INITIAL_COMMIT,
            "initial_worktree_status": ["?? codex_fusion_m1_1_module_swap_and_omega_seam.md"],
            "head": git(ROOT, "rev-parse", "HEAD").decode().strip(),
            "current_worktree_status": git(ROOT, "status", "--short").decode().splitlines(),
            "brief_sha256": sha(ROOT / "codex_fusion_m1_1_module_swap_and_omega_seam.md"),
            "implementation_sha256": code, "lock_sha256": sha(ROOT / "uv.lock")},
        "platform": sources["platform"], "tools": tools, "dependencies": dependencies,
        "gates": {
            "fixture_prerequisites": {"status": "AVAILABLE", "command": "uv run --python 3.11 python scripts/verify_m11.py --fixture-only"},
            "real_detta_prerequisites": {"status": "BLOCKED" if missing else "AVAILABLE_NOT_YET_TESTED",
                "missing": missing, "command": "uv run --python 3.11 python scripts/verify_m11.py",
                "cache_requirement": "cargo build --offline --locked must succeed; no fixture substitution"},
            "clean_checkout_reproduction": {"status": "BLOCKED", "reason": "Recorded DeTTa/F1R3 working-tree changes are not supplied by this repository. Obtain authorized exact working bytes/patches, or validate a new immutable source; HEAD alone is insufficient."},
            "OMEGA": {"status": "BLOCKED", "expected_repository": "PhysixSNET/omegahive", "expected_path": str(omega),
                "path_exists": omega.exists(), "hive_directory_exists": intended.is_dir(), "verified_entrypoint": None,
                "verified_runtime_command": None, "reason": "No verified intended runtime source/revision. Onboarding and hive-appliance are not that runtime."},
            "CHAIN": {"status": "NOT_RUN", "command": "See docs/module-interfaces/runbook.md optional isolated chain commands; fixtures do not pass this gate."}},
        "limits": "Metadata/hashes only; no upstream modifications, source contents, credentials or private data copied. Byte identity does not establish source availability or production guarantees."}
    output = ROOT / "artifacts/m1_1"
    output.mkdir(parents=True, exist_ok=True)
    (output / "preflight.json").write_text(json.dumps(report, indent=2)+"\n")
    return report


if __name__ == "__main__":
    report = preflight()
    print(json.dumps({"manifest": "artifacts/m1_1/preflight.json", "gates": report["gates"]}, indent=2))
    raise SystemExit(2 if report["gates"]["real_detta_prerequisites"]["status"] == "BLOCKED" else 0)
