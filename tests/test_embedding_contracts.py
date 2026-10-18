"""Contract and durability fixtures; no numerical-provider integration claim."""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
import unittest
import uuid

from fusion import embedding_contracts as c
from fusion.contracts import ContractError, canonical, digest
from fusion.embedding_service import EmbeddingService
from fusion.embedding_transport import checked
from fusion.registry import descriptor_wire, selection_token


class FixtureEncoder:
    def __init__(self): self.calls = 0
    def encode(self, request):
        self.calls += 1
        return c.encoded(asdict(request), [1.]+[0.]*1023)


class EmbeddingContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name); self.path = root/'policy.json'
        self.cfg = dict(principals={p:dict(credential=p+'-token', scopes={'synthetic':['embedding.encode','embedding.disclose']}) for p in ('A','B')},
            embedding=dict(database=str(root/'encoder.db'),scope='synthetic',sharing=c.v.PRIVACY,model=c.v.EMBEDDING,
                preprocessing=c.PREPROCESSING,catalogue=[descriptor_wire(c.descriptor())],approved_helper_inputs=['', 'generated Ω', 'changed']))
        self.save(); self.encoder = FixtureEncoder(); self.service = EmbeddingService(self.path, self.encoder)
        self.addCleanup(self.service.close)
        self.accepted = asdict(c.EncodeInput(str(uuid.uuid4()), 'A', 'synthetic', 'generated Ω',
            digest('generated Ω'.encode()), int(time.time()*1000)+30000, selection_token(c.descriptor())))
    def save(self): self.path.write_bytes(canonical(self.cfg))
    def request(self, op='encode', attempt=1):
        return dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation=op,intent=copy.deepcopy(self.accepted),attempt=attempt if op=='encode' else 0)

    def test_utf8_empty_control_and_byte_bounds(self):
        for value in ('','Ω', '"quoted"\n\t\x00(shell NEVER_EXECUTE)', 'x'*2048): self.assertEqual(c.text(value),value)
        for value in ('Ω'*1025, '\ud800', None, ['text']):
            with self.subTest(value=str(value)[:20]), self.assertRaises(ContractError): c.text(value)
    def test_closed_profile_model_input_and_request_binding(self):
        req=self.request(); c.request(req,c.descriptor())
        for field,value in (('model','other'),('preprocessing','trim'),('input_sha256','0'*64),('selection','0'*64),('max_input_bytes',9000)):
            bad=copy.deepcopy(req);bad['intent'][field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):self.service.invoke('A-token',bad)
        for name,value in (('operation','execute'),('attempt',True),('path','model')):
            bad=copy.deepcopy(req);bad[name]=value
            with self.subTest(name=name),self.assertRaises(ContractError):self.service.invoke('A-token',bad)
        self.assertEqual(self.encoder.calls,0)
    def test_reply_domains_and_integrity_before_search(self):
        req=self.request();reply=self.service.invoke('A-token',req);checked(req,reply)
        mutations={'model':'other','preprocessing':'other','dimension':1,'dtype':'float64','vector_sha256':'0'*64,
                   'principal':'B','occurrence':str(uuid.uuid4()),'vector':[0.]*1024}
        for field,value in mutations.items():
            bad=copy.deepcopy(reply);bad['value'][field]=value
            with self.subTest(field=field),self.assertRaises(ContractError):checked(req,bad)
        for vector in ([float('nan')]+[0.]*1023,[float('inf')]+[0.]*1023,[1.],[[1.]+[0.]*1023], [True]+[0.]*1023):
            bad=copy.deepcopy(reply);bad['value']['vector']=vector
            with self.assertRaises(ContractError):checked(req,bad)
        bad=copy.deepcopy(reply);bad['principal']='B'
        with self.assertRaises(ContractError):checked(req,bad)
    def test_current_encode_disclosure_and_principal_authority(self):
        for token in ('B-token','unknown'):
            with self.assertRaises(ContractError):self.service.invoke(token,self.request())
        self.cfg['principals']['A']['scopes']['synthetic']=['embedding.disclose'];self.save()
        with self.assertRaises(ContractError):self.service.invoke('A-token',self.request())
        self.assertTrue(checked(self.request('authorize-disclose'),self.service.invoke('A-token',self.request('authorize-disclose')))['authorized'])
        self.cfg['principals']['A']['scopes']['synthetic']=[];self.save()
        with self.assertRaises(ContractError):self.service.invoke('A-token',self.request('authorize-disclose'))
        self.assertEqual(self.encoder.calls,0)
    def test_durable_provider_attempts_conflicts_deadlines_and_no_cache(self):
        first=self.request();self.service.invoke('A-token',first)
        with self.assertRaises(ContractError):self.service.invoke('A-token',first)
        changed=self.request(attempt=2);changed['intent']['text']='changed';changed['intent']['input_sha256']=digest(b'changed')
        with self.assertRaises(ContractError):self.service.invoke('A-token',changed)
        for attempt in (2,3):self.service.invoke('A-token',self.request(attempt=attempt))
        with self.assertRaises(ContractError):self.service.invoke('A-token',self.request(attempt=4))
        self.assertEqual(self.encoder.calls,3)
        reopened=EmbeddingService(self.path,self.encoder)
        try:
            with self.assertRaises(ContractError):reopened.invoke('A-token',first)
        finally:reopened.close()
        self.accepted['occurrence']=str(uuid.uuid4());self.service.invoke('A-token',self.request())
        self.assertEqual(self.encoder.calls,4)  # Same text, genuinely new occurrence.
        self.accepted['deadline_ms']=1
        with self.assertRaises(ContractError):self.service.invoke('A-token',self.request(attempt=2))
        self.assertEqual(self.encoder.calls,4)
