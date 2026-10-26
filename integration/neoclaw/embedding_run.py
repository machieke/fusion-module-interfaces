"""S03.1 real-model native parity and caller-dependency demonstration."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

from fusion.contracts import canonical, digest, require
from .controlled_run import ControlledRun
from .embedding_composition import configure, CALLER_RUNTIME, PROVIDER_RUNTIME
from .memory_composition import SDK, MODEL, ROOT, configure as memory_configure
from .memory_corpus import QUERY
from .memory_oracle import prepare_original
from .memory_run import real_corpus, report as memory_report


def original(corpus, query=QUERY):
    run = ControlledRun('local', ['query '+query, ''])
    try:
        run.model['expected_feedback'] = {}; run.save()
        path = run.h.caller_root/'corpus.json'; path.write_bytes(canonical(corpus))
        args, env, work = prepare_original(run.app_path, path, SDK/'lib/python3.12/site-packages', vector_fixture=False, model=MODEL)
        bootstrap = work/'memory_bootstrap.py'
        with bootstrap.open('a') as stream:
            stream.write('''
import time
_native_encode = lib_llm_ext.useLocalEmbedding
def traced_encode(text):
 start=time.monotonic(); vector=_native_encode(text)
 Path('original-embedding.json').write_text(json.dumps(dict(input=text,input_utf8=list(text.encode()),vector=vector,encode_ms=(time.monotonic()-start)*1000)))
 return vector
lib_llm_ext.useLocalEmbedding=traced_encode
''')
        measure = work/'time.txt'; start = time.monotonic()
        result = subprocess.run(['/usr/bin/time','-v','-o',str(measure),*args], env=env, cwd=work, capture_output=True, text=True, timeout=60)
        require(result.returncode == 0 and len(run.observations()) == 2, 'NOT_AVAILABLE')
        return dict(feedback=run.observations()[1]['feedback'], candidates=json.loads((work/'original-candidates.json').read_text()),
            embedding=json.loads((work/'original-embedding.json').read_text()), elapsed_ms=(time.monotonic()-start)*1000,
            process_measurement=measure.read_text(), boundary='original native query + native E5; scripted model/channel; generated corpus and clock')
    finally: run.close()


def start(run, caller_runtime=CALLER_RUNTIME):
    Path(run.app['status_file']).unlink(missing_ok=True)
    python = json.loads(Path(caller_runtime).read_text())['python'] if caller_runtime else str(SDK/'bin/python')
    log = open(run.h.root/'native.log', 'a'); run.logs.append(log)
    process = subprocess.Popen(['/usr/bin/time','-v','-o',str(run.h.caller_root/'caller-time.txt'),python,
        '-m','integration.neoclaw.native_loop',str(run.app_path)], cwd=ROOT,stdout=log,stderr=log,start_new_session=True)
    run.processes.append(process); return process


def observed_finish(run, caller_runtime=CALLER_RUNTIME, *, observer_seconds=45):
    wall=time.time()*1000;begun=time.monotonic();process=start(run,caller_runtime)
    first=None
    while process.poll() is None:
        if first is None and Path(run.model['log']).exists():first=(time.monotonic()-begun)*1000
        if time.monotonic()-begun>observer_seconds:
            run.kill(process);raise TimeoutError('native observer; original application deadline unchanged')
        time.sleep(.02)
    code,status=run.finish(process)
    if (code,status)!=(0,{'status':'BOUNDED_STOP'}):
        raise RuntimeError(str((code,status))+'\n'+(run.h.root/'native.log').read_text()[-7000:])
    return dict(start_unix_ms=wall,cold_start_to_first_context_ms=first,total_ms=(time.monotonic()-begun)*1000,
                observer_resolution_ms=20)


def s03_measurement(corpus):
    run=ControlledRun('network',['query '+QUERY,''],search={'boundary':'recorded-response'})
    try:
        run.model['expected_feedback']={};run.save();memory_configure(run,corpus,'real');run.operator()
        measurement=observed_finish(run,None)
        return dict(composition='controlled-native-loop/3',embedding='original S03 caller-local E5',
            retrieval='same-host HTTPS',measurement=measurement,
            process_measurement=(run.h.caller_root/'caller-time.txt').read_text(),feedback=run.observations()[1]['feedback'])
    finally:run.close()


def report(run, cfg):
    value = memory_report(run)
    with sqlite3.connect(run.h.client['database']) as db:
        db.row_factory=sqlite3.Row
        value['encodings'] = [{k:json.loads(v) if k in ('intent','result','measurement') and v else v for k,v in dict(r).items()}
                               for r in db.execute('SELECT * FROM app_query_vectors')]
    with sqlite3.connect(cfg['encoder_database']) as db:
        db.row_factory=sqlite3.Row
        value['provider_attempts'] = [dict(r) for r in db.execute('SELECT * FROM encode_attempts')]
    for name,file in (('caller_dependencies','embedding-boundary.json'),('caller_ready','embedding-ready.json')):
        path=Path(run.app['workdir'])/file
        if path.exists():value[name]=json.loads(path.read_text())
    path=run.h.caller_root/'caller-time.txt'
    if path.exists():value['process_measurement']=path.read_text()
    return value


def compare(corpus, caller_runtime=CALLER_RUNTIME, provider_runtime=PROVIDER_RUNTIME):
    oracle=original(corpus); baseline=s03_measurement(corpus); values={}
    require(baseline['feedback']==oracle['feedback'],'CONFLICT')
    for encoder,retrieval in (('local','local'),('network','network'),('network','local'),('local','network')):
        run=ControlledRun(retrieval,['query '+QUERY,''],search={'boundary':'recorded-response'})
        try:
            run.model['expected_feedback']={};run.save()
            config=configure(run,corpus,encoder,caller_runtime=caller_runtime,provider_runtime=provider_runtime);run.operator()
            timing=observed_finish(run,caller_runtime)
            value=report(run,config);value['timing']=timing
            require(all(value['caller_dependencies']['absent'].values()) and value['caller_dependencies']['local_initializer_forbidden'],'CONFLICT')
            if encoder=='network':
                require(len(value['caller_dependencies']['denied_file_probes'])==4 and
                        set(value['caller_dependencies']['denied_file_probes'].values())=={'inaccessible'},'CONFLICT')
                require(value['lifecycle']['https']['encoder']['caller_canary_inaccessible'],'CONFLICT')
            require(run.observations()[1]['feedback']==oracle['feedback'],'CONFLICT')
            vector=value['encodings'][0]['result']['vector']; native=oracle['embedding']['vector']
            require(max(abs(a-b) for a,b in zip(vector,native))<=1e-7,'CONFLICT')
            require(value['encodings'][0]['intent']['text']==oracle['embedding']['input'],'CONFLICT')
            rows=value['read_receipts'][0]['payloads'];expected={r[0]:r for r in oracle['candidates']}
            require(set(r[0] for r in rows)==set(expected),'CONFLICT')
            for row in rows:require(row[:3]==expected[row[0]][:3] and abs(row[3]-expected[row[0]][3])<=1e-6,'CONFLICT')
            value.update(encoder_placement=encoder,retrieval_placement=retrieval,exact_feedback_match=True,
                exact_vector_match=vector==native,max_vector_difference=max(abs(a-b) for a,b in zip(vector,native)),
                candidate_order_match=[r[0] for r in rows]==[r[0] for r in oracle['candidates']])
            values[encoder+'-encoder_'+retrieval+'-retrieval']=value
        finally:run.close()
    return dict(oracle=oracle,s03_baseline=baseline,paths=values,corpus_sha256=digest(canonical(corpus)),same_host=True,
        fixtures=['scripted model','channel','unused history/global promoted context','enrichment clock'],
        real=['native query/parser/loop','pinned E5','Chroma','DeTTa','authenticated TLS'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--corpus');p.add_argument('--evidence',required=True);p.add_argument('--prepare',action='store_true')
    p.add_argument('--caller-runtime',default=str(CALLER_RUNTIME));p.add_argument('--provider-runtime',default=str(PROVIDER_RUNTIME))
    args=p.parse_args()
    if args.prepare: value=real_corpus()
    else: value=compare(json.loads(Path(args.corpus).read_text()) if args.corpus else real_corpus(),args.caller_runtime,args.provider_runtime)
    Path(args.evidence).write_bytes(canonical(value))
