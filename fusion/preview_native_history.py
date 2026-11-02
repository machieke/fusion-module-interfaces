"""Native-session administrative history through C1 and AtomStorage ports."""
from datetime import datetime, timezone
import json
import re
import uuid
from pathlib import Path
from .contracts import canonical, digest, require
from .ports import Mutation
from . import memory_contracts as c
from .preview_history import PROFILE
from .preview_atoms import client as atom_client


def write_body(atoms, scope, identity, data):
    """Bounded administrative-record chunks within the unchanged atom limit."""
    from .lookup_contracts import MAX_BYTES
    require(0<len(data)<=65536,'OVERLOADED')
    if len(data)<=MAX_BYTES:return atoms.create(Mutation(scope,identity),'application/omega-session-data-v1',data)
    refs=[]
    for number,offset in enumerate(range(0,len(data),MAX_BYTES)):
        refs.append(atoms.create(Mutation(scope,identity+'/chunk/'+str(number)),
            'application/omega-session-chunk-v1',data[offset:offset+MAX_BYTES])['ref'])
    manifest=canonical(dict(profile='omega-session-chunks/1',bytes=len(data),sha256=digest(data),chunks=refs))
    require(len(manifest)<=MAX_BYTES,'OVERLOADED')
    return atoms.create(Mutation(scope,identity),'application/omega-session-chunks-v1',manifest)


def read_body(atoms, ref):
    item=atoms.get(ref)
    if item.content_type=='application/omega-session-data-v1':return json.loads(item.bytes)
    require(item.content_type=='application/omega-session-chunks-v1','NOT_AVAILABLE')
    value=json.loads(item.bytes)
    require(set(value)=={'profile','bytes','sha256','chunks'} and value['profile']=='omega-session-chunks/1','NOT_AVAILABLE')
    require(type(value['chunks']) is list and 1<=len(value['chunks'])<=16,'NOT_AVAILABLE')
    chunks=[]
    from .contracts import validate_ref
    for ref0 in value['chunks']:
        validate_ref(ref0,ref['scope_ref']);chunk=atoms.get(ref0)
        require(chunk.content_type=='application/omega-session-chunk-v1','NOT_AVAILABLE');chunks.append(chunk.bytes)
    data=b''.join(chunks)
    require(len(data)==value['bytes'] and len(data)<=65536 and digest(data)==value['sha256'],'NOT_AVAILABLE')
    return json.loads(data)


