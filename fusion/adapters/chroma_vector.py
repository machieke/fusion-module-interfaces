"""Real Chroma projection; unpublished generations rebuilt after uncertain writes.

Only declared AtomCommitSource/AtomStorage are read. No caller metadata or SQL.
"""
from dataclasses import asdict
import fcntl
import json
import os
from pathlib import Path
import time
import uuid
from fusion import vector_contracts as c, lookup_contracts as a
from fusion.contracts import canonical,digest,require,ContractError
from fusion.responses import envelope
from fusion.vector_enrollment import validate_inputs


def publish(path,value):
    path=Path(path);tmp=path.with_suffix('.pending')
    with tmp.open('wb') as stream:
        stream.write(canonical(value));stream.flush();os.fsync(stream.fileno())
    tmp.replace(path)
    fd=os.open(path.parent,os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)


class ChromaVector:
    def __init__(self,root,atoms,source,access,scope,corpus,embedding,hook=lambda _:None):
        import chromadb
        require(chromadb.__version__=='1.5.5','UNSUPPORTED_PROFILE')
        self.sdk=chromadb;self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        self.atoms,self.source,self.access=atoms,source,access
        self.scope,self.corpus,self.embedding,self.hook=scope,corpus,c.model(embedding),hook

    def build(self,scope,through):
        require(scope==self.scope,'UNAUTHORIZED');self.access.authorize(scope,'build')
        through=a.head(through,scope);head=a.head(self.source.head(scope),scope)
        require(head['source']==through['source'] and head['sequence']>=through['sequence'],'CONFLICT')
        with (self.root/'maintenance.lock').open('a') as lock:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ContractError('OVERLOADED') from None
            generation=str(uuid.uuid4());directory=self.root/generation;directory.mkdir()
            client=self.sdk.PersistentClient(path=str(directory/'index'))
            collection=client.create_collection('memories',embedding_function=None)
            records=[];seen=set();after=0
            while after<through['sequence']:
                page=a.commits(self.source.readCommits(scope,after,through,8),scope,after,through,8)
                for entry in page['records']:
                    item=self.atoms.get(entry['ref']);envelope(item,entry['ref'])
                    require(item.content_type==entry['content_type'] and len(item.bytes)==entry['size'],'NOT_AVAILABLE')
                    if item.content_type!=c.ENROLLMENT:continue
                    enrolled=json.loads(item.bytes)
                    # Corpus is a scope-local operator selection; other corpus records do not enter this index.
                    require(enrolled.get('scope')==scope,'UNAUTHORIZED')
                    if enrolled.get('corpus')!=self.corpus:continue
                    enrolled=c.enrollment(enrolled,scope,self.corpus,self.embedding)
                    require(canonical(enrolled)==item.bytes,'NOT_AVAILABLE')
                    require(enrolled['uuid'] not in seen,'CONFLICT');seen.add(enrolled['uuid'])
                    require(len(records)<c.MAX_RECORDS,'OVERLOADED')
                    _,vector=validate_inputs(self.atoms,enrolled)
                    collection.add(ids=[enrolled['uuid']],embeddings=[vector],metadatas=[{'ref':canonical(enrolled['payload']).decode()}])
                    records.append({'uuid':enrolled['uuid'],'ref':enrolled['payload'],'vector_digest':enrolled['vector']['digest']})
                    self.hook('after_index_write')
                after=page['next_after']
            # Verify full reconstructible collection contents before publishing any source claim.
            got=collection.get(include=['embeddings','metadatas'])
            actual={u:(m['ref'],digest(c.vector_bytes([float(x) for x in v]))) for u,m,v in zip(got['ids'],got['metadatas'],got['embeddings'])}
            require(actual=={x['uuid']:(canonical(x['ref']).decode(),x['vector_digest']) for x in records},'NOT_AVAILABLE')
            snap=dict(generation=generation,head=through,corpus=self.corpus,embedding=self.embedding,index=c.INDEX,profile=c.PROFILE)
            snap['logical']=digest(canonical({k:v for k,v in snap.items() if k!='generation'}))
            manifest=dict(snapshot=c.snapshot(snap,scope),records=records,configuration=collection.configuration)
            self.hook('before_checkpoint')
            publish(directory/'manifest.json',manifest);self.hook('after_checkpoint')
            self.access.authorize(scope,'build')
            try: published=json.loads((self.root/'published.json').read_text())
            except FileNotFoundError: published={'current':None,'generations':{}}
            require(len(published['generations'])<32,'OVERLOADED')
            published['current']=snap;published['generations'][generation]=snap
            publish(self.root/'published.json',published)
            self.hook('after_publication');return snap

    def current(self):
        self.access.authorize(self.scope,'query')
        try:return c.snapshot(json.loads((self.root/'published.json').read_text())['current'],self.scope)
        except FileNotFoundError:raise ContractError('NOT_AVAILABLE') from None

    def query(self,request):
        request=c.query(asdict(request) if isinstance(request,c.VectorQuery) else request)
        require(request['scope']==self.scope,'UNAUTHORIZED');self.access.authorize(self.scope,'query')
        snap=request['snapshot'];require(snap['corpus']==self.corpus and snap['embedding']==self.embedding,'UNSUPPORTED_PROFILE')
        require(time.time_ns()//1_000_000<=request['deadline_ms'],'DEADLINE_EXCEEDED')
        try:published=json.loads((self.root/'published.json').read_text())
        except (FileNotFoundError,ValueError):raise ContractError('NOT_AVAILABLE') from None
        require(published['generations'].get(snap['generation'])==snap,'NOT_AVAILABLE')
        directory=self.root/snap['generation']
        try:manifest=json.loads((directory/'manifest.json').read_text())
        except (FileNotFoundError,ValueError):raise ContractError('NOT_AVAILABLE') from None
        require(manifest['snapshot']==snap,'NOT_AVAILABLE')
        require((directory/'index/chroma.sqlite3').is_file(),'NOT_AVAILABLE')
        try:
            client=self.sdk.PersistentClient(path=str(directory/'index'))
            collection=client.get_collection('memories',embedding_function=None)
            # Never turn a disappeared/partial generation into a successful empty result.
            require(collection.count()==len(manifest['records']),'NOT_AVAILABLE')
            hits=[]
            if manifest['records']:
                value=collection.query(query_embeddings=[request['vector']],n_results=request['k'],include=['metadatas','distances'])
                allowed={r['uuid']:r['ref'] for r in manifest['records']}
                for u,m,d in zip(value['ids'][0],value['metadatas'][0],value['distances'][0]):
                    ref=json.loads(m['ref']);require(allowed.get(u)==ref,'NOT_AVAILABLE')
                    hits.append(dict(uuid=u,ref=ref,distance=float(d)))
        except ContractError:raise
        except Exception:raise ContractError('NOT_AVAILABLE') from None
        self.access.authorize(self.scope,'query')
        require(time.time_ns()//1_000_000<=request['deadline_ms'],'DEADLINE_EXCEEDED')
        return c.result(dict(request_id=request['request_id'],request_digest=digest(canonical(request)),snapshot=snap,hits=hits,top_k=request['k'],exhaustive=False),request)
