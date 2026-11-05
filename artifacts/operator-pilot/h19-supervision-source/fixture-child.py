import json,os,signal,sys,time
from pathlib import Path
p=json.loads(Path(sys.argv[sys.argv.index('--plan')+1]).read_bytes())
root=Path(p['fixture_root']);mode=p['fixture_mode']
def stat(pid):
 s=Path('/proc',str(pid),'stat').read_text();f=s[s.rfind(')')+2:].split();return dict(pid=pid,start_ticks=int(f[19]),session=int(f[3]))
if mode=='nested':
 child=os.fork()
 if child==0:
  os.setsid();(root/'leaf.json').write_text(json.dumps(stat(os.getpid())))
  time.sleep(30);os._exit(0)
 until=time.monotonic()+5
 while not(root/'leaf.json').exists() and time.monotonic()<until:time.sleep(.01)
 (root/'fixture-ready').write_text('ready');os._exit(0)
if mode=='ignore-term':signal.signal(signal.SIGTERM,signal.SIG_IGN)
(root/'fixture-ready').write_text('ready')
time.sleep(2 if mode=='finish' else 30)
(root/'fixture-finished').write_text('finished')
