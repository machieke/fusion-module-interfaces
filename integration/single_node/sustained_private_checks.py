"""Adversarial bounded scope probes from B's own pod/credentials.

Only an operator supplies fresh synthetic test references. No foreign journal,
secret, unrestricted execution or successful private data is exported.
"""
import copy,json,sys,uuid,time
from pathlib import Path
from fusion.contracts import ContractError,canonical,require
from fusion.preview_transport import invoke
from fusion import cognitive_services as cs
from fusion.registry import selection_token
from .sustained_runtime import materialize


def check(request):
    require(type(request) is dict and set(request)=={'session','private_scope','private_ref','private_snapshot','private_episode','private_context','canary'})
    require(request['private_scope'].startswith('synthetic-') and type(request['canary']) is str,'UNAUTHORIZED')
    owner=Path('/run/fusion/owner.json');cfg=json.loads(owner.read_bytes());require(cfg['native_sessions']['principal']=='B','UNAUTHORIZED')
    app=json.loads(materialize(owner,Path('/state'),Path('/run/fusion'),request['session']).read_bytes())
    atom=json.loads(Path(app['history_atoms_config']).read_bytes());scope=request['private_scope'];ref=request['private_ref']
    results=[]
    def denied(name,call):
        try:call()
        except ContractError as error:
            require(error.code=='UNAUTHORIZED','CONFLICT');results.append(dict(name=name,code=error.code))
        else:require(False,'CONFLICT')
    from fusion.preview_atoms import client
    selected=dict(atom,scope=scope)
    for name,args in [('get',(ref,)),('getMany',((ref,),)),('head',(scope,)),('capacity',(scope,))]:
        denied('atom.'+name,lambda name=name,args=args:getattr(client(selected),name)(*args))
    denied('atom.feed',lambda:client(selected).readCommits(scope,0,request['private_snapshot']['head'],1))
    from fusion.preview_memory_services import Client,descriptor,COMPOSITION
    for name,op,args in [('memory.lifecycle','head',()),('search','current',(request['private_snapshot']['lifecycle'],)),('search','ready',(request['private_snapshot'],))]:
        raw=json.loads(Path(app['active_memory_configs'][name]).read_bytes());raw['scope']=scope
        # Construct the same closed wire as the existing client, changing only
        # the adversarial scope; all descriptor/profile selection stays exact.
        actual=Client(app['active_memory_configs'][name],name)
        q=dict(id=str(uuid.uuid4()),composition=COMPOSITION,scope=scope,selection=selection_token(descriptor(name)),interface=name,operation=op,args=list(args))
        denied(name+'.'+op,lambda raw=raw,q=q:invoke(raw,'/preview/memory',q))
    cog,_=cs.client_configuration(app['evidence_config']);cog=copy.deepcopy(cog);cog['scope']=scope
    denied('episode.read',lambda:cs.Remote(cog,'episodic.memory').readEpisode(request['private_episode'],1,1))
    denied('belief.read',lambda:cs.Remote(cog,'belief.revision').readBelief('synthetic-private-claim',request['private_context'],None))
    from fusion.preview_ports import descriptor as facet_descriptor,COMPOSITION as FACETS
    raw=json.loads(Path(app['facet_configs']['relations']).read_bytes())
    q=dict(id=str(uuid.uuid4()),composition=FACETS,scope=scope,interface='relations',selection=selection_token(facet_descriptor('relations')),operation='outgoing',args=[ref,1,None,None])
    denied('relations.outgoing',lambda:invoke(raw,'/preview/facets',q))
    from fusion.sustained_observation import PROFILE,ROUTE
    descriptor=cs.catalogue(cog)['attention'];q=dict(profile=PROFILE,id=str(uuid.uuid4()),scope=scope,selection=selection_token(descriptor),interface='attention',context=request['private_context'])
    denied('attention.current',lambda:invoke(cog['ports']['attention'],ROUTE,q))
    # Enumerate the shared authoritative feed through its declared pages and
    # verify the canary never appears in those underlying bytes, not just C1.
    audit_deadline=time.time_ns()//1000000+180000
    shared=client(atom,audit_deadline);head=shared.head(atom['scope']);cursor=0;count=0
    while cursor<head['sequence']:
        page=shared.readCommits(atom['scope'],cursor,head,8)
        payloads=shared.getMany(tuple(row['ref'] for row in page['records']))
        require(len(payloads)==len(page['records']),'NOT_AVAILABLE')
        for payload in payloads:
            require(request['canary'].encode() not in payload.bytes,'CONFLICT');count+=1
        cursor=page['next_after'] if not page['complete'] else head['sequence']
    return dict(status='PASS',shared_scope=atom['scope'],audit_deadline_ms=audit_deadline,observed_source_records=head['sequence'],denials=results,shared_payloads_checked=count,private_data_returned=False,additional_live_generations=0)

if __name__=='__main__':print(json.dumps(check(json.load(sys.stdin))))
