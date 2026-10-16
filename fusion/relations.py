"""Accepted structural records, replay and adjacency: one Relations owner."""
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
import uuid
from . import lookup_contracts as c
from .contracts import canonical,digest,require,ContractError
from .ports import Mutation
from .responses import envelope

class RelationOwner:
    def __init__(self,path,atoms,access,schemas,hook=lambda stage:None):
        self.path,self.atoms,self.access,self.hook=Path(path),atoms,access,hook
        self.schemas=c.schemas(schemas);self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(self.connect()) as db,db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables=={'relation_meta','accepted','commands','incidence'},'UNSUPPORTED_PROFILE')
            db.execute('CREATE TABLE IF NOT EXISTS relation_meta(value TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS accepted(structure TEXT PRIMARY KEY, scope TEXT, sequence INTEGER, value TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, structure TEXT, value TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS incidence(scope TEXT, sequence INTEGER, endpoint TEXT, direction TEXT, structure TEXT, UNIQUE(scope,sequence,endpoint,direction))')
            old=db.execute('SELECT value FROM relation_meta').fetchone()
            if old:
                self.meta=json.loads(old[0]);require(self.meta['profile']==c.RELATIONS and self.meta['schemas']==self.schemas,'UNSUPPORTED_PROFILE')
            else:
                self.meta={'profile':c.RELATIONS,'schemas':self.schemas,'source':str(uuid.uuid4()),'secret':secrets.token_hex(32)}
                db.execute('INSERT INTO relation_meta VALUES(?)',(canonical(self.meta).decode(),))
    def connect(self):
        db=sqlite3.connect(self.path,timeout=1);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db
    def assertRelation(self,command,relation_type,roles,directed):
        c.mutation(command);principal=self.access.authorize(command.scope_ref,'assertRelation')
        body=c.relation_body(command.scope_ref,relation_type,roles,directed,self.schemas)
        structure=digest(canonical(body));key=digest(canonical([principal,command.scope_ref,command.idempotency_key]))
        # Freeze semantic replay before a foreign owner's durable write.
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT structure FROM commands WHERE id=?',(key,)).fetchone()
            if old:require(old[0]==structure,'CONFLICT')
            else:
                require(db.execute('SELECT count(*) FROM commands').fetchone()[0]<c.MAX_COMMANDS,'OVERLOADED')
                self.access.authorize(command.scope_ref,'assertRelation');db.execute('INSERT INTO commands VALUES(?,?,NULL)',(key,structure))
        for _,endpoint in body['roles']:
            result=self.atoms.get(endpoint);envelope(result,endpoint)
        write=self.atoms.create(Mutation(command.scope_ref,'relation/'+structure),c.RELATION,canonical(body))
        c.ref(write['ref'],command.scope_ref);require(write['ref']['digest']==structure,'NOT_AVAILABLE')
        self.hook('after_relation_payload')
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT value FROM accepted WHERE structure=?',(structure,)).fetchone()
            if old:
                value=json.loads(old[0]);require(value['ref']==write['ref'],'CONFLICT')
            else:
                require(db.execute('SELECT count(*) FROM accepted').fetchone()[0]<c.MAX_RELATIONS,'OVERLOADED')
                seq=db.execute('SELECT coalesce(max(sequence),0)+1 FROM accepted WHERE scope=?',(command.scope_ref,)).fetchone()[0]
                value={'ref':write['ref'],'body':body,'accepted':c.make_head(self.meta['source'],command.scope_ref,seq,c.RELATIONS)}
                db.execute('INSERT INTO accepted VALUES(?,?,?,?)',(structure,command.scope_ref,seq,canonical(value).decode()))
                for direction,indexes in [('outgoing',body['schema']['origins']),('incoming',body['schema']['destinations'])]:
                    for index in indexes:
                        db.execute('INSERT OR IGNORE INTO incidence VALUES(?,?,?,?,?)',(command.scope_ref,seq,canonical(body['roles'][index][1]).decode(),direction,structure))
            self.access.authorize(command.scope_ref,'assertRelation')
            db.execute('UPDATE commands SET value=? WHERE id=?',(canonical(value).decode(),key))
        self.hook('after_relation_commit');self.access.authorize(command.scope_ref,'assertRelation');return c.relation(value,command.scope_ref)
    def getRelation(self,ref):
        scope=c.scope_of(ref);self.access.authorize(scope,'getRelation');ref=c.ref(ref,scope)
        with closing(self.connect()) as db:
            rows=db.execute('SELECT value FROM accepted WHERE scope=?',(scope,)).fetchall()
        value=next((json.loads(r[0]) for r in rows if json.loads(r[0])['ref']['id']==ref['id']),None)
        require(value is not None,'NOT_FOUND');require(value['ref']==ref,'CONFLICT')
        result=self.atoms.get(ref);envelope(result,ref)
        require(result.content_type==c.RELATION and result.bytes==canonical(value['body']),'NOT_AVAILABLE')
        self.access.authorize(scope,'getRelation');return c.relation(value,scope,ref)
    def outgoing(self,ref,limit,cursor=None,snapshot=None):return self.traverse('outgoing',ref,limit,cursor,snapshot)
    def incoming(self,ref,limit,cursor=None,snapshot=None):return self.traverse('incoming',ref,limit,cursor,snapshot)
    def traverse(self,direction,ref,limit,cursor,snapshot):
        scope=c.scope_of(ref);principal=self.access.authorize(scope,direction);ref=c.ref(ref,scope);c.integer(limit,1,c.PAGE)
        require(cursor is None or (type(cursor) is str and 1<=len(cursor)<=4096))
        envelope(self.atoms.get(ref),ref)
        binding=digest(canonical([direction,ref,limit,principal]))
        with closing(self.connect()) as db:
            seq=db.execute('SELECT coalesce(max(sequence),0) FROM accepted WHERE scope=?',(scope,)).fetchone()[0]
            current=c.make_head(self.meta['source'],scope,seq,c.RELATIONS)
            if cursor:
                decoded=c.unseal(self.meta['secret'],cursor)
                require(type(decoded) is dict and set(decoded)=={'binding','at','after'} and decoded['binding']==binding,'CONFLICT')
                if snapshot is not None:require(snapshot==decoded['at'],'CONFLICT')
                at=c.head(decoded['at'],scope,c.RELATIONS);after=decoded['after'];c.integer(after,0,at['sequence'])
            else:at=c.head(snapshot,scope,c.RELATIONS) if snapshot is not None else current;after=0
            require(at['source']==current['source'] and at['sequence']<=seq,'CONFLICT')
            rows=db.execute('SELECT a.sequence,a.value FROM incidence i JOIN accepted a ON a.structure=i.structure WHERE i.scope=? AND i.endpoint=? AND i.direction=? AND i.sequence>? AND i.sequence<=? ORDER BY i.sequence LIMIT ?',
                (scope,canonical(ref).decode(),direction,after,at['sequence'],limit+1)).fetchall()
        chosen=rows[:limit];more=len(rows)>limit
        result={'refs':[json.loads(r[1])['ref'] for r in chosen],'sequences':[r[0] for r in chosen],
                'at':at,'binding':binding,'page_complete':not more,'cursor':c.seal(self.meta['secret'],{'binding':binding,'at':at,'after':chosen[-1][0]}) if more else None}
        self.access.authorize(scope,direction);return c.relation_page(result,ref,direction,limit,principal,snapshot)
