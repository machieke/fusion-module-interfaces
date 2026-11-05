"""Real C1/Relations/archive owners; fixture payload backend and port transport.

These checks do not execute native tools, Kubernetes, E5 or a model runtime.
"""
import copy,json,tempfile,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fusion.contracts import canonical,digest,ContractError
from fusion.ports import Mutation
from fusion.preview_history import SessionHistoryOwner,PROFILE
from integration.single_node.sustained_current import explore
from integration.single_node.pilot_browser_handover import observe as authority,selection
from fusion.pilot_writer_fence import PROFILE as HANDOVER


class Explorer(unittest.TestCase):
    def test_real_archived_history_hydration_pagination_and_wrong_session_refusal(self):
        from tests import test_integrated_archive as fixture
        f=fixture.Archive();f.setUp();self.addCleanup(f.doCleanups);atoms=f.owner();scope=fixture.SCOPE;sid=str(uuid.uuid4())
        original_put=atoms.storage.put
        def put(*args):
            payload,_=original_put(*args)
            return payload,dict(provider='fixture-files/1',durability='local-files-process-restart',evidence={'classification':'explicit-payload-fixture'})
        atoms.storage.put=put
        access=SimpleNamespace(authorize=lambda *_:'A',selection=lambda:'e'*64)
        history=SessionHistoryOwner(f.root/'history.sqlite',atoms,access)
        episode=history.recordEpisode(Mutation(scope,'episode'),'synthetic-session')['ref']
        for n in range(6):
            body=canonical(dict(profile=PROFILE,session=sid,body={'text':'<script>inert '+str(n)}))
            ref=atoms.create(Mutation(scope,'body-'+str(n)),'application/omega-session-data-v1',body)['ref']
            history.appendHistory(Mutation(scope,'event-'+str(n)),episode,n,'occurrence-'+str(n),'tool-result',ref,[],'2026-11-04T00:00:00Z')
        head=atoms.head(scope);offset=0
        while offset<head['sequence']:
            count=min(f.archive['records'],head['sequence']-offset)
            atoms.publishArchive(Mutation(scope,'archive-'+str(offset)),offset,head,count);offset+=count
        cfg=f.root/'atoms.json';cfg.write_text('{}');app=dict(history_atoms_config=str(cfg),facet_configs={'episodic.memory':'fixture-port'})
        current=dict(scope=scope,session=sid,history=history.historySnapshot(episode))
        port=SimpleNamespace(call=lambda op,*args:getattr(history,op)(*args))
        with patch('integration.single_node.sustained_current.Facet',return_value=port),patch('integration.single_node.sustained_current.atoms',return_value=atoms),patch.object(atoms.storage,'get',side_effect=AssertionError('no hot fallback')):
            first=explore(app,current,dict(operation='history',body=dict(snapshot=None,start=1)))
            self.assertEqual(len(first['value']['events']),4);self.assertFalse(first['value']['complete'])
            second=explore(app,current,dict(operation='history',body=dict(snapshot=first['value']['snapshot'],start=5)))
            self.assertEqual(len(second['value']['events']),2);self.assertTrue(second['value']['complete'])
            self.assertEqual(first['value']['events'][0]['body'],{'text':'<script>inert 0'})
            self.assertEqual(first['value']['archive_used'],'NOT_INFERRED_FROM_SUCCESS')
            foreign=copy.deepcopy(first['value']['snapshot']);foreign['episode']['id']=str(uuid.uuid4())
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):explore(app,current,dict(operation='history',body=dict(snapshot=foreign,start=1)))
            wrong=dict(current,session=str(uuid.uuid4()))
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):explore(app,wrong,dict(operation='history',body=dict(snapshot=None,start=1)))

    def test_real_relation_pages_retained_cursor_and_current_withdrawal_gate(self):
        from tests import test_phase2_history_relations as fixture
        f=fixture.OwnerFixture();f.setUp();self.addCleanup(f.doCleanups);owner=f.relations();target=f.payload('target');logical=str(uuid.uuid4())
        for n in range(5):owner.assertRelation(Mutation(fixture.SCOPE,'edge-'+str(n)),'requires/1',(('dependent',target),('prerequisite',f.payload('other-'+str(n)))),True)
        port=SimpleNamespace(call=lambda op,*args:owner.traverse(op,*args) if op in ('outgoing','incoming') else getattr(owner,op)(*args))
        lifecycle=SimpleNamespace(call=lambda *_:{'authorized':True})
        memory=dict(logical_id=logical,uuid=str(uuid.uuid4()),payload=target,enrollment=target)
        current=dict(scope=fixture.SCOPE,session=str(uuid.uuid4()),lifecycle=dict(head={'fixture':'head'},membership={'active':[memory]}))
        app=dict(active_memory_configs={'memory.lifecycle':'fixture-lifecycle'},facet_configs={'relations':'fixture-port'})
        body=dict(logical_id=logical,direction='outgoing',cursor=None,snapshot=None)
        with patch('integration.single_node.sustained_current.Facet',return_value=port),patch('integration.single_node.sustained_current.Memory',return_value=lifecycle):
            first=explore(app,current,dict(operation='relations',body=body));page=first['value']['page']
            self.assertEqual(len(first['value']['records']),4);self.assertIsNotNone(page['cursor'])
            body.update(cursor=page['cursor'],snapshot=page['at']);last=explore(app,current,dict(operation='relations',body=body))
            self.assertEqual(len(last['value']['records']),1)
            removed=dict(current,lifecycle={'head':{},'membership':{'active':[]}})
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):explore(app,removed,dict(operation='relations',body=body))
            f.revoke('relations.outgoing')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):explore(app,current,dict(operation='relations',body=body))

    def test_handover_exact_authority_sanitized_rotated_and_outside_mount_refused(self):
        namespace='omega-ref-pilot-source';replacement='omega-ref-pilot-target'
        selected=selection(dict(profile=HANDOVER,authority_file='/writer-authority/current.json',deployments=[namespace,replacement]),namespace)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);mount=root/'authority';mount.mkdir();version=mount/'version';version.mkdir()
            value=dict(profile=HANDOVER,synthetic_only=True,deployment=namespace,incarnation='initial',generation=1,state='drained',allowed_methods=[],history=[],
                handover=dict(intent=dict(original=namespace,replacement=replacement,checkpoint_sha256='a'*64,closure_sha256='b'*64),retired={'secret_canary':'PRIVATE_NOT_FOR_BROWSER'}))
            (version/'current.json').write_bytes(canonical(value));(mount/'current.json').symlink_to(version/'current.json')
            body=dict(operation='observe',expected_sha256=None);read=authority(selected,body,root=mount)
            self.assertEqual(read['checkpoint']['checkpoint_sha256'],'a'*64);self.assertNotIn('PRIVATE_NOT_FOR_BROWSER',json.dumps(read));self.assertFalse(read['mutations_permitted'])
            exact=dict(body,expected_sha256=read['authority_sha256']);self.assertEqual(authority(selected,exact,root=mount),read)
            value['state']='retired';(version/'current.json').write_bytes(canonical(value))
            with self.assertRaisesRegex(ContractError,'CONFLICT'):authority(selected,exact,root=mount)
            with self.assertRaisesRegex(ContractError,'UNSUPPORTED_OPERATION'):authority(selected,dict(body,retired=True),root=mount)
            (root/'foreign').write_bytes(canonical(value));(mount/'current.json').unlink();(mount/'current.json').symlink_to(root/'foreign')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):authority(selected,body,root=mount)

    def test_http_handover_never_borrows_operator_role_or_accepts_mutation(self):
        from tests import test_pilot_browser as fixture
        f=fixture.BrowserTests();f.setUp();self.addCleanup(f.doCleanups)
        f.browser_cfg['namespace']='omega-ref-pilot-browser-test'
        f.browser_cfg['handover']=dict(profile=HANDOVER,authority_file='/writer-authority/current.json',deployments=[f.browser_cfg['namespace']])
        f.browser_path.write_bytes(canonical(f.browser_cfg));f.login('alice')
        body=dict(operation='observe',expected_sha256=None)
        with patch('integration.single_node.pilot_browser_handover.observe',return_value={'fixture':'sanitized-authority'}) as read:
            self.assertEqual(f.request('/api/handover',body)[0],400);self.assertEqual(read.call_count,0)
            f.login('operator');self.assertEqual(f.request('/api/handover',body)[0],200);self.assertEqual(read.call_count,1)
            self.assertEqual(f.request('/api/handover',body,csrf=False)[0],400);self.assertEqual(read.call_count,1)
