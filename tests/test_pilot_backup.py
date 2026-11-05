"""Real quiesced SQLite exports; synthetic rows, no native/provider claim."""
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fusion.contracts import canonical, digest, ContractError
from integration.single_node.backup_payload import export, restore
from integration.single_node.pilot_backup import pack, Chain, flatten, compare,compare_checkpoint
from integration.single_node.pilot_dependencies import page


class IncrementalBackup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.owner = self.root / 'owner'; self.owner.mkdir()
        self.seal = dict(role='omega-agent', scope='synthetic-pilot-backup', composition='omega-single-node-sustained-preview/1')
        (self.owner / 'owner-seal.json').write_bytes(canonical(self.seal))
        with sqlite3.connect(self.owner / 'caller.sqlite') as db:
            db.execute('CREATE TABLE retained(id INTEGER PRIMARY KEY,reserved INTEGER,result TEXT)')
            db.execute('INSERT INTO retained VALUES(1,3,?)', ('early-captured-result',))
        self.packets = []

    def full(self, name):
        root = self.root / name; root.mkdir(); output = io.BytesIO()
        with patch('sys.stdout', SimpleNamespace(buffer=output)): export(self.owner, 'omega-agent')
        raw = output.getvalue(); (root / 'omega-agent.tar.gz').write_bytes(raw)
        cut = dict(schema='synthetic-quiesced-backup/1', authority_excluded=True, original_remains_quiesced=True,
                   before=dict(namespace='omega-ref-pilot-fixture', namespace_uid='fixture'),
                   owners={'omega-agent': dict(file='omega-agent.tar.gz', sha256=digest(raw), bytes=len(raw), image='fixture')})
        (root / 'manifest.json').write_bytes(canonical(cut)); (root / 'manifest.sha256').write_text(digest(canonical(cut)) + '\n')
        return root

    def test_base_two_deltas_flatten_exact_full_and_read_early_recent(self):
        identity = None
        for index in range(3):
            with sqlite3.connect(self.owner / 'caller.sqlite') as db:
                db.execute('INSERT INTO retained VALUES(?,?,?)', (index + 2, index + 4, 'captured-' + str(index)))
            full = self.full('full-' + str(index)); target = self.root / ('packet-' + str(index))
            result = pack(full, target, self.packets, identity)
            identity = result['manifest_sha256']; self.packets.append(str(target))
            self.assertEqual(result['depth'], index + 1)
            self.assertEqual(compare(self.packets, identity, full)['status'], 'BYTE_EXACT')
        flat = self.root / 'flat'; flatten(self.packets, identity, flat)
        restored = self.root / 'restored'; restored.mkdir()
        with patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO((flat / 'omega-agent.tar.gz').read_bytes()))), patch('sys.stdout', io.StringIO()):
            restore(restored, 'omega-agent', 'omega-ref-pilot-copy')
        with sqlite3.connect(restored / 'caller.sqlite') as db:
            self.assertEqual(db.execute('SELECT result FROM retained ORDER BY id').fetchall(),
                             [('early-captured-result',), ('captured-0',), ('captured-1',), ('captured-2',)])
            self.assertEqual(db.execute('SELECT sum(reserved) FROM retained').fetchone()[0], 18)
        self.assertFalse(json.loads((restored / 'restore-fence.json').read_bytes())['external_effect_authority'])

    def test_missing_base_corrupt_chunk_and_wrong_full_refuse_before_flatten(self):
        full = self.full('full'); base = self.root / 'base'; first = pack(full, base)
        delta = self.root / 'delta'; second = pack(full, delta, [str(base)], first['manifest_sha256'])
        with self.assertRaisesRegex(ContractError, 'NOT_AVAILABLE'):
            flatten([str(delta)], second['manifest_sha256'], self.root / 'missing')
        self.assertFalse((self.root / 'missing').exists())
        chunk = next((base / 'chunks').iterdir()); chunk.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ContractError, 'CONFLICT'):
            flatten([str(base), str(delta)], second['manifest_sha256'], self.root / 'corrupt')
        self.assertFalse((self.root / 'corrupt').exists())

    def test_independent_reexport_compares_actual_owner_files_and_refuses_later_cut(self):
        original=self.full('original');packet=self.root/'packet';selected=pack(original,packet)
        independent=self.full('independent')
        self.assertEqual(compare_checkpoint([str(packet)],selected['manifest_sha256'],independent)['status'],'EXACT_OWNER_CHECKPOINT')
        with sqlite3.connect(self.owner/'caller.sqlite') as db:db.execute("INSERT INTO retained VALUES(99,4,'later-state')")
        changed=self.full('changed')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):compare_checkpoint([str(packet)],selected['manifest_sha256'],changed)

    def test_inventory_bound_page_denial_and_frozen_head(self):
        full = self.full('full'); packet = self.root / 'packet'; result = pack(full, packet)
        inventory = Chain([str(packet)]).packets[result['manifest_sha256']][1]['owners']['omega-agent']['owner_manifest']['dependency_inventory']
        head = inventory['head']; collected = []; after = 0
        while True:
            current = page(inventory, head, after, 1, lambda *_: None)
            collected += current['entries']; after = current['next']
            if current['complete']: break
        self.assertEqual(collected, inventory['entries'])
        self.assertEqual(inventory['cross_owner_closure'], 'UNVERIFIED')
        def deny(*_): raise ContractError('UNAUTHORIZED')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): page(inventory, head, 0, 128, deny)
        inventory['entries'][0]['bytes'] += 1
        with self.assertRaisesRegex(ContractError, 'CONFLICT'): page(inventory, head, 0, 128, lambda *_: None)

    def test_actual_ref_shape_recursive_history_chunks_and_current_denial(self):
        from fusion.adapters.fixture_feed import FileFeedFixture
        from fusion.preview_native_history import write_body,read_body
        from tests.test_phase2_native_relations import AuthorityFixture,SCOPE
        from integration.single_node.pilot_dependencies import dependencies,verify_closure,PROFILE
        atoms=FileFeedFixture(self.root/'fixture-atoms.json',AuthorityFixture('atom.storage'))
        body=canonical(dict(text='Synthetic retained history '*500))
        ref=write_body(atoms,SCOPE,'history-capture',body)['ref'];deps={};dependencies(dict(payload=ref),deps)
        self.assertEqual(len(deps),1)
        value=dict(profile=PROFILE,owner='omega-agent',dependencies=deps);value['head']=digest(canonical(value))
        proof=verify_closure(value,atoms,None,lambda *_:None)
        self.assertEqual(proof['status'],'VERIFIED_REFERENCES');self.assertGreater(len(proof['observations']),1)
        self.assertEqual(read_body(atoms,ref),json.loads(body))
        def deny(*_):raise ContractError('UNAUTHORIZED')
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):verify_closure(value,atoms,None,deny)
        bad=FileFeedFixture(self.root/'missing-fixture-atoms.json',AuthorityFixture('atom.storage'))
        with self.assertRaisesRegex(ContractError,'NOT_FOUND'):verify_closure(value,bad,None,lambda *_:None)

    def test_no_delta_uses_unverified_equal_filename_base(self):
        full = self.full('full'); base = self.root / 'base'; result = pack(full, base)
        with self.assertRaisesRegex(ContractError, 'NOT_AVAILABLE'):
            pack(full, self.root / 'bad', [str(base)], '0' * 64)
        self.assertFalse((self.root / 'bad').exists())

    def test_scoped_closure_partitions_private_refs_and_requires_all_original_dependencies(self):
        from integration.single_node.pilot_dependency_operator import partition,merge
        from integration.single_node.pilot_dependencies import dependencies,verify_closure,PROFILE
        from fusion.adapters.fixture_feed import FileFeedFixture
        from fusion.preview_native_history import write_body
        atoms=FileFeedFixture(self.root/'fixture-scoped-atoms.json',SimpleNamespace(authorize=lambda *_:'synthetic-fixture-operator'))
        scopes=('synthetic-pilot-shared','synthetic-pilot-private-A');deps={}
        for scope in scopes:
            ref=write_body(atoms,scope,'history-root',canonical(dict(note='synthetic-'+scope)))['ref'];dependencies(ref,deps)
        value=dict(profile=PROFILE,owner='omega-agent',dependencies=deps);value['head']=digest(canonical(value));inventories={'omega-agent':value}
        proofs={}
        for scope in scopes:
            fragment=partition(inventories,scope)['omega-agent']
            self.assertTrue(all(x['reference']['scope_ref']==scope for x in fragment['dependencies'].values()))
            proofs[scope]={'omega-agent':verify_closure(fragment,atoms,None,lambda *_:None)}
        merged=merge(inventories,proofs)['omega-agent'];self.assertEqual(merged['selected_head'],value['head'])
        self.assertEqual(set(merged['observations']),set(deps))
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):merge(inventories,{scopes[0]:proofs[scopes[0]]})
        proofs[scopes[0]]['omega-agent']['selected_head']='0'*64
        with self.assertRaisesRegex(ContractError,'CONFLICT'):merge(inventories,proofs)


if __name__ == '__main__': unittest.main()
