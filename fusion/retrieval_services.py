"""Explicit cross-pod disclosure: trusted issuer receipts, not proof of retrieval.

The caller alone validates capture/consent. The provider checks current issuer
and execution authority, exact binding and syntax; no shared file is consulted.
"""
import http.client
import json
from pathlib import Path
import time
import uuid
from . import model_contracts as m, neoclaw_retrieval_disclosure as r
from .contracts import canonical,digest,require,ContractError
from .neoclaw_transport import Network,json_loads
from .registry import descriptor_read,selection_token
from .policy import Policy

COMPOSITION='neoclaw-model-channel-services/1'
POLICY='synthetic-retrieval-service-disclosure/1'
RECEIPT='trusted-native-retrieval-receipt/1'
COMMON=('policy','scaffold','memories','users','query','recipient')


def configuration(cfg):
    p=cfg['disclosure']
    require(set(p)==set(COMMON)|{'consent_sha256','view_sha256','receipt_root'},'UNSUPPORTED_PROFILE')
    require(p['policy']==POLICY and cfg['placement']=='service-network' and cfg.get('service_composition')==COMPOSITION,'UNSUPPORTED_PROFILE')
    require(p['memories']==['()'] and len(p['users'])==2,'UNAUTHORIZED');r.safe_data(p['query'])
    for key in ('consent_sha256','view_sha256'):m.hash_value(p[key])
    require(type(cfg['commands']) is list and 3<=len(cfg['commands'])<=r.MAX_BODIES+1,'UNSUPPORTED_PROFILE')
    require(cfg['commands'][0]==['query',p['query']],'UNSUPPORTED_OPERATION')
    bodies=cfg['commands'][1:]
    require(all(type(x) is list and len(x)==2 and x[0]=='send' for x in bodies),'UNSUPPORTED_OPERATION')
    require(len(set(x[1] for x in bodies))==len(bodies),'INVALID_ARGUMENT')
    for _,body in bodies:r.safe_data(body);require(len(body.encode())<=400)


def binding(app):
    require(app.config['composition']==r.SERVICE_APPLICATION,'UNSUPPORTED_PROFILE')
    value=app.config['retrieval'];require(set(value)=={'initial_view','consent'},'UNSUPPORTED_PROFILE')
    view=value['initial_view'];consent=value['consent']
    require(set(view)=={'snapshot','metadata','metadata_seal'},'UNSUPPORTED_PROFILE')
    require(view['snapshot']==app.binding['memory']['snapshot'] and view['metadata_seal']==app.binding['memory']['metadata_seal']==digest(canonical(view['metadata'])),'CONFLICT')
    require(set(consent)=={'recipient','records'} and 2<=len(consent['records'])<=8,'UNAUTHORIZED')
    for record in consent['records']:
        require(set(record)=={'uuid','time','content','metadata'},'UNAUTHORIZED')
        m.uid(record['uuid']);r.safe_data(record['time']);r.safe_data(record['content'])
        require(record['metadata'] in view['metadata']['records'] and record['metadata']['uuid']==record['uuid'],'UNAUTHORIZED')
        require(record['metadata']['stv']==[1.,.5] and record['metadata']['links']==[record['time']] and record['metadata']['promotion']==0.,'UNAUTHORIZED')
    require(len({x['uuid'] for x in consent['records']})==len(consent['records'])==len(view['metadata']['records']),'UNAUTHORIZED')
    return value


def metadata(cfg,intent,operation):
    p=cfg['disclosure']
    return dict(profile=POLICY,issuer=cfg['principal'],recipient=p['recipient'],principal=intent['principal'],scope=intent['scope'],
        session=intent['session'],id=intent['id'],source_id=intent['source_id'],slot=intent['slot'],model_profile=intent['profile'],selection=intent['selection'],
        consent_sha256=p['consent_sha256'],view_sha256=p['view_sha256'],native_prompt_sha256=digest(intent['native_prompt'].encode()),
        messages_sha256=digest(canonical(intent['messages'])),deadline_ms=intent['deadline_ms'],operation=operation)


def rpc(cfg,path,request,timeout=2):
    net=Network(cfg['endpoint'],cfg['credential'],{},service_dns=True)
    conn=http.client.HTTPSConnection(net.endpoint['host'],net.endpoint['port'],timeout=timeout,context=net.context)
    try:
        data=canonical(request);require(len(data)<=m.MAX_WIRE)
        conn.request('POST',path,data,{'Content-Type':'application/json','Authorization':'Bearer '+net.credential})
        response=conn.getresponse();require(response.status==200,'NOT_AVAILABLE')
        raw=response.read(m.MAX_WIRE+1);require(len(raw)<=m.MAX_WIRE,'NOT_AVAILABLE');value=json_loads(raw)
        if type(value) is dict and set(value)=={'error'}:
            from .responses import error
            error(value['error']);raise ContractError(value['error']['code'])
        return value
    except (OSError,ValueError,http.client.HTTPException):raise ContractError('NOT_AVAILABLE') from None
    finally:conn.close()


