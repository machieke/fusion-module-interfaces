"""Static fresh configuration/chart checks; no cluster or runtime execution."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid

from fusion.contracts import ContractError,canonical
from fusion.preview_application import configuration
from fusion.preview_recorded_model import RecordedProposals
from integration.single_node.preview_configure import configure,COMPOSITION

ROOT=Path(__file__).resolve().parents[1]


class PreviewDeployment(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.secrets=self.root/'secrets';self.secrets.mkdir()
        names=['ca.crt','tls.crt','tls.key','caller-token','worker-token','session-operator-token','session-worker-token']
        roles=['omega-agent','omega-agent-b','fusion-execution','fusion-storage','fusion-messaging','fusion-model','fusion-episodes','fusion-relations']
        names += [role+'-token' for role in roles]+['facet-'+role+'-token' for role in roles]
        for who in ('A','B'):
            names += [prefix+who+'-token' for prefix in ('atom-','cog-caller-','facet-caller-','caller-')]
        for index,name in enumerate(names):(self.secrets/name).write_text(('generated-test-'+str(index)+'-').ljust(40,'x'))
        self.agents={role:dict(principal=who,sessions=[str(uuid.uuid4())],tools=['pin','unpin','task-context','episodes','read-file','write-file','append-file'],
                              facets=['episodic.memory','execution.workspace']) for role,who in (('omega-agent','A'),('omega-agent-b','B'))}
        self.settings=dict(role='omega-agent',service_composition=COMPOSITION,state='',run='',secret_directory=str(self.secrets),
            https_port=8443,capacity=8,revision='preview-test',native_enabled=True,worker_enabled=False,
            enable_test_faults=False,test={},peers={role:role+'.omega-ref-preview-test.svc.cluster.local' for role in roles},
            preview=dict(enabled=True,profile=COMPOSITION,scope='synthetic-preview-deployment',model_boundary='RECORDED_FIXTURE',
                authority_expires_ms=int(time.time()*1000)+120000,policy_revision='preview-policy-1',agents=self.agents,
                limits=dict(inputs=8,pending=4,timeout_ms=30000),assignments=['notes'],responses={
                    self.agents['omega-agent']['sessions'][0]+'/1':'pin task Synthetic note'}))

    def role(self,role):
        value=copy.deepcopy(self.settings);value.update(role=role,state=str(self.root/role/'state'),run=str(self.root/role/'run'))
        return configure(value)

    def test_separate_principals_sessions_tls_and_recorded_only_model(self):
        for role in self.agents:
            _,cfg,state,run=self.role(role)
            self.assertEqual(cfg['native_sessions']['principal'],self.agents[role]['principal'])
            sid=self.agents[role]['sessions'][0]
            app=json.loads((run/'sessions'/sid/'application.json').read_text())
            self.assertNotIn('model_fixture',app)
            selected=configuration(app['preview'])
            self.assertEqual(cfg['native_sessions']['session_templates'][sid]['catalogue'],selected.identity)
            caller=json.loads(Path(app['caller_config']).read_text())
            self.assertEqual(caller['principal'],self.agents[role]['principal'])
            self.assertTrue(Path(caller['database']).is_relative_to(state))
            self.assertFalse((state/'session-inbox.sqlite').exists())
        _,cfg,state,run=self.role('fusion-model')
        RecordedProposals(run/'owner.json')
        self.assertEqual(cfg['model_completion']['runtime_lock']['generative_runtime'],'FORBIDDEN')
        self.assertFalse((state/'model.sqlite').exists())
        for role in ('fusion-execution','fusion-storage','fusion-messaging','fusion-episodes','fusion-relations'):self.role(role)
        cfg=json.loads((self.root/'fusion-storage/run/cognitive-owner.json').read_text())
        self.assertEqual(cfg['actors'],{'A':'A','B':'B'})
        self.assertEqual(cfg['storage_layout'],'preview-shared-feed/1')
        self.assertEqual(cfg['backend_layout'],'detta-opaque-coordinate-partitions/1')

    def test_bounds_and_live_mode_refuse_before_configuration(self):
        self.settings['preview']['model_boundary']='LIVE'
        with self.assertRaises(ContractError):self.role('fusion-model')
        self.settings['preview']['model_boundary']='RECORDED_FIXTURE'
        self.settings['preview']['limits']['inputs']=33
        with self.assertRaises(ContractError):self.role('omega-agent')

    def test_memory_owner_ports_and_independent_agent_views(self):
        p=self.settings['preview'];p['memory']=dict(enabled=True,corpus='generated-preview-deployment')
        for role in ('fusion-search','fusion-embedding'):
            self.settings['peers'][role]=role+'.omega-ref-preview-test.svc.cluster.local'
            (self.secrets/(role+'-token')).write_text('generated-secret-for-'+role)
        for name in ('indexer-token','storage-source-token'):(self.secrets/name).write_text('x'*40)
        # The actual mounted A token must match the inherited S01 caller grant.
        (self.secrets/'caller-A-token').write_bytes((self.secrets/'caller-token').read_bytes())
        for a in p['agents'].values():a['tools']+=['remember','query']
        for role in ('fusion-storage','fusion-search','omega-agent','omega-agent-b'):
            _,cfg,state,run=self.role(role)
            if role.startswith('omega-agent'):
                sid=p['agents'][role]['sessions'][0]
                app=json.loads((run/'sessions'/sid/'application.json').read_text())
                self.assertEqual(app['preview']['base'],'controlled-native-loop/5')
                self.assertEqual(configuration(app['preview']).tools['query'].profile,'semantic-active-memory-view/1')
                self.assertIn('memory_atoms_config',app)
                self.assertEqual(json.loads(Path(app['model_config']).read_text())['profile'],'omega-recorded-native-text/2')
                self.assertFalse((run/'sessions'/sid/'memory-read.json').exists())
            else:
                self.assertEqual(cfg['active_memory']['scope'],p['scope'])
                self.assertEqual(cfg['memory_append']['writers'],['A','B'])
                if role=='fusion-search':self.assertNotIn('detta_binary',json.dumps(cfg))
                if role=='fusion-storage':
                    layout=json.loads((run/'cognitive-owner.json').read_text())['backend_layout']
                    self.assertEqual(cfg['memory_append']['backend_layout'],layout)
                    self.assertEqual(cfg['memory_read']['backend_layout'],layout)

    def test_original_chart_and_opt_in_service_dns_render(self):
        helm='helm'
        baseline=subprocess.check_output([helm,'template','omega',str(ROOT/'deploy/helm/omega-fusion'),'-n','omega-ref-preview-test'],text=True)
        self.assertNotIn('omega-single-node-developer-preview/1',baseline)
        values=self.root/'values.json'
        values.write_bytes(canonical(dict(preview=self.settings['preview'],networkPolicy={'enabled':True})))
        rendered=subprocess.check_output([helm,'template','omega',str(ROOT/'deploy/helm/omega-fusion'),'-n','omega-ref-preview-test','-f',str(values)],text=True)
        self.assertIn('omega-single-node-developer-preview/1',rendered)
        self.assertIn('scheme: HTTPS',rendered)
        self.assertNotIn('hostPath:',rendered)
        self.assertNotIn('claimName: state-fusion-storage-0',rendered)
        self.assertIn('persistentVolumeClaimRetentionPolicy: {whenDeleted: Retain, whenScaled: Retain}',rendered)
        self.assertIn('fsGroupChangePolicy: OnRootMismatch', rendered)


if __name__=='__main__':unittest.main()
