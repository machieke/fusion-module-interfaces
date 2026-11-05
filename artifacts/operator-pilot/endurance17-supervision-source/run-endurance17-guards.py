import os,runpy,sys
from pathlib import Path
python=Path(sys.executable).resolve()
def deny(event,args):
 if event in ('socket.connect','socket.connect_ex','socket.getaddrinfo'):raise RuntimeError('Network forbidden in supervisor fixtures')
 if event=='subprocess.Popen':
  exe=Path(args[0]).resolve()
  if exe!=python:raise RuntimeError('Only exact test Python children permitted')
 if event=='os.system':raise RuntimeError('Shell forbidden in supervisor fixtures')
sys.addaudithook(deny)
sys.argv=['test_endurance17_supervisor.py']
runpy.run_path('/data/fusion-operator-pilot-release/evidence-assembly/test_endurance17_supervisor.py',run_name='__main__')
