"""Trusted provider admission inside the existing application inbox owner.

No discovery daemon, executable loading or effect routing. The operator's
allowlist pins implementation/endpoint/capabilities. Readiness is an expiring
observation only. Selection is frozen atomically with a new session, and never
rewrites accepted work or authorizes a retry on another owner.
"""
import json,time
from .contracts import canonical,digest,require,ContractError,label
from .registry import descriptor_read,selection_token,resolve,Requirement

PROFILE='trusted-provider-lifecycle/1'
MAX_RECORDS,MAX_ACTIONS=32,256
STATES=('admitted','enabled','disabled','draining','retired')
ACTIONS=('add','enable','disable','drain','retire')


def configuration(value):
    require(type(value) is dict and set(value)=={'profile','records','templates','readiness_ms'},'UNSUPPORTED_PROFILE')
    require(value['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    require(type(value['readiness_ms']) is int and 1<=value['readiness_ms']<=300000)
    records=value['records'];require(type(records) is dict and 1<=len(records)<=MAX_RECORDS)
    for key,r in records.items():
        require(label(key) and type(r) is dict and set(r)=={'scope','endpoint','implementation','capabilities','requirements','conformance'},'INVALID_ARGUMENT')
        require(type(r['scope']) is str and r['scope'].startswith('synthetic-'),'UNAUTHORIZED')
        ep=r['endpoint'];require(type(ep) is dict and set(ep)=={'host','port','ca_sha256'},'INVALID_ARGUMENT')
        require(label(ep['host']) and ep['host'].endswith('.svc.cluster.local'),'UNAUTHORIZED')
        require(type(ep['port']) is int and 1<=ep['port']<=65535)
        pins=r['implementation'];require(type(pins) is dict and set(pins)=={'image','source'})
        for h in (ep['ca_sha256'],pins['image'],pins['source']):
            require(type(h) is str and len(h)==64 and all(c in '0123456789abcdef' for c in h),'INVALID_ARGUMENT')
        require(type(r['capabilities']) is list and 1<=len(r['capabilities'])<=32)
        ds=[descriptor_read(d) for d in r['capabilities']]
        require(len({selection_token(d) for d in ds})==len(ds),'CONFLICT')
        require(type(r['requirements']) is list and 1<=len(r['requirements'])<=32)
        for raw in r['requirements']:
            require(type(raw) is dict and set(raw)=={'interface','minimum','maximum_exclusive','profile','operations','guarantees','privacy','features','payload_bytes'})
            req=Requirement(**{**raw,**{k:frozenset(raw[k]) for k in ('operations','guarantees','features')}})
            resolve(ds,req) # shared compatibility resolver; advertisements alone do not grant trust
        require(type(r['conformance']) is list and len(r['conformance'])<=8)
        for h in r['conformance']:require(type(h) is str and len(h)==64 and all(c in '0123456789abcdef' for c in h))
    require(type(value['templates']) is dict and 1<=len(value['templates'])<=4)
    for template,keys in value['templates'].items():
        require(label(template) and type(keys) is list and 1<=len(keys)<=MAX_RECORDS and len(keys)==len(set(keys)))
        require(all(k in records for k in keys),'NOT_AVAILABLE')
        require(len({records[k]['scope'] for k in keys})==1,'UNAUTHORIZED')
    require(len(canonical(value))<=262144,'OVERLOADED')
    return value


class Registry:
    """Uses the caller's SessionStore connection; never opens provider files."""
    def __init__(self,store,config,authorize,hook=lambda _:None):
        self.store,self.db,self.cfg,self.authorize,self.hook=store,store.db,configuration(config),authorize,hook
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS integrated_providers(id TEXT PRIMARY KEY,record TEXT NOT NULL,state TEXT NOT NULL,readiness TEXT,retained TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS integrated_provider_actions(id TEXT PRIMARY KEY,intent TEXT NOT NULL,result TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS integrated_provider_bindings(session TEXT PRIMARY KEY,selection TEXT NOT NULL);
        ''')
    def _record(self,key,op):
        require(type(key) is str and key in self.cfg['records'],'UNAUTHORIZED')
        record=self.cfg['records'][key];self.authorize(record['scope'],'providers.'+op)
        old=self.db.execute('SELECT * FROM integrated_providers WHERE id=?',(key,)).fetchone()
        if old:
            retained=json.loads(old['record'])
            # Requirements are independently resolved predicates, not a
            # preference list. Early composition iterated a frozenset of
            # profiles. Preserve the exact admitted bytes/receipts while
            # accepting only a permutation of those same predicates.
            def ordered(value):
                return {**value,'requirements':sorted(value['requirements'],key=canonical)}
            require(canonical(ordered(retained))==canonical(ordered(record)),'CONFLICT')
            record=retained
        return record,old
    def _charge(self,extra):
        require(self.db.execute('SELECT count(*) FROM integrated_provider_actions').fetchone()[0]<MAX_ACTIONS,'OVERLOADED')
        used=sum(self.db.execute(q).fetchone()[0] or 0 for q in (
            'SELECT sum(length(CAST(record AS BLOB))+coalesce(length(CAST(readiness AS BLOB)),0)) FROM integrated_providers',
            'SELECT sum(length(CAST(intent AS BLOB))+length(CAST(result AS BLOB))) FROM integrated_provider_actions',
            'SELECT sum(length(CAST(selection AS BLOB))) FROM integrated_provider_bindings'))
        require(used+extra+1024<=1048576,'OVERLOADED')
    def act(self,identity,operation,key,retained='required'):
        require(label(identity) and operation in ACTIONS,'UNSUPPORTED_OPERATION')
        require(retained in ('required','explicit-unavailable'),'UNSUPPORTED_PROFILE')
        require(operation=='retire' or retained=='required','INVALID_ARGUMENT')
        record,_=self._record(key,operation)
        intent=canonical(dict(operation=operation,provider=key,record=record,retained=retained)).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');record,row=self._record(key,operation)
            old=self.db.execute('SELECT * FROM integrated_provider_actions WHERE id=?',(identity,)).fetchone()
            if old:
                require(old['intent']==intent,'CONFLICT');return json.loads(old['result'])
            self._charge(len(intent.encode())+len(canonical(record)));now=self.store._now()
            if operation=='add':
                require(row is None,'CONFLICT')
                require(self.db.execute('SELECT count(*) FROM integrated_providers').fetchone()[0]<MAX_RECORDS,'OVERLOADED')
                state='admitted';self.db.execute('INSERT INTO integrated_providers VALUES(?,?,?,NULL,?)',(key,canonical(record).decode(),state,'required'))
            else:
                require(row is not None,'NOT_FOUND');state={'enable':'enabled','disable':'disabled','drain':'draining','retire':'retired'}[operation]
                require(row['state']!='retired','NOT_AVAILABLE')
                if operation=='enable' or (operation=='retire' and retained=='required'):self._ready(row,now)
                if operation=='retire':require(row['state'] in ('disabled','draining'),'CONFLICT')
                self.db.execute('UPDATE integrated_providers SET state=?,retained=? WHERE id=?',(state,retained,key))
            result=dict(profile=PROFILE,provider=key,state=state,retained_access=retained,
                        new_work=state=='enabled',prior_bindings_unchanged=True,observed_ms=now)
            self.authorize(record['scope'],'providers.'+operation)
            self.db.execute('INSERT INTO integrated_provider_actions VALUES(?,?,?)',(identity,intent,canonical(result).decode()))
            self.store._check_bytes()
        self.hook('after_provider_action_commit');return result
    def _ready(self,row,now):
        ready=json.loads(row['readiness']) if row['readiness'] else None
        require(ready is not None and ready['status']=='ready' and ready['observed_ms']<=now<ready['valid_until'],'NOT_AVAILABLE')
    def probe(self,identity,key,probe):
        """Server-supplied HTTPS health observer, never a wire-supplied result."""
        require(label(identity));record,row=self._record(key,'probe');require(row is not None,'NOT_FOUND')
        intent=canonical(dict(operation='probe',provider=key,record=record)).decode()
        # Reserve BEFORE the bounded network observation. Replaying an unknown
        # probe never contacts the endpoint again or renews its readiness.
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self._record(key,'probe')
            old=self.db.execute('SELECT * FROM integrated_provider_actions WHERE id=?',(identity,)).fetchone()
            if old:require(old['intent']==intent,'CONFLICT');return json.loads(old['result'])
            self._charge(len(intent.encode()));started=self.store._now()
            result=dict(profile=PROFILE,provider=key,status='unknown',observed_ms=started,valid_until=started,authority=False)
            self.db.execute('INSERT INTO integrated_provider_actions VALUES(?,?,?)',(identity,intent,canonical(result).decode()))
            self.store._check_bytes()
        self.hook('after_provider_probe_reservation')
        try:
            observed=probe(record);require(type(observed) is bool,'NOT_AVAILABLE');status='ready' if observed else 'unready'
        except (OSError,ContractError):status='unavailable'
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');self._record(key,'probe');now=self.store._now()
            result.update(status=status,observed_ms=now,valid_until=started+self.cfg['readiness_ms'])
            # Slow observations cannot extend their pre-reserved eligibility.
            if now>=result['valid_until']:result.update(status='expired',valid_until=started)
            self.db.execute('UPDATE integrated_providers SET readiness=? WHERE id=?',(canonical(result).decode(),key))
            self.db.execute('UPDATE integrated_provider_actions SET result=? WHERE id=?',(canonical(result).decode(),identity))
            self.store._check_bytes()
        self.hook('after_provider_probe_capture');return result
    def admit(self,db,template,now,session):
        """Called inside the same BEGIN IMMEDIATE as new-session acceptance."""
        require(db is self.db and db.in_transaction,'CONFLICT')
        keys=self.cfg['templates'].get(template);require(keys is not None,'NOT_AVAILABLE');selected={}
        for key in keys:
            record,row=self._record(key,'select');require(row is not None and row['state']=='enabled','NOT_AVAILABLE');self._ready(row,now)
            selected[key]=dict(record=record,record_digest=digest(canonical(record)))
        self._charge(len(canonical(selected)))
        db.execute('INSERT INTO integrated_provider_bindings VALUES(?,?)',(session,canonical(selected).decode()))
        self.store._check_bytes()
    def inspect(self,key):
        record,row=self._record(key,'inspect')
        result=dict(profile=PROFILE,provider=key,advertised=record,admitted=row is not None,
                    state=row['state'] if row else 'not-admitted',readiness=json.loads(row['readiness']) if row and row['readiness'] else None,
                    conformance='REFERENCED_NOT_INFERRED',authority='CURRENT_SEPARATE_POLICY')
        if row:result['retained_access']=row['retained']
        return result
    def selected(self,session):
        allocated=self.store.allocated(self.store.allocation['templates'][next(iter(self.cfg['templates']))]['principal'],session)
        self.authorize(allocated['frozen']['scope'],'providers.inspect')
        row=self.db.execute('SELECT selection FROM integrated_provider_bindings WHERE session=?',(session,)).fetchone()
        require(row is not None,'NOT_FOUND');return json.loads(row[0])


def admit_input(db,session):
    """Existing selected sessions cannot mint new assignments to disabled peers.

    Called only for a new input, inside the owner's acceptance transaction.
    Captured/accepted inputs and observation are never rerouted or blocked here.
    Readiness expiry controls new *selection*, not a provider's health claim.
    """
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='integrated_provider_bindings'").fetchone():return
    row=db.execute('SELECT selection FROM integrated_provider_bindings WHERE session=?',(session,)).fetchone()
    require(row is not None,'NOT_AVAILABLE')
    for key,binding in json.loads(row[0]).items():
        provider=db.execute('SELECT state,record FROM integrated_providers WHERE id=?',(key,)).fetchone()
        require(provider is not None and provider['state']=='enabled','NOT_AVAILABLE')
        require(provider['record']==canonical(binding['record']).decode(),'CONFLICT')
