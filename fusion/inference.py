"""C4: one bounded explicit workset; independent durable attempts and feedback."""
from contextlib import closing
from dataclasses import asdict
import fcntl
import json
import sqlite3
import time
from . import cognition_contracts as c
from . import attention_contracts as a
from .contracts import ContractError, canonical, digest, require
from .ports import DerivationSubmission, Mutation, Stimulus
from .responses import envelope


class InferenceOwner:
    def __init__(self, database, atoms, beliefs, attention, access, selections, *, hook=lambda stage: None):
        self.database,self.atoms,self.beliefs,self.attention,self.access=str(database),atoms,beliefs,attention,access
        self.selections=c.detached(selections);self.hook=hook
        self.parameters=attention.profile()['parameters'];a.policy(self.parameters)
        self.identity=digest(canonical([self.profile(),selections,access.selection(),attention.profile()]))
        with closing(self._connect()) as db,db:
            db.executescript('CREATE TABLE IF NOT EXISTS meta(identity TEXT); CREATE TABLE IF NOT EXISTS steps(id TEXT PRIMARY KEY, fingerprint TEXT, value TEXT);')
            row=db.execute('SELECT identity FROM meta').fetchone()
            if row: require(row[0]==self.identity,'UNSUPPORTED_PROFILE')
            else: db.execute('INSERT INTO meta VALUES(?)',(self.identity,))

    def profile(self): return {'profile':c.CONTROL,'rule':c.RULE,'feedback_amount':'1','max_steps':c.MAX_STEPS,'max_tasks':c.MAX_TASKS}

    def _connect(self):
        db=sqlite3.connect(self.database,timeout=.5);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL');return db

    def _save(self, identity, fingerprint, state):
        with closing(self._connect()) as db,db:
            db.execute('INSERT OR REPLACE INTO steps VALUES(?,?,?)',(identity,fingerprint,canonical(state).decode()))

    def _result(self, state):
        return c.detached({key:state[key] for key in ('step_id','status','reason','counts','remaining','selection','results','feedback')})

    def _counts(self, state, request):
        state['remaining']={'candidates':request.budget.max_candidates-state['counts']['examined'],
                            'rule_applications':request.budget.max_rule_applications-state['counts']['reserved']}

    @c.boundary
    def step(self, request):
        semantic=c.inference(request);scope=request.command.scope_ref
        actor=self.access.authorize(scope,'step');require(request.selections==self.selections,'UNSUPPORTED_PROFILE')
        require(self.attention.profile()=={'profile':a.PROFILE,'parameters':self.parameters,'policy':a.policy(self.parameters)},'UNSUPPORTED_PROFILE')
        identity=digest(canonical([actor,scope,request.command.idempotency_key]));fingerprint=digest(canonical([semantic,self.identity]))
        # One local worker per owner. Lock is released by the OS on process death.
        with open(self.database+'.lock','a+b') as lock:
            try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise ContractError('NOT_AVAILABLE') from None
            with closing(self._connect()) as db:
                row=db.execute('SELECT fingerprint,value FROM steps WHERE id=?',(identity,)).fetchone()
                if row:
                    require(row[0]==fingerprint,'CONFLICT');state=json.loads(row[1])
                else:
                    require(db.execute('SELECT count(*) FROM steps').fetchone()[0]<c.MAX_STEPS,'OVERLOADED')
                    state={'step_id':identity,'semantic':semantic,'status':'pending','reason':'new','selection':None,
                        'entries':None,'cursor':0,'attempt':None,'results':[],'feedback':[],
                        'counts':{'examined':0,'reserved':0,'completed':0,'refused':0,'unique_admissions':0,
                                  'duplicate_admissions':0,'feedback_applied':0,'feedback_duplicate':0},'remaining':{}}
                    self._counts(state,request);self._save(identity,fingerprint,state)
            if state['status']=='complete': return self._result(state)
            def save():
                self.access.authorize(scope,'step');self._counts(state,request);self._save(identity,fingerprint,state)
            def stop(reason, terminal=True):
                state.update(status='complete' if terminal else 'pending',reason=reason);save();return self._result(state)
            def expired(): return time.time()*1000>=request.budget.deadline_ms
            if state['selection'] is None:
                if expired():return stop('deadline')
                value=self.atoms.get(request.workset);envelope(value,request.workset)
                require(value.content_type=='application/fusion-workset');record=json.loads(value.bytes);c.workset(record,scope,request.context)
                eligible=tuple(e['task'] for e in record['tasks'])
                selection=c.response_copy(self.attention.select(scope,request.context,eligible,len(eligible)))
                c.response(a.selection,selection,scope,request.context,eligible,len(eligible),self.parameters)
                state['selection']=selection
                state['entries']=[next(e for e in record['tasks'] if e['task']==r['target']) for r in selection['ranked']]
                save()
            while True:
                # Recover a committed C2 decision before deciding whether any new dispatch is affordable.
                if state['attempt'] is not None:
                    attempt=state['attempt'];decision=self.beliefs.readDerivation(scope,attempt['command']['idempotency_key'])
                    if decision is not None and decision.get('state') == 'pending':
                        c.response(c.fields, decision, 'state decision_id')
                        expected=digest(canonical([actor,scope,attempt['command']['idempotency_key']]))
                        require(decision['decision_id']==expected,'NOT_AVAILABLE')
                    if decision is not None and decision.get('state') not in ('pending',):
                        if decision.get('state')=='error' and decision.get('code') in ('NOT_AVAILABLE','OVERLOADED'):
                            return stop('provider-unavailable')
                        self._accept(state,decision,attempt,request);state['attempt']=None;save()
                    elif expired():return stop('deadline')
                    elif state['remaining']['rule_applications']==0:return stop('rule-budget')
                    else:
                        # Unknown/pending physical work is never retried under its old attempt key.
                        state['attempt']=None;save()
                pending=next((f for f in state['feedback'] if f['state']=='pending'),None)
                if pending:
                    if expired():return stop('deadline')
                    try:
                        stimulus=Stimulus(**{**pending['request'],'command':Mutation(**pending['request']['command'])})
                        receipt=c.response_copy(self.attention.submitStimulus(stimulus));c.response(a.receipt,receipt,stimulus,self.parameters)
                        self.hook('after_feedback_commit')
                        pending.update(state='complete',receipt=receipt);state['counts']['feedback_applied']+=1;save()
                    except ContractError as error:
                        if error.code in ('UNAUTHORIZED','UNSUPPORTED_PROFILE'):raise
                        pending['last_error']=error.code;save();return stop('feedback-unavailable',False)
                    continue
                if state['cursor']>=len(state['entries']):return stop('workset-exhausted')
                if expired():return stop('deadline')
                entry=state['entries'][state['cursor']]
                # Candidate counted once, before resolution, including every rejected task.
                if not entry.get('examined'):
                    if state['remaining']['candidates']==0:return stop('candidate-budget')
                    entry['examined']=True;state['counts']['examined']+=1;save()
                if state['remaining']['rule_applications']==0:return stop('rule-budget')
                try:
                    value=self.atoms.get(entry['task']);envelope(value,entry['task']);require(value.content_type=='application/fusion-task')
                    task=json.loads(value.bytes);c.manifest(task,scope,request.context)
                    snapshot=c.snapshot_reply(self.beliefs.readBelief(task['roles']['pr'],request.context,None),task['roles']['pr'],request.context)
                except ContractError as error:
                    if error.code in ('UNAUTHORIZED','UNSUPPORTED_PROFILE'):raise
                    if error.code in ('NOT_AVAILABLE','OVERLOADED'):return stop('provider-unavailable',False)
                    state['counts']['refused']+=1;state['results'].append({'task':entry['task'],'state':'refused','code':error.code});state['cursor']+=1;save();continue
                if expired():return stop('deadline')
                slot=state['counts']['reserved']+1
                attempt=DerivationSubmission(Mutation(scope,'inference/'+identity+'/'+str(slot)),entry['task'],request.context,
                    tuple(entry['premises']),snapshot['revision'],c.BELIEF_PROFILE,self.selections['kernel'],request.budget.deadline_ms)
                entry['output_claim']=task['roles']['pr']
                state['attempt']=asdict(attempt);state['counts']['reserved']=slot;save()
                self.hook('after_attempt_reservation')
                try: decision=self.beliefs.submitDerivation(attempt)
                except ContractError as error:
                    if error.code in ('UNAUTHORIZED','UNSUPPORTED_PROFILE'):raise
                    # C2 may have a committed refusal/error; the next pass reads it before allocating again.
                    if error.code in ('NOT_AVAILABLE','OVERLOADED'):return stop('provider-unavailable',False)
                    continue
                self._accept(state,decision,state['attempt'],request);state['attempt']=None;save()

    def _accept(self,state,decision,attempt,request):
        """Validate C2 response before progress/feedback. Never mutate another owner."""
        scope=request.command.scope_ref
        require(type(decision) is dict,'NOT_AVAILABLE')
        expected=digest(canonical([self.access.authorize(scope,'step'),scope,attempt['command']['idempotency_key']]))
        require(decision.get('decision_id')==expected,'NOT_AVAILABLE')
        if decision.get('state')=='complete':
            c.response(c.fields,decision,'state decision_id logical_id admission numerical snapshot')
            logical=c.logical_id(attempt['task'],attempt['premises'],self.selections['kernel'])
            require(decision['logical_id']==logical and decision['admission'] in ('admitted','duplicate'),'NOT_AVAILABLE')
            require(decision['numerical'] in ('initialized','retained-alternative','no-change'),'NOT_AVAILABLE')
            snapshot=decision['snapshot'];expected_claim=state['entries'][state['cursor']]['output_claim']
            c.snapshot_reply(snapshot,expected_claim,request.context)
            require(any(s['id']==logical for s in snapshot['supports']),'NOT_AVAILABLE')
            state['counts']['completed']+=1
            if decision['admission']=='admitted':
                state['counts']['unique_admissions']+=1
                selected=state['selection']['ranked'][state['cursor']];generation=selected['generation']+1
                if generation<=min(request.budget.max_feedback_generation,self.parameters['max_feedback_generation']):
                    feedback=Stimulus(Mutation(scope,'feedback/'+digest(logical.encode())),request.context,attempt['task'],'1',logical,
                        generation,a.policy(self.parameters),state['selection']['logical_step'],'feedback',selected['cause'])
                    state['feedback'].append({'state':'pending','request':asdict(feedback)})
                else:state['feedback'].append({'state':'generation-limit','logical_id':logical})
            else:
                state['counts']['duplicate_admissions']+=1
                state['counts']['feedback_duplicate']+=1
            state['results'].append({'task':attempt['task'],'state':'complete','logical_id':logical,'admission':decision['admission']})
        elif decision.get('state')=='refused':
            c.response(c.fields,decision,'state decision_id logical_id status detail')
            require(decision['logical_id']==c.logical_id(attempt['task'],attempt['premises'],self.selections['kernel']),'NOT_AVAILABLE')
            require(decision['status'] in ('FAIL','UNKNOWN'),'NOT_AVAILABLE')
            state['counts']['refused']+=1;state['results'].append({'task':attempt['task'],'state':'refused','status':decision['status']})
        elif decision.get('state')=='error':
            c.response(c.fields,decision,'state decision_id code')
            require(decision['code'] not in ('UNAUTHORIZED','UNSUPPORTED_PROFILE'),decision['code'])
            state['counts']['refused']+=1;state['results'].append({'task':attempt['task'],'state':'error','code':decision['code']})
        else:raise ContractError('NOT_AVAILABLE')
        state['cursor']+=1
