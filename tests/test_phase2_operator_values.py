"""Offline operator discovery and values generation with synthetic fixtures.

Real catalogue, policy and configuration validators are exercised. Image
manifests are explicit metadata fixtures, not verified OCI/provider evidence.
No cluster, native process, model runtime, image build or owner journal runs.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from fusion.contracts import ContractError, canonical
from fusion.preview_application import APPLICATION
from fusion.preview_sessions import PROFILE as SESSIONS
from integration.single_node import preview_operator as operator, preview_values as values


NOW = 1793620800000
SCOPE = 'synthetic-operator-values-tests'


def image_manifest_fixture():
    return dict(source_export_verification='PASS', source_manifest_sha256='a'*64,
        archive_sha256='b'*64, archive_bytes=4096, container_starts=0,
        generative_runtime_availability='NOT_CHECKED', images=[
            dict(kind=kind, repository='fixture.invalid/fusion-'+kind,
                 local_tag='fixture.invalid/fusion-'+kind+':reference-fixture',
                 manifest_digest='sha256:'+str(index)*64,
                 configuration_digest='sha256:'+str(index+3)*64,
                 source_package='image-'+kind+'/package.json')
            for index, kind in enumerate(('base', 'caller', 'embedding'), 1)])


class ValuesTests(unittest.TestCase):
    def setUp(self):
        clock = patch('time.time_ns', return_value=NOW*1000000)
        clock.start(); self.addCleanup(clock.stop)
        self.manifest = image_manifest_fixture()

    def refused(self, manifest=None, scope=SCOPE, **kwargs):
        with self.assertRaises(ContractError):
            values.generate(self.manifest if manifest is None else manifest, scope, **kwargs)

    def test_all_modes_keep_recorded_boundary_and_digest_pinned_selected_images(self):
        original = copy.deepcopy(self.manifest)
        for mode in ('minimal', 'memory', 'combined'):
            with self.subTest(mode=mode):
                cfg = values.generate(self.manifest, SCOPE, mode=mode, inputs=2, sessions=1, expires_ms=NOW+30000)
                p = cfg['preview']; components = cfg['components']
                self.assertEqual(p['model_boundary'], 'RECORDED_FIXTURE')
                self.assertEqual(p['authority_expires_ms'], NOW+30000)
                self.assertEqual(p['limits'], dict(inputs=2, pending=4, timeout_ms=120000))
                self.assertEqual(cfg['image']['digest'], self.manifest['images'][0]['manifest_digest'])
                self.assertEqual(cfg['image']['pullPolicy'], 'Never')
                for role in ('omega-agent', 'omega-agent-b'):
                    self.assertEqual(components[role]['image']['digest'], self.manifest['images'][1]['manifest_digest'])
                self.assertEqual(components['fusion-model'], {'enabled': True})
                self.assertTrue(cfg['networkPolicy']['enabled'])
                self.assertNotIn('liveEnabled', p); self.assertNotIn('futureLive', cfg)
                self.assertNotIn('credential', json.dumps(cfg)); self.assertNotIn('privateKey', json.dumps(cfg))
                self.assertTrue(all(value == {'proposal': 'input-command'} for value in p['responses'].values()))
                selected = p['agents']['omega-agent']['tools']
                if mode == 'minimal':
                    self.assertNotIn('query', selected); self.assertNotIn('fusion-embedding', components)
                else:
                    self.assertIn('query', selected); self.assertIn('delegate', selected)
                    self.assertEqual(components['fusion-embedding']['image']['digest'], self.manifest['images'][2]['manifest_digest'])
                self.assertEqual('support' in selected, mode == 'combined')
        self.assertEqual(self.manifest, original)

    def test_generated_occurrences_are_fresh_without_started_input_deadlines(self):
        first = values.generate(self.manifest, SCOPE, inputs=32, sessions=2)
        second = values.generate(self.manifest, SCOPE, inputs=32, sessions=2)
        ids = [sid for agent in first['preview']['agents'].values() for sid in agent['sessions']]
        next_ids = [sid for agent in second['preview']['agents'].values() for sid in agent['sessions']]
        self.assertEqual(len(ids), 4); self.assertEqual(len(set(ids)), 4)
        self.assertTrue(set(ids).isdisjoint(next_ids))
        for sid in ids: self.assertEqual(str(uuid.UUID(sid)), sid)
        self.assertEqual(len(first['preview']['responses']), 128)
        self.assertEqual(first['preview']['authority_expires_ms'], NOW+86400000)
        self.assertNotEqual(first['preview']['policy_revision'], second['preview']['policy_revision'])
        self.assertNotIn('deadline', canonical(first).decode())

    def test_full_reference_manifest_does_not_activate_extra_chain_or_generative_images(self):
        manifest = copy.deepcopy(self.manifest)
        for kind in ('chain', 'hive', 'generative'):
            manifest['images'].append(dict(kind=kind, repository='fixture.invalid/fusion-'+kind,
                local_tag='fixture.invalid/fusion-'+kind+':reference-fixture', manifest_digest='sha256:'+'f'*64,
                configuration_digest='sha256:'+'e'*64, source_package='image-'+kind+'/package.json'))
        cfg = values.generate(manifest, SCOPE)
        rendered = canonical(cfg).decode()
        self.assertNotIn('fixture.invalid/fusion-generative', rendered)
        self.assertNotIn('fixture.invalid/fusion-chain', rendered)
        self.assertNotIn('fixture.invalid/fusion-hive', rendered)
        self.assertEqual(cfg['preview']['model_boundary'], 'RECORDED_FIXTURE')

    def test_input_session_and_mode_bounds_are_closed(self):
        for field, candidates in [('inputs', (0, 33, True, 1.0, '2')), ('sessions', (0, 3, False, 1.0, '1'))]:
            for value in candidates:
                with self.subTest(field=field, value=value): self.refused(**{field: value})
        for mode in ('live', 'chain', '', None, []):
            with self.subTest(mode=mode): self.refused(mode=mode)

    def test_scope_rejects_private_malformed_and_path_like_values(self):
        for scope in ('private-memory', 'synthetic-', 'synthetic-a/b', 'synthetic-a\nb', 'synthetic-a b',
                      'synthetic-'+'x'*55, None, 3, []):
            with self.subTest(scope=scope): self.refused(scope=scope)

    def test_expiry_rejects_implicit_renewal_type_aliases_and_past_values(self):
        for expires in (0, False, True, -1, NOW, NOW-1, float(NOW+30000), str(NOW+30000)):
            with self.subTest(expires=expires): self.refused(expires_ms=expires)

    def test_source_export_pass_and_full_source_digest_are_required(self):
        for field, value in [('source_export_verification', 'FAIL'), ('source_export_verification', True),
                             ('source_manifest_sha256', None), ('source_manifest_sha256', 'a'*63),
                             ('source_manifest_sha256', 'g'*64)]:
            manifest = copy.deepcopy(self.manifest); manifest[field] = value
            with self.subTest(field=field, value=value): self.refused(manifest)
        for key in ('source_export_verification', 'source_manifest_sha256', 'images'):
            manifest = copy.deepcopy(self.manifest); del manifest[key]
            with self.subTest(missing=key): self.refused(manifest)

    def test_required_image_kinds_cannot_be_omitted_or_duplicated(self):
        for kind in ('base', 'caller', 'embedding'):
            manifest = copy.deepcopy(self.manifest)
            manifest['images'] = [image for image in manifest['images'] if image['kind'] != kind]
            with self.subTest(missing=kind): self.refused(manifest)
        for kind in ('base', 'caller', 'embedding'):
            manifest = copy.deepcopy(self.manifest)
            manifest['images'].append(next(image for image in copy.deepcopy(manifest['images']) if image['kind'] == kind))
            with self.subTest(duplicate=kind): self.refused(manifest)

    def test_image_digest_repository_and_tag_bindings_cannot_be_malformed(self):
        for field, value in [('manifest_digest', ''), ('manifest_digest', 'sha256:'+'f'*63),
                             ('manifest_digest', 'sha256:'+'z'*64), ('manifest_digest', None),
                             ('repository', ''), ('repository', 'fixture.invalid/unsafe\nimage'),
                             ('local_tag', 'fixture.invalid/different:reference-fixture'),
                             ('local_tag', 'fixture.invalid/fusion-base'), ('local_tag', 'fixture.invalid/fusion-base:')]:
            manifest = copy.deepcopy(self.manifest); manifest['images'][0][field] = value
            with self.subTest(field=field, value=value): self.refused(manifest)

    def test_malformed_manifest_roots_and_image_entries_fail_as_contract_errors(self):
        for manifest in ([], 'PASS', 1):
            with self.subTest(manifest=manifest): self.refused(manifest)
        for images in (None, {}, [], [None], ['base']):
            manifest = copy.deepcopy(self.manifest); manifest['images'] = images
            with self.subTest(images=images): self.refused(manifest)


class OperatorInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-operator-values-')
        self.addCleanup(self.temp.cleanup); self.root = Path(self.temp.name)
        self.run = self.root/'run'; self.state = self.root/'state'
        self.run.mkdir(); self.state.mkdir()
        self.sid = str(uuid.uuid4()); self.owner = self.run/'owner.json'
        self.authority_path = self.run/'authority.json'
        self.authority = dict(principal='A', scope=SCOPE, tools=['pin'], revision='fixture-policy-1',
            expires_ms=NOW+30000, revoked=False)
        self.authority_path.write_bytes(canonical(self.authority))
        self.cfg = dict(principals={'operator': dict(credential='SECRET_FIXTURE_MARKER', scopes={SCOPE: ['sessions.observe']})},
            native_sessions=dict(profile=SESSIONS, principal='A', scope=SCOPE, model_boundary='RECORDED_FIXTURE',
                session_templates={self.sid: dict(catalogue='fixture-selection', policy='fixture-policy-1',
                    model_boundary='RECORDED_FIXTURE', limits=dict(inputs=8, pending=4, timeout_ms=30000))},
                assignments=['synthetic-task']))
        self.owner.write_bytes(canonical(self.cfg))
        path = self.run/'sessions'/self.sid/'application.json'; path.parent.mkdir(parents=True)
        self.application = dict(preview=dict(profile=APPLICATION, base='controlled-native-loop/1',
            authority_file=str(self.authority_path), tools=['pin', 'unpin'], scope=SCOPE))
        path.write_bytes(canonical(self.application))
        self.application_path = path
        (self.state/'worker-status.json').write_bytes(canonical(dict(state='idle', model_boundary='RECORDED_FIXTURE')))
        clock = patch('time.time_ns', return_value=NOW*1000000)
        clock.start(); self.addCleanup(clock.stop)

    def inventory(self):
        with patch.object(operator, 'invoke', side_effect=AssertionError('inventory must not execute work')):
            return operator.inventory(owner=str(self.owner), run=str(self.run), state=str(self.state))

    def test_inventory_exposes_current_restrictions_and_no_credentials_or_payloads(self):
        value = self.inventory()
        self.assertEqual(value['principal'], 'A'); self.assertEqual(value['scope'], SCOPE)
        self.assertEqual(value['model_boundary'], 'RECORDED_FIXTURE'); self.assertEqual(value['additional_live_generations'], 0)
        policy = value['policies'][self.sid]
        self.assertEqual(policy, self.authority)
        self.assertNotIn('SECRET_FIXTURE_MARKER', canonical(value).decode())
        self.assertNotIn('authority_file', canonical(value).decode())
        self.assertIn('pin', value['catalogues'][self.sid]['tools'])
        self.assertNotIn('unpin', value['catalogues'][self.sid]['tools'])
        self.assertEqual(value['worker']['state'], 'idle')

    def test_inventory_rechecks_operator_permission_on_every_read(self):
        self.inventory()
        self.cfg['principals']['operator']['scopes'][SCOPE] = []
        self.owner.write_bytes(canonical(self.cfg))
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.inventory()

    def test_inventory_rejects_revoked_expired_or_foreign_session_authority(self):
        for key, value in [('revoked', True), ('expires_ms', NOW), ('principal', 'B'), ('scope', 'synthetic-foreign')]:
            self.authority_path.write_bytes(canonical(dict(self.authority, **{key: value})))
            with self.subTest(key=key), self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): self.inventory()

    def test_inventory_observes_policy_narrowing_without_operator_configuration_edits(self):
        before = self.inventory()
        restricted = dict(self.authority, tools=[], revision='fixture-policy-2')
        self.authority_path.write_bytes(canonical(restricted))
        after = self.inventory()
        self.assertEqual(after['policies'][self.sid]['tools'], [])
        self.assertEqual(after['policies'][self.sid]['revision'], 'fixture-policy-2')
        self.assertEqual(set(before['catalogues'][self.sid]['tools']), {'pin'})
        self.assertEqual(after['catalogues'][self.sid]['tools'], {})
        self.assertEqual(json.loads(self.application_path.read_text()), self.application)

    def test_inventory_refuses_unselected_session_profile_or_model_boundary(self):
        for key, value in [('profile', 'unselected-sessions/1'), ('model_boundary', 'REAL_GENERATION')]:
            cfg = copy.deepcopy(self.cfg); cfg['native_sessions'][key] = value
            self.owner.write_bytes(canonical(cfg))
            with self.subTest(key=key), self.assertRaises(ContractError): self.inventory()

    def test_inventory_rejects_malformed_authority_tools_without_coercion(self):
        for tools in ('pin', None, {'pin': True}, ['pin', 'pin']):
            self.authority_path.write_bytes(canonical(dict(self.authority, tools=tools)))
            with self.subTest(tools=tools), self.assertRaises(ContractError): self.inventory()


if __name__ == '__main__': unittest.main()
