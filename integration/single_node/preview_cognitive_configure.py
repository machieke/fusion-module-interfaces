"""Explicit synthetic cognitive delegation; one owner per service journal.

Each service-to-service credential remains bound to its initiating principal.
Only C2 receives the trusted completion capability. No numerical profile change.
"""
import json
from fusion import cognitive_services as c
from fusion.contracts import require
from fusion.registry import descriptor_wire
from .configure import write
from .cognitive_configure import ASSUMPTION

NAMES=('atom.storage','episodic.memory','belief.revision','attention')
ROLES=tuple(c.ROLES[n] for n in NAMES)


def provider(settings,state,run,token,ep):
    p=settings['preview'];role=settings['role'];scope=p['scope']
    if role not in ROLES:return
    require(p['cognition']['attention_provider'] in ('sqlite','file-fixture'),'UNSUPPORTED_PROFILE')
    principals=[a['principal'] for a in p['agents'].values()]
    catalogue=[descriptor_wire(d) for d in c.descriptors(p['cognition']['attention_provider'])]
    if role=='fusion-storage':cfg=json.loads((run/'cognitive-owner.json').read_text());cfg['catalogue']=catalogue
    else:
        cfg=dict(composition=c.COMPOSITION,privacy=c.PRIVACY,scope=scope,catalogue=catalogue,
            root=str(state/'cognitive'),runtime='/opt/native/runtime.json',attention_provider=p['cognition']['attention_provider'],
            origins={'preview-synthetic-operator':'fresh-explicitly-shareable-operator-input'},assumptions=[ASSUMPTION],
            actors={},principals={},ports_by_principal={},completion_relays={})
        for who in principals:
            cfg['actors'][who]=who
            methods=[n+'.'+op for n in NAMES for op in c.OPERATIONS[n]]+['belief.revision.assume']
            cfg['principals'][who]=dict(credential=token('cognitive-caller-'+who+'-token'),scopes={scope:methods})
            cfg['ports_by_principal'][who]={}
            if role in ('fusion-episodes','fusion-beliefs'):
                cfg['ports_by_principal'][who]['atom.storage']=dict(endpoint=ep('fusion-storage'),credential=token('cognitive-storage-'+who+'-token'))
            if role=='fusion-beliefs':
                cfg['ports_by_principal'][who]['episodic.memory']=dict(endpoint=ep('fusion-episodes'),credential=token('cognitive-episodes-'+who+'-token'))
    # Every owner validates the complete selected catalogue, including storage.
    # Keep its provider discriminator bound to the same explicit selection.
    cfg['attention_provider']=p['cognition']['attention_provider']
    if role=='fusion-storage':
        for who in principals:
            for source in ('fusion-episodes','fusion-beliefs'):
                actor='cognition-'+source+'-'+who;cfg['actors'][actor]=who
                cfg['principals'][actor]=dict(credential=token(actor+'-token'),scopes={scope:['atom.storage.'+op for op in ('create','get','getMany')]})
    if role=='fusion-episodes':
        for who in principals:
            actor='completion-relay-'+who;cfg['actors'][actor]=who;cfg['completion_relays'][actor]=who
            cfg['principals'][actor]=dict(credential=token(actor+'-token'),scopes={scope:['episodic.memory.'+op for op in ('readEpisode','readEvidence','pendingEvidence','acknowledgeDelivery')]})
    write(run/'cognitive-owner.json',cfg)


def agent(settings,app,current,own,principal,sid,token,ep):
    p=settings['preview'];require(p.get('memory',{}).get('enabled'),'UNSUPPORTED_PROFILE')
    require('episodic.memory' in app['facet_configs'],'UNSUPPORTED_PROFILE')
    catalogue=[descriptor_wire(d) for d in c.descriptors(p['cognition']['attention_provider'])]
    app['preview']['providers']+=catalogue
    app['preview']['base']=c.APPLICATION
    ports={name:dict(endpoint=ep(c.ROLES[name]),credential=token('atom-'+principal+'-token' if name=='atom.storage' else 'cognitive-'+c.ROLES[name]+'-token')) for name in NAMES}
    client=dict(composition=c.COMPOSITION,privacy=c.PRIVACY,scope=p['scope'],catalogue=catalogue,
        attention_provider=p['cognition']['attention_provider'],placement='service-network',fallback=False,
        principal=principal,context='synthetic-native-assessment',session=sid,sources={},assumption=ASSUMPTION,
        selected_interfaces=list(NAMES),ports=ports)
    write(current/'evidence-client.json',client)
    write(current/'attention-client.json',dict(client,output=str(own/'promoted-context.metta')))
    app.update(evidence_config=str(current/'evidence-client.json'),attention_config=str(current/'attention-client.json'))
    return app
