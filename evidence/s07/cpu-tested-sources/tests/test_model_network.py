"""Actual TLS/authentication with a labelled recorded model backend."""
import json
from pathlib import Path
import subprocess
import sys
import time
from fusion.contracts import canonical
from fusion.model_transport import Client
from integration.neoclaw.model_composition import EXPRESSION
from tests.test_model import ModelTests,setup


class ModelNetwork(ModelTests):
    # Only the explicitly selected network methods below are discovered.
    def network(self):
        root=self.root
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'key'),
            '-out',str(root/'cert'),'-days','1','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],capture_output=True,check=True)
        self.cfg.update(tls_key=str(root/'key'),tls_certificate=str(root/'cert'))
        self.path.write_bytes(canonical(self.cfg));ready=root/'ready'
        log=open(root/'host.log','a');self.addCleanup(log.close)
        process=subprocess.Popen([sys.executable,'-m','integration.neoclaw.model_fixture_host',str(self.path),'--port','0','--ready',str(ready)],stdout=log,stderr=log)
        self.addCleanup(lambda:(process.kill(),process.wait(timeout=5)) if process.poll() is None else None)
        until=time.monotonic()+5
        while not ready.exists() and time.monotonic()<until and process.poll() is None:time.sleep(.01)
        self.assertTrue(ready.exists())
        cfg=self.cfg['model_completion'];client={k:cfg[k] for k in ('scope','sharing','catalogue','disclosure')}
        client.update(profile=self.accepted['profile'],principal='A',session=self.accepted['session'],placement='network',fallback=False,
            commands=[['metta',EXPRESSION]],credential='generated-token',endpoint=dict(host='127.0.0.1',port=json.loads(ready.read_text())['port'],ca_file=str(root/'cert')))
        path=root/'client.json';path.write_bytes(canonical(client));return Client(path),path,client
    def test_network_replay_and_revocation(self):
        client,path,cfg=self.network();value=client.invoke('complete',self.accepted)
        self.assertEqual(value,client.invoke('complete',self.accepted));self.assertEqual(value,client.invoke('observe',self.accepted))
        self.cfg['principals']['A']['scopes'][self.accepted['scope']].remove('model.disclose');self.path.write_bytes(canonical(self.cfg))
        self.code('UNAUTHORIZED',lambda:client.invoke('authorize',self.accepted))
    def test_network_cpu_profile_selection_and_capture(self):
        from fusion import model_contracts as c
        from fusion.registry import descriptor_wire,selection_token
        self.cfg['model_completion']['catalogue']=[descriptor_wire(c.descriptor(c.CPU_PROFILE))]
        self.accepted.update(profile=c.CPU_PROFILE,selection=selection_token(c.descriptor(c.CPU_PROFILE)),
            limits=c.limits(c.CPU_PROFILE),deadline_ms=time.time_ns()//1_000_000+299000)
        client,path,cfg=self.network();value=client.invoke('complete',self.accepted)
        self.assertEqual(value,client.invoke('complete',self.accepted))
        old=dict(self.accepted,profile=c.PROFILE,selection=selection_token(c.descriptor()),limits=c.limits(c.PROFILE))
        self.code('UNSUPPORTED_PROFILE',lambda:client.invoke('complete',old))
    def test_network_wrong_credential_and_deadline_no_fallback(self):
        client,path,cfg=self.network();cfg['credential']='wrong';path.write_bytes(canonical(cfg))
        self.code('UNAUTHORIZED',lambda:client.invoke('complete',self.accepted))
        cfg['credential']='generated-token';path.write_bytes(canonical(cfg));self.accepted['deadline_ms']=1
        self.code('DEADLINE_EXCEEDED',lambda:client.invoke('complete',self.accepted))
        self.assertEqual(client.invoke('observe',self.accepted)['state'],'absent')
    def test_network_untrusted_certificate_no_fallback(self):
        client,path,cfg=self.network()
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(self.root/'wrong-key'),
            '-out',str(self.root/'wrong-cert'),'-days','1','-subj','/CN=127.0.0.1'],capture_output=True,check=True)
        cfg['endpoint']['ca_file']=str(self.root/'wrong-cert');path.write_bytes(canonical(cfg));other=Client(path)
        self.code('NOT_AVAILABLE',lambda:other.invoke('complete',self.accepted))


def load_tests(loader,tests,pattern):
    import unittest
    return unittest.TestSuite(ModelNetwork(name) for name in ModelNetwork.__dict__ if name.startswith('test_network_'))
