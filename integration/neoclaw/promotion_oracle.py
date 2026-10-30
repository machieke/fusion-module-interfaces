"""Unadapted native promote/demote/query/global context on a fresh synthetic corpus."""
import json
from pathlib import Path
import subprocess
import time
from fusion.contracts import canonical,digest,require
from .controlled_run import ControlledRun
from .memory_oracle import prepare_original,query_source,creation_source
from .memory_composition import ROOT,SDK,MODEL
from .append_oracle import TEXT,QUERY,CREATED


from .memory_oracle import function

def commands(corpus):
    candidate=corpus['records'][5]['time'];outside=corpus['records'][-1]['time']
    return ['remember '+TEXT,'query '+QUERY,'promote '+candidate,'query '+QUERY,
        'promote '+outside,'promote '+outside,'query '+QUERY,'demote '+candidate,'query '+QUERY,'']

def original(corpus,responses=None):
    run=ControlledRun('local',responses or commands(corpus));run.model['expected_feedback']={};run.save()
    try:
        path=run.h.caller_root/'corpus.json';path.write_bytes(canonical(corpus))
        args,env,work=prepare_original(run.app_path,path,SDK/'lib/python3.12/site-packages',vector_fixture=False,model=MODEL)
        runtime=json.loads(Path(run.app['runtime']).read_text());omega=Path(runtime['mettaclaw'])
        source=(work/'memory.metta').read_text().replace('(= (best-promoted-memories) "")','(= (mostPromotedMemories) 10)')
        source+='\n'+creation_source(omega).replace('(get_time_as_string)','"'+CREATED+'"')
        for name in ('promote','demote','best-promoted-memory-ids','best-promoted-memories'):
            source+='\n'+function(omega,name).replace('(get_time)','(py-call (memory_bootstrap.clock))')
        (work/'memory.metta').write_text(source)
        with (work/'memory_bootstrap.py').open('a') as f:
            f.write('''
events=[]
def record(kind, **body):
 events.append(dict(kind=kind,**body));Path('promotion-trace.json').write_text(json.dumps(events))
_old_commit=helper.promotion_commit
def commit():
 result=_old_commit();record('adjustment',state={u:[helper.promotion_get_value(u),helper.promotion_get_lasttime(u)] for u in helper.promotion_get_all_keys()});return result
helper.promotion_commit=commit
_old_query=lib_chromadb.query_with_ids_and_dists
def query(*args):
 result=_old_query(*args);record('query',rows=result);return result
lib_chromadb.query_with_ids_and_dists=query
_old_ids=lib_chromadb.query_by_ids
def ids(targets):
 result=_old_ids(targets);record('global',targets=targets,rows=result);return result
lib_chromadb.query_by_ids=ids
''')
        started=time.monotonic();proc=subprocess.run(args,cwd=work,env=env,capture_output=True,text=True,timeout=180)
        if proc.returncode or len(run.observations())!=len(run.model['responses']):
            (ROOT/'evidence/s05/oracle-development.log').write_text(proc.stdout+'\n'+proc.stderr)
            raise RuntimeError('original oracle failed; retained native log')
        return dict(boundary='original native wrappers, arithmetic, query and getContext; real E5/Chroma',
            fixtures=['generated corpus','scripted model/channel','creation and wall-clock comparison samples','unused history'],
            events=json.loads((work/'promotion-trace.json').read_text()),observations=run.observations(),turns=run.rows('app_turns'),
            output=(work/'repos/mettaclaw/memory/promoted_memories.metta').read_text(),elapsed_ms=(time.monotonic()-started)*1000,
            overlays={p.name:digest(p.read_bytes()) for p in (work/'memory.metta',work/'memory_bootstrap.py',work/'loop.metta')},
            corpus_sha256=digest(canonical(corpus)),parser='single argument with spaces retained; promote/demote do not replace underscores')
    finally:run.close()

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--corpus',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_bytes(canonical(original(json.loads(Path(a.corpus).read_text()))))
