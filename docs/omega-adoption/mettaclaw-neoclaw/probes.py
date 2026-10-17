"""Read-only source probes; all generated state lives in a temporary directory.

Usage: python3 probes.py SOURCE_ROOT OUTPUT_JSON
SOURCE_ROOT contains mettaclaw, petta_lib_chromadb, PeTTa and fusion checkouts.
No live channel, model, Chroma server, private memory or credential is used.
The Chroma double is explicitly a fixture, never provider conformance evidence.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types

sys.dont_write_bytecode = True
root = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2]).resolve()
results = []


def record(name, kind, detail):
    results.append(dict(name=name, evidence_class=kind, status="PASS", detail=detail))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


with tempfile.TemporaryDirectory(prefix="omega-mapping-probes-") as td:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run([sys.executable, str(root / "mettaclaw/src/helper.py")], cwd=td,
                       env=env, capture_output=True, text=True, timeout=20)
    assert p.returncode == 0, p.stderr
    record("upstream-helper-tests", "REAL_LOCAL_SQLITE_SYNTHETIC_INPUT", p.stdout.strip())
    helper = load("omega_helper_probe", root / "mettaclaw/src/helper.py")
    parsed = helper.balance_parentheses("\n".join("send x" for _ in range(6)))
    assert parsed.count('(send "x")') == 6
    unknown = helper.balance_parentheses("unknown-command input")
    assert "unknown-command" in unknown
    record("parser-is-not-an-allowlist-or-five-command-budget", "REAL_LOCAL_FUNCTION",
           {"six_commands": parsed, "unknown_command": unknown})
    irc = load("omega_irc_probe", root / "mettaclaw/channels/irc.py")
    irc._set_last("one")
    irc._set_last("two")
    assert irc.getLastMessage() == "one | two"
    assert irc.getLastMessage() == ""
    record("irc-read-consumes-volatile-buffer", "REAL_LOCAL_FUNCTION", "one | two; then empty; no socket opened")

    class Collection:
        def __init__(self):
            self.rows = {}
        def add(self, ids, documents, embeddings, metadatas):
            for i, d, e, m in zip(ids, documents, embeddings, metadatas):
                self.rows[i] = dict(document=d, embedding=e, metadata=dict(m))
        def get(self, ids=None, where=None, include=None):
            selected = [i for i in (ids or list(self.rows)) if i in self.rows]
            if where:
                selected = [i for i in selected if all(self.rows[i]["metadata"].get(k) == v for k, v in where.items())]
            return dict(ids=selected, documents=[self.rows[i]["document"] for i in selected],
                        metadatas=[dict(self.rows[i]["metadata"]) for i in selected])
        def update(self, ids, metadatas):
            for i, m in zip(ids, metadatas):
                self.rows[i]["metadata"] = dict(m)
        def delete(self, ids):
            for i in ids:
                self.rows.pop(i, None)

    collection = Collection()
    fixture = types.ModuleType("chromadb")
    fixture.PersistentClient = lambda **kw: types.SimpleNamespace(get_or_create_collection=lambda **k: collection)
    sys.modules["chromadb"] = fixture
    adapter = load("omega_chroma_fixture_probe", root / "petta_lib_chromadb/lib_chromadb.py")
    ident = adapter.remember("synthetic", [0.1, 0.2], "2000-01-01 00:00:00")
    adapter.link_episode(ident, "2000-01-01 00:00:01")
    adapter.link_episode(ident, "2000-01-01 00:00:01")
    assert adapter.query_linked_episodes(ident) == ["2000-01-01 00:00:01"]
    assert adapter.get_stv(ident) == [1.0, 0.5]
    adapter.forget_ids([ident])
    assert adapter.get_stv(ident) is None
    record("chroma-wrapper-link-dedup-and-missing-stv", "FIXTURE_BACKEND_REAL_WRAPPER",
           "One linked timestamp after two calls; deleted get_stv returns None. Does not validate Chroma SDK metadata acceptance or merge semantics.")
    source = (root / "mettaclaw/src/memory.metta").read_text()
    update = source[source.index('(= (update '):source.index('(= (tvUpdate ')]
    assert update.index('forget_ids') < update.index('get_stv')
    record("update-deletes-before-reading-old-truth", "STATIC_SOURCE_ASSERTION",
           "Full update execution unrun; source orders delete before old get_stv.")
    nal_input = Path(td) / "nal-probe.metta"
    nal_input.write_text('!(import! &self "' + str(root / "mettaclaw/lib_nal.metta") + '")\n'
                         '!(Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))\n'
                         '!(Truth_Revision (stv 1.0 0.5) (stv 0.0 0.5))\n'
                         '!(Truth_Revision (Truth_Revision (stv 1.0 0.5) (stv 1.0 0.5)) (stv 1.0 0.5))\n')
    cmd = ["swipl", "-q", "-s", str(root / "PeTTa/src/main.pl"), "--", str(nal_input), "--silent"]
    try:
        p = subprocess.run(cmd, cwd=td, env=env, capture_output=True, text=True, timeout=30)
        # Record output; no success inference from exit status alone.
        passed = p.returncode == 0 and "(stv 0.5 0.6666666666666666)" in p.stdout and "(stv 1.0 0.75)" in p.stdout
        results.append(dict(name="native-nal-isolated", evidence_class="REAL_NATIVE_SYNTHETIC_INPUT",
                            status="PASS" if passed else "EXECUTED_FAILURE", exit_code=p.returncode,
                            command=[s.replace(td, "<temporary-directory>") for s in cmd],
                            stdout=p.stdout.replace(td, "<temporary-directory>"), stderr=p.stderr.replace(td, "<temporary-directory>")))
    except subprocess.TimeoutExpired:
        results.append(dict(name="native-nal-isolated", evidence_class="REAL_NATIVE_SYNTHETIC_INPUT", status="TIMEOUT", seconds=30))

parsed_files = []
for repo in ("mettaclaw", "petta_lib_chromadb"):
    for path in sorted((root / repo).rglob("*.py")):
        ast.parse(path.read_text())
        parsed_files.append(str(path.relative_to(root)))
record("python-source-parse", "STATIC_SOURCE", parsed_files)
manifest = json.loads((root / "fusion/evidence/m5/final/verification.json").read_text())
mismatches = [p for p, h in manifest["source"]["files"].items()
              if hashlib.sha256((root / "fusion" / p).read_bytes()).hexdigest() != h]
assert not mismatches, mismatches
record("fusion-m5-evidence-hash-audit", "RECORDED_EVIDENCE_REVALIDATED_SOURCE",
       {"files": len(manifest["source"]["files"]), "tested_revision": manifest["source"]["commit"], "mismatches": mismatches,
        "runtime_gates_rerun": False})
out.write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps([{k: r[k] for k in ("name", "status")} for r in results], indent=2))
