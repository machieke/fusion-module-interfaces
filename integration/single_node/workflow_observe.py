"""Read-only operator diagnostics of this owner's synthetic PVC, no policies/keys."""
import json,sqlite3
from pathlib import Path
from .memory_observe import memory_observe

def observe(root=Path('/state')):
 value=memory_observe(root)
 for name in ('measured.sqlite','model.sqlite','bridge.sqlite','channel-messages.sqlite','channel-atoms.sqlite'):
  file=root/name
  if not file.exists():continue
  with sqlite3.connect(file.as_uri()+'?mode=ro',uri=True) as db:
   db.row_factory=sqlite3.Row;db.execute('BEGIN')
   tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   value[name]={t:[dict(r) for r in db.execute('SELECT * FROM '+t)] for t in sorted(tables) if (t.startswith('app_') or t.startswith('channel_') or t in ('model_calls','messages','atoms')) and t not in ('channel_bridge','channel_seal')}
 for name in ('setup-view.json','measured-status.json','channel-ready.json','measured-native/channel-boundary.json','measured-native/model-boundary.json','measured-native/embedding-boundary.json'):
  if (root/name).exists():value[name]=json.loads((root/name).read_text())
 for name in ('peer-traffic.jsonl','recorded-evaluations.jsonl'):
  if (root/name).exists():value[name]=[json.loads(line) for line in (root/name).read_text().splitlines()]
 return value
if __name__=='__main__':print(json.dumps(observe(),sort_keys=True))
