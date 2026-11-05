"""Real local TLS/process kill; file fixture owner, no native/model/cluster claim."""
import copy
import io
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fusion import https_pool
from fusion.contracts import ContractError,canonical
from fusion.ports import Mutation
from fusion.preview_client import AtomFeedClient,Endpoint
from integration.single_node.reply_faults import (PROFILE,MAX_IDENTITIES,ReplyFaults,
    selection,before_reply,write_body)
from examples.phase2_provider import server
from tests.test_phase2_sdk import prepare
from tests import test_phase2_fault_configuration as chart_fixtures


def configured(**changes):
    value=dict(profile=PROFILE,identity='bounded-fault',path='/reference-cognition',
               operation='create',mode='partial-body',delay_ms=0,
               observer_deadline_ms=time.time_ns()//1000000+10000)
    value.update(changes)
    return dict(enable_test_faults=True,test={'reply_fault':value})


class ReplyFaultTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def test_disabled_selection_is_inert_and_explicit_selection_is_closed(self):
        self.assertIsNone(selection({}));self.assertIsNone(selection({'test':{'drop_response_operation':'create'}}))
        self.assertIsNone(ReplyFaults(None,self.root).claim('/reference-cognition',{'operation':'create'},{}))
        self.assertEqual(list(self.root.iterdir()),[])
        for changes in [dict(enable_test_faults=False),dict(enable_test_faults=1)]:
            cfg=configured();cfg.update(changes)
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):selection(cfg)
        for changes in [dict(identity='../escape'),dict(operation='execute'),dict(path='/arbitrary'),
                        dict(delay_ms=True),dict(mode='delay',delay_ms=2000),dict(observer_deadline_ms=0)]:
            with self.subTest(changes=changes),self.assertRaises(ContractError):selection(configured(**changes))
        cfg=configured();cfg['test']['drop_response_operation']='create'
        with self.assertRaises(ContractError):selection(cfg)

    def test_atomic_claim_restart_binding_and_no_private_marker_content(self):
        cfg=selection(configured());owner=ReplyFaults(cfg,self.root);results=[];errors=[]
        def race():
            try:results.append(owner.claim(cfg['path'],dict(operation='create',content='PRIVATE'),dict(secret='PRIVATE')))
            except BaseException as e:errors.append(e)
        threads=[threading.Thread(target=race) for _ in range(8)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(errors,[]);self.assertEqual(sum(x is not None for x in results),1)
        marker=(self.root/'reply-fault-bounded-fault.json').read_bytes();self.assertNotIn(b'PRIVATE',marker)
        self.assertEqual(set(json.loads(marker)),{'selection','claimed_ms','state'})
        self.assertIsNone(ReplyFaults(cfg,self.root).claim(cfg['path'],dict(operation='create'),{}))
        changed=dict(cfg,mode='delay',delay_ms=250)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):ReplyFaults(changed,self.root)

    def test_paths_operations_errors_expiry_and_historical_read_deadlines(self):
        cfg=selection(configured());owner=ReplyFaults(cfg,self.root)
        for path,request,result in [('/health/ready',{'operation':'create'},{}),
                (cfg['path'],{'operation':'head'},{}),(cfg['path'],{'operation':'create'},{'error':{'code':'UNAUTHORIZED'}})]:
            self.assertIsNone(owner.claim(path,request,result))
        self.assertEqual(list(self.root.iterdir()),[])
        self.assertIsNone(owner.claim(cfg['path'],{'operation':'create','deadline_ms':1},{}))
        read=selection(configured(operation='observe',mode='delay',delay_ms=250))
        plan=ReplyFaults(read,self.root).claim(read['path'],{'operation':'observe'},{'inputs':[{'deadline':1}]})
        self.assertIsNotNone(plan);self.assertEqual(plan['deadline_ms'],read['observer_deadline_ms'])

    def test_delay_clips_to_original_bound_and_shutdown_never_rearms(self):
        now=time.time_ns()//1000000;cfg=selection(configured(mode='delay',delay_ms=5000))
        owner=ReplyFaults(cfg,self.root);plan=owner.claim(cfg['path'],{'operation':'create','deadline_ms':now+90},{})
        self.assertEqual(plan['deadline_ms'],now+90);start=time.monotonic()
        self.assertTrue(before_reply(plan,threading.Event()));self.assertLess(time.monotonic()-start,.5)
        stopped=threading.Event();stopped.set();self.assertFalse(before_reply(dict(plan,until=time.monotonic()+2,deadline_ms=now+5000),stopped))
        self.assertIsNone(ReplyFaults(cfg,self.root).claim(cfg['path'],{'operation':'create'},{}))

    def test_clock_regression_and_marker_sync_cannot_extend_original_delay(self):
        clock={'mono':40.,'wall':1000000}
        cfg=selection(configured(mode='delay',delay_ms=1000,observer_deadline_ms=1002000))
        def sync(_):clock['mono']+=.25
        class Stop:
            def is_set(self):return False
            def wait(self,seconds):clock['mono']+=seconds;return False
        with patch('integration.single_node.reply_faults.time.monotonic',side_effect=lambda:clock['mono']), \
             patch('integration.single_node.reply_faults.time.time_ns',side_effect=lambda:clock['wall']*1000000), \
             patch('integration.single_node.reply_faults.os.fsync',side_effect=sync):
            plan=ReplyFaults(cfg,self.root).claim(cfg['path'],{'operation':'create'},{})
            self.assertEqual(plan['until'],41.);self.assertEqual(clock['mono'],40.5)
            clock['wall']=1
            self.assertTrue(before_reply(plan,Stop()));self.assertEqual(clock['mono'],41.)
            clock['mono']=40.5;clock['wall']=1002001
            self.assertTrue(before_reply(plan,Stop()));self.assertEqual(clock['mono'],40.5)

    def test_process_kill_after_claim_keeps_test_identity_spent(self):
        cfg=selection(configured(mode='delay',delay_ms=5000));(self.root/'config.json').write_bytes(canonical(cfg))
        script='''import json,sys,threading
from pathlib import Path
from integration.single_node.reply_faults import ReplyFaults,before_reply
p=Path(sys.argv[1]);cfg=json.loads((p/'config.json').read_bytes());x=ReplyFaults(cfg,p).claim(cfg['path'],{'operation':'create'},{})
print('CLAIMED',flush=True);before_reply(x,threading.Event())
'''
        process=subprocess.Popen([sys.executable,'-c',script,str(self.root)],stdout=subprocess.PIPE,text=True)
        try:
            self.assertEqual(process.stdout.readline().strip(),'CLAIMED');process.kill();process.wait(timeout=3)
            self.assertEqual(process.returncode,-9)
            self.assertIsNone(ReplyFaults(cfg,self.root).claim(cfg['path'],{'operation':'create'},{}))
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=3)
            process.stdout.close()

    def test_marker_symlink_corruption_and_finite_identity_limit_refuse(self):
        cfg=selection(configured());path=self.root/'reply-fault-bounded-fault.json'
        path.symlink_to(self.root/'not-present')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):ReplyFaults(cfg,self.root)
        path.unlink();path.write_text('{')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):ReplyFaults(cfg,self.root)
        path.unlink()
        for i in range(MAX_IDENTITIES):
            value=selection(configured(identity='fault-'+str(i)));ReplyFaults(value,self.root).claim(value['path'],{'operation':'create'},{})
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):ReplyFaults(cfg,self.root)

    def test_default_body_is_byte_identical_and_partial_is_exact_actual_prefix(self):
        body=b'{"actual":"owner-committed-response"}';output=io.BytesIO()
        write_body(None,None,output,body);self.assertEqual(output.getvalue(),body)
        class Connection:
            stopped=None;closed=False
            def shutdown(self,value):self.stopped=value
            def close(self):self.closed=True
        conn=Connection();output=io.BytesIO();write_body({'mode':'partial-body'},conn,output,body)
        self.assertEqual(output.getvalue(),body[:32]);self.assertEqual(conn.stopped,socket.SHUT_RDWR);self.assertTrue(conn.closed)


