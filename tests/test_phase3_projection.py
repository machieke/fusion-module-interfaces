"""Real private application/feed journals, explicit file payload provider fixture."""
import json,sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion.atom_feed import FeedAtomOwner
from fusion.contracts import canonical,ContractError,require
from fusion.ports import Mutation
from fusion.preview_session_service import SessionPorts
from fusion.sustained_sessions import PROFILE as SESSIONS
from integration.single_node.sustained_projection import PROFILE,invoke
from tests.test_phase3_private import PrivateWiring
from tests.test_phase3_feed import FilePayloadFixture


class ExactProjection(PrivateWiring):
    def setup_projection(self):
        _,cfg,state,run=self.build();owner=run/'owner.json';token=cfg['principals']['operator']['credential']
        sid=SessionPorts(owner).invoke(token,dict(id='a',profile=SESSIONS,operation='allocate',body=dict(identity='private',template='private')))['value']['session']
        scopes=['synthetic-private-a',self.scope];stores={}
        for index,scope in enumerate(scopes):
            def auth(s,op,expected=scope):require(s==expected,'UNAUTHORIZED');return 'A'
            stores[scope]=FeedAtomOwner(self.root/('feed'+str(index)+'.sqlite'),FilePayloadFixture(self.root/('payload'+str(index))),
                SimpleNamespace(authorize=auth),capacity=dict(profile='bounded-feed-capacity/1',records=16,bytes=1048576,scopes=[scope]))
        content='The synthetic PRIVATE-CANARY conclusion is location cedar'
        source=canonical(dict(scope=scopes[0],corpus='private',uuid='PRIVATE-IDENTITY',time='private-creation',content=content))
        from fusion.vector_contracts import PAYLOAD
        ref=stores[scopes[0]].create(Mutation(scopes[0],'private-memory'),PAYLOAD,source)['ref']
        q=dict(profile=PROFILE,identity='operator-projection-one',session=sid,source=ref,content='location cedar',
            approval_record='synthetic-exact-output-consent',recipient_scope=self.scope)
        return owner,state,run,token,q,stores

    def test_public_artifact_excludes_private_ids_hashes_and_provenance(self):
        owner,state,run,token,q,stores=self.setup_projection()
        with patch('integration.single_node.sustained_projection.client',side_effect=lambda cfg,*args:stores[cfg['scope']]):
            value=invoke(owner,state,run,token,q);again=invoke(owner,state,run,token,q)
        self.assertEqual(value,again)
        raw=stores[self.scope].get(value['shared']).bytes
        for forbidden in ('PRIVATE-CANARY','The synthetic', 'PRIVATE-IDENTITY',q['source']['id'],q['source']['digest'],q['session'],'private-creation'):
            self.assertNotIn(forbidden.encode(),raw)
        self.assertEqual(stores[self.scope].head(self.scope)['sequence'],1)
        self.assertFalse(value['empirical_evidence'])
    def test_lost_public_reply_recovers_by_observation_with_original_deadline(self):
        owner,state,run,token,q,stores=self.setup_projection();public=stores[self.scope]
        original=public.create
        def lose(*args):original(*args);raise ConnectionError('fixture response loss after real feed commit')
        public.create=lose
        with patch('integration.single_node.sustained_projection.client',side_effect=lambda cfg,*args:stores[cfg['scope']]):
            with self.assertRaises(ConnectionError):invoke(owner,state,run,token,q)
            with sqlite3.connect(state/'private-projections.sqlite') as db:before=db.execute('SELECT deadline,calls FROM projections').fetchone()
            # This failure sentinel proves recovery does not issue a second create.
            public.create=lambda *args:self.fail('capture recovery reissued create')
            value=invoke(owner,state,run,token,q)
            with sqlite3.connect(state/'private-projections.sqlite') as db:after=db.execute('SELECT deadline,calls FROM projections').fetchone()
        self.assertEqual(before[0],after[0]);self.assertGreater(after[1],before[1]);self.assertEqual(public.head(self.scope)['sequence'],1)
    def test_wrong_output_and_worker_cannot_declassify(self):
        owner,state,run,token,q,stores=self.setup_projection()
        with patch('integration.single_node.sustained_projection.client',side_effect=lambda cfg,*args:stores[cfg['scope']]):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):invoke(owner,state,run,token,dict(q,content='Unapproved substitute'))
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):invoke(owner,state,run,token,dict(q,identity='full-source-denied',content='The synthetic PRIVATE-CANARY conclusion is location cedar'))
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                invoke(owner,state,run,json.loads(owner.read_bytes())['principals']['worker']['credential'],q)
        self.assertEqual(stores[self.scope].head(self.scope)['sequence'],0)

    def test_real_sigkill_source_and_publication_capture_recover_without_duplicate_artifact(self):
        import multiprocessing,signal,os
        owner,state,run,token,q,stores=self.setup_projection()
        for number,stage in enumerate(('after_private_projection_source_capture','after_private_projection_publication_capture')):
            request=dict(q,identity='kill-'+str(number))
            reader,writer=multiprocessing.get_context('fork').Pipe(False)
            def work():
                reader.close()
                def pause(observed):
                    if observed==stage:writer.send(stage);signal.pause()
                with patch('integration.single_node.sustained_projection.client',side_effect=lambda cfg,*args:stores[cfg['scope']]):
                    invoke(owner,state,run,token,request,pause)
            process=multiprocessing.get_context('fork').Process(target=work);process.start();writer.close()
            try:
                self.assertTrue(reader.poll(10));self.assertEqual(reader.recv(),stage)
                os.kill(process.pid,signal.SIGKILL);process.join(5);self.assertEqual(process.exitcode,-signal.SIGKILL)
                with sqlite3.connect(state/'private-projections.sqlite') as db:before=db.execute('SELECT deadline,calls FROM projections WHERE identity=?',(request['identity'],)).fetchone()
                with patch('integration.single_node.sustained_projection.client',side_effect=lambda cfg,*args:stores[cfg['scope']]):
                    result=invoke(owner,state,run,token,request)
                with sqlite3.connect(state/'private-projections.sqlite') as db:after=db.execute('SELECT deadline,calls FROM projections WHERE identity=?',(request['identity'],)).fetchone()
                self.assertEqual(before[0],after[0]);self.assertGreater(after[1],before[1]);self.assertEqual(stores[self.scope].head(self.scope)['sequence'],number+1)
                self.assertFalse(result['private_source_disclosed'])
            finally:
                if process.is_alive():process.kill();process.join()
                reader.close();process.close()
