"""Application append progress and read-view selection. Owner commits stay separate."""
import json
from pathlib import Path
import time
import uuid
from . import append_contracts as c, vector_contracts as v, embedding_contracts as e
from .contracts import canonical,digest,require,encode,decode
from .ports import AtomEnvelope,Mutation
from .responses import atom_write,envelope
from .registry import selection_token
from .append_composition import configuration
from .append_transport import binding
from .vector_enrollment import enroll


class WriteAtoms:
    """Port adapter for existing enrollment; observes accepted mutations first."""
    def __init__(self,owner,row,accepted):self.owner,self.row,self.accepted=owner,row,accepted
    def create(self,command,content_type,data):
        role=next((r for r in c.ROLES if c.key(self.accepted,r)==command.idempotency_key),None)
        require(command.scope_ref==self.accepted['scope'] and role is not None,'CONFLICT')
        c.envelope(self.accepted,role,content_type,data)
        seen=c.observation(self.owner.call(self.row,'atom.storage','observe',dict(role=role)),command.scope_ref,
                           self.owner.chosen()['atom.storage'],content_type=content_type,data=data)
        if seen['found']:value=seen['write']
        else:
            value=self.owner.call(self.row,'atom.storage','create',dict(role=role,content_type=content_type,data=encode(data)),effect=True)
            atom_write(value,command.scope_ref,self.owner.chosen()['atom.storage'])
            c.a.ref(value['ref'],command.scope_ref)
            require(value['ref']['digest']==digest(data),'NOT_AVAILABLE')
        self.owner.checkpoint(self.row,role,value)
        return value
    def get(self,ref):
        value=self.owner.call(self.row,'atom.storage','get',dict(ref=ref))
        v.fields(value,'ref content_type data');item=AtomEnvelope(value['ref'],value['content_type'],decode(value['data']))
        envelope(item,ref);return item


