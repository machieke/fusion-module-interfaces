"""New approved synthetic S07 corpus, real pinned E5; no historical private data."""
import json
from pathlib import Path
import uuid
from fusion.contracts import canonical
from .memory_embedding import load
from .memory_composition import ROOT,MODEL

TEXT='Synthetic S07 paper observatory stores a blue cardboard moon.'


def generate():
    model=json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())
    encode=load(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py',MODEL,model['files'])
    vector=encode(TEXT)
    return dict(corpus_id='synthetic-s07-new-2032',records=[dict(uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,'s07-new-synthetic-2032')),
        time='2032-07-01 00:00:00',content=TEXT,vector=vector,links=['2032-07-01 00:00:00'],stv=[.6,.5],promotion=0.)],
        queries={TEXT:vector},clock=2000000000.,embedding_boundary='real-native-e5',
        approved_append_inputs=[TEXT],creation_clock_fixture='2032-07-01 00:01:00')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_bytes(canonical(generate()))
