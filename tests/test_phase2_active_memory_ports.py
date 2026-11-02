"""Real Chroma/lifecycle/typed ports; explicit file-feed and vector fixtures.

Dependency injection replaces source transport only. No native, E5, DeTTa or
pod claim: authoritative fixture enrollment feeds the actual projection.
"""
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid
from fusion import vector_contracts as v,preview_vector_contracts as c
from fusion.contracts import canonical,ContractError
from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.preview_memory_services import Client,descriptor,OPS,COMPOSITION
from fusion.ports import Mutation
from fusion.registry import descriptor_wire
from fusion.vector_enrollment import enroll


class ActivePorts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.scope='synthetic-active-ports';self.corpus='generated-port-corpus'
        self.atoms=FileFeedFixture(self.root/'atoms.json',SimpleNamespace(authorize=lambda *_:'A'))
        scopes={self.scope:[n+'.'+op for n,ops in OPS.items() for op in ops]+[
            'memory.lifecycle.lifecycle.'+op for op in ('read','project','introduce','supersede','withdraw','history')]}
        self.storage=self.root/'storage.json';self.search=self.root/'search.json'
        for name,path in [('memory.lifecycle',self.storage),('search',self.search)]:
            cfg=dict(principals={'A':dict(credential='synthetic-token',scopes=scopes)},
                active_memory=dict(profile=COMPOSITION,scope=self.scope,corpus=self.corpus,root=str(self.root/name),descriptors={name:descriptor_wire(descriptor(name))}),
                memory_read=dict(scope=self.scope,queries=['synthetic query']))
            if name=='search':cfg['active_memory']['lifecycle_client']=self.config(self.storage,'memory.lifecycle')
            path.write_bytes(canonical(cfg))
        self.lifecycle=Client(self.config(self.storage,'memory.lifecycle'),'memory.lifecycle',inline=True)
        self.projection=Client(self.config(self.search,'search'),'search',inline=True)
        for target in ('fusion.vector_composition.ReadService','fusion.memory_services.SearchPorts'):
            mocked=patch(target,side_effect=lambda *_,**kw:SimpleNamespace(atoms=self.atoms if target.endswith('ReadService') else lambda:self.atoms))
            # Bind separate constructors; no foreign journal is opened.
            mocked=patch(target,return_value=SimpleNamespace(atoms=self.atoms if target.endswith('ReadService') else lambda:self.atoms))
            mocked.start();self.addCleanup(mocked.stop)

    def config(self,path,name):return dict(composition=COMPOSITION,placement='local',fallback=False,principal='A',scope=self.scope,
        credential='synthetic-token',provider_config=str(path),descriptors={name:descriptor_wire(descriptor(name))})

    def test_actual_query_passes_full_disclosure_arguments_and_withdrawal_blocks_old_view(self):
        deadline=int(time.time()*1000)+30000;identity=str(uuid.uuid4());vector=[1.]+[0.]*1023
        ref=enroll(self.atoms,self.scope,self.corpus,v.EMBEDDING,identity,
            dict(scope=self.scope,corpus=self.corpus,uuid=identity,time='2026-11-02 00:00:00',content='Fixture vector payload'),vector)
        receipt=self.lifecycle.call('change',Mutation(self.scope,'introduce'),'introduce',dict(logical_id=None,expected_revision=0,enrollment=ref,deadline_ms=deadline))
        snap=self.projection.call('build',receipt['source_head'],receipt['at'],'first-build',deadline)
        self.assertEqual(self.projection.call('current',receipt['at']),snap)
        query=asdict(c.VectorQuery(str(uuid.uuid4()),self.scope,snap,vector,2,deadline))
        self.assertEqual(self.projection.call('query',query)['hits'][0]['uuid'],identity)
        gone=self.lifecycle.call('change',Mutation(self.scope,'withdraw'),'withdraw',dict(logical_id=receipt['logical_id'],expected_revision=1,enrollment=None,deadline_ms=deadline))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.projection.call('query',query)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.projection.call('authorize','synthetic query',snap)
        latest=self.projection.call('build',gone['source_head'],gone['at'],'withdraw-build',deadline)
        self.assertEqual(self.projection.call('query',{**query,'snapshot':latest})['hits'],[])

    def test_original_deadline_replay_and_changed_deadline_conflict(self):
        deadline=int(time.time()*1000)+10000;identity=str(uuid.uuid4());vector=[1.]+[0.]*1023
        ref=enroll(self.atoms,self.scope,self.corpus,v.EMBEDDING,identity,
            dict(scope=self.scope,corpus=self.corpus,uuid=identity,time='2026-11-02 00:00:00',content='Fixture payload'),vector)
        args=dict(logical_id=None,expected_revision=0,enrollment=ref,deadline_ms=deadline)
        first=self.lifecycle.call('change',Mutation(self.scope,'same'),'introduce',args)
        with patch('fusion.preview_lifecycle.time.time_ns',return_value=(deadline+1)*1000000):
            self.assertEqual(self.lifecycle.call('change',Mutation(self.scope,'same'),'introduce',args),first)
            with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):
                self.lifecycle.call('change',Mutation(self.scope,'new'),'introduce',args)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            self.lifecycle.call('change',Mutation(self.scope,'same'),'introduce',{**args,'deadline_ms':deadline+100})

if __name__=='__main__':unittest.main()
