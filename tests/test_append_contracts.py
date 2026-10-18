"""DTO/consent fixtures; these tests make no native-provider claim."""
from dataclasses import asdict,replace
import copy
import unittest
import uuid
from fusion import append_contracts as c,embedding_contracts as e,vector_contracts as v
from fusion.contracts import ContractError,canonical,digest,encode
from fusion.registry import selection_token


class AppendContracts(unittest.TestCase):
    def accepted(self):
        chosen=c.select(c.descriptors())
        return dict(profile=c.PROFILE,session=str(uuid.uuid4()),occurrence=str(uuid.uuid4()),principal='A',
            scope='synthetic',corpus='new',uuid=str(uuid.uuid4()),time='2031-04-05 06:07:08',content='Synthetic Ω',
            helper_input='Synthetic Ω',model=v.EMBEDDING,vector_sha256=digest(v.vector_bytes([1.]+[0.]*1023)),
            deadline_ms=2000000000000,selections={**{n:selection_token(d) for n,d in chosen.items()},
                'embedding':selection_token(e.descriptor(c.MEMORY_EMBEDDING))})

    def wire(self,op='create'):
        accepted=self.accepted();chosen=c.select(c.descriptors());d=chosen['atom.storage']
        body=dict(role='payload',content_type=v.PAYLOAD,data=encode(canonical(c.payload(accepted))))
        return chosen,dict(request_id=accepted['occurrence'],scope=accepted['scope'],interface_ref=dict(id=d.interface,version=d.version),
            operation=op,profile=next(iter(d.profiles)),selection=selection_token(d),intent=accepted,body=body)

    def test_closed_append_and_historical_read_only_wire(self):
        chosen,wire=self.wire();self.assertEqual(c.request(wire,chosen),wire)
        for name,value in (('operation','delete'),('operation','eval'),('profile','memory/1'),('selection','0'*64),('path','/tmp/private')):
            with self.subTest(name=name,value=value),self.assertRaises(ContractError):c.request({**wire,name:value},chosen)
        from fusion.vector_composition import validate_request,select,descriptors
        readonly={k:x for k,x in wire.items() if k!='intent'}
        with self.assertRaises(ContractError):validate_request(readonly,select(descriptors(v.EMBEDDING),v.EMBEDDING))

    def test_memory_encoding_purpose_does_not_reauthorize_query_profile(self):
        query=e.descriptor();memory=e.descriptor(c.MEMORY_EMBEDDING)
        self.assertEqual(query.profiles,frozenset({'neoclaw-e5-query-text/1'}))
        self.assertEqual(e.select([memory],c.MEMORY_EMBEDDING),memory)
        with self.assertRaises(ContractError):e.select([memory])
        with self.assertRaises(ContractError):e.select([query],c.MEMORY_EMBEDDING)
        self.assertEqual(query.features,memory.features)

    def test_utf8_serialization_and_transformation_intersection(self):
        for raw,helper in (('Synthetic Ω\n\t\x00','Synthetic Ω_newline_\t\x00'),('x','x'*2048)):
            c.text(raw,helper,'s','c')
        for raw,helper in (('', ''),('x'*2049,'x'),('x','x'*2049),('x','\ud800'),('\x00'*1500,'ok')):
            with self.subTest(raw=len(raw),helper=len(helper)),self.assertRaises(ContractError):c.text(raw,helper,'s','c')

    def test_binding_envelopes_reject_changed_semantics(self):
        accepted=self.accepted();original=c.binding_bytes(accepted)
        for field,value in (('content','other'),('time','2031-04-06 06:07:08'),('uuid',str(uuid.uuid4())),('helper_input','other'),('deadline_ms',2000000000001)):
            changed={**accepted,field:value}
            with self.subTest(field=field),self.assertRaises(ContractError):c.envelope(changed,'binding',c.BINDING,original)
        with self.assertRaises(ContractError):c.envelope(accepted,'payload',v.PAYLOAD,canonical({**c.payload(accepted),'content':'other'}))
        with self.assertRaises(ContractError):c.envelope(accepted,'vector',v.VECTOR,v.vector_bytes([0.,1.]+[0.]*1022))
        for timestamp in ('2031-02-30 00:00:00','2031-4-05 06:07:08','../state'):
            with self.assertRaises(ContractError):c.timestamp(timestamp)

    def test_observations_are_explicit_and_receipts_validated(self):
        d=c.select(c.descriptors())['atom.storage']
        empty=dict(found=False,write=None,through=None,content_type=None,size=None)
        self.assertEqual(c.observation(empty,'s',d),empty)
        for value in (None,{},dict(empty,found=0),dict(empty,write={}),dict(empty,found=True)):
            with self.subTest(value=value),self.assertRaises(ContractError):c.observation(value,'s',d)

    def test_selected_scope_privacy_and_model_are_not_command_arguments(self):
        accepted=self.accepted()
        for field,value in (('model',v.FIXTURE),('profile','neoclaw-append-only-memory/2'),('path','/tmp'),('function','eval')):
            with self.subTest(field=field),self.assertRaises(ContractError):c.intent({**accepted,field:value})
        with self.assertRaises(ContractError):c.select([replace(d,privacy='private-local-only') for d in c.descriptors()])


if __name__=='__main__':unittest.main()
