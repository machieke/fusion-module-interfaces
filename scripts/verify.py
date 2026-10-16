"""Reproducible M0/M1 independent gate. Chain is an explicit optional local gate."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_detta import build
from scripts.discovery import collect
from scripts.demo import run


def main():
    os.chdir(ROOT)
    collect()
    build()
    started = time.monotonic()
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (ROOT / "artifacts/tests.log").write_text(result.stdout)
    print(result.stdout)
    (ROOT / "artifacts/verification.json").write_text(json.dumps({"command": command,
       "returncode": result.returncode, "elapsed_seconds": time.monotonic() - started}, indent=2))
    if result.returncode:
        return result.returncode
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
