"""One typed native inspect_atom call over an application-derived shared artifact.

The application never signs, submits chain deploys, reads provider journals, or
constructs inspection results. Saved requests retain occurrence/deadline/budget.
"""
import json,time
from .contracts import canonical,digest,require,ContractError
from .ports import Mutation
from .client import Peer
from .preview_inspect import Client
from . import preview_artifact_contracts as a,vector_contracts as v


class NativeInspection:
    def __init__(self,app):
        self.app,self.db=app,app.db;self.client=Client(app.config['inspect_config'])
        require(self.client.frozen==app.binding['inspection'],'CONFLICT')
        self.db.execute('''CREATE TABLE IF NOT EXISTS preview_inspections(
            occurrence TEXT PRIMARY KEY,task TEXT NOT NULL,artifact TEXT,artifact_ref TEXT,request TEXT,
            acceptance TEXT,result TEXT,completion TEXT,ack TEXT,calls INTEGER NOT NULL DEFAULT 0);''')
    def state(self,row):return self.db.execute('SELECT * FROM preview_inspections WHERE occurrence=?',(row['id'],)).fetchone()
    def admit(self,identity,task):
        self.db.execute('INSERT INTO preview_inspections(occurrence,task) VALUES(?,?)',(identity,task))
    def reserve(self,row,*,effect=False):
        if effect:require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');state=self.state(row);require(state['calls']<32,'OVERLOADED')
            self.db.execute('UPDATE preview_inspections SET calls=calls+1 WHERE occurrence=?',(row['id'],))
        self.app.hook('after_inspect_relay_reservation')
    def save(self,row,column,value):
        require(column in ('artifact','artifact_ref','request','acceptance','result','completion','ack'))
        encoded=canonical(value).decode()
        with self.db:
            old=self.state(row)[column];require(old is None or old==encoded,'CONFLICT')
            self.db.execute('UPDATE preview_inspections SET '+column+'=? WHERE occurrence=?',(encoded,row['id']))
        self.app.hook('after_inspect_'+column+'_capture')
    @staticmethod
    def observation_pause(row):
        remaining=(row['deadline']-time.time_ns()//1_000_000)/1000
        require(remaining>0,'DEADLINE_EXCEEDED')
        # Eight reserved observations remain the hard limit. Give the durable
        # storage owner time to commit within the already accepted window.
        time.sleep(min(2,remaining/8))
    def replay(self,row,args):
        require(self.state(row)['task']==args['task'],'CONFLICT')
        self.app.preview.authorize('inspection');self.reserve(row)
        selected=self.app.preview.tasks.report(args['task']);origin,task=selected['origin'],selected['task']
        body=origin['record'];state=self.state(row)
        if state['artifact'] is None:
            require(len(body['payloads'])<=a.MAX_OBSERVATIONS,'OVERLOADED');observations=[]
            for ref in body['payloads']:
                self.reserve(row,effect=True);item=self.app.preview.memory.atoms(row['deadline']).get(ref)
                require(item.content_type==v.PAYLOAD,'NOT_AVAILABLE');payload=v.payload(json.loads(item.bytes),body['scope'],body['view']['corpus'])
                require(canonical(payload)==item.bytes,'CONFLICT')
                observations.append(dict(payload_ref=ref,content=payload['content']))
            artifact=dict(profile=a.PROFILE,scope=body['scope'],task=task['id'],query=task['query'],sender=task['sender'],reporter=body['sender'],
                result_ref=origin['ref'],view=body['view'],observations=observations)
            self.save(row,'artifact',a.record(artifact,body['scope']))
        artifact=a.record(json.loads(self.state(row)['artifact']),body['scope']);raw=a.encode(artifact)
        require(artifact['result_ref']==origin['ref'] and artifact['task']==task['id'] and artifact['view']==body['view'],'CONFLICT')
        if self.state(row)['artifact_ref'] is None:
            self.reserve(row,effect=True)
            stored=self.app.preview.memory.atoms(row['deadline']).create(Mutation(body['scope'],'inspect-artifact/'+row['id']),a.PROFILE,raw)
            self.save(row,'artifact_ref',stored['ref'])
        ref=json.loads(self.state(row)['artifact_ref']);self.reserve(row)
        item=self.app.preview.memory.atoms().get(ref);require(item.bytes==raw and item.content_type==a.PROFILE,'NOT_AVAILABLE')
        peer=Peer(self.client,body['scope'],'inspect-'+self.app.binding['principal'])
        if self.state(row)['request'] is None:
            request=peer.request('execution','submit',dict(operation='inspect_atom',ref=ref),row['id'],row['id'],deadline_ms=row['deadline'])
            self.save(row,'request',request)
        request=json.loads(self.state(row)['request'])
        if self.state(row)['acceptance'] is None:
            # The exact submit request can observe a prior owner acceptance even
            # after expiry; the owner refuses a previously unaccepted effect.
            self.reserve(row);self.save(row,'acceptance',self.client.invoke(request))
        acceptance=json.loads(self.state(row)['acceptance']);job=acceptance['job_id']
        if self.state(row)['result'] is None:
            for _ in range(8):
                self.reserve(row)
                try:status=peer.status(job)
                except ContractError as error:
                    if error.code not in ('NOT_AVAILABLE','OVERLOADED'):raise
                    self.observation_pause(row);continue
                if status['execution']=='succeeded':
                    self.reserve(row);self.save(row,'result',peer.result(job));break
                require(status['execution']=='queued','NOT_AVAILABLE')
                self.observation_pause(row)
            require(self.state(row)['result'] is not None,'NOT_AVAILABLE')
        result=json.loads(self.state(row)['result']);self.reserve(row)
        output=self.app.preview.memory.atoms().get(result['ref'])
        require(output.content_type=='application/json' and output.bytes==canonical(dict(digest=digest(raw),length=len(raw),operation='inspect_atom',provider_version='0.1.0')),'NOT_AVAILABLE')
        if self.state(row)['completion'] is None:
            for _ in range(8):
                self.reserve(row)
                try:delivery=peer.poll()
                except ContractError as error:
                    if error.code not in ('NOT_AVAILABLE','OVERLOADED'):raise
                    self.observation_pause(row);continue
                if delivery is not None:
                    require(delivery['body']['job_id']==job and delivery['body']['result']==result and delivery['body']['error'] is None and
                        delivery['body']['correlation_id']==row['id'] and delivery['body']['causation_id']==request['message_id'],'NOT_AVAILABLE')
                    self.save(row,'completion',delivery);break
                self.observation_pause(row)
            require(self.state(row)['completion'] is not None,'NOT_AVAILABLE')
        delivery=json.loads(self.state(row)['completion'])
        if self.state(row)['ack'] is None:
            self.reserve(row);self.save(row,'ack',peer.ack(delivery['delivery_id'],'inspection/'+row['id']))
        return canonical(dict(status='INSPECTED_ARTIFACT',task=task['id'],artifact=ref,artifact_bytes=len(raw),inspection=result,
            job_id=job,completion=delivery['delivery_id'],caller_acknowledged=True,chain='NOT_SUBMITTED',approval='NOT_GRANTED')).decode()
