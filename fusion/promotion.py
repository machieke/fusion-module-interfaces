"""Separate SQLite Attention owner for the named native wall-clock policy."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time
from . import promotion_contracts as c
from .contracts import canonical,digest,require,ContractError


class PromotionOwner:
    def __init__(self,path,access,math,*,clock=time.time,hook=lambda _:None):
        self.path,self.access,self.math,self.clock,self.hook=str(path),access,math,clock,hook
        # Inspect existing files read-only before WAL or schema changes. Never
        # reinterpret a legacy promotion map or another owner's journal.
        existing=Path(self.path).resolve()
        if existing.exists():
            try:
                with closing(sqlite3.connect(existing.as_uri()+'?mode=ro',uri=True)) as prior:
                    tables={r[0] for r in prior.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
                    require(not tables or tables=={'identity','contexts','history','bindings'},'UNSUPPORTED_PROFILE')
                    if tables:
                        records=prior.execute('SELECT value FROM identity').fetchall()
                        require(records==[(access.selection(),)],'UNSUPPORTED_PROFILE')
                        expected={'identity':['value'],'contexts':['id','revision','water'],'history':['context','revision','state'],
                                  'bindings':['id','context','value','calls','result']}
                        for table,columns in expected.items():
                            require([r[1] for r in prior.execute('PRAGMA table_info('+table+')')]==columns,'UNSUPPORTED_PROFILE')
            except sqlite3.DatabaseError:raise ContractError('UNSUPPORTED_PROFILE') from None
        with closing(self.connect()) as db,db:
            db.executescript('''CREATE TABLE IF NOT EXISTS identity(value TEXT);
                CREATE TABLE IF NOT EXISTS contexts(id TEXT PRIMARY KEY,revision INTEGER,water REAL);
                CREATE TABLE IF NOT EXISTS history(context TEXT,revision INTEGER,state TEXT,PRIMARY KEY(context,revision));
                CREATE TABLE IF NOT EXISTS bindings(id TEXT PRIMARY KEY,context TEXT,value TEXT,calls INTEGER DEFAULT 0,result TEXT);''')
            identity=access.selection();old=db.execute('SELECT value FROM identity').fetchone()
            if old:require(old[0]==identity,'UNSUPPORTED_PROFILE')
            else:db.execute('INSERT INTO identity VALUES(?)',(identity,))
    def connect(self):
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db
    def authorize(self,scope):return self.access.authorize(scope,'authorize')
    def check(self,q,op):
        c.request(q);principal=self.access.authorize(q['scope'],op)
        require(principal==q['principal'],'UNAUTHORIZED');require(q['selection']==self.access.selection(),'UNSUPPORTED_PROFILE')
    def keys(self,q):
        return digest(canonical([q['principal'],q['scope'],q['context']])),digest(canonical([q['principal'],q['scope'],q['context'],q['id']]))
    def bind(self,q):
        q=json.loads(canonical(q));self.check(q,'bind');ctx,key=self.keys(q)
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT value FROM bindings WHERE id=?',(key,)).fetchone()
            if old:
                previous=c.binding(json.loads(old[0]));require(previous['request']==q,'CONFLICT');return previous
            require(time.time()*1000<=q['deadline_ms'],'DEADLINE_EXCEEDED')
            require(db.execute('SELECT count(*) FROM bindings').fetchone()[0]<c.MAX_BINDINGS,'OVERLOADED')
            state=db.execute('SELECT * FROM contexts WHERE id=?',(ctx,)).fetchone()
            now=c.number(self.clock())
            if state:require(now>=state['water'],'CONFLICT');revision=state['revision']
            else:
                require(db.execute('SELECT count(*) FROM contexts').fetchone()[0]<c.MAX_CONTEXTS,'OVERLOADED');revision=0
                db.execute('INSERT INTO contexts VALUES(?,?,?)',(ctx,0,now))
                db.execute('INSERT INTO history VALUES(?,?,?)',(ctx,0,'{}'))
            self.check(q,'bind')
            bound=dict(request=q,revision=revision,time=now,clock='trusted-local-epoch-seconds/1');c.binding(bound)
            db.execute('UPDATE contexts SET water=? WHERE id=?',(now,ctx))
            db.execute('INSERT INTO bindings(id,context,value) VALUES(?,?,?)',(key,ctx,canonical(bound).decode()))
        self.hook('after_priority_clock' if q['kind']=='adjust' else 'after_priority_read_clock');self.check(q,'bind');return bound
    def load(self,db,b):
        c.binding(b);ctx,key=self.keys(b['request'])
        row=db.execute('SELECT * FROM bindings WHERE id=?',(key,)).fetchone()
        require(row is not None,'NOT_AVAILABLE');require(json.loads(row['value'])==b,'CONFLICT')
        return ctx,key,row
    def observe(self,b):
        c.binding(b)
        self.check(b['request'],'observe')
        with closing(self.connect()) as db:
            _,_,row=self.load(db,b)
            result=json.loads(row['result']) if row['result'] else None
        self.check(b['request'],'observe')
        if result is not None:(c.receipt if b['request']['kind']=='adjust' else c.result)(result,b)
        return result
    def compute(self,b,kind):
        b=c.binding(json.loads(canonical(b)));q=b['request'];self.check(q,kind);require(q['kind']==kind,'CONFLICT')
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');ctx,key,row=self.load(db,b)
            if row['result'] is not None:return json.loads(row['result'])
            require(time.time()*1000<=q['deadline_ms'],'DEADLINE_EXCEEDED');require(row['calls']<c.MAX_EVALUATIONS,'OVERLOADED')
            state_row=db.execute('SELECT state FROM history WHERE context=? AND revision=?',(ctx,b['revision'])).fetchone()
            require(state_row is not None,'NOT_AVAILABLE');state=json.loads(state_row[0])
            if kind=='adjust':
                head=db.execute('SELECT revision FROM contexts WHERE id=?',(ctx,)).fetchone()[0]
                require(head==b['revision'],'CONFLICT');require(head<c.MAX_REVISIONS,'OVERLOADED')
                require(q['targets'][0] in state or len(state)<c.MAX_TARGETS,'OVERLOADED')
            db.execute('UPDATE bindings SET calls=calls+1 WHERE id=?',(key,))
        self.hook('after_priority_reservation')
        rows=[[state.get(t,[0.,0.])[0],state.get(t,[0.,0.])[1],b['time'],0] for t in q['targets']]
        # One bounded native batch; adjustment calculates score and exact native cap expression.
        if kind=='adjust':rows.append([*rows[0][:3],q['delta']])
        values=self.math.evaluate(rows,q['deadline_ms']);require(len(values)==len(rows),'NOT_AVAILABLE')
        for value in values:c.number(value,0,10)
        self.hook('after_priority_evaluation' if q['kind']=='adjust' else 'after_priority_score_evaluation')
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');ctx,key,row=self.load(db,b);self.check(q,kind)
            if row['result'] is not None:return json.loads(row['result'])
            require(time.time()*1000<=q['deadline_ms'],'DEADLINE_EXCEEDED')
            if kind=='adjust':
                require(db.execute('SELECT revision FROM contexts WHERE id=?',(ctx,)).fetchone()[0]==b['revision'],'CONFLICT')
                target=q['targets'][0];state[target]=[values[1],b['time']]
                result=dict(binding=b,revision=b['revision']+1,target=target,requested=q['delta'],before=values[0],value=values[1],time=b['time'])
                c.receipt(result,b)
                db.execute('INSERT INTO history VALUES(?,?,?)',(ctx,result['revision'],canonical(state).decode()))
                db.execute('UPDATE contexts SET revision=? WHERE id=?',(result['revision'],ctx))
            else:
                scores=[dict(target=t,score=s) for t,s in zip(q['targets'],values)]
                selected=[r['target'] for r in sorted(scores,key=lambda r:(-r['score'],r['target'])) if r['score']>0][:q['limit']] if kind=='rank' else q['targets']
                result=dict(binding=b,scores=scores,selected=selected,coverage=dict(eligible=len(scores),complete=True));c.result(result,b)
            db.execute('UPDATE bindings SET result=? WHERE id=?',(canonical(result).decode(),key))
        self.hook('after_priority_commit' if kind=='adjust' else 'after_priority_read_commit');self.check(q,kind);return result
    def adjust(self,b):return self.compute(b,'adjust')
    def scores(self,b):return self.compute(b,'scores')
    def rank(self,b):return self.compute(b,'rank')
