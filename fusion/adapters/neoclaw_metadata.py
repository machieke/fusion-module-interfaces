"""Application-owned immutable compatibility views; metadata only, no retrieval."""
import json
from pathlib import Path
import time
from ..contracts import canonical,digest,require,ContractError
from .chroma_vector import publish


def expected(manifest):
    return {r['uuid']:dict(linkedEpisodes=r['links'],strength=r['stv'][0],confidence=r['stv'][1])
            for r in manifest['records']}


class MetadataOnly:
    def __init__(self,collection,manifest):self.collection,self.expected=collection,expected(manifest)
    def get(self,*,ids,include):
        require(include==['metadatas'],'UNAUTHORIZED')
        require(all(i in self.expected for i in ids),'NOT_AVAILABLE')
        value=self.collection.get(ids=ids,include=include)
        require(dict(zip(value['ids'],value['metadatas']))=={i:self.expected[i] for i in ids},'CONFLICT')
        return value
    def __getattr__(self,name):raise RuntimeError('LEGACY_CANDIDATE_OR_PAYLOAD_ACCESS_FORBIDDEN')


def collection(root,manifest,*,prepare=False,deadline=None):
    import chromadb
    require(chromadb.__version__=='1.5.5','UNSUPPORTED_PROFILE')
    seal=digest(canonical(manifest));directory=Path(root)/seal;checkpoint=directory/'manifest.json'
    if not checkpoint.is_file():
        require(prepare,'NOT_AVAILABLE')
        require(deadline is not None and time.time_ns()//1_000_000<=deadline,'DEADLINE_EXCEEDED')
        directory.mkdir(parents=True,exist_ok=True)
    else:require(checkpoint.read_bytes()==canonical(manifest),'CONFLICT')
    require(prepare or (directory/'index/chroma.sqlite3').is_file(),'NOT_AVAILABLE')
    client=chromadb.PersistentClient(path=str(directory/'index'))
    if checkpoint.is_file():value=client.get_collection('metadata',embedding_function=None)
    else:
        value=client.get_or_create_collection('metadata',embedding_function=None)
        got=set(value.get(include=[])['ids']);desired=expected(manifest)
        require(got<=set(desired),'CONFLICT')
        for key,metadata in desired.items():
            if key not in got:
                require(time.time_ns()//1_000_000<=deadline,'DEADLINE_EXCEEDED')
                value.add(ids=[key],embeddings=[[0.]],metadatas=[metadata])
    got=value.get(include=['metadatas','documents','embeddings'])
    require(dict(zip(got['ids'],got['metadatas']))==expected(manifest) and
            all(x is None for x in got['documents']) and all(list(x)==[0.] for x in got['embeddings']),'CONFLICT')
    if not checkpoint.is_file():
        require(time.time_ns()//1_000_000<=deadline,'DEADLINE_EXCEEDED')
        publish(checkpoint,manifest)
    return MetadataOnly(value,manifest)


def ready(root,manifest):
    path=Path(root)/digest(canonical(manifest))/'manifest.json'
    if not path.is_file():return False
    collection(root,manifest);return True
