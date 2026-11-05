"""Additional trusted inspection selection without rebinding accepted templates.

The caller chooses only an allowlisted allocation template. Source paths,
endpoints, credentials and provider descriptor remain operator configuration.
No accepted session or foreign owner state is rewritten.
"""
import copy
from pathlib import Path
from fusion.contracts import require,canonical
from fusion.registry import descriptor_wire,selection_token
from fusion.reference_inspect_contracts import descriptor
from fusion.preview_inspect import selections
from fusion.preview_application import configuration as catalogue
from fusion.sustained_sessions import allocation_policy
from .configure import write
from .sustained_runtime import template_files,runtime_digest

PROFILE='retained-inspection-template/1'


def configure(settings,cfg,state,run):
    p=settings['preview'];extra=p.get('inspection',{}).get('additional_template')
    if extra is None or settings['role'] not in p['agents']:return cfg
    require(type(extra) is dict and set(extra)=={'profile','name','service','descriptor'},'UNSUPPORTED_PROFILE')
    require(extra['profile']==PROFILE and extra['name']=='go-shared' and extra['service']=='fusion-inspect-go','UNSUPPORTED_PROFILE')
    require(canonical(extra['descriptor'])==canonical(descriptor_wire(descriptor())),'UNSUPPORTED_PROFILE')
    require(extra['service'] in settings['peers'] and p['inspection'].get('enabled') and p.get('tasks',{}).get('enabled'),'NOT_AVAILABLE')
    selected=cfg['native_sessions'];name=extra['name'];original=selected['runtime_templates']['shared']
    require(name not in selected['allocation']['templates'] and name not in selected['runtime_templates'],'CONFLICT')
    files=template_files(original['directory']);app=files['application.json']
    filename=Path(app['inspect_config']).name;require(filename=='inspection.json' and filename in files,'NOT_AVAILABLE')
    inspector=files[filename];before=descriptor_wire(selections(inspector)['execution'])
    require(inspector['scope']==p['scope'] and inspector['principal']==selected['principal'],'UNAUTHORIZED')
    require(sum(canonical(raw)==canonical(before) for raw in app['preview']['providers'])==1,'CONFLICT')
    inspector['execution_descriptor']=copy.deepcopy(extra['descriptor'])
    inspector['ports']['execution']['endpoint']['host']=settings['peers'][extra['service']]
    require(selection_token(selections(inspector)['execution'])==selection_token(descriptor()),'UNSUPPORTED_PROFILE')
    app['preview']['providers']=[copy.deepcopy(extra['descriptor']) if canonical(raw)==canonical(before) else raw for raw in app['preview']['providers']]
    identity=catalogue(app['preview']).identity
    directory=Path(run)/'templates'/name;directory.mkdir(parents=True,exist_ok=True)
    for filename,value in files.items():write(directory/filename,value)
    template=copy.deepcopy(selected['allocation']['templates']['shared'])
    template['binding']['catalogue']=identity;template['runtime_digest']=runtime_digest(files,original['ca_file'])
    selected['allocation']['templates'][name]=template
    selected['runtime_templates'][name]={**original,'directory':str(directory)}
    allocation_policy(selected['allocation'])
    return cfg


def inspection_role(settings,recipe,app,raw):
    """Resolve the selected immutable descriptor through trusted recipe ports."""
    path=app.get('inspect_config')
    if path is None:return None
    files=template_files(recipe['directory']);selected=files.get(Path(path).name)
    require(type(selected) is dict,'NOT_AVAILABLE')
    if canonical(descriptor_wire(selections(selected)['execution']))!=canonical(raw):return None
    endpoint=selected['ports']['execution']['endpoint']
    require(endpoint['port']==settings['https_port'],'UNAUTHORIZED')
    matches=[role for role,host in settings['peers'].items() if host==endpoint['host']]
    require(len(matches)==1,'UNAUTHORIZED');return matches[0]
