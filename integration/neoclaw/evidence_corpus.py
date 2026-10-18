"""Generate a fresh public synthetic S04 corpus with the existing pinned E5 recipe."""
import argparse
from pathlib import Path
import uuid
from fusion.contracts import canonical
from .append_oracle import generated


def generate():
    corpus=generated();corpus['corpus_id']='synthetic-s04-local-evidence-2031'
    for i,record in enumerate(corpus['records']):
        record['uuid']=str(uuid.uuid5(uuid.NAMESPACE_URL,'s04-new-generated-distractor/'+str(i)))
    return corpus


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
    Path(a.out).write_bytes(canonical(generate()))
