"""Fresh S05 synthetic data; actual pinned unprefixed E5 vectors, no user stores."""
import json
from pathlib import Path
import uuid
from fusion.contracts import canonical
from .memory_embedding import load
from .memory_composition import ROOT,MODEL
from .append_oracle import QUERY,TEXT,CREATED


def generate():
    model=json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())
    encode=load(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py',MODEL,model['files'])
    texts=['Synthetic violet beacon stores '+str(i)+' paper moons in a notebook.' for i in range(8)]
    texts+=['Generated yellow triangle sings about imaginary weather.','Generated copper kettle boils water for imaginary tea.',
            'Generated astronomer stores a blue notebook of cardboard stars.','Synthetic privacy canary S05_LOCAL_PRIORITY: the glacier has twelve wool socks.']
    records=[dict(uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,'s05-new-synthetic/'+str(i))),time='2031-05-01 00:00:%02d'%i,
        content=text,vector=encode(text),links=['2031-05-01 00:00:%02d'%i],stv=[.6+i*.02,.5],promotion=0.) for i,text in enumerate(texts)]
    return dict(corpus_id='synthetic-s05-promotion-2031',records=records,queries={QUERY:encode(QUERY)},clock=2000000000.,
        embedding_boundary='real-native-e5',approved_append_inputs=[TEXT],creation_clock_fixture=CREATED)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_bytes(canonical(generate()))
