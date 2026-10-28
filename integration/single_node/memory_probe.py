"""Explicit operator probes on fresh synthetic qualification state only.

No new service endpoint. Reuses existing typed ports/owners. Never inserts a
memory or edits application/owner journals. Tests are not native workflow runs.
"""
import copy
import http.client
import json
from pathlib import Path
import sqlite3
import time
import uuid

from fusion import append_contracts as w, vector_contracts as v
from fusion.contracts import ContractError,canonical,digest
from fusion.neoclaw_transport import Network,json_loads
from fusion.registry import descriptor_read,selection_token
from fusion.vector_composition import select


def agent_auth():
    cfg=json.loads(Path('/run/fusion/memory-read.json').read_text());chosen=select([descriptor_read(d) for d in cfg['catalogue']],v.EMBEDDING,True)
    db=sqlite3.connect('file:/state/caller.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
    row=db.execute('SELECT * FROM app_memory_reads ORDER BY rowid LIMIT 1').fetchone();query=json.loads(row['request']);d=chosen['search']
    request=dict(request_id=query['request_id'],interface_ref=dict(id=d.interface,version=d.version),operation='authorize-ready',
        scope=cfg['scope'],profile=v.PROFILE,selection=selection_token(d),body=dict(query=cfg['queries'][0],snapshot=query['snapshot']))
    def send(name,path,req,token=None):
        port=Network(cfg['endpoints'][name],token or cfg['service_credentials'][name],None,service_dns=True)
        conn=http.client.HTTPSConnection(port.endpoint['host'],port.endpoint['port'],context=port.context,timeout=3)
        try:
            conn.request('POST',path,canonical(req),{'Authorization':'Bearer '+port.credential,'Content-Type':'application/json'})
            res=conn.getresponse();assert res.status==200;return json_loads(res.read(98305))
        finally:conn.close()
    result={}
    bad=send('search','/s03-read',request,'wrong-'*10);result['wrong_credential']=bad['error']['code'];assert result['wrong_credential']=='UNAUTHORIZED'
    for field,value in [('scope','another-scope'),('selection','0'*64),('profile','another-profile')]:
        bad=send('search','/s03-read',{**request,field:value});result[field]=bad['error']['code']
    assert result['scope']=='UNAUTHORIZED' and result['selection']==result['profile']=='UNSUPPORTED_PROFILE'
    bad_query={**request,'operation':'query','body':{**query,'vector':[float(0)]}}
    result['malformed_vector']=send('search','/s03-read',bad_query)['error']['code'];assert result['malformed_vector']=='INVALID_ARGUMENT'
    write=db.execute('SELECT * FROM app_memory_writes ORDER BY rowid LIMIT 1').fetchone();accepted=json.loads(write['intent'])
    descriptor=w.select(w.descriptors())['atom.storage'];changed={**accepted,'uuid':str(uuid.uuid4())}
    receipt=dict(request_id=accepted['occurrence'],scope=cfg['scope'],interface_ref=dict(id=descriptor.interface,version=descriptor.version),
        operation='observe',profile=next(iter(descriptor.profiles)),selection=selection_token(descriptor),intent=changed,body={'role':'binding'})
    result['changed_identity_content']=send('atom.storage','/s03-append',receipt)['error']['code'];assert result['changed_identity_content']=='CONFLICT'
    # A reference supplied by the authenticated caller is still structurally checked.
    d=chosen['atom.storage'];invalid={**request,'interface_ref':dict(id=d.interface,version=d.version),'profile':next(iter(d.profiles)),
        'selection':selection_token(d),'operation':'getMany','body':{'refs':[{'digest':'0'*64}]}}
    result['malformed_reference']=send('atom.storage','/s03-read',invalid)['error']['code'];assert result['malformed_reference']=='INVALID_ARGUMENT'
    return result


def search_authority():
    from fusion.memory_services import SearchPorts,SOURCE_PROFILE
    cfg=json.loads(Path('/run/fusion/owner.json').read_text());ports=SearchPorts('/run/fusion/owner.json')
    atoms=ports.atoms();request=dict(request_id=str(uuid.uuid4()),profile=SOURCE_PROFILE,scope=ports.scope,
        selection=selection_token(ports.read['atom.storage']),operation='head',body={})
    result={'head':atoms.head(ports.scope)}
    for name,change in [('scope',{'scope':'private'}),('descriptor',{'selection':'0'*64}),('principal-string',{'principal':'A'}),('write',{'operation':'create'})]:
        try:atoms.connection.invoke({**request,**change})
        except ContractError as exc:result[name]=exc.code
        else:raise AssertionError(name+' accepted')
    d=ports.read['search'];initial=json.loads(Path('/state/initial-view.json').read_text())
    req=dict(request_id=str(uuid.uuid4()),scope=ports.scope,interface_ref=dict(id=d.interface,version=d.version),operation='authorize-ready',
        profile=v.PROFILE,selection=selection_token(d),body=dict(query=cfg['memory_read']['queries'][0],snapshot=initial))
    try:ports.invoke('/s03-read',cfg['principals']['indexer']['credential'],req)
    except ContractError as exc:result['other_authenticated_principal']=exc.code
    else:raise AssertionError('indexer gained caller authority')
    assert result['other_authenticated_principal']=='UNAUTHORIZED'
    return result


def rebuild():
    import shutil
    from fusion.memory_services import SearchPorts
    from fusion.append_composition import AppendService
    from fusion.vector_composition import ReadService
    cfg=json.loads(Path('/run/fusion/owner.json').read_text());ports=SearchPorts('/run/fusion/owner.json');token=cfg['principals']['A']['credential']
    root=Path(cfg['memory_read']['root'])/'search';publication=json.loads((root/'published.json').read_text())
    old=publication['current']
    shutil.rmtree(root/old['generation']/'index')  # Only disposable derived bytes.
    reader=ReadService('/run/fusion/owner.json',token,atoms=ports.atoms())
    try:reader.search().ready(ports.scope,old)
    except ContractError as exc:refused=exc.code
    else:raise AssertionError('missing generation reported ready')
    assert refused=='NOT_AVAILABLE'
    owner=AppendService('/run/fusion/owner.json',token,atoms=ports.atoms()).search()
    deadline=time.time_ns()//1_000_000+30000
    rebuilt=owner.build_named(ports.scope,old['head'],'operator-derived-rebuild',deadline)
    assert rebuilt['logical']==old['logical'] and rebuilt['generation']!=old['generation']
    assert reader.search().ready(ports.scope,rebuilt)=={'ready':True}
    assert owner.build_named(ports.scope,old['head'],'operator-derived-rebuild',deadline)==rebuilt
    return dict(old=old,old_generation_refusal=refused,rebuilt=rebuilt,source_access='authenticated RemoteSource ports',deadline_ms=deadline,
                scope='operator maintenance only; retained application views not rebound')
