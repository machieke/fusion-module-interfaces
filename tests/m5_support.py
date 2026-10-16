"""Generated private corpus setup via ports; expected answers belong only to tests."""
from dataclasses import asdict,replace
import json
import os
from pathlib import Path
import random
import secrets
import tempfile
from fusion import lookup_contracts as c
from fusion.contracts import canonical
from fusion.lookup_composition import descriptors,OPERATIONS,open_lookup
from fusion.lookup import LookupConsumer
from fusion.ports import Mutation
from fusion.registry import descriptor_wire
from tests.m2_support import PortOnly

SCOPE='private-lookup'
ROOT=Path(__file__).resolve().parents[1]
class LookupHarness:
    def __init__(self,root=None,*,real=False,search='sqlite',hook=lambda stage:None):
        self.temp=tempfile.TemporaryDirectory(prefix='fusion-m5-') if root is None else None
        self.root=Path(root or self.temp.name);self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'lookup-config.json';self.hook=hook;self.real=real
        if self.path.exists():
            self.config=json.loads(self.path.read_text());self.credential=self.config['principals']['owner']['credential']
        else:
            self.credential='generated-'+secrets.token_hex(16)
            ops=[name+'.'+op for name,values in OPERATIONS.items() for op in values]
            self.config={'lookup_root':str(self.root/'private'),'shared_roots':[str(self.root/'shared')],
                'lookup_scopes':{SCOPE:'owner','other-lookup':'other'},'relation_schemas':c.copy(c.SCHEMAS),
                'lookup_descriptors':[descriptor_wire(d) for d in descriptors('detta' if real else 'fixture-files',search)],
                'principals':{'owner':{'credential':self.credential,'scopes':{SCOPE:ops}},'other':{'credential':'generated-other','scopes':{'other-lookup':ops}}},
                'detta_binary':os.environ.get('M2_DETTA_BINARY',str(ROOT/'artifacts/detta-build/target/debug/fusion-detta-adapter'))}
            self.save()
        self.reopen()
    def save(self):self.path.write_bytes(canonical(self.config));self.path.chmod(0o600)
    def reopen(self):
        self.modules=open_lookup(self.path,self.credential,SCOPE,hook=self.hook,wrap=PortOnly)
        self.atoms,self.relations,self.search=self.modules.atoms,self.modules.relations,self.modules.search
        return self
    def consumer(self,name='caller'):
        m=self.modules
        return LookupConsumer(m.root/(name+'.sqlite'),m.atoms,m.relations,m.search,m.access,m.selections,self.hook)
    def create(self,key,**fields):return self.atoms.create(Mutation(SCOPE,key),c.KNOWLEDGE,canonical(fields))['ref']
    def query(self,minimum=None,limit=2,**fields):return c.AttributeQuery(SCOPE,{'all':[{'field':k,'eq':v} for k,v in fields.items()]},minimum or self.atoms.head(SCOPE),limit)
    def drain(self,limit=4):
        receipts=[]
        for _ in range(c.MAX_ATOMS):
            receipt=self.search.catchUp(SCOPE,limit);receipts.append(receipt)
            if receipt['at']==receipt['target'] and not receipt['rebuilding']:return receipts
        raise AssertionError('bounded catch-up exhausted')
    def seed(self,seed=11):
        rng=random.Random(seed);nonce=secrets.token_hex(8);canary='PRIVATE-LOOKUP-'+secrets.token_hex(16)
        specs=[('task-'+str(i),{'kind':'task','topic':'retrieval-demo','label':canary+'-'+str(i)}) for i in range(5)]
        specs += [('pre-'+str(i),{'kind':'prerequisite','topic':'retrieval-demo','label':nonce+'-prerequisite-'+str(i)}) for i in range(3)]
        specs += [('wrong-kind',{'kind':'note','topic':'retrieval-demo'}),('wrong-topic',{'kind':'task','topic':'elsewhere'}),('missing',{'kind':'task'})]
        rng.shuffle(specs);refs={name:self.create(nonce+'/'+name,**fields) for name,fields in specs}
        edges=[]
        for i in range(5):
            for j in range(3):edges.append(self.relations.assertRelation(Mutation(SCOPE,nonce+'/edge-'+str(i)+'-'+str(j)),'requires/1',(('dependent',refs['task-'+str(i)]),('prerequisite',refs['pre-'+str(j)])),True))
        self.relations.assertRelation(Mutation(SCOPE,nonce+'/unrelated'),'association/1',(('first',refs['wrong-kind']),('second',refs['wrong-topic'])),False)
        self.atoms.create(Mutation(SCOPE,nonce+'/ignored'),'text/plain',b'not enrolled')
        other=open_lookup(self.path,'generated-other','other-lookup',wrap=PortOnly)
        other.atoms.create(Mutation('other-lookup',nonce+'/foreign'),c.KNOWLEDGE,canonical({'kind':'task','topic':'retrieval-demo','label':'PRIVATE-OTHER-SCOPE'}))
        head=self.atoms.head(SCOPE)
        # The consumer never receives this oracle. It receives only attributes + head.
        return {'refs':refs,'edges':edges,'head':head,'canary':canary,'order':[refs[name] for name,fields in specs if fields.get('kind')=='task' and fields.get('topic')=='retrieval-demo']}
    def close(self):
        if self.temp:self.temp.cleanup()