class ReplyFaultTLS(unittest.TestCase):
    """Production pool and fault seam over authenticated file-fixture effects."""
    def setUp(self):
        from http.server import ThreadingHTTPServer
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);prepare(self.root)
        self.owner=server.Ports(self.root/'config.json');self.calls=0;self.local=threading.local();self.fault=None
        self.stop=threading.Event();self.unexpected=[];case=self;original=self.owner.invoke
        def invoke(token,request):
            case.calls+=1;case.local.request=request;return original(token,request)
        self.owner.invoke=invoke
        class Handler(server.handler(self.owner)):
            protocol_version='HTTP/1.1'
            def handle_one_request(self):
                try:super().handle_one_request()
                except (BrokenPipeError,ConnectionResetError,ssl.SSLEOFError):
                    # An intentionally truncated/timed-out response closes the
                    # real peer. Other handler exceptions remain test failures.
                    self.close_connection=True
                except ssl.SSLError as exc:
                    if exc.reason!='UNEXPECTED_EOF_WHILE_READING':raise
                    self.close_connection=True
            def reply(self,status,value):
                plan=case.fault.claim(self.path,case.local.request,value) if self.command=='POST' and status==200 else None
                if not before_reply(plan,case.stop):self.close_connection=True;return
                data=canonical(value);self.send_response(status)
                if plan and plan['mode']=='partial-body':self.close_connection=True
                self.send_header('Content-Length',str(len(data)));self.send_header('Content-Type','application/json')
                if self.close_connection:self.send_header('Connection','close')
                self.end_headers()
                try:write_body(plan,self.connection,self.wfile,data)
                except (BrokenPipeError,ConnectionResetError):pass
        class ObservedServer(ThreadingHTTPServer):
            def handle_error(self,request,address):case.unexpected.append(sys.exc_info()[1])
        self.server=ObservedServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.root/'cert.pem',self.root/'key.pem')
        self.server.socket=context.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start()
        self.endpoint=Endpoint('127.0.0.1',self.server.server_port,str(self.root/'cert.pem'))
        https_pool.configure(dict(https_pool.LIMITS))

    def tearDown(self):
        self.stop.set();https_pool.close();https_pool.configure(None)
        self.server.shutdown();self.server.server_close();self.thread.join(2);self.temp.cleanup()
        self.assertEqual(self.unexpected,[])

    def client(self,**kw):
        cfg=dict(endpoint=self.endpoint,credential='generated-sdk-credential',principal='reader',scope='generated-sdk',
                 descriptor=server.descriptor(),deadline_ms=time.time_ns()//1000000+5000);cfg.update(kw)
        return AtomFeedClient(**cfg)

    def test_partial_after_actual_fixture_commit_is_one_send_then_explicit_same_identity_readback(self):
        cfg=selection(configured());self.fault=ReplyFaults(cfg,self.root);client=self.client()
        mutation=Mutation('generated-sdk','fixed-occurrence')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):client.create(mutation,'text/plain',b'actual-fixture-content')
        self.assertEqual(self.calls,1);self.assertEqual(https_pool._entries,[])
        self.fault=ReplyFaults(cfg,self.root)
        result=client.create(mutation,'text/plain',b'actual-fixture-content')
        self.assertEqual(client.head('generated-sdk')['sequence'],1)
        self.assertEqual(client.get(result['ref']).bytes,b'actual-fixture-content')
        self.assertEqual(self.calls,4)

    def test_delayed_actual_read_bound_has_no_hidden_retry(self):
        until=time.time_ns()//1000000+120
        cfg=selection(configured(operation='head',mode='delay',delay_ms=5000,observer_deadline_ms=until))
        self.fault=ReplyFaults(cfg,self.root);client=self.client(deadline_ms=until)
        with self.assertRaises(ContractError) as caught:client.head('generated-sdk')
        self.assertIn(caught.exception.code,('NOT_AVAILABLE','DEADLINE_EXCEEDED'))
        self.assertEqual(self.calls,1);self.assertTrue((self.root/'reply-fault-bounded-fault.json').exists())
        time.sleep(.15);self.assertEqual(self.client().head('generated-sdk')['sequence'],0);self.assertEqual(self.calls,2)

    def test_shutdown_during_claimed_read_closes_without_success_and_never_rearms(self):
        cfg=selection(configured(operation='head',mode='delay',delay_ms=5000))
        self.fault=ReplyFaults(cfg,self.root);observed=[]
        def read():
            try:observed.append(self.client().head('generated-sdk'))
            except ContractError as e:observed.append(e.code)
        reader=threading.Thread(target=read);reader.start()
        until=time.monotonic()+2;marker=self.root/'reply-fault-bounded-fault.json'
        while not marker.exists() and time.monotonic()<until:time.sleep(.005)
        self.assertTrue(marker.exists());self.stop.set();reader.join(2)
        self.assertFalse(reader.is_alive());self.assertEqual(observed,['NOT_AVAILABLE']);self.assertEqual(self.calls,1)
        self.stop.clear();self.fault=ReplyFaults(cfg,self.root)
        self.assertEqual(self.client().head('generated-sdk')['sequence'],0);self.assertEqual(self.calls,2)

    def test_unauthorized_response_and_health_do_not_consume_fault(self):
        cfg=selection(configured(operation='head'));self.fault=ReplyFaults(cfg,self.root)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.client(credential='wrong').head('generated-sdk')
        self.assertFalse((self.root/'reply-fault-bounded-fault.json').exists())
        import http.client
        c=http.client.HTTPSConnection(self.endpoint.host,self.endpoint.port,context=ssl.create_default_context(cafile=str(self.root/'cert.pem')))
        try:
            c.request('GET','/healthz');response=c.getresponse()
            self.assertEqual(response.status,200);response.read()
        finally:c.close()
        self.assertFalse((self.root/'reply-fault-bounded-fault.json').exists())


class ReplyFaultChart(unittest.TestCase):
    render=chart_fixtures.PreviewFaultChartTests.render
    def test_explicit_partial_and_fixed_delay_render(self):
        for change in ({},{'mode':'delay','delay_ms':5000},
                       {'path':'/memory-source','operation':'head'}):
            result=self.render(configured(**change)['test']);self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn(PROFILE,result.stdout)
    def test_unknown_field_delay_and_combined_fault_refuse(self):
        for change in ({'delay_ms':250},{'mode':'delay','delay_ms':2000},{'path':'/execute'}):
            self.assertNotEqual(self.render(configured(**change)['test']).returncode,0)
        value=configured()['test'];value['drop_response_operation']='create'
        self.assertNotEqual(self.render(value).returncode,0)


if __name__=='__main__':unittest.main()
