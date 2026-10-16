"""Independent persistent exact-filter Search CONTRACT FIXTURE.

Own atomic-file state and transition implementation; shares DTO validation only.
No SQLite, primary Search imports, owner inheritance or answer-list seeding.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
import uuid
from .. import lookup_contracts as c
from ..contracts import canonical,digest,require,ContractError
from ..responses import envelope

class FileSearchFixture:
    def __init__(self,path,atoms,source,access,scope,hook=lambda stage:None):
        self.path,self.atoms,self.source,self.access,self.scope,self.hook=Path(path),atoms,source,access,scope,hook
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.lock():
            if self.path.exists():
                s=self.load();require(s['profile']==c.SEARCH and s['extraction']==c.EXTRACTION and s['watermark']['scope_ref']==scope,'UNSUPPORTED_PROFILE')
            else:
                h=c.head(source.head(scope),scope)
                self.save({'profile':c.SEARCH,'extraction':c.EXTRACTION,'generation':str(uuid.uuid4()),'secret':secrets.token_hex(32),
                    'watermark':{**h,'sequence':0},'observation':{'head':h,'via':'maintenance.head','observed_ms':time.time_ns()//1_000_000},
                    'building':False,'target':None,'checkpoint_entry':None,'seen':[],'documents':[],'rebuild_commands':{}})
    @contextmanager
    def lock(self):
        with self.path.with_suffix('.lock').open('a+b') as lock:fcntl.flock(lock,fcntl.LOCK_EX);yield
    def load(self):return json.loads(self.path.read_bytes())
    def save(self,value):
        with tempfile.NamedTemporaryFile(dir=self.path.parent,delete=False) as f:
            f.write(canonical(value));f.flush();os.fsync(f.fileno());temporary=f.name
        os.replace(temporary,self.path)
        fd=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def catchUp(self,scope,limit):
        self.access.authorize(scope,'catchUp');require(scope==self.scope,'UNAUTHORIZED');c.integer(limit,1,c.BATCH)
        with self.lock():before=self.load()
        w=before['watermark'];h=c.head(self.source.head(scope),scope);observed_ms=time.time_ns()//1_000_000
        require(h['source']==w['source'] and h['sequence']>=w['sequence'],'CONFLICT')
        stop=before['target'] if before['building'] else h
        require(stop['sequence']<=h['sequence'],'NOT_AVAILABLE')
        try:
            if w['sequence']:
                previous=c.commits(self.source.readCommits(scope,w['sequence']-1,w,1),scope,w['sequence']-1,w,1)
                require(previous['records'][0]==before['checkpoint_entry'],'CONFLICT')
            batch=c.commits(self.source.readCommits(scope,w['sequence'],stop,limit),scope,w['sequence'],stop,limit)
        except ContractError as error:raise c.ProjectionError('source-prefix',w['sequence']+1,error.code) from None
        proposed=c.copy(before);ignored=0
        for change in batch['records']:
            try:
                identity=canonical(change['ref']).decode();require(identity not in proposed['seen'],'CONFLICT');proposed['seen'].append(identity)
                item=self.atoms.get(change['ref']);envelope(item,change['ref'])
                require(item.content_type==change['content_type'] and len(item.bytes)==change['size'],'NOT_AVAILABLE')
                if change['content_type']!=c.KNOWLEDGE:ignored+=1;continue
                attributes=c.record(item.bytes)
            except ContractError as error:raise c.ProjectionError('enrolled-record',change['sequence'],error.code) from None
            proposed['documents'].append({'number':change['sequence'],'reference':change['ref'],'attributes':attributes})
        require(len(proposed['documents'])<=c.MAX_RECORDS,'OVERLOADED')
        proposed['watermark']['sequence']=batch['next_after']
        proposed['observation']={'head':h,'via':'maintenance.head','observed_ms':observed_ms}
        if batch['records']:proposed['checkpoint_entry']=batch['records'][-1]
        if proposed['building'] and batch['complete']:proposed['building']=False
        with self.lock():
            require(self.load()==before,'CONFLICT');self.hook('before_checkpoint_commit');self.access.authorize(scope,'catchUp');self.save(proposed)
        self.hook('after_checkpoint_commit');self.access.authorize(scope,'catchUp')
        return {'at':proposed['watermark'],'target':stop,'generation':proposed['generation'],'rebuilding':proposed['building'],
                'processed':len(batch['records']),'ignored':ignored}
    def beginRebuild(self,command):
        c.mutation(command);who=self.access.authorize(command.scope_ref,'beginRebuild');require(command.scope_ref==self.scope,'UNAUTHORIZED')
        key=digest(canonical([who,command.scope_ref,command.idempotency_key]))
        with self.lock():before=self.load()
        if key in before['rebuild_commands']:
            self.access.authorize(command.scope_ref,'beginRebuild');return before['rebuild_commands'][key]
        require(not before['building'],'CONFLICT');target=c.head(self.source.head(self.scope),self.scope)
        require(target['source']==before['watermark']['source'] and target['sequence']>=before['watermark']['sequence'],'CONFLICT');require(len(before['rebuild_commands'])<64,'OVERLOADED')
        proposed=c.copy(before);proposed.update(generation=str(uuid.uuid4()),documents=[],checkpoint_entry=None,seen=[],
            watermark={**target,'sequence':0},target=target,building=target['sequence']>0,
            observation={'head':target,'via':'maintenance.head','observed_ms':time.time_ns()//1_000_000})
        result={'generation':proposed['generation'],'target':target};proposed['rebuild_commands'][key]=result
        with self.lock():
            require(self.load()==before,'CONFLICT');self.access.authorize(command.scope_ref,'beginRebuild');self.save(proposed)
        self.hook('after_rebuild_begin');return result
    def query(self,query):
        q=c.query(query);who=self.access.authorize(q.scope_ref,'query');require(q.scope_ref==self.scope,'UNAUTHORIZED')
        with self.lock():state=self.load()
        require(q.minimum['source']==state['watermark']['source'],'CONFLICT')
        require(not state['building'] and state['watermark']['sequence']>=q.minimum['sequence'],'NOT_AVAILABLE')
        binding=c.query_binding(q,who)
        if q.cursor:
            token=c.unseal(state['secret'],q.cursor)
            require(type(token) is dict and set(token)=={'binding','generation','watermark','observation','after'},'CONFLICT')
            require(token['binding']==binding and token['generation']==state['generation'],'CONFLICT')
            at=c.head(token['watermark'],self.scope);observation=token['observation'];after=token['after'];c.integer(after,0,at['sequence'])
            require(at['source']==state['watermark']['source'] and q.minimum['sequence']<=at['sequence']<=state['watermark']['sequence'],'CONFLICT')
        else:at=state['watermark'];observation=state['observation'];after=0
        hits=[]
        for row in state['documents']:
            if not after<row['number']<=at['sequence']:continue
            accepted=True
            for clause in q.expression['all']:
                if clause['field'] not in row['attributes'] or row['attributes'][clause['field']]!=clause['eq']:
                    accepted=False;break
            if accepted:hits.append(row)
        hits.sort(key=lambda item:item['number']);chosen=hits[:q.limit];remaining=len(hits)>q.limit
        cursor=c.seal(state['secret'],{'binding':binding,'generation':state['generation'],'watermark':at,'observation':observation,'after':chosen[-1]['number']}) if remaining else None
        result={'refs':[row['reference'] for row in chosen],'at':at,'observed_head':observation,'generation':state['generation'],
            'profile':c.SEARCH,'extraction':c.EXTRACTION,'binding':binding,'prefix_complete':True,'page_complete':not remaining,
            'fresh':True,'at_observed_head':at==observation['head'],'cursor':cursor}
        self.access.authorize(q.scope_ref,'query');return c.search_result(result,q,who)
