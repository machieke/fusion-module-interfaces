"""Real ModelService SQLite, authored backend only, deterministic clock seams.

No native tools, live model, sockets or generative runtime are used. Suspension
is an actual task-owned SIGSTOP/SIGCONT process at an owner commit boundary.
"""
import copy
import json
import multiprocessing
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError,canonical
from fusion.model_service import ModelService,inspect_journal
from fusion.pilot_model_clock import PROFILE,TABLES,selection
from tests import test_phase2_model as fixture


def suspended_owner(path,accepted,clock,writer):
    backend=fixture.RecordedProposals()
    def stop(stage):
        if stage=='after_model_reservation':
            writer.send('reserved');os.kill(os.getpid(),signal.SIGSTOP)
    with patch('fusion.model_service.now',lambda:clock.value):
        owner=ModelService(path,backend,stop,disclosure=fixture.PreviewModelTests.disclosure,contracts=fixture.c)
        try:
            try:owner.invoke(fixture.CREDENTIAL,dict(interface_ref=dict(id=fixture.c.INTERFACE,version=fixture.c.VERSION),operation='complete',intent=accepted))
            except ContractError as error:writer.send(dict(error=error.code,calls=len(backend.calls)))
        finally:owner.close();writer.close()


class ModelClockTests(unittest.TestCase):
    def fixture(self,selected=True):
        f=fixture.PreviewModelTests();f.setUp();self.addCleanup(f.doCleanups)
        if selected:f.cfg['model_completion']['owner_clock']={'profile':PROFILE};f.save()
        return f

    def test_fresh_opt_in_preserves_historical_seal_and_rejects_both_direction_migration(self):
        f=self.fixture();owner=f.owner();self.assertEqual(inspect_journal(f.path),'COMPATIBLE')
        tables={r[0] for r in owner.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(tables,{'model_seal','model_calls'}|TABLES)
        seal=owner.seal;f.close_owners();f.cfg['model_completion'].pop('owner_clock');f.save()
        self.assertEqual(fixture.c.PROFILE,'omega-recorded-native-text/2')
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):inspect_journal(f.path)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):f.owner()
        # An old empty journal is also existing state, never an implicit upgrade.
        f.cfg['model_completion']['database']=str(f.root/'historical.sqlite');f.save();old=f.owner()
        self.assertEqual(old.seal,seal.replace('model.sqlite','historical.sqlite'))
        self.assertEqual({r[0] for r in old.db.execute("SELECT name FROM sqlite_master WHERE type='table'")},{'model_seal','model_calls'})
        f.close_owners();f.cfg['model_completion']['owner_clock']={'profile':PROFILE};f.save()
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):f.owner()

    def test_clock_profile_cannot_select_live_numerical_profile(self):
        from fusion import model_contracts as live
        from fusion.registry import descriptor_wire
        f=self.fixture();cfg=copy.deepcopy(f.cfg['model_completion']);cfg['catalogue']=[descriptor_wire(live.descriptor(live.CPU_PROFILE))]
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):selection(cfg)

    def test_backward_effect_sample_survives_reopen_without_accepting_new_identity(self):
        f=self.fixture();backend=fixture.RecordedProposals();owner=f.owner(backend);first=f.invoke(owner)
        original=f.now;f.close_owners();f.now-=1;reopened=f.owner(backend)
        second=dict(f.accepted,id=str(fixture.uuid.uuid4()),slot=2)
        with self.assertRaisesRegex(ContractError,'CONFLICT'):f.invoke(reopened,accepted=second)
        rows=ModelService.inspect(f.path)
        self.assertEqual(len(rows),1);self.assertEqual(len(backend.calls),1)
        self.assertEqual(rows[0]['owner_clock']['high_water_ms'],original)
        self.assertEqual(rows[0]['owner_clock']['last_anomaly']['phase'],'acceptance')
        self.assertEqual(f.invoke(reopened,'observe'),first)

    def test_acceptance_suspension_at_deadline_does_not_reserve_or_renew(self):
        f=self.fixture();backend=fixture.RecordedProposals()
        def stop(stage):
            if stage=='after_model_acceptance':raise InterruptedError('accepted')
        owner=f.owner(backend,stop)
        with self.assertRaises(InterruptedError):f.invoke(owner)
        f.close_owners();f.now=f.accepted['deadline_ms'];reopened=f.owner(backend)
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):f.invoke(reopened)
        observed=f.invoke(reopened,'observe');self.assertEqual((observed['state'],observed['reserved']),('accepted',0))
        self.assertEqual(backend.calls,[])
        self.assertEqual(json.loads(ModelService.inspect(f.path)[0]['intent']),f.accepted)

    def test_actual_process_suspension_after_reservation_spends_budget_without_backend_entry(self):
        f=self.fixture();clock=multiprocessing.Value('q',f.now)
        reader,writer=multiprocessing.Pipe(False)
        process=multiprocessing.get_context('fork').Process(target=suspended_owner,args=(f.path,f.accepted,clock,writer))
        process.start();writer.close()
        try:
            self.assertTrue(reader.poll(5));self.assertEqual(reader.recv(),'reserved')
            clock.value=f.accepted['deadline_ms'];os.kill(process.pid,signal.SIGCONT)
            self.assertTrue(reader.poll(5));self.assertEqual(reader.recv(),dict(error='DEADLINE_EXCEEDED',calls=0))
            process.join(5);self.assertEqual(process.exitcode,0)
            f.now=clock.value+100000;backend=fixture.RecordedProposals();reopened=f.owner(backend)
            observed=f.invoke(reopened);self.assertEqual((observed['state'],observed['reserved']),('unknown',1))
            self.assertEqual(observed['failure_code'],'DEADLINE_EXCEEDED');self.assertEqual(backend.calls,[])
            f.now-=200000;self.assertEqual(f.invoke(reopened),observed);self.assertEqual(backend.calls,[])
        finally:
            if process.is_alive():os.kill(process.pid,signal.SIGCONT);process.kill();process.join(3)
            reader.close()

    def test_invalid_capture_clock_is_saved_exactly_before_refusal_and_never_regenerated(self):
        for raw in (999999,-1):
            with self.subTest(raw=raw):
                f=self.fixture();initial=f.now
                def rollback():f.now=raw
                backend=fixture.RecordedProposals(action=rollback);owner=f.owner(backend)
                with self.assertRaisesRegex(ContractError,'CONFLICT'):f.invoke(owner)
                rows=ModelService.inspect(f.path);self.assertEqual(len(rows),1)
                row=rows[0];self.assertEqual(row['captured_ms'],raw);self.assertEqual(row['reserved'],1)
                self.assertEqual(json.loads(row['response']),backend.response)
                self.assertEqual(row['owner_clock']['capture'],dict(raw_ms=raw,prior_water_ms=initial,valid=False))
                self.assertEqual(row['owner_clock']['last_anomaly']['phase'],'capture')
                f.close_owners();f.now=initial+1;replacement=fixture.RecordedProposals();reopened=f.owner(replacement)
                for operation in ('observe','complete'):
                    with self.assertRaisesRegex(ContractError,'CONFLICT'):f.invoke(reopened,operation)
                self.assertEqual(replacement.calls,[]);self.assertEqual(rows,ModelService.inspect(f.path))

    def test_capture_after_forward_jump_remains_late_and_currently_authorized(self):
        f=self.fixture()
        def forward():f.now=f.accepted['deadline_ms']+1
        backend=fixture.RecordedProposals(action=forward);owner=f.owner(backend)
        captured=f.invoke(owner);self.assertTrue(captured['late'])
        self.assertEqual(captured['captured_ms'],f.accepted['deadline_ms']+1)
        f.now+=900000;self.assertEqual(f.invoke(owner,'observe'),captured)
        f.cfg['principals']['A']['scopes'][fixture.SCOPE].remove('model.disclose');f.save()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):f.invoke(owner,'observe')
        self.assertEqual(len(backend.calls),1)

    def test_private_model_partitions_select_only_the_explicit_clock_extension(self):
        from tests.test_phase3_private import PrivateWiring
        from fusion.service_lanes import PROFILE as LANES,LIMITS
        from fusion.preview_model_binding import inspect_partitions
        f=PrivateWiring();f.setUp();self.addCleanup(f.doCleanups)
        f.preview['pilot']=dict(profile='omega-operator-pilot/1',capacity=True,subscriptions=False,workflows=False,
            owner_clock={'profile':PROFILE},request_lanes=dict(profile=LANES,limits=dict(LIMITS)))
        _,cfg,state,run=f.build('fusion-model')
        self.assertEqual(cfg['model_completion']['owner_clock'],{'profile':PROFILE})
        for name in ('private-a','private-b'):
            selected=json.loads((run/'scopes'/name/'owner.json').read_bytes())
            self.assertEqual(selected['model_completion']['owner_clock'],{'profile':PROFILE})
            self.assertNotIn('native_sessions',selected)
            self.assertNotIn('pilot_browser',selected)
        inspect_partitions(run/'owner.json')
        self.assertFalse(list(state.rglob('*.sqlite')))

    def test_existing_historical_profile_keeps_exact_tables_and_observation_bytes(self):
        f=self.fixture(selected=False);backend=fixture.RecordedProposals();owner=f.owner(backend)
        captured=f.invoke(owner);f.close_owners();f.now-=100
        self.assertEqual(f.invoke(f.owner(backend),'observe'),captured)
        self.assertNotIn('owner_clock',ModelService.inspect(f.path)[0]);self.assertEqual(len(backend.calls),1)


if __name__=='__main__':unittest.main()
