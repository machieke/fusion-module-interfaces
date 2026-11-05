"""Bounded derived cleanup inside the existing application owner.

Only a closed/archived session with no native worker can be selected. Exact
immutable prepared entries, verified history materializations and duplicate
startup diagnostics are eligible; captures, working-context snapshots, source
roots, historical intents, last results and spent reservations never are.
"""
import fcntl,json,os,re,sqlite3,uuid
from contextlib import contextmanager,closing
from pathlib import Path
from fusion.contracts import canonical,digest,require,ContractError
from fusion.policy import Policy
from fusion.sustained_sessions import SustainedSessionStore
from fusion.preview_native_history import read_body
from fusion.preview_atoms import client as atoms_client
from fusion.pilot_search_cleanup import tree

PROFILE='closed-session-derived-reclamation/1'
ROUTE='/preview/derived-maintenance'
LIMITS=dict(plans=32,files=128,bytes=16*1024*1024,cache_rows=4,result_bytes=98304)


def charges(store,session,current):
    """Reserve this owner's application bytes before a separate cache commit."""
    db=store.db
    db.execute('CREATE TABLE IF NOT EXISTS pilot_derived_cleanup_charges(session TEXT NOT NULL,identity TEXT NOT NULL,plan_sha256 TEXT NOT NULL,intent_bytes INTEGER NOT NULL,result_bound INTEGER NOT NULL,result_bytes INTEGER NOT NULL,state TEXT NOT NULL,PRIMARY KEY(session,identity))');db.commit()
    def account(selected,value):
        current();size=len(canonical(selected));result=len(canonical(value));require(size<=60096 and result<=LIMITS['result_bytes'],'OVERLOADED')
        with db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM pilot_derived_cleanup_charges WHERE session=? AND identity=?',(session,value['identity'])).fetchone()
            if old:
                require(old['plan_sha256']==selected['sha256'] and old['intent_bytes']==size,'CONFLICT')
            else:
                require(db.execute('SELECT count(*) FROM pilot_derived_cleanup_charges').fetchone()[0]<LIMITS['plans'],'OVERLOADED')
                db.execute('INSERT INTO pilot_derived_cleanup_charges VALUES(?,?,?,?,?,?,?)',(session,value['identity'],selected['sha256'],size,LIMITS['result_bytes'],0,'reserved'))
                store._check_bytes()
            if value['state']=='complete':
                db.execute("UPDATE pilot_derived_cleanup_charges SET result_bytes=?,state='complete' WHERE session=? AND identity=?",(result,session,value['identity']))
                store._check_bytes()
    return account


