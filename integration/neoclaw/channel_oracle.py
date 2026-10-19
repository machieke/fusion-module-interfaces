"""Pinned original IRC receive/buffer/send oracle, only on the disposable server."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from fusion.adapters.neoclaw_nal import NativeTruthDeduction
from fusion.contracts import canonical,digest,require
from .channel_composition import ChannelRun,ROOT
from tests.neoclaw_support import RUNTIME

INPUT='Synthetic calculate Ω "quoted" (send fake-tool).'
OUTPUT='Synthetic channel reply Ω: calculation observed.'

def original():
    r=ChannelRun('local',True,inputs=[INPUT],outputs=[OUTPUT]);runtime=NativeTruthDeduction(RUNTIME).runtime;omega=Path(runtime['mettaclaw']);petta=Path(runtime['petta'])
    try:
        r.start_server();r.start_peer();work=r.caller
        helper=work/'oracle_capture.py';helper.write_text('''import json,time
from pathlib import Path
import irc
values=[]
def record(value):
 values.append(str(value));Path('original-values.json').write_text(json.dumps(values));return True
def wait_input(count):
 Path('phase').write_text(str(count))
 until=time.monotonic()+15
 while time.monotonic()<until:
  if irc._last_message.count('peer:')>=count:return True
  time.sleep(.03)
 raise RuntimeError('ORIGINAL_REAL_IRC_OBSERVATION_TIMEOUT')
def settle():time.sleep(1);return True
''')
        lines=['!(import! &self (library lib_import))','!(import! &self (library lib_patrick))']
        imports=[omega/'src/helper.py',omega/'src/utils.metta',omega/'channels/irc.py',omega/'src/channels.metta',helper]
        lines+=['!(import! &self '+json.dumps(str(x))+')' for x in imports]
        lines+=['!(configure commchannel irc)',f'!(py-call (irc.start_irc {json.dumps(r.base["target"])} "127.0.0.1" {r.irc_port} "orig"))',
            '!(py-call (oracle_capture.wait_input 1))','!(py-call (oracle_capture.record (receive)))',
            '!(py-call (oracle_capture.wait_input 2))','!(py-call (oracle_capture.record (receive)))',
            '!(let $parsed (py-call (helper.balance_parentheses '+json.dumps('send '+OUTPUT,ensure_ascii=False)+')) (let $commands (sread $parsed) (let $result (collapse (let $command (superpose $commands) (eval $command))) (py-call (oracle_capture.record $result)))))',
            '!(py-call (oracle_capture.settle))']
        entry=work/'original.metta';entry.write_text('\n'.join(lines)+'\n');env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','TMPDIR')};env.update(runtime['environment'])
        args=[runtime['swipl'],'-q','-s',str(petta/'src/main.pl'),'-g',"asserta(library_path('"+str(omega)+"'))",'--',str(entry),'--silent']
        log=open(work/'original.log','w');r.logs.append(log);p=subprocess.Popen(args,cwd=work,env=env,stdout=log,stderr=log,start_new_session=True);r.processes.append(p)
        until=time.monotonic()+12
        while time.monotonic()<until:
            if any(' JOIN :' in x.get('received','') and x['received'].startswith(':orig') for x in r.traffic()):break
            time.sleep(.03)
        else:raise TimeoutError('original IRC join')
        r.send(INPUT);phase=work/'phase';until=time.monotonic()+8
        while time.monotonic()<until:
            if phase.exists() and phase.read_text()=='2':break
            time.sleep(.02)
        else:raise TimeoutError('original receive')
        r.send(INPUT);r.send(INPUT);p.wait(timeout=20)
        require(p.returncode==0,'NOT_AVAILABLE');values=json.loads((work/'original-values.json').read_text())
        require(values==['peer: '+INPUT,'peer: '+INPUT+' | peer: '+INPUT,'[\'SEND-SUCCESS\']'],'CONFLICT')
        seen=[x for x in r.traffic() if ' PRIVMSG '+r.base['target']+' :'+OUTPUT in x.get('received','')]
        if len(seen)!=1:raise RuntimeError('Original generated-message observation mismatch: '+repr([x for x in r.traffic() if ' PRIVMSG ' in x.get('received','')]))
        return dict(source_commit='2af37c3fec18613de54ca42fde2382a9087d4524',files={str(x.relative_to(omega)):digest(x.read_bytes()) for x in imports[:-1]},
            driver_sha256=digest(entry.read_bytes()),values=values,peer=seen,server=r.isolation,
            stdout=(work/'original.log').read_text(),scope='original native receive + actual parsed send; no full legacy loop/model startup')
    finally:r.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();Path(a.out).write_bytes(canonical(original()))
