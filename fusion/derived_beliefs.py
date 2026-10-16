"""The C2 owner under an explicit new profile: observed and derived support."""
from contextlib import closing
import json
from .beliefs import BeliefOwner
from . import cognition_contracts as c
from .contracts import ContractError, canonical, digest, require
from .ports import DerivationSubmission, Mutation
from .responses import envelope
from .deadlines import remaining


class DerivedBeliefOwner(BeliefOwner):
    def __init__(self, database, atoms, episodes, access, math, kernel, *, hook=lambda stage: None):
        self.kernel=kernel;self.kernel_selection=digest(canonical(kernel.profile()))
        super().__init__(database,atoms,episodes,access,math,hook=hook,contracts=c)
        with closing(self._connect()) as db, db:
            db.executescript('CREATE TABLE IF NOT EXISTS derivations(id TEXT PRIMARY KEY, fingerprint TEXT, semantic TEXT, result TEXT); CREATE TABLE IF NOT EXISTS kernel_meta(selection TEXT);')
            row=db.execute('SELECT selection FROM kernel_meta').fetchone()
            if row: require(row[0]==self.kernel_selection,'UNSUPPORTED_PROFILE')
            else: db.execute('INSERT INTO kernel_meta VALUES(?)',(self.kernel_selection,))

    def _snapshot(self, *args, **kwargs):
        value=super()._snapshot(*args,**kwargs);value.setdefault('coverage_kind',c.COVERAGE);return value

    def _read_claim(self, claim):
        value=self.atoms.get(claim);envelope(value,claim)
        require(value.content_type=='application/fusion-claim');record=json.loads(value.bytes)
        return c.claim_literal(claim,record),record

    def _observation(self, support):
        literal,_=self._read_claim(support['claim'])
        return dict(support,kind='observation',literal=literal,ancestors=[],coverage_kind=c.COVERAGE)

    def _base_support(self, support): return support['kind']!='revision'

    def _task(self, ref, context):
        value=self.atoms.get(ref);envelope(value,ref);require(value.content_type=='application/fusion-task')
        record=json.loads(value.bytes);c.manifest(record,ref['scope_ref'],context)
        claims={role:self._read_claim(record['roles'][role])[1] for role in c.ROLES}
        result={'ref':ref,'record':record,'claims':claims};c.task(result,ref['scope_ref'],context);return result

    def _derivation_actor(self, scope, operation):
        actor=self.access.authorize(scope,operation)
        require(digest(canonical(self.kernel.profile()))==self.kernel_selection,'UNSUPPORTED_PROFILE')
        return actor

    @c.boundary
    def readDerivation(self, scope, idempotency_key):
        c.identifier(scope);c.identifier(idempotency_key);actor=self._derivation_actor(scope,'readDerivation')
        identity=digest(canonical([actor,scope,idempotency_key]))
        with closing(self._connect()) as db:
            row=db.execute('SELECT result FROM derivations WHERE id=?',(identity,)).fetchone()
        return None if row is None else json.loads(row[0]) if row[0] else {'state':'pending','decision_id':identity}

    @c.boundary
    def submitDerivation(self, request):
        semantic=c.derivation(request)
        request=DerivationSubmission(**{**semantic,'command':Mutation(**semantic['command']),'premises':tuple(semantic['premises'])})
        scope=request.command.scope_ref;actor=self._derivation_actor(scope,'submitDerivation')
        require(request.kernel_selection==self.kernel_selection,'UNSUPPORTED_PROFILE')
        identity=digest(canonical([actor,scope,request.command.idempotency_key]));fingerprint=digest(canonical([semantic,self.selection]))
        # An attempt key owns at most one evaluation opportunity, even after a crash.
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            prior=db.execute('SELECT * FROM derivations WHERE id=?',(identity,)).fetchone()
            if prior:
                require(prior['fingerprint']==fingerprint,'CONFLICT')
                require(prior['result'] is not None,'NOT_AVAILABLE')
                recorded=json.loads(prior['result'])
                if recorded['state']=='error':raise ContractError(recorded['code'])
                return recorded
            require(db.execute('SELECT count(*) FROM derivations').fetchone()[0]<1024,'OVERLOADED')
            db.execute('INSERT INTO derivations VALUES(?,?,?,NULL)',(identity,fingerprint,canonical(semantic).decode()))
        try:
            remaining(request.deadline_ms)
            task=self._task(request.task,request.context);claim=task['record']['roles']['pr']
            logical=c.logical_id(request.task,list(request.premises),self.kernel_selection)
            with closing(self._connect()) as db:
                base=self._snapshot(db,claim,request.context)
            existing=next((s for s in base['supports'] if s['id']==logical),None)
            if existing:
                result=self._decision(identity,logical,'duplicate','no-change',base)
            else:
                require(base['revision']==request.expected_revision,'CONFLICT')
                resolved=[]
                for role,binding in zip(c.ROLES,request.premises):
                    remaining(request.deadline_ms)
                    require(binding['claim']==task['record']['roles'][role],'INVALID_ARGUMENT')
                    value=c.snapshot_reply(self.readBelief(binding['claim'],request.context,binding['revision']),binding['claim'],request.context)
                    support=next((s for s in value['supports'] if s['id']==binding['support_id']),None)
                    require(support is not None,'NOT_FOUND');resolved.append({'binding':binding,'support':support})
                proposal=c.response_copy(self.kernel.applyRule(task,tuple(resolved),request.deadline_ms))
                c.response(c.kernel_result,proposal,task,tuple(resolved),self.kernel_selection)
                self.hook('after_kernel_return')
                remaining(request.deadline_ms)
                if proposal['proposal'] is None:
                    result={'state':'refused','decision_id':identity,'logical_id':logical,'status':proposal['status'],'detail':proposal['detail']}
                else:
                    working=c.detached(base);require(len(working['supports'])<c.MAX_SUPPORTS*2,'OVERLOADED')
                    support=proposal['proposal'];working['supports'].append(support);working['revision']+=1
                    numerical='retained-alternative'
                    if working['aggregate'] is None:
                        working.update(aggregate=logical,truth=support['truth'],covered_supports=[logical]);numerical='initialized'
                    working['alternatives']=sorted(s['id'] for s in working['supports'] if self._base_support(s) and s['id'] not in working['covered_supports'])
                    c.snapshot(working,claim,request.context,self.runtime_selection)
                    result=self._decision(identity,logical,'admitted',numerical,working)
            with closing(self._connect()) as db, db:
                db.execute('BEGIN IMMEDIATE');self._derivation_actor(scope,'submitDerivation')
                current=self._snapshot(db,claim,request.context)
                concurrent=next((s for s in current['supports'] if s['id']==logical),None)
                if concurrent: result=self._decision(identity,logical,'duplicate','no-change',current)
                elif result['state']=='complete':
                    require(current['revision']==base['revision'],'CONFLICT');remaining(request.deadline_ms)
                    db.execute('INSERT INTO snapshots VALUES(?,?,?)',(self._key(claim,request.context),result['snapshot']['revision'],canonical(result['snapshot']).decode()))
                db.execute('UPDATE derivations SET result=? WHERE id=?',(canonical(result).decode(),identity))
        except ContractError as error:
            # Durable controlled failure. In-flight process death leaves explicit pending.
            result={'state':'error','decision_id':identity,'code':error.code}
            with closing(self._connect()) as db, db:
                db.execute('UPDATE derivations SET result=? WHERE id=?',(canonical(result).decode(),identity))
            raise
        self.hook('after_derived_commit');return result

    def _decision(self, identity, logical, admission, numerical, snapshot):
        return {'state':'complete','decision_id':identity,'logical_id':logical,'admission':admission,
                'numerical':numerical,'snapshot':snapshot}
