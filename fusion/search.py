"""SQLite exact-attribute projection. All source reads use declared owner ports."""
from contextlib import closing
import json
from pathlib import Path
import secrets
import sqlite3
import time
import uuid
from . import lookup_contracts as c
from .contracts import canonical,digest,require,ContractError
from .responses import envelope

class SearchOwner:
    def __init__(self,path,atoms,source,access,scope,hook=lambda stage:None):
        self.path,self.atoms,self.source,self.access,self.scope,self.hook=Path(path),atoms,source,access,scope,hook
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(self.connect()) as db,db:
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables=={'projection_meta','records','rebuilds'},'UNSUPPORTED_PROFILE')
            db.execute('CREATE TABLE IF NOT EXISTS projection_meta(value TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS records(sequence INTEGER PRIMARY KEY,ref TEXT,fields TEXT)')
            db.execute('CREATE TABLE IF NOT EXISTS rebuilds(id TEXT PRIMARY KEY,value TEXT)')
            row=db.execute('SELECT value FROM projection_meta').fetchone()
            if row:
                value=json.loads(row[0]);require(value['profile']==c.SEARCH and value['extraction']==c.EXTRACTION and value['at']['scope_ref']==scope,'UNSUPPORTED_PROFILE')
            else:
                observed=c.head(source.head(scope),scope)
                value={'profile':c.SEARCH,'extraction':c.EXTRACTION,'generation':str(uuid.uuid4()),'secret':secrets.token_hex(32),
                    'at':{**observed,'sequence':0},'observed':{'head':observed,'via':'maintenance.head','observed_ms':time.time_ns()//1_000_000},
                    'target':None,'rebuilding':False,'tail':None,'seen':[]}
                db.execute('INSERT INTO projection_meta VALUES(?)',(canonical(value).decode(),))
    def connect(self):
        db=sqlite3.connect(self.path,timeout=1);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db
    def state(self,db):return json.loads(db.execute('SELECT value FROM projection_meta').fetchone()[0])
    def catchUp(self,scope,limit):
        self.access.authorize(scope,'catchUp');require(scope==self.scope,'UNAUTHORIZED');c.integer(limit,1,c.BATCH)
        with closing(self.connect()) as db:before=self.state(db)
        at=before['at'];observed=c.head(self.source.head(scope),scope);observed_ms=time.time_ns()//1_000_000
        require(observed['source']==at['source'] and observed['sequence']>=at['sequence'],'CONFLICT')
        target=before['target'] if before['rebuilding'] else observed
        require(observed['sequence']>=target['sequence'],'NOT_AVAILABLE')
        try:
            if at['sequence']:
                anchor=c.commits(self.source.readCommits(scope,at['sequence']-1,at,1),scope,at['sequence']-1,at,1)
                require(digest(canonical(anchor['records'][0]))==before['tail'],'CONFLICT')
            page=c.commits(self.source.readCommits(scope,at['sequence'],target,limit),scope,at['sequence'],target,limit)
        except ContractError as error:raise c.ProjectionError('source-prefix',at['sequence']+1,error.code) from None
        prepared=[];ignored=0;seen=list(before['seen'])
        for entry in page['records']:
            try:
                identity=canonical(entry['ref']).decode();require(identity not in seen,'CONFLICT');seen.append(identity)
                payload=self.atoms.get(entry['ref']);envelope(payload,entry['ref'])
                require(payload.content_type==entry['content_type'] and len(payload.bytes)==entry['size'],'NOT_AVAILABLE')
                if entry['content_type']!=c.KNOWLEDGE:ignored+=1;continue
                fields=c.record(payload.bytes)
            except ContractError as error:raise c.ProjectionError('enrolled-record',entry['sequence'],error.code) from None
            prepared.append((entry['sequence'],entry['ref'],fields))
        after=c.copy(before);after['seen']=seen;after['at']={**at,'sequence':page['next_after']}
        after['observed']={'head':observed,'via':'maintenance.head','observed_ms':observed_ms}
        if page['records']:after['tail']=digest(canonical(page['records'][-1]))
        if before['rebuilding'] and page['complete']:after['rebuilding']=False
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');require(self.state(db)==before,'CONFLICT')
            require(db.execute('SELECT count(*) FROM records').fetchone()[0]+len(prepared)<=c.MAX_RECORDS,'OVERLOADED')
            for seq,ref,fields in prepared:db.execute('INSERT INTO records VALUES(?,?,?)',(seq,canonical(ref).decode(),canonical(fields).decode()))
            self.hook('before_checkpoint_commit')
            self.access.authorize(scope,'catchUp');db.execute('UPDATE projection_meta SET value=?',(canonical(after).decode(),))
        self.hook('after_checkpoint_commit');self.access.authorize(scope,'catchUp')
        return {'at':after['at'],'target':target,'generation':after['generation'],'rebuilding':after['rebuilding'],
                'processed':len(page['records']),'ignored':ignored}
    def beginRebuild(self,command):
        c.mutation(command);principal=self.access.authorize(command.scope_ref,'beginRebuild');require(command.scope_ref==self.scope,'UNAUTHORIZED')
        key=digest(canonical([principal,command.scope_ref,command.idempotency_key]))
        with closing(self.connect()) as db:
            before=self.state(db);old=db.execute('SELECT value FROM rebuilds WHERE id=?',(key,)).fetchone()
        if old:self.access.authorize(command.scope_ref,'beginRebuild');return json.loads(old[0])
        require(not before['rebuilding'],'CONFLICT')
        target=c.head(self.source.head(self.scope),self.scope);require(target['source']==before['at']['source'],'CONFLICT')
        after={**before,'at':{**target,'sequence':0},'generation':str(uuid.uuid4()),'tail':None,'seen':[],'target':target,'rebuilding':target['sequence']>0,
               'observed':{'head':target,'via':'maintenance.head','observed_ms':time.time_ns()//1_000_000}}
        receipt={'generation':after['generation'],'target':target}
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');require(self.state(db)==before,'CONFLICT')
            require(db.execute('SELECT count(*) FROM rebuilds').fetchone()[0]<64,'OVERLOADED')
            self.access.authorize(command.scope_ref,'beginRebuild')
            db.execute('DELETE FROM records');db.execute('UPDATE projection_meta SET value=?',(canonical(after).decode(),))
            db.execute('INSERT INTO rebuilds VALUES(?,?)',(key,canonical(receipt).decode()))
        self.hook('after_rebuild_begin');return receipt
    def query(self,query):
        request=c.query(query);principal=self.access.authorize(request.scope_ref,'query');require(request.scope_ref==self.scope,'UNAUTHORIZED')
        with closing(self.connect()) as db:
            db.execute('BEGIN');state=self.state(db)
            require(request.minimum['source']==state['at']['source'],'CONFLICT')
            require(not state['rebuilding'] and state['at']['sequence']>=request.minimum['sequence'],'NOT_AVAILABLE')
            binding=c.query_binding(request,principal)
            if request.cursor:
                frozen=c.unseal(state['secret'],request.cursor)
                require(type(frozen) is dict and set(frozen)=={'binding','generation','at','observed','after'},'CONFLICT')
                require(frozen['binding']==binding and frozen['generation']==state['generation'],'CONFLICT')
                at=c.head(frozen['at'],self.scope);observed=frozen['observed'];after=frozen['after'];c.integer(after,0,at['sequence'])
                require(at['source']==state['at']['source'] and request.minimum['sequence']<=at['sequence']<=state['at']['sequence'],'CONFLICT')
            else:at=state['at'];observed=state['observed'];after=0
            rows=db.execute('SELECT sequence,ref,fields FROM records WHERE sequence>? AND sequence<=? ORDER BY sequence',(after,at['sequence'])).fetchall()
        matched=[(seq,json.loads(ref)) for seq,ref,fields in rows if c.matches(json.loads(fields),request.expression)]
        chosen=matched[:request.limit];more=len(matched)>request.limit
        token=c.seal(state['secret'],dict(binding=binding,generation=state['generation'],at=at,observed=observed,after=chosen[-1][0])) if more else None
        result={'refs':[r for _,r in chosen],'at':at,'observed_head':observed,'generation':state['generation'],'profile':c.SEARCH,'extraction':c.EXTRACTION,
                'binding':binding,'prefix_complete':True,'page_complete':not more,'fresh':True,'at_observed_head':at==observed['head'],'cursor':token}
        self.access.authorize(request.scope_ref,'query');return c.search_result(result,request,principal)
