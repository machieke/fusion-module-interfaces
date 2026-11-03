"""Fresh bounded Phase 3 values. Seed UUIDs instantiate templates, not sessions."""
import argparse,json
from pathlib import Path
from fusion.contracts import require
from .preview_values import generate as preview_values
from fusion.preview_deployment_contracts import SUSTAINED_COMPOSITION as COMPOSITION


def generate(manifest,scope,*,mode='combined',expires_ms=None,chain=False):
    values=preview_values(manifest,scope,mode=mode,inputs=24,sessions=1,expires_ms=expires_ms,chain=chain)
    p=values['preview'];p['profile']=COMPOSITION
    p['sustained']=dict(allocation=dict(active=2,retained=8,pending=8,bytes=8388608,lifetime_ms=86400000),
        feed_capacity=dict(profile='bounded-feed-capacity/1',records=2048,bytes=33554432))
    if mode=='combined':p['sustained']['private_scopes']=True
    return values


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--images',required=True);p.add_argument('--scope',required=True);p.add_argument('--output',required=True)
    p.add_argument('--mode',choices=['minimal','memory','combined'],default='combined');p.add_argument('--chain',action='store_true');a=p.parse_args()
    import yaml
    path=Path(a.output);require(not path.exists(),'CONFLICT')
    value=generate(json.loads(Path(a.images).read_bytes()),a.scope,mode=a.mode,chain=a.chain)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(yaml.safe_dump(value,sort_keys=False))
if __name__=='__main__':main()
