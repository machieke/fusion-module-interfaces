"""Fixed-role synthetic task/result envelopes on the existing Messaging owner.

This port adds no task executor, scheduler or storage backend. Native callers
create the immutable records through AtomStorage and consume through their own
session inbox. Recipients validate referenced results, not sender assertions of
truth. The route topology and source scope are operator selected.
"""
import json,time,uuid
from pathlib import Path
from dataclasses import asdict
from .contracts import canonical,digest,require,validate_ref
from .ports import Mutation
from .policy import Policy
from .messaging import MessageOwner,MessagingSession
from .preview_native_history import read_body
from .preview_atoms import client as atoms_client
from .registry import Descriptor,selection_token,descriptor_read
from . import preview_vector_contracts as v

PROFILE='native-retrieval-task/1'
ROUTE='/preview/tasks'
OPS={'authorize':0,'send':5,'published':5,'poll':0,'ack':2}


def descriptor():
    return Descriptor('preview-durable-messaging','agent.messaging','1.0.0','1.0.0',frozenset({PROFILE}),
        frozenset(OPS),frozenset({'scoped','idempotent','process-restart'}),65536,privacy='generated-shareable')


def record(value,scope):
    require(type(value) is dict and value.get('profile')==PROFILE,'UNSUPPORTED_PROFILE')
    require(value.get('scope')==scope and scope.startswith('synthetic-'),'UNAUTHORIZED')
    common={'profile','kind','scope','id','sender','recipient','session','deadline','parent','limits'}
    require(value.get('kind') in ('task','result'))
    require(set(value)==common|({'query','minimum'} if value['kind']=='task' else {'task','view','projection','payloads','status'}))
    for key in ('id','session'):
        try:require(str(uuid.UUID(value[key]))==value[key])
        except (ValueError,TypeError,AttributeError):require(False)
    require(value['sender'] in ('A','B') and value['recipient'] in ('A','B') and value['sender']!=value['recipient'],'UNAUTHORIZED')
    require(type(value['parent']) is str and 1<=len(value['parent'])<=128)
    require(type(value['deadline']) is int and value['deadline']>0)
    require(type(value['limits']) is dict and type(value['limits'].get('queries')) is int and type(value['limits'].get('relay_calls')) is int and type(value['limits'].get('recursive_delegation')) is bool,'UNSUPPORTED_PROFILE')
    require(value['limits']=={'queries':1,'relay_calls':24,'recursive_delegation':False},'UNSUPPORTED_PROFILE')
    if value['kind']=='task':
        require(type(value['query']) is str and 0<len(value['query'].encode())<=512 and '\n' not in value['query'] and '\x00' not in value['query'])
        import unicodedata
        require(not any(unicodedata.category(x).startswith('C') for x in value['query']))
        require(not any(x in value['query'] for x in ('\"', "'", '_quote_', '_newline_', '_apostrophe_', ':-:-:-:')))
        v.snapshot(value['minimum'],scope)
    else:
        validate_ref(value['task'],scope);v.snapshot(value['view'],scope)
        require(value['status']=='captured-native-query','UNSUPPORTED_PROFILE')
        require(type(value['projection']) is str and 0<len(value['projection'].encode())<=32768)
        require(type(value['payloads']) is list and 0<=len(value['payloads'])<=16)
        for ref in value['payloads']:validate_ref(ref,scope)
    require(len(canonical(value))<=49152,'OVERLOADED')
    return value


def correlated(result,task,task_ref):
    require(result['kind']=='result' and task['kind']=='task','NOT_AVAILABLE')
    require(result['task']==task_ref and result['id']==task['id'] and result['parent']==task['parent'] and
        result['sender']==task['recipient'] and result['recipient']==task['sender'] and result['deadline']==task['deadline'],'UNAUTHORIZED')
    for name in ('head','lifecycle'):
        a,b=result['view'][name],task['minimum'][name]
        require(a['source']==b['source'] and a['sequence']>=b['sequence'],'NOT_AVAILABLE')
    require(result['view']['corpus']==task['minimum']['corpus'],'NOT_AVAILABLE')


