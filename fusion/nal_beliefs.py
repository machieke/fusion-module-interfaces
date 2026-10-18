"""Selected C2 NAL policy on the existing belief owner/journal, local only."""
from contextlib import closing
from contextvars import ContextVar
import json
import time
from .beliefs import BeliefOwner
from . import nal_memory_contracts as c
from .contracts import canonical,digest,require,validate_ref
from .responses import envelope

_ACTIVE=ContextVar('nal_admission',default=None)


class NalBeliefOwner(BeliefOwner):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,contracts=c,**kwargs)
        with closing(self._connect()) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS nal_budgets(id TEXT PRIMARY KEY, binding TEXT NOT NULL, evaluations INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS nal_priors(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, snapshot TEXT NOT NULL)')

    def _request(self,semantic): return c.request(semantic)

    def _evidence(self,request):
        record=super()._evidence(request)
        require(request.deadline_ms==record['event']['deadline_ms'],'CONFLICT')
        return record

    def _authorize(self,scope,operation,assumption=False):
        principal=super()._authorize(scope,operation,assumption)
        request=_ACTIVE.get()
        if operation=='submitEvidence' and request is not None:
            require(time.time_ns()//1_000_000<=request.deadline_ms,'DEADLINE_EXCEEDED')
            if request.independence: self.access.assumption(scope,request.independence)
        return principal

    @c.boundary
    def observeDecision(self,request):
        semantic=c.submission(request)
        request=c.request(semantic)
        principal=super()._authorize(request.command.scope_ref,'observeDecision')
        identity=digest(canonical([principal,request.command.scope_ref,request.command.idempotency_key]))
        fingerprint=digest(canonical([semantic,self.selection]))
        with closing(self._connect()) as db: result=self._replay(db,identity,fingerprint)
        if result is not None: c.response(c.decision,result,request.claim,request.context,self.runtime_selection)
        return result

    @c.boundary
    def submitEvidence(self,request):
        request=c.request(c.submission(request))
        # Observation permits exact already committed recovery after expiry, never
        # authorizes a missing admission. Current submit authority still applies.
        super()._authorize(request.command.scope_ref,'submitEvidence',request.independence is not None)
        if request.independence: self.access.assumption(request.command.scope_ref,request.independence)
        prior=self.observeDecision(request)
        if prior is not None: return prior
        token=_ACTIVE.set(request)
        try: return super().submitEvidence(request)
        finally: _ACTIVE.reset(token)

    @c.boundary
    def registerPrior(self,command,claim,context,creation,deadline_ms):
        claim,creation=c.detached(claim),c.detached(creation)
        c.mutation(command);validate_ref(claim,command.scope_ref);validate_ref(creation,command.scope_ref)
        c.identifier(context);c.integer(deadline_ms,1)
        principal=super()._authorize(command.scope_ref,'registerPrior'); self._claim(claim)
        atom=self.atoms.get(creation);envelope(atom,creation)
        require(atom.content_type=='application/neoclaw-fresh-creation','INVALID_ARGUMENT')
        value=json.loads(atom.bytes);c.fields(value,'policy memory_uuid occurrence time payload enrollment')
        from .append_contracts import timestamp
        timestamp(value['time'])
        require(value['policy']==c.PRIOR,'UNSUPPORTED_PROFILE')
        for k in ('memory_uuid','occurrence'):c.identifier(value[k])
        for k in ('payload','enrollment'):validate_ref(value[k],value[k]['scope_ref'])
        claim_atom=self.atoms.get(claim);envelope(claim_atom,claim)
        require(json.loads(claim_atom.bytes)==dict(predicate='neoclaw-memory-assessment',arguments=[creation['digest']],positive=True),'CONFLICT')
        identity=digest(canonical([principal,command.scope_ref,command.idempotency_key]))
        fingerprint=digest(canonical([claim,context,creation,deadline_ms,self.selection]))
        with closing(self._connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT * FROM nal_priors WHERE id=?',(identity,)).fetchone()
            if old:
                require(old['fingerprint']==fingerprint,'CONFLICT');return json.loads(old['snapshot'])
            require(time.time_ns()//1_000_000<=deadline_ms,'DEADLINE_EXCEEDED')
            current=self._snapshot(db,claim,context)
            prior=next((x for x in current['supports'] if x['kind']=='prior'),None)
            expected=c.prior_id(claim,context,creation)
            if prior: require(prior['id']==expected,'CONFLICT')
            else:
                require(current['revision']==0,'CONFLICT')
                prior=dict(id=expected,claim=claim,context=context,truth=c.stv('1.0','0.5'),evidence_ids=[],
                    lineage_roots=[],coverage=[],premises=[],formula=None,assumptions=[c.PRIOR],kind='prior',creation=creation)
                current.update(revision=1,supports=[prior],aggregate=expected,truth=prior['truth'])
                c.snapshot(current,claim,context,self.runtime_selection)
                super()._authorize(command.scope_ref,'registerPrior')
                require(time.time_ns()//1_000_000<=deadline_ms,'DEADLINE_EXCEEDED')
                db.execute('INSERT INTO snapshots VALUES(?,?,?)',(self._key(claim,context),1,canonical(current).decode()))
            db.execute('INSERT INTO nal_priors VALUES(?,?,?)',(identity,fingerprint,canonical(current).decode()))
        self.hook('after_prior_commit'); return current

    def _admit(self,snapshot,request,record):
        require(record is not None,'INVALID_ARGUMENT')
        identity=c.contribution(record)
        old=next((x for x in snapshot['observations'] if x['contribution']==identity),None)
        if old:
            require(old['truth']==record['event']['numerical']['truth'],'CONFLICT')
            return next((x for x in snapshot['supports'] if x['id']==old['support_id']),None),False
        require(len(snapshot['observations'])<c.MAX_SUPPORTS,'OVERLOADED')
        numeric=record['event']['numerical'];support=None
        if record['lineage_roots']:
            support=dict(id=identity,claim=request.claim,context=request.context,truth=numeric['truth'],
                evidence_ids=[digest(canonical(request.evidence))],lineage_roots=record['lineage_roots'],coverage=[identity],
                premises=[],formula=None,assumptions=[],kind='observation')
            c.support(support,request.command.scope_ref); snapshot['supports'].append(support)
        snapshot['observations'].append(dict(evidence=request.evidence,relationship=numeric['relationship'],truth=numeric['truth'],
            support_id=identity if support else None,lineage_roots=record['lineage_roots'],contribution=identity))
        return support,True

    def _reserve(self,request):
        principal=self._authorize(request.command.scope_ref,'submitEvidence',request.independence is not None)
        identity=digest(canonical([principal,request.command.scope_ref,request.work_id]))
        binding=canonical([request.claim,request.context,request.evidence,request.deadline_ms,request.max_evaluations,
            request.profile,request.runtime_selection]).decode()
        with closing(self._connect()) as db,db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT * FROM nal_budgets WHERE id=?',(identity,)).fetchone()
            if old: require(old['binding']==binding,'CONFLICT')
            else: db.execute('INSERT INTO nal_budgets VALUES(?,?,0)',(identity,binding))
            used=0 if old is None else old['evaluations'];require(used<request.max_evaluations,'OVERLOADED')
            db.execute('UPDATE nal_budgets SET evaluations=evaluations+1 WHERE id=?',(identity,))
        self.hook('after_nal_reservation')

    def _calculate(self,snapshot,request,record):
        candidate,added=self._admit(snapshot,request,record);changed=added
        require(any(x['kind']=='prior' for x in snapshot['supports']),'CONFLICT')
        numerical,detail='no-change','same underlying contribution; no new evidence'
        if candidate is None: numerical,detail='retained-alternative','unknown source lineage; no numerical support'
        elif added:
            aggregate=next(x for x in snapshot['supports'] if x['id']==snapshot['aggregate'])
            if request.independence is not None:
                require(set(request.independence['supports'])=={aggregate['id'],candidate['id']},'CONFLICT')
            if request.independence is None or set(aggregate['lineage_roots']) & set(candidate['lineage_roots']):
                numerical,detail='retained-alternative','missing assumption or overlapping lineage'
            else:
                self._reserve(request)
                result=c.response_copy(self.math.revise(aggregate,candidate,snapshot['revision'],request.independence,deadline_ms=request.deadline_ms))
                c.response(c.math_result,result,aggregate,candidate,request.independence)
                if result['proposal'] is not None:
                    self.hook('after_formula');p=result['proposal']
                    require(len(snapshot['supports'])<c.MAX_SUPPORTS*2,'OVERLOADED')
                    snapshot['supports'].append(p);snapshot.update(aggregate=p['id'],truth=p['truth'],covered_supports=p['coverage'])
                    numerical,detail='revised','pinned native NAL; compatibility prior explicitly included'
                else:numerical,detail='retained-alternative',result['detail']
        elif request.independence is not None:
            require(set(request.independence['supports'])=={snapshot['aggregate'],candidate['id']},'CONFLICT')
        snapshot['alternatives']=sorted(x['id'] for x in snapshot['supports'] if x['kind']=='observation' and x['id'] not in snapshot['covered_supports'])
        if changed:snapshot['revision']+=1
        return candidate,added,numerical,detail,changed
