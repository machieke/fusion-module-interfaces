"""Attention's local wall-clock sibling profile; never an STI conversion."""
import math
import uuid
from typing import Protocol
from .contracts import canonical, digest, require
from .neoclaw_contracts import fields

PROFILE='wall-clock-promotion/1'
APPLICATION='controlled-native-loop/7'
OPERATIONS=('bind','adjust','scores','rank','observe','authorize')
MAX_TARGETS=128
MAX_BINDINGS=256
MAX_REVISIONS=256
MAX_CONTEXTS=8
MAX_EVALUATIONS=3

def number(x,lo=0.,hi=2**53):
    require(type(x) in (int,float),'INVALID_ARGUMENT')
    try:y=float(x)
    except (ValueError,OverflowError):require(False,'INVALID_ARGUMENT')
    require(math.isfinite(y) and lo<=y<=hi,'INVALID_ARGUMENT');return y

def identifier(x):
    require(type(x) is str and 0<len(x)<=160 and all(ord(c)>=32 for c in x),'INVALID_ARGUMENT');return x

def targets(xs):
    require(type(xs) is list and len(xs)<=MAX_TARGETS and all(type(x) is str for x in xs),'INVALID_ARGUMENT')
    require(len(set(xs))==len(xs),'INVALID_ARGUMENT')
    for x in xs:
        identifier(x)
        try:require(str(uuid.UUID(x))==x,'INVALID_ARGUMENT')
        except ValueError:require(False,'INVALID_ARGUMENT')
    return xs

def request(x):
    fields(x,'profile selection principal scope context id kind targets delta deadline_ms limit')
    require(x['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    for k in ('selection','principal','scope','context','id'):identifier(x[k])
    require(x['kind'] in ('adjust','scores','rank'),'INVALID_ARGUMENT');targets(x['targets'])
    require(type(x['deadline_ms']) is int and x['deadline_ms']>0,'INVALID_ARGUMENT')
    require(type(x['limit']) is int and 0<=x['limit']<=MAX_TARGETS,'INVALID_ARGUMENT')
    if x['kind']=='adjust':require(len(x['targets'])==1 and type(x['delta']) is int and x['delta'] in (-1,1) and x['limit']==1,'INVALID_ARGUMENT')
    else:require(x['delta']==0 and type(x['delta']) is int,'INVALID_ARGUMENT')
    return x

def binding(x,q=None):
    fields(x,'request revision time clock');request(x['request'])
    require(type(x['revision']) is int and 0<=x['revision']<=MAX_REVISIONS,'NOT_AVAILABLE');number(x['time'])
    require(x['clock']=='trusted-local-epoch-seconds/1','UNSUPPORTED_PROFILE')
    if q is not None:require(x['request']==q,'NOT_AVAILABLE')
    return x

def receipt(x,b):
    fields(x,'binding revision target requested before value time');binding(b)
    require(x['binding']==b and b['request']['kind']=='adjust' and x['target']==b['request']['targets'][0] and
            x['requested']==b['request']['delta'] and x['revision']==b['revision']+1 and x['time']==b['time'],'NOT_AVAILABLE')
    number(x['before'],0,10);number(x['value'],0,10)
    # Shape and exact input binding; native math is the provider's responsibility.
    return x

def result(x,b):
    fields(x,'binding scores selected coverage');require(x['binding']==b,'NOT_AVAILABLE');binding(b)
    rows=x['scores'];require(type(rows) is list and len(rows)==len(b['request']['targets']),'NOT_AVAILABLE')
    for row,target in zip(rows,b['request']['targets']):
        fields(row,'target score');require(row['target']==target,'NOT_AVAILABLE');number(row['score'],0,10)
    require(x['coverage']=={'eligible':len(rows),'complete':True},'NOT_AVAILABLE')
    expected=[r['target'] for r in sorted(rows,key=lambda r:(-r['score'],r['target'])) if r['score']>0][:b['request']['limit']] if b['request']['kind']=='rank' else b['request']['targets']
    require(x['selected']==expected,'NOT_AVAILABLE');return x

class Promotion(Protocol):
    def bind(self,request:dict)->dict: ...
    def adjust(self,binding:dict)->dict: ...
    def observe(self,binding:dict)->dict|None: ...
    def scores(self,binding:dict)->dict: ...
    def rank(self,binding:dict)->dict: ...
    def authorize(self,scope:str)->str: ...

class PromotionMath(Protocol):
    def evaluate(self,rows:list,deadline_ms:int)->list: ...
