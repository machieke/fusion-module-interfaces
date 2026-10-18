"""Pinned original native query oracle; generated corpus only, no adoption adapter.

The selected unused history/global-promoted-context boundaries are fixtures.
The query, promotion arithmetic, linked-label/STV reads and parser are upstream.
"""
import json
import os
from pathlib import Path
import subprocess
from fusion.contracts import canonical, digest, require
from fusion import neoclaw_contracts as c
from .native_loop import prepare

ROOT = Path(__file__).resolve().parents[2]
HELPER = Path(os.environ.get('S03_HELPER', ROOT/'artifacts/omega-mapping-source/petta_lib_chromadb/lib_chromadb.py'))
HELPER_HASH = '461b78f92234b58e1090e66c332d627a063e201751d8247459d82a18e7afd36d'


def query_source(omega):
    text = (omega/'src/memory.metta').read_text()
    require(digest(text.encode()) == c.PINS['sources']['mettaclaw']['files']['src/memory.metta'], 'UNSUPPORTED_PROFILE')
    # Exact bounded functions, preserving their bodies including native uniqueness.
    names = ('embed', 'getSTV', 'get-promotion', 'query')
    return '\n'.join(text[text.index('(= ('+name+' '):text.index('\n(= (', text.index('(= ('+name+' ')+1)] for name in names)


def creation_source(omega):
    query_source(omega)  # Whole-file pin before selecting exact native bodies.
    text=(omega/'src/memory.metta').read_text()
    return '\n'.join(text[text.index('(= ('+name+' '):text.index('\n(= (',text.index('(= ('+name+' ')+1)]
                     for name in ('createMemory','remember'))


def prepare_original(app_path, corpus, site, *, vector_fixture=True, model=None):
    app_path = Path(app_path)
    args, env, work = prepare(app_path)
    app = json.loads(app_path.read_text())
    runtime = json.loads(Path(app['runtime']).read_text()); omega = Path(runtime['mettaclaw'])
    require(digest(HELPER.read_bytes()) == HELPER_HASH, 'UNSUPPORTED_PROFILE')
    bootstrap = work/'memory_bootstrap.py'
    bootstrap.write_text('''import sys, json, os, importlib.util
from pathlib import Path
sys.path.insert(0, SITE)
sys.path.insert(0, HELPER_DIR)
import lib_chromadb, helper, lib_llm_ext
corpus=json.loads(Path(CORPUS).read_text())
for row in corpus['records']:
 lib_chromadb.COLLECTION.add(ids=[row['uuid']],embeddings=[row['vector']],documents=[row['content']],metadatas=[dict(time=row['time'],linkedEpisodes=row['links'],strength=row['stv'][0],confidence=row['stv'][1])])
helper.promotion_open_map()
for row in corpus['records']:
 helper.promotion_set_value(row['uuid'], row['promotion']); helper.promotion_set_lasttime(row['uuid'], corpus['clock']-86400)
helper.promotion_commit()
lib_llm_ext.useLocalEmbedding=lambda text: corpus['queries'][text]
def clock(): return corpus['clock']
'''.replace('SITE', repr(str(site))).replace('HELPER_DIR', repr(str(HELPER.parent))).replace('CORPUS', repr(str(corpus))))
    if not vector_fixture:
        require(model is not None, 'UNSUPPORTED_PROFILE')
        bootstrap.write_text(bootstrap.read_text()+
            '\nfrom integration.neoclaw.memory_embedding import load\nlib_llm_ext.useLocalEmbedding=load('+repr(str(omega/'lib_llm_ext.py'))+','+repr(str(model))+','+repr(json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())['files'])+')\n')
        env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TOKENIZERS_PARALLELISM='false')
    # Instrument the original function without changing its inputs or output.
    bootstrap.write_text(bootstrap.read_text()+'''
_original_query=lib_chromadb.query_with_ids_and_dists
def traced_query(vector,k):
 value=_original_query(vector,k)
 Path('original-candidates.json').write_text(json.dumps(value))
 return value
lib_chromadb.query_with_ids_and_dists=traced_query
''')
    memory = work/'memory.metta'
    source = query_source(omega).replace('($current_time (get_time))', '($current_time (py-call (memory_bootstrap.clock)))')
    memory.write_text('''(= (maxFeedback) 50000)
(= (maxRecallItems) 2)
(= (maxSimilarityRecall) 4)
(= (promotionInflationFactor) 4)
(= (embeddingprovider) Local)
(= (initMemory) True)
(= (getPrompt) "Generated S03 memory read oracle")
(= (getHistory) "")
(= (best-promoted-memories) "")
(= (addToHistory $a $b $c $d) True)
'''+source)
    entry = work/'start.metta'
    text = ('!(import! &self (library lib_combinatorics))\n!(import! &self (library lib_vector))\n'+entry.read_text()).replace(str(ROOT/'integration/neoclaw/controlled/memory.metta'), str(memory))
    text = text.replace('!(import! &self '+json.dumps(str(memory))+')',
        '!(import! &self '+json.dumps(str(bootstrap))+')\n!(import! &self '+json.dumps(str(memory))+')')
    entry.write_text(text)
    return args, env, work
