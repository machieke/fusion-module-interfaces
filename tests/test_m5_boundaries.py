"""Adversarial ownership, authority, bounded capacity and response contracts."""
from dataclasses import replace
import builtins,hashlib,sqlite3,unittest
from unittest.mock import patch
from fusion import lookup_contracts as c
from fusion.contracts import ContractError,canonical,digest
from fusion.lookup import LookupConsumer
from fusion.ports import Mutation
from fusion.lookup_composition import open_lookup,descriptors
from fusion.registry import descriptor_wire
from tests.m5_support import LookupHarness,SCOPE,PortOnly

class Boundaries(unittest.TestCase):
    def harness(self,provider='sqlite'):
        h=LookupHarness(search=provider);self.addCleanup(h.close);return h
    def error(self,code,fn):
        with self.assertRaises(ContractError) as error:fn()
        self.assertEqual(error.exception.code,code)
    def test_bad_shape_bounds_profile_and_private_placement(self):
        h=self.harness();q=h.query(kind='task')
        for expression in [{'all':[{'field':[],'eq':'x'}]},{'all':[{'field':'kind','eq':'\ud800'}]}, {'all':[{'field':'kind','eq':{'all':[]}}]}]:
            self.error('INVALID_ARGUMENT',lambda:h.search.query(replace(q,expression=expression)))
        for ref in (None,[],{},'not-a-ref'):
            self.error('INVALID_ARGUMENT',lambda:h.atoms.get(ref));self.error('INVALID_ARGUMENT',lambda:h.relations.getRelation(ref))
        for limit in (True,0,9,-1):self.error('INVALID_ARGUMENT',lambda:h.search.catchUp(SCOPE,limit))
        self.error('INVALID_ARGUMENT',lambda:c.record(b'{"kind":"\\ud800"}'))
        for descriptor in h.config['lookup_descriptors']:descriptor['profiles']=['legacy/0']
        h.save();self.error('UNSUPPORTED_PROFILE',h.reopen)
        h.config['lookup_descriptors']=[descriptor_wire(d) for d in descriptors('fixture-files')]
        h.config['lookup_root']=h.config['shared_roots'][0];h.save();self.error('UNSUPPORTED_PROFILE',h.reopen)
    def test_feed_rejects_legacy_store_and_missing_incarnation(self):
        from fusion.atom_feed import FeedAtomOwner
        h=self.harness();path=h.root/'old.sqlite'
        with sqlite3.connect(path) as db:db.execute('CREATE TABLE atoms(value TEXT)');db.execute("INSERT INTO atoms VALUES('old')")
        self.error('UNSUPPORTED_PROFILE',lambda:FeedAtomOwner(path,None,h.modules.access['atom.storage']))
        path2=h.root/'new.sqlite';owner=FeedAtomOwner(path2,None,h.modules.access['atom.storage'])
        with sqlite3.connect(path2) as db:
            db.execute('DELETE FROM feed_meta');db.execute("INSERT INTO feed_atoms VALUES('x',1,'x','x','x','x')")
        self.error('NOT_AVAILABLE',lambda:FeedAtomOwner(path2,None,h.modules.access['atom.storage']))
    def test_query_cursor_rebinding_auth_and_generation(self):
        for provider in ('sqlite','atomic-file-fixture'):
            h=self.harness(provider);[h.create(str(i),kind='task') for i in range(3)];h.drain();q=h.query(kind='task');first=h.search.query(q)
            for changed in (replace(q,expression={'all':[{'field':'kind','eq':'other'}]}),replace(q,limit=1),replace(q,minimum={**q.minimum,'sequence':0})):
                self.error('CONFLICT',lambda:h.search.query(replace(changed,cursor=first['cursor'])))
            self.error('INVALID_ARGUMENT',lambda:h.search.query(replace(q,cursor='malformed')))
            self.error('UNAUTHORIZED',lambda:h.search.query(replace(q,scope_ref='other-lookup',minimum={**q.minimum,'scope_ref':'other-lookup'},cursor=first['cursor'])))
            # Same corpus/scope reassigned to a different authorized principal: old cursor is invalid.
            h.config['lookup_scopes'][SCOPE]='replacement';h.config['principals']['replacement']={'credential':'replacement','scopes':{SCOPE:h.config['principals']['owner']['scopes'][SCOPE]}}
            h.save();other=open_lookup(h.path,'replacement',SCOPE)
            self.error('CONFLICT',lambda:other.search.query(replace(q,cursor=first['cursor'])))
            self.error('UNAUTHORIZED',lambda:h.search.query(q))
    def test_authority_revocation_between_reads_and_commit(self):
        for provider in ('sqlite','atomic-file-fixture'):
            h=self.harness(provider);h.create('a',kind='task');head=h.atoms.head(SCOPE)
            original=list(h.config['principals']['owner']['scopes'][SCOPE])
            def revoke(stage):
                if stage=='before_checkpoint_commit':h.config['principals']['owner']['scopes'][SCOPE].remove('search.catchUp');h.save()
            h.hook=revoke;h.reopen();self.error('UNAUTHORIZED',lambda:h.search.catchUp(SCOPE,2))
            self.assertEqual(h.search.query(h.query({**head,'sequence':0},kind='task'))['refs'],[])
            h.config['principals']['owner']['scopes'][SCOPE]=original;h.save();h.hook=lambda stage:None;h.reopen();h.drain()
            # Replay rechecks current query authority, even when result is durable.
            consumer=h.consumer();consumer.lookup(Mutation(SCOPE,'done'),h.query(kind='task'))
            h.config['principals']['owner']['scopes'][SCOPE].remove('search.query');h.save()
            self.error('UNAUTHORIZED',lambda:consumer.lookup(Mutation(SCOPE,'done'),h.query(kind='task')))
        h=self.harness();a=h.create('a',kind='task');b=h.create('b',kind='task')
        def revoke_relation(stage):
            if stage=='after_relation_payload':h.config['principals']['owner']['scopes'][SCOPE].remove('relations.assertRelation');h.save()
        h.hook=revoke_relation;h.reopen()
        self.error('UNAUTHORIZED',lambda:h.relations.assertRelation(Mutation(SCOPE,'revoked'),'requires/1',(('dependent',a),('prerequisite',b)),True))
        self.assertEqual(h.relations.outgoing(a,8)['refs'],[]);self.assertEqual(h.atoms.head(SCOPE)['sequence'],3)
    def test_capacity_refusal_retains_complete_prefix(self):
        for provider in ('sqlite','atomic-file-fixture'):
            h=self.harness(provider)
            # Exercise the advertised 256-record bound, not a patched test limit.
            for i in range(c.MAX_RECORDS):h.create('r'+str(i),kind='task')
            h.drain(8);head=h.atoms.head(SCOPE);h.create('overflow',kind='task')
            self.error('OVERLOADED',lambda:h.search.catchUp(SCOPE,8))
            page=h.search.query(h.query(head,limit=8,kind='task'));count=len(page['refs'])
            while page['cursor']:
                page=h.search.query(replace(h.query(head,limit=8,kind='task'),cursor=page['cursor']));count+=len(page['refs'])
            self.assertEqual(count,256);self.assertEqual(page['at'],head)
            self.error('NOT_AVAILABLE',lambda:h.search.query(h.query(kind='task')))
    def test_consumer_rejects_forged_search_relation_and_payload(self):
        for mode in ('wrong-source','duplicate','empty-truncated','wrong-profile','nonmatching-root','relation-digest','payload-digest'):
            h=self.harness();oracle=h.seed();h.drain();q=h.query(oracle['head'],kind='task',topic='retrieval-demo');m=h.modules
            class BadSearch:
                def query(self,request):
                    value=h.search.query(request)
                    if mode=='wrong-source':value['at']['source']='00000000-0000-0000-0000-000000000000'
                    if mode=='duplicate':value['refs'][1]=value['refs'][0]
                    if mode=='empty-truncated':value['refs']=[]
                    if mode=='wrong-profile':value['extraction']='other/1'
                    if mode=='nonmatching-root':value['refs'][0]=oracle['refs']['wrong-kind']
                    return value
            class BadRelations:
                def outgoing(self,*args):return h.relations.outgoing(*args)
                def incoming(self,*args):return h.relations.incoming(*args)
                def getRelation(self,ref):
                    value=h.relations.getRelation(ref)
                    if mode=='relation-digest':value['body']['roles'].reverse()
                    return value
            class BadAtoms:
                def get(self,ref):return h.atoms.get(ref)
                def getMany(self,refs):
                    values=h.atoms.getMany(refs)
                    if mode=='payload-digest':values=(replace(values[0],bytes=b'wrong'),)+values[1:]
                    return values
            consumer=LookupConsumer(m.root/'bad.sqlite',PortOnly(BadAtoms(),('get','getMany')),PortOnly(BadRelations(),('outgoing','incoming','getRelation')),PortOnly(BadSearch(),('query',)),m.access,m.selections)
            with self.assertRaises(ContractError):consumer.lookup(Mutation(SCOPE,'bad'),q)
    def test_lookup_has_no_cognitive_runtime_dependency_or_mutation(self):
        from tests.m3_support import CognitionHarness
        old=CognitionHarness();self.addCleanup(old.close)
        entry,roles,episode=old.generated();old.stimulate(entry)
        def snapshot():return {str(p.relative_to(old.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in old.root.rglob('*') if p.is_file()}
        before=snapshot();original_import=builtins.__import__
        def restricted(name,*args,**kwargs):
            if name.startswith(('hive','reachability','fusion.cognition','fusion.private','fusion.adapters.pln','fusion.adapters.f1r3')):raise AssertionError('lookup attempted cognitive/chain runtime import')
            return original_import(name,*args,**kwargs)
        with patch('builtins.__import__',restricted):
            h=self.harness();oracle=h.seed();h.drain();h.consumer().lookup(Mutation(SCOPE,'isolated'),h.query(oracle['head'],kind='task',topic='retrieval-demo'))
        self.assertEqual(snapshot(),before)
    def test_each_advertised_operation_checks_live_authority(self):
        for provider in ('sqlite','atomic-file-fixture'):
            h=self.harness(provider);a=h.create('a',kind='task');b=h.create('b',kind='task')
            edge=h.relations.assertRelation(Mutation(SCOPE,'relation'),'requires/1',(('dependent',a),('prerequisite',b)),True)
            h.drain();head=h.atoms.head(SCOPE);q=h.query(head,kind='task')
            calls={'atom.storage.create':lambda:h.create('a',kind='task'),'atom.storage.get':lambda:h.atoms.get(a),
                'atom.storage.getMany':lambda:h.atoms.getMany((a,b)), 'atom.storage.availability':lambda:h.atoms.availability(a),
                'atom.storage.head':lambda:h.atoms.head(SCOPE),'atom.storage.readCommits':lambda:h.atoms.readCommits(SCOPE,0,head,2),
                'relations.assertRelation':lambda:h.relations.assertRelation(Mutation(SCOPE,'relation'),'requires/1',(('dependent',a),('prerequisite',b)),True),
                'relations.getRelation':lambda:h.relations.getRelation(edge['ref']),'relations.outgoing':lambda:h.relations.outgoing(a,2),
                'relations.incoming':lambda:h.relations.incoming(b,2),'search.query':lambda:h.search.query(q),
                'search.catchUp':lambda:h.search.catchUp(SCOPE,2),'search.beginRebuild':lambda:h.search.beginRebuild(Mutation(SCOPE,'no-permission'))}
            original=list(h.config['principals']['owner']['scopes'][SCOPE])
            for method,call in calls.items():
                with self.subTest(provider=provider,method=method):
                    h.config['principals']['owner']['scopes'][SCOPE]=[x for x in original if x!=method];h.save();self.error('UNAUTHORIZED',call)
            h.config['principals']['owner']['scopes'][SCOPE]=original;h.save()
            receipt=h.search.beginRebuild(Mutation(SCOPE,'replay-rebuild'))
            self.assertEqual(h.search.beginRebuild(Mutation(SCOPE,'replay-rebuild')),receipt)
            self.error('CONFLICT',lambda:h.search.beginRebuild(Mutation(SCOPE,'concurrent-rebuild')))
            h.reopen();h.drain();self.assertEqual(h.search.beginRebuild(Mutation(SCOPE,'replay-rebuild')),receipt)
    def test_atom_response_budget_is_checked_at_session_boundary(self):
        from fusion.lookup_composition import AtomSession
        from fusion.ports import AtomEnvelope
        h=self.harness();data=b'x'*(c.MAX_BYTES+1)
        ref={'scope_ref':SCOPE,'id':'forged','revision':1,'digest':digest(data)}
        class Oversized:
            def get(self,r):return AtomEnvelope(r,'text/plain',data)
            def getMany(self,rs):return tuple(self.get(r) for r in rs)
        session=AtomSession(PortOnly(Oversized(),('get','getMany')),h.modules.access['atom.storage'])
        self.error('NOT_AVAILABLE',lambda:session.get(ref))
        self.error('NOT_AVAILABLE',lambda:session.getMany((ref,)))

    def test_search_fixture_evaluates_predicates_independently(self):
        h=self.harness('atomic-file-fixture')
        expected=h.create('match',kind='task',topic='exact')
        h.create('wrong-kind',kind='note',topic='exact');h.create('missing',kind='task');h.drain()
        with patch('fusion.lookup_contracts.matches',side_effect=AssertionError('shared query evaluator')):
            self.assertEqual(h.search.query(h.query(kind='task',topic='exact'))['refs'],[expected])
            self.assertEqual(h.search.query(h.query(kind='absent'))['refs'],[])
