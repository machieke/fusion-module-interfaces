"""One fixed application continuation from captured inspection to approved chain.

This facet shares the caller's existing database. It never signs or reads another
owner's state. A new, explicit exact-result approval admits the second graph; it
does not renew the completed native occurrence or preapprove an unknown digest.
Only one submit may be reserved, and recovery performs bounded owner reads.
"""
import fcntl,json,os,time
from contextlib import contextmanager
from pathlib import Path
from .contracts import canonical,digest,require,label,ContractError
from .preview_chain import registration

PROFILE='bounded-approved-chain-continuation/1'
LIMITS=dict(nodes=5,edges=4,depth=5,inflight=1,submit=1,observations=16,
    window_ms=1200000,output_bytes=32768,continuations=128)
DEFINITION=dict(profile=PROFILE,handler='approved-native-inspection-chain/1',
    nodes=['native-capture','exact-approval','submit-reserved','signed-intent','chain-observation'],
    edges=[['native-capture','exact-approval'],['exact-approval','submit-reserved'],
           ['submit-reserved','signed-intent'],['signed-intent','chain-observation']],
    limits=LIMITS,mappings='exact-captured-inspection-and-operator-registration/1',
    recovery='intent-and-observe-only',new_authority='separate-exact-result-window',
    original_native_bounds='unchanged',observation_after_deadline='local-captures-only')


