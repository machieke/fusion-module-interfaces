"""Fresh restricted handover selection over the existing pilot chart factory."""
import argparse,json
from pathlib import Path
from fusion.contracts import require
from integration.single_node.pilot_values import generate as pilot
from .pilot_handover import ALLOWED


def generate(images,scope,namespace):
    value=pilot(images,scope,namespace,chain=False);p=value['preview']
    registry=p['sustained']['provider_registry'];registry['profile']='trusted-provider-lifecycle/1';registry.pop('limits',None)
    p['tasks']['enabled']=False;p['inspection']['enabled']=False
    if 'chain' in p:p['chain']['enabled']=False
    p['pilot']['workflows']=False;p['pilot'].pop('browser',None)
    for agent in p['agents'].values():agent['tools']=[x for x in agent['tools'] if x in ALLOWED]
    for role in ('fusion-inspect-go','f1r3node','fusion-commitment','fusion-channel-bridge','irc-server','irc-peer'):
        if role in value['components']:value['components'][role]['enabled']=False
    value.setdefault('workflow',{})['enabled']=False;value['testFaultsEnabled']=True
    p['sustained']['allocation'].update(active=2,retained=6,pending=8,bytes=8388608)
    return value


def main():
    import yaml
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('images','scope','namespace','output'):p.add_argument('--'+name,required=True)
    a=p.parse_args();path=Path(a.output);require(not path.exists(),'CONFLICT')
    value=generate(json.loads(Path(a.images).read_bytes()),a.scope,a.namespace)
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);path.write_text(yaml.safe_dump(value,sort_keys=False));path.chmod(0o600)


if __name__=='__main__':main()
