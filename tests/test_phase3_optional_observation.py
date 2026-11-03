"""Actual same-host HTTPS client; an explicit absent-observation server fixture."""
import json,ssl,tempfile,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from fusion import cognitive_services as cs,lookup_contracts as c
from fusion.contracts import canonical,digest,ContractError
from fusion.registry import selection_token
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.ports import Mutation
from tests.test_phase2_sdk import prepare

class OptionalObservation(unittest.TestCase):
 def test_declared_observation_reaches_https_with_exact_original_identity(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);prepare(root);descriptor=cs.descriptors(feed_profile=c.SUSTAINED_FEED)[0];seen=[]
   class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def do_POST(self):
     raw=self.rfile.read(int(self.headers['Content-Length']));q=json.loads(raw);seen.append((self.headers['Authorization'],q))
     value=dict(id=q['id'],request_digest=digest(raw),selection=q['selection'],principal='A',value=dict(found=False,write=None,through=None,content_type=None,size=None))
     body=canonical(value);self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
   server=ThreadingHTTPServer(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
   context.load_cert_chain(root/'cert.pem',root/'key.pem');server.socket=context.wrap_socket(server.socket,server_side=True)
   worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
   try:
    endpoint=Endpoint('127.0.0.1',server.server_port,str(root/'cert.pem'))
    client=AtomFeedClient(endpoint,'test-authority','A','synthetic-optional-observe',descriptor,deadline_ms=time.time_ns()//1000000+5000,composition=cs.COMPOSITION,feed_profile=c.SUSTAINED_FEED)
    command=Mutation(client.scope,'original-stable-identity');self.assertFalse(client.observe(command)['found'])
    self.assertEqual(seen[0][0],'Bearer test-authority');self.assertEqual(seen[0][1]['operation'],'observe');self.assertEqual(seen[0][1]['args'][0]['idempotency_key'],command.idempotency_key)
    old=cs.descriptors()[0];legacy=AtomFeedClient(endpoint,'test-authority','A',client.scope,old,deadline_ms=client.deadline_ms,composition=cs.COMPOSITION)
    with self.assertRaisesRegex(ContractError,'UNSUPPORTED_OPERATION'):legacy.observe(command)
    self.assertEqual(len(seen),1)
   finally:server.shutdown();worker.join(2);server.server_close()