class Continuation:
    def __init__(self,db,client,authorize,*,clock=lambda:time.time_ns()//1000000,hook=lambda _:None,initialize=True):
        self.db,self.client,self.authorize,self.clock,self.hook=db,client,authorize,clock,hook
        if initialize:
            self.db.executescript('''CREATE TABLE IF NOT EXISTS integrated_chain_continuations(
                occurrence TEXT PRIMARY KEY,identity TEXT UNIQUE NOT NULL,definition TEXT NOT NULL,
                binding TEXT NOT NULL,origin TEXT NOT NULL,deadline INTEGER NOT NULL,
                submit_reserved INTEGER NOT NULL DEFAULT 0,observations INTEGER NOT NULL DEFAULT 0,
                cancelled TEXT,submission TEXT,intent TEXT,result TEXT);
                CREATE TABLE IF NOT EXISTS integrated_chain_reads(
                occurrence TEXT NOT NULL,sequence INTEGER NOT NULL,operation TEXT NOT NULL,
                PRIMARY KEY(occurrence,sequence));''')

    def origin(self,occurrence):
        """Only this application's retained native captures are authoritative here."""
        self.authorize('observe')
        row=self.db.execute('SELECT * FROM app_occurrences WHERE id=?',(occurrence,)).fetchone()
        require(row is not None and row['done'] and row['result'] is not None,'NOT_AVAILABLE')
        native=self.db.execute('SELECT * FROM preview_inspections WHERE occurrence=?',(occurrence,)).fetchone()
        graph=self.db.execute('SELECT * FROM integrated_inspection_continuations WHERE occurrence=?',(occurrence,)).fetchone()
        require(native is not None and graph is not None and graph['deadline']==row['deadline'],'NOT_AVAILABLE')
        from .inspection_continuation import STEPS,DEFINITION as NATIVE_DEFINITION
        require(graph['definition']==canonical(NATIVE_DEFINITION).decode(),'UNSUPPORTED_PROFILE')
        hashes={}
        for step in STEPS:
            require(native[step] is not None,'NOT_AVAILABLE')
            raw=canonical(json.loads(native[step]));fingerprint=digest(raw)
            saved=self.db.execute('SELECT capture_digest FROM integrated_inspection_steps WHERE occurrence=? AND step=?',(occurrence,step)).fetchone()
            require(saved is not None and saved[0]==fingerprint,'NOT_AVAILABLE');hashes[step]=fingerprint
        reg=self.client.reg;scope=reg['approved']['scope_ref'];registration(reg,scope)
        artifact=json.loads(native['artifact']);acceptance=json.loads(native['acceptance'])
        require(artifact['scope']==scope and artifact['sender']==reg['principal'] and
            json.loads(native['artifact_ref'])==reg['artifact'] and json.loads(native['result'])==reg['result'] and
            acceptance['job_id']==reg['job_id'],'UNAUTHORIZED')
        expected=dict(status='INSPECTED_ARTIFACT',task=artifact['task'],artifact=reg['artifact'],
            artifact_bytes=len(canonical(artifact)),inspection=reg['result'],job_id=reg['job_id'],
            completion=json.loads(native['completion'])['delivery_id'],caller_acknowledged=True,
            chain='NOT_SUBMITTED',approval='NOT_GRANTED')
        require(row['result']==canonical(expected).decode(),'NOT_AVAILABLE')
        turn=self.db.execute('SELECT projection FROM app_turns WHERE id=?',(row['turn'],)).fetchone()
        require(turn is not None and turn[0] is not None,'NOT_AVAILABLE')
        return dict(occurrence=occurrence,original_deadline_ms=row['deadline'],task=artifact['task'],
            capture_sha256=digest(row['result'].encode()),steps=hashes,artifact=reg['artifact'],
            result=reg['result'],job_id=reg['job_id'])

    def state(self,occurrence):
        self.authorize('observe')
        row=self.db.execute('SELECT * FROM integrated_chain_continuations WHERE occurrence=?',(occurrence,)).fetchone()
        require(row is not None,'NOT_FOUND')
        require(row['definition']==canonical(DEFINITION).decode() and row['binding']==self.client.frozen.decode(),'CONFLICT')
        require(json.loads(row['origin'])==self.origin(occurrence),'NOT_AVAILABLE')
        return row

    def admit(self,occurrence,identity,deadline,approval_sha256):
        self.authorize('admit');require(label(identity))
        require(type(deadline) is int and 0<deadline<2**53)
        require(approval_sha256==digest(canonical(self.client.reg)),'UNAUTHORIZED')
        origin=self.origin(occurrence)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=self.db.execute('SELECT * FROM integrated_chain_continuations WHERE occurrence=? OR identity=?',(occurrence,identity)).fetchone()
            if old:
                require(old['occurrence']==occurrence and old['identity']==identity and old['deadline']==deadline,'CONFLICT')
                self.state(occurrence)
            else:
                now=self.clock();expires=self.client.reg['binding']['authority']['expires_at_ms']
                require(now<deadline<=min(now+LIMITS['window_ms'],expires),'DEADLINE_EXCEEDED')
                require(self.db.execute('SELECT count(*) FROM integrated_chain_continuations').fetchone()[0]<LIMITS['continuations'],'OVERLOADED')
                self.db.execute('INSERT INTO integrated_chain_continuations(occurrence,identity,definition,binding,origin,deadline) VALUES(?,?,?,?,?,?)',
                    (occurrence,identity,canonical(DEFINITION).decode(),self.client.frozen.decode(),canonical(origin).decode(),deadline))
        self.hook('after_chain_continuation_acceptance')
        return self.observe(occurrence)

    def reserve(self,occurrence,operation):
        self.authorize('advance')
        require(operation in ('submit','intent','observe'))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');row=self.state(occurrence)
            require(self.clock()<row['deadline'],'DEADLINE_EXCEEDED')
            if operation=='submit':
                require(row['cancelled'] is None and not row['submit_reserved'],'NOT_AVAILABLE')
                self.db.execute('UPDATE integrated_chain_continuations SET submit_reserved=1 WHERE occurrence=?',(occurrence,))
            else:
                require(row['submit_reserved'] and row['observations']<LIMITS['observations'],'OVERLOADED')
                seq=row['observations']+1
                self.db.execute('UPDATE integrated_chain_continuations SET observations=? WHERE occurrence=?',(seq,occurrence))
                self.db.execute('INSERT INTO integrated_chain_reads VALUES(?,?,?)',(occurrence,seq,operation))
        self.hook('after_chain_'+operation+'_reservation')

    def capture(self,occurrence,step,value):
        require(step in ('submission','intent','result'));require(len(canonical(value))<=LIMITS['output_bytes'],'OVERLOADED')
        self.authorize('advance')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');row=self.state(occurrence)
            old=json.loads(row[step]) if row[step] else None
            if step!='result':require(old is None or old==value,'CONFLICT')
            if step=='result':
                require(row['intent'] is not None,'NOT_AVAILABLE')
                require(value['deploy_id']==json.loads(row['intent'])['deploy_id'],'NOT_AVAILABLE')
                if old and old['effect_finality'] in ('finalized','rejected'):return
            self.db.execute('UPDATE integrated_chain_continuations SET '+step+'=? WHERE occurrence=?',(canonical(value).decode(),occurrence))
        self.hook('after_chain_'+step+'_capture')

    def advance(self,occurrence):
        """At most one remote call per explicit drive, never a hidden retry loop."""
        self.authorize('advance')
        with self.gate():return self._advance(occurrence)

    @contextmanager
    def gate(self):
        # One live transition per application owner, including two concurrent
        # HTTP requests. Process loss releases the lock, not any reservation.
        database=self.db.execute('PRAGMA database_list').fetchone()[2]
        require(database,'UNSUPPORTED_PROFILE')
        path=Path(database).with_suffix('.chain-continuation.lock')
        fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        try:
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise ContractError('OVERLOADED') from None
            yield
        finally:os.close(fd)

    def _advance(self,occurrence):
        self.authorize('advance');row=self.state(occurrence)
        result=json.loads(row['result']) if row['result'] else None
        if result and result['effect_finality'] in ('finalized','rejected'):return self.observe(occurrence)
        if row['cancelled'] and not row['submit_reserved']:return self.observe(occurrence)
        if not row['submit_reserved']:
            self.reserve(occurrence,'submit')
            reg=self.client.reg
            value=self.client.call('submit',dict(command=dict(scope_ref=reg['approved']['scope_ref'],
                idempotency_key=reg['binding']['operation'],intent_digest=None)),deadline=row['deadline'])
            self.capture(occurrence,'submission',value)
        elif row['intent'] is None:
            self.reserve(occurrence,'intent');value=self.client.call('intent',{},deadline=row['deadline'])
            if value is not None:self.capture(occurrence,'intent',value)
        else:
            self.reserve(occurrence,'observe')
            value=self.client.call('observe',dict(deploy_id=json.loads(row['intent'])['deploy_id']),deadline=row['deadline'])
            self.capture(occurrence,'result',value)
        return self.observe(occurrence)

    def cancel(self,occurrence,identity):
        self.authorize('cancel');require(label(identity))
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');row=self.state(occurrence)
            require(row['cancelled'] in (None,identity),'CONFLICT')
            self.db.execute('UPDATE integrated_chain_continuations SET cancelled=? WHERE occurrence=?',(identity,occurrence))
        return self.observe(occurrence)

    def observe(self,occurrence):
        row=self.state(occurrence);result=json.loads(row['result']) if row['result'] else None
        status='accepted'
        if row['submit_reserved']:status='needs-reconciliation'
        elif row['cancelled']:status='cancelled-before-submit'
        elif self.clock()>=row['deadline']:status='expired-before-submit'
        if row['intent']:status='signed-intent-captured'
        if result:status=result['effect_finality']
        return dict(profile=PROFILE,occurrence=occurrence,identity=row['identity'],deadline_ms=row['deadline'],
            definition_sha256=digest(row['definition'].encode()),registration_sha256=digest(canonical(self.client.reg)),
            origin=json.loads(row['origin']),status=status,cancel_requested=row['cancelled'] is not None,
            submit_reservations=row['submit_reserved'],observations_spent=row['observations'],limits=dict(LIMITS),
            submission=json.loads(row['submission']) if row['submission'] else None,
            signed_intent=json.loads(row['intent']) if row['intent'] else None,result=result,
            automatic_resubmissions=0,observation_authorizes_effect=False)
