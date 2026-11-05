"""Finite commit-hint subscriptions in the existing application owner database.

Hints are not results. Explicit snapshots use the existing authorized session
read. Acknowledgment moves only a consumption cursor; work identities, original
deadlines and spent reservations are untouched. This opt-in profile is fresh
state only and its retained hint window may report an explicit gap.
"""
import json
import sqlite3
import time
import uuid
from .contracts import canonical, digest, require

PROFILE='application-commit-subscription/1'
WINDOW=32
LIMITS=dict(subscriptions=64,actions=512,window=WINDOW,page=16,lifetime_ms=300000,total_lifetime_ms=900000)


def install(store):
    db=store.db
    schema='''
        CREATE TABLE pilot_subscription_source(source TEXT PRIMARY KEY,clock INTEGER NOT NULL);
        CREATE TABLE pilot_subscription_heads(session TEXT PRIMARY KEY,head INTEGER NOT NULL);
        CREATE TABLE pilot_subscription_events(session TEXT NOT NULL,seq INTEGER NOT NULL,input TEXT,kind TEXT NOT NULL,state TEXT NOT NULL,PRIMARY KEY(session,seq));
        CREATE TABLE pilot_subscriptions(actor TEXT NOT NULL,id TEXT NOT NULL,session TEXT NOT NULL,created INTEGER NOT NULL,expires INTEGER NOT NULL,state TEXT NOT NULL,cursor INTEGER NOT NULL,observed INTEGER NOT NULL,snapshot TEXT,PRIMARY KEY(actor,id));
        CREATE TABLE pilot_subscription_actions(actor TEXT NOT NULL,id TEXT NOT NULL,action TEXT NOT NULL,intent TEXT NOT NULL,result TEXT NOT NULL,PRIMARY KEY(actor,id,action));
        CREATE TRIGGER pilot_input_accepted AFTER INSERT ON preview_inputs BEGIN
          INSERT INTO pilot_subscription_heads VALUES(NEW.session,1) ON CONFLICT(session) DO UPDATE SET head=head+1;
          INSERT INTO pilot_subscription_events SELECT NEW.session,head,NEW.id,'input',NEW.state FROM pilot_subscription_heads WHERE session=NEW.session;
          DELETE FROM pilot_subscription_events WHERE session=NEW.session AND seq<=(SELECT head-32 FROM pilot_subscription_heads WHERE session=NEW.session);
        END;
        CREATE TRIGGER pilot_input_transition AFTER UPDATE OF state ON preview_inputs WHEN OLD.state!=NEW.state BEGIN
          INSERT INTO pilot_subscription_heads VALUES(NEW.session,1) ON CONFLICT(session) DO UPDATE SET head=head+1;
          INSERT INTO pilot_subscription_events SELECT NEW.session,head,NEW.id,'input',NEW.state FROM pilot_subscription_heads WHERE session=NEW.session;
          DELETE FROM pilot_subscription_events WHERE session=NEW.session AND seq<=(SELECT head-32 FROM pilot_subscription_heads WHERE session=NEW.session);
        END;
        CREATE TRIGGER pilot_session_transition AFTER UPDATE OF state ON preview_sessions WHEN OLD.state!=NEW.state BEGIN
          INSERT INTO pilot_subscription_heads VALUES(NEW.id,1) ON CONFLICT(session) DO UPDATE SET head=head+1;
          INSERT INTO pilot_subscription_events SELECT NEW.id,head,NULL,'session',NEW.state FROM pilot_subscription_heads WHERE session=NEW.id;
          DELETE FROM pilot_subscription_events WHERE session=NEW.id AND seq<=(SELECT head-32 FROM pilot_subscription_heads WHERE session=NEW.id);
        END;
    '''
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_subscription_source'").fetchone():
            require(db.execute('SELECT count(*) FROM pilot_subscription_source').fetchone()[0]==1,'CONFLICT');return
        require(db.execute('SELECT count(*) FROM preview_inputs').fetchone()[0]==0,'CONFLICT')
        # DDL, trigger installation and source identity commit together. A kill
        # cannot leave an apparently installed but empty source identity.
        statement=''
        for line in schema.splitlines(True):
            statement+=line
            if sqlite3.complete_statement(statement):db.execute(statement);statement=''
        require(not statement.strip(),'CONFLICT')
        db.execute('INSERT INTO pilot_subscription_source VALUES(?,0)',(str(uuid.uuid4()),))


