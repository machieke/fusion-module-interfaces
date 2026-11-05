"""Installed tooling without repository imports, credentials or model assets."""
import json,os,subprocess,sys,tempfile,unittest,venv
from pathlib import Path
from sdk.build import build
from fusion.contracts import digest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


class QualifierObservers(unittest.TestCase):
    def test_fault_retirement_keeps_required_empty_selection_and_owner_state(self):
        import copy,yaml
        from examples.pilot_faults import PilotRecovery
        from integration.single_node.pilot_values import generate
        images=dict(source_export_verification='PASS',source_manifest_sha256='a'*64,images=[
            dict(kind=k,repository='synthetic/'+k,local_tag='synthetic/'+k+':test',
                 manifest_digest='sha256:'+'b'*64) for k in ('base','caller','embedding')])
        original=generate(images,'synthetic-retirement','omega-ref-pilot-retirement')
        original['testFaultsEnabled']=True
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);values=root/'values.yaml';marker=root/'pause.json';journal=root/'fixture-journal'
            marker.write_text('{"stage":"after_task_payload_capture"}')
            journal.write_bytes(b'fixture spent reservation and retained result')
            retained={p.name:p.read_bytes() for p in (marker,journal)}
            def render():
                return subprocess.run(['helm','template','omega',str(ROOT/'deploy/helm/omega-fusion'),
                    '--namespace','omega-ref-pilot-retirement','-f',str(values)],
                    capture_output=True,text=True,timeout=30)
            # Reproduce the actual rejected shape, not a weakened schema.
            bad=copy.deepcopy(original);bad['components']['omega-agent-b']['config'].pop('test')
            values.write_text(yaml.safe_dump(bad));rejected=render()
            self.assertNotEqual(rejected.returncode,0)
            self.assertIn("missing property 'test'",rejected.stderr)
            for role in ('omega-agent','omega-agent-b','fusion-storage'):
                with self.subTest(role=role):
                    fault=PilotRecovery.__new__(PilotRecovery);fault.values=copy.deepcopy(original)
                    fault.values['components'][role].setdefault('config',{})['test']={'pause_at':'after_task_payload_capture'}
                    expected=copy.deepcopy(fault.values);expected['components'][role]['config']['test']={}
                    fault.values_path=values;fault.chart=str(ROOT/'deploy/helm/omega-fusion');fault.pod=lambda _: 'fixture-pod'
                    class Operator:
                        kubeconfig='fixture';context='fixture';namespace='omega-ref-pilot-retirement'
                        def command(self,*args,**kwargs):
                            result=render()
                            if result.returncode:raise RuntimeError(result.stderr)
                    fault.op=Operator();result=fault.disarm(role)
                    self.assertTrue(result['marker_retained'])
                    self.assertEqual(fault.values,expected)
                    self.assertEqual(yaml.safe_load(values.read_bytes()),expected)
                    self.assertEqual({p.name:p.read_bytes() for p in (marker,journal)},retained)

    def test_fault_export_preserves_actual_receipts_and_excludes_duplicate_replay(self):
        from examples.pilot_faults import joined_native
        from integration.single_node.pilot_evidence import native_inputs
        def row(identity,state='complete'):
            accepted=dict(id=identity,session='s',accepted=10,deadline=20,assignment='synthetic-task')
            observed=dict(id=identity,accepted=10,deadline=20,state=state,
                payload=dict(assignment='synthetic-task',text='pin exact '+identity),
                result=dict(projection='actual captured bytes',occurrences=['owned-occurrence']) if state=='complete' else None)
            return dict(role='omega-agent',session='s',identity=identity,command='pin exact '+identity,
                accepted=accepted,observed=observed)
        ordinary=row('ordinary');recovered=row('recovered');terminal=row('terminal','cancelled-before-start')
        report=dict(source_manifest_sha256='a'*64,cases=[dict(caller='omega-agent',command=recovered['command'],
            accepted=recovered['accepted'],observed=recovered['observed'],duplicate_receipt=recovered['accepted'])],
            terminal_requests=[dict(command=terminal['command'],accepted=terminal['accepted'])],terminal_inputs=[terminal['observed']])
        exported=joined_native(dict(inputs=[ordinary]),report);counts=native_inputs(exported)
        self.assertEqual(counts['operator_inputs'],3);self.assertEqual(counts['captured_inputs'],2)
        self.assertEqual(exported['inputs'][1]['observed'],recovered['observed'])
        self.assertEqual(exported['inputs'][2]['accepted'],terminal['accepted'])
        self.assertFalse(exported['internal_deliveries_in_operator_count'])
        # A conflicting overlap must not silently inflate or deduplicate counts.
        from fusion.contracts import ContractError
        with self.assertRaisesRegex(ContractError,'CONFLICT'):joined_native(dict(inputs=[recovered]),report)

    def test_fault_export_preserves_uncertain_acceptance_and_unobserved_failures(self):
        from examples.pilot_faults import joined_native
        from integration.single_node.pilot_evidence import native_inputs
        failure=dict(code='NOT_AVAILABLE')
        report=dict(source_manifest_sha256='a'*64,cases=[dict(caller='omega-agent',command='pin unknown response',
            status='FAILED',failure=failure),dict(caller='omega-agent',command='pin accepted uncertain',status='FAILED',
            failure=failure,accepted=dict(id='actual',session='s',accepted=1,deadline=20,assignment='synthetic-task'))])
        exported=joined_native(dict(inputs=[]),report)
        self.assertEqual(native_inputs(exported)['operator_inputs'],1)
        self.assertEqual(exported['inputs'][0]['failure'],failure)
        self.assertIsNone(exported['inputs'][0]['observed']);self.assertEqual(len(report['cases']),2)

    def test_uncertain_worker_is_not_claimed_as_native_completion(self):
        from examples.pilot_faults import check_fenced
        accepted=dict(id='original',accepted=10,deadline=20)
        observed=dict(**accepted,state='needs-reconciliation',result=None)
        control=dict(unresolved_assignments=1,current=dict(state='uncertain'))
        value=check_fenced(accepted,observed,control,[dict(attempts=1)],[dict(attempts=1)],
                           [dict(reserved=1)],[dict(reserved=1)])
        self.assertEqual(value['safety'],'PASS');self.assertEqual(value['native_completion'],'NOT_COMPLETED')

    def test_uncertain_oracle_rejects_manufactured_completion_retiming_or_refund(self):
        from examples.pilot_faults import check_fenced
        from fusion.contracts import ContractError
        accepted=dict(id='original',accepted=10,deadline=20)
        observed=dict(**accepted,state='dispatched',result=None)
        control=dict(unresolved_assignments=1,current=dict(state='uncertain'))
        candidates=[(dict(observed,state='complete',result=dict(projection='invented')),control,[1],[1]),
                    (dict(observed,deadline=21),control,[1],[1]),
                    (observed,dict(control,current=dict(state='running')),[1],[1]),
                    (observed,control,[1],[0])]
        for row,worker,before,after in candidates:
            with self.subTest(row=row,worker=worker,after=after):
                with self.assertRaisesRegex(ContractError,'CONFLICT'):
                    check_fenced(accepted,row,worker,before,after,[dict(reserved=1)],[dict(reserved=1)])
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            check_fenced(accepted,observed,control,[1],[1],[dict(reserved=1)],[dict(reserved=0)])

    def test_close_wait_observes_worker_exit_and_applies_only_once(self):
        from examples.pilot_endurance import cleanup
        calls=[]
        class Owner:
            def k(self,*args,**kw):
                request=json.loads(kw['data']);operation=request['operation'];calls.append(operation)
                if len(calls)==1:raise RuntimeError('NOT_AVAILABLE')
                if operation=='inventory':return json.dumps(dict(selection=dict(overlays=[],materializations=[],duplicate_startup=True)))
                if operation=='plan':return json.dumps(dict(fixture='selected-plan'))
                return json.dumps(dict(fixture='committed-receipt'))
        with patch('examples.pilot_endurance.time.monotonic',return_value=10),patch('examples.pilot_endurance.time.sleep'):
            result=cleanup(Owner(),'omega-agent','session',100)
        self.assertEqual(calls,['inventory','inventory','plan','apply','observe'])
        self.assertEqual(result['apply_calls'],1);self.assertTrue(result['replay_exact'])

    def test_empty_inventory_is_an_observation_without_a_cleanup_effect(self):
        from examples.pilot_endurance import cleanup
        from unittest.mock import Mock
        owner=Mock();owner.k.return_value=json.dumps(dict(selection=dict(overlays=[],materializations=[],duplicate_startup=False)))
        with patch('examples.pilot_endurance.time.monotonic',return_value=10):result=cleanup(owner,'omega-agent','session',100)
        self.assertEqual(result['status'],'NO_ELIGIBLE_DERIVED_CANDIDATE');self.assertEqual(owner.k.call_count,1)

    def test_authority_failure_is_not_polled_or_converted_to_an_empty_inventory(self):
        from examples.pilot_endurance import cleanup
        from unittest.mock import Mock
        owner=Mock();owner.k.side_effect=RuntimeError('UNAUTHORIZED')
        with patch('examples.pilot_endurance.time.monotonic',return_value=10):
            with self.assertRaisesRegex(RuntimeError,'UNAUTHORIZED'):cleanup(owner,'omega-agent','session',100)
        self.assertEqual(owner.k.call_count,1)

    def test_owned_belief_comparison_is_bound_to_target_not_candidate_order(self):
        from examples.pilot_endurance import target_belief
        from fusion.contracts import ContractError
        target=dict(claim={'fixture':'target'},context='ctx',truth={'strength':'0.8'},revision=3)
        other=dict(claim={'fixture':'other'},context='ctx',truth={'strength':'0.4'},revision=1)
        current=dict(retained=dict(view=dict(handles={'uuid':dict(envelope=dict(handle='selected'))},
            beliefs=[dict(uuid='uuid',claim=target['claim'],context='ctx')])),beliefs=[other,target])
        self.assertEqual(target_belief(current,'selected'),target)
        current['beliefs'].reverse();self.assertEqual(target_belief(current,'selected'),target)
        current['beliefs'].append(target)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):target_belief(current,'selected')


