"""Scope wiring uses real policies; TLS bytes and uncalled ports are fixtures."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError,canonical
from fusion.policy import Policy
from fusion.preview_session_service import SessionPorts
from fusion.sustained_sessions import PROFILE
from integration.single_node.sustained_private import ScopeRouter
from integration.single_node.sustained_runtime import materialize
from tests.test_phase3_composition import DynamicConfiguration


class PrivateWiring(DynamicConfiguration):
    def setUp(self):
        super().setUp()
        self.preview['sustained']['private_scopes']=True
        for role,spec in self.preview['agents'].items():
            spec['private_scope']='synthetic-private-'+spec['principal'].lower()

    def test_private_native_template_freezes_all_scopes_and_own_application_root(self):
        for agent in self.preview['agents']:
            _,cfg,state,run=self.build(agent);ports=SessionPorts(run/'owner.json')
            sid=ports.invoke(cfg['principals']['operator']['credential'],dict(id='allocate',profile=PROFILE,
                operation='allocate',body=dict(identity='private-session',template='private')))['value']['session']
            path=materialize(run/'owner.json',state,run,sid);app=json.loads(path.read_bytes())
            scope=self.preview['agents'][agent]['private_scope']
            self.assertEqual(app['preview']['scope'],scope)
            self.assertEqual(app['private_diagnostics'],'bounded-stages-only/1')
            for name in ('memory-atoms.json','history-atoms.json','evidence-client.json','attention-client.json',
                         'memory-read-template.json','memory-append.json','model.json'):
                self.assertEqual(json.loads((path.parent/name).read_bytes())['scope'],scope,name)
            self.assertNotIn('task_config',app)
            self.assertEqual(app['workdir'],str(state/'sessions'/sid/'native'))

    def test_wrong_principal_denied_before_any_private_owner_construction(self):
        for role,route,file,credential_name in (
            ('fusion-storage','/reference-cognition','cognitive-owner.json','cog-caller-B-token'),
            ('fusion-storage','/memory-source','owner.json','caller-B-token'),
            ('fusion-search','/preview/memory','owner.json','caller-B-token'),
            ('fusion-episodes','/preview/facets','facet-owner.json','facet-caller-B-token'),
            ('fusion-beliefs','/reference-cognition','cognitive-owner.json','cognitive-caller-B-token'),
            ('fusion-attention','/reference-cognition','cognitive-owner.json','cognitive-caller-B-token'),
            ('fusion-model','/preview/model','owner.json','caller-B-token')):
            with self.subTest(role=role,route=route):
                _,cfg,state,run=self.build(role);router=ScopeRouter(run/'owner.json',role)
                scope='synthetic-private-a'
                token=(self.root/role/'secrets'/credential_name).read_text()
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                    router.invoke(route,token,dict(scope=scope))
                self.assertFalse(list((state/'scopes'/'private-a').rglob('*.sqlite')))
                selected=run/'scopes'/'private-b'/file
                policy=Policy(selected)
                for record in policy.current().get('principals',{}).values():
                    self.assertNotIn(scope,record.get('scopes',{}))

    def test_full_generated_combined_configuration_preserves_every_declared_requirement(self):
        from integration.single_node.sustained_values import generate
        from integration.single_node.preview_secrets import material
        from tests.test_phase2_operator_values import image_manifest_fixture
        self.preview=generate(image_manifest_fixture(),'synthetic-private-full')['preview']
        clients={role:(self.root/role/'secrets'/'caller-token').read_text() for role in self.roles if role not in self.preview['agents']}
        for role,entries in material(self.preview,self.roles,clients).items():
            for name,value in entries.items():(self.root/role/'secrets'/name).write_bytes(value)
        for role in self.roles:
            if role=='fusion-embedding':continue  # Native E5 asset lock unavailable in this config-only fixture.
            _,cfg,state,run=self.build(role)
            if role in self.preview['agents']:
                self.assertEqual(set(cfg['native_sessions']['allocation']['templates']),{'shared','private'})
                private=json.loads((run/'templates'/'private'/'application.json').read_bytes())
                self.assertNotIn('delegate',private['preview']['tools'])
                self.assertNotIn('inspect-atom',private['preview']['tools'])
                self.assertNotIn('execution.workspace',private['facet_configs'])

    def test_revoked_private_scope_cannot_reuse_an_authenticated_route(self):
        _,cfg,state,run=self.build('fusion-storage');router=ScopeRouter(run/'owner.json','fusion-storage')
        path=run/'scopes'/'private-a'/'cognitive-owner.json';value=json.loads(path.read_bytes())
        token=value['principals']['A']['credential'];value['principals']['A']['scopes']={};path.write_bytes(canonical(value))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
            router.invoke('/reference-cognition',token,dict(scope='synthetic-private-a'))

    def test_private_owner_barrier_preserves_preexisting_unarmed_runtime_binding(self):
        from integration.single_node.sustained_configure import configure
        from integration.single_node.sustained_runtime import template_files,public_config
        from fusion.contracts import digest
        settings=self.settings('omega-agent',enabled=False)
        settings['service_composition']='omega-single-node-sustained-preview/1'
        _,cfg,state,run=configure(settings)
        old=cfg['native_sessions']['allocation']['templates']['private']
        files=template_files(run/'templates/private')
        # Reconstruct the prior implementation's canonical digest. Compatibility
        # is established against its bytes, not just two calls to the new code.
        legacy={name:public_config({k:v for k,v in value.items() if k not in ('pause_at','test_failpoints')}
            if name=='application.json' else value) for name,value in files.items()}
        ca=self.root/'omega-agent'/'secrets'/'ca.crt'
        self.assertEqual(old['runtime_digest'],digest(canonical(dict(files=legacy,ca_sha256=digest(ca.read_bytes())))))
        settings.update(enable_test_faults=True,test={'pause_at':'after_source_acceptance'})
        _,armed,_,_=configure(settings)
        self.assertEqual(armed['native_sessions']['allocation']['templates']['private'],old)
        (state/'scopes/private-a/pause.json').write_text('{}')
        _,consumed,_,_=configure(settings)
        self.assertEqual(consumed['native_sessions']['allocation']['templates']['private'],old)

    def test_fenced_private_reads_select_private_recipe_without_materializing(self):
        from integration.single_node import sustained_current as current
        from fusion.contracts import digest
        from types import SimpleNamespace
        _,cfg,state,run=self.build('omega-agent');ports=SessionPorts(run/'owner.json')
        sid=ports.invoke(cfg['principals']['operator']['credential'],dict(id='allocate',profile=PROFILE,
            operation='allocate',body=dict(identity='restored-private-read',template='private')))['value']['session']
        (state/'restore-fence.json').write_text('{}');scope='synthetic-private-a'
        db=Path(cfg['native_sessions']['database']);before=db.read_bytes()
        selected=[]
        def atoms(config):
            self.assertEqual(config['scope'],scope);selected.append(config['scope'])
            def head(requested):self.assertEqual(requested,scope);return {'sequence':7}
            return SimpleNamespace(head=head,capacity=lambda requested:{'records':7})
        class Memory:
            def __init__(_,path,interface):self.assertEqual(json.loads(Path(path).read_bytes())['scope'],scope)
            def call(_,operation,*args):return {}
        def remote(endpoint,route,q):
            self.assertEqual(q['scope'],scope)
            return dict(profile=q['profile'],id=q['id'],request_digest=digest(canonical(q)),selection=q['selection'],principal='A',value={})
        with patch.object(current,'atoms',side_effect=atoms),patch.object(current,'Memory',Memory),patch.object(current,'materialize',side_effect=AssertionError('no executable materialization')),patch('fusion.preview_transport.invoke',side_effect=remote):
            result=current.observe(sid,run/'owner.json',state,run)
        self.assertTrue(result['restore_fenced']);self.assertEqual(result['scope'],scope)
        self.assertEqual(selected,[scope]);self.assertEqual(db.read_bytes(),before)
        self.assertFalse((run/'sessions'/sid).exists())

if __name__=='__main__':unittest.main()
