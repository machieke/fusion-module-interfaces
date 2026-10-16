"""Independent bounded atomic-file AtomStorage + source CONTRACT FIXTURE.

A single atomic document commits payload, acceptance and feed metadata. No
AtomOwner inheritance, SQLite, or real provider helpers. No DA claim.
"""
from contextlib import contextmanager
import base64
import fcntl
import json
import os
from pathlib import Path
import tempfile
import uuid
from .. import lookup_contracts as c
from ..contracts import canonical,digest,require,ContractError
from ..ports import AtomEnvelope

class FileFeedFixture:
    def __init__(self,path,access,hook=lambda stage:None):
        self.path,self.access,self.hook=Path(path),access,hook
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.lock():
            if self.path.exists():require(self.load()['profile']==c.FEED,'UNSUPPORTED_PROFILE')
            else:self.save({'profile':c.FEED,'source':str(uuid.uuid4()),'atoms':[]})
    @contextmanager
    def lock(self):
        with self.path.with_suffix('.lock').open('a+b') as f:
            fcntl.flock(f,fcntl.LOCK_EX);yield
    def load(self):
        value=json.loads(self.path.read_bytes());require(type(value) is dict and value.get('profile')==c.FEED,'UNSUPPORTED_PROFILE');return value
    def save(self,value):
        with tempfile.NamedTemporaryFile(dir=self.path.parent,delete=False) as f:
            f.write(canonical(value));f.flush();os.fsync(f.fileno());name=f.name
        os.replace(name,self.path)
        fd=os.open(self.path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def create(self,command,content_type,data):
        c.mutation(command);c.integer(len(data),1,c.MAX_BYTES)
        principal=self.access.authorize(command.scope_ref,'create');identity=[principal,command.scope_ref,command.idempotency_key]
        fingerprint=digest(canonical([content_type,digest(data)]))
        with self.lock():
            state=self.load()
            for row in state['atoms']:
                if row['identity']==identity:
                    require(row['fingerprint']==fingerprint,'CONFLICT');self.access.authorize(command.scope_ref,'create');return c.copy(row['write'])
            require(len(state['atoms'])<c.MAX_ATOMS,'OVERLOADED')
            seq=1+sum(r['write']['ref']['scope_ref']==command.scope_ref for r in state['atoms'])
            write={'ref':{'scope_ref':command.scope_ref,'id':str(uuid.uuid5(uuid.UUID(state['source']),canonical(identity).decode())),
                          'revision':1,'digest':digest(data)},'receipt':{'provider':'contract-fixture-files/1',
                          'durability':'local-files-process-restart','evidence':{'classification':'contract-test-provider','persistence':'atomic-owner-document'}}}
            state['atoms'].append({'identity':identity,'fingerprint':fingerprint,'sequence':seq,'write':write,'content_type':content_type,
                                   'bytes':base64.b64encode(data).decode(),'size':len(data)})
            self.access.authorize(command.scope_ref,'create');self.save(state)
        self.hook('after_atom_feed_commit');return c.copy(write)
    def get(self,ref):
        self.access.authorize(ref['scope_ref'],'get')
        with self.lock():state=self.load()
        for row in state['atoms']:
            if row['write']['ref']['scope_ref']==ref['scope_ref'] and row['write']['ref']['id']==ref['id']:
                require(row['write']['ref']==ref,'CONFLICT')
                try:data=base64.b64decode(row['bytes'],validate=True)
                except ValueError:raise ContractError('NOT_AVAILABLE') from None
                require(digest(data)==ref['digest'],'NOT_AVAILABLE');self.access.authorize(ref['scope_ref'],'get')
                return AtomEnvelope(c.copy(ref),row['content_type'],data)
        raise ContractError('NOT_FOUND')
    def getMany(self,refs):return tuple(self.get(ref) for ref in refs)
    def availability(self,ref):
        self.access.authorize(ref['scope_ref'],'availability');self.get(ref)
        return {'available':True,'present_shares':1,'threshold':1,'bytes':None,'content_hash':ref['digest']}
    def head(self,scope):
        self.access.authorize(scope,'head')
        with self.lock():state=self.load()
        result=c.make_head(state['source'],scope,sum(r['write']['ref']['scope_ref']==scope for r in state['atoms']))
        self.access.authorize(scope,'head');return result
    def readCommits(self,scope,after,through,limit):
        self.access.authorize(scope,'readCommits');through=c.head(through,scope);c.integer(after,0,through['sequence']);c.integer(limit,1,c.PAGE)
        with self.lock():state=self.load()
        require(through['source']==state['source'],'CONFLICT')
        scoped=[r for r in state['atoms'] if r['write']['ref']['scope_ref']==scope]
        require(through['sequence']<=len(scoped),'CONFLICT')
        selected=scoped[after:min(after+limit,through['sequence'])]
        records=[dict(sequence=r['sequence'],ref=r['write']['ref'],content_type=r['content_type'],size=r['size']) for r in selected]
        self.access.authorize(scope,'readCommits')
        return c.commits(dict(through=through,after=after,records=records,next_after=after+len(records),complete=after+len(records)==through['sequence']),scope,after,through,limit)
