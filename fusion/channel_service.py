"""Narrow channel admission. Existing atom and mailbox owners retain all state."""
import json
from pathlib import Path
import sqlite3
from . import channel_contracts as c
from .contracts import canonical, digest, decode, require, ContractError
from .composition import service
from .registry import descriptors, descriptor_read, selection_token
from .policy import Policy
from .neoclaw_transport import json_loads


class ChannelService:
    def __init__(self, path, hook=lambda _:None, *, owner=None, policy=None):
        self.path=Path(path);self.cfg=json.loads(self.path.read_text())
        c.route_config(self.cfg['channel_store']);self.policy=policy or Policy(path)
        self.chosen=c.selected([descriptor_read(x) for x in self.cfg['channel_store']['catalogue']])
        require(self.chosen == c.selected(descriptors(atom_provider=self.cfg.get('atom_provider','detta'))),'UNSUPPORTED_PROFILE')
        if owner is not None:
            from .channel_services import COMPOSITION
            require(self.cfg.get('service_composition')==COMPOSITION and self.cfg.get('channel_role') in ('storage','messaging'),'UNSUPPORTED_PROFILE')
            self.owner,self.hook=owner,hook;return
        binding=canonical(dict(channel=self.cfg['channel_store'],paths={k:self.cfg.get(k) for k in
            ('database','atoms_database','messages_database','da_root','atom_provider','atom_records','detta_binary')})).decode()
        # Seal before constructing owners. A partially constructed fresh service
        # may restart; a pre-existing unsealed journal is never adopted.
        with sqlite3.connect(self.cfg['database']) as db:
            db.execute('PRAGMA synchronous=FULL')
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or 'channel_seal' in tables,'UNSUPPORTED_PROFILE')
            if not tables:
                require(not any(Path(self.cfg[k]).exists() for k in ('atoms_database','messages_database','da_root','atom_records') if k in self.cfg),'UNSUPPORTED_PROFILE')
                db.execute('BEGIN IMMEDIATE')
                db.execute('CREATE TABLE channel_seal(binding TEXT NOT NULL)')
                db.execute('INSERT INTO channel_seal VALUES(?)',(binding,))
            else:require(db.execute('SELECT binding FROM channel_seal').fetchone()[0]==binding,'CONFLICT')
        self.owner=service(path,hook);self.hook=hook

    def close(self): self.owner.close()

    def invoke(self, credential, request):
        name,op=c.wire(request,self.chosen);q=request['invocation'];body=q['body']
        if self.cfg.get('channel_role'):
            require(name==('atom.storage' if self.cfg['channel_role']=='storage' else 'agent.messaging'),'UNSUPPORTED_OPERATION')
        cfg=c.route_config(self.policy.current()['channel_store'])
        require(c.selection(self.chosen)==c.selection(c.selected([descriptor_read(x) for x in cfg['catalogue']])),'UNSUPPORTED_PROFILE')
        principal=self.policy.authenticate(credential)
        require(principal==request['principal'] and principal in cfg['roles'],'UNAUTHORIZED')
        role=cfg['roles'][principal];require(role in ('bridge','application'),'UNAUTHORIZED')
        require(q['scope_ref']==cfg['scope'],'UNAUTHORIZED')
        receive=cfg['egress_route' if role=='bridge' else 'ingress_route']
        send=cfg['ingress_route' if role=='bridge' else 'egress_route']
        # Every release requires the live complete selected role. A revoked send
        # permission cannot be bypassed by reading a cached accepted payload.
        for family,ops in c.OPERATIONS.items():
            for method in ops:self.policy.check(principal,cfg['scope'],family+'.'+method)
        self.policy.check(principal,cfg['scope'],'channel.'+role)
        self.policy.route(cfg['scope'],receive,principal)
        self.policy.route(cfg['scope'],send)
        value=None
        if name=='atom.storage' and op=='create':
            require(body['content_type']==c.CONTENT,'UNSUPPORTED_PROFILE')
            value=json_loads(decode(body['bytes']));c.record(value,cfg)
            require(canonical(value)==decode(body['bytes']))
            require(value['kind']==('ingress' if role=='bridge' else 'egress'),'UNAUTHORIZED')
            require(q.get('deadline_ms')==value['deadline_ms'],'CONFLICT')
            require(q['idempotency_key']=='payload/'+value['id'],'CONFLICT')
        if name=='agent.messaging':
            require(body['route']==(send if op=='send' else receive),'UNAUTHORIZED')
            if op=='ack':require(q['idempotency_key']=='ack/'+body['delivery_id'],'CONFLICT')
            if op=='send':
                envelope=self.owner.atoms_for(principal).get(body['ref'])
                require(envelope.content_type==c.CONTENT,'UNSUPPORTED_PROFILE')
                value=c.record(json.loads(envelope.bytes),cfg)
                require(value['route']==send and q['correlation_id']==value['id'] and
                    q['reply_route']==receive and q['idempotency_key']=='mail/'+value['id'] and
                    q.get('deadline_ms')==value['deadline_ms'],'CONFLICT')
        # Bounded fresh S06 journal; no old service rows are adopted or evicted.
        old=self.owner.db.execute('SELECT count(*) FROM mutations').fetchone()[0]
        identity=canonical([principal,cfg['scope'],name,op,q.get('idempotency_key')]).decode()
        replay=self.owner.db.execute('SELECT 1 FROM mutations WHERE identity=?',(identity,)).fetchone()
        require(old < c.MAX_EVENTS*8 or replay or op not in ('create','send'), 'OVERLOADED')
        result=self.owner.invoke(credential,q)
        if op=='get':
            require(result['content_type']==c.CONTENT,'NOT_AVAILABLE')
            c.record(json.loads(decode(result['bytes'])),cfg)
        self.hook('after_channel_'+op)
        return dict(request_id=q['message_id'],request_digest=digest(canonical(request)),
                    principal=principal,selection=request['selections'],
                    reply=dict(ok=result,provider=selection_token(self.chosen[name])))
