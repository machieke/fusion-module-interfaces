"""Bounded query -> accepted relations -> exact payload consumer; own journal only."""
from contextlib import closing
from dataclasses import asdict,replace
import json
from pathlib import Path
import sqlite3
from . import lookup_contracts as c
from .contracts import canonical,digest,require
from .responses import envelope

class LookupConsumer:
    def __init__(self,path,atoms,relations,search,access,selections,hook=lambda stage:None):
        self.path,self.atoms,self.relations,self.search,self.access,self.selections,self.hook=Path(path),atoms,relations,search,access,c.copy(selections),hook
        with closing(self.connect()) as db,db:db.execute('CREATE TABLE IF NOT EXISTS lookups(id TEXT PRIMARY KEY,intent TEXT,value TEXT)')
    def connect(self):
        db=sqlite3.connect(self.path,timeout=1);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db
    def authorize(self,scope):
        for name,ops in [('atom.storage',('get','getMany')),('relations',('getRelation','outgoing','incoming')),('search',('query',))]:
            for op in ops:principal=self.access[name].authorize(scope,op)
        return principal
    def save(self,key,before,after,scope):
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT value FROM lookups WHERE id=?',(key,)).fetchone()
            require(json.loads(row[0])==before,'CONFLICT');self.authorize(scope)
            db.execute('UPDATE lookups SET value=? WHERE id=?',(canonical(after).decode(),key))
    def lookup(self,command,query):
        c.mutation(command);q=c.query(query);require(q.scope_ref==command.scope_ref and q.cursor is None)
        principal=self.authorize(q.scope_ref);key=digest(canonical([principal,q.scope_ref,command.idempotency_key]))
        intent=canonical([asdict(q),self.selections]).decode()
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT intent,value FROM lookups WHERE id=?',(key,)).fetchone()
            if row:require(row[0]==intent,'CONFLICT');state=json.loads(row[1])
            else:
                require(db.execute('SELECT count(*) FROM lookups').fetchone()[0]<64,'OVERLOADED')
                state={'roots':[],'cursor':None,'search':None,'pages':0,'search_done':False,'result':None}
                db.execute('INSERT INTO lookups VALUES(?,?,?)',(key,intent,canonical(state).decode()))
        while not state['search_done']:
            require(state['pages']<8,'OVERLOADED')
            request=replace(q,cursor=state['cursor']);page=c.search_result(self.search.query(request),request,principal,state['search'])
            roots=state['roots']+page['refs'];require(len(roots)<=32 and len({canonical(r) for r in roots})==len(roots),'NOT_AVAILABLE')
            updated={**state,'roots':roots,'cursor':page['cursor'],'search':page if state['search'] is None else state['search'],
                     'pages':state['pages']+1,'search_done':page['page_complete']}
            self.save(key,state,updated,q.scope_ref);state=updated;self.hook('after_lookup_page')
        if state['result'] is not None:self.authorize(q.scope_ref);return c.copy(state['result'])
        # One hop, finite visited sets and per-incidence pagination at a separate fixed head.
        at=None;seen_edges={};payloads={canonical(r).decode():r for r in state['roots']}
        calls={'query':state['pages'],'outgoing':0,'incoming':0,'getRelation':0,'get':0,'getMany':0}
        for root in state['roots']:
            cursor=None;seen_pages=set()
            for _ in range(16):
                page=self.relations.outgoing(root,2,cursor,at);calls['outgoing']+=1
                page=c.relation_page(page,root,'outgoing',2,principal,at);at=page['at']
                for r in page['refs']:
                    identity=canonical(r).decode()
                    if identity in seen_edges:continue
                    require(len(seen_edges)<128,'OVERLOADED')
                    edge=c.relation(self.relations.getRelation(r),q.scope_ref,r);calls['getRelation']+=1
                    require(edge['accepted']['source']==at['source'] and edge['accepted']['sequence']<=at['sequence'],'NOT_AVAILABLE')
                    spec=edge['body']['schema'];roles=edge['body']['roles']
                    require(any(roles[i][1]==root for i in spec['origins']),'NOT_AVAILABLE')
                    for index in spec['destinations']:
                        neighbor=roles[index][1];payloads[canonical(neighbor).decode()]=neighbor;require(len(payloads)<=64,'OVERLOADED')
                        reverse_cursor=None;found=False;previous=set()
                        for _ in range(16):
                            reverse=self.relations.incoming(neighbor,2,reverse_cursor,at);calls['incoming']+=1
                            reverse=c.relation_page(reverse,neighbor,'incoming',2,principal,at)
                            found=found or r in reverse['refs']
                            if reverse['page_complete']:break
                            require(reverse['cursor'] not in previous,'NOT_AVAILABLE');previous.add(reverse['cursor']);reverse_cursor=reverse['cursor']
                        else:require(False,'OVERLOADED')
                        require(found,'NOT_AVAILABLE')
                    seen_edges[identity]=edge
                if page['page_complete']:break
                require(page['cursor'] not in seen_pages,'NOT_AVAILABLE');seen_pages.add(page['cursor']);cursor=page['cursor']
            else:require(False,'OVERLOADED')
        require(len(payloads)<=64,'OVERLOADED');documents=[]
        refs=list(payloads.values())
        if refs:
            first=self.atoms.get(refs[0]);envelope(first,refs[0]);calls['get']+=1
        for offset in range(0,len(refs),8):
            batch=tuple(refs[offset:offset+8]);items=self.atoms.getMany(batch);calls['getMany']+=1
            require(type(items) is tuple and len(items)==len(batch),'NOT_AVAILABLE')
            for r,item in zip(batch,items):
                envelope(item,r);require(item.content_type==c.KNOWLEDGE,'NOT_AVAILABLE');fields=c.record(item.bytes)
                if r in state['roots']:require(c.matches(fields,q.expression),'NOT_AVAILABLE')
                documents.append({'ref':r,'record':fields})
        result={'roots':state['roots'],'relations':list(seen_edges.values()),'documents':documents,'search_at':state['search']['at'],
                'search_generation':state['search']['generation'],'relations_at':at,'calls':calls,'hop_limit':1}
        updated={**state,'result':result};self.save(key,state,updated,q.scope_ref);self.hook('after_lookup_result');return c.copy(result)
