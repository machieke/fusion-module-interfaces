"""Pinned Linux development build for the verified Programs seam; no upstream edits.

Downloads require authorized Git SSH access for Hive and DeTTa. Download caches
may be warm; native objects and venv live exclusively under the given directory.
This does not install the mind/LLM/chromadb smoke environment.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((ROOT / "integration/hive/sources.json").read_text())


def run(args, **kwargs):
    print("+", " ".join(map(str, args)), flush=True)
    return subprocess.run(list(map(str, args)), check=True, **kwargs)


def build(destination):
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError("build recipe requires an empty destination; existing work is never overwritten")
    started = time.monotonic()
    destination.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0",
               GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10")
    sources = destination / "sources"
    sources.mkdir(exist_ok=True)
    for name, pin in PINS["repositories"].items():
        path = sources / name
        if not path.exists():
            run(["git", "init", path], env=env)
            run(["git", "-C", path, "remote", "add", "origin", pin["url"]], env=env)
            run(["git", "-C", path, "fetch", "--depth", "1", "origin", pin["commit"]], env=env)
            run(["git", "-C", path, "checkout", "--detach", pin["commit"]], env=env)
        head = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
        dirty = subprocess.check_output(["git", "-C", str(path), "status", "--porcelain"], text=True)
        if head != pin["commit"] or dirty:
            raise RuntimeError(f"source mismatch/dirty checkout: {path}; refusing to reset it")
    swisrc = sources / "swipl"
    run(["git", "-C", swisrc, "submodule", "update", "--init", "--depth", "1",
         *["packages/" + m for m in PINS["swipl_modules"]]], env=env)
    venv = destination / "venv"
    run(["uv", "venv", "--python", PINS["python"], venv], env=env)
    python = venv / "bin/python"
    base = subprocess.check_output([str(python), "-c", "import sys; print(sys.base_prefix)"], text=True).strip()
    prefix, builddir = destination / "swipl", destination / "swipl-build"
    run(["cmake", "-S", swisrc, "-B", builddir, "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release",
         "-DSWIPL_PACKAGES_X=OFF", "-DSWIPL_PACKAGES_JAVA=OFF", "-DSWIPL_PACKAGES_ODBC=OFF",
         "-DSWIPL_PACKAGES_QT=OFF", "-DINSTALL_DOCUMENTATION=OFF", "-DBUILD_TESTING=OFF",
         f"-DCMAKE_INSTALL_PREFIX={prefix}", f"-DPython_EXECUTABLE={base}/bin/python3.12",
         f"-DPython_ROOT_DIR={base}", f"-DPython3_EXECUTABLE={base}/bin/python3.12",
         f"-DPython3_ROOT_DIR={base}"], env=env)
    # CMake 3.16 uses PATH/FILEPATH; newer CMake uses INTERNAL. Verify values,
    # not the cache type (the upstream setup script's INTERNAL-only guard fails).
    cache = dict(line.split("=", 1) for line in (builddir / "CMakeCache.txt").read_text().splitlines()
                 if "=" in line and not line.startswith(("#", "//")))
    for key in ("_Python_INCLUDE_DIR", "_Python_LIBRARY_RELEASE"):
        values = [v for k, v in cache.items() if k.split(":")[0] == key]
        if len(values) != 1 or not Path(values[0]).is_relative_to(base):
            raise RuntimeError(f"wrong Python build input: {key}: {values}")
    run(["ninja", "-C", builddir, "-j4"], env=env)
    if not (builddir / "packages/swipy/janus.so").exists():
        raise RuntimeError("native Janus was not built")
    run(["ninja", "-C", builddir, "install"], env=env)
    env.update(PATH=f"{prefix}/bin:{env['PATH']}", LD_LIBRARY_PATH=f"{base}/lib",
               PETTA_PATH=str(sources / "PeTTa"), HIVE_REPO=str(sources / "omegahive"),
               DETTA_REPO=str(sources / "secured-contract-spaces"),
               PYTHONPATH=os.pathsep.join([str(ROOT), str(sources / "omegahive")]))
    version = subprocess.check_output([str(prefix / "bin/swipl"), "--version"], text=True, env=env)
    if "version 10.1.14 " not in version:
        raise RuntimeError(version)
    bridge = subprocess.check_output([str(prefix / "bin/swipl"), "-g",
        "use_module(library(janus)), py_call(operator:add(20,22), V), print(V), nl, halt"], text=True, env=env)
    if bridge.strip() != "42":
        raise RuntimeError("Prolog-to-Python bridge failed")
    run(["uv", "pip", "sync", "--no-cache", "--python", python, "--require-hashes", "--no-binary", "janus-swi",
         "--build-constraints", ROOT / "integration/hive/build-constraints.txt",
         ROOT / "integration/hive/requirements.lock"], env=env)
    run([python, "-c", 'import janus_swi as j; assert j.query_once("X is 1+1")["X"] == 2'], env=env)
    checkdir = destination / "petta-check"
    checkdir.mkdir(exist_ok=True)
    check = checkdir / "check.metta"
    check.write_text("(= (f $x) (+ $x 1))\n!(f 41)\n")
    petta = subprocess.check_output(["sh", str(sources / "PeTTa/run.sh"), str(check)],
                                    cwd=checkdir, env=env, text=True)
    if re.sub(r"\x1b\[[0-9;]*m", "", petta).strip().splitlines()[-1] != "42":
        raise RuntimeError("PeTTa did not evaluate the generated expression to 42")
    print("SWI 10.1.14, both Janus bridges, PeTTa generated expression: PASS", flush=True)
    # Only explicit non-secret runtime variables, never the inherited environment.
    keys = ("PATH", "LD_LIBRARY_PATH", "PETTA_PATH", "HIVE_REPO", "DETTA_REPO", "PYTHONPATH")
    (destination / "environment.json").write_text(json.dumps({k: env[k] for k in keys}, indent=2) + "\n")
    (destination / "build.json").write_text(json.dumps({"fresh_destination": True,
        "fusion_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
        "source_pins": PINS, "seconds": round(time.monotonic() - started, 3),
        "checks": {"swipl": "10.1.14", "prolog_to_python": 42, "python_to_prolog": 2, "petta": 42},
        "tools": {name: subprocess.check_output(args, text=True).strip() for name, args in
                  {"cmake": ["cmake", "--version"], "ninja": ["ninja", "--version"],
                   "cc": ["cc", "--version"], "uv": ["uv", "--version"], "python": [str(python), "--version"]}.items()},
        "requirements_sha256": hashlib.sha256((ROOT / "integration/hive/requirements.lock").read_bytes()).hexdigest(),
        "cache": "Python interpreter download cache permitted. uv pip sync --no-cache rebuilds Janus against this prefix. All native objects/venv fresh; global empty-cache build not tested."}, indent=2) + "\n")
    return env, python


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    build(parser.parse_args().destination)
