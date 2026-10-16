"""Build inspected F1R3node with a staged protoc; no upstream source edits."""
import json
import os
from pathlib import Path
import subprocess
import sys


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
    raise SystemExit(main())
