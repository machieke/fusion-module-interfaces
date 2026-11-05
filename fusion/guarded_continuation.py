"""Guarded recipe facet of the existing native session/continuation owner.

One explicit advance can admit one existing native input. This is no scheduler
or execution framework. Owner observations, reservations, amendments and human
decisions commit independently. Recovery never resubmits an uncertain input.
"""
from contextlib import contextmanager
import fcntl,json,os,time,uuid
from .contracts import ContractError,canonical,digest,require
from .lookup_contracts import identity as uid
from .workflow_prerequisites import condition,PROFILE as GUARDS
from .workflow_recipes import definition,validate_steps,render,native_object

PROFILE='guarded-native-continuation/1'
LIMITS=dict(workflows=8,steps=8,observations=64,amendments=4,checkpoints=8,
    lifetime_ms=3600000,metadata_bytes=8388608,completion_reserved_bytes=600000,output_bytes=98304)
TABLES=('pilot_workflows','pilot_workflow_versions','pilot_workflow_steps',
        'pilot_workflow_observations','pilot_workflow_checkpoints')
TERMINAL=('expired-before-start','cancelled-before-start','rejected')


def text(value,maximum=128):
    require(type(value) is str and 0<len(value.encode())<=maximum and '\x00' not in value); return value


def guard_spec(spec,scope,predecessors):
    if type(spec) is dict and set(spec)=={'id','from_capture','kind'}:
        text(spec['id'],64); require(spec['kind']=='memory-active' and spec['from_capture'] in predecessors)
    else:condition(spec,scope)


