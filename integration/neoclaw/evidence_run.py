"""Reproducible generated local S04 native session and owner-port trace."""
import json
from pathlib import Path
import sqlite3
from fusion.contracts import canonical,require,digest
from fusion.neoclaw_application import Application
from .controlled_run import ControlledRun
from .evidence_composition import configure,TEXT as SOURCE_TEXT,SECOND_LABEL
from .append_oracle import TEXT,QUERY,CREATED
from .evidence_oracle import SOURCE_LABEL
from .embedding_run import start
from .append_run import report as append_report
from .memory_composition import ROOT


def commands():
    target=CREATED.replace(' ','_');source=SOURCE_LABEL.replace(' ','_')
    return ['remember '+TEXT,'query '+QUERY,'support '+target+' '+source,'query '+QUERY,
            'support '+target+' '+source,'query '+QUERY,'contradict '+target+' '+source,'query '+QUERY,
            'contradict '+target+' '+SECOND_LABEL.replace(' ','_'),'query '+QUERY,'']


def report(run,cfg):
    value=append_report(run,cfg)
    with sqlite3.connect(run.h.client['database']) as db:
        db.row_factory=sqlite3.Row
        for table in ('app_sources','app_assessments','app_read_views','app_query_views'):
            encoded={'accepted','binding','episode','receipt','event','creation','claim','declaration','decision','value'}
            if table=='app_assessments':encoded.add('view')
            value[table]=[{k:json.loads(v) if k in encoded and v else v for k,v in dict(x).items()}
                          for x in db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
    app=Application(run.app_path)
    try:
        sources=value['app_sources'];episode=sources[0]['episode'] if sources else None
        records=[]
        if episode:
            n=1
            while True:
                page=app.evidence.modules.episodes.readEpisode(episode,n,16);records+=page['events']
                if page['complete']:break
                n=page['next_sequence']
            value['pending']=app.evidence.modules.episodes.pendingEvidence(episode,16)
        value['episode_records']=records
    finally:app.close()
    # Test-side owner-journal inspection is labelled; runtime uses declared ports.
    path=cfg['cognitive_root']/'beliefs.sqlite'
    with sqlite3.connect(path) as db:
        value['owner_budget_audit']=[dict(id=r[0],binding=json.loads(r[1]),evaluations=r[2]) for r in db.execute('SELECT * FROM nal_budgets')]
    value['placement']='local C1/C2/provenance/native revision; no remote cognitive gate'
    value['fixtures']=['scripted external model and generated channel','creation/enrichment comparison clocks','unused history/global promoted context']
    return value


def execute(corpus):
    run=ControlledRun('local',commands(),search={'boundary':'recorded-response'});run.model['expected_feedback']={};run.save()
    try:
        cfg=configure(run,corpus);run.operator();result=run.finish(start(run))
        if result!=(0,{'status':'BOUNDED_STOP'}):
            raise RuntimeError(str(result)+'\n'+(run.h.root/'native.log').read_text()[-14000:])
        value=report(run,cfg)
        require(len(value['app_assessments'])==4 and value['pending']==(),'CONFLICT')
        require([x['decision']['numerical'] for x in value['app_assessments']]==['revised','no-change','retained-alternative','revised'],'CONFLICT')
        require('0.6666666666666666' in value['observations'][4]['feedback'],'CONFLICT')
        require(len(value['maintenance_audit'])==1 and len(value['app_memory_vectors'])==1,'CONFLICT')
        return value
    finally:run.close()


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--corpus',required=True);p.add_argument('--evidence',required=True);a=p.parse_args()
    Path(a.evidence).write_bytes(canonical(execute(json.loads(Path(a.corpus).read_text()))))
