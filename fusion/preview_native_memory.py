"""Native memory view selection over owned lifecycle, Search and AtomStorage.

The application captures provider replies and maintains presentation metadata.
It never opens a foreign journal. Compatibility priors are explicitly labelled,
not imported empirical evidence. Numerical query/enrichment stays native.
"""
from fusion.native_telemetry import traced
import json
from pathlib import Path
import time
from . import vector_contracts as v,preview_vector_contracts as c
from .contracts import canonical,digest,require
from .ports import Mutation
from .registry import selection_token
from .preview_memory_services import Client,descriptor
from .preview_atoms import client as atoms_client
from .preview_handles import make
from .neoclaw_append import MemoryAppend
from .neoclaw_memory import MemoryRead


def bindings(config):return {n:Client(p,n).frozen for n,p in config['active_memory_configs'].items()}


class SharedMemory:
    def __init__(self,app):
        self.app,self.db=app,app.db;self.scope=app.preview_config['scope']
        self.clients={n:Client(p,n) for n,p in app.config['active_memory_configs'].items()}
        require(bindings(app.config)==app.binding['active_memory'],'CONFLICT')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS preview_memory_plans(identity TEXT PRIMARY KEY,deadline INTEGER NOT NULL,
                calls INTEGER NOT NULL DEFAULT 0,plan TEXT,snapshot TEXT,view TEXT);
            CREATE TABLE IF NOT EXISTS preview_memory_receipts(occurrence TEXT PRIMARY KEY,lifecycle TEXT NOT NULL,result TEXT);
            CREATE TABLE IF NOT EXISTS preview_memory_handles(handle TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_lifecycle_acceptances(occurrence TEXT PRIMARY KEY,value TEXT NOT NULL);
        ''')

    def atoms(self,deadline=None):
        cfg=json.loads(Path(self.app.config['memory_atoms_config']).read_text())
        require({k:v0 for k,v0 in cfg.items() if k!='credential'}==self.app.binding['memory_atoms'],'CONFLICT')
        return atoms_client(cfg,deadline)

    def call(self,identity,name,operation,*args,bounded=True):
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row=self.db.execute('SELECT * FROM preview_memory_plans WHERE identity=?',(identity,)).fetchone()
            require(row is not None and row['calls']<96,'OVERLOADED')
            if bounded:require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
            self.db.execute('UPDATE preview_memory_plans SET calls=calls+1 WHERE identity=?',(identity,))
        self.app.hook('after_shared_view_reservation')
        return self.clients[name].call(operation,*args,deadline=row['deadline'] if bounded else None)

    def open_plan(self,identity,deadline):
        with self.db:
            row=self.db.execute('SELECT deadline FROM preview_memory_plans WHERE identity=?',(identity,)).fetchone()
            require(row is None or row[0]==deadline,'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO preview_memory_plans(identity,deadline) VALUES(?,?)',(identity,deadline))

    def prepare(self,identity,deadline):
        self.open_plan(identity,deadline)
        row=self.db.execute('SELECT * FROM preview_memory_plans WHERE identity=?',(identity,)).fetchone()
        if row['view'] is not None:return json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(row['view'],)).fetchone()[0])
        if row['plan'] is None:
            head=self.call(identity,'memory.lifecycle','head')
            membership=self.call(identity,'memory.lifecycle','activeSet',head)
            require(len(membership['active'])<=16,'OVERLOADED')
            if head['sequence']:
                page=self.call(identity,'memory.lifecycle','readEvents',head['sequence']-1,head,1)
                require(page['complete'] and len(page['events'])==1 and page['at']==head,'NOT_AVAILABLE')
                through=page['events'][0]['source_head']
            else:
                through=self.atoms(deadline).head(self.scope);through['sequence']=0
            plan=dict(head=head,membership=membership,through=through)
            with self.db:self.db.execute('UPDATE preview_memory_plans SET plan=? WHERE identity=?',(canonical(plan).decode(),identity))
            self.app.hook('after_shared_view_bind')
        else:plan=json.loads(row['plan'])
        if row['snapshot'] is None:
            snapshot=self.call(identity,'search','current',plan['head'])
            if snapshot is None:
                snapshot=self.call(identity,'search','published',plan['through'],plan['head'],identity)
                if snapshot is None:snapshot=self.call(identity,'search','build',plan['through'],plan['head'],identity,deadline)
            c.snapshot(snapshot,self.scope)
            require(snapshot['head']==plan['through'] and snapshot['lifecycle']==plan['head'] and
                snapshot['active_digest']==digest(canonical(plan['membership'])),'NOT_AVAILABLE')
            with self.db:self.db.execute('UPDATE preview_memory_plans SET snapshot=? WHERE identity=?',(canonical(snapshot).decode(),identity))
            self.app.hook('after_shared_view_publication')
        else:snapshot=json.loads(row['snapshot'])
        self.call(identity,'search','ready',snapshot)
        records=[];handles={};defaults={}
        for member in plan['membership']['active']:
            self.call(identity,'memory.lifecycle','disclose',member['logical_id'],{k:member[k] for k in ('uuid','payload','enrollment')},plan['head'],False)
            item=self.atoms(deadline).get(member['payload']);require(item.content_type==v.PAYLOAD,'NOT_AVAILABLE')
            payload=v.payload(json.loads(item.bytes),self.scope,snapshot['corpus'])
            require(canonical(payload)==item.bytes and payload['uuid']==member['uuid'],'NOT_AVAILABLE')
            handle=make('memory',self.scope,self.app.binding['principal'],{k:member[k] for k in ('enrollment','payload')})
            structure=self.app.preview.relations.presentation(member['payload']) if self.app.preview.relations else None
            handles[payload['uuid']]=dict(envelope=handle,logical_id=member['logical_id'],revision=member['revision'],time=payload['time'],uuid=payload['uuid'],structure=structure)
            links=[payload['time']]+([x['history']['handle'] for x in structure['links']] if structure else [])
            records.append(dict(uuid=payload['uuid'],links=links,stv=[1.,.5],promotion=0.))
            defaults[payload['uuid']]='neoclaw-fresh-memory-compatibility-prior/1:not-empirical'
        cognition=self.app.evidence.refresh(records,handles) if self.app.evidence_enabled else dict(defaults=defaults)
        manifest=dict(records=records,promotion_time=0.)
        from .adapters.neoclaw_metadata import collection
        cfg,_=self.app.write.settings();collection(cfg['metadata_root'],manifest,prepare=True,deadline=deadline)
        view=dict(snapshot=snapshot,metadata=manifest,metadata_seal=digest(canonical(manifest)),handles=handles,**cognition)
        if self.app.evidence_enabled:self.app.evidence.materialize(view,deadline)
        key=digest(canonical(view))
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO app_read_views VALUES(?,?)',(key,canonical(view).decode()))
            self.db.execute('UPDATE app_active_view SET view=? WHERE singleton=1',(key,))
            self.db.execute('UPDATE preview_memory_plans SET view=? WHERE identity=?',(key,identity))
            for h in handles.values():
                envelope=h['envelope'];prior=self.db.execute('SELECT value FROM preview_memory_handles WHERE handle=?',(envelope['handle'],)).fetchone()
                encoded=canonical(envelope).decode();require(prior is None or prior[0]==encoded,'CONFLICT')
                self.db.execute('INSERT OR IGNORE INTO preview_memory_handles VALUES(?,?)',(envelope['handle'],encoded))
        self.app.hook('after_shared_view_selection');return view

    @traced('memory.select_view')
    def input(self):
        source=self.app.preview.input.source()
        return self.prepare('input-'+source['occurrence'],source['deadline'])

    def written(self,row):
        state=self.app.write.state(row);receipts=json.loads(state['receipts'])
        require('enrollment' in receipts,'NOT_AVAILABLE')
        identity='write-'+row['id'];self.open_plan(identity,row['deadline'])
        update=json.loads(row['premises'])['operation']=='update'
        prior=json.loads(self.db.execute('SELECT value FROM preview_lifecycle_acceptances WHERE occurrence=?',(row['id'],)).fetchone()[0]) if update else None
        receipt=self.call(identity,'memory.lifecycle','change',Mutation(self.scope,identity),'supersede' if update else 'introduce',
            dict(logical_id=prior['logical_id'] if prior else None,expected_revision=prior['revision'] if prior else 0,
                enrollment=receipts['enrollment']['ref'],deadline_ms=row['deadline']))
        require(receipt['memory']['enrollment']==receipts['enrollment']['ref'] and receipt['memory']['uuid']==state['uuid'],'NOT_AVAILABLE')
        with self.db:
            old=self.db.execute('SELECT lifecycle FROM preview_memory_receipts WHERE occurrence=?',(row['id'],)).fetchone()
            encoded=canonical(receipt).decode();require(old is None or old[0]==encoded,'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO preview_memory_receipts VALUES(?,?,NULL)',(row['id'],encoded))
        view=self.prepare(identity,row['deadline'])
        own=view['handles'][state['uuid']]
        result=canonical(dict(status='MEMORY-SUPERSEDED' if update else 'REMEMBER-SUCCESS',memory=own['envelope'],logical_id=own['logical_id'],revision=own['revision'],
            source=view['snapshot']['head'],snapshot=view['snapshot'],publication='observed',metadata='ready',
            prior='labelled-compatibility-not-empirical')).decode()
        with self.db:self.db.execute('UPDATE preview_memory_receipts SET result=? WHERE occurrence=?',(result,row['id']))
        return view

    def resolve(self,handle):
        from .preview_handles import parse
        parse(handle,'memory')
        view=json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=(SELECT view FROM app_active_view)').fetchone()[0])
        found=[x for x in view.get('handles',{}).values() if x['envelope']['handle']==handle]
        require(len(found)==1,'NOT_FOUND' if not found else 'CONFLICT')
        return found[0]

    def admit(self,occurrence,handle):
        value=self.resolve(handle)
        self.db.execute('INSERT INTO preview_lifecycle_acceptances VALUES(?,?)',(occurrence,canonical(value).decode()))

    def withdraw(self,row,args):
        prior=json.loads(self.db.execute('SELECT value FROM preview_lifecycle_acceptances WHERE occurrence=?',(row['id'],)).fetchone()[0])
        require(prior['envelope']['handle']==args['target'],'CONFLICT')
        identity='withdraw-'+row['id'];self.open_plan(identity,row['deadline'])
        if row['result'] is not None:
            self.call(identity,'memory.lifecycle','head',bounded=False)
            return row['result']
        receipt=self.call(identity,'memory.lifecycle','change',Mutation(self.scope,identity),'withdraw',
            dict(logical_id=prior['logical_id'],expected_revision=prior['revision'],enrollment=None,deadline_ms=row['deadline']))
        require(receipt['logical_id']==prior['logical_id'] and receipt['state']=='withdrawn','NOT_AVAILABLE')
        view=self.prepare(identity,row['deadline'])
        return canonical(dict(status='WITHDRAWN_FROM_ACTIVE_VIEW',logical_id=prior['logical_id'],revision=receipt['revision'],
            snapshot=view['snapshot'],physical_erasure=False,history_and_captured_results_retained=True)).decode()


class PreviewAppend(MemoryAppend):
    def capture(self,value):
        row=self.current()
        if row['result'] is not None:
            require(row['result']==value,'CONFLICT');return self.replay(row)
        return super().capture(value)
    def publish_view(self,row,through):
        # The new active profile publishes only its lifecycle-authoritative
        # generation. Historical append profiles retain their original method.
        view=self.app.preview.memory.written(row);key=digest(canonical(view))
        require(view['snapshot']['head']['source']==through['source'] and view['snapshot']['head']['sequence']>=through['sequence'],'CONFLICT')
        with self.db:self.db.execute('UPDATE app_memory_writes SET snapshot=?,view=? WHERE id=?',
            (canonical(view['snapshot']).decode(),key,row['id']))
        for stage in ('search-published','read-provider-ready','metadata-ready','view-selected'):self.note(row,stage)
        self.app.hook('after_append_view_selection')
        return view
    def read_ready(self,row,snapshot):
        c.snapshot(snapshot,self.app.preview_config['scope']);self.reserve(row)
        require(self.app.preview.memory.clients['search'].call('ready',snapshot)=={'ready':True},'NOT_AVAILABLE')
        self.note(row,'read-provider-ready')
    def result_value(self,row):
        value=self.db.execute('SELECT result FROM preview_memory_receipts WHERE occurrence=?',(row['id'],)).fetchone()
        require(value is not None and value[0] is not None,'NOT_AVAILABLE');return value[0]


class PreviewRead(MemoryRead):
    def __init__(self,app):super().__init__(app,contracts=c)
    def settings(self,row=None):
        cfg,chosen=super().settings(row)
        return cfg,{**chosen,'search':descriptor('search')}
    def authorize(self,row):
        super().authorize(row)
        # Captures never substitute for current payload-owner authority.
        state=self.db.execute('SELECT candidates FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
        if state is not None and state[0] is not None:
            for hit in json.loads(state[0])['hits']:self.app.preview.memory.atoms().get(hit['ref'])
    def capture(self,value):
        row=self.current()
        if row['result'] is None:
            state=self.db.execute('SELECT payloads FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
            require(state is not None and state[0] is not None,'NOT_AVAILABLE')
            view=self.app.write.view_for(row)
            handles={x[0]:view['handles'][x[0]]['envelope'] for x in json.loads(state[0])}
            value+='\nPREVIEW_MEMORY_HANDLES: '+canonical(handles).decode()
        return super().capture(value)
    def transport(self,cfg,chosen):
        owner=self
        class Transport:
            def invoke(self,q):
                body=q['body'];op=q['operation'];memory=owner.app.preview.memory
                if q['interface_ref']['id']=='atom.storage':
                    from .contracts import encode
                    return [dict(ref=x.ref,content_type=x.content_type,data=encode(x.bytes)) for x in memory.atoms().getMany(tuple(body['refs']))]
                port=memory.clients['search']
                if op.startswith('authorize'):return port.call('authorize',body['query'],body['snapshot'])
                if op=='ready':return port.call('ready',body['snapshot'])
                require(op=='query','UNSUPPORTED_OPERATION');return port.call('query',body,deadline=body['deadline_ms'])
        return Transport()
