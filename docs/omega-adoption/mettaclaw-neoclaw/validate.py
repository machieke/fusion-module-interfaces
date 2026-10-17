"""Validate this review packet against its pinned, fresh inspection sources.

Read-only except for validation-results.json in this review directory. It does not
start providers, change source checkouts, inspect private state, or exercise a new
interface. Run from any working directory after restoring source-state.json pins.
"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
results = []


def read(name):
    return json.loads((HERE / name).read_text())


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def checked(name, detail):
    results.append(dict(check=name, status='PASS', detail=detail))


state = read('source-state.json')
sources = {r['repository']: r for r in state['sources']}
hashes = 0
for source in sources.values():
    path = ROOT / source['inspection_path']
    assert git(path, 'rev-parse', 'HEAD') == source['commit']
    assert git(path, 'status', '--porcelain').splitlines() == source['worktree_status'] == []
    for filename, expected in source['sha256'].items():
        assert hashlib.sha256((path / filename).read_bytes()).hexdigest() == expected, filename
        hashes += 1
checked('source-pins-cleanliness-and-file-hashes', dict(repositories=len(sources), hashes=hashes))

ledger = read('mapping-ledger.json')['rows']
index = read('symbol-index.json')['definitions']
coverage = read('coverage.json')
allowed = {'DIRECT_FIT', 'ADAPTER_FIT', 'SPLIT_REQUIRED', 'PROFILE_REQUIRED',
           'INTERFACE_GAP', 'NOT_A_MODULE', 'UNASSESSED'}
assert len({r['component_id'] for r in ledger}) == len(ledger) == coverage['semantic_components']
counts = {k: sum(r['classification'] == k for r in ledger) for k in sorted(allowed)}
assert counts == coverage['by_classification']
by_id = {r['component_id']: r for r in ledger}
for row in ledger:
    assert row['classification'] in allowed
    source = row['source']
    repo = sources[source['repository']]
    assert source['commit'] == repo['commit']
    assert source['symbols'] and row['current_behavior'] and row['evidence']
    assert row['dependencies'], row['component_id']
    for loc in source['locations']:
        lines = (ROOT / repo['inspection_path'] / loc['path']).read_text().splitlines()
        assert 1 <= loc['start_line'] <= loc['end_line'] <= len(lines), row['component_id']
        assert repo['commit'] in row['evidence'][0]['url']
    for gap in row['contract_gaps']:
        assert gap in {f'G{i:02d}' for i in range(1, 14)} | {f'X{i:02d}' for i in range(1, 8)}
for definition in index:
    row = by_id[definition['component_id']]
    assert definition['repository'] == row['source']['repository']
    assert definition['commit'] == row['source']['commit']
    assert definition['symbol'] in row['source']['symbols']
    loc = row['source']['locations'][0]
    assert loc['start_line'] <= definition['line'] <= loc['end_line']
    text = (ROOT / sources[definition['repository']]['inspection_path'] / definition['path']).read_text().splitlines()
    assert definition['signature'].strip() == text[definition['line'] - 1].strip()
assert len(index) == coverage['definition_occurrences']
assert len(coverage['modules']) == 15
for family, ids in coverage['modules'].items():
    actual = [r['component_id'] for r in ledger if any(m['family'] == family for m in r['module_mappings'])]
    assert actual == ids
assert sum(bool(v) for v in coverage['modules'].values()) == coverage['module_families_with_observed_semantic_responsibility'] == 9
assert coverage['omega_fusion_contract_conformance_demonstrated'] == 0
checked('ledger-symbols-classifications-and-family-coverage', dict(rows=len(ledger), definitions=len(index), counts=counts))

# Independently reconcile all application/adapter Python and MeTTa definition
# starts, and application Prolog predicate starts. Selected imported runtime
# coverage is explicitly smaller than the entire PeTTa engine.
actual = set()
for repo in ('patham9/mettaclaw', 'patham9/petta_lib_chromadb'):
    path = ROOT / sources[repo]['inspection_path']
    for filename in git(path, 'ls-files').splitlines():
        text = (path / filename).read_text()
        if filename.endswith('.py'):
            def walk(nodes, prefix=''):
                for node in nodes:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        actual.add((repo, filename, node.lineno, prefix + node.name))
                    elif isinstance(node, ast.ClassDef):
                        walk(node.body, node.name + '.')
            walk(ast.parse(text).body)
        elif filename.endswith('.metta'):
            for line, value in enumerate(text.splitlines(), 1):
                m = re.match(r'\(=\s+\(([^\s()]+)', value)
                if m:
                    actual.add((repo, filename, line, m.group(1)))
        elif filename == 'src/skills.pl':
            for line, value in enumerate(text.splitlines(), 1):
                m = re.match(r'([a-z_][a-zA-Z_0-9]*)\(', value)
                if m:
                    actual.add((repo, filename, line, m.group(1)))
recorded = {(d['repository'], d['path'], d['line'], d['symbol']) for d in index
            if d['repository'] in ('patham9/mettaclaw', 'patham9/petta_lib_chromadb')}
assert actual == recorded, (actual - recorded, recorded - actual)
checked('independent-application-and-adapter-definition-reconciliation', len(actual))

omega = ROOT / sources['patham9/mettaclaw']['inspection_path']
tree = ast.parse((omega / 'src/helper.py').read_text())
commands = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'LLM_COMMANDS' for t in n.targets))
assert len(commands) == 19
command_map = (HERE / 'command-map.md').read_text()
for command in commands:
    assert '`' + command + '(' in command_map, command
assert '`receive()`' in command_map
checked('advertised-command-and-runtime-receive-coverage', sorted(commands))

scores = read('remote-scorecard.json')
assert len(scores['criteria']) == 12 and len(scores['candidates']) == 10
for row in scores['candidates']:
    assert row['scores'].keys() == scores['criteria'].keys()
    assert all(type(v) is int and 0 <= v <= 3 for v in row['scores'].values())
    assert sum(row['scores'].values()) == row['total']
    assert row['rationale'] and row['placement']
assert sorted(r['prototype_rank'] for r in scores['candidates'] if r['prototype_rank']) == [1, 2, 3]
checked('placement-scores-and-ranked-candidates', 10)

required = ['README.md', 'mapping-ledger.json', 'command-map.md', 'state-ownership.md',
            'remote-placement.md', 'interface-gaps.md', 'diagrams.md', 'source-state.json',
            'evidence.md', 'next-slice.md']
assert all((HERE / name).is_file() for name in required)
links = 0
for doc in HERE.glob('*.md'):
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if target.startswith(('https://', 'http://', '#')):
            continue
        pathname = target.split('#', 1)[0]
        # validation-results is the output of this very check.
        assert (doc.parent / pathname).exists() or pathname == 'validation-results.json', (doc.name, target)
        links += 1
checked('required-deliverables-and-local-links', dict(required=len(required), links=links))

blocks = re.findall(r'```mermaid\n([\s\S]*?)```', (HERE / 'diagrams.md').read_text())
rendered = read('diagram-validation.json')
assert len(blocks) == len(rendered['results']) == 7
assert all(r['status'] == 'PASS' and r['svg_bytes'] > 1000 for r in rendered['results'])
assert rendered['source_sha256'] == hashlib.sha256((HERE / 'diagrams.md').read_bytes()).hexdigest()
checked('mermaid-render-evidence-matches-current-diagrams', 7)

# The inspection baseline stays pinned after the review packet is committed.
# Permit only this packet and its original brief in descendant/working changes;
# runtime changes still fail. Keep evidence stable across staging and commit.
baseline = state['fusion_worktree']['commit']
subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', baseline, 'HEAD'], check=True)
review_paths = sorted(set(git(ROOT, 'diff', '--name-only', baseline, '--').splitlines()) |
                      set(git(ROOT, 'ls-files', '--others', '--exclude-standard').splitlines()))
assert all(p == state['task_brief']['path'] or p.startswith('docs/omega-adoption/mettaclaw-neoclaw/') for p in review_paths)
brief = ROOT / state['task_brief']['path']
assert hashlib.sha256(brief.read_bytes()).hexdigest() == state['task_brief']['sha256']
old = state['untouched_existing_mettaclaw']
assert git(old['path'], 'rev-parse', 'HEAD') == old['commit']
assert git(old['path'], 'status', '--porcelain').splitlines() == old['status']
checked('no-runtime-change-and-preserved-existing-worktrees',
        dict(runtime_changes=[], review_scope_paths=review_paths))

gates = read('gates.json')
assert len(gates['gates']) == 13 and all(g['result'] == 'PASS' and g['evidence'] for g in gates['gates'])
checked('mapping-gate-consistency', 13)
(HERE / 'validation-results.json').write_text(json.dumps(dict(schema='omega-mapping-validation/1',
    scope='Review consistency only; not semantic or runtime conformance proof', results=results), indent=2) + '\n')
print(json.dumps(dict(checks=len(results), status='PASS', rows=len(ledger), definitions=len(index)), indent=2))