class MemoryAppend:
    def __init__(self,app):
        self.app,self.db=app,app.db
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS app_memory_writes (
              id TEXT PRIMARY KEY, uuid TEXT UNIQUE NOT NULL, sampled_time TEXT, intent TEXT,
              calls INTEGER NOT NULL DEFAULT 0, builds INTEGER NOT NULL DEFAULT 0,
              receipts TEXT NOT NULL DEFAULT '{}', through_head TEXT, snapshot TEXT, view TEXT,
              linked INTEGER NOT NULL DEFAULT 0, observations TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS app_read_views (id TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS app_active_view (singleton INTEGER PRIMARY KEY CHECK(singleton=1), view TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS app_query_views (id TEXT PRIMARY KEY, view TEXT NOT NULL);
        ''')
        initial=json.loads(Path(json.loads(Path(app.config['memory_native_config']).read_text())['metadata_manifest']).read_text())
        memory=app.binding['memory'];require(digest(canonical(initial))==memory['metadata_seal'],'CONFLICT')
        view=dict(snapshot=memory['snapshot'],metadata_seal=memory['metadata_seal'],metadata=initial)
        key=digest(canonical(view))
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO app_read_views VALUES(?,?)',(key,canonical(view).decode()))
            self.db.execute('INSERT OR IGNORE INTO app_active_view VALUES(1,?)',(key,))
        from .neoclaw_embedding import MemoryEmbedding
        self.embedding=MemoryEmbedding(app)

    def close(self):self.embedding.close()
    def settings(self):
        cfg,chosen,frozen=configuration(self.app.config['memory_append_config'])
        require(frozen==self.app.binding['memory_append'],'CONFLICT');return cfg,chosen
    def chosen(self):return self.settings()[1]
    def state(self,row):
        result=self.db.execute('SELECT * FROM app_memory_writes WHERE id=?',(row['id'],)).fetchone()
        require(result is not None,'CONFLICT');return result
    def current(self):
        require(self.app.current is not None,'CONFLICT')
        row=self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?',self.app.current).fetchone()
        require(row is not None and json.loads(row['premises'])['profile']==c.PROFILE,'UNSUPPORTED_PROFILE');return row
    def admit(self,key,intent):
        if intent['profile']==c.PROFILE:
            self.db.execute('INSERT INTO app_memory_writes(id,uuid) VALUES(?,?)',(key,str(uuid.uuid4())))
        elif intent['profile']==v.PROFILE:
            selected=self.db.execute('SELECT view FROM app_active_view WHERE singleton=1').fetchone()[0]
            self.db.execute('INSERT INTO app_query_views VALUES(?,?)',(key,selected))
    def view_for(self,row):
        selected=self.db.execute('SELECT view FROM app_query_views WHERE id=?',(row['id'],)).fetchone()
        require(selected is not None,'NOT_AVAILABLE')
        return json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(selected[0],)).fetchone()[0])
    def clock(self,observed):
        row=self.current();state=self.state(row);c.timestamp(observed)
        if state['sampled_time'] is None:
            require(time.time_ns()//1_000_000<=row['deadline'],'DEADLINE_EXCEEDED')
            with self.db:self.db.execute('UPDATE app_memory_writes SET sampled_time=? WHERE id=?',(observed,row['id']))
        self.note(row,'identity-and-time')
        self.app.hook('after_write_identity')
        return self.state(row)['sampled_time']
    def note(self,row,stage):
        observed=json.loads(self.state(row)['observations'])
        if stage not in observed:
            observed[stage]=time.time_ns()//1_000_000
            with self.db:self.db.execute('UPDATE app_memory_writes SET observations=? WHERE id=?',(canonical(observed).decode(),row['id']))
    def accepted(self,row):
        state=self.state(row);require(state['intent'] is not None,'NOT_AVAILABLE');return c.intent(json.loads(state['intent']))
    def intent(self,row,vector_sha256):
        state=self.state(row);cfg,_=self.settings();raw=json.loads(row['premises'])['arguments']['content']
        return c.intent(dict(profile=c.PROFILE,session=self.app.session,occurrence=row['id'],principal=cfg['principal'],
            scope=cfg['scope'],corpus=cfg['corpus'],uuid=state['uuid'],time=state['sampled_time'],content=raw,
            helper_input=cfg['inputs'][raw],model=cfg['model'],vector_sha256=vector_sha256,deadline_ms=row['deadline'],
            selections={**self.app.binding['memory_append']['selections'],
                        'embedding':self.app.binding['memory_embedding']['selection']}))
    def preflight(self,row):
        # Permission-only probe, never an accepted owner binding or mutation.
        provisional=self.intent(row,'0'*64)
        require(self.call(row,'atom.storage','authorize',dict(mode='write'),provisional=provisional)=={'authorized':True},'NOT_AVAILABLE')
    def call(self,row,name,op,body,*,effect=False,provisional=None):
        cfg,chosen=self.settings()
        if effect:require(time.time_ns()//1_000_000<=row['deadline'],'DEADLINE_EXCEEDED')
        self.reserve(row,op=='build')
        d=chosen[name]
        require(provisional is None or op=='authorize','UNSUPPORTED_OPERATION')
        request=dict(request_id=row['id'],scope=cfg['scope'],interface_ref=dict(id=name,version=d.version),
                     operation=op,profile=next(iter(d.profiles)),selection=selection_token(d),intent=provisional or self.accepted(row),body=body)
        return binding(cfg,chosen).invoke(request)
    def reserve(self,row,build=False):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');state=self.state(row)
            require(state['calls']<c.MAX_CALLS,'OVERLOADED')
            if build:require(state['builds']<c.MAX_BUILDS,'OVERLOADED')
            self.db.execute('UPDATE app_memory_writes SET calls=calls+1,builds=builds+? WHERE id=?',(int(build),row['id']))
        self.app.hook('after_append_reservation')
        if build:self.app.hook('after_append_build_reservation')
    def read_ready(self,row,snapshot):
        from .neoclaw_memory import configuration as read_configuration
        from .vector_transport import binding as read_binding
        cfg,chosen,frozen=read_configuration(self.app.config['memory_read_config'])
        require(frozen==self.app.binding['memory'],'CONFLICT');self.reserve(row)
        d=chosen['search']
        request=dict(request_id=row['id'],scope=cfg['scope'],interface_ref=dict(id='search',version=d.version),operation='ready',
                     profile=v.PROFILE,selection=selection_token(d),body=dict(snapshot=snapshot))
        require(read_binding(cfg,chosen).invoke(request)=={'ready':True},'NOT_AVAILABLE')
        self.note(row,'read-provider-ready')
    def authorize(self,row):
        self.embedding.authorize(row)
        require(self.call(row,'atom.storage','authorize',dict(mode='disclose'))=={'authorized':True},'NOT_AVAILABLE')
    def checkpoint(self,row,role,value):
        state=self.state(row);receipts=json.loads(state['receipts'])
        require(role not in receipts or receipts[role]==value,'CONFLICT');receipts[role]=value
        with self.db:self.db.execute('UPDATE app_memory_writes SET receipts=? WHERE id=?',(canonical(receipts).decode(),row['id']))
        self.note(row,role+'-accepted')
        self.app.hook('after_append_'+role+'_receipt')
    def append(self,content,vector,timestamp):
        row=self.current();state=self.state(row);cfg,chosen=self.settings()
        raw=json.loads(row['premises'])['arguments']['content']
        require(content==raw and timestamp==state['sampled_time'],'CONFLICT')
        encoded=self.embedding.selected(row);require(vector==encoded['vector'],'CONFLICT')
        accepted=self.intent(row,encoded['vector_sha256'])
        serialized=canonical(accepted).decode();require(state['intent'] is None or state['intent']==serialized,'CONFLICT')
        with self.db:self.db.execute('UPDATE app_memory_writes SET intent=? WHERE id=?',(serialized,row['id']))
        self.authorize(row);ports=WriteAtoms(self,row,accepted)
        ports.create(Mutation(cfg['scope'],c.key(accepted,'binding')),c.BINDING,c.binding_bytes(accepted))
        ref=enroll(ports,cfg['scope'],cfg['corpus'],cfg['model'],'remember-'+row['id'],c.payload(accepted),vector)
        observed=c.observation(self.call(row,'atom.storage','observe',dict(role='enrollment')),cfg['scope'],chosen['atom.storage'],content_type=v.ENROLLMENT)
        require(observed['found'] and observed['write']['ref']==ref,'NOT_AVAILABLE')
        through=observed['through']
        with self.db:self.db.execute('UPDATE app_memory_writes SET through_head=? WHERE id=?',(canonical(through).decode(),row['id']))
        self.app.hook('after_append_enrollment')
        snap=self.call(row,'search','published',dict(through=through))
        if snap is None:
            snap=self.call(row,'search','build',dict(through=through),effect=True)
            require(self.call(row,'search','published',dict(through=through))==snap,'NOT_AVAILABLE')
        v.snapshot(snap,cfg['scope']);require(snap['head']==through and snap['corpus']==cfg['corpus'] and snap['embedding']==cfg['model'],'NOT_AVAILABLE')
        with self.db:self.db.execute('UPDATE app_memory_writes SET snapshot=? WHERE id=?',(canonical(snap).decode(),row['id']))
        self.note(row,'search-published')
        self.app.hook('after_append_publication')
        self.read_ready(row,snap)
        self.ready_view(row,snap)
        return state['uuid']
    def ready_view(self,row,snapshot):
        state=self.state(row);cfg,_=self.settings()
        if state['view'] is not None:
            view=json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(state['view'],)).fetchone()[0])
            require(view['snapshot']==snapshot,'CONFLICT');return view
        active=self.db.execute('SELECT value FROM app_read_views WHERE id=(SELECT view FROM app_active_view)').fetchone()[0]
        prior=json.loads(active);manifest=prior['metadata']
        require(snapshot['head']['source']==prior['snapshot']['head']['source'] and
                snapshot['head']['sequence']>=prior['snapshot']['head']['sequence'],'CONFLICT')
        require(state['uuid'] not in {x['uuid'] for x in manifest['records']},'CONFLICT')
        manifest['records'].append(dict(uuid=state['uuid'],links=[state['sampled_time']],stv=[1.,.5],promotion=0.))
        from .adapters.neoclaw_metadata import collection,ready
        if not ready(cfg['metadata_root'],manifest):
            require(self.call(row,'atom.storage','authorize',dict(mode='write'))=={'authorized':True},'NOT_AVAILABLE')
        collection(cfg['metadata_root'],manifest,prepare=True,deadline=row['deadline'])
        self.note(row,'metadata-ready')
        self.app.hook('after_append_metadata')
        view=dict(snapshot=snapshot,metadata_seal=digest(canonical(manifest)),metadata=manifest);key=digest(canonical(view))
        self.authorize(row)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO app_read_views VALUES(?,?)',(key,canonical(view).decode()))
            self.db.execute('UPDATE app_active_view SET view=? WHERE singleton=1',(key,))
            self.db.execute('UPDATE app_memory_writes SET view=? WHERE id=?',(key,row['id']))
        self.note(row,'view-selected')
        self.app.hook('after_append_view_selection');return view
    def link(self,key,timestamp):
        row=self.current();state=self.state(row)
        require(key==state['uuid'] and timestamp==state['sampled_time'] and state['view'] is not None,'CONFLICT')
        self.authorize(row)
        with self.db:self.db.execute('UPDATE app_memory_writes SET linked=1 WHERE id=?',(row['id'],))
        return key
    def capture(self,value):
        row=self.current();state=self.state(row)
        require(value=='REMEMBER-SUCCESS' and state['linked']==1 and state['view'] is not None,'NOT_AVAILABLE')
        self.authorize(row);self.read_ready(row,json.loads(state['snapshot']))
        require(row['result'] is None or row['result']==value,'CONFLICT')
        with self.db:self.db.execute('UPDATE app_occurrences SET result=?,done=1 WHERE id=?',(value,row['id']))
        self.note(row,'native-success-captured')
        self.app.hook('after_native_result_capture');return value
    def replay(self,row=None):
        row=self.current() if row is None else row;state=self.state(row)
        require(row['result']=='REMEMBER-SUCCESS' and state['view'] is not None and state['linked']==1,'NOT_AVAILABLE')
        self.authorize(row);self.read_ready(row,json.loads(state['snapshot']));return row['result']
    def partial(self):
        row=self.current();state=self.state(row);receipts=json.loads(state['receipts'])
        return dict(memory_uuid=state['uuid'],creation_time=state['sampled_time'],
            storage='accepted' if 'enrollment' in receipts else 'not-yet-observed',
            publication='observed' if state['snapshot'] else 'not-yet-observed',
            metadata='ready-observed' if 'metadata-ready' in json.loads(state['observations']) else 'not-yet-observed',
            coherent_view='selected' if state['view'] else 'not-yet-observed',native_success=row['result'] is not None)
