"""Build an adapter against an explicit local checkout; never edit upstream."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def build():
    repo = Path(os.environ.get("DETTA_REPO", ROOT.parent / "secured-contract-spaces")).resolve()
    build_dir = ROOT / "artifacts" / "detta-build"
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "src").mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "adapters/detta/src/main.rs", build_dir / "src/main.rs")
    manifest = '[package]\nname = "fusion-detta-adapter"\nversion = "0.1.0"\nedition = "2021"\n[dependencies]\n'
    for name in ("detta-da", "detta-storage"):
        manifest += f'{name} = {{ path = {json.dumps(str(repo / "crates" / name))} }}\n'
    manifest += 'serde = { version = "1.0", features = ["derive"] }\nserde_json = "1.0"\n'
    (build_dir / "Cargo.toml").write_text(manifest)
    lock = ROOT / "adapters/detta/Cargo.lock"
    if lock.exists():
        shutil.copyfile(lock, build_dir / "Cargo.lock")
    subprocess.run(["cargo", "build", "--offline", *( ["--locked"] if lock.exists() else []),
                    "--manifest-path", str(build_dir / "Cargo.toml")], check=True)
    shutil.copyfile(build_dir / "Cargo.lock", lock)
    return build_dir / "target/debug/fusion-detta-adapter"


if __name__ == "__main__":
    print(build())
