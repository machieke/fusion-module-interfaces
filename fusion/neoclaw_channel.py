"""S06 application input assignment and bounded native send; no IRC socket ownership."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from . import channel_contracts as c
from .channel_transport import Client,configuration
from .contracts import canonical,require


def settings(app):
    cfg,_,frozen=configuration(app.config['channel_config'])
    require(cfg['role']=='application' and cfg['principal']==app.binding['memory']['principal'],'UNAUTHORIZED')
    require(cfg['session']==app.config['session_id'],'CONFLICT')
    require(100<=app.config['channel_wait_ms']<=10000 and 1<=app.config['channel_poll_limit']<=128,'INVALID_ARGUMENT')
    frozen.update(wait_ms=app.config['channel_wait_ms'],poll_limit=app.config['channel_poll_limit'])
    return cfg,frozen


class ChannelAdoption:
    def __init__(self,app):
        self.app,self.db=app,app.db;_,frozen=settings(app);require(frozen==app.binding['channel'],'CONFLICT')
        self.client=Client(app.config['channel_config'])
        self.db.executescript('''CREATE TABLE IF NOT EXISTS app_channel_inputs(
          slot INTEGER PRIMARY KEY,id TEXT UNIQUE,delivery TEXT,envelope TEXT,ack TEXT,
          wait_deadline INTEGER,polls INTEGER DEFAULT 0,deadline INTEGER,ack_calls INTEGER DEFAULT 0);
          CREATE TABLE IF NOT EXISTS app_channel_outputs(id TEXT PRIMARY KEY,envelope TEXT,payload TEXT,acceptance TEXT,
          put_calls INTEGER DEFAULT 0,send_calls INTEGER DEFAULT 0);
        ''')
    def current(self):
        cfg,frozen=settings(self.app);require(frozen==self.app.binding['channel'],'CONFLICT');return cfg
    def slot(self):return self.app.evidence.slot()
    def input(self):return self.db.execute('SELECT * FROM app_channel_inputs WHERE slot=?',(self.slot(),)).fetchone()
    def receive(self):
        cfg=self.current();slot=self.slot();row=self.input()
        if row is None:
            require(self.db.execute('SELECT count(*) FROM app_channel_inputs').fetchone()[0]<self.app.config['turn_limit'],'OVERLOADED')
            with self.db:self.db.execute('INSERT INTO app_channel_inputs(slot,wait_deadline) VALUES(?,?)',
                                        (slot,time.time_ns()//1_000_000+self.app.config['channel_wait_ms']))
            row=self.input()
        while row['id'] is None:
            require(time.time_ns()//1_000_000<row['wait_deadline'],'DEADLINE_EXCEEDED')
            require(row['polls']<self.app.config['channel_poll_limit'],'OVERLOADED')
            with self.db:self.db.execute('UPDATE app_channel_inputs SET polls=polls+1 WHERE slot=?',(slot,))
            self.app.hook('after_channel_poll_reservation')
            delivery=self.client.poll()
            if delivery is None:time.sleep(.05);row=self.input();continue
            value=self.client.get(delivery['body']['ref']);require(value['kind']=='ingress' and value['id']==delivery['body']['correlation_id'],'CONFLICT')
            require(self.db.execute('SELECT 1 FROM app_channel_inputs WHERE id=?',(value['id'],)).fetchone() is None,'CONFLICT')
            deadline=time.time_ns()//1_000_000+self.app.config['invocation_timeout_ms']
            with self.db:self.db.execute('UPDATE app_channel_inputs SET id=?,delivery=?,envelope=?,deadline=? WHERE slot=?',
                (value['id'],canonical(delivery).decode(),canonical(value).decode(),deadline,slot))
            self.app.hook('after_application_input_commit');row=self.input()
        value=json.loads(row['envelope']);delivery=json.loads(row['delivery'])
        require(self.client.get(delivery['body']['ref'])==value,'CONFLICT')
        if row['ack'] is None:
            require(row['ack_calls']<c.MAX_ATTEMPTS,'OVERLOADED')
            with self.db:self.db.execute('UPDATE app_channel_inputs SET ack_calls=ack_calls+1 WHERE slot=?',(slot,))
            ack=self.client.ack(delivery);self.app.hook('after_application_input_ack_reply')
            with self.db:self.db.execute('UPDATE app_channel_inputs SET ack=? WHERE slot=?',(canonical(ack).decode(),slot))
            self.app.hook('after_application_input_ack')
        return value['nick']+': '+value['text']
    def new_input(self):
        row=self.input();require(row is not None and row['id'] is not None and row['ack'] is not None,'NOT_AVAILABLE')
        return True # New for this durable processing assignment; replay keeps the assignment.
    def source_spec(self):
        row=self.input();require(row is not None and row['ack'] is not None,'NOT_AVAILABLE')
        value=json.loads(row['envelope']);require(self.client.get(json.loads(row['delivery'])['body']['ref'])==value,'CONFLICT')
        return dict(text=value['nick']+': '+value['text'],label='irc-'+value['id'],source='isolated-irc-observation',
                    message_id=value['id'],observed_time=datetime.fromtimestamp(value['observed_ms']/1000,timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                    deadline_ms=row['deadline'])
    def source(self,text):
        value=self.app.evidence.source(text);spec=self.source_spec()
        require(value==text+' RECORDED_SOURCE: '+spec['label'],'NOT_AVAILABLE')
        return text # Keep the native human rendering; source identity stays local.
    def accept_turn(self):
        row=self.input();require(row is not None and row['ack'] is not None,'NOT_AVAILABLE')
        require(self.client.get(json.loads(row['delivery'])['body']['ref'])==json.loads(row['envelope']),'CONFLICT')
        # Already accepted commands can replay after expiry; missing model work cannot.
        if self.app.pending() is None:require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
    def intent(self,command):
        require(len(command)==2 and command[0]=='send','INVALID_ARGUMENT')
        cfg=self.current();c.output(command[1],cfg['approved_outputs'],cfg['target'])
        return dict(profile=c.PROFILE,operation='send',arguments=dict(text=command[1]))
    def admit(self,key,intent,turn,position,deadline):
        if intent['profile']!=c.PROFILE:return
        cfg=self.current();value=dict(profile=c.PROFILE,kind='egress',scope=cfg['scope'],route=cfg['egress_route'],
            bridge=cfg['bridge'],session=cfg['session'],id=key,epoch=None,sequence=(turn-1)*5+position+1,
            observed_ms=deadline-self.app.config['invocation_timeout_ms'],nick=None,target=cfg['target'],text=intent['arguments']['text'],deadline_ms=deadline)
        c.record(value,cfg);self.db.execute('INSERT INTO app_channel_outputs(id,envelope) VALUES(?,?)',(key,canonical(value).decode()))
    def occurrence(self):
        require(self.app.current is not None,'CONFLICT')
        row=self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?',self.app.current).fetchone()
        require(row is not None and json.loads(row['premises'])['profile']==c.PROFILE,'CONFLICT');return row
    def state(self,row):return self.db.execute('SELECT * FROM app_channel_outputs WHERE id=?',(row['id'],)).fetchone()
    def reserve(self,row,column):
        require(column in ('put_calls','send_calls'))
        with self.db:
            state=self.state(row);require(state[column]<c.MAX_ATTEMPTS,'OVERLOADED')
            self.db.execute('UPDATE app_channel_outputs SET '+column+'='+column+'+1 WHERE id=?',(row['id'],))
    def send(self,text):
        row=self.occurrence();state=self.state(row);value=json.loads(state['envelope']);cfg=self.current()
        c.output(text,cfg['approved_outputs'],cfg['target']);require(value['text']==text,'CONFLICT')
        if state['acceptance'] is not None:
            require(self.client.get(json.loads(state['payload'])['ref'])==value,'CONFLICT');return 'SEND-ACCEPTED'
        if state['payload'] is None:
            self.reserve(row,'put_calls');payload=self.client.put(value);self.app.hook('after_output_payload_reply')
            with self.db:self.db.execute('UPDATE app_channel_outputs SET payload=? WHERE id=?',(canonical(payload).decode(),row['id']))
        else:payload=json.loads(state['payload'])
        self.reserve(row,'send_calls');receipt=self.client.send(value,payload['ref']);self.app.hook('after_output_mailbox_reply')
        with self.db:self.db.execute('UPDATE app_channel_outputs SET acceptance=? WHERE id=?',(canonical(receipt).decode(),row['id']))
        self.app.hook('after_output_acceptance');return 'SEND-ACCEPTED'
    def capture(self,value):
        row=self.occurrence();state=self.state(row);require(value=='SEND-ACCEPTED' and state['acceptance'] is not None,'NOT_AVAILABLE')
        envelope=json.loads(state['envelope']);cfg=self.current()
        c.output(envelope['text'],cfg['approved_outputs'],cfg['target'])
        require(self.client.get(json.loads(state['payload'])['ref'])==envelope,'CONFLICT')
        require(row['result'] is None or row['result']==value,'CONFLICT')
        if row['result'] is None:require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
        with self.db:self.db.execute('UPDATE app_occurrences SET result=?,done=1 WHERE id=?',(value,row['id']))
        self.app.hook('after_channel_native_result');return value
    def replay(self,row):
        state=self.state(row);require(row['result']=='SEND-ACCEPTED' and state['acceptance'] is not None,'NOT_AVAILABLE')
        value=json.loads(state['envelope']);c.output(value['text'],self.current()['approved_outputs'],self.client.cfg['target'])
        require(self.client.get(json.loads(state['payload'])['ref'])==value,'CONFLICT');return row['result']

    def lastsend(self):
        row=self.db.execute('SELECT o.* FROM app_occurrences o JOIN app_channel_outputs c ON c.id=o.id WHERE c.acceptance IS NOT NULL ORDER BY turn DESC,position DESC LIMIT 1').fetchone()
        if row is None:return ''
        state=self.state(row);value=json.loads(state['envelope']);c.output(value['text'],self.current()['approved_outputs'],self.client.cfg['target'])
        require(self.client.get(json.loads(state['payload'])['ref'])==value,'CONFLICT');return value['text']