def table_head(db):
    """Semantic head excludes only independently removable caches and receipts."""
    result={};count=0
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        require(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',table),'UNSUPPORTED_PROFILE')
        if table in ('preview_history_materializations','pilot_derived_cleanup'):continue
        rows=db.execute('SELECT * FROM '+table+' LIMIT 65537').fetchall();count+=len(rows);require(count<=65536,'OVERLOADED')
        def wire(row):return [dict(bytes=len(v),sha256=digest(v)) if type(v) is bytes else v for v in row]
        result[table]=sorted(digest(canonical(wire(row))) for row in rows)
    return digest(canonical(result))


class Cleanup:
    def __init__(self,root,session,db,authorize,atoms,*,hook=lambda _:None,account=lambda *_:None):
        self.root,self.session,self.db,self.authorize,self.atoms,self.hook=Path(root),session,db,authorize,atoms,hook
        self.account=account
        db.execute('CREATE TABLE IF NOT EXISTS pilot_derived_cleanup(identity TEXT PRIMARY KEY,intent TEXT NOT NULL,result TEXT NOT NULL)');db.commit()
    def _head(self):self.authorize();return table_head(self.db)
    def _native(self):
        native=self.root/'native';require(native.is_dir() and not native.is_symlink(),'NOT_AVAILABLE')
        observed=native/'preparation-observation.json';require(observed.is_file() and not observed.is_symlink(),'NOT_AVAILABLE')
        value=json.loads(observed.read_bytes());require(value['profile']=='verified-native-preparation/1','UNSUPPORTED_PROFILE')
        require(re.fullmatch('[0-9a-f]{64}',value['key']),'CONFLICT')
        return native,value['key'],digest(observed.read_bytes())
    def _cache(self,key):
        require(re.fullmatch('[0-9a-f]{64}',key),'INVALID_ARGUMENT')
        row=self.db.execute('SELECT * FROM preview_history_materializations WHERE key=?',(key,)).fetchone();require(row is not None,'NOT_FOUND')
        value=dict(row);binding=json.loads(value['binding']);require(binding['session']==self.session,'CONFLICT')
        actual=canonical(read_body(self.atoms,binding['payload']))
        require(actual.decode()==value['body'] and digest(actual)==value['body_digest'],'CONFLICT')
        return dict(kind='history-materialization',key=key,sha256=digest(canonical(value)),bytes=len(value['body'].encode()),reference=binding['payload'])
    def inventory(self):
        """Owner-selected candidates, with no payload text or caller paths."""
        head=self._head();rows=self.db.execute('SELECT key FROM preview_history_materializations ORDER BY key LIMIT 5').fetchall()
        require(len(rows)<=LIMITS['cache_rows'],'OVERLOADED')
        keys=[row[0] for row in rows];native,current,pin=self._native()
        candidates=[];root=native/'prepared';entries=list(root.iterdir());require(len(entries)<=32,'OVERLOADED')
        for path in sorted(entries):
            if path.name==current or not re.fullmatch('[0-9a-f]{64}',path.name):continue
            try:self.plan(dict(overlays=[path.name],materializations=[],duplicate_startup=False))
            except ContractError as error:
                if error.code in ('NOT_AVAILABLE','CONFLICT'):continue
                raise
            candidates.append(path.name)
        duplicate=False
        if (native/'startup.json').exists():
            try:self.plan(dict(overlays=[],materializations=[],duplicate_startup=True));duplicate=True
            except ContractError as error:
                if error.code not in ('NOT_AVAILABLE','CONFLICT'):raise
        require(self._head()==head,'CONFLICT')
        return dict(profile=PROFILE,session=self.session,authoritative_head=head,preparation_pin=pin,
            current_preparation=current,selection=dict(overlays=candidates[:8],materializations=keys,duplicate_startup=duplicate),
            bounded_overlays_remaining=max(0,len(candidates)-8),authority='CURRENT_OWNER_CLOSED_SESSION')
    def plan(self,selection):
        require(type(selection) is dict and set(selection)=={'overlays','materializations','duplicate_startup'},'INVALID_ARGUMENT')
        require(type(selection['overlays']) is list and len(selection['overlays'])<=8 and len(set(selection['overlays']))==len(selection['overlays']),'OVERLOADED')
        require(type(selection['materializations']) is list and len(selection['materializations'])<=4 and len(set(selection['materializations']))==len(selection['materializations']),'OVERLOADED')
        require(type(selection['duplicate_startup']) is bool,'INVALID_ARGUMENT')
        head=self._head();candidates=[];pin=None
        if selection['overlays'] or selection['duplicate_startup']:
            native,current,pin=self._native()
            from integration.neoclaw.prepared_startup import verified
            retained=native/'prepared'/current;retained_value=verified(retained,current)
            for key in sorted(selection['overlays']):
                require(type(key) is str and re.fullmatch('[0-9a-f]{64}',key),'INVALID_ARGUMENT');require(key!=current,'CONFLICT')
                target=native/'prepared'/key;old=verified(target,key);files=tree(target)
                # Reconstructibility is byte-proved from a retained current
                # immutable template, not an assumed ability to run old code.
                # Differently configured/source overlays remain pinned.
                translated={}
                for name in retained_value['files']:
                    data=(retained/name).read_bytes().replace(str(retained).encode(),str(target).encode())
                    translated[name]=digest(data)
                rebuilt=json.loads(canonical(retained_value).replace(str(retained).encode(),str(target).encode()))
                rebuilt.update(key=key,files=translated)
                require(old==rebuilt and set(files)==set(translated)|{'prepared.json'} and files['prepared.json']['sha256']==digest(canonical(rebuilt)),'NOT_AVAILABLE')
                require(all(files[name]['sha256']==value for name,value in translated.items()),'NOT_AVAILABLE')
                candidates.append(dict(kind='prepared-overlay',key=key,files=files,retained_key=current,
                    retained_sha256=digest(canonical(retained_value))))
            if selection['duplicate_startup']:
                retained=native/'prepared'/current;verified(retained,current)
                source=retained/'startup.json';target=native/'startup.json'
                require(source.is_file() and target.is_file() and not target.is_symlink() and source.read_bytes()==target.read_bytes(),'CONFLICT')
                candidates.append(dict(kind='duplicate-startup',sha256=digest(target.read_bytes()),bytes=target.stat().st_size,blocks=target.stat().st_blocks*512,retained_key=current))
        for key in sorted(selection['materializations']):candidates.append(self._cache(key))
        require(candidates,'INVALID_ARGUMENT')
        count=sum(len(x['files']) if x['kind']=='prepared-overlay' else 1 for x in candidates)
        size=sum(sum(y['bytes'] for y in x['files'].values()) if x['kind']=='prepared-overlay' else x['bytes'] for x in candidates)
        require(count<=LIMITS['files'] and size<=LIMITS['bytes'],'OVERLOADED');require(self._head()==head,'CONFLICT')
        plan=dict(profile=PROFILE,session=self.session,authoritative_head=head,preparation_pin=pin,candidates=candidates,
            limits=LIMITS,authoritative_deletion=False,minimum_replay_retention='UNCHANGED',capacity_refund=False,
            physical_freed_bytes='MEASURE_SEPARATELY_SQLITE_AND_OPEN_HANDLES_RETAIN_BLOCKS')
        require(len(canonical(plan))<=60000,'OVERLOADED');return dict(plan=plan,sha256=digest(canonical(plan)))
    def _validate(self,selected):
        require(type(selected) is dict and set(selected)=={'plan','sha256'} and digest(canonical(selected['plan']))==selected['sha256'],'CONFLICT')
        p=selected['plan'];require(p['profile']==PROFILE and p['session']==self.session and p['limits']==LIMITS and p['authoritative_deletion'] is False and p['capacity_refund'] is False,'UNSUPPORTED_PROFILE')
        require(self._head()==p['authoritative_head'],'CONFLICT')
        if p['preparation_pin'] is not None:require(self._native()[2]==p['preparation_pin'],'CONFLICT')
        return p
    def observe(self,selected,identity):
        self.authorize();require(type(identity) is str and 0<len(identity)<=128,'INVALID_ARGUMENT')
        row=self.db.execute('SELECT intent,result FROM pilot_derived_cleanup WHERE identity=?',(identity,)).fetchone()
        if row is None:return dict(identity=identity,state='absent',plan_sha256=selected['sha256'])
        require(row['intent']==canonical(selected).decode(),'CONFLICT');return json.loads(row['result'])
    def _save(self,selected,value):
        require(len(canonical(value))<=LIMITS['result_bytes'],'OVERLOADED')
        with self.db:self.db.execute('INSERT OR REPLACE INTO pilot_derived_cleanup VALUES(?,?,?)',(value['identity'],canonical(selected).decode(),canonical(value).decode()))
    def apply(self,selected,identity):
        p=self._validate(selected);value=self.observe(selected,identity)
        if value['state']=='complete':self.account(selected,value);return value
        if value['state']=='absent':
            require(self.db.execute('SELECT count(*) FROM pilot_derived_cleanup').fetchone()[0]<LIMITS['plans'],'OVERLOADED')
            # A new plan must still describe all exact current candidates.
            sel=dict(overlays=[c['key'] for c in p['candidates'] if c['kind']=='prepared-overlay'],materializations=[c['key'] for c in p['candidates'] if c['kind']=='history-materialization'],duplicate_startup=any(c['kind']=='duplicate-startup' for c in p['candidates']))
            require(self.plan(sel)==selected,'CONFLICT')
            value=dict(profile=PROFILE,identity=identity,state='applying',plan_sha256=selected['sha256'],removed=[],pending=None,
                unlinked_bytes=0,unlinked_allocated_bytes=0,cache_body_bytes_removed=0,capacity_refund=False,
                physical_freed_bytes='NOT_ESTABLISHED_SQLITE_FREELIST_AND_OPEN_HANDLES_MAY_RETAIN_BLOCKS')
            self.account(selected,value);self._save(selected,value)
        for index,c in enumerate(p['candidates']):
            self._validate(selected)
            if c['kind']=='prepared-overlay':
                from integration.neoclaw.prepared_startup import verified
                require(digest(canonical(verified(self.root/'native/prepared'/c['retained_key'],c['retained_key'])))==c['retained_sha256'],'CONFLICT')
            if c['kind']=='history-materialization':
                key='cache/'+c['key']
                if key in value['removed']:continue
                self._cache(c['key']);require(self._cache(c['key'])==c,'CONFLICT')
                with self.db:
                    self.db.execute('DELETE FROM preview_history_materializations WHERE key=?',(c['key'],))
                    value['removed'].append(key);value['cache_body_bytes_removed']+=c['bytes']
                    self.db.execute('UPDATE pilot_derived_cleanup SET result=? WHERE identity=?',(canonical(value).decode(),identity))
                self.hook('after_cache_remove');continue
            if c['kind']=='prepared-overlay':items=[('native/prepared/'+c['key']+'/'+name,meta) for name,meta in sorted(c['files'].items())]
            else:items=[('native/startup.json',c)]
            for name,meta in items:
                if name in value['removed']:continue
                self._validate(selected);path=self.root/name;require(path.resolve().is_relative_to(self.root.resolve()) and not path.is_symlink(),'UNAUTHORIZED')
                require(all(not parent.is_symlink() for parent in path.parents if parent.is_relative_to(self.root)),'UNAUTHORIZED')
                if path.exists():
                    require(path.is_file() and path.stat().st_size==meta['bytes'] and digest(path.read_bytes())==meta['sha256'],'CONFLICT')
                    if c['kind']=='duplicate-startup':
                        source=self.root/'native/prepared'/c['retained_key']/'startup.json';require(source.is_file() and digest(source.read_bytes())==c['sha256'],'CONFLICT')
                    require(value['pending'] in (None,name),'CONFLICT');value['pending']=name;self._save(selected,value)
                    path.parent.chmod(path.parent.stat().st_mode|0o700);path.unlink()
                    fd=os.open(path.parent,os.O_DIRECTORY)
                    try:os.fsync(fd)
                    finally:os.close(fd)
                    self.hook('after_derived_unlink')
                    value['unlinked_bytes']+=meta['bytes'];value['unlinked_allocated_bytes']+=meta['blocks']
                else:require(value['pending']==name,'CONFLICT')
                value['removed'].append(name);value['pending']=None;self._save(selected,value)
            if c['kind']=='prepared-overlay':
                target=self.root/'native/prepared'/c['key']
                if target.exists():
                    # Only now-empty directories inside the exact validated
                    # immutable entry; never recursive deletion or wildcards.
                    for folder in sorted((x for x in target.rglob('*') if x.is_dir()),reverse=True):folder.rmdir()
                    target.rmdir()
        self._validate(selected);value['state']='complete';self._save(selected,value);self.account(selected,value);return value


def invoke(config,state,run,credential,q,supervisor,hook=lambda _:None):
    require(type(q) is dict and set(q)=={'profile','id','session','operation','body'} and len(canonical(q))<=65536,'INVALID_ARGUMENT')
    require(q['profile']==PROFILE and q['operation'] in ('inventory','plan','apply','observe'),'UNSUPPORTED_PROFILE');uuid.UUID(q['session'])
    policy=Policy(config);actor=policy.authenticate(credential);cfg=policy.current();selected=cfg['native_sessions']
    require(selected.get('derived_cleanup')==PROFILE,'UNSUPPORTED_PROFILE')
    with supervisor.guard:
        require(q['session'] not in supervisor.pending and (supervisor.session!=q['session'] or supervisor.child is None or supervisor.child.poll() is not None),'NOT_AVAILABLE')
        def authorize(who,scope,method):
            require(policy.authenticate(credential)==actor and who==selected['principal'],'UNAUTHORIZED')
            policy.check(actor,scope,'sessions.derived-'+q['operation']);policy.check(actor,scope,'sessions.disclose')
        store=SustainedSessionStore(selected['database'],authorize,selected['allocation'])
        try:
            allocation=store.allocated(selected['principal'],q['session']);scope=allocation['frozen']['scope']
            def current():
                require(policy.current()['native_sessions'].get('derived_cleanup')==PROFILE,'UNSUPPORTED_PROFILE')
                authorize(selected['principal'],scope,'cleanup')
                require(store.observe(selected['principal'],q['session'])['state'] in ('closed','archived'),'CONFLICT')
            current();root=Path(state)/'sessions'/q['session'];database=root/'caller.sqlite'
            require(root.is_dir() and not root.is_symlink() and database.is_file() and not database.is_symlink(),'NOT_AVAILABLE')
            with open(str(database)+'.application.lock','a') as lock:
                try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError:require(False,'NOT_AVAILABLE')
                with closing(sqlite3.connect(database)) as db:
                    db.row_factory=sqlite3.Row
                    atom_path=Path(run)/'sessions'/q['session']/'history-atoms.json'
                    class Atoms:
                        def get(self,ref):
                            current();require(ref['scope_ref']==scope,'UNAUTHORIZED')
                            cfg=json.loads(atom_path.read_bytes());require(cfg['scope']==scope,'UNAUTHORIZED');return atoms_client(cfg).get(ref)
                    owner=Cleanup(root,q['session'],db,current,Atoms(),hook=hook,account=charges(store,q['session'],current))
                    body=q['body'];require(type(body) is dict,'INVALID_ARGUMENT')
                    if q['operation']=='inventory':
                        require(not body,'INVALID_ARGUMENT');value=owner.inventory()
                    elif q['operation']=='plan':value=owner.plan(body)
                    else:
                        require(set(body)=={'plan','identity'},'INVALID_ARGUMENT')
                        value=getattr(owner,q['operation'])(body['plan'],body['identity'])
                    current()
        finally:store.close()
    return dict(profile=PROFILE,id=q['id'],request_digest=digest(canonical(q)),actor=actor,value=value)


def request(q,component='/config/component.json',owner='/run/fusion/owner.json'):
    from fusion.preview_transport import invoke as exchange
    settings=json.loads(Path(component).read_bytes());cfg=json.loads(Path(owner).read_bytes())
    role=settings['role'];require(role in settings['preview']['agents'],'UNAUTHORIZED')
    require(type(q) is dict and set(q)=={'operation','session','body'},'INVALID_ARGUMENT')
    wire=dict(profile=PROFILE,id=str(uuid.uuid4()),**q)
    value=exchange(dict(endpoint=dict(host=settings['peers'][role],port=settings['https_port'],ca_file=str(Path(settings.get('secret_directory','/secrets'))/'ca.crt')),
        credential=cfg['principals']['operator']['credential']),ROUTE,wire)
    require(type(value) is dict and set(value)=={'profile','id','request_digest','actor','value'} and
        value['profile']==PROFILE and value['id']==wire['id'] and value['request_digest']==digest(canonical(wire)) and value['actor']=='operator','NOT_AVAILABLE')
    return value['value']


def main():
    import sys
    raw=sys.stdin.buffer.read(65537);require(len(raw)<=65536,'OVERLOADED')
    print(json.dumps(request(json.loads(raw)),sort_keys=True))


if __name__=='__main__':main()
