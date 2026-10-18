"""Fresh AtomStorage-owned immutable envelopes and atomic commit metadata.

The source capability interprets neither knowledge fields nor relations. It only
enumerates this owner's accepted opaque envelopes. No foreign database is read.
"""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import uuid
from . import lookup_contracts as c
from .contracts import canonical, digest, require, ContractError
from .ports import AtomEnvelope

class FeedAtomOwner:
    def __init__(self,path,storage,access,hook=lambda stage:None):
        self.path,self.storage,self.access,self.hook=Path(path),storage,access,hook
        self.path.parent.mkdir(parents=True,exist_ok=True)
        if self.path.exists():
            with closing(sqlite3.connect(f'file:{self.path}?mode=ro',uri=True)) as db:
                tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                require(not tables or tables=={'feed_meta','feed_atoms'},'UNSUPPORTED_PROFILE')
        with closing(self.connect()) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS feed_meta(value TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS feed_atoms(scope TEXT, sequence INTEGER, identity TEXT UNIQUE, fingerprint TEXT, value TEXT, payload TEXT, PRIMARY KEY(scope,sequence))')
            row=db.execute('SELECT value FROM feed_meta').fetchone()
            if row:
                meta=json.loads(row[0]);require(meta['profile']==c.FEED,'UNSUPPORTED_PROFILE')
            else:
                require(db.execute('SELECT count(*) FROM feed_atoms').fetchone()[0]==0,'NOT_AVAILABLE')
                meta={'profile':c.FEED,'source':str(uuid.uuid4())};db.execute('INSERT INTO feed_meta VALUES(?)',(canonical(meta).decode(),))
        c.identity(meta['source']);self.source=meta['source']

    def connect(self):
        db=sqlite3.connect(self.path,timeout=1);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db

    def create(self,command,content_type,data):
        c.mutation(command);c.integer(len(data),1,c.MAX_BYTES)
        principal=self.access.authorize(command.scope_ref,'create')
        identity=canonical([principal,command.scope_ref,command.idempotency_key]).decode()
        fingerprint=digest(canonical([content_type,digest(data)]))
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT fingerprint,value FROM feed_atoms WHERE identity=?',(identity,)).fetchone()
            if old:
                require(old[0]==fingerprint,'CONFLICT');self.access.authorize(command.scope_ref,'create')
                return json.loads(old[1])['write']
            require(db.execute('SELECT count(*) FROM feed_atoms').fetchone()[0]<c.MAX_ATOMS,'OVERLOADED')
            seq=db.execute('SELECT coalesce(max(sequence),0)+1 FROM feed_atoms WHERE scope=?',(command.scope_ref,)).fetchone()[0]
            atom_id=str(uuid.uuid5(uuid.UUID(self.source),identity))
            payload,receipt=self.storage.put(command.scope_ref,identity,data)
            self.access.authorize(command.scope_ref,'create')
            write={'ref':{'scope_ref':command.scope_ref,'id':atom_id,'revision':1,'digest':digest(data)},'receipt':receipt}
            value={'write':write,'content_type':content_type,'size':len(data)}
            db.execute('INSERT INTO feed_atoms VALUES(?,?,?,?,?,?)',(command.scope_ref,seq,identity,fingerprint,canonical(value).decode(),payload))
        self.hook('after_atom_feed_commit');return c.copy(write)

    def row(self,ref):
        with closing(self.connect()) as db:
            rows=db.execute('SELECT value,payload FROM feed_atoms WHERE scope=?',(ref['scope_ref'],)).fetchall()
        for encoded,payload in rows:
            value=json.loads(encoded)
            if value['write']['ref']['id']==ref['id']:
                require(value['write']['ref']==ref,'CONFLICT');return value,payload
        raise ContractError('NOT_FOUND')

    def observe(self,command):
        """Optional 1.2 capability: observe acceptance, never create or retry it."""
        c.mutation(command)
        principal=self.access.authorize(command.scope_ref,'observe')
        identity=canonical([principal,command.scope_ref,command.idempotency_key]).decode()
        with closing(self.connect()) as db:
            row=db.execute('SELECT sequence,value FROM feed_atoms WHERE identity=?',(identity,)).fetchone()
        self.access.authorize(command.scope_ref,'observe')
        if row is None:return dict(found=False,write=None,through=None,content_type=None,size=None)
        sequence,encoded=row;value=json.loads(encoded)
        return dict(found=True,write=value['write'],through=c.make_head(self.source,command.scope_ref,sequence),
                    content_type=value['content_type'],size=value['size'])

    def get(self,ref):
        self.access.authorize(ref['scope_ref'],'get');value,payload=self.row(ref)
        try:data=self.storage.get(ref['scope_ref'],payload)
        except ContractError as error:
            if error.code=='NOT_FOUND':raise ContractError('NOT_AVAILABLE') from None
            raise
        require(digest(data)==ref['digest'],'NOT_AVAILABLE');self.access.authorize(ref['scope_ref'],'get')
        return AtomEnvelope(c.copy(ref),value['content_type'],data)

    def getMany(self,refs):return tuple(self.get(ref) for ref in refs)
    def availability(self,ref):
        self.access.authorize(ref['scope_ref'],'availability');_,payload=self.row(ref)
        result=self.storage.availability(ref['scope_ref'],payload);self.access.authorize(ref['scope_ref'],'availability');return result

    def head(self,scope):
        self.access.authorize(scope,'head')
        with closing(self.connect()) as db:seq=db.execute('SELECT coalesce(max(sequence),0) FROM feed_atoms WHERE scope=?',(scope,)).fetchone()[0]
        self.access.authorize(scope,'head');return c.make_head(self.source,scope,seq)

    def readCommits(self,scope,after,through,limit):
        self.access.authorize(scope,'readCommits');through=c.head(through,scope)
        c.integer(after,0,through['sequence']);c.integer(limit,1,c.PAGE)
        require(through['source']==self.source,'CONFLICT')
        with closing(self.connect()) as db:
            highest=db.execute('SELECT coalesce(max(sequence),0) FROM feed_atoms WHERE scope=?',(scope,)).fetchone()[0]
            require(through['sequence']<=highest,'CONFLICT')
            rows=db.execute('SELECT sequence,value FROM feed_atoms WHERE scope=? AND sequence>? AND sequence<=? ORDER BY sequence LIMIT ?',(scope,after,through['sequence'],limit)).fetchall()
        records=[]
        for seq,encoded in rows:
            value=json.loads(encoded);records.append({'sequence':seq,'ref':value['write']['ref'],'content_type':value['content_type'],'size':value['size']})
        self.access.authorize(scope,'readCommits')
        return c.commits(dict(through=through,after=after,records=records,next_after=after+len(records),complete=after+len(records)==through['sequence']),scope,after,through,limit)
