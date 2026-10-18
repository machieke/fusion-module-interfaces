"""S05 application identities/views; Attention owns scores, AtomStorage owns content."""
import json
import os
from pathlib import Path
import tempfile
import time
from . import promotion_contracts as c,vector_contracts as v,lookup_contracts as a
from .contracts import canonical,digest,require
from .promotion_composition import configuration,open_local
from .responses import envelope


def settings(app):
    cfg,_,frozen=configuration(app.config['attention_config'])
    require(frozen['principal']==app.binding['memory']['principal'],'UNAUTHORIZED')
    require(app.evidence_enabled,'UNSUPPORTED_PROFILE');app.evidence.authorize() if hasattr(app,'evidence') else None
    return cfg,frozen


class PriorityAdoption:
    def __init__(self,app):
        self.app,self.db=app,app.db;cfg,frozen=settings(app);require(frozen==app.binding['attention'],'CONFLICT')
        self.owner=open_local(app.config['attention_config'],app.hook)
        # Local composition obtains only existing AtomStorage ports. No Search or foreign DB access.
        from .vector_composition import ReadService
        from .neoclaw_memory import configuration as memory_configuration
        rc,_,_=memory_configuration(app.config['memory_read_config']);require(rc['placement']=='local','UNSUPPORTED_PROFILE')
        self.atoms=ReadService(rc['provider_config'],rc['credential']).atoms;self.scope=rc['scope']
        self.db.executescript('''CREATE TABLE IF NOT EXISTS app_priority(id TEXT PRIMARY KEY,request TEXT,binding TEXT,receipt TEXT,visible INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS app_priority_queries(id TEXT PRIMARY KEY,binding TEXT,result TEXT);
            CREATE TABLE IF NOT EXISTS app_priority_contexts(slot INTEGER PRIMARY KEY,view TEXT,deadline INTEGER,calls INTEGER DEFAULT 0,binding TEXT,result TEXT,payloads TEXT,rendered TEXT,lines TEXT);
            CREATE TABLE IF NOT EXISTS app_priority_payload_views(view TEXT PRIMARY KEY,value TEXT);
        ''');self.lines=[]
    def authorize(self):
        cfg,frozen=settings(self.app);require(frozen==self.app.binding['attention'],'CONFLICT')
        require(self.owner.authorize(cfg['scope'])==frozen['principal'],'UNAUTHORIZED');return cfg
    def active_view(self):
        key=self.db.execute('SELECT view FROM app_active_view').fetchone()[0]
        return key,json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(key,)).fetchone()[0])
    def view(self,key):
        row=self.db.execute('SELECT value FROM app_read_views WHERE id=?',(key,)).fetchone();require(row is not None,'NOT_AVAILABLE')
        value=json.loads(row[0]);self.app.evidence.validate_view(value);return value
    def payload(self,ref,view):
        atom=self.atoms.get(ref);envelope(atom,ref);require(atom.content_type==v.PAYLOAD,'NOT_AVAILABLE')
        value=v.payload(json.loads(atom.bytes),self.scope,view['snapshot']['corpus']);require(canonical(value)==atom.bytes,'NOT_AVAILABLE');return value
    def payload_view(self,key,deadline):
        self.authorize();view=self.view(key);old=self.db.execute('SELECT value FROM app_priority_payload_views WHERE view=?',(key,)).fetchone()
        if old is not None:
            self.atoms.head(self.scope) # live owner authority, never an external private-store read
            return json.loads(old[0])
        require(time.time()*1000<=deadline,'DEADLINE_EXCEEDED')
        through=view['snapshot']['head'];after=0;items={}
        require(through['sequence']<=c.MAX_TARGETS*3,'OVERLOADED')
        while after<through['sequence']:
            require(time.time()*1000<=deadline,'DEADLINE_EXCEEDED')
            page=a.commits(self.atoms.readCommits(self.scope,after,through,8),self.scope,after,through,8)
            for record in page['records']:
                if record['content_type']!=v.ENROLLMENT:continue
                atom=self.atoms.get(record['ref']);envelope(atom,record['ref']);require(atom.content_type==v.ENROLLMENT,'NOT_AVAILABLE')
                entry=json.loads(atom.bytes)
                if entry.get('corpus')!=view['snapshot']['corpus']:continue
                v.enrollment(entry,self.scope,view['snapshot']['corpus'],view['snapshot']['embedding'])
                require(canonical(entry)==atom.bytes and entry['uuid'] not in items,'NOT_AVAILABLE')
                p=self.payload(entry['payload'],view);require(p['uuid']==entry['uuid'],'NOT_AVAILABLE')
                items[p['uuid']]=dict(ref=entry['payload'],time=p['time'])
            after=page['next_after']
        require(set(items)=={r['uuid'] for r in view['metadata']['records']} and len(items)<=c.MAX_TARGETS,'NOT_AVAILABLE')
        self.authorize()
        with self.db:self.db.execute('INSERT INTO app_priority_payload_views VALUES(?,?)',(key,canonical(items).decode()))
        return items
    def request(self,key,kind,targets,deadline,delta=0,limit=10):
        cfg=self.authorize();f=self.app.binding['attention']
        return c.request(dict(profile=c.PROFILE,selection=f['selection'],principal=f['principal'],scope=cfg['scope'],context=cfg['context'],
            id=key,kind=kind,targets=targets,delta=delta,deadline_ms=deadline,limit=limit))
    def intent(self,command):
        require(len(command)==2 and type(command[1]) is str,'INVALID_ARGUMENT')
        self.authorize();key,view=self.active_view()
        items=self.payload_view(key,int(time.time()*1000)+self.app.config['invocation_timeout_ms'])
        # Native promote/demote do NOT replace underscores. Preserve parser/alias behavior.
        matches=[u for u,p in items.items() if p['time']==command[1]]
        require(len(matches)==1,'CONFLICT' if matches else 'NOT_FOUND');target=matches[0]
        self.payload(items[target]['ref'],view)
        return dict(profile=c.PROFILE,operation=command[0],arguments=dict(alias=command[1],target=target,view=key))
    def admit(self,key,intent):
        if intent['profile']==c.PROFILE:self.db.execute('INSERT INTO app_priority(id,request) VALUES(?,?)',(key,canonical(intent).decode()))
    def current(self):
        require(self.app.current is not None,'CONFLICT');row=self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?',self.app.current).fetchone()
        require(row is not None and json.loads(row['premises'])['profile']==c.PROFILE,'CONFLICT');return row
    def state(self,row):return self.db.execute('SELECT * FROM app_priority WHERE id=?',(row['id'],)).fetchone()
    def adjust(self,alias,delta):
        row=self.current();state=self.state(row);intent=json.loads(state['request']);args=intent['arguments'];self.authorize()
        require(alias==args['alias'] and delta==(1 if intent['operation']=='promote' else -1),'CONFLICT')
        items=self.payload_view(args['view'],row['deadline']);self.payload(items[args['target']]['ref'],self.view(args['view']))
        if state['binding'] is None:
            request=self.request(row['id'],'adjust',[args['target']],row['deadline'],delta,1)
            bound=c.binding(self.owner.bind(request),request)
            with self.db:self.db.execute('UPDATE app_priority SET binding=? WHERE id=?',(canonical(bound).decode(),row['id']))
            self.app.hook('after_priority_binding')
        else:bound=c.binding(json.loads(state['binding']))
        value=self.owner.observe(bound)
        if value is None:value=self.owner.adjust(bound)
        value=c.receipt(value,bound);self.authorize()
        with self.db:self.db.execute('UPDATE app_priority SET receipt=? WHERE id=?',(canonical(value).decode(),row['id']))
        self.app.hook('after_priority_receipt')
        if not self.state(row)['visible']:
            require(time.time()*1000<=row['deadline'],'DEADLINE_EXCEEDED')
            with self.db:self.db.execute('UPDATE app_priority SET visible=1 WHERE id=?',(row['id'],))
            self.app.hook('after_priority_visibility')
        return 'PROMOTE-SUCCESS' if delta==1 else 'DEMOTE-SUCCESS'
    def replay(self,row=None):
        row=self.current() if row is None else row;self.authorize();state=self.state(row)
        require(row['result'] is not None and state['visible'] and state['receipt'] is not None,'NOT_AVAILABLE')
        args=json.loads(state['request'])['arguments'];items=self.payload_view(args['view'],row['deadline'])
        self.payload(items[args['target']]['ref'],self.view(args['view']))
        bound=c.binding(json.loads(state['binding']));value=c.receipt(self.owner.observe(bound),bound)
        require(value==json.loads(state['receipt']),'NOT_AVAILABLE');return row['result']
    def capture(self,value):
        row=self.current();state=self.state(row);self.authorize();intent=json.loads(state['request'])
        require(value==('PROMOTE-SUCCESS' if intent['operation']=='promote' else 'DEMOTE-SUCCESS') and state['visible'],'NOT_AVAILABLE')
        require(row['result'] is None or row['result']==value,'CONFLICT')
        if row['result'] is None:require(time.time()*1000<=row['deadline'],'DEADLINE_EXCEEDED')
        with self.db:self.db.execute('UPDATE app_occurrences SET result=?,done=1 WHERE id=?',(value,row['id']))
        self.app.hook('after_priority_result');return value
    def query_clock(self):
        row=self.app.memory.current();self.authorize();state=self.db.execute('SELECT * FROM app_priority_queries WHERE id=?',(row['id'],)).fetchone()
        if state is None:
            read=self.db.execute('SELECT * FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone();require(read and read['payloads'] is not None,'NOT_AVAILABLE')
            targets=[r[0] for r in json.loads(read['payloads'])]
            request=self.request('query/'+row['id'],'scores',targets,row['deadline'],limit=len(targets));bound=c.binding(self.owner.bind(request),request)
            with self.db:self.db.execute('INSERT INTO app_priority_queries VALUES(?,?,NULL)',(row['id'],canonical(bound).decode()))
        else:bound=c.binding(json.loads(state['binding']))
        answer=self.owner.observe(bound)
        if answer is None:answer=self.owner.scores(bound)
        c.result(answer,bound);self.authorize()
        with self.db:self.db.execute('UPDATE app_priority_queries SET result=? WHERE id=?',(canonical(answer).decode(),row['id']))
        return self.app.memory.clock(bound['time'])
    def query_authorize(self,row):
        self.authorize();state=self.db.execute('SELECT * FROM app_priority_queries WHERE id=?',(row['id'],)).fetchone()
        if state is not None and state['result'] is not None:
            b=c.binding(json.loads(state['binding']));require(c.result(self.owner.observe(b),b)==json.loads(state['result']),'NOT_AVAILABLE')
    def score(self,observed,target):
        row=self.app.memory.current();self.query_authorize(row)
        state=self.db.execute('SELECT * FROM app_priority_queries WHERE id=?',(row['id'],)).fetchone();require(state and state['result'],'NOT_AVAILABLE')
        answer=json.loads(state['result']);require(observed==answer['binding']['time'],'CONFLICT')
        values=[r['score'] for r in answer['scores'] if r['target']==target];require(len(values)==1,'NOT_AVAILABLE');return values[0]
    def slot(self):return self.app.evidence.slot()
    def context(self):
        slot=self.slot();self.authorize();row=self.db.execute('SELECT * FROM app_priority_contexts WHERE slot=?',(slot,)).fetchone()
        if row is None:
            require(type(slot) is int and 1<=slot<=self.app.config['turn_limit'],'OVERLOADED')
            require(self.db.execute('SELECT count(*) FROM app_priority_contexts').fetchone()[0]<self.app.config['turn_limit'],'OVERLOADED')
            key,_=self.active_view();deadline=int(time.time()*1000)+self.app.config['invocation_timeout_ms']
            with self.db:self.db.execute('INSERT INTO app_priority_contexts(slot,view,deadline) VALUES(?,?,?)',(slot,key,deadline))
        return self.db.execute('SELECT * FROM app_priority_contexts WHERE slot=?',(slot,)).fetchone()
    def context_captured(self):
        row=self.context();self.lines=[];self.view(row['view'])
        return row['rendered'] is not None
    def context_ids(self):
        row=self.context();self.authorize()
        require(time.time()*1000<=row['deadline'],'DEADLINE_EXCEEDED')
        with self.db:
            require(row['calls']<c.MAX_EVALUATIONS,'OVERLOADED');self.db.execute('UPDATE app_priority_contexts SET calls=calls+1 WHERE slot=?',(row['slot'],))
        items=self.payload_view(row['view'],row['deadline'])
        if row['binding'] is None:
            request=self.request('context/'+self.app.session+'/'+str(row['slot']),'rank',sorted(items),row['deadline'])
            bound=c.binding(self.owner.bind(request),request)
            with self.db:self.db.execute('UPDATE app_priority_contexts SET binding=? WHERE slot=?',(canonical(bound).decode(),row['slot']))
        else:bound=c.binding(json.loads(row['binding']))
        value=self.owner.observe(bound)
        if value is None:value=self.owner.rank(bound)
        value=c.result(value,bound)
        with self.db:self.db.execute('UPDATE app_priority_contexts SET result=? WHERE slot=?',(canonical(value).decode(),row['slot']))
        self.app.hook('after_global_selection')
        return value['selected']
    def context_payloads(self,targets):
        row=self.context();require(row['result'] is not None,'NOT_AVAILABLE');require(time.time()*1000<=row['deadline'],'DEADLINE_EXCEEDED');result=json.loads(row['result'])
        require(targets==result['selected'],'CONFLICT');view=self.view(row['view']);items=self.payload_view(row['view'],row['deadline']);payloads=[]
        for target in targets:
            require(time.time()*1000<=row['deadline'],'DEADLINE_EXCEEDED')
            require(target in items,'NOT_AVAILABLE');p=self.payload(items[target]['ref'],view);require(p['uuid']==target,'NOT_AVAILABLE')
            payloads.append([target,p['time'],p['content']])
        with self.db:self.db.execute('UPDATE app_priority_contexts SET payloads=? WHERE slot=?',(canonical(payloads).decode(),row['slot']))
        return payloads
    def promoted_line(self,line):
        require(type(line) is str and len(line)<=8192 and len(self.lines)<c.MAX_TARGETS,'NOT_AVAILABLE');self.lines.append(line);return True
    def output(self,lines):
        cfg=self.authorize();path=Path(cfg['output']);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd,name=tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd,'w') as f:f.write(''.join(line+'\n' for line in lines));f.flush();os.fsync(f.fileno())
            os.replace(name,path)
            directory=os.open(path.parent,os.O_RDONLY)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            if os.path.exists(name):os.unlink(name)
    def context_capture(self,value):
        row=self.context();require(type(value) is str and len(value)<=50000 and row['payloads'] is not None,'NOT_AVAILABLE')
        require(time.time()*1000<=row['deadline'],'DEADLINE_EXCEEDED');self.authorize()
        require(len(self.lines)==len(json.loads(row['payloads'])),'NOT_AVAILABLE')
        with self.db:self.db.execute('UPDATE app_priority_contexts SET rendered=?,lines=? WHERE slot=?',(value,canonical(self.lines).decode(),row['slot']))
        self.app.hook('after_global_capture');return self.context_replay()
    def context_replay(self):
        row=self.context();require(row['rendered'] is not None,'NOT_AVAILABLE');self.authorize()
        b=c.binding(json.loads(row['binding']));require(c.result(self.owner.observe(b),b)==json.loads(row['result']),'NOT_AVAILABLE')
        view=self.view(row['view']);items=self.payload_view(row['view'],row['deadline'])
        for target,stamp,text in json.loads(row['payloads']):
            p=self.payload(items[target]['ref'],view);require([p['uuid'],p['time'],p['content']]==[target,stamp,text],'NOT_AVAILABLE')
        self.authorize();self.output(json.loads(row['lines']));return row['rendered']
