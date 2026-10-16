"""Build inspected F1R3node with a staged protoc; no upstream source edits."""
import json
import os
from pathlib import Path
import subprocess
import sys
import argparse
import hashlib
import time


def pinned(destination):
    """Fresh source/object directory. Warm dependency download caches are allowed."""
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "integration/chain/sources.json").read_text())
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    repo = destination / "source"
    repo.mkdir()
    began = time.monotonic()
    def run(args, **kw):
        subprocess.run(args, check=True, **kw)
    run(["git", "init", "-q", str(repo)])
    run(["git", "-C", str(repo), "remote", "add", "origin", manifest["url"]])
    run(["git", "-C", str(repo), "fetch", "--depth", "1", "origin", manifest["commit"]])
    run(["git", "-C", str(repo), "checkout", "--detach", "FETCH_HEAD"])
    assert subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip() == manifest["commit"]
    assert not subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True).strip()
    # Locked fetch may use the network here, before the isolated runtime starts.
    run(["cargo", "fetch", "--locked"], cwd=repo)
    import grpc_tools
    from importlib.metadata import version
    wrapper = destination / "protoc"
    include = str(Path(grpc_tools.__path__[0]) / "_proto")
    wrapper.write_text(f'#!{sys.executable}\nimport sys\nfrom grpc_tools import protoc\n'
                       f'raise SystemExit(protoc.main(["protoc", "-I" + {include!r}, *sys.argv[1:]]))\n')
    wrapper.chmod(0o755)
    environment = {**os.environ, **manifest["environment"], "PROTOC": str(wrapper), "CARGO_TARGET_DIR": str(destination / "target")}
    with open(destination / "build.log", "w") as log:
        result = subprocess.run(["cargo", *manifest["cargo"]], cwd=repo, env=environment, stdout=log, stderr=subprocess.STDOUT)
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    binary = destination / "target/debug/node"
    report = {"source": manifest, "fresh_destination": True, "download_cache": "warm; locked fetch then offline build",
        "returncode": result.returncode, "seconds": round(time.monotonic() - began, 3),
        "files": {p: sha(repo / p) for p in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml", ".cargo/config.toml",
            "models/src/main/protobuf/CasperMessage.proto", "node/src/rust/api/web_api.rs", "node/src/rust/web/routes.rs")},
        "binary_sha256": sha(binary) if binary.is_file() else None, "recipe_sha256": sha(__file__),
        "grpcio-tools": version("grpcio-tools"), "protoc": subprocess.check_output([str(wrapper), "--version"], text=True).strip(),
        "rustc": subprocess.check_output(["rustc", "-Vv"], cwd=repo, text=True).strip(),
        "openssl": subprocess.check_output(["pkg-config", "--modversion", "openssl"], text=True).strip(),
        "submodules": subprocess.check_output(["git", "-C", str(repo), "submodule", "status"], text=True).strip()}
    (destination / "build.json").write_text(json.dumps(report, indent=2) + "\n")
    return result.returncode


def main():
    import grpc_tools
    from importlib.metadata import version
    root = Path(__file__).resolve().parents[1]
    repo = Path(os.environ.get("F1R3_REPO", "/home/purplezky/work/asi/f1r3node-rust"))
    wrapper = root / "artifacts/protoc"
    wrapper.parent.mkdir(exist_ok=True)
    include = str(Path(grpc_tools.__path__[0]) / "_proto")
    wrapper.write_text(f'#!{sys.executable}\nimport sys\nfrom grpc_tools import protoc\n'
                       f'raise SystemExit(protoc.main(["protoc", "-I" + {include!r}, *sys.argv[1:]]))\n')
    wrapper.chmod(0o755)
    command = ["cargo", "build", "--offline", "--locked", "-j", "2", "-p", "node", "--bin", "node"]
    with open(root / "artifacts/chain-build.log", "w") as log:
        result = subprocess.run(command, cwd=repo, env={**os.environ, "PROTOC": str(wrapper)},
                                stdout=log, stderr=subprocess.STDOUT)
    (root / "artifacts/chain-build.json").write_text(json.dumps({"command": command, "cwd": str(repo),
           "returncode": result.returncode, "grpcio-tools": version("grpcio-tools")}, indent=2))
    print(json.dumps({"chain_build_exit": result.returncode, "log": "artifacts/chain-build.log"}))
    return result.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", type=Path, help="fresh pinned M4 build; omitted retains historical workspace recipe")
    args = parser.parse_args()
    raise SystemExit(pinned(args.destination) if args.destination else main())
