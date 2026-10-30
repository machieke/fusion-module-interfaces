"""Isolated pinned F1R3node supervisor. No consensus overrides or work in health."""
import fcntl,json,os,signal,subprocess,time
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from fusion.contracts import canonical,digest,require,ContractError
from fusion.adapters.f1r3 import F1R3HTTP
from fusion.adapters.f1r3_m4 import chain_identity
from .configure import write

BINARY_SHA='2021389d8e1a1db0470d55ba6744124e33f2bc44f5155e6cfa662798b4ffd085'
CONFIG='''standalone = true
dev-mode = false
metrics.prometheus = false
casper.genesis-ceremony {
 required-signatures = 0
 approve-interval = 1 seconds
 approve-duration = 1 seconds
 autogen-shard-size = 1
 ceremony-master-mode = true
}
casper.genesis-block-data {
 number-of-active-validators = 1
 pos-multi-sig-quorum = 1
}
'''

def main(settings):
 chain=settings['reference']['chain'];state=Path('/state');run=Path('/run/fusion');run.mkdir(exist_ok=True)
 require(settings['reference']['synthetic'] is True and settings['role']=='f1r3node' and os.environ['POD_NAME']=='f1r3node-0','UNSUPPORTED_PROFILE')
 lock=open(state/'owner.lock','a')
 try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:raise SystemExit('OWNER_ALREADY_RUNNING') from None
 seal=dict(role='f1r3node',composition='isolated-f1r3node/1',source=BINARY_SHA,public=chain['public_key'])
 if (state/'owner-seal.json').exists():require(json.loads((state/'owner-seal.json').read_text())==seal,'CONFLICT')
 else:
  require({x.name for x in state.iterdir()}<={'owner.lock','lost+found'},'UNSUPPORTED_PROFILE');write(state/'owner-seal.json',seal)
 stop=False;child=None;ready=False;began=time.monotonic()
 def terminate(*_):
  nonlocal stop
  stop=True
 signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_GET(self):
   if self.path not in ('/health/startup','/health/ready','/health/live'):self.send_error(404);return
   good=not stop and (child is None or child.poll() is None)
   if chain['nodeEnabled'] and self.path!='/health/live':good=good and ready
   body=canonical(dict(role='f1r3node',ready=good,activated=chain['nodeEnabled']))
   self.send_response(200 if good else 503);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 require(digest(Path('/opt/chain/bin/node').read_bytes())==BINARY_SHA,'UNSUPPORTED_PROFILE')
 if chain['nodeEnabled']:
  require(chain.get('isolationVerified') is True,'UNAUTHORIZED')
  key=Path('/secrets/validator.hex').read_text().strip();require(len(key)==64 and all(c in '0123456789abcdef' for c in key),'UNAUTHORIZED')
  (run/'node.conf').write_text(CONFIG+'\ncasper.validator-private-key = \"'+key+'\"\n');(run/'node.conf').chmod(0o600);(run/'bonds.txt').write_text(chain['public_key']+' 1000\n');(run/'wallets.txt').write_text(chain['wallet_address']+',9000000000000\n')
  command=['/opt/chain/bin/node','--log-level','warn','run','--standalone','--config-file',str(run/'node.conf'),'--data-dir','/state/data','--host','127.0.0.1','--api-host','0.0.0.0','--no-upnp','--allow-private-addresses','--bonds-file',str(run/'bonds.txt'),'--wallets-file',str(run/'wallets.txt'),'--shard-name','fusion-m4','--network-id','fusion-m4-isolated','--heartbeat-enabled','--heartbeat-check-interval','2 seconds','--heartbeat-max-lfb-age','4 seconds']
  for flag,port in [('protocol-port',40400),('api-port-grpc-external',40401),('api-port-grpc-internal',40402),('api-port-http',40403),('discovery-port',40404),('api-port-admin-http',40405)]:command.extend(['--'+flag,str(port)])
  log=open(state/'node.log','ab');child=subprocess.Popen(command,stdout=log,stderr=log,env={**os.environ,'RUST_MIN_STACK':'8388608'},start_new_session=True)
 write(state/'process.json',dict(pid=os.getpid(),role='f1r3node',native_pid=child.pid if child else None,activated=chain['nodeEnabled']))
 next_probe=0
 try:
  with HTTPServer(('0.0.0.0',settings['https_port']),Handler) as server:
   server.timeout=.2
   while not stop:
    server.handle_request()
    if child is not None:
     require(child.poll() is None,'NOT_AVAILABLE')
     if not ready and time.monotonic()>=next_probe:
      next_probe=time.monotonic()+1
      try:
       identity=chain_identity(F1R3HTTP('http://127.0.0.1:40403'))
       require(identity['network']=='fusion-m4-isolated' and identity['shard']=='fusion-m4','CONFLICT')
       prior=state/'chain-identity.json'
       if prior.exists():require(json.loads(prior.read_text())==identity,'CONFLICT')
       else:write(prior,identity)
       write(state/'node-ready.json',dict(identity=identity,startup_seconds=time.monotonic()-began,sockets={f:Path('/proc/net/'+f).read_text() for f in ('tcp','tcp6','udp','udp6')}));ready=True
      except ContractError as e:
       if e.code!='NOT_AVAILABLE':raise
      if not ready and time.monotonic()-began>90:
       write(state/'node-timeout.json',dict(status='OBSERVATION_TIMEOUT',seconds=90));raise SystemExit('NODE_READINESS_TIMEOUT')
 finally:
  if child is not None and child.poll() is None:
   os.killpg(child.pid,signal.SIGTERM)
   try:child.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
   log.close()
  write(state/'shutdown.json',dict(role='f1r3node',graceful=True));lock.close()
