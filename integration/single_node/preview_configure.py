"""Fresh preview selections on the existing chart/process host.

Only trusted ConfigMap and mounted Secret inputs choose scopes, ports and
bounded session templates. No occurrence deadline starts during configuration.
"""
import copy
import json
from pathlib import Path
from fusion import cognitive_services as cs, preview_model_contracts as mc
from fusion import neoclaw_contracts as nal
from fusion.contracts import canonical,digest,require
from fusion.preview_application import APPLICATION, configuration as catalogue
from fusion.preview_ports import COMPOSITION as FACETS, ROLES as FACET_ROLES, OPERATIONS, descriptor
from fusion.preview_sessions import PROFILE as SESSIONS,MAX_INPUT_WINDOW_MS
from fusion.registry import descriptor_wire
from .configure import write

from fusion.preview_deployment_contracts import COMPOSITION


def configure(settings):
    if settings['preview'].get('profile') == 'omega-single-node-sustained-preview/1':
        from .sustained_configure import configure as sustained
        return sustained(settings)
    role=settings['role'];p=settings['preview'];scope=p['scope']
    require(p['profile']==COMPOSITION and p['enabled'] is True and p['model_boundary']=='RECORDED_FIXTURE','UNSUPPORTED_PROFILE')
    require(scope.startswith('synthetic-') and 1<=len(p['agents'])<=2,'UNAUTHORIZED')
    limits=p['limits'];require(type(limits) is dict and set(limits)=={'inputs','pending','timeout_ms'})
    for key,upper in (('inputs',32),('pending',4),('timeout_ms',MAX_INPUT_WINDOW_MS)):
        require(type(limits[key]) is int and 1<=limits[key]<=upper,'OVERLOADED')
    require(settings.get('futureLive') is None,'UNAUTHORIZED')
    state=Path(settings.get('state','/state'));run=Path(settings.get('run','/run/fusion'))
    secret=Path(settings.get('secret_directory','/secrets'))
    state.mkdir(parents=True,exist_ok=True);run.mkdir(parents=True,exist_ok=True)
    def token(name):
        value=(secret/name).read_text().strip();require(value.isascii() and 32<=len(value)<=256,'UNAUTHORIZED');return value
    def ep(name):return dict(host=settings['peers'][name],port=settings['https_port'],ca_file=str(secret/'ca.crt'))
    agents=p['agents'];principals=[a['principal'] for a in agents.values()]
    require(len(set(principals))==len(principals),'CONFLICT')
    private={a['principal']:a['private_scope'] for a in agents.values() if 'private_scope' in a}
    # Older development selections remain shared-only. New generated selections
    # allocate both private synthetic denial scopes together; no data is migrated.
    if private:
        import re
        require(all(type(s) is str and re.fullmatch(r'synthetic-[A-Za-z0-9_.-]+',s) for s in private.values()),'UNAUTHORIZED')
        require(len(private)==len(agents) and len(set([scope,*private.values()]))==len(agents)+1,'CONFLICT')
    session_principals={sid:a['principal'] for a in agents.values() for sid in a['sessions']}
    require(len(session_principals)==sum(len(a['sessions']) for a in agents.values()),'CONFLICT')
    disclosure=dict(profile='synthetic-recorded-prompt/1',scope=scope,principals=principals,
        session_principals=session_principals,max_prompt_bytes=mc.MAX_PROMPT)
    cfg=dict(tls_certificate=str(secret/'tls.crt'),tls_key=str(secret/'tls.key'))
    test=settings.get('test',{})
    require(not test or settings.get('enable_test_faults') is True,'UNAUTHORIZED')
    base_role='omega-agent' if role in agents else role
    if base_role in ('omega-agent','fusion-execution','fusion-storage','fusion-messaging'):
        base={k:v for k,v in settings.items() if k not in ('preview','reference','workflow')}
        base.update(role=base_role,service_composition='neoclaw-separated-services/1')
        write(run/'base-component.json',base)
        from .configure import configure as historical
        _,cfg,_,_=historical(run/'base-component.json')
    # Separate native principals also use the existing deterministic S01 ports.
    if role in ('fusion-execution','fusion-storage','fusion-messaging'):
        if role=='fusion-execution' and p.get('inspection',{}).get('nal_envelopes'):
            from fusion.nal_envelope import PROFILE as nal_envelope
            cfg['portable_execution']=nal_envelope
        for principal in principals:
            if principal!='A':cfg['principals'][principal]={**copy.deepcopy(cfg['principals']['A']), 'credential':token('caller-'+principal+'-token')}
        cfg['routes'].update({'reply-'+principal:dict(scope=nal.SCOPE,owner=principal) for principal in principals})
    descriptors={name:descriptor_wire(descriptor(name)) for name in OPERATIONS}
    def atoms(principal,selected_scope=scope):
        return dict(composition=cs.COMPOSITION,principal=principal,scope=selected_scope,credential=token('atom-'+principal+'-token'),
            endpoint={**ep('fusion-storage'),'path':cs.ROUTE},descriptor=descriptor_wire(cs.descriptors()[0]))
    if role=='fusion-storage':
        cc=dict(composition=cs.COMPOSITION,privacy=cs.PRIVACY,scope=scope,root=str(state/'memory'),
            storage_layout='preview-shared-feed/1',backend_layout='detta-opaque-coordinate-partitions/1',catalogue=[descriptor_wire(d) for d in cs.descriptors()],
            detta_binary='/opt/native/fusion-detta-adapter',actors={x:x for x in principals},principals={})
        for principal in principals:
            cc['principals'][principal]=dict(credential=token('cog-caller-'+principal+'-token'),
                scopes={scope:['atom.storage.'+op for op in cs.OPERATIONS['atom.storage']]})
            if principal in private:
                cc['principals'][principal]['scopes'][private[principal]]=['atom.storage.'+op for op in cs.OPERATIONS['atom.storage']]
            for delegated in ('fusion-episodes','fusion-relations'):
                key='delegated-'+delegated+'-'+principal+'-token'
                if (secret/key).exists():
                    actor='facet-'+delegated+'-'+principal
                    cc['actors'][actor]=principal
                    cc['principals'][actor]=dict(credential=token(key),scopes={scope:['atom.storage.'+op for op in ('create','get','getMany')]})
        if private:cc['allowed_scopes']=[scope,*private.values()]
        write(run/'cognitive-owner.json',cc)
    if role in FACET_ROLES.values():
        names=[name for name,owner in FACET_ROLES.items() if owner==role]
        methods=[name+'.'+op for name in names for op in OPERATIONS[name]]
        if 'episodic.memory' in names:methods+=['episodic.memory.appendEvent','episodic.memory.readEpisode']
        if 'relations' in names:methods+=['relations.history']
        from fusion.lookup_contracts import SCHEMAS
        from fusion.preview_native_relations import SCHEMAS as PREVIEW_SCHEMAS
        fc=dict(composition=FACETS,scope=scope,root=str(state/'preview-facets'),schemas={**SCHEMAS,**PREVIEW_SCHEMAS},
            descriptors={name:descriptors[name] for name in names},principals={},atom_clients={})
        for principal in principals:
            fc['principals'][principal]=dict(credential=token('facet-caller-'+principal+'-token'),scopes={scope:methods})
            if role!='fusion-execution':fc['atom_clients'][principal]=atoms(principal)
        write(run/'facet-owner.json',fc)
    if role=='fusion-model':
        require(p.get('responses') is not None,'NOT_AVAILABLE')
        cfg.update(principals={x:dict(credential=token('caller-'+x+'-token'),scopes={scope:['model.'+op for op in ('disclose','complete','observe','authorize')]}) for x in principals},
            model_completion=dict(database=str(state/'model.sqlite'),scope=scope,sharing=mc.PRIVACY,
                sessions=[sid for a in agents.values() for sid in a['sessions']],max_calls=128,
                expires_ms=p['authority_expires_ms'],catalogue=[descriptor_wire(mc.descriptor())],disclosure=disclosure,
                recorded_proposals=p['responses'],runtime_lock=dict(profile=mc.PROFILE,generative_runtime='FORBIDDEN',
                    proposals_sha256=digest(canonical(p['responses'])))))
    if p.get('memory',{}).get('enabled') and role in ('fusion-storage','fusion-search','fusion-embedding'):
        from .preview_memory_configure import provider
        provider(settings,cfg,state,run,secret,token,ep)
    if p.get('cognition',{}).get('enabled'):
        from .preview_cognitive_configure import provider
        provider(settings,state,run,token,ep)
    if role in agents:
        agent=agents[role];principal=agent['principal']
        if principal in private:write(run/'private-atoms.json',atoms(principal,private[principal]))
        require(1<=len(agent['sessions'])<=8 and len(set(agent['sessions']))==len(agent['sessions']))
        base_app=json.loads((run/'application.json').read_text());base_caller=json.loads((run/'caller.json').read_text())
        if p.get('inspection',{}).get('nal_envelopes'):
            from fusion.nal_envelope import PROFILE as nal_envelope
            base_caller['portable_execution']=nal_envelope
        authority=run/'authority.json'
        write(authority,dict(principal=principal,scope=scope,tools=agent['tools'],revision=p['policy_revision'],
            expires_ms=p['authority_expires_ms'],revoked=False))
        templates={}
        for sid in agent['sessions']:
            mc.uid(sid)
            current=run/'sessions'/sid;current.mkdir(parents=True,exist_ok=True)
            own=state/'sessions'/sid;own.mkdir(parents=True,exist_ok=True)
            chosen=[descriptor_wire(d) for d in nal.catalogue('detta')]+[descriptors[n] for n in agent['facets']]
            if p.get('memory',{}).get('enabled'):
                from fusion import append_contracts as w,embedding_contracts as e,vector_contracts as v
                from fusion.vector_composition import descriptors as reads
                from fusion.preview_memory_services import descriptor as active_descriptor
                chosen += [descriptor_wire(d) for d in (*w.descriptors(),*reads(v.EMBEDDING,True),e.descriptor(),e.descriptor(e.MEMORY_PROFILE),active_descriptor('search'),active_descriptor('memory.lifecycle'))]
            if p.get('tasks',{}).get('enabled'):
                from fusion.preview_tasks import descriptor as task_descriptor
                chosen.append(descriptor_wire(task_descriptor()))
            if p.get('inspection',{}).get('enabled'):
                from fusion.registry import descriptors as inspection_descriptors
                inspection_values=[descriptor_wire(d) for d in inspection_descriptors() if d.interface in ('execution','agent.messaging')]
                selected=p.get('inspection',{}).get('execution_descriptor')
                if selected is not None:
                    inspection_values=[d for d in inspection_values if d['interface']!='execution']+[selected]
                chosen += inspection_values
            preview=dict(profile=APPLICATION,base='controlled-native-loop/1',authority_file=str(authority),
                tools=agent['tools'],scope=scope,providers=chosen)
            write(current/'caller.json',{**base_caller,'principal':principal,'reply_route':'reply-'+principal,'database':str(own/'caller.sqlite')})
            client=dict(profile=SESSIONS,placement='network',endpoint=ep(role),principal=principal,
                actor='worker',session=sid,credential=token('session-worker-token'))
            write(current/'session.json',client)
            write(current/'model.json',dict(profile=mc.PROFILE,placement='network',fallback=False,endpoint=ep('fusion-model'),
                principal=principal,scope=scope,session=sid,credential=token('fusion-model-token'),catalogue=[descriptor_wire(mc.descriptor())],
                disclosure=disclosure))
            facet_configs={}
            for name in agent['facets']:
                file=current/(name+'.json')
                write(file,dict(composition=FACETS,placement='network',fallback=False,principal=principal,scope=scope,
                    credential=token('facet-'+FACET_ROLES[name]+'-token'),endpoint=ep(FACET_ROLES[name]),descriptors={name:descriptors[name]}))
                facet_configs[name]=str(file)
            app={**base_app,'composition':APPLICATION,'preview':preview,'session_id':sid,
                'caller_config':str(current/'caller.json'),'session_config':str(current/'session.json'),
                'model_config':str(current/'model.json'),'facet_configs':facet_configs,'turn_limit':p['limits']['inputs'],
                'workdir':str(own/'native'),'status_file':str(own/'native-status.json'),
                'preparation_diagnostics':settings['enable_test_faults'] is True}
            app.pop('model_fixture',None)
            if 'episodic.memory' in agent['facets']:
                write(current/'history-atoms.json',atoms(principal));app['history_atoms_config']=str(current/'history-atoms.json')
            if p.get('memory',{}).get('enabled'):
                from .preview_memory_configure import agent as memory_agent
                app=memory_agent(settings,app,current,own,principal,sid,secret,token,ep)
                write(current/'memory-atoms.json',atoms(principal));app['memory_atoms_config']=str(current/'memory-atoms.json')
            if p.get('cognition',{}).get('enabled'):
                from .preview_cognitive_configure import agent as cognitive_agent
                app=cognitive_agent(settings,app,current,own,principal,sid,token,ep)
            if p.get('tasks',{}).get('enabled'):
                from .preview_task_configure import client as task_client
                app['task_config']=str(task_client(settings,current,principal,token,ep))
            if p.get('inspection',{}).get('enabled'):
                from .preview_inspect_configure import client as inspection_client
                app['inspect_config']=str(inspection_client(settings,current,principal,token,ep))
            selected=catalogue(app['preview'])
            write(current/'application.json',app)
            templates[sid]=dict(catalogue=selected.identity,policy=p['policy_revision'],model_boundary='RECORDED_FIXTURE',limits=p['limits'])
        cfg.update(principals={
            'operator':dict(credential=token('session-operator-token'),scopes={scope:['sessions.'+op for op in ('create','submit','observe','disclose','pause','resume','close')]}),
            'worker':dict(credential=token('session-worker-token'),scopes={scope:['sessions.next','sessions.complete']})},
            native_sessions=dict(profile=SESSIONS,model_boundary='RECORDED_FIXTURE',scope=scope,principal=principal,
                database=str(state/'session-inbox.sqlite'),assignments=p['assignments'],session_templates=templates))
    if p.get('tasks',{}).get('enabled'):
        from .preview_task_configure import provider as task_provider
        task_provider(settings,cfg,state,run,token,ep)
    if p.get('inspection',{}).get('enabled'):
        from .preview_inspect_configure import provider as inspection_provider
        inspection_provider(settings,cfg,state,run,token,ep)
    if p.get('chain',{}).get('enabled'):
        from .preview_chain_configure import provider as chain_provider
        chain_provider(settings,cfg,state,run,token,ep)
    # New preview owners share the existing one-shot deployed kill barrier.
    # Its durable marker suppresses the barrier after replacement; it grants
    # no retry, new identity, authority, or renewed operation window.
    cfg.update(test_failpoints=bool(test),failpoint_marker=str(state/'pause.json'))
    if test.get('pause_at') and not (state/'pause.json').exists():cfg['pause_at']=test['pause_at']
    else:cfg.pop('pause_at',None)
    write(run/'owner.json',cfg)
    return settings,cfg,state,run
