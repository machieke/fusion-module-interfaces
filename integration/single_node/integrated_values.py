"""Explicit fresh-state integrated native selection over the retained chart."""
import argparse,json
from pathlib import Path
from fusion.contracts import require
from fusion.resident_workers import LIMITS
from .sustained_values import generate as sustained

def generate(images,scope,*,mode='combined',native_mode='prepared',transport='pooled',history='original',chain=False,archive=False,registry=False,envelopes=False,nal_envelopes=False,search_repair=False,chain_continuation=False):
    require(native_mode in ('cold','resident','prepared'),'UNSUPPORTED_PROFILE')
    require(transport in ('original','pooled'),'UNSUPPORTED_PROFILE')
    require(history in ('original','compact'),'UNSUPPORTED_PROFILE')
    values=sustained(images,scope,mode=mode,chain=chain)
    if chain_continuation:
        from fusion.chain_continuation import PROFILE
        require(chain and envelopes and mode=='combined','UNSUPPORTED_PROFILE')
        values['preview']['chain']['continuation']=PROFILE
    if search_repair:
        from fusion.search_repair import PROFILE
        require(mode in ('memory','combined'),'UNSUPPORTED_PROFILE')
        values['preview']['memory']['maintenance_profile']=PROFILE
    if envelopes:
        from fusion.execution_envelope import PROFILE
        require(mode=='combined','UNSUPPORTED_PROFILE')
        values['preview']['inspection']['envelopes']=PROFILE
    if nal_envelopes:
        from fusion.nal_envelope import PROFILE
        require(mode=='combined','UNSUPPORTED_PROFILE')
        values['preview']['inspection']['nal_envelopes']=PROFILE
    if native_mode!='cold':values['preview']['sustained']['resident_worker']=dict(LIMITS)
    if native_mode=='prepared':values['preview']['sustained']['native_preparation']='verified-native-preparation/1'
    if transport=='pooled':
        from fusion.https_pool import LIMITS as transport_limits
        values['preview']['sustained'].update(transport_pool=dict(transport_limits),history_hydration='bounded-history-hydration/1')
    if history=='compact':values['preview']['sustained']['history_representation']='immutable-administrative-captures/1'
    require(type(archive) is bool,'INVALID_ARGUMENT')
    if archive:
        from fusion.archive_contracts import DEFAULT
        values['preview']['sustained']['storage_archive']=dict(DEFAULT)
    require(type(registry) is bool)
    if registry:
        from .integrated_registry import ROLES,PROFILE
        pins={}
        for role in set(ROLES.values()):
            image=values['components'].get(role,{}).get('image',values['image'])
            pins[role]=dict(image=image['digest'].removeprefix('sha256:'),source=images['source_manifest_sha256'])
        values['preview']['sustained']['provider_registry']=dict(profile=PROFILE,pins=pins,readiness_ms=300000)
    return values

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--images',required=True);p.add_argument('--scope',required=True);p.add_argument('--output',required=True)
    p.add_argument('--mode',choices=['minimal','memory','combined'],default='combined');p.add_argument('--native-mode',choices=['cold','resident','prepared'],default='prepared');p.add_argument('--transport',choices=['original','pooled'],default='pooled');p.add_argument('--history',choices=['original','compact'],default='original');p.add_argument('--chain',action='store_true');p.add_argument('--archive',action='store_true');p.add_argument('--registry',action='store_true');p.add_argument('--envelopes',action='store_true');p.add_argument('--nal-envelopes',action='store_true');p.add_argument('--search-repair',action='store_true');p.add_argument('--chain-continuation',action='store_true');a=p.parse_args()
    import yaml
    path=Path(a.output);require(not path.exists(),'CONFLICT')
    value=generate(json.loads(Path(a.images).read_bytes()),a.scope,mode=a.mode,native_mode=a.native_mode,transport=a.transport,history=a.history,chain=a.chain,archive=a.archive,registry=a.registry,envelopes=a.envelopes,nal_envelopes=a.nal_envelopes,search_repair=a.search_repair,chain_continuation=a.chain_continuation)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(yaml.safe_dump(value,sort_keys=False))

if __name__=='__main__':main()