class NativeHistory:
    def __init__(self, app, port):
        self.app,self.db,self.port=app,app.db,port
        self.scope=app.preview_config['scope']
        self.atom_path=Path(app.config['history_atoms_config'])
        require(self.atom_configuration()==app.binding['history_atoms'],'CONFLICT')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS preview_history_episode(value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_history_outbox(
                ordinal INTEGER PRIMARY KEY,identity TEXT UNIQUE NOT NULL,intent TEXT NOT NULL,receipt TEXT);
            CREATE TABLE IF NOT EXISTS preview_history_contexts(turn INTEGER PRIMARY KEY,snapshot TEXT NOT NULL);
        ''')

    def atom_configuration(self):
        cfg=json.loads(self.atom_path.read_text())
        return {k:v for k,v in cfg.items() if k!='credential'}

    def atoms(self, deadline=None):
        require(self.atom_configuration()==self.app.binding['history_atoms'],'CONFLICT')
        return atom_client(json.loads(self.atom_path.read_text()),deadline_ms=deadline)

    def episode(self, deadline=None):
        # Current C1 authority is checked even for the application cache.
        require(self.port.call('authorize','recordEpisode',deadline=deadline)=={'authorized':True},'UNAUTHORIZED')
        old=self.db.execute('SELECT value FROM preview_history_episode').fetchone()
        if old:return json.loads(old[0])
        receipt=self.port.call('recordEpisode',Mutation(self.scope,'history-session/'+self.app.session),'native-session-'+self.app.session,deadline=deadline)
        c.episode_ref(receipt['ref'],self.scope)
        require(receipt['head']==0,'NOT_AVAILABLE')
        with self.db:self.db.execute('INSERT INTO preview_history_episode VALUES(?)',(canonical(receipt['ref']).decode(),))
        return receipt['ref']

    def handle(self):
        from .preview_handles import derive
        return derive('episode',self.scope,self.episode())

    def resolve(self,handle):
        from .preview_handles import parse,make,derive
        parsed=parse(handle)
        require(parsed.kind in ('episode','event'),'INVALID_ARGUMENT')
        episode=self.episode()
        snapshot=self.port.call('historySnapshot',episode)
        if parsed.kind=='episode':
            require(handle==derive('episode',self.scope,episode),'NOT_FOUND')
            return make('episode',self.scope,self.app.binding['principal'],episode)
        found=[]
        for raw, in self.db.execute('SELECT receipt FROM preview_history_outbox WHERE receipt IS NOT NULL'):
            evidence=json.loads(raw)['evidence']
            if derive('event',self.scope,evidence)==handle:found.append(evidence)
        if not found and self.app.evidence_enabled:
            return self.app.evidence.resolve_source(handle)
        require(len(found)==1,'NOT_FOUND' if not found else 'CONFLICT')
        evidence=found[0]
        page=self.port.call('readHistory',snapshot,evidence['sequence'],1)
        require(len(page['events'])==1 and page['events'][0]['event']['evidence']==evidence,'NOT_AVAILABLE')
        return make('event',self.scope,self.app.binding['principal'],evidence)

    def record(self, identity, kind, body, *, deadline):
        require(type(deadline) is int and deadline>body['observed_ms'],'INVALID_ARGUMENT')
        episode=self.episode(deadline)
        # Delivery keeps the accepted input's original window, including after
        # interruption. No fresh transport clock is manufactured by draining.
        wire=canonical(dict(kind=kind,body=body,deadline=deadline)).decode()
        with self.db:
            old=self.db.execute('SELECT intent FROM preview_history_outbox WHERE identity=?',(identity,)).fetchone()
            if old:require(old[0]==wire,'CONFLICT')
            else:
                count=self.db.execute('SELECT count(*) FROM preview_history_outbox').fetchone()[0]
                require(count<c.MAX_EVENTS,'OVERLOADED')
                self.db.execute('INSERT INTO preview_history_outbox VALUES(?,?,?,NULL)',(count+1,identity,wire))
        self.drain(episode)

    def drain(self, episode=None):
        episode=episode or self.episode()
        rows=self.db.execute('SELECT * FROM preview_history_outbox WHERE receipt IS NULL ORDER BY ordinal').fetchall()
        for row in rows:
            value=json.loads(row['intent']);ordinal=row['ordinal']
            require(type(value.get('deadline')) is int,'UNSUPPORTED_PROFILE')
            deadline=value['deadline']
            previous=self.db.execute('SELECT receipt FROM preview_history_outbox WHERE ordinal=?',(ordinal-1,)).fetchone()
            causes=[] if previous is None else [json.loads(previous[0])['evidence']['event_ref']]
            data=canonical(dict(profile=PROFILE,session=self.app.session,identity=row['identity'],body=value['body']))
            stored=write_body(self.atoms(deadline),self.scope,'history-data/'+row['identity'],data)
            # Logical time is the bound input observation, never a retry clock.
            observed=value['body']['observed_ms']
            stamp=datetime.fromtimestamp(observed/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
            receipt=self.port.call('appendHistory',Mutation(self.scope,'history/'+row['identity']),episode,ordinal-1,
                row['identity'],value['kind'],stored['ref'],causes,stamp,deadline=deadline)
            c.evidence_ref(receipt['evidence'],self.scope)
            require(receipt['head']==ordinal and receipt['evidence']['episode']==episode and
                    receipt['evidence']['occurrence_id']==row['identity'] and receipt['delivery_id'] is None,'NOT_AVAILABLE')
            self.app.hook('after_history_provider_commit')
            with self.db:self.db.execute('UPDATE preview_history_outbox SET receipt=? WHERE identity=?',
                (canonical(receipt).decode(),row['identity']))

    def input(self):
        value=self.app.preview.input.source()
        self.record(value['occurrence']+'/input','input-receipt',dict(observed_ms=value['accepted'],
            source_id=value['occurrence'],text=value['payload']['text'],assignment=value['assignment']),deadline=value['deadline'])

    def model(self):
        row=self.app.model.row();value=self.app.preview.input.source()
        require(row is not None and row['result'] is not None,'NOT_AVAILABLE')
        self.record(row['id']+'/proposal','model-proposal',dict(observed_ms=value['accepted'],
            source_id=value['occurrence'],model_id=row['id'],capture=json.loads(row['result'])),deadline=value['deadline'])

    def commands(self, turn, results=False):
        source=json.loads(self.db.execute('SELECT source FROM preview_native_inputs WHERE turn=?',(turn,)).fetchone()[0])
        for row in self.db.execute('SELECT * FROM app_occurrences WHERE turn=? ORDER BY position',(turn,)).fetchall():
            body=dict(observed_ms=source['accepted'],source_id=source['occurrence'],occurrence=row['id'],position=row['position'])
            if results:
                require(row['done']==1 and row['result'] is not None,'NOT_AVAILABLE');body['result']=row['result']
            else:body['intent']=json.loads(row['premises'])
            self.record(row['id']+('/result' if results else '/admission'), 'tool-result' if results else 'command-admitted',body,deadline=source['deadline'])
            if results:
                intent=json.loads(row['premises'])
                from .preview_application import APPLICATION
                if intent.get('profile')==APPLICATION and intent.get('operation')=='delegate':
                    key='task/'+row['id']
                    publication=self.db.execute('SELECT record,ref,receipt FROM preview_task_outbox WHERE id=?',(key,)).fetchone()
                    require(publication is not None and publication['ref'] is not None and publication['receipt'] is not None,'NOT_AVAILABLE')
                    self.task_publication(key,json.loads(publication['record']),json.loads(publication['ref']),
                        json.loads(publication['receipt']),source)

    def task_publication(self, key, task, ref, receipt, source):
        """Observe a committed mailbox effect, separately from its tool result.

        This is neither recipient consumption nor empirical corroboration. The
        event retains the input's logical observation time and the task's
        original (possibly narrower) deadline; draining cannot renew either.
        """
        require(source['accepted']<task['deadline']<=source['deadline'],'CONFLICT')
        self.record(key+'/external-effect','external-effect',dict(
            observed_ms=source['accepted'],source_id=source['occurrence'],
            effect='durable-task-mailbox-acceptance',task=task['id'],kind=task['kind'],
            sender=task['sender'],recipient=task['recipient'],payload=ref,
            acceptance=receipt,recipient_consumption='NOT_OBSERVED',
            independent_corroboration=False),deadline=task['deadline'])

    def read(self, selector='current', snapshot=None):
        if selector=='current': start=1
        else:
            match=re.fullmatch(r'(oh1:episode:[0-9a-f-]{36})@([0-9]+):([0-9]+)',selector)
            require(match is not None and match[1]==self.handle(),'NOT_FOUND')
            from .preview_ports import descriptor
            from .registry import selection_token
            snapshot=dict(profile=PROFILE,episode=self.episode(),through=int(match[2]),selection=selection_token(descriptor('episodic.memory')))
            start=int(match[3])
        snapshot=snapshot or self.port.call('historySnapshot',self.episode())
        page=self.port.call('readHistory',snapshot,start,4)
        require(page['snapshot']==snapshot and type(page['events']) is list and len(page['events'])<=4,'NOT_AVAILABLE')
        entries=[]
        for item in page['events']:
            record=item['event'];c.evidence_record(record,record['evidence'])
            body=read_body(self.atoms(),item['payload'])
            require(body['profile']==PROFILE and body['session']==self.app.session,'UNAUTHORIZED')
            wire=canonical(body['body'])
            from .preview_handles import derive
            entries.append(dict(kind=item['kind'],sequence=record['evidence']['sequence'],
                event_handle=derive('event',self.scope,record['evidence']),
                evidence=record['evidence'],payload=item['payload'],body=body['body'] if len(wire)<=1536 else None,
                body_omitted=len(wire)>1536,body_sha256=digest(wire),body_bytes=len(wire)))
        return dict(profile=PROFILE,episode=self.handle(),ref=self.episode(),snapshot=snapshot,events=entries,
            next_selector=self.handle()+'@'+str(snapshot['through'])+':'+str(page['next_sequence']) if page['next_sequence'] is not None else None,
            complete=page['complete'],interpretation='administrative-history-not-empirical-evidence')

    def context(self):
        turn=self.app.processing_slot()
        old=self.db.execute('SELECT snapshot FROM preview_history_contexts WHERE turn=?',(turn,)).fetchone()
        if old:snapshot=json.loads(old[0])
        else:
            snapshot=self.port.call('historySnapshot',self.episode())
            with self.db:self.db.execute('INSERT INTO preview_history_contexts VALUES(?,?)',(turn,canonical(snapshot).decode()))
        selector=self.handle()+'@'+str(snapshot['through'])+':'+str(max(1,snapshot['through']-3))
        value=self.read(selector,snapshot=snapshot)
        value['context_window']='last-four-committed-events'
        value['omitted_bodies']=[]
        for entry in value['events']:
            if len(canonical(value))<=8192:break
            if entry['body'] is not None:
                entry['body']=None;entry['body_omitted']=True
                value['omitted_bodies'].append(entry['event_handle'])
        require(len(canonical(value))<=8192,'OVERLOADED')
        return canonical(value).decode().replace(':-:-:-:', '\\u003a-\\u003a-\\u003a-\\u003a')
