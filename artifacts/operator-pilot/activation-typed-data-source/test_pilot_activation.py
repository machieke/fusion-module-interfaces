"""Real application inbox/capture boundary; native/model/cluster not claimed."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fusion.contracts import canonical,digest,ContractError
from fusion.sustained_sessions import SustainedSessionStore
from integration.single_node.pilot_activation import install,request_guard,selected
from fusion.pilot_writer_fence import PROFILE
from tests.test_phase3_sessions import policy


class Activation(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.cfg=policy();self.path=self.root/'session-inbox.sqlite';self.clock=lambda:1000
        db=SustainedSessionStore(self.path,lambda *_:None,self.cfg,clock=self.clock)
        self.old=db.allocate('A','old-allocate','shared')['session']
        db.submit('A',self.old,'old-input','pin first First capture','synthetic-task');db.next_input('A',self.old)
        db.complete('A',self.old,'old-input',dict(turn=1,projection='exact-native-projection-fixture',occurrences=['old-occurrence']))
        db.control('A',self.old,'drain-old','close');self.before=db.observe('A',self.old,True)
        self.rows={name:db.db.execute('SELECT * FROM '+name).fetchall() for name in ('preview_sessions','preview_inputs','sustained_allocations','sustained_dispatch','sustained_outcomes','sustained_actions')}
        self.rows={k:[tuple(x) for x in v] for k,v in self.rows.items()};db.close()
        (self.root/'owner-seal.json').write_bytes(canonical(dict(role='omega-agent',scope='synthetic-activation',composition='omega-single-node-sustained-preview/1')))
        (self.root/'restore-fence.json').write_bytes(canonical(dict(mode='READ_ONLY_RECONCILIATION',role='omega-agent',external_effect_authority=False)))
        self.receipt=install(self.root,'omega-agent','a'*64,2)
        self.newcfg=copy.deepcopy(self.cfg);self.newcfg['templates']={'g2-shared':dict(self.cfg['templates']['shared'],runtime_digest='d'*64)}
        self.authority=self.root/'current.json'
        self.authority.write_bytes(canonical(dict(profile=PROFILE,synthetic_only=True,state='active',deployment='replacement',incarnation='new',generation=2,allowed_methods=['writer.start'])))
        # Pure selection unit uses a trusted local file; deployed configuration
        # separately requires /writer-authority/current.json.
        self.settings=dict(role='omega-agent',preview=dict(agents={'omega-agent':dict(tools=['remember','query','episodes'])},pilot=dict(
            handover=dict(profile=PROFILE,checkpoint_sha256='a'*64,generation=2),
            writer_fence=dict(profile=PROFILE,authority_file=str(self.authority),deployment='replacement',incarnation='new',generation=2))))

    def test_old_capture_exact_old_mutations_denied_new_occurrence_accepted(self):
        db=SustainedSessionStore(self.path,lambda *_:None,self.newcfg,clock=self.clock);self.addCleanup(db.close)
        self.assertEqual(db.observe('A',self.old,True),self.before)
        for operation in (lambda:db.submit('A',self.old,'new-for-old','pin x X','synthetic-task'),
                          lambda:db.next_input('A',self.old),lambda:db.reconcile('A',self.old),
                          lambda:db.control('A',self.old,'resume-old','resume')):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):operation()
        for name,rows in self.rows.items():self.assertEqual([tuple(x) for x in db.db.execute('SELECT * FROM '+name)],rows)
        fresh=db.allocate('A','new-allocation','g2-shared')['session'];self.assertNotEqual(fresh,self.old)
        db.submit('A',fresh,'new-input','pin new New intentional input','synthetic-task')
        self.assertEqual(db.next_input('A',fresh)['id'],'new-input')
        self.assertEqual(db.allocated('A',self.old)['frozen'],self.cfg['templates']['shared'])
        self.assertEqual(db.capacity('A')['retained'],2)

    def test_marker_replay_and_original_scope_permissions(self):
        self.assertEqual(install(self.root,'omega-agent','a'*64,2),self.receipt)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):install(self.root,'omega-agent','b'*64,2)
        cfg=copy.deepcopy(self.newcfg);cfg['templates']['g2-shared']['scope']='synthetic-other'
        def current(principal,scope,operation):
            if scope!='synthetic-other':raise ContractError('UNAUTHORIZED')
        db=SustainedSessionStore(self.path,current,cfg,clock=self.clock);self.addCleanup(db.close)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):db.observe('A',self.old,True)

    def test_new_shared_selection_keeps_all_old_registry_records_and_private_read_authority(self):
        from unittest.mock import patch
        from integration.single_node.pilot_activation import configure
        from tests.test_integrated_registry import selection
        from fusion.provider_lifecycle import Registry
        owner=SustainedSessionStore(self.path,lambda *_:None,self.cfg,clock=self.clock)
        old=selection(self.cfg['templates']['shared']['scope']);reg=Registry(owner,old,lambda *_:None)
        reg.act('old-storage','add','storage');before=owner.db.execute('SELECT * FROM integrated_providers').fetchall();owner.close()
        allocation=copy.deepcopy(self.cfg);allocation['templates']['private']=dict(allocation['templates']['shared'],scope='synthetic-private')
        selected=copy.deepcopy(old);selected['records']['private-storage']=dict(selected['records']['storage'],scope='synthetic-private');selected['templates']['private']=['private-storage']
        cfg=dict(native_sessions=dict(database=str(self.path),allocation=allocation,runtime_templates={'shared':{'directory':'shared'},'private':{'directory':'private'}},provider_registry=selected))
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):configure(self.settings,cfg,self.root,self.root/'run')
        result=cfg['native_sessions'];self.assertEqual(set(result['allocation']['templates']),{'g2-shared'})
        self.assertEqual(set(result['provider_registry']['records']),{'storage','g2-storage'})
        self.assertEqual(result['provider_registry']['templates'],{'g2-shared':['g2-storage']})
        with sqlite3.connect(self.path) as db:self.assertEqual(db.execute('SELECT * FROM integrated_providers').fetchall(),[tuple(r) for r in before])

    def empty_registry_copy(self,compact=False):
        from tests.test_integrated_registry import selection
        from fusion.provider_retention import PROFILE as compact_profile,LIMITS
        root=self.root/('unused-compact' if compact else 'unused-legacy');root.mkdir();path=root/'session-inbox.sqlite'
        owner=SustainedSessionStore(path,lambda *_:None,self.cfg,clock=self.clock);owner.close()
        for name in ('restore-fence.json','owner-seal.json'):(root/name).write_bytes((self.root/name).read_bytes())
        install(root,'omega-agent','c'*64,2)
        settings=copy.deepcopy(self.settings);settings['preview']['pilot']['handover']['checkpoint_sha256']='c'*64
        choice=selection(self.cfg['templates']['shared']['scope'])
        if compact:choice.update(profile=compact_profile,limits=dict(LIMITS))
        def fresh():return dict(native_sessions=dict(database=str(path),allocation=copy.deepcopy(self.cfg),
            runtime_templates={'shared':{'directory':'shared'}},provider_registry=copy.deepcopy(choice)))
        return root,path,settings,fresh

    def test_unused_registry_startup_and_restart_are_read_only_for_both_profiles(self):
        from unittest.mock import patch
        from integration.single_node.pilot_activation import configure
        for compact in (False,True):
            with self.subTest(compact=compact):
                root,path,settings,fresh=self.empty_registry_copy(compact);before=path.read_bytes();first=fresh()
                with patch('integration.single_node.pilot_activation.check',lambda *_:None):
                    configure(settings,first,root,root/'run');again=fresh();configure(settings,again,root,root/'restart')
                self.assertEqual(first,again);self.assertEqual(path.read_bytes(),before)
                self.assertEqual(set(first['native_sessions']['provider_registry']['records']),{'g2-storage'})
                self.assertEqual(first['native_sessions']['provider_registry']['templates'],{'g2-shared':['g2-storage']})
                with sqlite3.connect(path) as db:self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='integrated_providers'").fetchone())

    def test_missing_registry_schema_refuses_partial_tables_or_historical_sessions(self):
        from unittest.mock import patch
        from integration.single_node.pilot_activation import configure
        for compact in (False,True):
            with self.subTest(compact=compact):
                root,path,settings,fresh=self.empty_registry_copy(compact)
                for name in ('integrated_provider_actions','pilot_registry_meta'):
                    with sqlite3.connect(path) as db:db.execute('CREATE TABLE '+name+'(fixture TEXT)')
                    before=path.read_bytes()
                    with patch('integration.single_node.pilot_activation.check',lambda *_:None):
                        with self.assertRaisesRegex(ContractError,'CONFLICT'):configure(settings,fresh(),root,root/'run')
                    self.assertEqual(path.read_bytes(),before)
                    with sqlite3.connect(path) as db:db.execute('DROP TABLE '+name)
                owner=SustainedSessionStore(path,lambda *_:None,self.cfg,clock=self.clock)
                owner.allocate('A','unfenced-allocation','shared');owner.close();before=path.read_bytes()
                with patch('integration.single_node.pilot_activation.check',lambda *_:None):
                    with self.assertRaisesRegex(ContractError,'CONFLICT'):configure(settings,fresh(),root,root/'run')
                self.assertEqual(path.read_bytes(),before)
        # The imported historical-session marker independently forbids treating
        # a missing Registry as a new empty owner.
        from tests.test_integrated_registry import selection
        cfg=dict(native_sessions=dict(database=str(self.path),allocation=copy.deepcopy(self.cfg),
            runtime_templates={'shared':{}},provider_registry=selection(self.cfg['templates']['shared']['scope'])))
        before=self.path.read_bytes()
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            with self.assertRaisesRegex(ContractError,'CONFLICT'):configure(self.settings,cfg,self.root,self.root/'run')
        self.assertEqual(self.path.read_bytes(),before)

    def test_historical_effect_guard_and_new_caller_identity(self):
        from unittest.mock import patch
        # Path validation is independently covered; this test uses local temp
        # authority rather than mounting a Kubernetes Secret.
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                request_guard(self.settings,self.root,'/preview/session',dict(id='transport',profile='omega-native-sessions/3',operation='submit',body=dict(session=self.old,identity='old-input',text='pin old Old input',assignment='synthetic-task')))
            request_guard(self.settings,self.root,'/preview/session',dict(operation='observe',body=dict(session=self.old,id='old-input')))
            request_guard(self.settings,self.root,'/preview/session',dict(id='transport',profile='omega-native-sessions/3',operation='submit',body=dict(session='new-session',identity='new-operation',text='pin new New input',assignment='synthetic-task')))
            for path,operation in (('/preview/tasks','published'),('/preview/model','query'),('/preview/projection','observe')):
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                    request_guard(self.settings,self.root,path,dict(operation=operation,body=dict(session=self.old,id='old-input')))
            # The same retained payload can be a target of new work. Its ref id
            # cannot be misclassified as an old executable occurrence.
            request_guard(self.settings,self.root,'/reference-cognition',dict(operation='create',interface='atom.storage',body=dict(id='new-effect',
                ref=dict(scope_ref='synthetic-activation',id='old-input',revision=1,digest='b'*64))))

            self.settings['preview']['agents']['omega-agent']['tools'].append('delegate')
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):selected(self.settings,self.root)

    def registry_copy(self,compact=False,historical_collision=False):
        """Fresh real owner/Registry; all authority and timing are fixtures."""
        from tests.test_integrated_registry import selection
        from fusion.provider_lifecycle import Registry
        from fusion.provider_retention import PROFILE as compact_profile,LIMITS
        name=('compact' if compact else 'legacy')+('-historical' if historical_collision else '')
        root=self.root/name;root.mkdir();path=root/'session-inbox.sqlite'
        choice=selection(self.cfg['templates']['shared']['scope'])
        if compact:choice.update(profile=compact_profile,limits=dict(LIMITS))
        historical=copy.deepcopy(choice)
        key='g2-storage' if historical_collision else 'storage'
        historical['records']={key:historical['records']['storage']};historical['templates']={'shared':[key]}
        owner=SustainedSessionStore(path,lambda *_:None,self.cfg,clock=self.clock)
        Registry(owner,historical,lambda *_:None).act('before-cut','add',key);owner.close()
        for name in ('restore-fence.json','owner-seal.json'):(root/name).write_bytes((self.root/name).read_bytes())
        install(root,'omega-agent','b'*64,2)
        settings=copy.deepcopy(self.settings);settings['preview']['pilot']['handover']['checkpoint_sha256']='b'*64
        def fresh():
            return dict(native_sessions=dict(database=str(path),allocation=copy.deepcopy(self.cfg),
                runtime_templates={'shared':{'directory':'shared'}},provider_registry=copy.deepcopy(choice)))
        return root,path,settings,fresh

    def attention_request(self,operation='bind'):
        from fusion import promotion_contracts as promotion
        from fusion.cognitive_services import COMPOSITION
        target='c34b9dd9-0fd8-47ca-b07f-630014d1144d'
        marker=self.root/'pilot-activation.json';value=json.loads(marker.read_bytes())
        value['historical_identity_digests']=sorted(set(value['historical_identity_digests'])|{digest(target.encode())})
        marker.write_bytes(canonical(value))
        body=dict(profile=promotion.PROFILE,selection='selected-attention',principal='A',scope='synthetic-activation',
                  context='shared-context',id='fresh-rank-occurrence',kind='rank',targets=[target],delta=0,deadline_ms=2000,limit=10)
        argument=body if operation=='bind' else dict(request=body,revision=0,time=1.0,clock='trusted-local-epoch-seconds/1')
        return dict(id='fresh-transport',composition=COMPOSITION,scope=body['scope'],interface='attention',
                    selection=body['selection'],operation=operation,args=[argument])

    def test_typed_attention_retained_targets_allowed_but_historical_operations_fenced(self):
        from unittest.mock import patch
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            for operation in ('bind','rank','scores','adjust','observe'):
                request=self.attention_request(operation)
                inner=request['args'][0] if operation=='bind' else request['args'][0]['request']
                if operation in ('scores','adjust'):
                    inner.update(kind=operation,delta=1 if operation=='adjust' else 0,limit=1)
                original=copy.deepcopy(request)
                request_guard(self.settings,self.root,'/reference-cognition',request)
                self.assertEqual(request,original)
                inner['id']='old-input'
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                    request_guard(self.settings,self.root,'/reference-cognition',request)
                request=copy.deepcopy(original);request['id']='old-input'
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                    request_guard(self.settings,self.root,'/reference-cognition',request)

    def test_attention_target_exclusion_requires_exact_route_profile_and_shape(self):
        from unittest.mock import patch
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            base=self.attention_request()
            for path in ('/preview/tasks','/preview/model'):
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                    request_guard(self.settings,self.root,path,base)
            changed=copy.deepcopy(base);changed['interface']='belief.revision'
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                request_guard(self.settings,self.root,'/reference-cognition',changed)
            mutations=(lambda q:q['args'][0].update(profile='other/1'),
                       lambda q:q['args'][0].update(targets=['not-a-uuid']),
                       lambda q:q['args'][0].update(extra='old-input'),
                       lambda q:q['args'].append(copy.deepcopy(q['args'][0])),
                       lambda q:q.update(extra='old-input'),
                       lambda q:q['args'][0].update(scope='synthetic-other'),
                       lambda q:q['args'][0].update(selection='other-selection'))
            for mutate in mutations:
                changed=copy.deepcopy(base);mutate(changed)
                with self.assertRaises(ContractError):request_guard(self.settings,self.root,'/reference-cognition',changed)
            changed=self.attention_request('rank');changed['operation']='adjust'
            with self.assertRaisesRegex(ContractError,'CONFLICT'):
                request_guard(self.settings,self.root,'/reference-cognition',changed)
            changed=self.attention_request('rank');changed['args'][0]['clock']='other-clock/1'
            with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):
                request_guard(self.settings,self.root,'/reference-cognition',changed)

    def test_memory_and_model_wire_content_does_not_become_execution_identity(self):
        from unittest.mock import patch
        from dataclasses import asdict
        import uuid
        from fusion import embedding_contracts as embedding,append_contracts as append,preview_model_contracts as model
        from fusion.registry import selection_token
        from fusion.contracts import encode
        from tests.test_append_contracts import AppendContracts
        text=canonical(dict(session=self.old,identity='old-input')).decode()
        requests=[]
        for profile in (embedding.PROFILE,embedding.MEMORY_PROFILE):
            accepted=asdict(embedding.EncodeInput(str(uuid.uuid4()),'A','synthetic-activation',text,digest(text.encode()),2000,
                           selection_token(embedding.descriptor(profile)),profile=profile))
            requests.append(('/s03-encode',dict(interface_ref=dict(id=embedding.INTERFACE,version=embedding.VERSION),operation='encode',intent=accepted,attempt=1),'occurrence'))
        _,wire=AppendContracts().wire();wire['intent'].update(content=text,helper_input=text)
        wire['body']['data']=encode(canonical(append.payload(wire['intent'])))
        requests.append(('/s03-append',wire,'occurrence'))
        prompt=text+':-:-:-:'+text
        accepted=asdict(model.CompletionInput(str(uuid.uuid4()),str(uuid.uuid4()),1,str(uuid.uuid4()),'A','synthetic-activation',
                       selection_token(model.descriptor()),prompt,model.messages(prompt),2000,model.PROFILE,model.MODEL,model.MODEL_DIGEST,model.TRANSFORM,model.LIMITS))
        requests.append(('/preview/model',dict(interface_ref=dict(id=model.INTERFACE,version=model.VERSION),operation='complete',intent=accepted),'source_id'))
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            for path,request,identity_field in requests:
                original=copy.deepcopy(request);request_guard(self.settings,self.root,path,request);self.assertEqual(request,original)
                old=copy.deepcopy(request);old['intent'][identity_field]=self.old
                if path=='/s03-append':old['request_id']=self.old
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):request_guard(self.settings,self.root,path,old)
                malformed=copy.deepcopy(request);malformed['intent']['additional_execution_id']='old-input'
                with self.assertRaises(ContractError):request_guard(self.settings,self.root,path,malformed)
            changed=copy.deepcopy(requests[-1][1]);changed['intent']['messages'][0]['content']='not-the-selected-prompt'
            with self.assertRaisesRegex(ContractError,'CONFLICT'):request_guard(self.settings,self.root,'/preview/model',changed)

    def test_worker_history_projection_is_data_but_session_input_and_occurrences_remain_fenced(self):
        from unittest.mock import patch
        import uuid
        from fusion.resident_workers import PROFILE as WORKER
        body=dict(identity='fresh-input',result=dict(turn=1,projection=canonical(dict(session=self.old,id='old-input')).decode(),occurrences=['fresh-occurrence']))
        request=dict(id='transport',profile=WORKER,operation='complete',session=str(uuid.uuid4()),incarnation=str(uuid.uuid4()),body=body)
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            original=copy.deepcopy(request);request_guard(self.settings,self.root,'/preview/worker',request);self.assertEqual(request,original)
            for mutate in (lambda q:q.update(session=self.old),lambda q:q['body'].update(identity='old-input'),
                           lambda q:q['body']['result'].update(occurrences=['old-occurrence'])):
                changed=copy.deepcopy(request);mutate(changed)
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):request_guard(self.settings,self.root,'/preview/worker',changed)
            changed=copy.deepcopy(request);changed['body']['result']['execute']='old-input'
            with self.assertRaises(ContractError):request_guard(self.settings,self.root,'/preview/worker',changed)
            submitted=dict(id='new-transport',profile='omega-native-sessions/3',operation='submit',body=dict(
                session=request['session'],identity='new-input',assignment='synthetic-task',text=body['result']['projection']))
            request_guard(self.settings,self.root,'/preview/session',submitted)

    def test_pending_workspace_raw_identity_is_fenced_without_receipt_and_content_is_opaque(self):
        from unittest.mock import patch
        from fusion.preview_workspace import Workspace
        from fusion.preview_ports import COMPOSITION,descriptor
        from fusion.registry import selection_token
        root=self.root/'execution-copy';root.mkdir();scope='synthetic-activation';identity='pending-original-effect'
        def crash(stage):
            if stage=='after_workspace_effect':raise RuntimeError('fixture-process-interruption')
        owner=Workspace(root/'workspace',root/'workspace.sqlite',lambda *_:None,scope=scope,hook=crash)
        with self.assertRaisesRegex(RuntimeError,'fixture-process-interruption'):owner.mutate('A',scope,identity,'write','old.txt','old data',0)
        self.assertIsNone(owner.db.execute('SELECT receipt FROM workspace_effects').fetchone()[0]);owner.close()
        for name in ('restore-fence.json','owner-seal.json'):(root/name).write_bytes((self.root/name).read_bytes())
        install(root,'omega-agent','d'*64,2);marker=json.loads((root/'pilot-activation.json').read_bytes())
        self.assertNotIn(digest(identity.encode()),marker['historical_identity_digests'])
        settings=copy.deepcopy(self.settings);settings['preview']['pilot']['handover']['checkpoint_sha256']='d'*64
        settings['preview']['agents']['omega-agent']['principal']='A'
        request=dict(id='fresh-transport',composition=COMPOSITION,scope=scope,interface='execution.workspace',selection=selection_token(descriptor('execution.workspace')),
                     operation='write',args=[identity,'old.txt','old data',0])
        before={p.name:p.read_bytes() for p in (root/'workspace.sqlite',root/'workspace'/'old.txt')}
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):request_guard(settings,root,'/preview/facets',request)
            request['args']=['fresh-effect','new.txt',canonical(dict(identity=identity,id='old-input')).decode(),0]
            request_guard(settings,root,'/preview/facets',request)
            changed=copy.deepcopy(request);changed['args'][1]='../escape'
            with self.assertRaises(ContractError):request_guard(settings,root,'/preview/facets',changed)
        self.assertEqual({p.name:p.read_bytes() for p in (root/'workspace.sqlite',root/'workspace'/'old.txt')},before)

    def test_actual_history_memory_and_search_shapes_retain_data_refs_and_fence_new_effect_keys(self):
        from unittest.mock import patch
        import uuid
        from fusion import lookup_contracts as lookup,preview_ports as facets,preview_memory_services as memory,cognitive_services as cognition
        from fusion.preview_lifecycle import PROFILE as LIFECYCLE
        from fusion.registry import selection_token
        from fusion.contracts import encode,validate_ref
        scope='synthetic-activation';ref=dict(scope_ref=scope,id=self.old,revision=1,digest='a'*64);validate_ref(ref,scope)
        through=lookup.make_head(self.old,scope,3,lookup.SUSTAINED_FEED)
        head=lookup.make_head(self.old,scope,1,LIFECYCLE)
        command=dict(scope_ref=scope,idempotency_key='new-mutation',intent_digest=None)
        def wire(composition,interface,selection,operation,args):return dict(id=str(uuid.uuid4()),composition=composition,scope=scope,interface=interface,selection=selection,operation=operation,args=args)
        requests=[
            ('/preview/facets',wire(facets.COMPOSITION,'episodic.memory',selection_token(facets.descriptor('episodic.memory')),
                'appendHistory',[command,ref,1,'new-history-occurrence','tool-result',ref,[ref],'2026-11-05T00:00:00Z']),0),
            ('/preview/memory',wire(memory.COMPOSITION,'memory.lifecycle',selection_token(memory.descriptor('memory.lifecycle')),
                'change',[command,'introduce',dict(logical_id=None,expected_revision=0,enrollment=ref,deadline_ms=2000)]),0),
            ('/preview/memory',wire(memory.COMPOSITION,'search',selection_token(memory.descriptor('search')),
                'build',[through,head,'new-build-occurrence',2000]),2),
            ('/reference-cognition',wire(cognition.COMPOSITION,'atom.storage','selected-atoms','create',
                [command,'application/omega-history',dict(bytes=encode(canonical(dict(session=self.old,id='old-input'))))]),0),
        ]
        with patch('integration.single_node.pilot_activation.check',lambda *_:None):
            for path,request,key_index in requests:
                original=copy.deepcopy(request);request_guard(self.settings,self.root,path,request);self.assertEqual(request,original)
                changed=copy.deepcopy(request)
                if key_index==2:changed['args'][key_index]='old-input'
                else:changed['args'][key_index]['idempotency_key']='old-input'
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):request_guard(self.settings,self.root,path,changed)
            # A reference-shaped exception remains exact. Missing its digest
            # does not make a historical executable id disappear from scan.
            bad=copy.deepcopy(requests[-1][1]);bad['args'].append(dict(scope_ref=scope,id=self.old,revision=1))
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):request_guard(self.settings,self.root,'/reference-cognition',bad)
            malformed=dict(requests[-1][1],interface_ref=['not-a-reference'])
            with self.assertRaisesRegex(ContractError,'INVALID_ARGUMENT'):request_guard(self.settings,self.root,'/reference-cognition',malformed)

    def test_restart_retains_exact_current_registry_receipts_readiness_and_binding(self):
        from unittest.mock import patch
        from integration.single_node.pilot_activation import configure
        from fusion.provider_lifecycle import Registry
        for compact in (False,True):
            with self.subTest(compact=compact):
                root,path,settings,fresh=self.registry_copy(compact)
                first=fresh()
                with patch('integration.single_node.pilot_activation.check',lambda *_:None):configure(settings,first,root,root/'run')
                cfg=first['native_sessions'];owner=SustainedSessionStore(path,lambda *_:None,cfg['allocation'],clock=self.clock)
                registry=Registry(owner,cfg['provider_registry'],lambda *_:None)
                add=registry.act('after-cut-add','add','g2-storage')
                probe=registry.probe('after-cut-probe','g2-storage',lambda _:True)
                registry.act('after-cut-enable','enable','g2-storage')
                allocation=owner.allocate('A','after-cut-allocation','g2-shared',admission=registry.admit)
                binding=registry.selected(allocation['session'])
                tables=[row[0] for row in owner.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                rows={table:[tuple(row) for row in owner.db.execute('SELECT * FROM '+table)] for table in tables};owner.close()
                restarted=fresh()
                with patch('integration.single_node.pilot_activation.check',lambda *_:None):configure(settings,restarted,root,root/'restart')
                self.assertEqual(restarted,first)
                with sqlite3.connect(path) as db:
                    for table,expected in rows.items():self.assertEqual(db.execute('SELECT * FROM '+table).fetchall(),expected)
                owner=SustainedSessionStore(path,lambda *_:None,cfg['allocation'],clock=self.clock);self.addCleanup(owner.close)
                registry=Registry(owner,restarted['native_sessions']['provider_registry'],lambda *_:None)
                self.assertEqual(registry.act('after-cut-add','add','g2-storage'),add)
                self.assertEqual(registry.probe('after-cut-probe','g2-storage',lambda _:self.fail('readiness must not renew')),probe)
                self.assertEqual(registry.selected(allocation['session']),binding)

    def test_restart_refuses_changed_current_binding_and_historical_alias(self):
        from unittest.mock import patch
        from integration.single_node.pilot_activation import configure
        from fusion.provider_lifecycle import Registry
        for compact in (False,True):
            with self.subTest(compact=compact):
                root,path,settings,fresh=self.registry_copy(compact)
                first=fresh()
                with patch('integration.single_node.pilot_activation.check',lambda *_:None):configure(settings,first,root,root/'run')
                cfg=first['native_sessions'];owner=SustainedSessionStore(path,lambda *_:None,cfg['allocation'],clock=self.clock)
                Registry(owner,cfg['provider_registry'],lambda *_:None).act('after-cut','add','g2-storage');owner.close()
                for field in ('source','image'):
                    changed=fresh();changed['native_sessions']['provider_registry']['records']['storage']['implementation'][field]='f'*64
                    with patch('integration.single_node.pilot_activation.check',lambda *_:None):
                        with self.assertRaisesRegex(ContractError,'CONFLICT'):configure(settings,changed,root,root/'restart')
        # A key already present in the imported snapshot cannot be adopted as
        # a current-generation admission even when its provider record matches.
        for compact in (False,True):
            root,path,settings,fresh=self.registry_copy(compact,historical_collision=True)
            with patch('integration.single_node.pilot_activation.check',lambda *_:None):
                with self.assertRaisesRegex(ContractError,'CONFLICT'):configure(settings,fresh(),root,root/'run')

    def test_uncertain_old_worker_does_not_block_or_replay_new_epoch(self):
        from fusion.resident_workers import Workers,LIMITS
        import uuid
        root=self.root/'uncertain-copy';root.mkdir();path=root/'session-inbox.sqlite'
        owner=Workers(path,lambda *_:None,self.cfg,dict(LIMITS),clock=self.clock)
        old=owner.store.allocate('A','unknown-old-allocation','shared')['session']
        owner.store.submit('A',old,'uncaptured-old-input','pin uncertain Preserve spent work','synthetic-task')
        epoch=str(uuid.uuid4());owner.register('A',old,epoch);owner.invoke('A',old,epoch,'ready',{})
        dispatched=owner.invoke('A',old,epoch,'next',{})['input']
        owner.retire('A',old,epoch);owner.store.control('A',old,'close-unknown','close')
        original=owner.store.observe('A',old,True);owner.close()
        for name in ('restore-fence.json','owner-seal.json'):(root/name).write_bytes((self.root/name).read_bytes())
        install(root,'omega-agent','c'*64,2)
        current=Workers(path,lambda *_:None,self.newcfg,dict(LIMITS),clock=self.clock);self.addCleanup(current.close)
        new=current.store.allocate('A','new-epoch-allocation','g2-shared')['session']
        current.store.submit('A',new,'fresh-input','pin new New intentional work','synthetic-task')
        fresh=str(uuid.uuid4());current.register('A',new,fresh);current.invoke('A',new,fresh,'ready',{})
        actual=current.invoke('A',new,fresh,'next',{})['input'];self.assertEqual(actual['id'],'fresh-input')
        self.assertEqual(current.store.observe('A',old,True),original)
        self.assertEqual(current.db.execute('SELECT state FROM native_worker_epochs WHERE incarnation=?',(epoch,)).fetchone()[0],'uncertain')
        self.assertEqual(dispatched['deadline'],original['inputs'][0]['deadline'])
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):current.store.next_input('A',old)


if __name__=='__main__':unittest.main()
