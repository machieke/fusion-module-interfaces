"""S02 addition to the existing disposable controlled-run operator recipe."""
import json
import os
from pathlib import Path

from fusion import neoclaw_contracts as c, neoclaw_search_contracts as s, neoclaw_operations as ops
from fusion.contracts import canonical
from fusion.registry import descriptor_wire

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = Path(os.environ.get('S02_RUNTIME', ROOT/'artifacts/s02/search-runtime.json'))
QUERY = 'Python programming language official documentation'
COMMAND = 'search ' + QUERY
ROWS_A = [dict(title='Python documentation', href='https://docs.python.org/3/', body='Generated recorded observation A.')]
ROWS_B = [dict(title='Python documentation', href='https://docs.python.org/3/', body='Generated recorded observation B.')]


def configure(run, search):
    h = run.h
    config = dict(runtime=str(RUNTIME), boundary=search['boundary'], audit=str(h.server_root/'search-audit.jsonl'))
    if config['boundary'] == 'recorded-response':
        path = h.server_root/'search-recording.json'
        path.write_bytes(canonical(dict(observations=search.get('observations', [dict(rows=ROWS_A)]))))
        config['recording'] = str(path)
    h.config.update(profile=ops.COMPOSITION, search=config, search_queries=[QUERY])
    for name in ('A', 'B', 'worker'):
        scopes = h.config['principals'][name]['scopes']
        scopes[c.SCOPE] = list(dict.fromkeys([*scopes[c.SCOPE], 'execution.web_search']))
    h.save()
    h.client.update(composition=ops.COMPOSITION, search_max_attempts=1, search_queries=[QUERY],
                    search_catalogue=[descriptor_wire(x) for x in s.catalogue(h.config['atom_provider'])])
    h.save_client()
    run.app['composition'] = ops.APPLICATION
    if h.client['placement'] == 'network':
        runtime = json.loads(RUNTIME.read_text())
        run.app['denied_paths'].append(str(Path(runtime['python']).parent.parent))


def audit(run):
    path = Path(run.h.config['search']['audit'])
    return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
