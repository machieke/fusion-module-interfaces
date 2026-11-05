"""Two explicit compositions for the extracted Go provider onboarding recipe.

Initial composition keeps historical inspection selected. Replacement changes
only trusted future-session selection; captured application/provider state is
never moved. Independent Go source identity stays separate from Python images.
"""
import argparse,copy,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.registry import descriptor_wire,selection_token
from fusion.reference_inspect_contracts import descriptor
from fusion import cognitive_services
from .pilot_values import generate as pilot
from .pilot_provider_image import verify


def initial(images,artifact,scope,namespace):
    checked=verify(artifact);require(checked['contract']==selection_token(descriptor()),'UNSUPPORTED_PROFILE');value=pilot(images,scope,namespace)
    # The reference Go owner supports its own single-writer flock, not the
    # separately named writer-handover protocol. Do not falsely advertise it.
    value['preview']['pilot'].pop('writer_fence')
    for component in value['components'].values():component.pop('writerAuthoritySecret',None)
    value['components']['fusion-inspect-go']=dict(enabled=True,existingSecret='fusion-inspect-go-tls-auth',
        image=dict(repository=checked['repository'],tag='pilot-reference',digest=checked['manifest'],pullPolicy='Never'),
        persistence=dict(storageClass='local-path',size='256Mi'),
        resources=dict(requests=dict(cpu='25m',memory='32Mi'),limits=dict(cpu='500m',memory='128Mi')),
        config=dict(revision='initial',capacity=4,nativeEnabled=False,workerEnabled=False,test={}))
    p=value['preview']
    from fusion.lookup_contracts import FEED,SUSTAINED_FEED
    feed=SUSTAINED_FEED if p['sustained'].get('feed_capacity') else FEED
    p['inspection']['reference_storage_descriptor']=descriptor_wire(cognitive_services.descriptors(feed_profile=feed)[0])
    p['sustained']['provider_registry']['pins']['fusion-inspect-go']=dict(image=checked['manifest'].removeprefix('sha256:'),source=checked['source_manifest_sha256'])
    combined=copy.deepcopy(images);combined['images'].append(dict(kind='inspect-go',repository=checked['repository'],
        local_tag=checked['repository']+':pilot-reference',manifest_digest=checked['manifest'],configuration_digest=checked['configuration'],
        source_manifest_sha256=checked['source_manifest_sha256'],source_kind='independent-go',
        source_package=checked['source_package'],reference_artifact_sha256=checked['manifest_sha256']))
    return value,combined


def replace(initial_values):
    value=copy.deepcopy(initial_values);p=value['preview'];require('writer_fence' not in p['pilot'],'UNSUPPORTED_PROFILE')
    from .pilot_inspection_template import PROFILE
    require('execution_descriptor' not in p['inspection'],'CONFLICT')
    p['inspection']['additional_template']=dict(profile=PROFILE,name='go-shared',service='fusion-inspect-go',descriptor=descriptor_wire(descriptor()))
    return value


def main():
    import yaml
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['initial','replace'])
    for name in ('images','artifact','scope','namespace','initial-values','directory'):p.add_argument('--'+name)
    a=p.parse_args();root=Path(a.directory);root.mkdir(parents=True,exist_ok=False)
    if a.action=='initial':
        value,images=initial(json.loads(Path(a.images).read_bytes()),a.artifact,a.scope,a.namespace)
        (root/'images.json').write_bytes(canonical(images))
    else:value=replace(yaml.safe_load(Path(a.initial_values).read_text()))
    (root/'values.yaml').write_text(yaml.safe_dump(value,sort_keys=False))
    (root/'preparation.json').write_bytes(canonical(dict(profile='go-reference-onboarding-preparation/1',stage=a.action,
        values_sha256=digest(canonical(value)),additional_live_generations=0,cluster_writes=0,
        provider_state_transfer=False,writer_handover_profile='UNSUPPORTED_NOT_ADVERTISED')))

if __name__=='__main__':main()
