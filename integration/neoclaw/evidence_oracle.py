"""Original native support/contradict duplicate counterexample, generated data."""
import json
from pathlib import Path
import subprocess
from fusion.contracts import canonical,digest,require
from .controlled_run import ControlledRun
from .memory_oracle import prepare_original,creation_source,query_source
from .memory_composition import ROOT,SDK,MODEL
from .append_oracle import TEXT,QUERY,CREATED

SOURCE_LABEL='2031-04-05 06:08:09'


def revision_source(omega):
    query_source(omega)
    text=(omega/'src/memory.metta').read_text()
    return '\n'.join(text[text.index('(= ('+name+' '):text.index('\n(= (',text.index('(= ('+name+' ')+1)]
                     for name in ('tvUpdate','support','contradict','link'))


def original(corpus):
    target=CREATED.replace(' ','_');source=SOURCE_LABEL.replace(' ','_')
    responses=['remember '+TEXT,'support '+target+' '+source,'query '+QUERY,
        'support '+target+' '+source,'query '+QUERY,'contradict '+target+' '+source,'query '+QUERY,'']
    run=ControlledRun('local',responses);run.model['expected_feedback']={};run.save()
    try:
        path=run.h.caller_root/'corpus.json';path.write_bytes(canonical(corpus))
        args,env,work=prepare_original(run.app_path,path,SDK/'lib/python3.12/site-packages',vector_fixture=False,model=MODEL)
        runtime=json.loads(Path(run.app['runtime']).read_text());omega=Path(runtime['mettaclaw'])
        with (work/'memory.metta').open('a') as stream:
            stream.write('\n'+creation_source(omega).replace('(get_time_as_string)','"'+CREATED+'"')+'\n'+revision_source(omega))
        with (work/'memory_bootstrap.py').open('a') as stream:
            stream.write('''
events=[]
def trace(kind, **fields):
 events.append(dict(kind=kind, **fields));Path('revision-trace.json').write_text(json.dumps(events))
_remember=lib_chromadb.remember
def remember(*args):
 key=_remember(*args);trace('default',uuid=key,stv=lib_chromadb.get_stv(key));return key
lib_chromadb.remember=remember
_set=lib_chromadb.set_stv
def update(key,s,c):
 result=_set(key,s,c);trace('revision',uuid=key,stv=lib_chromadb.get_stv(key),labels=lib_chromadb.query_linked_episodes(key));return result
lib_chromadb.set_stv=update
''')
        result=subprocess.run(args,env=env,cwd=work,capture_output=True,text=True,timeout=120)
        require(result.returncode==0 and len(run.observations())==len(responses),'NOT_AVAILABLE')
        events=json.loads((work/'revision-trace.json').read_text())
        require(events[0]['stv']==[1.,.5] and len(events)==4,'CONFLICT')
        require(events[1]['stv'][1]<events[2]['stv'][1] and events[1]['labels']==events[2]['labels'],'CONFLICT')
        require(abs(events[3]['stv'][0]-.75)<1e-12,'CONFLICT')
        return dict(boundary='original native loop/parser/tvUpdate/Truth_Revision/query; real E5 and Chroma',
            fixtures=['scripted external model; channel empty','unused history and global context','comparison creation/query clocks'],
            events=events,observations=run.observations(),turns=run.rows('app_turns'),exit_code=result.returncode,
            source_hashes={p.name:digest(p.read_bytes()) for p in (omega/'lib_nal.metta',omega/'src/memory.metta')},
            overlay_hashes={p.name:digest(p.read_bytes()) for p in (work/'memory.metta',work/'loop.metta',work/'memory_bootstrap.py')},
            duplicate_counterexample='same linked label, second update increases confidence; original is not contribution-idempotent')
    finally:run.close()


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--corpus',required=True);p.add_argument('--evidence',required=True);a=p.parse_args()
    Path(a.evidence).write_bytes(canonical(original(json.loads(Path(a.corpus).read_text()))))
