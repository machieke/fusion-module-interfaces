"""Extend the existing M3 provider recipe with optional pinned chain dependencies."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, str(ROOT / "scripts/build_m3.py"), str(destination / "providers")], check=True)
    env = json.loads((destination / "providers/environment.json").read_text())
    python = str(Path(env["VIRTUAL_ENV"]) / "bin/python")
    subprocess.run(["uv", "pip", "install", "--python", python, "-r", str(ROOT / "integration/chain/requirements.lock")], check=True)
    subprocess.run([python, str(ROOT / "scripts/build_chain.py"), str(destination / "chain")], check=True)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    raise SystemExit(build(parser.parse_args().destination))
