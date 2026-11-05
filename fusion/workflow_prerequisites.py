"""Closed prerequisites through existing authenticated owner ports.

Read failures are UNKNOWN or UNAUTHORIZED, never invented negative facts.
Finite comparisons over existing NAL snapshots do not change their mathematics.
"""
from decimal import Decimal
import time
from .contracts import ContractError, canonical, digest, require, validate_ref
from . import lookup_contracts as c, nal_memory_contracts as n
from .preview_lifecycle import PROFILE as MEMORY
from .preview_relations import PROFILE as RELATIONS
from .sustained_sessions import PROFILE as SESSIONS

PROFILE = 'owner-observed-workflow-prerequisites/1'
KINDS = {'memory-active': MEMORY, 'relation-active': RELATIONS,
    'snapshot-available': 'immutable-bytes/1', 'belief-predicate': n.BELIEF_PROFILE,
    'result-captured': SESSIONS, 'capacity-authority': SESSIONS}
MAX_CONDITIONS = 8


def condition(value, scope):
    require(type(value) is dict and set(value) == {'id','kind','policy','scope','target','predicate'})
    require(type(value['id']) is str and 1 <= len(value['id']) <= 64)
    require(value['kind'] in KINDS and value['policy'] == KINDS[value['kind']], 'UNSUPPORTED_PROFILE')
    require(value['scope'] == scope and scope.startswith('synthetic-'), 'UNAUTHORIZED')
    t, k = value['target'], value['kind']; require(type(t) is dict)
    if k == 'memory-active':
        require(set(t) == {'logical_id','revision','payload'})
        c.identity(t['logical_id']); c.integer(t['revision'],1,256); validate_ref(t['payload'],scope)
    elif k == 'relation-active':
        require(set(t) == {'ref','asserted_at'}); validate_ref(t['ref'],scope); c.head(t['asserted_at'],scope,RELATIONS)
    elif k == 'snapshot-available':
        require(set(t) == {'ref','content_type'}); validate_ref(t['ref'],scope)
        require(type(t['content_type']) is str and 1 <= len(t['content_type']) <= 128)
    elif k == 'belief-predicate':
        require(set(t) == {'claim','context','runtime_selection'})
        validate_ref(t['claim'],scope); n.identifier(t['context'])
        from .delivery_contracts import sha
        sha(t['runtime_selection']); p=value['predicate']
        require(type(p) is dict and set(p) == {'field','comparison','value'})
        require(p['field'] in ('strength','confidence') and p['comparison'] in ('gte','lte','eq')); n.decimal(p['value'])
    elif k == 'result-captured':
        require(set(t) == {'session','input','result_sha256'}); c.identity(t['session'])
        require(type(t['input']) is str and 1 <= len(t['input']) <= 128)
        from .delivery_contracts import sha
        sha(t['result_sha256'])
    else:
        require(set(t) == {'session','minimum_inputs','minimum_pending'}); c.identity(t['session'])
        c.integer(t['minimum_inputs'],1,32); c.integer(t['minimum_pending'],1,4)
    if k != 'belief-predicate': require(value['predicate'] is None)
    require(len(canonical(value)) <= 4096,'OVERLOADED'); return value


