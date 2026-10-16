"""M5 fixture contract/owner/substitution tests; no Hive, PLN, chain or DA required."""
from dataclasses import replace
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch
from fusion import lookup_contracts as c
from fusion.contracts import ContractError,canonical,digest
from fusion.ports import Mutation
from fusion.lookup_composition import descriptors,open_lookup,OPERATIONS
from fusion.registry import descriptor_wire
from tests.m5_support import LookupHarness,SCOPE,PortOnly

class LookupContracts(unittest.TestCase):
    def harness(self,search='sqlite'):
        h=LookupHarness(search=search);self.addCleanup(h.close);return h
    def error(self,code,call):
        with self.assertRaises(ContractError) as cm:call()
        self.assertEqual(cm.exception.code,code)
    def test_all_relation_roles_directions_identity_and_replay(self):
        h=self.harness();a,b,d=[h.create(k,kind='node',label=k) for k in 'abd']
        r=h.relations.assertRelation(Mutation(SCOPE,'binary'),'requires/1',(('dependent',a),('prerequisite',b)),True)
        self.assertEqual(h.relations.getRelation(r['ref']),r)
        self.assertEqual(h.relations.assertRelation(Mutation(SCOPE,'alias'),'requires/1',(('dependent',a),('prerequisite',b)),True),r)
        self.assertEqual(h.relations.outgoing(a,1)['refs'],[r['ref']]);self.assertEqual(h.relations.incoming(b,1)['refs'],[r['ref']])
        self.assertEqual(h.relations.outgoing(b,1)['refs'],[]);self.assertEqual(h.relations.incoming(a,1)['refs'],[])
        self.error('CONFLICT',lambda:h.relations.assertRelation(Mutation(SCOPE,'binary'),'requires/1',(('dependent',b),('prerequisite',a)),True))
        hyper=h.relations.assertRelation(Mutation(SCOPE,'three'),'transfer/1',(('sender',a),('object',b),('recipient',d)),True)
        self.assertEqual([x[0] for x in hyper['body']['roles']],['sender','object','recipient'])
        self.assertIn(hyper['ref'],h.relations.incoming(b,8)['refs']);self.assertEqual(h.relations.outgoing(d,8)['refs'],[])
        association=h.relations.assertRelation(Mutation(SCOPE,'assoc'),'association/1',(('first',b),('second',d)),False)
        for endpoint in (b,d):
            for operation in (h.relations.incoming,h.relations.outgoing):self.assertIn(association['ref'],operation(endpoint,8)['refs'])
        selflink=h.relations.assertRelation(Mutation(SCOPE,'self'),'association/1',(('first',a),('second',a)),False)
        self.assertEqual(h.relations.outgoing(a,8)['refs'].count(selflink['ref']),1)
        h.reopen();self.assertEqual(h.relations.getRelation(r['ref']),r)
    def test_relation_boundary_validation_unaccepted_payload_and_revocation(self):
        h=self.harness();a,b=[h.create(k,kind='node') for k in 'ab'];roles=(('dependent',a),('prerequisite',b))
        for schema,rs,direction,code in [('unknown/1',roles,True,'UNSUPPORTED_PROFILE'),('requires/1',roles,False,'INVALID_ARGUMENT'),
            ('requires/1',roles[:1],True,'INVALID_ARGUMENT'),('requires/1',(('dependent',a),('dependent',b)),True,'INVALID_ARGUMENT')]:
            self.error(code,lambda:h.relations.assertRelation(Mutation(SCOPE,'bad'),schema,rs,direction))
        for change,code in [({'scope_ref':'other-lookup'},'UNAUTHORIZED'),({'revision':2},'INVALID_ARGUMENT'),({'digest':'a'*64},'CONFLICT'),({'id':'absent'},'NOT_FOUND')]:
            wrong={**b,**change}
            self.error(code,lambda:h.relations.assertRelation(Mutation(SCOPE,'bad-'+code), 'requires/1',(('dependent',a),('prerequisite',wrong)),True))
        body=c.relation_body(SCOPE,'requires/1',roles,True,c.SCHEMAS)
        orphan=h.atoms.create(Mutation(SCOPE,'orphan'),c.RELATION,canonical(body))['ref']
        self.error('NOT_FOUND',lambda:h.relations.getRelation(orphan));self.assertEqual(h.relations.outgoing(a,8)['refs'],[])
        r=h.relations.assertRelation(Mutation(SCOPE,'good'),'requires/1',roles,True)
        h.config['principals']['owner']['scopes'][SCOPE]=[];h.save()
        for call in [lambda:h.relations.assertRelation(Mutation(SCOPE,'good'),'requires/1',roles,True),lambda:h.relations.getRelation(r['ref']),
                     lambda:h.relations.outgoing(a,1),lambda:h.relations.incoming(b,1)]:self.error('UNAUTHORIZED',call)
    def test_relation_pagination_fixed_head_cursor_binding(self):
        h=self.harness();a=h.create('root',kind='node');bs=[h.create('b'+str(i),kind='node') for i in range(5)]
        for i,b in enumerate(bs):h.relations.assertRelation(Mutation(SCOPE,'r'+str(i)),'requires/1',(('dependent',a),('prerequisite',b)),True)
        first=h.relations.outgoing(a,2);h.relations.assertRelation(Mutation(SCOPE,'late'),'requires/1',(('dependent',a),('prerequisite',a)),True)
        second=h.relations.outgoing(a,2,first['cursor']);last=h.relations.outgoing(a,2,second['cursor'])
        refs=first['refs']+second['refs']+last['refs'];self.assertEqual(len(refs),5);self.assertEqual(len({r['id'] for r in refs}),5)
        self.assertTrue(last['page_complete']);self.assertEqual(first['at'],last['at'])
        for call in [lambda:h.relations.incoming(a,2,first['cursor']),lambda:h.relations.outgoing(bs[0],2,first['cursor']),lambda:h.relations.outgoing(a,3,first['cursor'])]:self.error('CONFLICT',call)
        self.error('INVALID_ARGUMENT',lambda:h.relations.outgoing(a,2,'broken'))
        self.error('INVALID_ARGUMENT',lambda:h.relations.outgoing(a,2,''))
        self.error('INVALID_ARGUMENT',lambda:h.relations.outgoing(a,2,snapshot={}))
    def test_exact_query_lag_rebuild_and_independent_search_substitution(self):
        h=self.harness();oracle=h.seed();query=h.query(oracle['head'],kind='task',topic='retrieval-demo')
        self.error('NOT_AVAILABLE',lambda:h.search.query(query));h.drain();consumer=h.consumer();before=consumer.lookup(Mutation(SCOPE,'lookup'),query)
        self.assertEqual(before['roots'],oracle['order']);self.assertEqual(len(before['documents']),8);self.assertEqual(len(before['relations']),15)
        self.assertTrue(all(before['calls'][k]>0 for k in ['query','outgoing','incoming','getRelation','get','getMany']))
        self.assertEqual(h.search.query(h.query(kind='absent'))['refs'],[])
        first=h.search.query(query);added=h.create('late',kind='task',topic='retrieval-demo');new=h.query(kind='task',topic='retrieval-demo')
        self.error('NOT_AVAILABLE',lambda:h.search.query(new));self.assertEqual(h.search.query(query)['at'],oracle['head'])
        h.drain();old_page=h.search.query(replace(query,cursor=first['cursor']));self.assertEqual(old_page['at'],first['at'])
        h.search.beginRebuild(Mutation(SCOPE,'rebuild'));self.error('NOT_AVAILABLE',lambda:h.search.query(new));h.search.catchUp(SCOPE,2);h.reopen();h.drain()
        self.error('CONFLICT',lambda:h.search.query(replace(query,cursor=first['cursor'])))
        rebuilt=h.consumer('rebuilt').lookup(Mutation(SCOPE,'lookup'),new);self.assertEqual(rebuilt['roots'],oracle['order']+[added])
        h.config['lookup_descriptors']=[descriptor_wire(d) for d in descriptors('fixture-files','atomic-file-fixture')];h.save();h.reopen();h.drain()
        swapped=h.consumer('swapped').lookup(Mutation(SCOPE,'lookup'),new)
        for field in ['roots','relations','documents','search_at','relations_at']:self.assertEqual(swapped[field],rebuilt[field])
    def test_feed_snapshot_replay_and_source_binding(self):
        h=self.harness();a=h.create('a',kind='task');head=h.atoms.head(SCOPE);self.assertEqual(head['sequence'],1)
        self.assertEqual(h.create('a',kind='task'),a);self.assertEqual(h.atoms.head(SCOPE),head)
        h.create('b',kind='task');page=h.atoms.readCommits(SCOPE,0,head,1)
        self.assertEqual(page['records'][0]['ref'],a);self.assertTrue(page['complete']);h.reopen();self.assertEqual(h.atoms.readCommits(SCOPE,0,head,1),page)
        wrong={**head,'source':'00000000-0000-0000-0000-000000000000'}
        self.error('CONFLICT',lambda:h.atoms.readCommits(SCOPE,0,wrong,1));self.error('CONFLICT',lambda:h.search.query(h.query(wrong,kind='task')))
        self.error('CONFLICT',lambda:h.create('a',kind='different'))
    def test_query_exact_unicode_missing_field_and_bounded_parser(self):
        for provider in ['sqlite','atomic-file-fixture']:
            h=self.harness(provider);a=h.create('a',kind='task',topic='Café');h.create('b',kind='Task',topic='Cafe\u0301');h.create('c',kind='task');h.drain()
            self.assertEqual(h.search.query(h.query(kind='task',topic='Café'))['refs'],[a])
            self.assertEqual(h.search.query(h.query(topic='café'))['refs'],[])
            for expression in [{'any':[]},{'all':[]},{'all':[{'field':'secret','eq':'x'}]},{'all':[{'field':'kind','eq':1}]},
                               {'all':[{'field':'kind','eq':'x'},{'field':'kind','eq':'x'}]},{'all':[{'field':'kind','regex':'.*'}]}]:
                self.error('INVALID_ARGUMENT',lambda:h.search.query(replace(h.query(kind='task'),expression=expression)))
            self.error('UNSUPPORTED_PROFILE',lambda:h.search.query(replace(h.query(kind='task'),profile='embedding/1')))
            self.error('INVALID_ARGUMENT',lambda:h.search.query(h.query(limit=9,kind='task')))
    def test_malformed_enrolled_record_and_revocation_do_not_advance_checkpoint(self):
        for provider in ['sqlite','atomic-file-fixture']:
            h=self.harness(provider);h.create('a',kind='task');h.search.catchUp(SCOPE,1);old=h.atoms.head(SCOPE)
            h.atoms.create(Mutation(SCOPE,'bad'),c.KNOWLEDGE,b'{bad')
            with self.assertRaises(c.ProjectionError) as cm:h.search.catchUp(SCOPE,2)
            self.assertEqual(cm.exception.sequence,2);self.assertEqual(cm.exception.reason,'enrolled-record')
            self.assertEqual(h.search.query(h.query(old,kind='task'))['at'],old)
            self.error('NOT_AVAILABLE',lambda:h.search.query(h.query(kind='task')))
            h.config['principals']['owner']['scopes'][SCOPE].remove('search.query');h.save()
            self.error('UNAUTHORIZED',lambda:h.search.query(h.query(old,kind='task')))
    def test_source_duplicate_gap_changed_metadata_and_checkpoint_anchor(self):
        for provider in ['sqlite','atomic-file-fixture']:
            for mode in ['gap','duplicate','reorder','metadata','replay','rebuild-rollback']:
                h=self.harness(provider);[h.create('r'+str(i),kind='task') for i in range(3)]
                h.search.catchUp(SCOPE,1);base=h.atoms.head(SCOPE)
                # Construct the selected projection with a malicious public source port.
                underlying=h.atoms
                class Bad:
                    def head(self,scope):
                        value=underlying.head(scope)
                        return {**value,'sequence':0} if mode=='rebuild-rollback' else value
                    def readCommits(self,scope,after,through,limit):
                        result=underlying.readCommits(scope,after,through,limit)
                        if mode=='replay' and after==0:result['records'][0]['size']+=1
                        if after==1:
                            if mode=='gap':result['records'][0]['sequence']+=1
                            if mode=='reorder':result['records'].reverse()
                            if mode=='duplicate':result['records'][1]['ref']=result['records'][0]['ref']
                            if mode=='metadata':result['records'][0]['content_type']='text/plain'
                        return result
                if provider=='sqlite':
                    from fusion.search import SearchOwner
                    p=h.modules.root/('search-'+digest(SCOPE.encode())+'.sqlite');search=SearchOwner(p,h.atoms,PortOnly(Bad(),('head','readCommits')),h.modules.access['search'],SCOPE)
                else:
                    from fusion.adapters.fixture_search import FileSearchFixture
                    p=h.modules.root/('search-'+digest(SCOPE.encode())+'.json');search=FileSearchFixture(p,h.atoms,PortOnly(Bad(),('head','readCommits')),h.modules.access['search'],SCOPE)
                with self.assertRaises(ContractError):
                    if mode=='rebuild-rollback':search.beginRebuild(Mutation(SCOPE,'rollback'))
                    else:search.catchUp(SCOPE,2)
                self.assertEqual(search.query(h.query({**base,'sequence':1},kind='task'))['at']['sequence'],1)
