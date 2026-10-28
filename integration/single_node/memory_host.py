"""Composition startup/observation only; native lifecycle still owns all commands."""
import json
from pathlib import Path
import sqlite3
import time
import uuid

from fusion import vector_contracts as v
from fusion.contracts import canonical,digest,require
from fusion.memory_services import SearchPorts,StoragePorts,SourceConnection
from fusion.policy import Policy
from fusion.registry import selection_token
from fusion.vector_composition import ReadService
from .configure import write


def initial_request(scope,selection):
    return dict(request_id=str(uuid.uuid4()),profile='neoclaw-memory-initial-view/1',scope=scope,selection=selection,operation='initial',body={})


class SearchHost(SearchPorts):
    def initialize(self,state):
        cfg=Policy(self.path).current();credential=cfg['principals']['indexer']['credential']
        service=ReadService(self.path,credential,self.hook,atoms=self.atoms())
        path=state/'initial-view.json'
        if path.exists():
            self.initial=json.loads(path.read_text());service.search().ready(self.scope,self.initial);return
        intent_path=state/'initial-intent.json'
        if intent_path.exists():intent=json.loads(intent_path.read_text())
        else:
            head=service.atoms.head(self.scope);require(head['sequence']==0,'CONFLICT')
            intent=dict(head=head,deadline_ms=time.time_ns()//1_000_000+30000);write(intent_path,intent)
        from fusion.append_composition import AppendService
        builder=AppendService(self.path,cfg['principals']['A']['credential'],atoms=self.atoms())
        self.initial=builder.search().build_named(self.scope,intent['head'],'initial-empty',intent['deadline_ms'])
        write(path,self.initial)
    def invoke(self,path,credential,request):
        if path!='/memory-initial':return super().invoke(path,credential,request)
        v.fields(request,'request_id profile scope selection operation body');v.a.identity(request['request_id'])
        require(request['profile']=='neoclaw-memory-initial-view/1' and request['operation']=='initial' and request['body']=={},'UNSUPPORTED_PROFILE')
        require(request['selection']==selection_token(self.read['search']) and request['scope']==self.scope,'UNSUPPORTED_PROFILE')
        service=ReadService(self.path,credential,self.hook,atoms=self.atoms())
        require(service.access['search'].principal=='A','UNAUTHORIZED');service.access['search'].authorize(self.scope,'query')
        service.search().ready(self.scope,self.initial)
        return dict(request_id=request['request_id'],request_digest=digest(canonical(request)),selection=request['selection'],principal='A',value=self.initial)


def prepare_agent(settings,state,run):
    import http.client
    from fusion.neoclaw_transport import Network,json_loads
    from fusion.vector_transport import checked
    from fusion.vector_composition import select
    from fusion.registry import descriptor_read
    read=json.loads((run/'memory-read-template.json').read_text());selected=select([descriptor_read(d) for d in read['catalogue']],v.EMBEDDING,True)
    port=Network(read['endpoints']['search'],read['service_credentials']['search'],selected,service_dns=True)
    request=initial_request(read['scope'],selection_token(selected['search']))
    conn=http.client.HTTPSConnection(port.endpoint['host'],port.endpoint['port'],timeout=3,context=port.context)
    try:
        conn.request('POST','/memory-initial',canonical(request),{'Authorization':'Bearer '+port.credential,'Content-Type':'application/json'})
        response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE');raw=response.read(98305);require(len(raw)<=98304,'NOT_AVAILABLE')
        snapshot=v.snapshot(checked(request,json_loads(raw),'A'),read['scope'])
    finally:conn.close()
    require(snapshot['head']['sequence']==0,'CONFLICT')
    initial=state/'initial-view.json'
    if initial.exists():require(json.loads(initial.read_text())==snapshot,'CONFLICT')
    else:write(initial,snapshot)
    manifest=dict(records=[],promotion_time=2000000000.-86400);seal=digest(canonical(manifest))
    write(state/'metadata.json',manifest)
    read.update(snapshot=snapshot,metadata_seal=seal);write(run/'memory-read.json',read)
    runtime=Path('/opt/memory-runtime.json');sdk=json.loads(runtime.read_text())
    promotions=state/'promotions.sqlite'
    # Empty legitimate local metadata, initialized with the pinned helper schema.
    import importlib.util
    source=Path('/opt/native/sources/mettaclaw/src/helper.py')
    spec=importlib.util.spec_from_file_location('memory_metadata_helper',source);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.promotion_open_map(str(promotions));helper.promotion_commit();helper.promotion_close_map()
    write(run/'memory-native.json',dict(site=str(Path(sdk['sdk'])/'lib/python3.12/site-packages'),
        helper=sdk['helper'],runtime=str(runtime),runtime_sha256=digest(runtime.read_bytes()),embedding_boundary='port',
        metadata_manifest=str(state/'metadata.json'),metadata_seal=seal,promotions=str(promotions),
        clock_fixture=settings['memory'].get('clock_fixture',2000000000.),
        creation_clock_fixture=settings['memory'].get('creation_clock_fixture')))
    from fusion.adapters.neoclaw_metadata import collection
    collection(state/'metadata-views',manifest,prepare=True,deadline=time.time_ns()//1_000_000+30000)
