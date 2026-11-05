"""Application-owned task publication and captured native-query return.

The recorded model never supplies a result value. Every report is constructed
from the same application's committed query occurrence and retained view.
"""
import json,time
from pathlib import Path
from .contracts import canonical,digest,require,ContractError
from .preview_tasks import Client,PROFILE,record,correlated
from .preview_native_history import write_body,read_body


class NativeTasks:
    def __init__(self,app):
        self.app,self.db=app,app.db;self.port=Client(app.config['task_config'])
        require(self.port.frozen==app.binding['tasks'],'CONFLICT')
        self.db.executescript('''CREATE TABLE IF NOT EXISTS preview_task_outbox(
            id TEXT PRIMARY KEY,record TEXT NOT NULL,calls INTEGER NOT NULL DEFAULT 0,ref TEXT,receipt TEXT,wake TEXT);''')
    def authorize(self):
        self.app.preview.authorize('tasks');require(self.port.call('authorize')=={'authorized':True},'UNAUTHORIZED')
    def reserve(self,key,deadline,*,observe=False,input_source=None):
        if not observe:
            if input_source is None:self.app.preview.input.execution_permit()
            else:self.app.preview.input.execution_permit(input_source)
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            row=self.db.execute('SELECT * FROM preview_task_outbox WHERE id=?',(key,)).fetchone()
            require(row is not None and row['calls']<24,'OVERLOADED')
            if not observe:require(time.time_ns()//1_000_000<deadline,'DEADLINE_EXCEEDED')
            self.db.execute('UPDATE preview_task_outbox SET calls=calls+1 WHERE id=?',(key,))
        self.app.hook('after_task_relay_reservation');return row
    def publish(self,body,*,input_source=None):
        self.authorize();record(body,self.app.preview_config['scope']);key=body['kind']+'/'+body['id'];wire=canonical(body).decode()
        with self.db:
            old=self.db.execute('SELECT record FROM preview_task_outbox WHERE id=?',(key,)).fetchone()
            require(old is None or old[0]==wire,'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO preview_task_outbox(id,record) VALUES(?,?)',(key,wire))
        self.app.hook('after_task_outbox_bind')
        state=self.db.execute('SELECT * FROM preview_task_outbox WHERE id=?',(key,)).fetchone()
        if state['ref'] is None:
            self.reserve(key,body['deadline'],input_source=input_source);stored=write_body(self.app.preview.memory.atoms(body['deadline']),body['scope'],key,canonical({'body':body}))['ref']
            with self.db:self.db.execute('UPDATE preview_task_outbox SET ref=? WHERE id=?',(canonical(stored).decode(),key))
            self.app.hook('after_task_payload_capture')
        else:stored=json.loads(state['ref'])
        if state['receipt'] is None:
            self.reserve(key,body['deadline'],observe=True)
            receipt=self.port.call('published',key,stored,body['recipient'],body['deadline'],body['id'])
            if receipt is None:
                self.reserve(key,body['deadline'],input_source=input_source)
                receipt=self.port.call('send',key,stored,body['recipient'],body['deadline'],body['id'],deadline=body['deadline'])
            with self.db:self.db.execute('UPDATE preview_task_outbox SET receipt=? WHERE id=?',(canonical(receipt).decode(),key))
            self.app.hook('after_task_publication_capture')
        else:receipt=json.loads(state['receipt'])
        if state['wake'] is None and time.time_ns()//1_000_000>=body['deadline']:
            wake=dict(status='NOT_OBSERVED',code='DEADLINE_EXCEEDED',mailbox_acceptance_retained=True)
        elif state['wake'] is None:
            self.reserve(key,body['deadline'],input_source=input_source);cfg,_=self.port.current();target=cfg['recipients'][body['recipient']]
            from .preview_transport import invoke
            q=dict(profile=PROFILE,id=body['id'])
            try:
                wake=invoke(target,'/preview/task-ingress',q,body['deadline'])
                require(type(wake) is dict and set(wake)=={'profile','id','principal','status'} and wake['profile']==PROFILE and
                    wake['id']==body['id'] and wake['principal']==body['recipient'] and wake['status'] in ('accepted','empty','refused','observed-late-result'),'NOT_AVAILABLE')
            except ContractError as error:
                # Publication is an observed commit; failed hint never resends.
                wake=dict(status='NOT_AVAILABLE',code=error.code,mailbox_acceptance_retained=True)
            with self.db:self.db.execute('UPDATE preview_task_outbox SET wake=? WHERE id=?',(canonical(wake).decode(),key))
        else:wake=json.loads(state['wake'])
        return dict(status='TASK_PUBLISHED' if body['kind']=='task' else 'RESULT_PUBLISHED',task=body['id'],ref=stored,
            acceptance=receipt,recipient_observation=wake,deadline=body['deadline'],independent_corroboration=False)
    def delegate(self,row,args):
        self.authorize();require(args['recipient']!=self.app.binding['principal'],'UNAUTHORIZED')
        # Native startup rehydrates the prior completed tool result while the
        # newly accepted input may itself be the correlated agent report.
        # Observation cannot turn that report into recursive delegation.
        if row['result'] is not None:return row['result']
        source=self.app.preview.input.source();require('task_origin' not in source,'UNAUTHORIZED')
        plan=self.db.execute('SELECT view FROM preview_memory_plans WHERE identity=?',('input-'+source['occurrence'],)).fetchone()
        require(plan is not None and plan[0] is not None,'NOT_AVAILABLE')
        view=json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(plan[0],)).fetchone()[0])
        body=dict(profile=PROFILE,kind='task',scope=self.app.preview_config['scope'],id=row['id'],sender=self.app.binding['principal'],
            recipient=args['recipient'],session=self.app.session,deadline=row['deadline'],parent=source['occurrence'],
            limits=dict(queries=1,relay_calls=24,recursive_delegation=False),query=args['query'],minimum=view['snapshot'])
        return canonical(self.publish(body)).decode()
    def complete(self,input_row):
        source=json.loads(input_row['source']);origin=source.get('task_origin')
        if origin is None or origin['record']['kind']!='task':return
        task=record(origin['record'],self.app.preview_config['scope'])
        rows=self.db.execute('SELECT * FROM app_occurrences WHERE turn=? ORDER BY position',(input_row['turn'],)).fetchall()
        require(len(rows)==1 and rows[0]['done']==1 and rows[0]['result'] is not None,'NOT_AVAILABLE')
        row=rows[0];intent=json.loads(row['premises'])
        from .preview_vector_contracts import PROFILE as QUERY_PROFILE
        require(intent['profile']==QUERY_PROFILE and intent['operation']=='query_with_ids_and_dists' and intent['arguments']['query']==task['query'],'UNAUTHORIZED')
        view=self.app.write.view_for(row);self.app.memory.authorize(row)
        captured=self.db.execute('SELECT payloads,candidates FROM app_memory_reads WHERE id=?',(row['id'],)).fetchone()
        require(captured is not None and captured['payloads'] is not None,'NOT_AVAILABLE')
        candidates=json.loads(captured['candidates'])
        refs=[hit['ref'] for hit in candidates['hits']]
        result=dict(profile=PROFILE,kind='result',scope=task['scope'],id=task['id'],sender=task['recipient'],recipient=task['sender'],
            session=self.app.session,deadline=task['deadline'],parent=task['parent'],limits=task['limits'],task=origin['ref'],
            view=view['snapshot'],projection=row['result'],payloads=refs,status='captured-native-query')
        correlated(result,task,origin['ref']);self.publish(result,input_source=source)
    def input(self):
        source=self.app.preview.input.source();origin=source.get('task_origin')
        if origin is None:return
        body=record(origin['record'],self.app.preview_config['scope']);self.authorize()
        require(read_body(self.app.preview.memory.atoms(),origin['ref'])['body']==body,'CONFLICT')
        if body['kind']=='task':
            view=self.app.preview.memory.input()
            for name in ('head','lifecycle'):
                a,b=view['snapshot'][name],body['minimum'][name]
                require(a['source']==b['source'] and a['sequence']>=b['sequence'],'NOT_AVAILABLE')
        else:
            task=record(read_body(self.app.preview.memory.atoms(),body['task'])['body'],body['scope']);correlated(body,task,body['task'])
            old=self.db.execute('SELECT ref FROM preview_task_outbox WHERE id=?',('task/'+body['id'],)).fetchone()
            require(old is not None and json.loads(old[0])==body['task'],'UNAUTHORIZED')
            # Release only payloads still visible in the recipient's active view.
            view=self.app.preview.memory.input();visible={canonical(h['envelope']['target']['payload']) for h in view['handles'].values()}
            self.app.preview.memory.call('input-'+source['occurrence'],'search','authorize',task['query'],view['snapshot'],bounded=False)
            for ref in body['payloads']:
                require(canonical(ref) in visible,'UNAUTHORIZED');self.app.preview.memory.atoms().get(ref)

    def report(self,task_id):
        """Observe an already consumed correlated report for a new typed tool.

        Only the local application's accepted/captured input records are read.
        Every payload release rechecks the remote active-view authority.
        """
        self.authorize();found=[]
        for row in self.db.execute('SELECT i.source FROM preview_native_inputs i JOIN app_turns t ON t.id=i.turn WHERE i.acknowledged=1 AND t.projection IS NOT NULL'):
            origin=json.loads(row['source']).get('task_origin')
            if origin and origin['record']['kind']=='result' and origin['record']['id']==task_id:found.append(origin)
        require(len(found)==1,'NOT_FOUND' if not found else 'CONFLICT')
        origin=found[0];body=record(origin['record'],self.app.preview_config['scope'])
        require(read_body(self.app.preview.memory.atoms(),origin['ref'])['body']==body,'CONFLICT')
        task=record(read_body(self.app.preview.memory.atoms(),body['task'])['body'],body['scope']);correlated(body,task,body['task'])
        own=self.db.execute('SELECT ref FROM preview_task_outbox WHERE id=?',('task/'+task_id,)).fetchone()
        require(own is not None and json.loads(own[0])==body['task'] and body['recipient']==self.app.binding['principal'],'UNAUTHORIZED')
        source=self.app.preview.input.source();view=self.app.preview.memory.input()
        self.app.preview.memory.call('input-'+source['occurrence'],'search','authorize',task['query'],view['snapshot'],bounded=False)
        visible={canonical(h['envelope']['target']['payload']) for h in view['handles'].values()}
        require(all(canonical(ref) in visible for ref in body['payloads']),'UNAUTHORIZED')
        return dict(origin=origin,task=task)