def preflight(cfg,intent,operation='disclose'):
    request=metadata(cfg,intent,operation);result=rpc(cfg,'/model-disclosure',request)
    require(result==dict(authorized=True,principal=cfg['principal'],request_sha256=digest(canonical(request))),'UNAUTHORIZED')


def validate_receipt(raw,policy,intent,receipt):
    require(intent is not None and raw==intent['native_prompt'],'UNAUTHORIZED');m.intent(intent)
    require(type(receipt) is dict and set(receipt)=={'profile','issuer','recipient','consent_sha256','view_sha256','intent_sha256','native_prompt_sha256','messages_sha256','principal','scope','session','occurrence','source_id','slot','selection','model_profile','deadline_ms','query'},'UNAUTHORIZED')
    require(receipt['profile']==RECEIPT and receipt['issuer']==receipt['principal']==intent['principal'],'UNAUTHORIZED')
    for key,field in [('scope','scope'),('session','session'),('occurrence','id'),('source_id','source_id'),('slot','slot'),('selection','selection'),('model_profile','profile'),('deadline_ms','deadline_ms')]:require(receipt[key]==intent[field],'UNAUTHORIZED')
    require(receipt['intent_sha256']==digest(canonical(intent)) and receipt['native_prompt_sha256']==digest(raw.encode()) and receipt['messages_sha256']==digest(canonical(intent['messages'])),'UNAUTHORIZED')
    require(receipt['recipient']==policy['recipient'],'UNAUTHORIZED')
    for key in ('consent_sha256','view_sha256'):
        m.hash_value(receipt[key])
        if key in policy:require(receipt[key]==policy[key],'UNAUTHORIZED')
    parts=r.structural(raw,policy);require(intent['slot'] in (1,2) and parts['user']==policy['users'][intent['slot']-1],'UNAUTHORIZED')
    q=receipt['query']
    if intent['slot']==1:require(q is None and parts['feedback']=='','UNAUTHORIZED')
    else:
        require(type(q) is dict and set(q)=={'occurrence','view','projection','result','capture_sha256'},'UNAUTHORIZED')
        require(q['occurrence']==str(uuid.uuid5(uuid.UUID(intent['session']),'1/0')) and q['view']==receipt['view_sha256'],'UNAUTHORIZED')
        require(q['projection']==parts['feedback']==r.projection(policy['query'],q['result']) and parts['feedback'],'UNAUTHORIZED');m.hash_value(q['capture_sha256'])
    return parts


def validate_local(raw,policy,intent):
    path=r.receipt_path(policy,intent);require(path.is_file() and path.stat().st_size<=16384,'UNAUTHORIZED')
    return validate_receipt(raw,policy,intent,json.loads(path.read_bytes()))


def issue(app,intent):
    cfg,_=app.model.current();p=cfg['disclosure'];value=binding(app)
    require(value==app.binding['retrieval'],'CONFLICT');consent=value['consent'];view=value['initial_view']
    require(p['consent_sha256']==digest(canonical(consent)) and p['view_sha256']==digest(canonical(view)) and p['recipient']==consent['recipient'],'UNAUTHORIZED')
    parts=r.structural(intent['native_prompt'],p);require(parts['feedback']==app.restore(),'CONFLICT')
    q=None
    if intent['slot']==1:
        require(parts['feedback']=='','UNAUTHORIZED');r.initial_history(app,p['query'])
    else:
        require(intent['slot']==2,'UNAUTHORIZED');turn=app.db.execute('SELECT * FROM app_turns WHERE id=1').fetchone()
        require(turn and json.loads(turn['commands'])==[['query',p['query']]] and turn['projection']==parts['feedback'],'UNAUTHORIZED')
        rows=app.db.execute('SELECT * FROM app_occurrences WHERE turn=1 ORDER BY position').fetchall();require(len(rows)==1 and rows[0]['done']==1 and rows[0]['result'] is not None,'NOT_AVAILABLE')
        row=rows[0];require(app.write.view_for(row)==view,'CONFLICT');app.memory.authorize(row)
        capture=app.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone();require(capture and capture['payloads'] and capture['candidates'],'NOT_AVAILABLE')
        permitted={x['uuid']:x for x in consent['records']}
        for uid,stamp,text,distance in json.loads(capture['payloads']):require(uid in permitted and [stamp,text]==[permitted[uid]['time'],permitted[uid]['content']],'UNAUTHORIZED')
        r.presentation(row['result'],json.loads(capture['payloads']),permitted)
        require(parts['feedback']==r.projection(p['query'],row['result']),'CONFLICT')
        q=dict(occurrence=row['id'],view=digest(canonical(view)),projection=parts['feedback'],result=row['result'],capture_sha256=digest(canonical({k:capture[k] for k in ('request','candidates','payloads','enrichment')})))
    preflight(cfg,intent) # Metadata only; no prompt/corpus bytes before provider consent.
    receipt=dict(profile=RECEIPT,issuer=cfg['principal'],recipient=p['recipient'],consent_sha256=p['consent_sha256'],view_sha256=p['view_sha256'],intent_sha256=digest(canonical(intent)),native_prompt_sha256=digest(intent['native_prompt'].encode()),messages_sha256=digest(canonical(intent['messages'])),principal=intent['principal'],scope=intent['scope'],session=intent['session'],occurrence=intent['id'],source_id=intent['source_id'],slot=intent['slot'],selection=intent['selection'],model_profile=intent['profile'],deadline_ms=intent['deadline_ms'],query=q)
    validate_receipt(intent['native_prompt'],p,intent,receipt);path=r.receipt_path(p,intent);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    if path.exists():require(path.read_bytes()==canonical(receipt),'CONFLICT')
    else:
        import os
        pending=path.with_suffix('.pending')
        with open(pending,'wb') as stream:
            os.chmod(pending,0o600);stream.write(canonical(receipt));stream.flush();os.fsync(stream.fileno())
        os.replace(pending,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)


