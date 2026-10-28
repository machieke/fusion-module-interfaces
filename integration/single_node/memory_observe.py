"""Operator-only, read-only observations of this pod's own synthetic state."""
import json
from pathlib import Path
import sqlite3
from integration.single_node.observe import observe


def memory_observe(root=Path('/state')):
    value=observe(root)
    for name in ('caller.sqlite','encoder.sqlite','memory/feed.sqlite'):
        file=root/name
        if not file.exists():continue
        with sqlite3.connect(file.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row;db.execute('BEGIN')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            for table in sorted(tables):
                if table.startswith('app_') or table in ('encode_intents','encode_attempts','feed_atoms','feed_meta'):
                    value[table]=[dict(r) for r in db.execute('SELECT * FROM '+table)]
    for name in ('initial-view.json','initial-intent.json','encoder-readiness.json','native/embedding-boundary.json'):
        if (root/name).exists():value[name]=json.loads((root/name).read_text())
    search=root/'memory/search'
    if search.exists():
        value['search_files']=[str(p.relative_to(search)) for p in search.rglob('*') if p.is_file()]
        value['publications']=json.loads((search/'published.json').read_text()) if (search/'published.json').exists() else None
        value['maintenance']={p.parent.name:json.loads(p.read_text()) for p in search.glob('*/maintenance.json')}
    value['root_files']=[str(p.relative_to(root)) for p in root.iterdir()]
    return value

if __name__=='__main__':print(json.dumps(memory_observe(),sort_keys=True))
