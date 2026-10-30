"""Bounded operator actors: real socket peer or durable IRC bridge, never a daemon server."""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import socket
import sys
import time
from fusion.contracts import canonical,ContractError,require
from fusion.irc_bridge import Bridge
from .host import failpoint


def peer(cfg,ready):
    # Independent test actor: uses only its own socket and observation log.
    host=cfg.get('host','127.0.0.1')
    if host!='127.0.0.1':
        from fusion.channel_services import COMPOSITION
        from fusion.neoclaw_services import service_hostname
        require(cfg.get('deployment')==COMPOSITION,'UNSUPPORTED_PROFILE');service_hostname(host)
    sock=socket.create_connection((host,cfg['port']),timeout=2)
    sock.sendall(('NICK peer\r\nUSER peer 0 * :synthetic peer\r\n').encode())
    buffer=b'';commands=b'';until=time.monotonic()+cfg.get('seconds',120)
    with open(cfg['log'],'a',buffering=1) as log:
        while time.monotonic()<until:
            readable,_,_=select.select([sock,sys.stdin],[],[],.1)
            if sys.stdin in readable:
                data=os.read(sys.stdin.fileno(),4096)
                if not data:break
                commands+=data
            while b'\n' in commands:
                line,commands=commands.split(b'\n',1);action=json.loads(line)
                if 'text' in action:
                    body=('PRIVMSG '+cfg['target']+' :'+action['text']+'\r\n').encode()
                    cut=action.get('split')
                    if cut:sock.sendall(body[:cut]);time.sleep(.03);sock.sendall(body[cut:])
                    else:sock.sendall(body)
                    log.write(json.dumps(dict(sent=action['text']))+'\n')
                elif 'nick' in action:sock.sendall(('NICK '+action['nick']+'\r\n').encode())
                elif 'raw' in action:sock.sendall(bytes.fromhex(action['raw']))
            if sock in readable:
                data=sock.recv(4096)
                if not data:break
                buffer+=data
                while b'\r\n' in buffer:
                    line,buffer=buffer.split(b'\r\n',1);line=line.decode('utf-8')
                    log.write(json.dumps(dict(received=line))+'\n')
                    if line.startswith('PING :'):sock.sendall(('PONG :'+line[6:]+'\r\n').encode())
                    if ' 001 peer ' in line:sock.sendall(('JOIN '+cfg['target']+'\r\n').encode())
                    if ' 366 peer '+cfg['target']+' ' in line:Path(ready).write_text(json.dumps(dict(pid=os.getpid(),joined=True)))
    sock.close()


def bridge(path,ready):
    cfg=json.loads(Path(path).read_text())
    denied=cfg.get('denied_paths',[])
    if denied and os.environ.get('S06_BRIDGE_ISOLATED')!='1':
        command=['bwrap','--die-with-parent','--ro-bind','/','/','--bind','/tmp','/tmp','--proc','/proc','--dev','/dev',
                 *[v for p in cfg.get('writable_paths',[]) for v in ('--bind',str(Path(p).resolve()),str(Path(p).resolve()))],
                 *[v for p in denied for v in ('--tmpfs',str(Path(p).resolve()))],'--',sys.executable,'-m','integration.neoclaw.channel_actor',*sys.argv[1:]]
        os.execvpe(command[0],command,dict(os.environ,S06_BRIDGE_ISOLATED='1'))
    owner=Bridge(path,lambda stage:failpoint(cfg,stage));until=time.monotonic()+cfg.get('seconds',120)
    try:
        owner.connect()
        while time.monotonic()<until:
            if owner.irc:
                try:
                    for nick,text in owner.irc.receive():
                        owner.capture(nick,text)
                        owner.relay() # Limit pending capture even within a coalesced burst.
                except (ContractError,OSError) as exc:
                    code=exc.code if isinstance(exc,ContractError) else 'NOT_AVAILABLE'
                    owner.discontinuity('capacity' if code=='OVERLOADED' else 'disconnect' if code=='NOT_AVAILABLE' else 'invalid-frame')
                if owner.irc and owner.irc.ready and not Path(ready).exists():
                    Path(ready).write_text(json.dumps(dict(pid=os.getpid(),epoch=owner.epoch,
                        denied_paths_visible=[p for p in denied if Path(p).exists() and any(Path(p).iterdir())])))
            try:owner.relay();owner.take_egress();owner.effect()
            except ContractError as exc:
                # State is retained; only bounded availability/capacity retries.
                if exc.code not in ('OVERLOADED','NOT_AVAILABLE'):raise
            time.sleep(.02)
    finally:
        if owner.irc:owner.discontinuity('operator-stop')
        owner.close()


def main():
    def terminate(*_):raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('role',choices=['peer','bridge']);p.add_argument('config');p.add_argument('--ready',required=True);a=p.parse_args()
    if a.role=='peer':peer(json.loads(Path(a.config).read_text()),a.ready)
    else:bridge(a.config,a.ready)

if __name__=='__main__':main()