class OwnerObservations:
    """SessionStore is this application's own owner. Other objects are ports."""
    def __init__(self,scope,principal,sessions,selections,*,lifecycle=None,relations=None,
                 atoms=None,beliefs=None,clock=lambda:time.time_ns()//1000000):
        self.scope,self.principal,self.sessions=scope,principal,sessions
        self.lifecycle,self.relations,self.atoms,self.beliefs=lifecycle,relations,atoms,beliefs
        self.clock=clock; require(type(selections) is dict and len(canonical(selections)) <= 32768)
        self.selections=selections

    def observe(self,declared,deadline):
        condition(declared,self.scope); start=self.clock()
        require(type(start) is int and start < deadline,'DEADLINE_EXCEEDED')
        try:
            state,evidence=self._read(declared['kind'],declared['target'],declared['predicate'],deadline)
            require(state in ('SATISFIED','INVALID','UNKNOWN'),'NOT_AVAILABLE'); error=None
        except ContractError as exc:
            state='UNAUTHORIZED' if exc.code=='UNAUTHORIZED' else 'UNKNOWN'; evidence=None; error=exc.code
        except (OSError,TimeoutError,KeyError,TypeError,ValueError): state,evidence,error='UNKNOWN',None,'NOT_AVAILABLE'
        end=self.clock(); require(type(end) is int and end >= start,'CONFLICT')
        if end >= deadline: state,error='UNKNOWN','DEADLINE_EXCEEDED'
        result=dict(profile=PROFILE,condition=declared,condition_sha256=digest(canonical(declared)),
            selection_sha256=digest(canonical(self.selections)),started_ms=start,observed_ms=end,
            state=state,evidence=evidence,error=error,global_atomic_snapshot=False)
        require(len(canonical(result)) <= 8192,'OVERLOADED'); return result

    def _read(self,kind,t,p,deadline):
        if kind=='memory-active':
            require(self.lifecycle is not None,'NOT_AVAILABLE')
            head=self.lifecycle.call('head',deadline=deadline)
            membership=self.lifecycle.call('activeSet',head,deadline=deadline)
            found=[x for x in membership['active'] if x['logical_id']==t['logical_id']]
            require(len(found)<=1,'NOT_AVAILABLE')
            valid=bool(found and found[0]['revision']==t['revision'] and found[0]['payload']==t['payload'])
            return ('SATISFIED' if valid else 'INVALID'),dict(at=head,selected=found[0] if found else None,
                active_set_sha256=digest(canonical(membership)))
        if kind=='relation-active':
            require(self.relations is not None,'NOT_AVAILABLE')
            v=self.relations.call('getRelation',t['ref'],True,deadline=deadline)
            require(type(v) is dict and v.get('profile')==RELATIONS and v.get('ref')==t['ref'],'NOT_AVAILABLE')
            require(v.get('state') in ('asserted','retracted') and digest(canonical(v['body']))==t['ref']['digest'],'NOT_AVAILABLE')
            return ('SATISFIED' if v['state']=='asserted' and v['asserted_at']==t['asserted_at'] else 'INVALID'),dict(
                ref=v['ref'],state=v['state'],asserted_at=v['asserted_at'],retracted_at=v.get('retracted_at'))
        if kind=='snapshot-available':
            require(self.atoms is not None,'NOT_AVAILABLE')
            from .responses import envelope
            v=self.atoms(deadline).get(t['ref']); envelope(v,t['ref']); require(v.content_type==t['content_type'],'NOT_AVAILABLE')
            return 'SATISFIED',dict(ref=v.ref,content_type=v.content_type,bytes=len(v.bytes))
        if kind=='belief-predicate':
            require(self.beliefs is not None,'NOT_AVAILABLE')
            v=self.beliefs.readBelief(t['claim'],t['context'],None)
            n.snapshot(v,t['claim'],t['context'],t['runtime_selection'])
            if v['truth'] is None: return 'UNKNOWN',dict(revision=v['revision'],truth=None)
            a,b=Decimal(v['truth'][p['field']]),Decimal(p['value'])
            valid={'gte':a>=b,'lte':a<=b,'eq':a==b}[p['comparison']]
            return ('SATISFIED' if valid else 'INVALID'),dict(revision=v['revision'],truth=v['truth'],
                claim=v['claim'],context=v['context'],snapshot_sha256=digest(canonical(v)))
        observed=self.sessions.observe(self.principal,t['session'],kind=='result-captured')
        require(observed['scope']==self.scope,'UNAUTHORIZED')
        if kind=='result-captured':
            found=[x for x in observed['inputs'] if x['id']==t['input']]
            if not found:return 'UNKNOWN',dict(session=t['session'],complete_page=observed['complete'])
            require(len(found)==1,'NOT_AVAILABLE'); v=found[0]
            if v['result'] is None:return 'UNKNOWN',dict(session=t['session'],state=v['state'])
            actual=digest(canonical(v['result']))
            return ('SATISFIED' if actual==t['result_sha256'] else 'INVALID'),dict(session=t['session'],
                input=v['id'],state=v['state'],result_sha256=actual,deadline_ms=v['deadline'])
        cap=observed['capacity']; valid=observed['state']=='active' and cap['remaining_inputs']>=t['minimum_inputs'] and cap['remaining_pending']>=t['minimum_pending']
        return ('SATISFIED' if valid else 'INVALID'),dict(session=t['session'],capacity=cap,
            state=observed['state'],current_authority_checked=True,admission_reserved=False)
