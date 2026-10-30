"""Irreversible-by-API restore fence: read ports and inert diagnostics only.

This is a bounded synthetic clone, not failover. No worker, native loop, encoder,
model, bridge or chain process is started. Rebuild is an explicit operator-only
Search maintenance action; caller occurrences and their old views stay intact.
"""
import fcntl,json,os,signal,ssl,threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from fusion.contracts import ContractError,canonical,require
from fusion import neoclaw_contracts as c
from fusion.neoclaw_transport import json_loads
from .configure import configure,write

READS={
 ('fusion-storage','/memory-source'):frozenset(('get','head','readCommits','observe')),
 ('fusion-storage','/s03-read'):frozenset(('getMany','authorize')),
 ('fusion-storage','/s03-append'):frozenset(('get','observe','authorize')),
 ('fusion-search','/s03-read'):frozenset(('query','authorize')),
 ('fusion-search','/s03-append'):frozenset(('published',)),
}
def allowed(role,path,request):
 require(type(request) is dict and request.get('operation') in READS.get((role,path),()),'UNAUTHORIZED')

def main(path):
 initial=json.loads(Path(path).read_text());state=Path('/state');fence=json.loads((state/'restore-fence.json').read_text());role=initial['role']
 require(fence['mode']=='READ_ONLY_RECONCILIATION' and fence['role']==role and fence['namespace']==os.environ['POD_NAMESPACE'],'UNAUTHORIZED')
 require(os.environ['POD_NAME']==role+'-0','UNSUPPORTED_PROFILE');lock=open(state/'owner.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 expected=dict(composition=initial['service_composition'],role=role,scope=initial.get('reference',{}).get('scope',initial.get('memory',{}).get('scope',c.SCOPE)))
 # A restored seal is not rewritten. Chart/config mismatches refuse startup.
 actual=json.loads((state/'owner-seal.json').read_text());require(actual==expected and actual['scope']==fence['original_scope'],'UNSUPPORTED_PROFILE')
 owner=None;cfg={};run=Path('/run/fusion');run.mkdir(exist_ok=True)
 if role in ('fusion-storage','fusion-search'):
  settings,cfg,_,_=configure(path)
  from fusion.memory_services import StoragePorts,SearchPorts
  owner=StoragePorts(run/'owner.json') if role=='fusion-storage' else SearchPorts(run/'owner.json')
 stop=threading.Event();signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
 plain=role in ('omega-agent','fusion-channel-bridge','irc-server','irc-peer','f1r3node')
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*_):pass
  def reply(self,value,status=200):
   raw=canonical(value);self.send_response(status);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
  def do_GET(self):
   if self.path not in ('/health/startup','/health/ready','/health/live'):self.reply(dict(error='NOT_FOUND'),404);return
   self.reply(dict(role=role,ready=not stop.is_set(),mode=fence['mode']))
  def do_POST(self):
   try:
    require(owner is not None,'UNAUTHORIZED');auth=self.headers.get_all('Authorization',[]);require(len(auth)==1 and auth[0].startswith('Bearer '),'UNAUTHORIZED')
    lengths=self.headers.get_all('Content-Length',[]);require(not self.headers.get('Transfer-Encoding') and len(lengths)==1 and lengths[0].isdigit() and 0<int(lengths[0])<=98304,'INVALID_ARGUMENT')
    q=json_loads(self.rfile.read(int(lengths[0])));allowed(role,self.path,q)
    value=owner.invoke(self.path,auth[0][7:],q)
   except ContractError as e:value=dict(error=e.wire())
   except (ValueError,KeyError,TypeError):value=dict(error=ContractError('INVALID_ARGUMENT').wire())
   self.reply(value)
 context=None
 if not plain:
  context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain('/secrets/tls.crt','/secrets/tls.key')
 class Server(ThreadingHTTPServer):
  def get_request(self):
   s,a=super().get_request();s.settimeout(2)
   try:return (context.wrap_socket(s,server_side=True) if context else s),a
   except BaseException:s.close();raise
 write(state/'restore-process.json',dict(role=role,mode=fence['mode'],pid=os.getpid(),effect_authority=False))
 with Server(('0.0.0.0',initial['https_port']),Handler) as server:
  server.timeout=.2
  while not stop.is_set():server.handle_request()
 lock.close()
