"""IRC-owned capture/relay and one-attempt egress. Not a second mailbox."""
import fcntl
import json
from pathlib import Path
import sqlite3
import time
import uuid
from . import channel_contracts as c
from .channel_transport import Client
from .contracts import canonical,require,ContractError
from .adapters.irc_socket import IRC


def milliseconds():return time.time_ns()//1_000_000


class Bridge:
    @staticmethod
    def inspect(path):
        """Owner-authoritative read-only diagnostics, without reconnect/resend."""
        cfg=json.loads(Path(path).read_text()); database=Path(cfg['database'])
        if not database.exists():return []
        with sqlite3.connect(database.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            if not db.execute("SELECT 1 FROM sqlite_master WHERE name='channel_egress'").fetchone():return []
            return [dict(r) for r in db.execute('SELECT id,reserved,outcome,effect_epoch FROM channel_egress ORDER BY rowid')]

    def __init__(self,path,hook=lambda _:None):
        self.path=Path(path);self.cfg=json.loads(self.path.read_text());self.hook=hook
        self.client=Client(self.cfg['client']);require(self.client.cfg['role']=='bridge','UNAUTHORIZED')
        self.lock=open(self.cfg['database']+'.lock','a')
        try:fcntl.flock(self.lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:self.lock.close();raise ContractError('OVERLOADED') from None
        self.db=None;self.irc=None;self.epoch=None
        try:
            self.db=sqlite3.connect(self.cfg['database']);self.db.row_factory=sqlite3.Row
            tables={r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or 'channel_bridge' in tables,'UNSUPPORTED_PROFILE')
            self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
            self.db.executescript('''CREATE TABLE IF NOT EXISTS channel_bridge(binding TEXT);
              CREATE TABLE IF NOT EXISTS channel_epochs(id TEXT PRIMARY KEY,started INTEGER,state TEXT,reason TEXT);
              CREATE TABLE IF NOT EXISTS channel_ingress(id TEXT PRIMARY KEY,envelope TEXT,payload TEXT,acceptance TEXT,
                put_calls INTEGER DEFAULT 0,send_calls INTEGER DEFAULT 0,next_try INTEGER DEFAULT 0);
              CREATE TABLE IF NOT EXISTS channel_egress(id TEXT PRIMARY KEY,envelope TEXT,delivery TEXT,ack TEXT,
                ack_calls INTEGER DEFAULT 0,reserved INTEGER DEFAULT 0,outcome TEXT DEFAULT 'pending',effect_epoch TEXT);
            ''')
            binding=canonical(dict(client=self.client.frozen,server=self.cfg['server'],nick=self.cfg['nick'])).decode()
            with self.db:
                old=self.db.execute('SELECT binding FROM channel_bridge').fetchone()
                if old:require(old[0]==binding,'CONFLICT')
                else:self.db.execute('INSERT INTO channel_bridge VALUES(?)',(binding,))
            self.irc=None;self.epoch=None
        except BaseException:
            if self.db is not None:self.db.close()
            self.lock.close();raise
    def close(self):
        if self.irc:self.irc.close();self.irc=None
        self.db.close();self.lock.close()
    def connect(self):
        require(self.irc is None,'CONFLICT')
        with self.db:
            self.db.execute("UPDATE channel_epochs SET state='discontinuous',reason='process-interruption-or-reconnect' WHERE state='open'")
            require(self.db.execute('SELECT count(*) FROM channel_epochs').fetchone()[0]<16,'OVERLOADED')
            self.epoch=str(uuid.uuid4());self.db.execute('INSERT INTO channel_epochs VALUES(?,?,?,?)',(self.epoch,milliseconds(),'open','upstream-history-unavailable'))
        self.irc=IRC(**self.cfg['server'],target=self.client.cfg['target'],nick=self.cfg['nick'])
    def discontinuity(self,reason):
        require(reason in ('disconnect','capacity','invalid-frame','operator-stop'))
        with self.db:self.db.execute("UPDATE channel_epochs SET state='discontinuous',reason=? WHERE id=?",(reason,self.epoch))
        if self.irc:self.irc.close();self.irc=None
    def capture(self,nick,text):
        cfg=self.client.current();c.text(text);require(text in cfg['approved_inputs'],'UNAUTHORIZED')
        require(self.epoch is not None,'CONFLICT')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            require(self.db.execute('SELECT count(*) FROM channel_ingress WHERE acceptance IS NULL').fetchone()[0]<c.PENDING,'OVERLOADED')
            require(self.db.execute('SELECT count(*) FROM channel_ingress').fetchone()[0]<c.MAX_EVENTS,'OVERLOADED')
            seq=1+sum(json.loads(r[0])['epoch']==self.epoch for r in self.db.execute('SELECT envelope FROM channel_ingress'))
            ident=str(uuid.uuid5(uuid.UUID(self.epoch),str(seq)));now=milliseconds()
            value=dict(profile=c.PROFILE,kind='ingress',scope=cfg['scope'],route=cfg['ingress_route'],bridge=cfg['bridge'],session=cfg['session'],
                id=ident,epoch=self.epoch,sequence=seq,observed_ms=now,nick=nick,target=cfg['target'],text=text,deadline_ms=now+120000)
            c.record(value,cfg);self.db.execute('INSERT INTO channel_ingress(id,envelope) VALUES(?,?)',(ident,canonical(value).decode()))
        self.hook('after_bridge_capture');return value
    def reserve_rpc(self,table,ident,column):
        require((table,column) in (('channel_ingress','put_calls'),('channel_ingress','send_calls'),('channel_egress','ack_calls')))
        with self.db:
            row=self.db.execute('SELECT '+column+' FROM '+table+' WHERE id=?',(ident,)).fetchone();require(row[0]<c.MAX_ATTEMPTS,'OVERLOADED')
            self.db.execute('UPDATE '+table+' SET '+column+'='+column+'+1 WHERE id=?',(ident,))
    def relay(self):
        row=self.db.execute('SELECT * FROM channel_ingress WHERE acceptance IS NULL ORDER BY rowid LIMIT 1').fetchone()
        if row is None or row['next_try']>milliseconds():return False
        value=json.loads(row['envelope'])
        try:
            if row['payload'] is None:
                self.reserve_rpc('channel_ingress',row['id'],'put_calls');payload=self.client.put(value)
                self.hook('after_channel_payload_reply')
                with self.db:self.db.execute('UPDATE channel_ingress SET payload=? WHERE id=?',(canonical(payload).decode(),row['id']))
            else:payload=json.loads(row['payload'])
            self.reserve_rpc('channel_ingress',row['id'],'send_calls');receipt=self.client.send(value,payload['ref'])
            self.hook('after_channel_mailbox_reply')
            with self.db:self.db.execute('UPDATE channel_ingress SET acceptance=? WHERE id=?',(canonical(receipt).decode(),row['id']))
            return True
        except ContractError as exc:
            if exc.code not in ('OVERLOADED','NOT_AVAILABLE'):raise
            with self.db:self.db.execute('UPDATE channel_ingress SET next_try=? WHERE id=?',(milliseconds()+1000,row['id']))
            return False
    def take_egress(self):
        # Poll omits acknowledged deliveries. Recover our own receipt first when
        # ack committed remotely but its reply/local commit was interrupted.
        pending=self.db.execute('SELECT * FROM channel_egress WHERE ack IS NULL ORDER BY rowid LIMIT 1').fetchone()
        if pending:
            self.ack_egress(pending);return True
        item=self.client.poll()
        if item is None:return False
        value=self.client.get(item['body']['ref']);c.delivery(item,self.client.cfg,'egress')
        require(value['id']==item['body']['correlation_id'] and value['kind']=='egress','CONFLICT')
        with self.db:
            old=self.db.execute('SELECT * FROM channel_egress WHERE id=?',(value['id'],)).fetchone()
            if old:require(json.loads(old['envelope'])==value and json.loads(old['delivery'])==item,'CONFLICT')
            else:
                require(self.db.execute('SELECT count(*) FROM channel_egress').fetchone()[0]<c.MAX_EVENTS,'OVERLOADED')
                self.db.execute('INSERT INTO channel_egress(id,envelope,delivery) VALUES(?,?,?)',(value['id'],canonical(value).decode(),canonical(item).decode()))
        self.hook('after_bridge_egress_commit')
        row=self.db.execute('SELECT * FROM channel_egress WHERE id=?',(value['id'],)).fetchone()
        self.ack_egress(row)
        return True
    def ack_egress(self,row):
        item=json.loads(row['delivery']);value=json.loads(row['envelope'])
        require(self.client.get(item['body']['ref'])==value,'CONFLICT')
        if row['ack'] is None:
            self.reserve_rpc('channel_egress',value['id'],'ack_calls');ack=self.client.ack(item)
            self.hook('after_bridge_egress_ack')
            with self.db:self.db.execute('UPDATE channel_egress SET ack=? WHERE id=?',(canonical(ack).decode(),value['id']))
    def effect(self):
        row=self.db.execute("SELECT * FROM channel_egress WHERE outcome='pending' AND ack IS NOT NULL ORDER BY rowid LIMIT 1").fetchone()
        if row is None:return False
        value=json.loads(row['envelope']);ref=json.loads(row['delivery'])['body']['ref']
        require(self.client.get(ref)==value,'CONFLICT')
        if milliseconds()>=value['deadline_ms']:
            with self.db:self.db.execute("UPDATE channel_egress SET outcome='expired-before-reservation' WHERE id=?",(row['id'],))
            return False
        if self.irc is None or not self.irc.ready:return False
        with self.db:
            require(row['reserved']==0,'CONFLICT')
            self.db.execute("UPDATE channel_egress SET reserved=1,outcome='unknown',effect_epoch=? WHERE id=?",(self.epoch,row['id']))
        self.hook('after_socket_reservation')
        # Current authority again at the effect boundary; never refund reservation.
        try:require(self.client.get(ref)==value,'CONFLICT')
        except ContractError:
            with self.db:self.db.execute("UPDATE channel_egress SET outcome='rejected-before-write' WHERE id=?",(row['id'],))
            raise
        if milliseconds()>=value['deadline_ms']:
            with self.db:self.db.execute("UPDATE channel_egress SET outcome='expired-after-reservation' WHERE id=?",(row['id'],))
            return False
        try:self.irc.send(value['text'])
        except OSError:return False # Some bytes may have escaped. Keep unknown.
        self.hook('after_socket_write')
        with self.db:self.db.execute("UPDATE channel_egress SET outcome='socket-write-returned' WHERE id=?",(row['id'],))
        self.hook('after_socket_outcome');return True
    def observe(self,ident):
        row=self.db.execute('SELECT * FROM channel_egress WHERE id=?',(ident,)).fetchone();require(row is not None,'NOT_FOUND')
        require(self.client.get(json.loads(row['delivery'])['body']['ref'])==json.loads(row['envelope']),'CONFLICT')
        return dict(id=ident,reserved=row['reserved'],outcome=row['outcome'],effect_epoch=row['effect_epoch'],recipient='not-observed-by-provider')