def usage(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_subscription_source'").fetchone():return None
    # Physical SQLite/PVC sizes belong to the common owner capacity observer.
    values={name:db.execute('SELECT count(*) FROM '+table).fetchone()[0] for name,table in
        [('subscriptions','pilot_subscriptions'),('actions','pilot_subscription_actions'),('retained_hints','pilot_subscription_events')]}
    values['logical_bytes']=sum(db.execute(sql).fetchone()[0] or 0 for sql in (
        'SELECT sum(length(CAST(actor||id||session||state AS BLOB))+64+coalesce(length(snapshot),0)) FROM pilot_subscriptions',
        'SELECT sum(length(CAST(actor||id||action||intent||result AS BLOB))) FROM pilot_subscription_actions',
        'SELECT sum(length(CAST(session||coalesce(input,\'\')||kind||state AS BLOB))+8) FROM pilot_subscription_events',
        'SELECT sum(length(session)+8) FROM pilot_subscription_heads'))
    open_=db.execute("SELECT count(*) FROM pilot_subscriptions WHERE state!='closed'").fetchone()[0]
    return dict(profile=PROFILE,**values,limits=LIMITS,closure_reserved_actions=open_,closure_reserved_bytes=open_*4096,authoritative_history_deleted=False)


class Subscriptions:
    def __init__(self,store,actor,authorize,clock=lambda:time.time_ns()//1000000):
        self.store,self.db,self.actor,self.authorize,self.clock=store,store.db,actor,authorize,clock
        require(self.db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_subscription_source'").fetchone() is not None,'UNSUPPORTED_PROFILE')
        row=self.db.execute('SELECT source FROM pilot_subscription_source').fetchone();require(row is not None,'CONFLICT')
        self.source=row[0];require(str(uuid.UUID(self.source))==self.source,'CONFLICT')

    def _now(self):
        now=self.clock();old=self.db.execute('SELECT clock FROM pilot_subscription_source').fetchone()[0]
        require(type(now) is int and now>=old,'CONFLICT')
        self.db.execute('UPDATE pilot_subscription_source SET clock=?',(now,));return now

    def _row(self,sid):
        row=self.db.execute('SELECT * FROM pilot_subscriptions WHERE actor=? AND id=?',(self.actor,sid)).fetchone()
        require(row is not None,'NOT_FOUND');self.authorize(row['session']);return row

    def _view(self,row,now):
        return dict(profile=PROFILE,source=self.source,subscription=row['id'],session=row['session'],
            state='expired' if row['expires']<=now and row['state']!='closed' else row['state'],
            created_ms=row['created'],expires_ms=row['expires'],cursor=row['cursor'],
            task_deadlines_extended=False,reservations_refunded=False,notifications_are_results=False)

    def control(self,operation,sid,action,body):
        require(operation in ('create','pause','resume','renew','ack','close','rebase'),'UNSUPPORTED_OPERATION')
        require(type(sid) is str and 1<=len(sid)<=128 and type(action) is str and 1<=len(action)<=128)
        require(type(body) is dict and len(canonical(body))<=2048)
        intent=canonical(dict(operation=operation,body=body)).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');now=self._now()
            row=self.db.execute('SELECT * FROM pilot_subscriptions WHERE actor=? AND id=?',(self.actor,sid)).fetchone()
            if row:self.authorize(row['session'])
            old=self.db.execute('SELECT intent,result FROM pilot_subscription_actions WHERE actor=? AND id=? AND action=?',(self.actor,sid,action)).fetchone()
            if old:
                require(old['intent']==intent,'CONFLICT')
                # Replaying an old renewal cannot resurrect or report an
                # expired subscription as active. The original receipt stays.
                if row and row['expires']<=now:return dict(receipt=json.loads(old['result']),current=self._view(row,now))
                return json.loads(old['result'])
            actions=self.db.execute('SELECT count(*) FROM pilot_subscription_actions').fetchone()[0]
            open_=self.db.execute("SELECT count(*) FROM pilot_subscriptions WHERE state!='closed'").fetchone()[0]
            require(actions+(1 if operation=='close' else open_+2 if operation=='create' else open_+1)<=LIMITS['actions'],'OVERLOADED')
            if operation=='create':
                require(set(body)=={'session','lifetime_ms'} and row is None,'CONFLICT')
                self.authorize(body['session'])
                require(type(body['lifetime_ms']) is int and 1000<=body['lifetime_ms']<=LIMITS['lifetime_ms'])
                require(self.db.execute('SELECT count(*) FROM pilot_subscriptions').fetchone()[0]<LIMITS['subscriptions'],'OVERLOADED')
                self.db.execute('INSERT INTO pilot_subscriptions VALUES(?,?,?,?,?,?,?,?,NULL)',
                    (self.actor,sid,body['session'],now,now+body['lifetime_ms'],'active',0,0))
            else:
                require(row is not None,'NOT_FOUND')
                if operation=='close':
                    require(body=={});self.db.execute("UPDATE pilot_subscriptions SET state='closed' WHERE actor=? AND id=?",(self.actor,sid))
                else:
                    require(row['state']!='closed' and row['expires']>now,'DEADLINE_EXCEEDED')
                    if operation in ('pause','resume'):
                        require(body=={});self.db.execute('UPDATE pilot_subscriptions SET state=? WHERE actor=? AND id=?',('paused' if operation=='pause' else 'active',self.actor,sid))
                    elif operation=='renew':
                        require(set(body)=={'expires_ms'} and type(body['expires_ms']) is int)
                        require(row['expires']<body['expires_ms']<=min(now+LIMITS['lifetime_ms'],row['created']+LIMITS['total_lifetime_ms']),'INVALID_ARGUMENT')
                        self.db.execute('UPDATE pilot_subscriptions SET expires=? WHERE actor=? AND id=?',(body['expires_ms'],self.actor,sid))
                    elif operation=='ack':
                        require(set(body)=={'source','cursor'} and body['source']==self.source,'CONFLICT')
                        require(type(body['cursor']) is int and row['cursor']<=body['cursor']<=row['observed'],'CONFLICT')
                        self.db.execute('UPDATE pilot_subscriptions SET cursor=? WHERE actor=? AND id=?',(body['cursor'],self.actor,sid))
                    else:
                        require(set(body)=={'source','head','snapshot_sha256'} and row['snapshot'] is not None,'CONFLICT')
                        require(body==json.loads(row['snapshot']),'CONFLICT')
                        head=self.db.execute('SELECT head FROM pilot_subscription_heads WHERE session=?',(row['session'],)).fetchone()
                        require(body['head']>=max(0,(head[0] if head else 0)-WINDOW),'CONFLICT')
                        self.db.execute('UPDATE pilot_subscriptions SET cursor=?,observed=?,snapshot=NULL WHERE actor=? AND id=?',(body['head'],body['head'],self.actor,sid))
            result=self._view(self._row(sid),now)
            self.db.execute('INSERT INTO pilot_subscription_actions VALUES(?,?,?,?,?)',(self.actor,sid,action,intent,canonical(result).decode()))
            self.authorize(result['session']);self.store._check_bytes()
            return result

    def read(self,sid,limit=16):
        require(type(limit) is int and 1<=limit<=LIMITS['page'])
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');now=self._now();row=self._row(sid);value=self._view(row,now)
            require(value['state'] in ('active','paused'),'DEADLINE_EXCEEDED')
            head=self.db.execute('SELECT head FROM pilot_subscription_heads WHERE session=?',(row['session'],)).fetchone();head=head[0] if head else 0
            first=max(1,head-WINDOW+1);gap=row['cursor']<first-1
            events=[] if gap or value['state']=='paused' else [dict(sequence=e['seq'],kind=e['kind'],state=e['state'],input=e['input']) for e in self.db.execute(
                'SELECT * FROM pilot_subscription_events WHERE session=? AND seq>? ORDER BY seq LIMIT ?',(row['session'],row['cursor'],limit))]
            next_=events[-1]['sequence'] if events else row['cursor']
            self.db.execute('UPDATE pilot_subscriptions SET observed=max(observed,?) WHERE actor=? AND id=?',(next_,self.actor,sid))
            self.authorize(row['session'])
            return dict(value,head=head,first_retained=first,next=next_,events=events,gap=gap,
                missing=None if not gap else dict(first=row['cursor']+1,last=first-1),
                recovery='READ_FULL_OWNER_SNAPSHOT_THEN_EXPLICIT_REBASE' if gap else 'READ_OWNER_RESULT_BEFORE_ACK',
                ordering='per-session-owner-commit',stream_complete=not gap and next_==head)

    def snapshot(self,sid,principal):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');now=self._now();row=self._row(sid)
            require(row['expires']>now and row['state']!='closed','DEADLINE_EXCEEDED')
            value=self.store.observe(principal,row['session'],True,after=0)
            # A bounded partial page cannot stand in for a full snapshot.
            require(value['complete'] is True,'OVERLOADED')
            head=self.db.execute('SELECT head FROM pilot_subscription_heads WHERE session=?',(row['session'],)).fetchone()
            receipt=dict(source=self.source,head=head[0] if head else 0,snapshot_sha256=digest(canonical(value)))
            self.db.execute('UPDATE pilot_subscriptions SET snapshot=? WHERE actor=? AND id=?',(canonical(receipt).decode(),self.actor,sid))
            self.authorize(row['session']);self.store._check_bytes();return dict(rebase=receipt,snapshot=value,events_are_results=False)
