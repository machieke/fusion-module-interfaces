"""Operator registration and service identity; never a model-facing grant."""
import json
from fusion import cognitive_services as cs
from fusion.contracts import require
from fusion.registry import descriptor_wire
from fusion.preview_inspect import PROFILE as INSPECTION
from .configure import write


def provider(settings,cfg,state,run,token,ep):
    p=settings['preview'];chain=p['chain'];role=settings['role'];scope=p['scope']
    require(p.get('inspection',{}).get('enabled') and chain['enabled'] is True,'UNSUPPORTED_PROFILE')
    if role=='fusion-storage':
        path=run/'cognitive-owner.json';v=json.loads(path.read_text());v['actors']['commit-observer']='commit-observer'
        v['principals']['commit-observer']=dict(credential=token('commit-storage-token'),scopes={scope:['atom.storage.get']});write(path,v)
    elif role=='fusion-execution':
        path=run/'inspect-owner.json';v=json.loads(path.read_text());v['actors']={}
        for who in ('A','B'):
            v['actors']['commit-'+who]=who
            v['principals']['commit-'+who]=dict(credential=token('commit-observer-'+who+'-token'),scopes={scope:['execution.status','execution.result']})
        write(path,v)
    elif role=='fusion-commitment':
        reg=chain.get('registration');who=reg['principal'] if reg else 'A'
        inspection=run/'inspection.json'
        # Client shape retains both declared ports, but only execution reads are
        # authorized and the commitment network policy has no Messaging edge.
        write(inspection,dict(profile=INSPECTION,fallback=False,scope=scope,principal='commit-'+who,
            ports={name:dict(endpoint=ep(owner),credential=token('commit-observer-'+who+'-token'))
                for name,owner in [('execution','fusion-execution'),('agent.messaging','fusion-messaging')]}))
        cfg.update(scope=scope,registration=reg,principals={'operator':dict(credential=token('caller-token'),
            scopes={scope:['consensus.finality.submit','consensus.finality.observe']})},
            journal=str(state/'commitments.sqlite'),protobuf='/opt/chain/signing/signing_pb2.py',
            signer_file='/secrets/signer.hex',node_endpoint='http://'+settings['peers']['f1r3node']+':40403',inspection=str(inspection),
            atoms=dict(composition=cs.COMPOSITION,principal='commit-observer',scope=scope,credential=token('commit-storage-token'),
                endpoint={**ep('fusion-storage'),'path':cs.ROUTE},descriptor=descriptor_wire(cs.descriptors()[0])))
        write(run/'commitment-client.json',dict(endpoint=ep('fusion-commitment'),credential=token('caller-token'),registration=reg))
