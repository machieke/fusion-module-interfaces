"""Fixed A/B task route selection; no model-controlled endpoint or credentials."""
import json
from fusion.contracts import require
from fusion.preview_tasks import PROFILE,descriptor
from fusion.registry import descriptor_wire
from .configure import write


def enabled(settings):return settings['preview'].get('tasks',{}).get('enabled',False)


def client(settings,current,principal,token,ep):
    p=settings['preview'];recipients={}
    for role,agent in p['agents'].items():
        if agent['principal']!=principal:
            recipients[agent['principal']]=dict(endpoint=ep(role),credential=token('task-wake-'+agent['principal']+'-token'))
    path=current/'tasks.json'
    write(path,dict(profile=PROFILE,fallback=False,scope=p['scope'],principal=principal,endpoint=ep('fusion-messaging'),
        credential=token('task-mailbox-token'),descriptor=descriptor_wire(descriptor()),recipients=recipients))
    return path


def provider(settings,cfg,state,run,token,ep):
    p=settings['preview'];agents=p['agents'];role=settings['role'];scope=p['scope']
    require(len(agents)==2 and p.get('memory',{}).get('enabled') is True,'UNSUPPORTED_PROFILE')
    sessions={a['principal']:a['sessions'] for a in agents.values()}
    if role=='fusion-storage':
        path=run/'cognitive-owner.json';value=json.loads(path.read_text())
        for who in sessions:
            key='tasks-reader-'+who;value['actors'][key]=who
            value['principals'][key]=dict(credential=token('task-storage-'+who+'-token'),scopes={scope:['atom.storage.get']})
        write(path,value)
    elif role=='fusion-messaging':
        from fusion import cognitive_services as cs
        value=dict(profile=PROFILE,scope=scope,messages_database=cfg['messages_database'],capacity=4,
            inboxes={who:'task-'+who for who in sessions},sessions=sessions,routes={},principals={},atom_clients={})
        for who in sessions:
            value['routes']['task-'+who]=dict(scope=scope,owner=who)
            value['principals'][who]=dict(credential=token('task-caller-'+who+'-token'),scopes={scope:[*['tasks.'+op for op in ('authorize','send','published','poll','ack')],*['agent.messaging.'+op for op in ('send','poll','ack')]]})
            value['atom_clients'][who]=dict(composition=cs.COMPOSITION,principal=who,scope=scope,credential=token('task-storage-'+who+'-token'),
                endpoint={**ep('fusion-storage'),'path':cs.ROUTE},descriptor=descriptor_wire(cs.descriptors()[0]))
        write(run/'task-owner.json',value)
    elif role in agents:
        agent=agents[role];who=agent['principal'];sid=agent['sessions'][0]
        for peer in sessions:
            if peer!=who:cfg['principals']['task-hint-'+peer]=dict(credential=token('task-ingress-'+peer+'-token'),scopes={scope:['tasks.wake']})
        cfg['principals']['worker']['scopes'][scope].append('tasks.ingress')
        cfg['task_ingress']=dict(profile=PROFILE,principal=who,scope=scope,peers=[x for x in sessions if x!=who],
            session=sid,database=str(state/'task-ingress.sqlite'),client=str(run/'sessions'/sid/'tasks.json'),
            atoms=json.loads((run/'sessions'/sid/'memory-atoms.json').read_text()))
