"""Bounded mailbox-to-session acceptance by the native application's owner.

A hint processes at most one delivery. Startup observes once. There is no
periodic task scheduler, deadline renewal, command execution or model here.
Lost hints leave durable mailbox work available to explicit drain or restart.
"""
import json,time,sqlite3,uuid
from pathlib import Path
from fusion.contracts import canonical,require,ContractError
from fusion.preview_tasks import Client,PROFILE,record,correlated
from fusion.preview_atoms import client as atoms_client
from fusion.preview_native_history import read_body
from fusion.preview_sessions import SessionStore
from fusion.policy import Policy


class Ingress:
    def __init__(self,path,wake,hook=lambda _:None):self.path,self.wake,self.hook=Path(path),wake,hook
    def drain(self):
        cfg=json.loads(self.path.read_text());p=cfg['task_ingress'];scope=p['scope'];principal=p['principal']
        # Current worker authority remains independent of the sender's hint.
        policy=Policy(self.path);worker=cfg['principals']['worker']['credential']
        def authorize(who,selected,op):
            require(who==principal and selected==scope and policy.authenticate(worker)=='worker','UNAUTHORIZED')
            policy.check('worker',scope,'tasks.ingress')
        authorize(principal,scope,'input.accept')
        db=sqlite3.connect(p['database'],timeout=.5);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
        db.executescript('''CREATE TABLE IF NOT EXISTS ingress_limits(singleton INTEGER PRIMARY KEY,calls INTEGER NOT NULL);
            INSERT OR IGNORE INTO ingress_limits VALUES(1,0);
            CREATE TABLE IF NOT EXISTS task_ingress(id TEXT PRIMARY KEY,delivery TEXT NOT NULL,origin TEXT,session TEXT,
                input TEXT,status TEXT NOT NULL DEFAULT 'captured',ack INTEGER NOT NULL DEFAULT 0);''')
        def reserve():
            with db:
                db.execute('BEGIN IMMEDIATE');used=db.execute('SELECT calls FROM ingress_limits').fetchone()[0]
                require(used<256,'OVERLOADED');db.execute('UPDATE ingress_limits SET calls=calls+1')
            self.hook('after_task_ingress_reservation')
        port=Client(p['client']);atoms=atoms_client(p['atoms'])
        selected_profile=cfg['native_sessions'].get('profile','omega-native-sessions/2')
        require(selected_profile in ('omega-native-sessions/2','omega-native-sessions/3'),'UNSUPPORTED_PROFILE')
        sustained=selected_profile=='omega-native-sessions/3'
        if sustained:
            from fusion.sustained_sessions import SustainedSessionStore
            require(p.get('allocation_profile')=='allocated-native-task-routing/1','UNSUPPORTED_PROFILE')
            store=SustainedSessionStore(cfg['native_sessions']['database'],authorize,cfg['native_sessions']['allocation'])
        else:store=SessionStore(cfg['native_sessions']['database'],authorize)
        try:
            reserve();require(port.call('authorize')=={'authorized':True},'UNAUTHORIZED')
            pending=db.execute('SELECT delivery FROM task_ingress WHERE ack=0 ORDER BY rowid LIMIT 1').fetchone()
            if pending is not None:delivery=json.loads(pending[0])
            else:
                reserve();delivery=port.call('poll')
            if delivery is None:return 'empty'
            key=delivery['delivery_id'];encoded=canonical(delivery).decode()
            with db:
                old=db.execute('SELECT delivery FROM task_ingress WHERE id=?',(key,)).fetchone()
                require(old is None or old[0]==encoded,'CONFLICT')
                require(old is not None or db.execute('SELECT count(*) FROM task_ingress').fetchone()[0]<64,'OVERLOADED')
                db.execute('INSERT OR IGNORE INTO task_ingress(id,delivery) VALUES(?,?)',(key,encoded))
            self.hook('after_task_ingress_capture')
            row=db.execute('SELECT * FROM task_ingress WHERE id=?',(key,)).fetchone()
            reserve();body=record(read_body(atoms,delivery['body']['ref'])['body'],scope)
            require(body['recipient']==principal and body['id']==delivery['body']['correlation_id'],'UNAUTHORIZED')
            require(body['sender'] in p['peers'] and delivery['body']['reply_route']=='task-'+body['sender'],'UNAUTHORIZED')
            if body['kind']=='task':
                if sustained:
                    allocation='incoming/'+body['sender']+'/'+body['session']
                    sid=str(uuid.uuid5(uuid.UUID(cfg['native_sessions']['allocation']['owner']),canonical([principal,allocation]).decode()))
                else:sid=p['session']
                text='query '+body['query']
            else:
                reserve();task=record(read_body(atoms,body['task'])['body'],scope);correlated(body,task,body['task'])
                sid=task['session'];text='task-context'
                if sustained:require(store.allocated(principal,sid)['frozen']['scope']==scope,'UNAUTHORIZED')
                else:require(sid in cfg['native_sessions']['session_templates'],'UNAUTHORIZED')
                for ref in body['payloads']:reserve();atoms.get(ref)
            origin=dict(profile=PROFILE,delivery=key,ref=delivery['body']['ref'],record=body)
            identity='mailbox/'+key
            if row['status']=='captured':
                # Expiry is recorded as a terminal refusal. Never substitute a
                # new input deadline to turn old task work into new work.
                prior_input=store.db.execute('SELECT id FROM preview_inputs WHERE session=? AND id=?',(sid,identity)).fetchone()
                if prior_input is None and time.time_ns()//1_000_000>=body['deadline']:
                    status='observed-late-result' if sustained and body['kind']=='result' else 'refused'
                    with db:db.execute("UPDATE task_ingress SET origin=?,status=? WHERE id=?",(canonical(origin).decode(),status,key))
                else:
                    if sustained:
                        if body['kind']=='task':require(store.allocate(principal,allocation,p['template'])['session']==sid,'CONFLICT')
                        require(store.allocated(principal,sid)['frozen']['scope']==scope,'UNAUTHORIZED')
                    else:store.create(principal,sid,scope,cfg['native_sessions']['session_templates'][sid])
                    # Origin capture precedes publish into the native inbox.
                    with store.db:
                        saved=store.db.execute('SELECT origin FROM preview_input_origins WHERE session=? AND id=?',(sid,identity)).fetchone()
                        require(saved is None or saved[0]==canonical(origin).decode(),'CONFLICT')
                        store.db.execute('INSERT OR IGNORE INTO preview_input_origins VALUES(?,?,?)',(sid,identity,canonical(origin).decode()))
                    accepted=store.submit(principal,sid,identity,text,'delegated-'+body['kind'],deadline_ms=body['deadline'])
                    self.hook('after_task_session_acceptance')
                    with db:db.execute("UPDATE task_ingress SET origin=?,session=?,input=?,status='accepted' WHERE id=?",
                        (canonical(origin).decode(),sid,canonical(accepted).decode(),key))
            row=db.execute('SELECT * FROM task_ingress WHERE id=?',(key,)).fetchone()
            if not row['ack']:
                reserve();port.call('ack','ingress/'+key,key)
                self.hook('after_task_ingress_ack')
                with db:db.execute('UPDATE task_ingress SET ack=1 WHERE id=?',(key,))
            if row['status']=='accepted':self.wake(sid)
            return row['status']
        finally:store.close();db.close()
    def invoke(self,credential,q):
        require(type(q) is dict and set(q)=={'profile','id'} and q['profile']==PROFILE,'UNSUPPORTED_PROFILE')
        require(type(q['id']) is str and len(q['id'])<=128)
        policy=Policy(self.path);actor=policy.authenticate(credential);cfg=policy.current()
        policy.check(actor,cfg['task_ingress']['scope'],'tasks.wake')
        status=self.drain()
        return dict(profile=PROFILE,id=q['id'],principal=cfg['task_ingress']['principal'],status=status)
