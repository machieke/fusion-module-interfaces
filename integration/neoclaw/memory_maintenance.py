"""Bounded operator maintenance entrypoint; no maintenance operation on HTTPS."""
import argparse,json
from pathlib import Path
from fusion.vector_composition import ReadService
from .host import failpoint


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('config');p.add_argument('--pause-at');p.add_argument('--through');a=p.parse_args()
    cfg=json.loads(Path(a.config).read_text())
    if a.pause_at:cfg['pause_at']=a.pause_at
    service=ReadService(a.config,cfg['principals']['worker']['credential'],lambda stage:failpoint(cfg,stage))
    scope=cfg['memory_read']['scope'];head=json.loads(a.through) if a.through else service.atoms.head(scope)
    print(json.dumps(service.search().build(scope,head)))
if __name__=='__main__':main()
