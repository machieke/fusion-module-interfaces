"""Deterministic vector/DTO fixtures only; no real-model integration claims."""
from dataclasses import asdict
import copy
import math
import time
import unittest
import uuid
from fusion import vector_contracts as c
from fusion.contracts import ContractError,canonical,digest
from fusion.vector_composition import descriptors,select,validate_request
from fusion.registry import descriptor_wire,descriptor_read,selection_token

class VectorContracts(unittest.TestCase):
    def request(self):
        head=dict(source=str(uuid.uuid4()),scope_ref='generated-s03',sequence=0,profile='immutable-commit-feed/1')
        snap=dict(head=head,corpus='generated',embedding=c.FIXTURE,index=c.INDEX,profile=c.PROFILE)
        snap.update(logical=digest(canonical(snap)),generation=str(uuid.uuid4()))
        return asdict(c.VectorQuery(str(uuid.uuid4()),'generated-s03',snap,[1.]+[0.]*1023,8,int(time.time()*1000)+30000))
    def test_float32_encoding_and_metric_oracle(self):
        a=[1.]+[0.]*1023;b=[0.,1.]+[0.]*1022
        self.assertEqual(len(c.vector_bytes(a)),4096);self.assertEqual(c.from_bytes(c.vector_bytes(a)),a)
        self.assertEqual(sum((x-y)**2 for x,y in zip(a,b)),2.)
    def test_vector_domains(self):
        for value in ([],[0.]*1024,[True]+[0.]*1023,[float('nan')]+[0.]*1023,[float('inf')]+[0.]*1023,[2.]+[0.]*1023):
            with self.subTest(value=str(value[:2])),self.assertRaises(ContractError):c.vector(value)
    def test_closed_profile_and_snapshot(self):
        req=self.request();self.assertEqual(c.query(req),req)
        for field,value in [('cursor','invented'),('metric','cosine'),('profile','exact-attributes/1'),('k',101),('k',0)]:
            with self.subTest(field=field,value=value),self.assertRaises(ContractError):c.query({**req,field:value})
        for field,value in [('embedding','other-model'),('generation','../index'),('logical','wrong')]:
            with self.subTest(field=field),self.assertRaises(ContractError):c.query({**req,'snapshot':{**req['snapshot'],field:value}})
    def test_descriptor_and_privacy_binding(self):
        catalogue=descriptors(c.FIXTURE);chosen=select(catalogue,c.FIXTURE);d=chosen['search'];req=self.request()
        wire=dict(request_id=req['request_id'],interface_ref=dict(id='search',version=d.version),operation='query',scope=req['scope'],profile=c.PROFILE,selection=selection_token(d),body=req)
        validate_request(wire,chosen)
        for key,value in [('selection','other'),('profile','external-web-search/1'),('operation','build')]:
            with self.subTest(key=key),self.assertRaises(ContractError):validate_request({**wire,key:value},chosen)
        from dataclasses import replace
        with self.assertRaises(ContractError):select([replace(x,privacy='private-local-only') for x in catalogue],c.FIXTURE)
        with self.assertRaises(ContractError):select(catalogue,c.EMBEDDING)
    def test_malformed_results_never_empty(self):
        req=self.request();result=dict(request_id=req['request_id'],request_digest=digest(canonical(req)),snapshot=req['snapshot'],hits=[],top_k=8,exhaustive=False)
        self.assertEqual(c.result(result,req),result)
        for key,value in [('request_id',str(uuid.uuid4())),('request_digest','wrong'),('exhaustive',True),('top_k',7),('hits',None),('cursor','x')]:
            with self.subTest(key=key),self.assertRaises(ContractError):c.result({**result,key:value},req)
        ref=dict(scope_ref=req['scope'],id=str(uuid.uuid4()),revision=1,digest='a'*64)
        hit=dict(ref=ref,uuid=str(uuid.uuid4()),distance=0.)
        for hits in ([hit,hit],[{**hit,'distance':float('nan')}],[{**hit,'ref':{**ref,'scope_ref':'private'}}],[{**hit,'distance':2.},{**hit,'uuid':str(uuid.uuid4()),'distance':1.}]):
            with self.subTest(hits=str(hits)[:80]),self.assertRaises(ContractError):c.result({**result,'hits':hits},req)

if __name__=='__main__':unittest.main()
