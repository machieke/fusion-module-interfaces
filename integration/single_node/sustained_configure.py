"""Opt-in fresh-state operational selection over the existing component recipe."""
import copy
import json
from pathlib import Path
import uuid

from fusion.contracts import canonical, digest, require
from fusion.sustained_sessions import PROFILE, ALLOCATION, allocation_policy
from .configure import write
from .sustained_runtime import template_files, runtime_digest

COMPOSITION='omega-single-node-sustained-preview/1'


def configure(settings):
    p=settings['preview'];require(p['profile']==COMPOSITION,'UNSUPPORTED_PROFILE')
    selected=p['sustained']
    require(type(selected) is dict and {'allocation'}<=set(selected)<={'allocation','feed_capacity','private_scopes','model_binding'},'UNSUPPORTED_PROFILE')
    a=selected['allocation']
    require(type(a) is dict and set(a)=={'active','retained','pending','bytes','lifetime_ms'})
    shadow=copy.deepcopy(settings);shadow['preview']['profile']='omega-single-node-developer-preview/1'
    shadow['preview'].pop('sustained')
    from .preview_configure import configure as existing
    _,cfg,state,run=existing(shadow)
    from .sustained_capacity import configure as capacity_selection
    cfg=capacity_selection(settings,cfg,state,run)
    role=settings['role'];principals=[x['principal'] for x in p['agents'].values()]
    disclosure=dict(profile='synthetic-session-prompt/1',scope=p['scope'],principals=principals,
                    max_prompt_bytes=32768,session_authority='bounded-authenticated-model-sessions/1')
    if role=='fusion-model':
        m=cfg['model_completion'];proposals={who:{'proposal':'input-command'} for who in principals}
        m.update(sessions=dict(profile='bounded-authenticated-model-sessions/1',principals=principals,max_sessions=min(16,a['retained']*len(principals))),
            disclosure=disclosure,session_proposals=proposals,
            runtime_lock=dict(profile=m['runtime_lock']['profile'],generative_runtime='FORBIDDEN',session_proposals_sha256=digest(canonical(proposals))))
        m.pop('recorded_proposals')
    from .sustained_model import configure as model_selection
    cfg=model_selection(settings,cfg,state,run)
    if role in p['agents']:
        agent=p['agents'][role];require(len(agent['sessions'])==1,'UNSUPPORTED_PROFILE')
        seed=agent['sessions'][0];source=run/'sessions'/seed
        files=template_files(source)
        files['session.json']['profile']=PROFILE
        files['model.json']['disclosure']=dict(disclosure,max_prompt_bytes=files['model.json']['disclosure']['max_prompt_bytes'])
        # Operational telemetry is selected independently of fault injection.
        files['application.json']['preparation_diagnostics']=True
        files['application.json']['native_telemetry']=dict(profile='bounded-native-stage-timing/1',max_bytes=4194304)
        files['application.json']['native_dispatch_quantum']=1
        directory=run/'templates'/'shared';directory.mkdir(parents=True,exist_ok=True)
        for name,value in files.items():write(directory/name,value)
        ca_file=Path(settings.get('secret_directory','/secrets'))/'ca.crt'
        binding=cfg['native_sessions']['session_templates'][seed]
        from fusion.preview_application import configuration as catalogue
        from fusion.preview_model_binding import boundary
        binding=dict(binding,catalogue=catalogue(files['application.json']['preview']).identity,model_boundary=boundary(files['model.json']))
        template=dict(principal=agent['principal'],scope=p['scope'],binding=binding,
                      lifetime_ms=a['lifetime_ms'],runtime_digest=runtime_digest(files,ca_file))
        allocation=dict(profile=ALLOCATION,owner=str(uuid.uuid5(uuid.NAMESPACE_URL,p['policy_revision']+'/'+role)),
            **{k:a[k] for k in ('active','retained','pending','bytes')},templates={'shared':template})
        allocation_policy(allocation)
        cfg['native_sessions']=dict(profile=PROFILE,principal=agent['principal'],scope=p['scope'],
            database=str(state/'session-inbox.sqlite'),assignments=p['assignments'],allocation=allocation,
            runtime_templates={'shared':dict(seed_session=seed,directory=str(directory),ca_file=str(ca_file))})
        ops=('allocate','capacity','list','submit','observe','disclose','pause','resume','close','archive','cancel','reconcile')
        cfg['principals']['operator']['scopes'][p['scope']]=['sessions.'+op for op in ops]
        worker=cfg['principals']['worker']['scopes'][p['scope']]
        worker[:]=list(dict.fromkeys(worker+['sessions.'+op for op in ('list','permit','reconcile','observe')]))
    from .sustained_tasks import configure as task_selection
    task_selection(settings,cfg,state,run)
    if (run/'cognitive-owner.json').exists():
        from fusion.sustained_observation import PROFILE as observations
        value=json.loads((run/'cognitive-owner.json').read_bytes());value['current_observations']=observations;write(run/'cognitive-owner.json',value)
    from .sustained_private import configure as private_selection
    cfg=private_selection(settings,cfg,state,run)
    write(run/'owner.json',cfg)
    return settings,cfg,state,run
