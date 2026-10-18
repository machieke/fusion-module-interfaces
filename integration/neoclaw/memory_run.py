"""Three actual native-loop paths on one new synthetic corpus. No live model/channel.

Run with the pinned S03 Python environment. Embeddings and Chroma remain real
unless --vectors is explicitly selected; S02 regressions use recorded responses.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import subprocess
from fusion.contracts import canonical,require
from .controlled_run import ControlledRun
from .memory_composition import configure,SDK,MODEL,ROOT
from .memory_corpus import generated,QUERY
from .memory_oracle import prepare_original
from .memory_embedding import load


def real_corpus():
    corpus=generated()
    model=json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())
    embed=load(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py',MODEL,model['files'])
    for row in corpus['records']:row['vector']=embed(row['content'])
    for query in corpus['queries']:corpus['queries'][query]=embed(query)
    corpus['embedding_boundary']='real-native-e5';return corpus


def original(corpus,real=False):
    run=ControlledRun('local',['query '+QUERY,''])
    try:
        run.model['expected_feedback']={};run.save()
        path=run.h.caller_root/'original-corpus.json';path.write_bytes(canonical(corpus))
        args,env,work=prepare_original(run.app_path,path,SDK/'lib/python3.12/site-packages',vector_fixture=not real,model=MODEL)
        process=subprocess.run(args,env=env,cwd=work,capture_output=True,text=True,timeout=60)
        require(process.returncode==0 and len(run.observations())==2,'NOT_AVAILABLE')
        return dict(boundary='original native; original Chroma helper; scripted model/channel; unused history/global-promoted-context',
            feedback=run.observations()[1]['feedback'],candidates=json.loads((work/'original-candidates.json').read_text()),
            turns=run.rows('app_turns'),exit_code=process.returncode)
    finally:run.close()


def report(run):
    value=run.report()
    with sqlite3.connect(run.h.client['database']) as db:
        db.row_factory=sqlite3.Row
        value['read_receipts']=[{k:json.loads(v) if k in ('request','candidates','payloads') and v else v for k,v in dict(row).items()} for row in db.execute('SELECT * FROM app_memory_reads')]
    return value


def compare(corpus,real=False):
    oracle=original(corpus,real);results={}
    for placement in ('local','network'):
        run=ControlledRun(placement,['query '+QUERY,''],search={'boundary':'recorded-response'})
        try:
            run.model['expected_feedback']={};run.save()
            configure(run,corpus,'real' if real else 'vector-fixture')
            run.operator();code,status=run.finish(run.start())
            require(code==0 and status=={'status':'BOUNDED_STOP'},'NOT_AVAILABLE')
            value=report(run);feedback=run.observations()[1]['feedback']
            require(feedback==oracle['feedback'],'CONFLICT')
            rows=value['read_receipts'][0]['payloads']
            # Original/adapted ordered candidates and distances: ties can differ in
            # identity order, but the admitted corpus renders duplicate ties identically.
            expected={r[0]:r for r in oracle['candidates']}
            require(set(r[0] for r in rows)==set(expected),'CONFLICT')
            for row in rows:
                require(row[:3]==expected[row[0]][:3] and abs(row[3]-expected[row[0]][3])<=1e-6,'CONFLICT')
            value['exact_native_feedback_match']=True
            value['candidate_order_match']=[r[0] for r in rows]==[r[0] for r in oracle['candidates']]
            results[placement]=value
        finally:run.close()
    return dict(oracle=oracle,paths=results,embedding='real-local-E5' if real else 'vector-fixture',corpus_hash=__import__('hashlib').sha256(canonical(corpus)).hexdigest(),
        providers=['real Chroma 1.5.5','real DeTTa','real SWI/PeTTa/native MeTTaClaw','real certificate-checked loopback HTTPS'],
        fixtures=['scripted external model','IRC/channel','unused history/global-promoted-context','fixed enrichment clock'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--vectors',action='store_true');p.add_argument('--evidence',required=True);args=p.parse_args()
    corpus=generated() if args.vectors else real_corpus()
    Path(args.evidence).write_bytes(canonical(compare(corpus,not args.vectors)))

if __name__=='__main__':main()
