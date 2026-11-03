"""Operator-only exact literal excerpt disclosure, using existing owned AtomStorage.

Only a proper literal excerpt of the generated source may be approved. No
summary is generated or inferred; full raw source content stays private.
The private source/ref/approval remain in this application's journal. The new
shared artifact includes only the explicitly approved content, no source IDs,
private hashes, history or empirical evidence. This is not a model tool.
"""
import json,sqlite3,time,uuid
from pathlib import Path
from fusion import vector_contracts as v
from fusion.contracts import canonical,digest,require
from fusion.neoclaw_retrieval_disclosure import safe_data
from fusion.policy import Policy
from fusion.ports import Mutation
from fusion.preview_atoms import client
from fusion.sustained_sessions import SustainedSessionStore,identity
from .sustained_runtime import materialize

PROFILE='operator-approved-synthetic-projection/1'


def invoke(owner,state,run,credential,q,hook=lambda _:None):
    require(type(q) is dict and set(q)=={'profile','identity','session','source','content','approval_record','recipient_scope'})
    require(q['profile']==PROFILE,'UNSUPPORTED_PROFILE');identity(q['identity']);identity(q['approval_record']);safe_data(q['content'])
    policy=Policy(owner);cfg=policy.current();selected=cfg['native_sessions']
    require(selected['profile']=='omega-native-sessions/3','UNSUPPORTED_PROFILE')
    actor=policy.authenticate(credential);require(actor=='operator','UNAUTHORIZED')
    def authorize(who,scope,operation):
        require(policy.authenticate(credential)==actor and who==selected['principal'],'UNAUTHORIZED')
        policy.check(actor,scope,'sessions.project');policy.check(actor,scope,'sessions.disclose')
    store=SustainedSessionStore(selected['database'],authorize,selected['allocation'])
    try:allocation=store.allocated(selected['principal'],q['session'])
    finally:store.close()
    require(allocation['template']=='private' and q['recipient_scope']==selected['scope'],'UNAUTHORIZED')
    source_scope=allocation['frozen']['scope'];v.a.ref(q['source'],source_scope)
    authorize(selected['principal'],source_scope,'project');authorize(selected['principal'],selected['scope'],'project')
    app_path=materialize(owner,state,run,q['session']);app=json.loads(app_path.read_bytes())
    private=json.loads(Path(app['memory_atoms_config']).read_bytes())
    shared=json.loads((Path(run)/'templates'/'shared'/'memory-atoms.json').read_bytes())
    require(private['scope']==source_scope and shared['scope']==q['recipient_scope'],'CONFLICT')
    db=sqlite3.connect(Path(state)/'private-projections.sqlite',timeout=2);db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
    db.execute('''CREATE TABLE IF NOT EXISTS projections(identity TEXT PRIMARY KEY,intent TEXT NOT NULL,
        public_identity TEXT NOT NULL,deadline INTEGER NOT NULL,calls INTEGER NOT NULL DEFAULT 0,source TEXT,result TEXT)''')
    serialized=canonical(q).decode()
    try:
        with db:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT * FROM projections WHERE identity=?',(q['identity'],)).fetchone()
            require(old is None or old['intent']==serialized,'CONFLICT')
            if old is None:
                require(db.execute('SELECT count(*) FROM projections').fetchone()[0]<16,'OVERLOADED')
                # Public identity is independently allocated, not derived from
                # the private source, session, principal or approval fingerprint.
                db.execute('INSERT INTO projections(identity,intent,public_identity,deadline) VALUES(?,?,?,?)',
                    (q['identity'],serialized,str(uuid.uuid4()),time.time_ns()//1000000+30000))
        hook('after_private_projection_acceptance')
        def reserve(effect=False):
            authorize(selected['principal'],source_scope,'project');authorize(selected['principal'],selected['scope'],'project')
            with db:
                db.execute('BEGIN IMMEDIATE');row=db.execute('SELECT * FROM projections WHERE identity=?',(q['identity'],)).fetchone()
                require(row['calls']<8,'OVERLOADED')
                if effect:require(time.time_ns()//1000000<row['deadline'],'DEADLINE_EXCEEDED')
                db.execute('UPDATE projections SET calls=calls+1 WHERE identity=?',(q['identity'],))
            return row
        row=reserve();item=client(private).get(q['source'])
        require(item.content_type==v.PAYLOAD,'UNSUPPORTED_PROFILE');source=json.loads(item.bytes)
        require(canonical(source)==item.bytes and source['scope']==source_scope and type(source['content']) is str and 1<=len(q['content'].encode())<=512 and q['content'] in source['content'] and q['content']!=source['content'],'UNAUTHORIZED')
        with db:
            require(row['source'] is None or row['source']==item.bytes.decode(),'CONFLICT')
            db.execute('UPDATE projections SET source=? WHERE identity=?',(item.bytes.decode(),q['identity']))
        hook('after_private_projection_source_capture')
        artifact=dict(profile=PROFILE,content=q['content'],evidence='operator-approved-projection-not-independent-observation')
        raw=canonical(artifact);command=Mutation(shared['scope'],'projection/'+row['public_identity'])
        if row['result'] is None:
            reserve();observed=client(shared).observe(command)
            if observed['found']:result=observed['write']
            else:
                row=reserve(effect=True);result=client(shared,row['deadline']).create(command,PROFILE,raw)
            require(result['ref']['digest']==digest(raw),'CONFLICT')
            with db:db.execute('UPDATE projections SET result=? WHERE identity=?',(canonical(result).decode(),q['identity']))
            hook('after_private_projection_publication_capture')
        else:result=json.loads(row['result'])
        reserve();observed=client(shared).get(result['ref']);require(observed.bytes==raw and observed.content_type==PROFILE,'CONFLICT')
        authorize(selected['principal'],source_scope,'project');authorize(selected['principal'],selected['scope'],'project')
        return dict(profile=PROFILE,shared=result['ref'],empirical_evidence=False,private_source_disclosed=False)
    finally:db.close()