class Workflow:
    def __init__(self,store,principal,observations,authorize,*,wake=lambda _:None,
                 clock=lambda:time.time_ns()//1000000,hook=lambda _:None,initialize=True,observation_only=False):
        self.store,self.db,self.principal=store,store.db,principal
        self.observations,self.authorize,self.wake=observations,authorize,wake
        self.clock,self.hook,self.observation_only=clock,hook,observation_only
        if initialize:
            require(not observation_only,'UNAUTHORIZED')
            self.db.executescript('''
            CREATE TABLE IF NOT EXISTS pilot_workflows(id TEXT PRIMARY KEY,session TEXT NOT NULL,scope TEXT NOT NULL,
              accepted TEXT NOT NULL,version INTEGER NOT NULL,deadline INTEGER NOT NULL,selection TEXT NOT NULL,
              observations INTEGER NOT NULL DEFAULT 0,reservations INTEGER NOT NULL DEFAULT 0,
              last_ms INTEGER NOT NULL,status TEXT NOT NULL,hold TEXT);
            CREATE TABLE IF NOT EXISTS pilot_workflow_versions(workflow TEXT NOT NULL,version INTEGER NOT NULL,
              identity TEXT NOT NULL,plan TEXT NOT NULL,cause TEXT NOT NULL,inherited TEXT NOT NULL,
              PRIMARY KEY(workflow,version),UNIQUE(workflow,identity));
            CREATE TABLE IF NOT EXISTS pilot_workflow_steps(workflow TEXT NOT NULL,node TEXT NOT NULL,version INTEGER NOT NULL,
              input_id TEXT NOT NULL,command TEXT NOT NULL,deadline INTEGER NOT NULL,vector TEXT NOT NULL,
              receipt TEXT,result_digest TEXT,terminal TEXT,PRIMARY KEY(workflow,node));
            CREATE TABLE IF NOT EXISTS pilot_workflow_observations(workflow TEXT NOT NULL,sequence INTEGER NOT NULL,
              node TEXT NOT NULL,declared TEXT NOT NULL,value TEXT,PRIMARY KEY(workflow,sequence));
            CREATE TABLE IF NOT EXISTS pilot_workflow_checkpoints(workflow TEXT NOT NULL,identity TEXT NOT NULL,
              binding TEXT NOT NULL,decision TEXT,PRIMARY KEY(workflow,identity));''')

    def _mutate(self):require(not self.observation_only,'UNAUTHORIZED')

    def _state(self,workflow,action='observe'):
        uid(workflow); row=self.db.execute('SELECT * FROM pilot_workflows WHERE id=?',(workflow,)).fetchone()
        require(row is not None,'NOT_FOUND'); self.authorize(action,row['scope'])
        allocation=self.store.allocated(self.principal,row['session'])
        require(allocation['frozen']['scope']==row['scope'],'CONFLICT')
        require(row['selection']==canonical(self.observations.selections).decode(),'CONFLICT')
        accepted=json.loads(row['accepted'])
        require(accepted['profile']==PROFILE and accepted['limits']==LIMITS and
                accepted['recipe']==definition(accepted['recipe']['recipe']) and
                accepted['deadline_ms']==row['deadline'] and accepted['scope']==row['scope'] and
                accepted['session']==row['session'] and accepted['principal']==self.principal,'CONFLICT')
        return row

    def _now(self,row,*,effect=False):
        now=self.clock(); require(type(now) is int and now>=row['last_ms'],'CONFLICT')
        if effect:require(now<row['deadline'],'DEADLINE_EXCEEDED')
        self.db.execute('UPDATE pilot_workflows SET last_ms=? WHERE id=?',(now,row['id'])); return now

    def _plan(self,row):
        raw=self.db.execute('SELECT plan FROM pilot_workflow_versions WHERE workflow=? AND version=?',(row['id'],row['version'])).fetchone()
        require(raw is not None,'NOT_AVAILABLE'); return json.loads(raw[0])

    def _steps(self,workflow):
        return {x['node']:x for x in self.db.execute('SELECT * FROM pilot_workflow_steps WHERE workflow=?',(workflow,))}

    def capacity(self):
        total=sum(sum(len(canonical(dict(row))) for row in self.db.execute('SELECT * FROM '+table)) for table in TABLES)
        active=self.db.execute("SELECT count(*) FROM pilot_workflows WHERE status NOT IN ('complete','refused')").fetchone()[0]
        return dict(profile=PROFILE,logical_bytes=total,completion_reserved_bytes=active*LIMITS['completion_reserved_bytes'],
                    limits=dict(LIMITS),physical_bytes='NOT_INFERRED',reservations_refunded=False)

    def _capacity(self):
        value=self.capacity(); require(value['logical_bytes']+value['completion_reserved_bytes']<=LIMITS['metadata_bytes'],'OVERLOADED')
        self.store._check_bytes()

    def admit(self,workflow,session,recipe,steps,deadline):
        self._mutate(); uid(workflow); uid(session); selected=definition(recipe); validate_steps(recipe,steps)
        require([x['node'] for x in steps]==[x['id'] for x in selected['nodes']])
        allocation=self.store.allocated(self.principal,session); scope=allocation['frozen']['scope']; self.authorize('admit',scope)
        require(scope==self.observations.scope and scope.startswith('synthetic-'),'UNAUTHORIZED'); seen=[]
        for step in steps:
            for guard in step['guards']:guard_spec(guard,scope,seen)
            require(len({g['id'] for g in step['guards']})==len(step['guards'])); seen.append(step['node'])
        require(type(deadline) is int and 0<deadline<2**53)
        accepted=dict(profile=PROFILE,session=session,recipe=selected,steps=steps,deadline_ms=deadline,
            principal=self.principal,scope=scope,limits=dict(LIMITS),effect_limit=len(steps)); wire=canonical(accepted).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); old=self.db.execute('SELECT * FROM pilot_workflows WHERE id=?',(workflow,)).fetchone()
            if old:require(old['accepted']==wire,'CONFLICT'); self._state(workflow,'admit')
            else:
                now=self.clock(); require(now<deadline<=min(now+LIMITS['lifetime_ms'],allocation['expires_ms']),'DEADLINE_EXCEEDED')
                require(self.db.execute('SELECT count(*) FROM pilot_workflows').fetchone()[0]<LIMITS['workflows'],'OVERLOADED')
                self.db.execute('INSERT INTO pilot_workflows(id,session,scope,accepted,version,deadline,selection,last_ms,status) VALUES(?,?,?,?,1,?,?,?,?)',
                    (workflow,session,scope,wire,deadline,canonical(self.observations.selections).decode(),now,'ready'))
                self.db.execute('INSERT INTO pilot_workflow_versions VALUES(?,1,?,?,?,?)',(workflow,'original',canonical(steps).decode(),
                    'original-admission',canonical(dict(deadline_ms=deadline,effect_limit=len(steps),observations_limit=LIMITS['observations'],
                    original_digest=digest(wire.encode()))).decode())); self._capacity()
        self.hook('after_workflow_admission'); return self.observe(workflow)

    def _input(self,row,step):
        after=0
        for _ in range(32):
            observed=self.store.observe(self.principal,row['session'],True,after=after)
            found=[x for x in observed['inputs'] if x['id']==step['input_id']]
            if found:
                value=found[0]; require(value['deadline']==step['deadline'] and value['payload']==dict(text=step['command'],assignment='synthetic-task'),'CONFLICT')
                return value
            if observed['complete']:return None
            require(type(observed['next_after']) is int and observed['next_after']>after,'NOT_AVAILABLE'); after=observed['next_after']
        require(False,'OVERLOADED')

    def _capture(self,row,step):
        value=self._input(row,step)
        if value is None:return None
        receipt=self.store.receipt(value); fingerprint=digest(canonical(value['result'])) if value.get('result') is not None else None
        require(fingerprint is None or value['state']=='complete','NOT_AVAILABLE')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); self._state(row['id']); current=self._steps(row['id'])[step['node']]
            require(current['result_digest'] in (None,fingerprint),'CONFLICT')
            self.db.execute('UPDATE pilot_workflow_steps SET receipt=?,result_digest=?,terminal=? WHERE workflow=? AND node=?',
                (canonical(receipt).decode(),fingerprint,value['state'] if value['state'] in TERMINAL else None,row['id'],step['node']))
        self.hook('after_workflow_result_observation'); return value

    def _captured(self,row):
        result={}
        for node,step in self._steps(row['id']).items():
            if step['result_digest'] is not None:
                value=self._input(row,step); require(value is not None and digest(canonical(value['result']))==step['result_digest'],'NOT_AVAILABLE')
                result[node]=value['result']
        return result

    def _task_result(self,row,publication):
        # The origin table belongs to this SAME session owner. Foreign task
        # bytes are hydrated only through AtomStorage and the existing codec.
        from .preview_tasks import record,correlated
        from .preview_native_history import read_body
        require(publication.get('status')=='TASK_PUBLISHED','NOT_AVAILABLE')
        self.store._session(self.principal,row['session'],'session.disclose')
        found=[]
        for item in self.db.execute("SELECT o.origin FROM preview_input_origins o JOIN preview_inputs i ON i.session=o.session AND i.id=o.id WHERE i.session=? AND i.state='complete' AND i.result IS NOT NULL",(row['session'],)):
            origin=json.loads(item[0]);body=origin.get('record',{})
            if body.get('kind')=='result' and body.get('id')==publication['task']:found.append(origin)
        require(len(found)==1,'NOT_AVAILABLE' if not found else 'CONFLICT')
        require(self.observations.atoms is not None,'NOT_AVAILABLE');atoms=self.observations.atoms(row['deadline'])
        origin=found[0];body=record(read_body(atoms,origin['ref'])['body'],row['scope'])
        require(body==origin['record'] and body['recipient']==self.principal and body['task']==publication['ref'],'UNAUTHORIZED')
        task=record(read_body(atoms,publication['ref'])['body'],row['scope']);correlated(body,task,publication['ref'])
        for ref in body['payloads']:atoms.get(ref)
        require(body['status']=='captured-native-query','NOT_AVAILABLE');return body['projection']

    def _guard(self,spec,captured,scope):
        if 'from_capture' not in spec:return spec
        require(spec['from_capture'] in captured,'NOT_AVAILABLE'); value=native_object(captured[spec['from_capture']])
        require(value.get('status') in ('REMEMBER-SUCCESS','MEMORY-SUPERSEDED'),'NOT_AVAILABLE')
        from .preview_lifecycle import PROFILE as MEMORY
        return condition(dict(id=spec['id'],kind='memory-active',policy=MEMORY,scope=scope,target=dict(
            logical_id=value['logical_id'],revision=value['revision'],payload=value['memory']['target']['payload']),predicate=None),scope)

    def _vector(self,row,step,captured):
        values=[]
        for declared in step['guards']:
            declared=self._guard(declared,captured,row['scope'])
            with self.db:
                self.db.execute('BEGIN IMMEDIATE'); current=self._state(row['id'],'advance'); self._now(current,effect=True)
                require(current['observations']<LIMITS['observations'],'OVERLOADED'); sequence=current['observations']+1
                self.db.execute('UPDATE pilot_workflows SET observations=? WHERE id=?',(sequence,row['id']))
                self.db.execute('INSERT INTO pilot_workflow_observations VALUES(?,?,?,?,NULL)',(row['id'],sequence,step['node'],canonical(declared).decode()))
            self.hook('after_workflow_observation_reservation'); value=self.observations.observe(declared,row['deadline'])
            with self.db:
                self.db.execute('BEGIN IMMEDIATE'); current=self._state(row['id'],'advance'); self._now(current)
                self.db.execute('UPDATE pilot_workflow_observations SET value=? WHERE workflow=? AND sequence=?',(canonical(value).decode(),row['id'],sequence))
            # Keep references to full bounded owner observations in this same owner.
            values.append(dict(sequence=sequence,state=value['state'],condition_sha256=value['condition_sha256'],
                observation_sha256=digest(canonical(value)),observed_ms=value['observed_ms'],error=value['error']))
        return dict(profile=GUARDS,observations=values,satisfied=all(x['state']=='SATISFIED' for x in values),
            global_atomic_snapshot=False,race_window='owner-observation-to-native-owner-admission')

    @contextmanager
    def gate(self):
        fd=os.open(str(self.store.path)+'.workflow.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ContractError('OVERLOADED') from None
            yield
        finally:os.close(fd)

    def advance(self,workflow,expected_version):
        self._mutate()
        with self.gate():return self._advance(workflow,expected_version)

    def _advance(self,workflow,expected_version):
        row=self._state(workflow,'advance'); require(row['version']==expected_version,'CONFLICT')
        plan,started=self._plan(row),self._steps(workflow)
        # Observing started work remains useful after expiry; it never resubmits.
        for step in plan:
            saved=started.get(step['node'])
            if saved and saved['result_digest'] is None:
                self._capture(row,saved); return self.observe(workflow)
        if row['status']=='refused':return self.observe(workflow)
        pending=next((x for x in plan if x['node'] not in started),None)
        if pending is None:
            with self.db:self.db.execute("UPDATE pilot_workflows SET status='complete' WHERE id=?",(workflow,))
            return self.observe(workflow)
        require(row['hold'] is None,'NOT_AVAILABLE')
        with self.db:self._now(row,effect=True)
        captured=self._captured(row); vector=self._vector(row,pending,captured)
        if not vector['satisfied']:
            with self.db:self.db.execute("UPDATE pilot_workflows SET status='prerequisite-held' WHERE id=?",(workflow,))
            return dict(self.observe(workflow),latest_prerequisites=vector)
        if pending['checkpoint']:
            approvals=[json.loads(x[0]) for x in self.db.execute('SELECT decision FROM pilot_workflow_checkpoints WHERE workflow=? AND decision IS NOT NULL',(workflow,))]
            require(any(x['action']=='approve' and x['version']==row['version'] and x['node']==pending['node'] and x['effective'] for x in approvals),'NOT_AVAILABLE')
        for argument in pending['arguments']:
            if type(argument) is dict and argument['field']=='task-result':
                source=captured[argument['capture']]
                source['_task_result']=self._task_result(row,native_object(source))
        command=render(pending,captured)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE'); current=self._state(workflow,'advance'); now=self._now(current,effect=True)
            require(current['version']==expected_version and current['hold'] is None and current['status']!='refused','CONFLICT')
            require(current['reservations']<json.loads(current['accepted'])['effect_limit'],'OVERLOADED')
            session=self.store._session(self.principal,row['session'],'input.accept'); limits=json.loads(session['binding'])['limits']
            deadline=min(row['deadline'],now+limits['timeout_ms']); input_id=str(uuid.uuid5(uuid.UUID(workflow),'native/'+pending['node']))
            self.db.execute('INSERT INTO pilot_workflow_steps(workflow,node,version,input_id,command,deadline,vector) VALUES(?,?,?,?,?,?,?)',
                (workflow,pending['node'],expected_version,input_id,command,deadline,canonical(vector).decode()))
            self.db.execute("UPDATE pilot_workflows SET reservations=reservations+1,status='inflight' WHERE id=?",(workflow,))
        self.hook('after_workflow_input_reservation')
        self.store.submit(self.principal,row['session'],input_id,command,'synthetic-task',deadline_ms=deadline)
        self.hook('after_workflow_native_acceptance')
        try:self.wake(row['session'])
        except (OSError,RuntimeError,ContractError):pass
        self._capture(row,self._steps(workflow)[pending['node']]); return self.observe(workflow)

    def amend(self,workflow,identity,expected_version,suffix,cause):
        self._mutate(); text(identity); text(cause,512)
        with self.gate(),self.db:
            self.db.execute('BEGIN IMMEDIATE'); row=self._state(workflow,'amend')
            prior=self.db.execute('SELECT * FROM pilot_workflow_versions WHERE workflow=? AND identity=?',(workflow,identity)).fetchone()
            if prior:
                expected=json.loads(prior['inherited']); require(expected['predecessor']==expected_version and expected['suffix']==suffix and prior['cause']==cause,'CONFLICT')
                return self.observe(workflow)
            require(row['version']==expected_version and expected_version<=LIMITS['amendments'],'CONFLICT')
            require(row['status'] not in ('refused','complete'),'NOT_AVAILABLE'); self._now(row,effect=True)
            old,started=self._plan(row),self._steps(workflow); prefix=[x for x in old if x['node'] in started]
            require([x['node'] for x in old[:len(prefix)]]==[x['node'] for x in prefix],'CONFLICT')
            accepted=json.loads(row['accepted']); validate_steps(accepted['recipe']['recipe'],prefix+suffix)
            require(len(suffix)<=accepted['effect_limit']-row['reservations'],'OVERLOADED'); seen=[x['node'] for x in prefix]
            for step in suffix:
                require(step['node'] not in started,'CONFLICT')
                for guard in step['guards']:guard_spec(guard,row['scope'],seen)
                seen.append(step['node'])
            inherited=dict(predecessor=expected_version,suffix=suffix,deadline_ms=row['deadline'],
                original_sha256=digest(row['accepted'].encode()),reservations_spent=row['reservations'],observations_spent=row['observations'],
                selected_step_digests={k:digest(canonical(dict(v))) for k,v in started.items()})
            self.db.execute('INSERT INTO pilot_workflow_versions VALUES(?,?,?,?,?,?)',(workflow,expected_version+1,identity,
                canonical(prefix+suffix).decode(),cause,canonical(inherited).decode()))
            self.db.execute("UPDATE pilot_workflows SET version=?,hold=NULL,status='ready' WHERE id=?",(expected_version+1,workflow)); self._capacity()
        self.hook('after_workflow_amendment'); return self.observe(workflow)

    def checkpoint(self,workflow,identity,expected_version,reason):
        self._mutate(); text(identity); text(reason,512)
        with self.gate(),self.db:
            self.db.execute('BEGIN IMMEDIATE'); row=self._state(workflow,'checkpoint')
            old=self.db.execute('SELECT * FROM pilot_workflow_checkpoints WHERE workflow=? AND identity=?',(workflow,identity)).fetchone()
            if old:
                value=json.loads(old['binding']); require(value['version']==expected_version and value['reason']==reason,'CONFLICT'); return self.observe(workflow)
            require(row['version']==expected_version,'CONFLICT'); now=self._now(row)
            require(self.db.execute('SELECT count(*) FROM pilot_workflow_checkpoints WHERE workflow=?',(workflow,)).fetchone()[0]<LIMITS['checkpoints'],'OVERLOADED')
            started,plan=self._steps(workflow),self._plan(row); pending=next((x for x in plan if x['node'] not in started),None)
            require(pending is not None and row['hold'] is None and row['status']!='refused','NOT_AVAILABLE')
            observations=[dict(r) for r in self.db.execute('SELECT * FROM pilot_workflow_observations WHERE workflow=? ORDER BY sequence',(workflow,))]
            binding=dict(profile=PROFILE,workflow=workflow,identity=identity,version=expected_version,node=pending['node'],
                reason=reason,created_ms=now,deadline_ms=row['deadline'],scope=row['scope'],principal=self.principal,
                plan_sha256=digest(canonical(plan)),selection_sha256=digest(row['selection'].encode()),observations_sha256=digest(canonical(observations)),
                captures={k:v['result_digest'] for k,v in started.items()},actions=['approve','refuse','amend'],grants_authority=False)
            self.db.execute('INSERT INTO pilot_workflow_checkpoints VALUES(?,?,?,NULL)',(workflow,identity,canonical(binding).decode()))
            self.db.execute("UPDATE pilot_workflows SET hold=?,status='operator-held' WHERE id=?",(identity,workflow))
        self.hook('after_workflow_checkpoint'); return self.observe(workflow)

    def decide(self,workflow,checkpoint,identity,actor,binding_sha256,action):
        self._mutate(); text(identity); text(actor); require(action in ('approve','refuse'),'UNSUPPORTED_OPERATION')
        with self.gate(),self.db:
            self.db.execute('BEGIN IMMEDIATE'); row=self._state(workflow,'decide')
            saved=self.db.execute('SELECT * FROM pilot_workflow_checkpoints WHERE workflow=? AND identity=?',(workflow,checkpoint)).fetchone()
            require(saved is not None,'NOT_FOUND'); binding=json.loads(saved['binding']); require(digest(saved['binding'].encode())==binding_sha256,'CONFLICT')
            if saved['decision']:
                old=json.loads(saved['decision']); require((old['identity'],old['actor'],old['action'],old['binding_sha256'])==(identity,actor,action,binding_sha256),'CONFLICT')
                return self.observe(workflow)
            require(row['hold']==checkpoint and row['version']==binding['version'],'CONFLICT'); now=self._now(row); effective=now<row['deadline']
            value=dict(identity=identity,actor=actor,action=action,binding_sha256=binding_sha256,version=binding['version'],node=binding['node'],
                observed_ms=now,effective=effective,original_deadline_ms=row['deadline'],recheck_required=True,grants_authority=False)
            self.db.execute('UPDATE pilot_workflow_checkpoints SET decision=? WHERE workflow=? AND identity=?',(canonical(value).decode(),workflow,checkpoint))
            self.db.execute('UPDATE pilot_workflows SET hold=NULL,status=? WHERE id=?',('expired' if not effective else 'refused' if action=='refuse' else 'ready',workflow))
        self.hook('after_workflow_decision'); return self.observe(workflow)

    def observe(self,workflow):
        row=self._state(workflow); steps,plan=self._steps(workflow),self._plan(row); status=row['status']
        if any(v['result_digest'] is None for v in steps.values()):status='needs-reconciliation'
        elif self.clock()>=row['deadline'] and status!='complete':status='expired'
        checkpoints=[dict(identity=r['identity'],binding=json.loads(r['binding']),binding_sha256=digest(r['binding'].encode()),
            decision=json.loads(r['decision']) if r['decision'] else None) for r in self.db.execute('SELECT * FROM pilot_workflow_checkpoints WHERE workflow=?',(workflow,))]
        value=dict(profile=PROFILE,workflow=workflow,session=row['session'],scope=row['scope'],version=row['version'],recipe=json.loads(row['accepted'])['recipe'],
            deadline_ms=row['deadline'],status=status,plan=plan,reservations_spent=row['reservations'],observations_spent=row['observations'],limits=dict(LIMITS),
            steps={k:dict(input_id=v['input_id'],version=v['version'],deadline_ms=v['deadline'],receipt=json.loads(v['receipt']) if v['receipt'] else None,
                result_sha256=v['result_digest'],terminal=v['terminal'],prerequisite_vector=json.loads(v['vector'])) for k,v in steps.items()},checkpoints=checkpoints,
            observation_only=self.observation_only,automatic_resubmissions=0,refunded_reservations=0,global_atomic_snapshot=False,additional_live_generations=0)
        require(len(canonical(value))<=LIMITS['output_bytes'],'OVERLOADED'); return value