def invoke(cfg,request):
    receipt=json.loads(r.receipt_path(cfg['disclosure'],request['intent']).read_bytes())
    timeout=2 if request['operation']!='complete' else max(.05,min(300,(request['intent']['deadline_ms']-time.time_ns()//1_000_000)/1000))
    return rpc(cfg,'/s07-model-services',dict(profile=POLICY,request=request,receipt=receipt),timeout)


class ModelPorts:
    def __init__(self,path,backend,hook=lambda _:None):self.path,self.backend,self.hook=path,backend,hook
    def authority(self,credential,meta):
        require(set(meta)=={'profile','issuer','recipient','principal','scope','session','id','source_id','slot','model_profile','selection','consent_sha256','view_sha256','native_prompt_sha256','messages_sha256','deadline_ms','operation'},'INVALID_ARGUMENT')
        policy=Policy(self.path);cfg=policy.current()['model_completion'];p=cfg['disclosure'];principal=policy.authenticate(credential)
        require(meta['profile']==p['policy']==POLICY and meta['principal']==meta['issuer']==principal,'UNAUTHORIZED')
        require(meta['recipient']==p['recipient'] and meta['session'] in cfg['sessions'] and meta['scope']==cfg['scope'],'UNAUTHORIZED')
        require(meta['operation'] in ('disclose','complete','observe','authorize'),'UNSUPPORTED_OPERATION')
        require(meta['selection']==selection_token(m.select([descriptor_read(d) for d in cfg['catalogue']],meta['model_profile'])),'UNSUPPORTED_PROFILE')
        for key in ('id','session','source_id'):m.uid(meta[key])
        for key in ('consent_sha256','view_sha256','native_prompt_sha256','messages_sha256'):m.hash_value(meta[key])
        m.integer(meta['slot'],1,2);m.integer(meta['deadline_ms'],1)
        require(principal in cfg['disclosure_issuers'],'UNAUTHORIZED')
        for op in ('issue','disclose',meta['operation']):policy.check(principal,meta['scope'],'model.'+op)
        return cfg
    def invoke(self,path,credential,request):
        if path=='/model-disclosure':
            self.authority(credential,request)
            return dict(authorized=True,principal=request['principal'],request_sha256=digest(canonical(request)))
        require(path=='/s07-model-services','UNSUPPORTED_OPERATION')
        require(set(request)=={'profile','request','receipt'} and request['profile']==POLICY,'UNSUPPORTED_PROFILE');m.request(request['request'])
        accepted=request['request']['intent'];receipt=request['receipt'];policy=Policy(self.path).current()['model_completion']['disclosure']
        cfg=dict(principal=accepted['principal'],disclosure={**policy,**{k:receipt[k] for k in ('consent_sha256','view_sha256')}})
        meta=metadata(cfg,accepted,request['request']['operation']);self.authority(credential,meta)
        def disclose(intent,p):
            self.authority(credential,meta);return validate_receipt(intent['native_prompt'],p,intent,receipt)
        from .model_service import ModelService
        service=ModelService(self.path,self.backend,self.hook,disclosure=disclose)
        try:return service.invoke(credential,request['request'])
        finally:service.close()
