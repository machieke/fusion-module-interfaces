"""Deployment seam checks. Unit fixtures are not E5/Chroma/native evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fusion import append_contracts as w, vector_contracts as v
from fusion.append_composition import AppendService
from fusion.contracts import ContractError,canonical
from fusion.memory_services import ReceiptAuthority,SearchPorts,StoragePorts,freeze_placement,COMPOSITION
from fusion.policy import Policy
from fusion.registry import descriptor_wire
from fusion.vector_composition import ReadService,descriptors


class MemoryServiceSeams(unittest.TestCase):
    def config(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.path=self.root/'policy.json'
        from tests.test_append_contracts import AppendContracts
        accepted=AppendContracts().accepted();self.accepted=accepted
        append={k:accepted[k] for k in ('profile','session','scope','corpus','model')}
        append.update(sharing=v.PRIVACY,session_principal='A',writers=['A'],inputs={accepted['content']:accepted['helper_input']},
            root=str(self.root/'projection'),catalogue=[descriptor_wire(d) for d in w.descriptors()],embedding_selection=accepted['selections']['embedding'])
        read=dict(root=append['root'],scope=accepted['scope'],corpus=accepted['corpus'],embedding=v.EMBEDDING,
            sharing=v.PRIVACY,readers=['A','indexer'],catalogue=[descriptor_wire(d) for d in descriptors(v.EMBEDDING,True)],require_ready=True)
        self.cfg=dict(memory_append=append,memory_read=read,
            source=dict(endpoint=dict(host='fusion-storage.unit.svc.cluster.local',port=8443,ca_file='unused'),credential='source'),
            source_delegation=dict(principal='A',session=accepted['session'],scope=accepted['scope']),
            principals={'A':dict(credential='caller',scopes={accepted['scope']:['memory.append.disclose','atom.storage.observe']}),
                        'B':dict(credential='other',scopes={accepted['scope']:['memory.append.disclose','atom.storage.observe']}),
                        'indexer':dict(credential='source',scopes={accepted['scope']:['memory.source.observe']})})
        self.save();return accepted
    def save(self):self.path.write_bytes(canonical(self.cfg))
    def rejects(self,code,fn,*args,**kwargs):
        with self.assertRaises(ContractError) as e:fn(*args,**kwargs)
        self.assertEqual(e.exception.code,code)
    def test_read_only_receipt_delegation_checks_both_current_principals(self):
        intent=self.config();policy=ReceiptAuthority(Policy(self.path),'source')
        service=AppendService(self.path,'source',atoms=object(),policy=policy)
        service.authorize(intent,'disclose')
        self.rejects('UNAUTHORIZED',service.authorize,{**intent,'principal':'B'},'disclose')
        self.rejects('UNAUTHORIZED',service.authorize,intent,'write')
        for who,method in [('A','memory.append.disclose'),('indexer','memory.source.observe')]:
            original=copy.deepcopy(self.cfg);self.cfg['principals'][who]['scopes'][intent['scope']].remove(method);self.save()
            self.rejects('UNAUTHORIZED',service.authorize,intent,'disclose');self.cfg=original;self.save()
        self.cfg['source_delegation']['session']='different';self.save()
        self.rejects('UNAUTHORIZED',service.authorize,intent,'disclose')
    def test_injected_search_never_constructs_detta_and_rejects_storage_paths(self):
        self.config()
        with patch('fusion.adapters.detta.DettaStorage',side_effect=AssertionError('foreign owner')):
            ReadService(self.path,'caller',atoms=object())
            AppendService(self.path,'caller',atoms=object())
            SearchPorts(self.path)
        self.assertFalse((self.root/'projection').exists())
        self.cfg['memory_append']['detta_binary']='forbidden';self.save()
        self.rejects('UNSUPPORTED_PROFILE',SearchPorts,self.path)
    def test_search_cannot_accept_storage_operations(self):
        self.config();ports=SearchPorts(self.path)
        for path in ('/s03-read','/s03-append'):
            self.rejects('UNSUPPORTED_OPERATION',ports.invoke,path,'caller',{'interface_ref':{'id':'atom.storage'}})
    def test_storage_source_refuses_caller_or_arbitrary_operations_before_io(self):
        a=self.config();ports=StoragePorts(self.path)
        from fusion.memory_services import SOURCE_PROFILE
        request=dict(request_id=a['occurrence'],scope=a['scope'],profile=SOURCE_PROFILE,selection='0'*64,operation='head',body={})
        self.rejects('UNAUTHORIZED',ports.invoke,'/memory-source','caller',request)
        self.rejects('UNAUTHORIZED',ports.invoke,'/memory-source','wrong',request)
        self.rejects('UNAUTHORIZED',ports.invoke,'/memory-source','source',{**request,'scope':'private'})
        self.rejects('INVALID_ARGUMENT',ports.invoke,'/memory-source','source',{**request,'principal':'A'})
    def test_embedding_composition_preserves_existing_credential_rotation_contract(self):
        from fusion import embedding_contracts as e
        from fusion.embedding_composition import configuration
        self.config();ca=self.root/'ca';ca.write_text('fixture CA')
        cfg=dict(profile=e.PROFILE,sharing=v.PRIVACY,fallback=False,model=v.EMBEDDING,preprocessing=e.PREPROCESSING,
                 principal='A',scope='synthetic',inputs={'query':'query'},placement='service-network',
                 service_composition=COMPOSITION,catalogue=[descriptor_wire(e.descriptor())],
                 endpoints={'embedding':dict(host='fusion-embedding.test.svc.cluster.local',port=8443,ca_file=str(ca))},
                 service_credentials={'embedding':'first'})
        path=self.root/'encoder.json';path.write_bytes(canonical(cfg));first,_,frozen=configuration(path)
        self.assertEqual(first['credential'],'first')
        cfg['service_credentials']['embedding']='rotated';path.write_bytes(canonical(cfg));second,_,other=configuration(path)
        self.assertEqual(second['credential'],'rotated');self.assertEqual(frozen,other)

    def test_service_placement_requires_explicit_consent_and_freezes_ca(self):
        self.config();ca=self.root/'ca';ca.write_text('fixture CA identity, no TLS claimed')
        cfg=dict(service_composition=COMPOSITION,fallback=False,endpoints={'embedding':dict(host='fusion-embedding.test.svc.cluster.local',port=8443,ca_file=str(ca))},service_credentials={'embedding':'token'})
        before=freeze_placement(cfg,('embedding',));ca.write_text('rotated')
        self.assertNotEqual(before,freeze_placement(cfg,('embedding',)))
        for updates in ({'fallback':True},{'service_composition':'old'},{'provider_config':'local'}, {'endpoint':{}}):
            self.rejects('UNSUPPORTED_PROFILE',freeze_placement,{**cfg,**updates},('embedding',))

if __name__=='__main__':unittest.main()
