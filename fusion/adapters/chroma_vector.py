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

    @staticmethod
    def _deadline(deadline):
        if deadline is not None:require(time.time_ns()//1_000_000<=deadline,'DEADLINE_EXCEEDED')

    def _head(self,scope,through):
        require(scope==self.scope,'UNAUTHORIZED')
        through=a.head(through,scope);head=a.head(self.source.head(scope),scope)
        require(head['source']==through['source'] and head['sequence']>=through['sequence'],'CONFLICT')
        return through

    def _lock(self):
        lock=(self.root/'maintenance.lock').open('a')
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            lock.close();raise ContractError('OVERLOADED') from None
        return lock

    def build(self,scope,through):
        require(scope==self.scope,'UNAUTHORIZED');self.access.authorize(scope,'build')
        through=self._head(scope,through)
        with self._lock():return self._project(scope,through,str(uuid.uuid4()))

    def _project(self,scope,through,generation,deadline=None,rebuild=False):
        self._deadline(deadline)
        directory=self.root/generation;directory.mkdir(exist_ok=rebuild)
        client=self.sdk.PersistentClient(path=str(directory/'index'))
        if rebuild and 'memories' in {x.name for x in client.list_collections()}:
            client.delete_collection('memories')
        collection=client.create_collection('memories',embedding_function=None)
        records=[];seen=set();after=0
        while after<through['sequence']:
            self._deadline(deadline)
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
                self._deadline(deadline)
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
        self._deadline(deadline);self.hook('before_checkpoint')
        publish(directory/'manifest.json',manifest);self.hook('after_checkpoint')
        return self._publish(scope,manifest,deadline)

    def _publish(self,scope,manifest,deadline):
        self.access.authorize(scope,'build');self._deadline(deadline)
        snap=manifest['snapshot'];generation=snap['generation']
        try:published=json.loads((self.root/'published.json').read_text())
        except FileNotFoundError:published={'current':None,'generations':{}}
        require(generation in published['generations'] or len(published['generations'])<32,'OVERLOADED')
        published['current']=snap;published['generations'][generation]=snap
        publish(self.root/'published.json',published)
        self.hook('after_publication');return snap

    def _named(self,scope,through,key,principal):
        from fusion.contracts import label
        require(label(key));a.head(through,scope)
        generation=str(uuid.uuid5(uuid.UUID(through['source']),canonical([principal,scope,key]).decode()))
        expected=dict(principal=principal,scope=scope,key=key,through=through,corpus=self.corpus,
                      embedding=self.embedding,index=c.INDEX,profile=c.PROFILE)
        return generation,expected

    def _verified(self,generation,through):
        directory=self.root/generation
        try:manifest=json.loads((directory/'manifest.json').read_text())
        except (OSError,ValueError):raise ContractError('NOT_AVAILABLE') from None
        snap=c.snapshot(manifest['snapshot'],self.scope)
        require(snap['generation']==generation and snap['head']==through and snap['corpus']==self.corpus and
                snap['embedding']==self.embedding,'CONFLICT')
        require((directory/'index/chroma.sqlite3').is_file(),'NOT_AVAILABLE')
        try:
            collection=self.sdk.PersistentClient(path=str(directory/'index')).get_collection('memories',embedding_function=None)
            got=collection.get(include=['embeddings','metadatas'])
            actual={u:(m['ref'],digest(c.vector_bytes([float(x) for x in v]))) for u,m,v in zip(got['ids'],got['metadatas'],got['embeddings'])}
            require(actual=={x['uuid']:(canonical(x['ref']).decode(),x['vector_digest']) for x in manifest['records']},'NOT_AVAILABLE')
        except ContractError:raise
        except Exception:raise ContractError('NOT_AVAILABLE') from None
        return manifest

    def published(self,scope,through,key):
        require(scope==self.scope,'UNAUTHORIZED');principal=self.access.authorize(scope,'published')
        generation,expected=self._named(scope,through,key,principal);directory=self.root/generation
        if not directory.exists():return None
        if not (directory/'maintenance.json').exists():
            # An interrupted first journal publication precedes every index effect.
            require({p.name for p in directory.iterdir()}<={'maintenance.pending'},'NOT_AVAILABLE')
            return None
        try:record=json.loads((directory/'maintenance.json').read_text())
        except (OSError,ValueError):raise ContractError('NOT_AVAILABLE') from None
        require(all(record['intent'].get(k)==v for k,v in expected.items()),'CONFLICT')
        try:published=json.loads((self.root/'published.json').read_text())['generations']
        except FileNotFoundError:published={}
        if generation not in published:return None
        manifest=self._verified(generation,through)
        require(manifest['snapshot']==published[generation],'NOT_AVAILABLE')
        self.access.authorize(scope,'published');return manifest['snapshot']

    def build_named(self,scope,through,key,deadline_ms):
        require(scope==self.scope,'UNAUTHORIZED');principal=self.access.authorize(scope,'build')
        through=self._head(scope,through);a.integer(deadline_ms,1,2**63-1)
        generation,expected=self._named(scope,through,key,principal);expected['deadline_ms']=deadline_ms
        directory=self.root/generation;journal=directory/'maintenance.json'
        with self._lock():
            done=self.published(scope,through,key)
            if journal.exists():
                record=json.loads(journal.read_text());require(record['intent']==expected,'CONFLICT')
            else:
                self._deadline(deadline_ms)
                require(sum(p.is_dir() for p in self.root.iterdir())-int(directory.exists())<32,'OVERLOADED')
                directory.mkdir(exist_ok=True);record=dict(intent=expected,attempts=0);publish(journal,record)
            if done is not None:return done
            self._deadline(deadline_ms)
            if (directory/'manifest.json').is_file():
                return self._publish(scope,self._verified(generation,through),deadline_ms)
            require(record['attempts']<3,'OVERLOADED');record['attempts']+=1;publish(journal,record)
            self.hook('after_named_build_reservation')
            return self._project(scope,through,generation,deadline_ms,rebuild=True)

    def current(self):
        self.access.authorize(self.scope,'query')
        try:return c.snapshot(json.loads((self.root/'published.json').read_text())['current'],self.scope)
        except FileNotFoundError:raise ContractError('NOT_AVAILABLE') from None

    def ready(self,scope,snapshot):
        """Observe a retained generation without querying or starting maintenance."""
        require(scope==self.scope,'UNAUTHORIZED');self.access.authorize(scope,'ready')
        snapshot=c.snapshot(snapshot,scope)
        try:published=json.loads((self.root/'published.json').read_text())['generations']
        except (OSError,ValueError):raise ContractError('NOT_AVAILABLE') from None
        require(published.get(snapshot['generation'])==snapshot,'NOT_AVAILABLE')
        require(self._verified(snapshot['generation'],snapshot['head'])['snapshot']==snapshot,'NOT_AVAILABLE')
        self.access.authorize(scope,'ready');return {'ready':True}

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
