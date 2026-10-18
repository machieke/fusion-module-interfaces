"""S03.2 original remember/query oracle on a new generated corpus only."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid

from fusion.contracts import canonical, digest, require
from .controlled_run import ControlledRun
from .memory_composition import ROOT, SDK, MODEL
from .memory_embedding import load
from .memory_oracle import prepare_original, creation_source

TEXT = 'Synthetic violet beacon Ω stores seven paper moons.'
QUERY = 'Which synthetic beacon stores seven paper moons?'
CREATED = '2031-04-05 06:07:08'


def generated():
    model = json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())
    encode = load(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py', MODEL, model['files'])
    texts = ('Generated copper kettle boils water for imaginary tea.',
             'Generated striped observatory counts cardboard planets.')
    records = [dict(uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 's03.2/distractor/'+str(i))),
                    time='2031-04-04 00:00:0'+str(i), content=text, vector=encode(text),
                    links=['2031-04-04 00:00:0'+str(i)], stv=[.7,.6], promotion=float(i))
               for i,text in enumerate(texts)]
    return dict(corpus_id='synthetic-append-memory-2031',records=records, queries={QUERY:encode(QUERY)}, clock=2_000_000_000.,
                embedding_boundary='real-native-e5', approved_append_inputs=[TEXT], creation_clock_fixture=CREATED)


def original(corpus, text=TEXT, *, responses=None):
    responses = responses or ['query '+QUERY, 'remember '+text, 'query '+QUERY, '']
    run = ControlledRun('local', responses)
    try:
        run.model['expected_feedback'] = {}; run.save()
        path=run.h.caller_root/'corpus.json';path.write_bytes(canonical(corpus))
        args,env,work=prepare_original(run.app_path,path,SDK/'lib/python3.12/site-packages',vector_fixture=False,model=MODEL)
        runtime=json.loads(Path(run.app['runtime']).read_text());omega=Path(runtime['mettaclaw'])
        source=creation_source(omega).replace('(get_time_as_string)', '(py-call (memory_bootstrap.creation_clock (get_time_as_string)))')
        with (work/'memory.metta').open('a') as out:out.write('\n'+source+'\n')
        with (work/'memory_bootstrap.py').open('a') as out:
            out.write('''
import time
events=[]
def emit(event, **value):
 events.append(dict(event=event, **value));Path('creation-trace.json').write_text(json.dumps(events))
def creation_clock(observed):
 chosen=corpus.get('creation_clock_fixture',observed)
 emit('time',observed=observed,selected=chosen);return chosen
_encode=lib_llm_ext.useLocalEmbedding
def encode(text):
 start=time.monotonic();v=_encode(text)
 emit('encode',helper_input=text,helper_utf8=list(text.encode()),vector=v,elapsed_ms=(time.monotonic()-start)*1000)
 return v
lib_llm_ext.useLocalEmbedding=encode
_remember=lib_chromadb.remember
def remember(content, vector, timestamp):
 key=_remember(content,vector,timestamp)
 emit('remember',uuid=key,content=content,raw_utf8=list(content.encode()),time=timestamp,
      record=lib_chromadb.COLLECTION.get(ids=[key],include=['documents','metadatas']),
      stv=lib_chromadb.get_stv(key),promotion=helper.promotion_get_value(key),
      promotion_lasttime=helper.promotion_get_lasttime(key),promotion_has_key=helper.promotion_has_key(key))
 return key
lib_chromadb.remember=remember
_link=lib_chromadb.link_episode
def link(key, timestamp):
 result=_link(key,timestamp)
 emit('link',uuid=key,time=timestamp,record=lib_chromadb.COLLECTION.get(ids=[key],include=['documents','metadatas']),
      links=lib_chromadb.query_linked_episodes(key),stv=lib_chromadb.get_stv(key))
 return result
lib_chromadb.link_episode=link
_query=lib_chromadb.query_with_ids_and_dists
def query(vector,k):
 result=_query(vector,k);emit('query',candidates=result);return result
lib_chromadb.query_with_ids_and_dists=query
''')
        begun=time.monotonic();measurement=work/'oracle-time.txt'
        result=subprocess.run(['/usr/bin/time','-v','-o',str(measurement),*args],env=env,cwd=work,capture_output=True,text=True,timeout=90)
        elapsed=(time.monotonic()-begun)*1000
        require(result.returncode==0 and len(run.observations())==len(responses),'NOT_AVAILABLE')
        events=json.loads((work/'creation-trace.json').read_text())
        remembers=[e for e in events if e['event']=='remember']
        commands=[command[1] for row in run.rows('app_turns') for command in json.loads(row['commands']) if command[0]=='remember']
        require(remembers and [e['content'] for e in remembers]==commands and all(e['stv']==[1.,.5] and
                e['promotion']==0. and e['promotion_lasttime']==0. and e['promotion_has_key'] is False for e in remembers),'CONFLICT')
        require(all(e['links']==[e['time']] for e in events if e['event']=='link'),'CONFLICT')
        feedback=run.observations()
        require(any('REMEMBER-SUCCESS' in str(o['feedback']) for o in feedback),'CONFLICT')
        return dict(boundary='original native loop/parser/remember/createMemory/embed/query and Chroma helper; real pinned E5',
                    fixtures=['external model/channel','unused history/global promoted context','creation and enrichment clocks'],
                    model_input=text,accepted_contents=commands,events=events,observations=feedback,turns=run.rows('app_turns'),exit_code=result.returncode,
                    total_process_ms=elapsed,process_measurement=measurement.read_text(),
                    recipe_source_sha256=digest(Path(__file__).read_bytes()),
                    generated_overlay_sha256={p.name:digest(p.read_bytes()) for p in (work/'start.metta',work/'memory_bootstrap.py',work/'memory.metta',work/'loop.metta')},
                    corpus_sha256=digest(canonical(corpus)),random_uuid_correspondence='compare per accepted occurrence; legacy UUIDs are newly random')
    finally:run.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus',required=True);parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--evidence',required=True);args=parser.parse_args()
    path=Path(args.corpus)
    if args.prepare:path.write_bytes(canonical(generated()))
    Path(args.evidence).write_bytes(canonical(original(json.loads(path.read_text()))))
