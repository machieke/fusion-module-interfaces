"""Real native S05 reproduction; unchanged caller, composition-selected Attention."""
import json
from pathlib import Path
import sqlite3
from fusion.contracts import canonical,require
from .controlled_run import ControlledRun
from .promotion_composition import configure
from .promotion_oracle import commands
from .embedding_run import start
from .append_run import report as append_report


def report(run,cfg):
    value=append_report(run,cfg)
    with sqlite3.connect(run.h.client['database']) as db:
        db.row_factory=sqlite3.Row
        for table in ('app_priority','app_priority_queries','app_priority_contexts','app_read_views','app_query_views','app_assessments'):
            rows=[]
            for record in db.execute('SELECT * FROM '+table+' ORDER BY rowid'):
                row=dict(record)
                for k in ('request','binding','receipt','result','payloads','lines','value','decision'):
                    if k in row and row[k] is not None:row[k]=json.loads(row[k])
                rows.append(row)
            value[table]=rows
    # Evidence-only inspection of each owner journal, never used by consumers.
    primary=cfg['attention_root']/'attention.sqlite'
    if primary.exists():
        with sqlite3.connect(primary) as db:
            value['attention_owner_audit']=[dict(binding=json.loads(b),spent=n,result=json.loads(r) if r else None) for b,n,r in db.execute('SELECT value,calls,result FROM bindings ORDER BY rowid')]
    else:
        state=json.loads((cfg['attention_root']/'attention.json').read_text())
        value['attention_owner_audit']=list(state['work'].values())
    value['placement']='local private Attention; same-host process; no network attention claim'
    value['fixtures']=['scripted external model/channel','synthetic initial metadata','comparison clocks','unused history']
    value['output']=Path(json.loads(cfg['attention_client'].read_text())['output']).read_text()
    return value


def execute(corpus,provider='sqlite',responses=None,sources=None):
    run=ControlledRun('local',responses or commands(corpus),search={'boundary':'recorded-response'});run.model['expected_feedback']={};run.save()
    try:
        cfg=configure(run,corpus,provider,sources=sources);run.operator();p=start(run);p.wait(timeout=180);result=run.finish(p)
        if result!=(0,{'status':'BOUNDED_STOP'}):
            raise RuntimeError(str(result)+'\n'+(run.h.root/'native.log').read_text()[-14000:])
        return report(run,cfg)
    finally:run.close()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--corpus',required=True);p.add_argument('--out',required=True);p.add_argument('--provider',default='sqlite');a=p.parse_args()
    Path(a.out).write_bytes(canonical(execute(json.loads(Path(a.corpus).read_text()),a.provider)))
