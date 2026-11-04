"""Read-only startup compatibility; no backend calls or native generation."""
import copy
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError, canonical
from fusion.model_service import configuration_seal, inspect_journal
from fusion.preview_model_binding import inspect_configuration, inspect_partitions
from tests import test_phase2_model as fixture


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture.PreviewModelTests();self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def test_absent_does_not_create_database(self):
        database=Path(self.f.cfg['model_completion']['database'])
        before=set(self.f.root.iterdir())
        self.assertEqual(inspect_journal(self.f.path),'ABSENT')
        self.assertFalse(database.exists());self.assertEqual(set(self.f.root.iterdir()),before)

    def test_existing_seal_exact_and_credential_rotation_compatible(self):
        owner=self.f.owner();before=list(owner.db.iterdump())
        self.assertEqual(inspect_journal(self.f.path),'COMPATIBLE')
        self.f.cfg['principals']['A']['credential']='rotated-synthetic-token';self.f.save()
        self.assertEqual(inspect_journal(self.f.path),'COMPATIBLE')
        self.assertEqual(list(owner.db.iterdump()),before)
        self.assertEqual(owner.seal,configuration_seal(self.f.cfg['model_completion']))

    def test_sealed_limits_refused_before_backend_and_no_state_changes(self):
        owner=self.f.owner();before=list(owner.db.iterdump())
        self.f.cfg['model_completion']['max_calls']+=1;self.f.save()
        with patch('fusion.preview_recorded_model.RecordedProposals',side_effect=AssertionError('backend constructed')):
            with self.assertRaises(ContractError) as error:inspect_configuration(self.f.path)
        self.assertEqual(error.exception.code,'CONFLICT')
        self.assertEqual(list(owner.db.iterdump()),before)

    def test_private_partitions_checked_before_ready(self):
        self.f.owner()
        directory=self.f.root/'private';directory.mkdir()
        private=copy.deepcopy(self.f.cfg)
        private['model_completion']['max_calls']+=1
        (directory/'owner.json').write_bytes(canonical(private))
        self.f.cfg['scope_routes']={'scopes':{'synthetic-private':{'directory':str(directory)}}};self.f.save()
        with patch('fusion.preview_recorded_model.RecordedProposals') as backend:
            with self.assertRaises(ContractError) as error:inspect_partitions(self.f.path)
        self.assertEqual(error.exception.code,'CONFLICT');self.assertEqual(backend.call_count,1)

    def test_malformed_existing_seal_refused_without_repair(self):
        self.f.owner();self.f.close_owners()
        database=self.f.cfg['model_completion']['database']
        with sqlite3.connect(database) as db:db.execute('DELETE FROM model_seal')
        with self.assertRaises(ContractError) as error:inspect_journal(self.f.path)
        self.assertEqual(error.exception.code,'CONFLICT')
        with sqlite3.connect(database) as db:self.assertEqual(db.execute('SELECT count(*) FROM model_seal').fetchone()[0],0)


if __name__=='__main__':unittest.main()
