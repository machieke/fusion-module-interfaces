"""Opt-in sealed payload tier inside the existing AtomStorage/feed owner.

No new owner, mutation of source records, global snapshot, quota refund or hot
deletion. Reservation, file publication and activation commit independently.
An activated corrupt/missing segment fails closed; hot copies are not fallback.
"""
from contextlib import closing
import json,os,tempfile,uuid
from pathlib import Path
from .contracts import canonical,digest,require,ContractError,encode,decode
from . import lookup_contracts as c
from .ports import AtomEnvelope

from .archive_contracts import PROFILE,SEGMENT_BYTES,RESERVATION_BYTES,DEFAULT,policy
TABLES={'feed_archive_policy','feed_archive_intents','feed_archive_members'}

def initialize(owner,selected,db):
    selected=policy(selected)
    root=Path(str(owner.path)+'.archive');require(not root.is_symlink(),'UNAUTHORIZED')
    root.mkdir(exist_ok=True)
    db.execute('CREATE TABLE IF NOT EXISTS feed_archive_policy(value TEXT NOT NULL)')
    db.execute('''CREATE TABLE IF NOT EXISTS feed_archive_intents(
            id TEXT PRIMARY KEY,identity TEXT UNIQUE NOT NULL,scope TEXT NOT NULL,
            intent TEXT NOT NULL,state TEXT NOT NULL,manifest_digest TEXT,bytes INTEGER,
            charge INTEGER NOT NULL)''')
    db.execute('''CREATE TABLE IF NOT EXISTS feed_archive_members(
            scope TEXT NOT NULL,atom TEXT NOT NULL,segment TEXT NOT NULL,ordinal INTEGER NOT NULL,
            PRIMARY KEY(scope,atom))''')
    old=db.execute('SELECT value FROM feed_archive_policy').fetchone()
    if old:require(old[0]==canonical(selected).decode(),'CONFLICT')
    else:db.execute('INSERT INTO feed_archive_policy VALUES(?)',(canonical(selected).decode(),))
    return selected

def _authorize(owner,scope,operation):
    require(owner.archive_policy is not None,'UNSUPPORTED_PROFILE')
    require(owner.capacity_policy is None or scope in owner.capacity_policy['scopes'],'UNAUTHORIZED')
    return owner.access.authorize(scope,operation)

def _path(owner,segment):
    c.identity(segment)
    root=Path(str(owner.path)+'.archive');path=root/(segment+'.json')
    require(not root.is_symlink() and not path.is_symlink(),'UNAUTHORIZED')
    return path

def _rows(owner,db,scope,after,through,limit):
    c.head(through,scope,owner.profile);c.integer(after,0,through['sequence']);c.integer(limit,1,owner.archive_policy['records'])
    require(through['source']==owner.source,'CONFLICT')
    highest=db.execute('SELECT coalesce(max(sequence),0) FROM feed_atoms WHERE scope=?',(scope,)).fetchone()[0]
    require(through['sequence']<=highest,'CONFLICT')
    rows=db.execute('SELECT sequence,value FROM feed_atoms WHERE scope=? AND sequence>? AND sequence<=? ORDER BY sequence LIMIT ?',
                    (scope,after,through['sequence'],limit)).fetchall()
    require(rows,'NOT_FOUND')
    return [dict(sequence=number,value=json.loads(value)) for number,value in rows]

def plan(owner,scope,after,through,limit):
    _authorize(owner,scope,'planArchive');owner.access.authorize(scope,'get');owner.access.authorize(scope,'readCommits')
    with closing(owner.connect()) as db:rows=_rows(owner,db,scope,after,through,limit)
    _authorize(owner,scope,'planArchive')
    return dict(profile=PROFILE,source=owner.source,scope_ref=scope,after=after,through=through,
        records=[dict(sequence=r['sequence'],ref=r['value']['write']['ref'],size=r['value']['size']) for r in rows],
        maximum_charge_bytes=RESERVATION_BYTES,hot_deletion=False,source_head_unchanged=True,
        admission_reserved=False)

