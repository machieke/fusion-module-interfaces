"""Caller-owned handoff between setup and a new measured read-only session."""
import json
from pathlib import Path
import sqlite3
import time
from fusion.contracts import canonical,digest,require
from fusion import model_contracts as m,retrieval_services as rs
from fusion.registry import descriptor_wire
from integration.neoclaw.model_startup import retrieval_scaffold
from .configure import write


def seal_setup(settings,state):
    status=json.loads((state/'native-status.json').read_text())
    require(status['status']=='BOUNDED_STOP','NOT_AVAILABLE')
    with sqlite3.connect((state/'caller.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        writes=db.execute('SELECT * FROM app_memory_writes ORDER BY rowid').fetchall()
        occs=db.execute('SELECT * FROM app_occurrences').fetchall()
        require(len(writes)==len(settings['memory']['inputs']) and all(r['done']==1 for r in occs),'NOT_AVAILABLE')
        view=json.loads(db.execute('SELECT value FROM app_read_views WHERE id=(SELECT view FROM app_active_view)').fetchone()[0])
        records=[]
        for r in writes:
            require(r['linked']==1 and r['view'],'NOT_AVAILABLE');intent=json.loads(r['intent'])
            records.append(dict(uuid=r['uuid'],time=r['sampled_time'],content=intent['content'],metadata=next(x for x in view['metadata']['records'] if x['uuid']==r['uuid'])))
        require({r['content'] for r in records}==set(settings['memory']['inputs'].values()),'UNAUTHORIZED')
    value=dict(view=view,records=records,setup_session=settings['memory']['session'])
    p=state/'setup-view.json'
    if p.exists():require(json.loads(p.read_bytes())==value,'CONFLICT')
    else:write(p,value)


def prepare(settings,state,run):
    if settings['workflow']['phase']=='setup':
        from .memory_host import prepare_agent
        return prepare_agent(settings,state,run)
    w=settings['workflow'];setup=json.loads((state/'setup-view.json').read_bytes());view=setup['view']
    require(set(view)=={'snapshot','metadata','metadata_seal'} and len(view['metadata']['records'])==len(setup['records']),'CONFLICT')
    read=json.loads((run/'memory-read-template.json').read_text());read.update(snapshot=view['snapshot'],metadata_seal=view['metadata_seal']);write(run/'memory-read.json',read)
    write(state/'measured-metadata.json',view['metadata'])
    # Same helper and metadata view as native append selected, not a new store.
    sdk=json.loads(Path('/opt/memory-runtime.json').read_text());runtime=Path('/opt/memory-runtime.json')
    write(run/'memory-native.json',dict(site=str(Path(sdk['sdk'])/'lib/python3.12/site-packages'),helper=sdk['helper'],runtime=str(runtime),runtime_sha256=digest(runtime.read_bytes()),embedding_boundary='port',metadata_manifest=str(state/'measured-metadata.json'),metadata_seal=view['metadata_seal'],promotions=str(state/'measured-promotions.sqlite'),clock_fixture=settings['memory'].get('clock_fixture',2000000000.),creation_clock_fixture=settings['memory'].get('creation_clock_fixture')))
    import importlib.util
    source=Path('/opt/native/sources/mettaclaw/src/helper.py')
    spec=importlib.util.spec_from_file_location('measured_metadata_helper',source);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    promotions=state/'measured-promotions.sqlite'
    helper.promotion_open_map(str(promotions))
    keys=set(helper.promotion_get_all_keys());require(keys<={r['uuid'] for r in view['metadata']['records']},'CONFLICT')
    for row in view['metadata']['records']:
        if row['uuid'] in keys:
            require(helper.promotion_get_value(row['uuid'])==row['promotion'] and helper.promotion_get_lasttime(row['uuid'])==view['metadata']['promotion_time'],'CONFLICT')
        else:
            helper.promotion_set_value(row['uuid'],row['promotion']);helper.promotion_set_lasttime(row['uuid'],view['metadata']['promotion_time'])
    helper.promotion_commit();helper.promotion_close_map()
    consent=dict(recipient=w['recipient'],records=setup['records'])
    policy=dict(policy=rs.POLICY,scaffold=retrieval_scaffold(),memories=['()'],users=[str(['HUMAN-MSG:','peer: '+x]) for x in (w['question'],w['followup'])],query=w['query'],recipient=w['recipient'],consent_sha256=digest(canonical(consent)),view_sha256=digest(canonical(view)),receipt_root=str(state/'disclosure-receipts'))
    client=dict(profile=m.CPU_PROFILE,sharing=m.PRIVACY,principal='M',scope=w['modelScope'],session=w['session'],placement='service-network',service_composition=rs.COMPOSITION,fallback=False,catalogue=[descriptor_wire(m.descriptor(m.CPU_PROFILE))],disclosure=policy,commands=[['query',w['query']]]+[['send',x] for x in w['bodies']],endpoint=dict(host=settings['peers']['fusion-model'],port=settings['https_port'],ca_file='/secrets/ca.crt'),credential=Path('/secrets/fusion-model-token').read_text().strip())
    write(run/'model-client.json',client)
    app=json.loads((run/'application.json').read_text());app['retrieval']=dict(initial_view=view,consent=consent);write(run/'application.json',app)
