"""Application-owned bounded read capture. No jobs, outbox or mailbox for reads."""
from dataclasses import asdict
import json
from pathlib import Path
import time
from . import vector_contracts as c
from .contracts import canonical,digest,require,decode
from .registry import descriptor_read,selection_token
from .vector_composition import select
from .vector_transport import binding
from .ports import AtomEnvelope
from .responses import envelope

MAX_CALLS=64
MAX_QUERIES=3


def configuration(path):
    cfg=json.loads(Path(path).read_text())
    require(cfg['sharing']==c.PRIVACY and cfg['profile']==c.PROFILE,'UNSUPPORTED_PROFILE')
    require(type(cfg['principal']) is str and 1<=len(cfg['principal'])<=80)
    c.snapshot(cfg['snapshot'],cfg['scope']);require(cfg['snapshot']['embedding']==cfg['embedding'],'UNSUPPORTED_PROFILE')
    require(type(cfg['queries']) is list and 1<=len(cfg['queries'])<=32)
    for query in cfg['queries']:c.query_text(query)
    require(type(cfg.get('require_ready',False)) is bool)
    chosen=select([descriptor_read(d) for d in cfg['catalogue']],cfg['embedding'],cfg.get('require_ready',False))
    frozen={k:cfg[k] for k in ('principal','scope','sharing','profile','embedding','snapshot','queries','metadata_seal','native_config')}
    require(cfg['native_config']=={'recall':2,'similarity':4,'inflation':4},'UNSUPPORTED_PROFILE')
    frozen['selections']={n:selection_token(d) for n,d in chosen.items()}
    if cfg.get('require_ready'):frozen['require_ready']=True
    return cfg,chosen,frozen


