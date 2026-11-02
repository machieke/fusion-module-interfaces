"""Explicit synthetic inspect ports on the existing three physical owners."""
import json
from fusion.contracts import require
from fusion import cognitive_services as cs
from fusion.registry import descriptor_wire,descriptors
from fusion.preview_inspect import PROFILE
from .configure import write


def client(settings,current,principal,token,ep):
    path=current/'inspection.json'
    write(path,dict(profile=PROFILE,fallback=False,scope=settings['preview']['scope'],principal=principal,
        ports={name:dict(endpoint=ep(role),credential=token('inspect-'+role+'-token'))
            for name,role in [('execution','fusion-execution'),('agent.messaging','fusion-messaging')]}))
    return path


def provider(settings,cfg,state,run,token,ep):
    p=settings['preview'];scope=p['scope'];role=settings['role']
    require(p.get('tasks',{}).get('enabled') and p.get('memory',{}).get('enabled'),'UNSUPPORTED_PROFILE')
    if role=='fusion-storage':
        path=run/'cognitive-owner.json';value=json.loads(path.read_text());who='inspect-worker'
        value['actors'][who]=who;value['principals'][who]=dict(credential=token('inspect-storage-token'),scopes={scope:['atom.storage.get','atom.storage.create']})
        write(path,value)
    elif role in ('fusion-execution','fusion-messaging'):
        value=dict(profile=PROFILE,scope=scope,database=str(state/'preview-inspect.sqlite'),capacity=4,
            routes={'inspect-'+a['principal']:dict(scope=scope,owner=a['principal']) for a in p['agents'].values()},principals={})
        for a in p['agents'].values():
            who=a['principal'];methods=['execution.submit','execution.status','execution.result','atom.storage.get','agent.messaging.poll'] if role=='fusion-execution' else ['agent.messaging.poll','agent.messaging.ack']
            value['principals'][who]=dict(credential=token('inspect-caller-'+who+'-token'),scopes={scope:methods})
        if role=='fusion-execution':
            value['principals']['worker']=dict(credential=token('worker-token'),scopes={scope:['atom.storage.get','atom.storage.create']})
            value['atom_clients']={'worker':dict(composition=cs.COMPOSITION,principal='inspect-worker',scope=scope,
                credential=token('inspect-storage-token'),endpoint={**ep('fusion-storage'),'path':cs.ROUTE},descriptor=descriptor_wire(cs.descriptors()[0]))}
            value['completion_port']=dict(endpoint=ep('fusion-messaging'),credential=token('inspect-completion-token'))
        else:
            value['messages_database']=cfg['messages_database']
            value['principals']['worker']=dict(credential=token('inspect-completion-token'),scopes={scope:['agent.messaging.accept']})
        write(run/'inspect-owner.json',value)
