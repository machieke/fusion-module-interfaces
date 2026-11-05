"""Actual Chroma owner; immutable feed and vectors explicitly fixtures."""
import json
import os
import signal
import subprocess
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fusion.contracts import canonical, ContractError, digest
from fusion.pilot_search_cleanup import Cleanup
from fusion.preview_memory_services import Access, search_owner
from tests.test_integrated_search_repair import SearchRepair


class DerivedCleanup(unittest.TestCase):
    config = SearchRepair.config
    add = SearchRepair.add
    repair = SearchRepair.repair

    def setUp(self):
        SearchRepair.setUp(self)
        cfg = json.loads(self.search.read_bytes())
        cfg['principals']['A']['scopes'][self.scope] += ['search.maintenance.' + x for x in ('planCleanup', 'applyCleanup', 'observeCleanup')]
        self.search.write_bytes(canonical(cfg)); self.expiry = int(time.time() * 1000) + 1000
        self.engine = self.owner.search
        def fail(stage):
            if stage == 'after_index_write': raise ContractError('NOT_AVAILABLE')
        self.engine.hook = fail
        with self.assertRaisesRegex(ContractError, 'NOT_AVAILABLE'):
            self.engine.build_named(self.scope, self.snap['head'], 'unfinished', self.expiry)
        self.engine.hook = lambda _: None
        self.unpublished, _ = self.engine._named(self.scope, self.snap['head'], 'unfinished', 'A')
        self.clean = Cleanup(self.engine, clock=lambda: self.expiry + 1)

    def test_real_index_reclamation_retains_early_result_source_and_spend(self):
        plan = self.clean.plan([self.unpublished]); journal = self.engine.root / self.unpublished / 'maintenance.json'
        before = journal.read_bytes(); head = self.atoms.head(self.scope)
        result = self.clean.apply(plan, 'cleanup-1')
        self.assertEqual(result['state'], 'complete'); self.assertGreater(result['removed_logical_bytes'], 0)
        self.assertEqual(journal.read_bytes(), before); self.assertEqual(self.atoms.head(self.scope), head)
        self.assertEqual(self.projection.call('query', self.query), self.original)
        self.assertEqual(self.clean.apply(plan, 'cleanup-1'), result)
        self.assertFalse(result['capacity_refund'])

    def test_publication_race_and_published_pin_refuse(self):
        with self.assertRaisesRegex(ContractError, 'CONFLICT'): self.clean.plan([self.snap['generation']])
        plan = self.clean.plan([self.unpublished]); self.add('new-view')
        with self.assertRaisesRegex(ContractError, 'CONFLICT'): self.clean.apply(plan, 'stale')
        self.assertEqual(self.clean.observe(plan, 'stale')['state'], 'absent')

    def test_revocation_source_outage_and_symlink_refuse(self):
        plan = self.clean.plan([self.unpublished]); cfg = json.loads(self.search.read_bytes())
        cfg['principals']['A']['scopes'][self.scope].remove('search.maintenance.applyCleanup'); self.search.write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.clean.apply(plan, 'revoked')
        with patch.object(self.engine, '_head', side_effect=ContractError('NOT_AVAILABLE')):
            with self.assertRaisesRegex(ContractError, 'NOT_AVAILABLE'): self.clean.plan([self.unpublished])
        (self.engine.root / self.unpublished / 'index' / 'outside').symlink_to(self.root / 'atoms.json')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.clean.plan([self.unpublished])

    def test_explicit_new_profile_on_existing_authenticated_port(self):
        from fusion.pilot_search_maintenance import Client, descriptor
        from fusion.pilot_search_cleanup import PROFILE
        from fusion.registry import descriptor_wire
        cfg = json.loads(self.search.read_bytes()); cfg['active_memory']['cleanup_profile'] = PROFILE
        self.search.write_bytes(canonical(cfg))
        client = Client(dict(profile=PROFILE,scope=self.scope,placement='local',fallback=False,principal='A',
            credential='synthetic-token',provider_config=str(self.search),descriptor=descriptor_wire(descriptor())))
        with patch('fusion.pilot_search_cleanup.time.time_ns', return_value=(self.expiry+1)*1000000):
            plan = client.call('planCleanup',self.snap['lifecycle'],[self.unpublished])
            done = client.call('applyCleanup',self.snap['lifecycle'],plan,'through-port')
        self.assertEqual(done['state'],'complete')
        self.assertEqual(client.call('observeCleanup',self.snap['lifecycle'],plan,'through-port'),done)
        cfg['principals']['A']['credential']='new-token';self.search.write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):client.call('observeCleanup',self.snap['lifecycle'],plan,'through-port')

    def test_real_kill_after_unlink_recovers_observation_without_new_identity(self):
        plan = self.clean.plan([self.unpublished]); args = self.root / 'cleanup.json'
        args.write_bytes(canonical(dict(plan=plan,config=str(self.search),atoms=str(self.root/'atoms.json'),
                                       lifecycle=self.snap['lifecycle'],now=self.expiry+1)))
        process = subprocess.run([sys.executable, '-m', 'tests.test_pilot_search_cleanup', '--kill', str(args)],
                                 capture_output=True, timeout=30)
        self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr.decode())
        pending = self.clean.observe(plan, 'killed'); self.assertEqual(pending['state'], 'applying')
        self.assertIsNotNone(pending['unlink_intent'])
        done = self.clean.apply(plan, 'killed'); self.assertEqual(done['state'], 'complete')
        self.assertGreater(done['uncertain_unlink_bytes'], 0)
        self.assertEqual(self.projection.call('query', self.query), self.original)


def kill(file):
    from fusion.adapters.fixture_feed import FileFeedFixture
    args = json.loads(Path(file).read_bytes())
    atoms = FileFeedFixture(args['atoms'], SimpleNamespace(authorize=lambda *_: 'A'))
    with patch('fusion.vector_composition.ReadService',return_value=SimpleNamespace(atoms=atoms)), patch('fusion.memory_services.SearchPorts',return_value=SimpleNamespace(atoms=lambda:atoms)):
        def hook(stage):
            if stage == 'after_derived_unlink': os.kill(os.getpid(), signal.SIGKILL)
        owner = search_owner(args['config'], Access(args['config'],'synthetic-token','search'), args['lifecycle'], hook)
        Cleanup(owner, clock=lambda:args['now']).apply(args['plan'], 'killed')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--kill': kill(sys.argv[2])
    else: unittest.main()
