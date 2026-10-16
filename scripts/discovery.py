"""Record source identity without copying source changes or private data."""
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPOSITORIES = {
    "omegahive-start-here": ROOT.parent / "omegahive-start-here",
    "metta-attention": ROOT.parent / "metta-attention",
    "das": Path.home() / "work/asi/das",
    "mettaclaw": ROOT.parent / "mettaclaw",
    "reachability-atomspace-prototype": ROOT.parent / "reachability-atomspace-prototype",
    "secured-contract-spaces": ROOT.parent / "secured-contract-spaces",
    "f1r3node-rust": Path.home() / "work/asi/f1r3node-rust",
    "freeciv-omegaclaw": ROOT.parent / "freeciv-omegaclaw",
    "omega-shared-memory-pilot-archive": ROOT.parent / "omega-shared-memory-pilot-archive",
}


def git(path, *arguments):
    return subprocess.check_output(["git", "-C", str(path), *arguments], stderr=subprocess.DEVNULL)


def collect():
    records = {}
    for name, path in REPOSITORIES.items():
        if not path.exists():
            records[name] = {"path": str(path), "accessible": False}
            continue
        tracked = git(path, "ls-files", "--cached", "--others", "--exclude-standard", "-z").decode().split("\0")
        hashes = {}
        # Source fingerprints include dirty working files actually used; no file contents are copied.
        for rel in tracked:
            file = path / rel
            excluded = {"memory", "data", "profile", "repos", "artifacts", "proofshot-artifacts",
                        "node_modules", "target", "__pycache__", "build"}
            if any(part in excluded or part.startswith(".") for part in Path(rel).parts):
                continue
            if file.is_file() and file.suffix in {".rs", ".toml", ".proto", ".py", ".metta", ".rho", ".conf"}:
                hashes[rel] = hashlib.sha256(file.read_bytes()).hexdigest()
        records[name] = {"path": str(path), "accessible": True,
                         "commit": git(path, "rev-parse", "HEAD").decode().strip(),
                         "remotes": git(path, "remote", "-v").decode().splitlines(),
                         "worktree_status": git(path, "status", "--short").decode().splitlines(),
                         "tracked_diff_sha256": hashlib.sha256(git(path, "diff", "HEAD", "--binary")).hexdigest(),
                         "source_sha256": hashes}
    report = {"python": sys.version, "platform": platform.platform(), "sources": records}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/discovery.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    collect()
    print("Source fingerprints written to artifacts/discovery.json")