class Installed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='omega-pilot-operator-');cls.root=Path(cls.tmp.name)
        cls.result=build(cls.root/'wheels',pilot=True);venv.create(cls.root/'venv',with_pip=True)
        cls.python=cls.root/'venv/bin/python';cls.env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME','KUBECONFIG')}
        cls.env.update(PYTHONNOUSERSITE='1',PIP_NO_INDEX='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
        wheels=[cls.root/'wheels'/cls.result[k]['file'] for k in ('client','operator')]
        # Optional artifact/install extra from the repository's historical
        # pinned operator wheel inventory. No download or new resolver choice.
        pin=next(x for x in json.loads((ROOT/'sdk/operator-wheel-inputs.json').read_bytes())['files'] if x['file'].startswith('pyyaml-'))
        candidate=ROOT/'artifacts/integrated-service/sdk-dev14'/pin['file']
        if candidate.is_file():
            assert digest(candidate.read_bytes())==pin['sha256'];wheels.append(candidate)
        else:raise unittest.SkipTest('Pinned optional PyYAML wheel unavailable; installed gate not executed')
        subprocess.run([str(cls.python),'-I','-m','pip','install','--no-index','--no-deps',*map(str,wheels)],cwd=cls.root,env=cls.env,check=True,capture_output=True)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def invoke(self,*args):
        return subprocess.run([str(self.python),'-I',*args],cwd=self.root,env=self.env,text=True,capture_output=True,timeout=20)
    def test_every_installed_tool_loads_without_checkout_or_runtime_assets(self):
        from integration.single_node.pilot_cli import COMMANDS
        for command in COMMANDS:
            with self.subTest(command=command):
                result=self.invoke('-m','integration.single_node.pilot_cli',command,'--help')
                self.assertEqual(result.returncode,0,result.stderr)
        result=self.invoke('-c',"import importlib.util;assert all(importlib.util.find_spec(x) is None for x in ('torch','transformers','chromadb'));print('NO_INFERENCE_LIBRARIES')")
        self.assertEqual(result.returncode,0,result.stderr)
    def test_evidence_reader_does_not_import_native_application(self):
        result=self.invoke('-c',"import sys;from integration.single_node.pilot_evidence import PROFILE;assert not any(x in sys.modules for x in ('fusion.preview_application','fusion.model_service','integration.single_node.server'));print(PROFILE)")
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'operator-pilot-evidence/1')
    def test_extension_version_and_exact_source_manifest(self):
        result=self.invoke('-c',"import json,hashlib;from pathlib import Path;from importlib.metadata import distribution;d=distribution('fusion-preview-operator');assert d.version=='0.4.0';assert 'fusion-pilot' in {x.name for x in d.entry_points};v=json.loads(d.read_text('source-manifest.json'));assert all(hashlib.sha256(Path(d.locate_file(p)).read_bytes()).hexdigest()==r['sha256'] for p,r in v['sources'].items());print('EXACT')")
        self.assertEqual(result.returncode,0,result.stderr)
    def test_handover_uses_installed_secret_recipe_without_checkout(self):
        result=self.invoke('-c',"import subprocess,sys;from examples.pilot_handover import secret_command;q=secret_command();assert q[:3]==[sys.executable,'-I','-c'];r=subprocess.run([*q,'--help'],cwd='/',capture_output=True,text=True,timeout=15);assert r.returncode==0,r.stderr;assert '--preview-values' in r.stdout;print('INSTALLED_SECRET_RECIPE_NO_CLUSTER_CONTACT')")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stdout.strip(),'INSTALLED_SECRET_RECIPE_NO_CLUSTER_CONTACT')
