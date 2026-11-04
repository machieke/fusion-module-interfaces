"""Real TLS sockets/authority; storage is the explicitly declared file fixture."""
import json,socket,ssl,tempfile,threading,time,unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from fusion import https_pool as pool
from fusion.contracts import ContractError
from fusion.ports import Mutation
from fusion.preview_client import AtomFeedClient,Endpoint
from examples.phase2_provider import server
from tests.test_phase2_sdk import prepare


class PooledHTTPS(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.cfg=prepare(self.root)
        self.ports=server.Ports(self.root/'config.json');self.connections=0;self.operations=[];self.mode=None;self.filter=lambda x:x
        owner=self;original=server.handler(self.ports)
        class Handler(original):
            protocol_version='HTTP/1.1'
            def do_POST(self):
                owner.operations.append('POST');return super().do_POST()
            def reply(self,status,value):
                value=owner.filter(value)
                if owner.mode=='lost':
                    self.close_connection=True;self.connection.shutdown(socket.SHUT_RDWR);return
                if owner.mode=='partial':
                    self.send_response(200);self.send_header('Content-Length','100');self.end_headers();self.wfile.write(b'{');self.wfile.flush()
                    self.close_connection=True;self.connection.shutdown(socket.SHUT_RDWR);return
                if owner.mode=='hold':owner.entered.set();owner.release.wait(3)
                super().reply(status,value)
        class Server(ThreadingHTTPServer):
            def get_request(self):
                sock,address=super().get_request();owner.connections+=1;sock.settimeout(3);return sock,address
        self.server=Server(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(self.root/'cert.pem',self.root/'key.pem');self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.02},daemon=True);self.thread.start()
        self.endpoint=Endpoint('127.0.0.1',self.server.server_port,str(self.root/'cert.pem'))
        pool.configure(dict(pool.LIMITS));self.client=self.client_for()
    def tearDown(self):
        pool.close();pool.configure(None);self.server.shutdown();self.server.server_close();self.thread.join(2);self.temp.cleanup()
    def client_for(self,**changes):
        args=dict(endpoint=self.endpoint,credential='generated-sdk-credential',principal='reader',scope='generated-sdk',descriptor=server.descriptor(),deadline_ms=time.time_ns()//1000000+10000)
        args.update(changes);return AtomFeedClient(**args)
    def test_real_connection_reuse_and_per_request_revocation(self):
        for _ in range(5):self.client.head('generated-sdk')
        self.assertEqual((self.connections,len(self.operations)),(1,5))
        self.cfg['principals']['reader']['scopes']={};(self.root/'config.json').write_text(json.dumps(self.cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.client.head('generated-sdk')
        self.assertEqual(self.connections,1)
    def test_lost_mutation_response_has_one_call_and_explicit_same_identity_replay(self):
        self.mode='lost';mutation=Mutation('generated-sdk','original-id')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.client.create(mutation,'text/plain',b'synthetic')
        self.assertEqual(len(self.operations),1);self.mode=None
        result=self.client.create(mutation,'text/plain',b'synthetic')
        self.assertEqual(self.client.head('generated-sdk')['sequence'],1)
        self.assertEqual(self.client.get(result['ref']).bytes,b'synthetic');self.assertEqual(self.connections,2)
    def test_partial_response_never_retransmits(self):
        self.mode='partial'
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.client.head('generated-sdk')
        self.assertEqual(len(self.operations),1);self.assertEqual(pool._entries,[])
    def test_credential_and_ca_epoch_rotation_uses_new_connections(self):
        self.client.head('generated-sdk');self.cfg['principals']['reader']['credential']='rotated-credential'
        (self.root/'config.json').write_text(json.dumps(self.cfg))
        rotated=self.client_for(credential='rotated-credential');rotated.head('generated-sdk');self.assertEqual(self.connections,2)
        (self.root/'new-ca.pem').write_bytes((self.root/'cert.pem').read_bytes()+b'\n')
        trust=self.client_for(credential='rotated-credential',endpoint=Endpoint('127.0.0.1',self.server.server_port,str(self.root/'new-ca.pem')))
        trust.head('generated-sdk');self.assertEqual(self.connections,3)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.client.head('generated-sdk')
    def test_deadline_not_renewed_and_malformed_semantics_still_checked(self):
        self.client.head('generated-sdk');self.filter=lambda x:dict(x,id='wrong')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.client.head('generated-sdk')
        self.assertEqual(self.connections,1)
        self.client.deadline_ms=time.time_ns()//1000000-1
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.client.head('generated-sdk')
        self.assertEqual(len(self.operations),2)
    def test_bounded_headroom_rejects_without_sending_another_request(self):
        pool.configure(dict(pool.LIMITS,connections=1));self.mode='hold';self.entered=threading.Event();self.release=threading.Event();errors=[]
        def invoke():
            try:self.client.head('generated-sdk')
            except Exception as error:errors.append(error)
        thread=threading.Thread(target=invoke);thread.start()
        try:
            self.assertTrue(self.entered.wait(2))
            with self.assertRaisesRegex(ContractError,'OVERLOADED'):self.client_for().head('generated-sdk')
            self.assertEqual(len(self.operations),1)
        finally:self.release.set();thread.join(3)
        self.assertEqual(errors,[])
    def test_server_socket_loss_is_explicit_not_an_automatic_retry(self):
        self.client.head('generated-sdk')
        for row in pool._entries:row['connection'].sock.shutdown(socket.SHUT_RDWR)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.client.head('generated-sdk')
        self.assertEqual(len(self.operations),1)
        self.client.head('generated-sdk');self.assertEqual(len(self.operations),2)

if __name__=='__main__':unittest.main()
