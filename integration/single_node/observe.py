"""Read only this pod owner's synthetic observations; never mount foreign state."""
import json
from pathlib import Path
import sqlite3


def observe(root=Path('/state')):
    result={}
    tables={'caller.sqlite':('app_session','app_turns','app_occurrences','caller_requests'),
            'execution.sqlite':('jobs','s01_work','outbox','mutations'),
            'atoms.sqlite':('atoms',),'messages.sqlite':('messages','acknowledgements')}
    for name,names in tables.items():
        file=root/name
        if not file.exists():continue
        with sqlite3.connect(file.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row;db.execute('BEGIN')
            available={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            result.update({table:[dict(r) for r in db.execute('SELECT * FROM '+table)] for table in names if table in available})
    for name in ('owner-seal.json','process.json','pause.json','response-dropped.json','native-status.json','native-exit.json','shutdown.json','worker-status.json'):
        if (root/name).exists():result[name]=json.loads((root/name).read_text())
    if (root/'model-contexts.jsonl').exists():result['model_contexts']=[json.loads(x) for x in (root/'model-contexts.jsonl').read_text().splitlines()]
    if (root/'native/startup.json').exists():result['native_startup']=json.loads((root/'native/startup.json').read_text())
    return result


if __name__=='__main__':print(json.dumps(observe(),sort_keys=True))
