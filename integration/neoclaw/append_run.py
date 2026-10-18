"""Original/local/HTTPS same-session append and readback, with declared fixtures."""
import argparse
import json
from pathlib import Path
import sqlite3
from fusion.contracts import canonical,digest,require
from fusion import vector_contracts as v
from .append_oracle import TEXT,QUERY,original
from .append_composition import configure
from .controlled_run import ControlledRun
from .embedding_run import start,report as read_report,observed_finish
from .memory_composition import ROOT


def report(run,cfg):
    value=read_report(run,cfg)
    with sqlite3.connect(run.h.client['database']) as db:
        db.row_factory=sqlite3.Row
        for table in ('app_memory_writes','app_memory_vectors','app_read_views','app_active_view','app_query_views'):
            value[table]=[{k:json.loads(v) if k in ('intent','result','measurement','receipts','through_head','snapshot','value','observations') and v else v
                           for k,v in dict(r).items()} for r in db.execute('SELECT * FROM '+table)]
    from fusion.append_composition import AppendService
    service=AppendService(run.h.config_path,run.h.client['credential'])
    head=service.atoms.head(run.h.config['memory_append']['scope']);after=0;records=[]
    while after<head['sequence']:
        page=service.atoms.readCommits(head['scope_ref'],after,head,8);records+=page['records'];after=page['next_after']
    value['source']=dict(head=head,records=records)
    root=Path(run.h.config['memory_append']['root'])/'search'
    # Test audit only; the application has no access to these provider files.
    value['publication_audit']=json.loads((root/'published.json').read_text())
    value['maintenance_audit']=[json.loads(p.read_text()) for p in root.glob('*/maintenance.json')]
    return value


def compare(corpus,**options):
    oracle=original(corpus);paths={}
    for encoder,retrieval in (('local','local'),('network','network'),('network','local')):
        run=ControlledRun(retrieval,['query '+QUERY,'remember '+TEXT,'query '+QUERY,''],search={'boundary':'recorded-response'})
        try:
            run.model['expected_feedback']={};run.save();cfg=configure(run,corpus,encoder,**options)
            initial_source=cfg['memory']['source'];configuration_hashes={str(p):digest(Path(p).read_bytes()) for p in
                (run.app_path,run.app['memory_append_config'],run.app['memory_read_config'],run.app['memory_native_config'],run.app['embedding_config'],run.app['memory_embedding_config'])}
            from fusion.vector_composition import ReadService
            service=ReadService(run.h.config_path,run.h.client['credential']);initial_payloads=[];after=0
            while after<initial_source['sequence']:
                page=service.atoms.readCommits(initial_source['scope_ref'],after,initial_source,8)
                for entry in page['records']:
                    if entry['content_type']==v.PAYLOAD:initial_payloads.append(json.loads(service.atoms.get(entry['ref']).bytes))
                after=page['next_after']
            require(all(p['content']!=TEXT for p in initial_payloads),'CONFLICT')
            run.operator();timing=observed_finish(run,options.get('caller_runtime') or cfg['caller_runtime']);value=report(run,cfg)
            require([o['feedback'] for o in run.observations()]==[o['feedback'] for o in oracle['observations']],'CONFLICT')
            require(all(digest(Path(p).read_bytes())==h for p,h in configuration_hashes.items()),'CONFLICT')
            write=value['app_memory_writes'][0];reads=value['read_receipts']
            require(write['uuid'] not in {p[0] for p in reads[0]['payloads']},'CONFLICT')
            require(any(p[0]==write['uuid'] and p[2]==TEXT for p in reads[1]['payloads']),'CONFLICT')
            require(reads[0]['request']['snapshot']==cfg['memory']['snapshot'] and reads[1]['request']['snapshot']==write['snapshot'],'CONFLICT')
            require(write['through_head']['sequence']==initial_source['sequence']+4,'CONFLICT')
            require(all(value['caller_dependencies']['absent'].values()),'CONFLICT')
            native_write_index=next(i for i,x in enumerate(oracle['events']) if x['event']=='remember')
            native_write=oracle['events'][native_write_index];native_encode=oracle['events'][native_write_index-1]
            memory_vector=value['app_memory_vectors'][0]
            require(memory_vector['intent']['text']==native_encode['helper_input'] and memory_vector['result']['vector']==native_encode['vector'],'CONFLICT')
            require(write['intent']['content']==native_write['content'] and write['sampled_time']==native_write['time'],'CONFLICT')
            correspondence={native_write['uuid']:write['uuid']}
            native_queries=[x['candidates'] for x in oracle['events'] if x['event']=='query']
            for read,expected in zip(reads,native_queries):
                mapped=[[correspondence.get(row[0],row[0]),*row[1:]] for row in expected]
                require([r[:3] for r in read['payloads']]==[r[:3] for r in mapped],'CONFLICT')
                require(all(abs(a[3]-b[3])<=1e-6 for a,b in zip(read['payloads'],mapped)),'CONFLICT')
            value.update(timing=timing,exact_native_feedback_match=True,exact_memory_vector_match=True,
                candidate_order_match=True,identity_correspondence=correspondence,initial_authoritative_payloads=initial_payloads,
                configuration_unchanged=True,encoder=encoder,retrieval=retrieval)
            paths[encoder+'-encoder_'+retrieval+'-retrieval']=value
        except BaseException:
            log=run.h.root/'native.log'
            if log.exists():print(log.read_text()[-12000:])
            raise
        finally:run.close()
    return dict(oracle=oracle,paths=paths,corpus_sha256=digest(canonical(corpus)),same_host=True,
        real=['native loop/parser/remember/createMemory/embed/query','E5','Chroma','DeTTa','authenticated HTTPS'],
        fixtures=['scripted external model/channel','unused history/global promoted context','creation/enrichment clocks'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--corpus',required=True);parser.add_argument('--evidence',required=True)
    parser.add_argument('--caller-runtime');args=parser.parse_args()
    options={'caller_runtime':args.caller_runtime} if args.caller_runtime else {}
    Path(args.evidence).write_bytes(canonical(compare(json.loads(Path(args.corpus).read_text()),**options)))