def _status(owner,row):
    intent=json.loads(row[3])
    summary={k:v for k,v in intent.items() if k!='records'}
    summary['records']=[dict(sequence=r['sequence'],ref=r['value']['write']['ref'],size=r['value']['size']) for r in intent['records']]
    return dict(profile=PROFILE,id=row[0],scope_ref=row[2],intent=summary,intent_sha256=digest(row[3].encode()),state=row[4],
        manifest_sha256=row[5],sealed_bytes=row[6],charged_bytes=row[7],hot_deletion=False,
        source_head_unchanged=True,effect_budget_refund=False)

def observe(owner,command):
    c.mutation(command);who=_authorize(owner,command.scope_ref,'observeArchive')
    identity=canonical([who,command.scope_ref,command.idempotency_key]).decode()
    with closing(owner.connect()) as db:
        row=db.execute('SELECT * FROM feed_archive_intents WHERE identity=?',(identity,)).fetchone()
        count,charge,sealed=db.execute("SELECT count(*),coalesce(sum(charge),0),coalesce(sum(CASE WHEN state='sealed' THEN 1 ELSE 0 END),0) FROM feed_archive_intents WHERE scope=?",(command.scope_ref,)).fetchone()
    _authorize(owner,command.scope_ref,'observeArchive')
    return dict(profile=PROFILE,scope_ref=command.scope_ref,found=row is not None,
        archive=_status(owner,row) if row else None,capacity=dict(limits=owner.archive_policy,reserved_segments=count,
        charged_bytes=charge,sealed_segments=sealed,refunds=False))

def publish(owner,command,after,through,limit):
    c.mutation(command);scope=command.scope_ref;who=_authorize(owner,scope,'publishArchive')
    owner.access.authorize(scope,'get');owner.access.authorize(scope,'readCommits')
    identity=canonical([who,scope,command.idempotency_key]).decode()
    segment=str(uuid.uuid5(uuid.UUID(owner.source),'sealed-archive/'+identity))
    with closing(owner.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE')
        rows=_rows(owner,db,scope,after,through,limit)
        intent=canonical(dict(profile=PROFILE,source=owner.source,scope_ref=scope,after=after,through=through,limit=limit,records=rows)).decode()
        require(len(intent.encode())<=SEGMENT_BYTES,'OVERLOADED')
        prior=db.execute('SELECT * FROM feed_archive_intents WHERE identity=?',(identity,)).fetchone()
        if prior:
            require(prior[3]==intent,'CONFLICT')
            if prior[4]=='sealed':
                # Acknowledged identity stays stable; also check the current
                # segment before reporting its accessible retained state.
                _read(owner,prior);_authorize(owner,scope,'publishArchive');return _status(owner,prior)
        else:
            count,charge=db.execute('SELECT count(*),coalesce(sum(charge),0) FROM feed_archive_intents WHERE scope=?',(scope,)).fetchone()
            require(count<owner.archive_policy['segments'] and charge+RESERVATION_BYTES<=owner.archive_policy['bytes'],'OVERLOADED')
            for row in rows:
                require(db.execute('SELECT segment FROM feed_archive_members WHERE scope=? AND atom=?',(scope,row['value']['write']['ref']['id'])).fetchone() is None,'CONFLICT')
            db.execute('INSERT INTO feed_archive_intents VALUES(?,?,?,?,?,NULL,NULL,?)',(segment,identity,scope,intent,'reserved',RESERVATION_BYTES))
            for ordinal,row in enumerate(rows):
                db.execute('INSERT INTO feed_archive_members VALUES(?,?,?,?)',(scope,row['value']['write']['ref']['id'],segment,ordinal))
        _authorize(owner,scope,'publishArchive')
    owner.hook('after_archive_reservation')
    records=[]
    for row in rows:
        ref=row['value']['write']['ref'];item=owner.get(ref)
        require(item.ref==ref and item.content_type==row['value']['content_type'] and len(item.bytes)==row['value']['size'],'CONFLICT')
        records.append(dict(**row,data=encode(item.bytes)))
    value=dict(profile=PROFILE,source=owner.source,scope_ref=scope,id=segment,intent_sha256=digest(intent.encode()),records=records)
    wire=canonical(value);require(len(wire)<=SEGMENT_BYTES,'OVERLOADED');path=_path(owner,segment)
    _authorize(owner,scope,'publishArchive')
    if path.exists():require(path.read_bytes()==wire,'NOT_AVAILABLE')
    else:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=segment+'.',suffix='.pending',delete=False) as stream:
            stream.write(wire);stream.flush();os.fsync(stream.fileno());pending=stream.name
        # File publication precedes the routing change. Concurrent requests for
        # this identity produce identical bytes; distinct identities cannot
        # reserve overlapping members under the owner transaction.
        os.replace(pending,path)
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    owner.hook('after_archive_file_publish')
    require(path.read_bytes()==wire,'NOT_AVAILABLE')
    with closing(owner.connect()) as db,db:
        db.execute('BEGIN IMMEDIATE');_authorize(owner,scope,'publishArchive')
        owner.access.authorize(scope,'get');owner.access.authorize(scope,'readCommits')
        old=db.execute('SELECT * FROM feed_archive_intents WHERE id=?',(segment,)).fetchone()
        require(old is not None and old[3]==intent and old[4] in ('reserved','sealed'),'CONFLICT')
        if old[4]=='sealed':require(old[5]==digest(wire) and old[6]==len(wire),'CONFLICT')
        else:db.execute("UPDATE feed_archive_intents SET state='sealed',manifest_digest=?,bytes=? WHERE id=?",(digest(wire),len(wire),segment))
        result=db.execute('SELECT * FROM feed_archive_intents WHERE id=?',(segment,)).fetchone()
    owner.hook('after_archive_activation')
    _authorize(owner,scope,'publishArchive');owner.access.authorize(scope,'get')
    return _status(owner,result)

