"""Read-only actual owner observations; finite fixtures only, no native claims."""
import json,sqlite3,tempfile,unittest,uuid
from pathlib import Path
from integration.single_node.pilot_capacity import dimension,inspect,collect
from integration.single_node.integrated_capacity import collect as historical
from tests import test_pilot_registry as registry_fixture

class Dimensions(unittest.TestCase):
    def test_unknown_bound_and_unknown_reservation_are_never_zero(self):
        value=dimension('retained',5)
        self.assertIsNone(value['limit']);self.assertIsNone(value['reserved']);self.assertIsNone(value['remaining'])
        self.assertEqual(value['used'],5)
    def test_actual_registry_owner_reports_all_finite_units(self):
        fixture=registry_fixture.Compact('test_seal_exact_binding_receipts_and_replay');fixture.setUp()
        try:
            fixture.setup_provider();fixture.registry.seal('seal','storage')
            rows={x['category']:x for x in inspect(fixture.store.db)}
            self.assertEqual(rows['registry_actions']['used'],3)
            self.assertEqual(rows['registry_active_actions']['used'],0)
            self.assertEqual(rows['registry_retained_bytes']['unit'],'bytes')
            self.assertGreater(rows['registry_retained_bytes']['control_reserve'],0)
        finally:fixture.doCleanups()
    def test_real_mailbox_schema_and_scope_names_never_leave_owner_report(self):
        from fusion.messaging import MessageOwner
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);MessageOwner(str(root/'messages.sqlite'),None,4)
            report=collect(root,root)
            rows={x['category']:x for x in report['dimensions']}
            self.assertEqual(rows['retained_mailbox_messages']['used'],0)
            self.assertEqual(rows['mailbox_unacknowledged']['used'],0)
            self.assertIsNone(rows['retained_mailbox_messages']['limit'])
            self.assertFalse(report['cross_owner_atomic'])
    def test_old_profile_remains_exact_and_new_profile_timestamps_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'owner.json').write_text('{}')
            self.assertNotIn('pilot',historical(root,root))
            (root/'owner.json').write_text(json.dumps({'pilot_capacity':'pilot-owner-headroom/1'}))
            self.assertGreater(historical(root,root)['pilot']['observed_ms'],0)

    def test_model_time_guard_and_embedding_actual_owner_tables(self):
        from tests import test_pilot_model_clock as model_fixture,test_embedding_contracts as encoder_fixture
        f=model_fixture.ModelClockTests();self.addCleanup(f.doCleanups);m=f.fixture();owner=m.owner();m.invoke(owner)
        rows={x['category']:x for x in inspect(owner.db,m.cfg)}
        self.assertEqual(rows['model_captures']['used'],1);self.assertEqual(rows['model_capture_clock_rows']['used'],1)
        self.assertEqual(rows['model_reserved_calls']['remaining'],m.cfg['model_completion']['max_calls']-1)
        e=encoder_fixture.EmbeddingContracts();e.setUp();self.addCleanup(e.doCleanups);e.service.invoke('A-token',e.request())
        values={x['category']:x for x in inspect(e.service.db,e.cfg)}
        self.assertEqual(values['embedding_attempts']['used'],1);self.assertEqual(values['embedding_uncaptured_reservations']['used'],0)
        self.assertEqual(values['largest_embedding_attempts']['limit'],3)

    def test_subscription_workflow_and_application_reserved_space_not_refunded(self):
        from tests import test_pilot_workflows as workflow_fixture
        from fusion.pilot_subscriptions import install,Subscriptions
        f=workflow_fixture.Workflows();f.setUp();self.addCleanup(f.doCleanups);install(f.store)
        subscriptions=Subscriptions(f.store,'browser-alice',lambda _:None,clock=lambda:1000)
        subscriptions.control('create','sub','start',dict(session=f.sid,lifetime_ms=5000));f.admit();f.owner.advance(f.wid,1)
        rows={x['category']:x for x in inspect(f.store.db,dict(native_sessions=dict(allocation=f.cfg)))}
        self.assertEqual(rows['subscription_actions']['reserved'],1)
        self.assertEqual(rows['workflow_spent_reservations']['used'],1)
        self.assertEqual(rows['workflow_logical_bytes']['reserved'],600000)
        self.assertGreater(rows['application_logical_bytes']['reserved'],600000)
        self.assertEqual(rows['largest_workflow_steps']['used'],1)

    def test_sealed_archive_keeps_feed_charges_and_scope_is_never_exported(self):
        from tests import test_integrated_archive as fixture
        from integration.single_node.integrated_capacity import snapshot
        from fusion.ports import Mutation
        f=fixture.Archive();f.setUp();self.addCleanup(f.doCleanups);owner=f.owner();f.write(1,owner)
        owner.publishArchive(Mutation(fixture.SCOPE,'seal'),0,owner.head(fixture.SCOPE),1)
        with snapshot(owner.path) as db:rows={x['category']:x for x in inspect(db)}
        self.assertEqual(rows['feed_scope_0_reserved_records']['used'],1)
        self.assertEqual(rows['feed_scope_0_archive_segments']['used'],1)
        self.assertEqual(rows['feed_scope_0_archive_pending']['used'],0)
        self.assertNotIn(fixture.SCOPE,json.dumps(rows))

    def test_private_model_partitions_use_their_own_selected_limit_and_missing_is_unknown(self):
        from tests import test_phase2_model as fixture
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'state';run=Path(tmp)/'run';root.mkdir();run.mkdir()
            for label,limit in [('',4),('scopes/private-a',7)]:
                f=fixture.PreviewModelTests();f.setUp();self.addCleanup(f.doCleanups)
                state=root/label;configuration=run/label;state.mkdir(exist_ok=True,parents=True);configuration.mkdir(exist_ok=True,parents=True)
                f.cfg['model_completion']['database']=str(state/'model.sqlite');f.cfg['model_completion']['max_calls']=limit;f.save();f.owner()
                (configuration/'owner.json').write_text(json.dumps(f.cfg))
            report=collect(root,run);rows=[x for x in report['dimensions'] if x['category']=='model_occurrences']
            self.assertEqual([(x['partition'],x['limit']) for x in rows],[(0,4),(1,7)])
            self.assertEqual(report['unavailable'],[])
            (run/'scopes/private-b').mkdir();(run/'scopes/private-b/owner.json').write_text(json.dumps({'model_completion':{'database':str(root/'scopes/private-b/model.sqlite'),'max_calls':9}}))
            missing=collect(root,run);self.assertEqual(missing['unavailable'][0]['status'],'UNKNOWN')
            self.assertFalse((root/'scopes/private-b').exists())

    def test_search_metadata_is_not_an_index_or_provider_read(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);search=root/'memory/search';search.mkdir(parents=True);generation=str(uuid.uuid4());directory=search/generation;directory.mkdir()
            (directory/'maintenance.json').write_text(json.dumps({'attempts':2}))
            (directory/'manifest.json').write_text(json.dumps({'records':[{'fixture':True}]}))
            (search/'published.json').write_text(json.dumps({'generations':{generation:{}},'current':{}}))
            with patch('fusion.adapters.chroma_vector.ChromaVector.__init__',side_effect=AssertionError('no index or source owner')):report=collect(root,root)
            rows={x['category']:x for x in report['dimensions']}
            self.assertEqual(rows['search_build_attempts']['used'],2);self.assertEqual(rows['retained_search_generations']['used'],1)
            self.assertIsNone(rows['search_generation_directories']['reclaimable_derived_bytes'])

    def test_symlink_foreign_configuration_and_corruption_are_unknown_without_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            top=Path(tmp);root=top/'state';root.mkdir();foreign=top/'foreign.sqlite';foreign.write_bytes(b'PRIVATE-CANARY')
            (root/'model.sqlite').symlink_to(foreign)
            (root/'owner.json').write_text(json.dumps({'model_completion':{'database':str(foreign),'max_calls':2}}))
            report=collect(root,root);self.assertEqual(len(report['unavailable']),2)
            self.assertEqual(report['dimensions'],[]);self.assertNotIn('PRIVATE-CANARY',json.dumps(report));self.assertEqual(foreign.read_bytes(),b'PRIVATE-CANARY')

    def test_retained_application_resolves_only_its_allocated_caller_journals(self):
        from fusion.sustained_sessions import SustainedSessionStore
        from fusion.preview_context import WorkingContext
        from fusion.chain_continuation import Continuation
        from tests.test_phase3_sessions import policy
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg=policy();store=SustainedSessionStore(root/'session-inbox.sqlite',lambda *_:None,cfg,clock=lambda:1000)
            self.addCleanup(store.close);session=store.allocate('A','capacity-owned','shared')['session']
            (root/'owner.json').write_text(json.dumps(dict(native_sessions=dict(database=str(root/'session-inbox.sqlite'),allocation=cfg))))
            path=root/'sessions'/session;path.mkdir(parents=True)
            db=sqlite3.connect(path/'caller.sqlite');db.row_factory=sqlite3.Row
            context=WorkingContext(db,lambda _:None);context.change('once','note','synthetic retained note',0)
            Continuation(db,None,lambda _:None);db.close()
            # An unallocated UUID directory is not evidence and is never read.
            foreign=root/'sessions'/str(uuid.uuid4());foreign.mkdir();(foreign/'caller.sqlite').write_bytes(b'FOREIGN-CANARY')
            report=collect(root,root);self.assertEqual(report['unavailable'],[])
            rows={x['category']:x for x in report['dimensions'] if x['partition']=='session-0'}
            self.assertEqual(rows['working_context_history']['used'],2);self.assertEqual(rows['largest_working_context_items']['limit'],8)
            self.assertEqual(rows['chain_continuations']['used'],0);self.assertEqual(rows['chain_spent_submit_reservations']['used'],0)
            self.assertNotIn(session,json.dumps(report));self.assertNotIn('synthetic retained note',json.dumps(report))
