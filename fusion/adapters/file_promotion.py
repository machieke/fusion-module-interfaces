"""Independent bounded atomic-file Attention conformance provider (fixture storage).

Shares only DTOs and pure native math. No primary-owner import, helpers or tables.
"""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
import time
from .. import promotion_contracts as c
from ..contracts import canonical,digest,require,ContractError


class FilePromotion:
    def __init__(self,path,access,math,*,clock=time.time,hook=lambda _:None):
        self.path,self.access,self.math,self.clock,self.hook=Path(path),access,math,clock,hook
        if self.path.exists():
            try:value=json.loads(self.path.read_bytes())
            except (ValueError,UnicodeError):raise ContractError('UNSUPPORTED_PROFILE') from None
            require(type(value) is dict and set(value)=={'selection','contexts','work'} and
                    type(value['contexts']) is dict and type(value['work']) is dict,'UNSUPPORTED_PROFILE')
        with self.locked() as data:require(data['selection']==self.access.selection(),'UNSUPPORTED_PROFILE')
    @contextmanager
    def locked(self):
        with self.path.with_suffix('.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            value=json.loads(self.path.read_bytes()) if self.path.exists() else dict(selection=self.access.selection(),contexts={},work={})
            yield value
    def save(self,data):
        fd,name=tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write(canonical(data));f.flush();os.fsync(f.fileno())
            os.replace(name,self.path)
            fd=os.open(self.path.parent,os.O_RDONLY)
            try:os.fsync(fd)
            finally:os.close(fd)
        finally:
            if os.path.exists(name):os.unlink(name)
    def authorize(self,scope):return self.access.authorize(scope,'authorize')
    def check(self,q,method):
        c.request(q);require(self.access.authorize(q['scope'],method)==q['principal'],'UNAUTHORIZED')
        require(q['selection']==self.access.selection(),'UNSUPPORTED_PROFILE')
    def identity(self,q):return canonical([q['principal'],q['scope'],q['context']]).decode(),canonical([q['principal'],q['scope'],q['context'],q['id']]).decode()
    def bind(self,q):
        q=json.loads(canonical(q));self.check(q,'bind');context,key=self.identity(q)
        with self.locked() as d:
            if key in d['work']:
                previous=c.binding(d['work'][key]['binding']);require(previous['request']==q,'CONFLICT');return previous
            require(time.time()*1000<=q['deadline_ms'],'DEADLINE_EXCEEDED');require(len(d['work'])<c.MAX_BINDINGS,'OVERLOADED')
            now=c.number(self.clock())
            if context not in d['contexts']:
                require(len(d['contexts'])<c.MAX_CONTEXTS,'OVERLOADED');d['contexts'][context]=dict(water=now,versions=[{}])
            state=d['contexts'][context];require(now>=state['water'],'CONFLICT');state['water']=now
            b=dict(request=q,revision=len(state['versions'])-1,time=now,clock='trusted-local-epoch-seconds/1')
            d['work'][key]=dict(binding=b,spent=0,result=None);self.check(q,'bind');self.save(d)
        self.hook('after_priority_clock' if q['kind']=='adjust' else 'after_priority_read_clock');self.check(q,'bind');return b
    def record(self,d,b):
        c.binding(b);context,key=self.identity(b['request']);require(key in d['work'],'NOT_AVAILABLE')
        work=d['work'][key];require(work['binding']==b,'CONFLICT');return d['contexts'][context],work
    def observe(self,b):
        c.binding(b)
        self.check(b['request'],'observe')
        with self.locked() as d:_,w=self.record(d,b);result=w['result']
        self.check(b['request'],'observe');return result
    def execute(self,b,method):
        b=c.binding(json.loads(canonical(b)));q=b['request'];self.check(q,method);require(q['kind']==method,'CONFLICT')
        with self.locked() as d:
            context,work=self.record(d,b)
            if work['result'] is not None:return work['result']
            require(time.time()*1000<=q['deadline_ms'],'DEADLINE_EXCEEDED');require(work['spent']<c.MAX_EVALUATIONS,'OVERLOADED')
            require(b['revision']<len(context['versions']),'NOT_AVAILABLE');nodes=context['versions'][b['revision']]
            if method=='adjust':
                require(b['revision']==len(context['versions'])-1,'CONFLICT')
                require(b['revision']<c.MAX_REVISIONS and (q['targets'][0] in nodes or len(nodes)<c.MAX_TARGETS),'OVERLOADED')
            arguments=[]
            for target in q['targets']:
                previous=nodes.get(target,dict(value=0.,time=0.));arguments.append([previous['value'],previous['time'],b['time'],0])
            if method=='adjust':arguments.append(arguments[0][:3]+[q['delta']])
            work['spent']+=1;self.save(d)
        self.hook('after_priority_reservation');values=self.math.evaluate(arguments,q['deadline_ms'])
        require(len(values)==len(arguments),'NOT_AVAILABLE')
        for v in values:c.number(v,0,10)
        self.hook('after_priority_evaluation' if q['kind']=='adjust' else 'after_priority_score_evaluation')
        with self.locked() as d:
            context,work=self.record(d,b);self.check(q,method)
            if work['result'] is not None:return work['result']
            require(time.time()*1000<=q['deadline_ms'],'DEADLINE_EXCEEDED')
            if method=='adjust':
                require(b['revision']==len(context['versions'])-1,'CONFLICT')
                nodes=dict(context['versions'][-1]);nodes[q['targets'][0]]=dict(value=values[1],time=b['time']);context['versions'].append(nodes)
                answer=dict(binding=b,revision=b['revision']+1,target=q['targets'][0],requested=q['delta'],before=values[0],value=values[1],time=b['time']);c.receipt(answer,b)
            else:
                scores=[dict(target=t,score=v) for t,v in zip(q['targets'],values)]
                ordered=sorted(zip(values,q['targets']),key=lambda pair:(-pair[0],pair[1]))
                selected=[target for value,target in ordered if value>0][:q['limit']] if method=='rank' else q['targets']
                answer=dict(binding=b,scores=scores,selected=selected,coverage=dict(eligible=len(scores),complete=True));c.result(answer,b)
            work['result']=answer;self.save(d)
        self.hook('after_priority_commit' if method=='adjust' else 'after_priority_read_commit');self.check(q,method);return answer
    def adjust(self,b):return self.execute(b,'adjust')
    def scores(self,b):return self.execute(b,'scores')
    def rank(self,b):return self.execute(b,'rank')
