"""One fresh opt-in operator-pilot selection over the existing chart."""
import argparse,json,uuid
from pathlib import Path
from fusion.contracts import require
from fusion.provider_retention import PROFILE as REGISTRY,LIMITS as RETENTION
from fusion.service_lanes import PROFILE as LANES,LIMITS as LANE_LIMITS
from .integrated_values import generate as integrated


def generate(images,scope,namespace,*,chain=False):
    require(namespace.startswith('omega-ref-pilot-') and len(namespace)<=63,'UNAUTHORIZED')
    value=integrated(images,scope,history='compact',chain=chain,archive=True,registry=True,
                     envelopes=True,nal_envelopes=True,search_repair=True,chain_continuation=chain)
    p=value['preview'];p['sustained']['allocation']['retained']=16
    p['sustained']['provider_registry'].update(profile=REGISTRY,limits=dict(RETENTION))
    p['pilot']=dict(profile='omega-operator-pilot/1',capacity=True,subscriptions=True,workflows=True,derived_cleanup=True,
        owner_clock=dict(profile='recorded-model-owner-time/1'),
        request_lanes=dict(profile=LANES,limits=dict(LANE_LIMITS)),
        writer_fence=dict(profile='planned-synthetic-writer-handover/1',authority_file='/writer-authority/current.json',
                          deployment=namespace,incarnation='initial-'+str(uuid.uuid4()),generation=1),
        browser=dict(profile='synthetic-browser-sessions/1',users={
            'alice':dict(role='developer',scopes=[p['agents']['omega-agent']['private_scope']],credential_key='browser-alice-token'),
            'bob':dict(role='developer',scopes=[p['agents']['omega-agent-b']['private_scope']],credential_key='browser-bob-token'),
            'shared':dict(role='developer',scopes=[scope],credential_key='browser-shared-token'),
            'operator':dict(role='operator',scopes=[scope],credential_key='browser-operator-token')}))
    for role in ('omega-agent','fusion-execution','fusion-storage','fusion-messaging',*value['components']):
        value['components'].setdefault(role,{})['writerAuthoritySecret']='pilot-current-writer'
    return value


def main():
    import yaml
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--images',required=True);p.add_argument('--scope',required=True)
    p.add_argument('--namespace',required=True);p.add_argument('--output',required=True);p.add_argument('--chain',action='store_true');a=p.parse_args()
    out=Path(a.output);require(not out.exists(),'CONFLICT')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(yaml.safe_dump(generate(json.loads(Path(a.images).read_bytes()),a.scope,a.namespace,chain=a.chain),sort_keys=False))


if __name__=='__main__':main()
