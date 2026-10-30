"""Qualification observer of this owner's synthetic PVC only; never an RPC."""
import json,sqlite3
from pathlib import Path
from .memory_observe import memory_observe

def observe(root=Path('/state')):
 value=memory_observe(root);value['cognitive']={}
 for file in sorted((root/'cognitive').glob('*.sqlite')):
  with sqlite3.connect(file.as_uri()+'?mode=ro',uri=True) as db:
   db.row_factory=sqlite3.Row;db.execute('BEGIN')
   tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
   value['cognitive'][file.name]={t:[dict(r) for r in db.execute('SELECT * FROM "'+t+'" LIMIT 600')] for t in tables}
 for name in ('promoted-context.metta','native/run.log'):
  if (root/name).exists():value[name]=(root/name).read_text()[-30000:]
 return value
if __name__=='__main__':print(json.dumps(observe(),sort_keys=True))
