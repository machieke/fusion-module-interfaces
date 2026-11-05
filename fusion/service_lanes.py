"""Finite in-process admission lanes for the existing service host.

No retry, waiting scheduler, persisted work queue, deadline or effect allowance.
The existing owner authorizes and accounts every accepted request. These slots
protect observation/control admission during ordinary request pressure only.
"""
import threading
from contextlib import contextmanager
from .contracts import require

PROFILE='bounded-service-request-lanes/1'
LIMITS={'normal':4,'maintenance':1,'observation':4,'per_actor':2}
READS={
 '/preview/session':{'observe','disclose','binding','list','capacity'},
 '/preview/browser':{'inventory','current'},
 '/preview/capabilities':{'inspect','preflight'},
 '/preview/providers':{'inspect','selected','headroom'},
 '/preview/subscriptions':{'read','observe'},
 '/preview/worker':{'observe'},
 '/preview/worker-control':{'observe'},
 '/preview/continuation':{'observe'},
 '/preview/chain-continuation':{'observe'},
 '/preview/tasks':{'observe','read','events'},
 '/preview/inspection':{'status','result','events'},
 '/preview/commitment':{'observe','saved_intent'},
 '/preview/search-maintenance':{'observeRepair','observeCleanup'},
 '/s03-encode':{'authorize-invoke','authorize-disclose'},
 '/preview/model':{'observe','authorize'},
 '/s03-read':{'get','getMany','availability'},
 '/memory-source':{'head','readCommits','capacity'},
 '/reference-cognition':{'readEpisode','readEvidence','pendingEvidence','readOccurrence','readBelief','observeDecision','readDecisions','observe','getRelation','outgoing','incoming','get','getMany','availability','head','readCommits'},
}
CONTROL={
 '/preview/session':{'cancel','reconcile','pause','close'},
 '/preview/providers':{'seal','disable','drain','retire'},
 '/preview/worker-control':{'drain','stop'},
 '/preview/search-maintenance':{'planRepair','repair','planCleanup','applyCleanup'},
 '/preview/subscriptions':{'pause','ack','close'},
}


def classify(route,request):
    op=request.get('operation')
    if type(op) is not str:return 'normal'
    if op in READS.get(route,()):return 'observation'
    if op in CONTROL.get(route,()):return 'maintenance'
    return 'normal'


class Lanes:
    def __init__(self,selection):
        require(type(selection) is dict and set(selection)=={'profile','limits'} and selection['profile']==PROFILE,'UNSUPPORTED_PROFILE')
        limits=selection['limits'];require(type(limits) is dict and set(limits)==set(LIMITS))
        require(all(type(v) is int and 1<=v<=LIMITS[k] for k,v in limits.items()))
        self.limits=dict(limits);self.lock=threading.Lock();self.active={x:0 for x in LIMITS if x!='per_actor'};self.actors={}
    def enter(self,lane,actor):
        require(lane in self.active and type(actor) is str)
        with self.lock:
            key=(lane,actor);used=self.actors.get(key,0)
            require(self.active[lane]<self.limits[lane] and used<self.limits['per_actor'],'OVERLOADED')
            self.active[lane]+=1;self.actors[key]=used+1
        return key
    def leave(self,key):
        with self.lock:
            require(key in self.actors and self.actors[key]>0,'CONFLICT')
            self.active[key[0]]-=1;self.actors[key]-=1
            if not self.actors[key]:del self.actors[key]
    def observe(self):
        with self.lock:return dict(profile=PROFILE,active=dict(self.active),limits=dict(self.limits),queue=0,retries=0,authority=False)
    @contextmanager
    def admit(self,route,request,actor):
        key=self.enter(classify(route,request),actor)
        try:yield
        finally:self.leave(key)