class Ports:
    def __init__(self,path,hook=lambda _:None,atoms_for=None):self.path,self.hook,self.atoms_for=Path(path),hook,atoms_for
    def invoke(self,credential,q):
        require(type(q) is dict and set(q)=={'id','profile','selection','scope','operation','args'})
        require(type(q['id']) is str and 0<len(q['id'])<=128)
        require(q['profile']==PROFILE and q['selection']==selection_token(descriptor()),'UNSUPPORTED_PROFILE')
        op,args=q['operation'],q['args'];require(type(op) is str and op in OPS,'UNSUPPORTED_OPERATION')
        require(type(args) is list and len(args)==OPS[op])
        policy=Policy(self.path);principal=policy.authenticate(credential);cfg=policy.current()
        require(cfg['profile']==PROFILE and q['scope']==cfg['scope'],'UNAUTHORIZED')
        def check():
            require(policy.authenticate(credential)==principal,'UNAUTHORIZED');policy.check(principal,q['scope'],'tasks.'+op)
        check();scope=q['scope']
        atoms=self.atoms_for(principal) if self.atoms_for else atoms_client(cfg['atom_clients'][principal])
        owner=MessageOwner(cfg['messages_database'],policy,cfg['capacity'])
        mailbox=MessagingSession(owner,policy,principal,atoms,q['id']);route=cfg['inboxes'][principal]
        if op=='authorize':value={'authorized':True}
        elif op=='poll':value=mailbox.poll(scope,route)
        elif op=='ack':
            identity,delivery=args;require(type(identity) is str and 1<=len(identity)<=128)
            value=mailbox.ack(Mutation(scope,identity),route,delivery)
        else:
            identity,ref,recipient,deadline,correlation=args
            require(type(identity) is str and 1<=len(identity)<=128 and recipient in cfg['inboxes'],'UNAUTHORIZED')
            body=record(read_body(atoms,ref)['body'],scope)
            require(identity==body['kind']+'/'+body['id'],'CONFLICT')
            if 'session_authority' in cfg:
                authority=cfg['session_authority']
                require(type(authority) is dict and set(authority)=={'profile','principals'} and authority['profile']=='allocated-native-task-routing/1','UNSUPPORTED_PROFILE')
                require(principal in authority['principals'],'UNAUTHORIZED')
                from .preview_transport import invoke
                query=dict(id=q['id'],profile='omega-native-sessions/3',operation='binding',body={'session':body['session']})
                reply=invoke(authority['principals'][principal],'/preview/session',query,deadline if op=='send' else None)
                require(type(reply) is dict and set(reply)=={'id','profile','request_digest','actor','principal','value'},'NOT_AVAILABLE')
                require((reply['id'],reply['profile'],reply['request_digest'],reply['actor'],reply['principal'])==
                    (query['id'],query['profile'],digest(canonical(query)),'task-router',principal),'UNAUTHORIZED')
                bound=reply['value'];require(type(bound) is dict and set(bound)=={'session','principal','scope','state','expires_ms'},'NOT_AVAILABLE')
                require((bound['session'],bound['principal'],bound['scope'])==(body['session'],principal,scope),'UNAUTHORIZED')
                require(type(bound['expires_ms']) is int and bound['expires_ms']>0 and bound['state'] in ('active','paused','closed','archived'),'NOT_AVAILABLE')
                if op=='send':require(bound['state']=='active' and time.time_ns()//1_000_000<bound['expires_ms'],'NOT_AVAILABLE')
            else:require(body['session'] in cfg['sessions'][principal],'UNAUTHORIZED')
            require((body['sender'],body['recipient'],body['deadline'],body['id'])==(principal,recipient,deadline,correlation),'UNAUTHORIZED')
            if op=='send':require(time.time_ns()//1_000_000<deadline,'DEADLINE_EXCEEDED')
            if body['kind']=='result':
                task=record(read_body(atoms,body['task'])['body'],scope);correlated(body,task,body['task'])
                key=canonical([task['sender'],scope,'agent.messaging','send','task/'+task['id']]).decode()
                from contextlib import closing
                with closing(owner._connect()) as db:
                    prior=db.execute('SELECT body FROM messages WHERE id=? AND scope=? AND route=?',
                        (str(uuid.uuid5(uuid.NAMESPACE_URL,key)),scope,cfg['inboxes'][principal])).fetchone()
                    require(prior is not None and json.loads(prior[0])['ref']==body['task'],'UNAUTHORIZED')
                for payload in body['payloads']:atoms.get(payload)
            value=None
            if op=='published':
                key=canonical([principal,scope,'agent.messaging','send',identity]).decode()
                from contextlib import closing
                with closing(owner._connect()) as db:
                    prior=db.execute('SELECT body FROM messages WHERE id=? AND scope=? AND route=?',
                        (str(uuid.uuid5(uuid.NAMESPACE_URL,key)),scope,cfg['inboxes'][recipient])).fetchone()
                    if prior is not None:require(json.loads(prior[0])['ref']==ref,'CONFLICT')
            if op=='send' or prior is not None:
                value=mailbox.send(Mutation(scope,identity,digest(canonical(body))),ref,cfg['inboxes'][recipient],body['id'],route)
                self.hook('after_task_mailbox_accept')
        check()
        return dict(id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],principal=principal,value=value)


class Client:
    def __init__(self,path):
        self.path=Path(path);self.cfg,self.frozen=self.current()
    def current(self):
        cfg=json.loads(self.path.read_text());require(cfg['profile']==PROFILE and cfg['fallback'] is False,'UNSUPPORTED_PROFILE')
        require(descriptor_read(cfg['descriptor'])==descriptor(),'UNSUPPORTED_PROFILE')
        frozen={k:v for k,v in cfg.items() if k not in ('credential','recipients')}
        frozen['recipients']={k:{**{n:x for n,x in v.items() if n!='credential'},'ca_sha256':digest(Path(v['endpoint']['ca_file']).read_bytes())} for k,v in cfg.get('recipients',{}).items()}
        return cfg,{**frozen,'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
    def call(self,op,*args,deadline=None):
        cfg,frozen=self.current();require(frozen==self.frozen,'CONFLICT')
        require(op in OPS and len(args)==OPS[op],'UNSUPPORTED_OPERATION')
        q=dict(id=str(uuid.uuid4()),profile=PROFILE,selection=selection_token(descriptor()),scope=cfg['scope'],operation=op,args=list(args))
        from .preview_transport import invoke
        reply=invoke(cfg,ROUTE,q,deadline)
        require(type(reply) is dict and set(reply)=={'id','request_digest','selection','principal','value'},'NOT_AVAILABLE')
        require((reply['id'],reply['request_digest'],reply['selection'],reply['principal'])==
            (q['id'],digest(canonical(q)),q['selection'],cfg['principal']),'NOT_AVAILABLE')
        value=reply['value']
        if op=='published' and value is None:return None
        if op in ('send','published','ack'):
            from .responses import completion_acceptance,evidence
            if op in ('send','published'):
                key=canonical([cfg['principal'],cfg['scope'],'agent.messaging','send',args[0]]).decode()
                delivery=str(uuid.uuid5(uuid.NAMESPACE_URL,key))
                completion_acceptance(value,cfg['scope'],'task-'+args[2],delivery,args[4])
            else:
                require(type(value) is dict and set(value)=={'delivery_id','delivery','persistence','evidence','scope_ref','route'},'NOT_AVAILABLE')
                require(value['delivery_id']==args[1] and value['delivery']=='acknowledged' and value['persistence']=='process-restart' and
                    value['scope_ref']==cfg['scope'] and value['route']=='task-'+cfg['principal'],'NOT_AVAILABLE')
                evidence(value['evidence'])
        elif op=='poll' and value is not None:
            require(type(value) is dict and set(value)=={'scope_ref','route','delivery_id','body','order','delivery'},'NOT_AVAILABLE')
            require(value['scope_ref']==cfg['scope'] and value['route']=='task-'+cfg['principal'],'UNAUTHORIZED')
            require(type(value['order']) is int and 0<value['order']<=10000 and value['delivery']=='observed-unacknowledged','NOT_AVAILABLE')
            from .channel_contracts import identifier
            require(type(value['body']) is dict and set(value['body'])=={'ref','correlation_id','reply_route','causation_id'},'NOT_AVAILABLE')
            identifier(value['delivery_id']);identifier(value['body']['correlation_id'])
            validate_ref(value['body']['ref'],cfg['scope'])
            require(value['body']['reply_route'] in ('task-A','task-B') and value['body']['reply_route']!=value['route'],'UNAUTHORIZED')
        return value