class MemoryRead:
    def __init__(self,application):
        self.app=application;self.db=application.db
        self.db.execute('''CREATE TABLE IF NOT EXISTS app_memory_reads (
            id TEXT PRIMARY KEY, request TEXT NOT NULL, calls INTEGER NOT NULL DEFAULT 0,
            queries INTEGER NOT NULL DEFAULT 0, candidates TEXT, payloads TEXT, enrichment REAL)''')
        self.db.commit()

    def current(self):
        require(self.app.current is not None,'CONFLICT')
        row=self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?',self.app.current).fetchone()
        require(row is not None and row['premises'] is not None,'CONFLICT')
        require(json.loads(row['premises'])['profile']==c.PROFILE,'UNSUPPORTED_PROFILE');return row

    def settings(self,row=None):
        cfg,chosen,frozen=configuration(self.app.config['memory_read_config'])
        require(frozen==self.app.binding['memory'],'CONFLICT')
        if getattr(self.app,'append_enabled',False):
            row=self.current() if row is None else row
            view=self.app.write.view_for(row)
            cfg={**cfg,'snapshot':view['snapshot'],'metadata_seal':view['metadata_seal']}
        return cfg,chosen

    def call(self,row,name,op,body,*,bounded=True):
        cfg,chosen=self.settings(row);d=chosen[name]
        if bounded:require(time.time_ns()//1_000_000<=row['deadline'],'DEADLINE_EXCEEDED')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            state=self.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
            require(state is not None and state['calls']<MAX_CALLS,'OVERLOADED')
            if op=='query':require(state['queries']<MAX_QUERIES,'OVERLOADED')
            self.db.execute('UPDATE app_memory_reads SET calls=calls+1, queries=queries+? WHERE id=?',(int(op=='query'),row['id']))
        self.app.hook('after_read_reservation')
        req=dict(request_id=row['id'],scope=cfg['scope'],interface_ref=dict(id=name,version=d.version),operation=op,
                 profile=next(iter(d.profiles)),selection=selection_token(d),body=body)
        result=binding(cfg,chosen).invoke(req)
        if bounded:require(time.time_ns()//1_000_000<=row['deadline'],'DEADLINE_EXCEEDED')
        return result

    def authorize(self,row):
        if getattr(self.app,'evidence_enabled',False):self.app.evidence.validate_view(self.app.write.view_for(row))
        if self.app.embedding_enabled:self.app.embedding.authorize(row)
        cfg,_=self.settings(row);intent=json.loads(row['premises'])
        require(intent['arguments']['query'] in cfg['queries'],'UNAUTHORIZED')
        result=self.call(row,'search','authorize-ready' if cfg.get('require_ready') else 'authorize',dict(query=intent['arguments']['query'],snapshot=cfg['snapshot']),bounded=False)
        require(result=={'authorized':True},'NOT_AVAILABLE')

    def retrieve(self,vector,k):
        row=self.current();cfg,_=self.settings(row)
        if self.app.embedding_enabled:
            require(vector==self.app.embedding.selected(row)['vector'],'CONFLICT')
        request=c.query(asdict(c.VectorQuery(row['id'],cfg['scope'],cfg['snapshot'],c.vector(vector),k,row['deadline'])))
        encoded=canonical(request).decode()
        with self.db:
            old=self.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
            require(old is None or old['request']==encoded,'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO app_memory_reads(id,request) VALUES(?,?)',(row['id'],encoded))
        self.app.hook('after_read_bind');self.authorize(row)
        state=self.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
        if state['candidates'] is None:
            candidates=c.result(self.call(row,'search','query',request),request)
            self.app.hook('after_read_reply')
            with self.db:self.db.execute('UPDATE app_memory_reads SET candidates=? WHERE id=?',(canonical(candidates).decode(),row['id']))
            self.app.hook('after_candidate_capture')
        else:candidates=c.result(json.loads(state['candidates']),request)
        if state['payloads'] is None:
            rows=[]
            for offset in range(0,len(candidates['hits']),8):
                hits=candidates['hits'][offset:offset+8]
                values=self.call(row,'atom.storage','getMany',dict(refs=[x['ref'] for x in hits]))
                require(type(values) is list and len(values)==len(hits),'NOT_AVAILABLE')
                for hit,value in zip(hits,values):
                    c.fields(value,'ref content_type data')
                    item=AtomEnvelope(value['ref'],value['content_type'],decode(value['data']))
                    envelope(item,hit['ref']);require(item.content_type==c.PAYLOAD,'NOT_AVAILABLE')
                    p=c.payload(json.loads(item.bytes),cfg['scope'],cfg['snapshot']['corpus'])
                    require(canonical(p)==item.bytes and p['uuid']==hit['uuid'],'NOT_AVAILABLE')
                    rows.append([p['uuid'],p['time'],p['content'],hit['distance']])
            self.authorize(row)
            with self.db:self.db.execute('UPDATE app_memory_reads SET payloads=? WHERE id=?',(canonical(rows).decode(),row['id']))
            self.app.hook('after_payload_validation')
        else:rows=json.loads(state['payloads'])
        return rows

    def clock(self,observed):
        row=self.current();state=self.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
        require(state is not None and state['payloads'] is not None,'NOT_AVAILABLE')
        if state['enrichment'] is None:
            require(type(observed) in (int,float) and 0<observed<2**53)
            with self.db:self.db.execute('UPDATE app_memory_reads SET enrichment=? WHERE id=?',(observed,row['id']))
            return observed
        return state['enrichment']

    def captured(self):
        row=self.current();return row['result'] is not None

    def replay(self,row=None):
        row=self.current() if row is None else row
        require(row['result'] is not None,'NOT_AVAILABLE');self.authorize(row);return row['result']

    def capture(self,value):
        row=self.current();self.authorize(row)
        require(type(value) is str and len(value.encode())<=50000,'NOT_AVAILABLE')
        state=self.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
        require(state is not None and state['payloads'] is not None and state['enrichment'] is not None,'NOT_AVAILABLE')
        require(row['result'] is None or row['result']==value,'CONFLICT')
        with self.db:self.db.execute('UPDATE app_occurrences SET result=?,done=1 WHERE id=?',(value,row['id']))
        self.app.hook('after_native_result_capture');return value
