"""Disposable S06 recipe: pinned ngIRCd, separate peer, existing payload/mailbox owners."""
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from fusion import channel_contracts as c
from fusion.contracts import canonical,digest,require
from fusion.registry import descriptors,descriptor_wire
from tests.neoclaw_support import ROOT,DETTA

SERVER=ROOT/'artifacts/s06/ngircd/sbin/ngircd'


def write(path,value):
    path=Path(path);pending=path.with_suffix('.new')
    pending.write_bytes(canonical(value));pending.chmod(0o600);pending.replace(path)


class ChannelRun:
    def __init__(self,placement='local',real=True,*,root=None,session=None,inputs=None,outputs=None,denied=None,defer=False):
        self.temp=tempfile.TemporaryDirectory(prefix='fusion-s06-') if root is None else None
        self.root=Path(self.temp.name) if self.temp else Path(root);self.root.mkdir(exist_ok=True)
        self.processes=[];self.logs=[];self.placement=placement;self.denied=denied or []
        self.provider=self.root/'mailbox';self.bridge_root=self.root/'bridge';self.server_root=self.root/'irc';self.peer_root=self.root/'peer';self.caller=self.root/'caller'
        for p in (self.provider,self.bridge_root,self.server_root,self.peer_root,self.caller):p.mkdir(mode=0o700)
        self.base=dict(profile=c.PROFILE,sharing='generated-shareable',scope='synthetic-s06',session=session or str(uuid.uuid4()),bridge=str(uuid.uuid4()),
            target='#s06-generated',ingress_route='in-A',egress_route='out-bridge',approved_inputs=inputs or ['synthetic hello'],approved_outputs=outputs or ['synthetic reply'],
            catalogue=[descriptor_wire(d) for d in descriptors(atom_provider='detta' if real else 'fixture-files') if d.interface in c.OPERATIONS])
        methods=[n+'.'+o for n,ops in c.OPERATIONS.items() for o in ops]
        self.config=dict(channel_store=dict(self.base,roles={'A':'application','bridge':'bridge'}),capacity=c.MAILBOX_CAPACITY,
            database=str(self.provider/'service.sqlite'),atoms_database=str(self.provider/'atoms.sqlite'),messages_database=str(self.provider/'mailbox.sqlite'),
            da_root=str(self.provider/'da'),atom_records=str(self.provider/'records'),atom_provider='detta' if real else 'fixture-files',detta_binary=str(DETTA),
            routes={'in-A':dict(scope=self.base['scope'],owner='A'),'out-bridge':dict(scope=self.base['scope'],owner='bridge')},
            principals={p:dict(credential=secrets.token_hex(24),scopes={self.base['scope']:methods+['channel.'+r]}) for p,r in (('A','application'),('bridge','bridge'))},
            test_failpoints=True,failpoint_marker=str(self.provider/'pause.json'))
        self.config_path=self.provider/'config.json';write(self.config_path,self.config);self.port=None;self.host=None
        if placement=='network':
            if defer:
                self.prepare_host()
                with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
            else:self.start_host()
        self.clients={}
        for role,name,path in [('application','A',self.caller/'client.json'),('bridge','bridge',self.bridge_root/'client.json')]:
            cfg=dict(self.base,role=role,principal=name,placement=placement,fallback=False,credential=self.config['principals'][name]['credential'])
            if placement=='network':
                ca=path.parent/'ca.pem';ca.write_bytes((self.provider/'server.pem').read_bytes());cfg['endpoint']=dict(host='127.0.0.1',port=self.port,ca_file=str(ca))
            else:cfg['provider_config']=str(self.config_path)
            write(path,cfg);self.clients[role]=path
        self.bridge_config_path=self.bridge_root/'config.json';self.peer_config_path=self.peer_root/'config.json'
        self.bridge_config=None;self.bridge=None;self.peer=None;self.server=None
    def spawn(self,args,name,stdin=False):
        log=open(self.root/(name+'.log'),'a');self.logs.append(log)
        p=subprocess.Popen(args,cwd=ROOT,stdout=log,stderr=log,stdin=subprocess.PIPE if stdin else subprocess.DEVNULL,
            text=True,start_new_session=True);self.processes.append(p);return p
    def wait(self,path,p,seconds=15):
        until=time.monotonic()+seconds
        while not Path(path).exists() and time.monotonic()<until and p.poll() is None:time.sleep(.02)
        if not Path(path).exists():raise RuntimeError('actor readiness failed '+str(path)+' '+str(p.poll())+'\n'+'\n'.join(x.read_text()[-3000:] for x in self.root.glob('*.log')))
    def prepare_host(self):
        if not (self.provider/'server.pem').exists():
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(self.provider/'server.key'),'-out',str(self.provider/'server.pem'),
                '-days','365','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],capture_output=True,check=True)
            (self.provider/'server.key').chmod(0o600)
        self.config.update(tls_certificate=str(self.provider/'server.pem'),tls_key=str(self.provider/'server.key'),
            memory_read=dict(denied_paths=self.denied+[str(self.bridge_root),str(self.caller)]))
        write(self.config_path,self.config)
    def start_host(self):
        self.prepare_host();ready=self.provider/'ready.json';ready.unlink(missing_ok=True)
        self.host=self.spawn([sys.executable,'-m','integration.neoclaw.host','serve',str(self.config_path),'--port',str(self.port or 0),'--ready',str(ready)],'https')
        self.wait(ready,self.host);self.port=json.loads(ready.read_text())['port']
    def start_server(self):
        if hasattr(self,'irc_port'):port=self.irc_port
        else:
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
        cfg=self.server_root/'ngircd.conf';cfg.write_text(f'''[Global]
Name = s06.local
Info = isolated generated S06
Listen = 127.0.0.1
Ports = {port}
PidFile = {self.server_root}/pid
[Limits]
MaxConnections = 8
MaxConnectionsIP = 8
MaxJoins = 1
MaxPenaltyTime = 0
[Options]
DNS = no
Ident = no
PAM = no
SyslogFacility = none
''')
        self.server=self.spawn([str(SERVER),'-n','-p','-f',str(cfg)],'irc-server')
        until=time.monotonic()+5
        while time.monotonic()<until:
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1):break
            except OSError:time.sleep(.05)
        require(self.server.poll() is None,'NOT_AVAILABLE');self.irc_port=port
        # Verify the running server's own listener descriptors, not only config.
        sockets=set()
        for p in Path('/proc',str(self.server.pid),'fd').iterdir():
            try:target=os.readlink(p)
            except FileNotFoundError:continue # Readiness probe connection closed.
            if target.startswith('socket:['):sockets.add(target[8:-1])
        listeners=[]
        for table in ('tcp','tcp6'):
            for line in Path('/proc/net',table).read_text().splitlines()[1:]:
                fields=line.split()
                if fields[9] in sockets and fields[3]=='0A':listeners.append(dict(table=table,address=fields[1]))
        require(listeners==[dict(table='tcp',address=f'0100007F:{port:04X}')],'UNSUPPORTED_PROFILE')
        self.isolation=dict(listeners=listeners,server_sha256=digest(SERVER.read_bytes()),config=cfg.read_text(),passive=True,irc_tls=False)
        return port
    def start_bridge(self, seconds=180):
        if self.bridge_config is None:
            self.bridge_config=dict(client=str(self.clients['bridge']),database=str(self.bridge_root/'bridge.sqlite'),
                server=dict(host='127.0.0.1',port=self.irc_port),nick='omega',seconds=seconds,test_failpoints=True,failpoint_marker=str(self.bridge_root/'pause.json'),
                denied_paths=self.denied+[str(self.caller),str(self.peer_root),str(self.server_root)])
        write(self.bridge_config_path,self.bridge_config);ready=self.bridge_root/'ready.json';ready.unlink(missing_ok=True)
        self.bridge=self.spawn([sys.executable,'-m','integration.neoclaw.channel_actor','bridge',str(self.bridge_config_path),'--ready',str(ready)],'bridge')
        self.wait(ready,self.bridge);return self.bridge
    def start_peer(self, seconds=180):
        write(self.peer_config_path,dict(port=self.irc_port,target=self.base['target'],log=str(self.peer_root/'traffic.jsonl'),seconds=seconds))
        ready=self.peer_root/'ready.json';ready.unlink(missing_ok=True)
        self.peer=self.spawn([sys.executable,'-m','integration.neoclaw.channel_actor','peer',str(self.peer_config_path),'--ready',str(ready)],'peer',True)
        self.wait(ready,self.peer);return self.peer
    def send(self,text,**kw):
        self.peer.stdin.write(json.dumps(dict(text=text,**kw))+'\n');self.peer.stdin.flush()
    def traffic(self):
        p=self.peer_root/'traffic.jsonl';return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
    def rows(self,path,table):
        with sqlite3.connect(path) as db:
            db.row_factory=sqlite3.Row
            return [dict(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid')]
    def kill(self,p):
        if p and p.poll() is None:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)
            # bwrap's parent can exit just before its child drops owner locks.
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                try:os.killpg(p.pid,0)
                except ProcessLookupError:break
                time.sleep(.01)
    def close(self):
        for p in self.processes:self.kill(p)
        for p in self.processes:
            if p.stdin:p.stdin.close()
        for f in self.logs:f.close()
        if self.temp:self.temp.cleanup()


def configure(run,corpus,placement='local',inputs=None,outputs=None):
    from .promotion_composition import configure as promotion
    value=promotion(run,corpus,sources={})
    # Session identity is operator-owned before accepting any channel occurrence.
    run.app.setdefault('session_id',str(uuid.uuid4()))
    channel=ChannelRun(placement,True,session=run.app['session_id'],inputs=inputs,outputs=outputs,
        denied=[str(run.h.caller_root),str(run.h.server_root)])
    # Application config must be accessible while bridge/provider configs are hidden.
    local=run.h.caller_root/'channel.json';local.write_bytes(channel.clients['application'].read_bytes());local.chmod(0o600)
    run.app.update(composition=c.APPLICATION,channel_config=str(local),channel_wait_ms=10000,channel_poll_limit=128)
    channel.start_server();run.app['channel_irc_probe_port']=channel.irc_port
    run.app['denied_paths'] += [str(channel.bridge_root),str(channel.server_root),str(channel.peer_root)]
    if placement=='network':run.app['denied_paths']+=[str(channel.provider)]
    run.save();value['channel']=channel;return value