def _read(owner,row):
    require(row[4]=='sealed','NOT_AVAILABLE')
    try:
        with _path(owner,row[0]).open('rb') as stream:raw=stream.read(SEGMENT_BYTES+1)
    except OSError:raise ContractError('NOT_AVAILABLE') from None
    require(len(raw)==row[6] and len(raw)<=SEGMENT_BYTES and digest(raw)==row[5],'NOT_AVAILABLE')
    try:value=json.loads(raw)
    except (ValueError,UnicodeError):raise ContractError('NOT_AVAILABLE') from None
    require(type(value) is dict and set(value)=={'profile','source','scope_ref','id','intent_sha256','records'} and
        canonical(value)==raw and value['profile']==PROFILE and value['source']==owner.source and value['scope_ref']==row[2] and
        value['id']==row[0] and value['intent_sha256']==digest(row[3].encode()),'NOT_AVAILABLE')
    require(type(value['records']) is list and 1<=len(value['records'])<=owner.archive_policy['records'],'NOT_AVAILABLE')
    require(all(type(r) is dict and set(r)=={'sequence','value','data'} for r in value['records']),'NOT_AVAILABLE')
    require([{k:r[k] for k in ('sequence','value')} for r in value['records']]==json.loads(row[3])['records'],'NOT_AVAILABLE')
    return value

def read(owner,ref,expected):
    if owner.archive_policy is None:return None
    with closing(owner.connect()) as db:
        member=db.execute('SELECT segment,ordinal FROM feed_archive_members WHERE scope=? AND atom=?',(ref['scope_ref'],ref['id'])).fetchone()
        if member is None:return None
        row=db.execute('SELECT * FROM feed_archive_intents WHERE id=?',(member[0],)).fetchone()
    require(row is not None,'NOT_AVAILABLE')
    if row[4]=='reserved':return None
    _authorize(owner,ref['scope_ref'],'get')
    value=_read(owner,row);require(0<=member[1]<len(value['records']),'NOT_AVAILABLE')
    item=value['records'][member[1]]
    require(type(item) is dict and set(item)=={'sequence','value','data'} and item['value']==expected,'NOT_AVAILABLE')
    data=decode(item['data']);require(digest(data)==ref['digest'] and len(data)==expected['size'],'NOT_AVAILABLE')
    _authorize(owner,ref['scope_ref'],'get')
    return AtomEnvelope(c.copy(ref),expected['content_type'],data)
