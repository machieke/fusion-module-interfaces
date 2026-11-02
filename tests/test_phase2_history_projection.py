"""Disposable history projection reconstruction over real persistent owners.

NativeHistory owns the actual application SQLite history tables and calls the
real SessionHistoryOwner. The application shell/current authority, direct
transport and FileFeedFixture AtomStorage are explicit fixtures. No native
loop, DeTTa, HTTPS, cluster, process kill or generative runtime runs here.

NativeHistory has no display-file dependency. The exported JSON below is an
explicit disposable display artifact, not an invented production history file.
Deleting it and reopening both journals checks reconstruction from the same
retained snapshot without appending owner effects or minting evidence roots.
"""
import json
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion.contracts import ContractError, canonical
from fusion.preview_history import SessionHistoryOwner
from fusion.preview_native_history import NativeHistory
from tests.test_phase2_native_relations import AuthorityFixture, DirectOwnerPort, NOW, SCOPE


class HistoryProjectionReconstruction(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='phase2-history-projection-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.atom_access = AuthorityFixture('atom.storage')
        self.history_access = AuthorityFixture('episodic.memory')
        self.atom_path = self.root/'explicit-fixture-atoms.json'
        self.owner_path = self.root/'c1-history.sqlite'
        self.application_path = self.root/'application.sqlite'
        self.config = self.root/'atom-port-fixture.json'
        self.config.write_bytes(canonical(dict(boundary='FILE_FEED_FIXTURE', credential='unused-synthetic')))
        self.session = str(uuid.uuid4())
        self.turn = 1
        self.db = None
        self.addCleanup(lambda: self.db.close() if self.db is not None else None)
        self.factory = patch('fusion.preview_native_history.atom_client', side_effect=self.atom_client)
        self.factory.start(); self.addCleanup(self.factory.stop)
        self.reopen()

    def atom_client(self, config, *, deadline_ms):
        self.assertEqual(config, dict(boundary='FILE_FEED_FIXTURE', credential='unused-synthetic'))
        return self.atoms

    def reopen(self):
        if self.db is not None:
            self.db.close()
        self.db = sqlite3.connect(self.application_path)
        self.db.row_factory = sqlite3.Row
        self.atoms = FileFeedFixture(self.atom_path, self.atom_access)
        self.owner = SessionHistoryOwner(self.owner_path, self.atoms, self.history_access)
        self.port = DirectOwnerPort(self.owner, self.history_access)
        self.app = SimpleNamespace(db=self.db, preview_config={'scope':SCOPE},
            binding={'principal':'A', 'history_atoms':{'boundary':'FILE_FEED_FIXTURE'}},
            config={'history_atoms_config':str(self.config)}, session=self.session,
            hook=lambda _: None, processing_slot=lambda: self.turn)
        self.history = NativeHistory(self.app, self.port)

    def record(self, number, kind='input-receipt'):
        self.history.record('synthetic-occurrence-'+str(number), kind,
            dict(observed_ms=NOW+number, text='Synthetic administrative event '+str(number)),
            deadline=NOW+120000)

    def populate(self):
        kinds = ['input-receipt', 'model-proposal', 'command-admitted', 'tool-result',
                 'external-observation', 'external-effect']
        for number, kind in enumerate(kinds, 1):
            self.record(number, kind)
        return kinds

    def persisted(self):
        # Compare complete authoritative logical contents, not only row counts.
        with sqlite3.connect('file:'+str(self.owner_path)+'?mode=ro', uri=True) as owner:
            c1 = tuple(owner.iterdump())
        return dict(c1=c1, atoms=self.atom_path.read_bytes(), application=tuple(self.db.iterdump()))

    def export_and_delete(self, projection):
        export = self.root/'disposable-history-display.json'
        export.write_text(projection)
        self.assertEqual(export.read_text(), projection)
        export.unlink()
        self.assertFalse(export.exists())
        return export

    def denied(self, callback):
        with self.assertRaises(ContractError) as caught:
            callback()
        self.assertEqual(caught.exception.code, 'UNAUTHORIZED')

    def test_deleted_export_rebuilds_exact_retained_projection_after_caller_and_owner_restart(self):
        kinds = self.populate()
        projection = self.history.context()
        first = json.loads(projection)
        self.assertEqual(first['snapshot']['through'], 6)
        self.assertEqual([entry['sequence'] for entry in first['events']], [3,4,5,6])
        self.assertEqual([entry['kind'] for entry in first['events']], kinds[2:])
        self.assertEqual(first['interpretation'], 'administrative-history-not-empirical-evidence')
        episode = first['ref']
        page = self.owner.readHistory(first['snapshot'], 1, 16)
        for event in page['events']:
            self.assertEqual(event['event']['lineage_roots'], [])
            self.assertEqual(event['event']['event']['provenance'], [])
            self.assertIsNone(event['event']['event']['numerical'])
        self.assertEqual(self.owner.pendingEvidence(episode, 16), ())

        export = self.export_and_delete(projection)
        # A later committed event must not silently replace an old turn's view.
        self.record(7)
        before = self.persisted()
        self.reopen()
        self.assertEqual(self.persisted(), before)
        self.assertEqual(self.history.context(), projection)
        self.assertEqual(self.owner.readHistory(first['snapshot'], 1, 16), page)
        self.assertEqual(self.owner.historySnapshot(episode)['through'], 7)
        self.assertEqual(self.persisted(), before)
        self.assertFalse(export.exists())
        self.assertFalse(any(operation in ('recordEpisode','appendHistory')
            for operation, _, _ in self.port.calls))
        retained = self.db.execute('SELECT snapshot FROM preview_history_contexts WHERE turn=1').fetchone()[0]
        self.assertEqual(json.loads(retained), first['snapshot'])

        # A genuinely new turn may select the new head; owner records still do
        # not change merely because another display projection is requested.
        self.turn = 2
        later = json.loads(self.history.context())
        self.assertEqual(later['snapshot']['through'], 7)
        self.assertEqual([entry['sequence'] for entry in later['events']], [4,5,6,7])
        after = self.persisted()
        self.assertEqual(after['c1'], before['c1'])
        self.assertEqual(after['atoms'], before['atoms'])
        self.turn = 1
        self.assertEqual(self.history.context(), projection)

    def test_reconstruction_requires_current_c1_and_payload_authority_even_with_retained_snapshot(self):
        self.populate()
        projection = self.history.context()
        export = self.export_and_delete(projection)
        self.reopen()
        before = self.persisted()
        for access, operation in ((self.history_access,'readEpisode'),
                (self.history_access,'recordEpisode'), (self.atom_access,'get')):
            with self.subTest(interface=access.interface, operation=operation):
                access.denied.add(operation)
                try:
                    self.denied(self.history.context)
                    self.assertEqual(self.persisted(), before)
                    self.assertFalse(export.exists())
                finally:
                    access.denied.remove(operation)
                self.assertEqual(self.history.context(), projection)
                self.assertEqual(self.persisted(), before)
        self.assertFalse(any(operation in ('recordEpisode','appendHistory')
            for operation, _, _ in self.port.calls))

    def test_modified_disposable_export_cannot_replace_authoritative_history(self):
        self.populate()
        original = self.history.context()
        export = self.root/'disposable-history-display.json'
        export.write_text('{"events":["fabricated display-only event"]}')
        before = self.persisted()
        self.reopen()
        self.assertEqual(self.history.context(), original)
        self.assertEqual(self.persisted(), before)
        self.assertEqual(export.read_text(), '{"events":["fabricated display-only event"]}')
        export.unlink()
        self.assertEqual(self.history.context(), original)
        self.assertEqual(self.persisted(), before)


if __name__ == '__main__':
    unittest.main()
