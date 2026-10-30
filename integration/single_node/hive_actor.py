"""Bounded operator action driver around the pinned, authenticated native Hive.

No model, imitation dispatch or provider journal reads. Native plugins persist
caller progress and use only the configured HTTPS ports. Windows and observation
budgets are caller-owned and retained across pod replacement.
"""
import contextlib,json,os,sys,time
from pathlib import Path
from fusion.contracts import require,ContractError
from .configure import write


def main():
 from fastapi.testclient import TestClient
 from hive.core.app import create_app
 from hive.core.config import load_settings
 from hive.core import exclusive
 state=Path('/state');run=Path('/run/fusion');cfg=json.loads(Path('/config/component.json').read_text());chain=cfg['reference']['chain']
 os.environ.update(HIVE_PLUGIN_DIRS='/opt/fusion/integration/hive/program:/opt/fusion/integration/hive/commitment',FUSION_HIVE_CONFIG=str(run/'hive-caller.json'),HIVE_OFFLINE='1',HIVE_DATA_DIR='/state/hive')
 settings=load_settings(data_dir=state/'hive',admin_password='generated-isolated-operator-password',petta_path=os.environ['PETTA_PATH'],offline=True)
 exclusive.acquire_or_exit(settings.data_dir,exclusive.HELD);app=create_app(settings,reconcile_seconds=0);exclusive.startup_recovery(exclusive.HELD,app.state.hive)
 with TestClient(app) as client:
  login=client.post('/api/auth/login',json={'password':'generated-isolated-operator-password'});login.raise_for_status();client.headers['Authorization']='Bearer '+login.json()['token']
  swarmfile=state/'swarm.json'
  if swarmfile.exists():swarm=json.loads(swarmfile.read_text())['id']
  else:
   response=client.post('/api/swarms',json={'name':'Explicitly shareable reference inspection'});response.raise_for_status();swarm=response.json()['id'];write(swarmfile,dict(id=swarm))
  caller=json.loads((run/'hive-caller.json').read_text());caller['grants']=[dict(principal='user:operator',swarm=swarm,credential=Path('/secrets/fusion-execution-token').read_text().strip(),scope='shared-test',reply_route='reply-A',counterparty='reply-B')];write(run/'hive-caller.json',caller)
  for program in ('fusion-inspect','fusion-commitment'):
   response=client.get('/api/programs/'+program);response.raise_for_status();require(response.json()['source']=='plugin-dir','UNSUPPORTED_PROFILE')
  def window(name):
   f=state/(name+'-window.json')
   if not f.exists():write(f,dict(deadline_ms=time.time_ns()//1000000+180000,calls=0,max_calls=120))
   return f
  def call(program,body,f):
   b=json.loads(f.read_text());require(b['calls']<b['max_calls'] and time.time_ns()//1000000<b['deadline_ms'],'DEADLINE_EXCEEDED');b['calls']+=1;write(f,b)
   r=client.post('/api/programs/'+program+'/act',json=body);r.raise_for_status();v=r.json()
   write(state/'last-native-response.json',dict(program=program,response=v));return v
  body=dict(swarm_id=swarm,action='inspect',items=[],params=dict(seed=chain['seed']),idempotency_key=chain['command'])
  # A retained completed inspection is still revalidated through the native
  # accessor during commitment. Do not start a replacement inspection window.
  if not (state/'inspection.json').exists():
   w=window('inspect')
   while True:
    v=call('fusion-inspect',body,w)
    if v['status']=='done':break
    require(v['status']=='started' or (v['status']=='error' and v.get('detail',{}).get('error',{}).get('retryable') is True),'NOT_AVAILABLE');time.sleep(.1)
   write(state/'inspection.json',dict(command=chain['command'],swarm=swarm,principal='user:operator',response=v))
  if chain['registration'] is None:
   write(state/'native-status.json',dict(status='INSPECTED_AWAITING_EXACT_REGISTRATION'));return
  w=window('commitment');body=dict(swarm_id=swarm,action='commit',items=[],params=dict(original_command=chain['command']))
  # Adapter replay uses the exact signed intent; never invent a fresh operation.
  while True:
   v=call('fusion-commitment',body,w);write(state/'submission.json',v)
   require(v['status'] in ('started','done'),'NOT_AVAILABLE')
   if v.get('detail',{}).get('chain',{}).get('deploy_id') is not None:break
   # Response loss cannot create another logical intent. Replay exact original
   # native command under the same durable observer/call bound.
   time.sleep(.2)
  body['action']='observe'
  while v.get('detail',{}).get('chain',{}).get('effect_finality') not in ('finalized','rejected'):
   v=call('fusion-commitment',body,w)
   require(v['status'] in ('started','done'),'NOT_AVAILABLE');time.sleep(.5)
  write(state/'final-observation.json',v);write(state/'native-status.json',dict(status='FINALIZED' if v['detail']['chain']['effect_finality']=='finalized' else 'REJECTED'))

if __name__=='__main__':
 try:main()
 except Exception as e:
  write('/state/native-status.json',dict(status='STOPPED',code=e.code if isinstance(e,ContractError) else type(e).__name__));raise
