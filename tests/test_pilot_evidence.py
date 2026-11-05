"""Verifier parser fixtures only; no real native/provider execution is claimed.

All intentional damaged bundles are fresh synthetic files. No runtime service,
model, chain endpoint, private journal or protected deployment is contacted.
"""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError,canonical,digest
from integration.single_node.pilot_evidence import verify,PROFILE,PLAN,unittest_log,go_log,native_inputs,chain_export

class Evidence(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.m=dict(profile=PROFILE,release_status='PARTIAL',candidate=dict(source={'fusion/example.py':'a'*64},
            source_manifest_sha256=digest(canonical({'fusion/example.py':'a'*64})),images={'caller':'sha256:'+'b'*64}),distribution=None,
            artifacts=[],runs=[],scenario_plan='plan',gates={k:dict(status='NOT_RUN',runs=[],scenarios=[],reason='Deployment not executed by parser fixture') for k in 'ABCDEFGH'},
            packages={'V%02d'%n:dict(status='NOT_RUN',gates=[],reason='Not exercised by parser fixture') for n in range(1,41)},
            counts=dict(authored_test_methods=2,test_method_invocations=2,test_runs=1,test_subscenarios=0,test_skipped_invocations=0,
                workflow_scenarios=1,native_operator_inputs=0,native_accepted_inputs=0,observed_internal_native_inputs=0,native_captures=0,additional_live_generations=0),historical=[],
            authorization=dict(additional_live_generations=0,live_reservations=0,live_captures=0,generative_runtime_contact=False),
            limitations=['Synthetic verifier parser fixtures; no runtime/provider result'])
        self.file('log','test.log',b'test_one (tests.sample.Check.test_one) ... ok\ntest_two (tests.sample.Check.test_two) ... ok\n\nRan 2 tests in 0.001s\n\nOK\n')
        self.file('primary','primary.json',dict(status='PASS',additional_live_generations=0,measured=dict(value=3),provider=dict(fixture=True)))
        self.file('plan','plan.json',dict(profile=PLAN,scenarios=[dict(id='measured-value',run='static',assertions=[dict(
            artifact='primary',pointer='/measured/value',operator='equals',expected=3)])]))
        self.m['runs']=[self.run_row('tests','unittest-verbose','log'),self.run_row('static','primary-json','primary')]
        self.m['gates']['unit']=dict(status='PASS',runs=['tests','static'],scenarios=['measured-value'],reason='')
        self.m['packages']['V38']=dict(status='PASS',gates=['unit'],reason='')
    def run_row(self,identity,kind,primary):
        return dict(id=identity,kind=kind,phase='candidate',status='PASS',classification='STATIC',primary=primary,native=None,internal=[],chain=None,
            source_manifest_sha256=self.m['candidate']['source_manifest_sha256'],images={},image_binding=None,components={},depends_on=[],reason='')
    def file(self,key,path,value):
        raw=value if type(value) is bytes else canonical(value);(self.root/path).write_bytes(raw)
        row=dict(id=key,path=path,sha256=digest(raw),bytes=len(raw),visibility='approved-public')
        self.m['artifacts']=[x for x in self.m['artifacts'] if x['id']!=key]+[row]
    def check(self):
        raw=canonical(self.m);path=self.root/'evidence.json';path.write_bytes(raw);path.with_suffix('.sha256').write_text(digest(raw)+'\n');return verify(path)
    def test_partial_candidate_accepted_without_turning_unrun_into_pass(self):
        result=self.check();self.assertEqual(result['status'],'VERIFIED_PARTIAL')
        self.assertFalse(result['distribution_verified']);self.assertEqual(result['counts'],self.m['counts'])
        self.assertEqual(len(result['authored_test_methods']),2);self.assertTrue(result['exceptions'])
    def test_no_service_or_native_application_import_for_static_packet(self):
        with patch('subprocess.run',side_effect=AssertionError('process prohibited')), \
             patch('socket.socket',side_effect=AssertionError('network prohibited')):
            self.assertEqual(self.check()['additional_live_generations'],0)
    def test_primary_failure_cannot_hide_behind_summary(self):
        self.file('primary','primary.json',dict(status='FAIL',additional_live_generations=0,measured=dict(value=3)))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_primary_failure_is_retained_as_known_negative_in_partial_packet(self):
        self.file('primary','primary.json',dict(status='FAIL',additional_live_generations=0,measured=dict(value=2)))
        self.m['runs'][1].update(status='FAIL',reason='Executed mismatch')
        self.m['gates']['unit'].update(status='FAIL',reason='Actual report failed')
        self.m['packages']['V38'].update(status='PARTIAL',reason='Known negative retained')
        value=self.check();self.assertEqual(value['unsuccessful_runs'],[dict(run='static',status='FAIL',phase='candidate')])
    def test_literal_restore_failed_spelling_remains_a_negative_without_rewriting(self):
        raw=canonical(dict(status='FAILED',additional_live_generations=0,measured=dict(value=2)))
        self.file('primary','primary.json',raw)
        self.m['runs'][1].update(status='FAIL',reason='Actual restore observer returned FAILED')
        self.m['gates']['unit'].update(status='FAIL',reason='Actual report failed')
        self.m['packages']['V38'].update(status='PARTIAL',reason='Known negative retained')
        value=self.check();self.assertEqual(value['unsuccessful_runs'],[dict(run='static',status='FAIL',phase='candidate')])
        self.assertEqual((self.root/'primary.json').read_bytes(),raw)
        self.m['runs'][1]['status']='PASS'
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_nonempty_and_nonselfasserted_acceptance_required(self):
        for field in ('runs','scenarios'):
            original=self.m['gates']['unit'][field];self.m['gates']['unit'][field]=[]
            with self.assertRaises(ContractError):self.check()
            self.m['gates']['unit'][field]=original
        self.file('plan','plan.json',dict(profile=PLAN,scenarios=[dict(id='invented',run='static',assertions=[dict(
            artifact='plan',pointer='/profile',operator='equals',expected=PLAN)])]))
        with self.assertRaises(ContractError):self.check()
    def test_source_counts_and_historical_phase_cannot_be_inflated(self):
        for mutation in ('source','method_count','run_duplicate','scenario_duplicate','historical'):
            with self.subTest(mutation=mutation):
                original=copy.deepcopy(self.m)
                if mutation=='source':self.m['runs'][0]['source_manifest_sha256']='c'*64
                elif mutation=='method_count':self.m['counts']['authored_test_methods']=3
                elif mutation=='run_duplicate':self.m['runs'].append(copy.deepcopy(self.m['runs'][0]))
                elif mutation=='scenario_duplicate':
                    plan=json.loads((self.root/'plan.json').read_bytes());plan['scenarios']*=2;self.file('plan','plan.json',plan)
                else:self.m['runs'][0]['phase']='historical'
                with self.assertRaises(ContractError):self.check()
                self.m=original
                self.file('plan','plan.json',dict(profile=PLAN,scenarios=[dict(id='measured-value',run='static',assertions=[dict(
                    artifact='primary',pointer='/measured/value',operator='equals',expected=3)])]))
    def test_fixture_cannot_supply_real_provider_claim(self):
        run=self.m['runs'][1];run.update(classification='REAL_PROVIDER',images=self.m['candidate']['images'],
            image_binding=dict(artifact='primary',pointer='/images'),components=dict(storage=dict(kind='REAL',evidence=[dict(artifact='primary',pointer='/provider')])))
        self.file('primary','primary.json',dict(status='PASS',additional_live_generations=0,measured=dict(value=3),
            provider=dict(provider='contract-fixture-files/1'),images=self.m['candidate']['images']))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_actual_selected_images_are_checked_against_candidate(self):
        run=self.m['runs'][1];run.update(classification='REAL_PROVIDER',images=self.m['candidate']['images'],
            image_binding=dict(artifact='primary',pointer='/images'),components=dict(provider=dict(kind='REAL',evidence=[dict(artifact='primary',pointer='/provider')])) )
        self.file('primary','primary.json',dict(status='PASS',additional_live_generations=0,measured=dict(value=3),
            provider=dict(provider='typed-reference-provider',receipt='observed'),images={'caller':'sha256:'+'c'*64}))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def role_case(self):
        selected=self.m['candidate'];pin=selected['images']['caller']
        plan=dict(profile='omega-single-node-placement/1',source_manifest_sha256=selected['source_manifest_sha256'],
            additional_live_generations=0,images=dict(source_export_verification='PASS',source_manifest_sha256=selected['source_manifest_sha256'],
                images=[dict(kind='caller',repository='fixture/caller',manifest_digest=pin)]),
            values=dict(image=dict(repository='fixture/caller',digest=pin),components={'omega-agent':{}},preview={}),
            graph=dict(nodes={'omega-agent':dict(image='fixture/caller@'+pin)}))
        self.file('placement','placement.json',plan)
        selected['image_roles']={'omega-agent':dict(kind='caller',plan='placement')}
        observed={'omega-agent':'fixture/caller@'+pin}
        self.m['runs'][1].update(classification='REAL_PROVIDER',images=observed,
            image_binding=dict(artifact='primary',pointer='/images'),
            components=dict(provider=dict(kind='REAL',evidence=[dict(artifact='primary',pointer='/provider')])) )
        self.file('primary','primary.json',dict(status='PASS',additional_live_generations=0,measured=dict(value=3),
            provider=dict(provider='typed-reference-provider',receipt='observed'),images=observed))
        return plan
    def test_role_image_alias_requires_exact_source_bound_placement(self):
        self.role_case();value=self.check()
        self.assertEqual(value['image_role_bindings']['omega-agent']['kind'],'caller')
        self.assertEqual(value['image_role_bindings']['omega-agent']['source_manifest_sha256'],self.m['candidate']['source_manifest_sha256'])
        self.m['candidate'].pop('image_roles')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_wrong_role_digest_and_stale_placement_refuse(self):
        self.role_case();original=copy.deepcopy(self.m)
        for mode in ('role','digest','source','image-source','graph','selection'):
            with self.subTest(mode=mode):
                self.m=copy.deepcopy(original);plan=json.loads((self.root/'placement.json').read_bytes())
                # Restore the unmodified fixture for each independently damaged plan.
                plan=self.role_case()
                if mode=='role':self.m['candidate']['image_roles']['omega-agent']['kind']='base'
                elif mode=='digest':plan['images']['images'][0]['manifest_digest']='sha256:'+'c'*64
                elif mode=='source':plan['source_manifest_sha256']='c'*64
                elif mode=='image-source':plan['images']['images'][0]['source_manifest_sha256']='c'*64
                elif mode=='graph':plan['graph']['nodes']['omega-agent']['image']='fixture/caller@sha256:'+'c'*64
                else:plan['values']['components']={}
                self.file('placement','placement.json',plan)
                with self.assertRaises(ContractError):self.check()
    def test_independent_go_role_cannot_borrow_python_source_binding(self):
        from integration.single_node.pilot_evidence import Packet,image_role_bindings
        plan=self.role_case();kind='inspect-go';selected=self.m['candidate'];selected['images'][kind]='sha256:'+'d'*64
        selected['image_roles']={'fusion-inspect-go':dict(kind=kind,plan='placement')}
        source='e'*64;artifact='f'*64
        plan['images']['images']=[dict(kind=kind,repository='fixture/go',manifest_digest=selected['images'][kind],
            source_manifest_sha256=source,source_kind='independent-go',reference_artifact_sha256=artifact)]
        plan['values']=dict(image=dict(repository='fixture/go',digest=selected['images'][kind]),components={'fusion-inspect-go':{}},preview={})
        plan['graph']['nodes']={'fusion-inspect-go':dict(image='fixture/go@'+selected['images'][kind])};self.file('placement','placement.json',plan)
        raw=canonical(self.m);path=self.root/'evidence.json';path.write_bytes(raw);path.with_suffix('.sha256').write_text(digest(raw)+'\n')
        packet=Packet(path);packet.register(self.m['artifacts'])
        distribution=dict(images={kind:dict(source_kind='independent-go',source_manifest_sha256=source,
            manifest=selected['images'][kind],manifest_sha256=artifact)})
        bound=image_role_bindings(packet,selected,selected['images'],distribution)
        self.assertEqual(bound['fusion-inspect-go']['source_manifest_sha256'],source)
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):image_role_bindings(packet,selected,selected['images'],None)
        distribution['images'][kind]['source_manifest_sha256']=selected['source_manifest_sha256']
        with self.assertRaisesRegex(ContractError,'CONFLICT'):image_role_bindings(packet,selected,selected['images'],distribution)
    def test_live_counts_bool_and_hidden_nested_generation_rejected(self):
        for value in (True,1,-1,'0',None):
            with self.subTest(value=value):
                self.m['authorization']['additional_live_generations']=value
                with self.assertRaises(ContractError):self.check()
        self.m['authorization']['additional_live_generations']=0
        self.file('primary','primary.json',dict(status='PASS',measured=dict(value=3,live_reservations=1)))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.check()
    def test_missing_tampered_path_and_circular_references_rejected(self):
        original=(self.root/'test.log').read_bytes();(self.root/'test.log').unlink()
        with self.assertRaises(ContractError):self.check()
        (self.root/'test.log').write_bytes(original+b'changed')
        with self.assertRaises(ContractError):self.check()
        (self.root/'test.log').write_bytes(original)
        self.m['runs'][0]['depends_on']=['static'];self.m['runs'][1]['depends_on']=['tests']
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
        self.m['runs'][0]['depends_on']=[];self.m['runs'][1]['depends_on']=[]
        self.m['artifacts'][0]['path']='../outside'
        with self.assertRaises(ContractError):self.check()
    def test_unavailable_private_is_not_a_negative_or_a_pass(self):
        self.m['artifacts'].append(dict(id='private',path='withheld.json',sha256=None,bytes=None,visibility='unavailable-private'))
        run=self.run_row('private-review','primary-json',None);run.update(status='UNAVAILABLE_PRIVATE',reason='Not exported by owner')
        self.m['runs'].append(run);out=self.check()
        self.assertEqual(out['unavailable_private_evidence'],['private']);self.assertEqual(out['unsuccessful_runs'],[])
        self.m['gates']['unit']['runs'].append('private-review')
        with self.assertRaises(ContractError):self.check()
    def test_source_bound_discovery_alias_deduplicates_only_authored_identity(self):
        self.file('test-source','source.py',b'class Check:\n def test_one(self): pass\n def test_two(self): pass\n')
        self.m['test_sources']={'tests/test_sample.py':'test-source'}
        self.file('log','test.log',b'test_one (tests.test_sample.Check.test_one) ... ok\ntest_two (tests.test_sample.Check.test_two) ... ok\n\nRan 2 tests in 0.001s\n\nOK\n')
        self.file('log2','discover.log',b'test_one (test_sample.Check.test_one) ... ok\ntest_two (test_sample.Check.test_two) ... ok\n\nRan 2 tests in 0.001s\n\nOK\n')
        self.m['runs'].append(self.run_row('discovery','unittest-verbose','log2'))
        self.m['counts'].update(test_method_invocations=4,test_runs=2)
        result=self.check()
        self.assertEqual(result['authored_test_methods'],['tests/test_sample.py::Check.test_one','tests/test_sample.py::Check.test_two'])
        self.assertEqual(len(result['raw_authored_test_methods']),4)
        self.assertEqual(len(result['test_identity_bindings']),4)
        self.assertEqual(result['counts']['test_method_invocations'],4)
        self.m.pop('test_sources');self.m['counts']['authored_test_methods']=4
        self.assertEqual(len(self.check()['authored_test_methods']),4)
    def test_test_source_must_be_real_bound_class_not_blind_alias(self):
        self.file('test-source','source.py',b'class Other:\n pass\n')
        self.m['test_sources']={'tests/test_sample.py':'test-source'}
        self.file('log','test.log',b'test_one (tests.test_sample.Check.test_one) ... ok\ntest_two (test_sample.Check.test_two) ... ok\n\nRan 2 tests in 0.001s\n\nOK\n')
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.check()
        self.m['test_sources']={'tests/test_sample.py':'test-source','tests/tests/test_sample.py':'test-source'}
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_unavailable_private_metadata_cannot_export_identifying_digest(self):
        self.m['artifacts'].append(dict(id='withheld',path='withheld.json',sha256='d'*64,bytes=100,visibility='unavailable-private'))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.check()

    def test_old_index_pin_detects_overwritten_historical_identity(self):
        original=next(x['sha256'] for x in self.m['artifacts'] if x['id']=='primary')
        self.file('old-index','old.json',dict(original_sha256=original))
        self.m['historical']=[dict(artifact='primary',index='old-index',pointer='/original_sha256')]
        self.check();self.file('primary','primary.json',dict(status='PASS',measured=dict(value=3),new_label='rewritten'))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_go_methods_subscenarios_runs_and_skips_stay_distinct(self):
        rows=[]
        for test in ('TestOne','TestOne/case','TestHelper'):
            rows += [dict(Action='run',Package='example/port',Test=test),dict(Action='skip' if test=='TestHelper' else 'pass',Package='example/port',Test=test)]
        rows.append(dict(Action='pass',Package='example/port'))
        report=go_log(b'\n'.join(canonical(x) for x in rows))
        self.assertEqual(report['methods'],['example/port.TestOne']);self.assertEqual(report['invocations'],2)
        self.assertEqual(report['test_scenarios'],['example/port.TestOne/case']);self.assertEqual(report['skips'],1)
        rows.append(rows[1])
        with self.assertRaises(ContractError):go_log(b'\n'.join(canonical(x) for x in rows))

    def test_candidate_go_log_retains_verified_independent_source_identity(self):
        source='e'*64;image='sha256:'+'d'*64
        self.m['candidate']['images']['inspect-go']=image
        self.file('distribution','distribution.json',dict(tested_source=self.m['candidate']['source']))
        self.m['distribution']='distribution'
        verified=dict(images=dict(caller=dict(manifest=self.m['candidate']['images']['caller']),
            **{'inspect-go':dict(manifest=image,source_kind='independent-go',source_manifest_sha256=source,manifest_sha256='f'*64)}))
        self.file('go-log','go.jsonl',b'\n'.join(canonical(x) for x in [
            dict(Action='run',Package='example/provider',Test='TestExact'),
            dict(Action='pass',Package='example/provider',Test='TestExact'),dict(Action='pass',Package='example/provider')]))
        run=self.run_row('go','go-test-json','go-log');run.update(source_manifest_sha256=source,classification='FIXTURE')
        self.m['runs'].append(run);self.m['counts'].update(authored_test_methods=3,test_method_invocations=3,test_runs=2)
        with patch('integration.single_node.pilot_evidence.verify_distribution',return_value=verified):
            result=self.check()
            self.assertEqual(result['independent_test_sources']['go'],dict(kind='inspect-go',
                source_manifest_sha256=source,image=image,reference_artifact_sha256='f'*64))
            run['source_manifest_sha256']='c'*64
            with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
            run['source_manifest_sha256']=source;verified['images']['inspect-go']['source_kind']='unverified-go'
            with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
            verified['images']['inspect-go']['source_kind']='independent-go'
            self.m['distribution']=None
            with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
        self.m['distribution']='distribution'
        with patch('integration.single_node.pilot_evidence.verify_distribution',side_effect=ContractError('CONFLICT')):
            with self.assertRaisesRegex(ContractError,'CONFLICT'):self.check()
    def test_unittest_primary_failure_and_duplicate_invocation_union(self):
        log=b'test_one (tests.sample.Check.test_one) ... ok\ntest_one (tests.sample.Check.test_one) ... FAIL\nRan 2 tests in 0.001s\nFAILED (failures=1)\n'
        value=unittest_log(log);self.assertEqual(value['status'],'FAIL');self.assertEqual(len(value['methods']),1);self.assertEqual(value['invocations'],2)

    def test_unittest_intervening_real_diagnostic_shapes_preserve_exact_identity(self):
        # These are literal diagnostic forms observed in final-checks07. The
        # parser test itself is a fixture, not another execution of those tests.
        log=(b'test_process_kill_retains_real_commit_hint_and_original_acceptance (tests.test_pilot_subscriptions.SubscriptionTests.test_process_kill_retains_real_commit_hint_and_original_acceptance) ... '
             b'/home/purplezky/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/lib/python3.12/multiprocessing/popen_fork.py:66: DeprecationWarning: This process (pid=3486105) is multi-threaded, use of fork() may lead to deadlocks in the child.\n'
             b'  self.pid = os.fork()\nok\n'
             b'test_real_sigkill_source_and_publication_capture_recover_without_duplicate_artifact (test_phase3_projection.ExactProjection.test_real_sigkill_source_and_publication_capture_recover_without_duplicate_artifact) ... Verified image configs and registered immutable digest references.\nok\n'
             b'\nRan 2 tests in 0.001s\n\nOK\n')
        value=unittest_log(log);self.assertEqual(value['status'],'PASS');self.assertEqual(value['invocations'],2)
        self.assertEqual(value['methods'],[
            'test_phase3_projection.ExactProjection.test_real_sigkill_source_and_publication_capture_recover_without_duplicate_artifact',
            'tests.test_pilot_subscriptions.SubscriptionTests.test_process_kill_retains_real_commit_hint_and_original_acceptance'])
        failure=log.replace(b'  self.pid = os.fork()\nok\n',b'  self.pid = os.fork()\nFAIL\n').replace(b'\nOK\n',b'\nFAILED (failures=1)\n')
        self.assertEqual(unittest_log(failure)['status'],'FAIL')

    def test_unittest_orphan_duplicate_interleaved_missing_and_total_mismatch_refuse(self):
        first=b'test_one (tests.sample.Check.test_one) ... diagnostic\n'
        second=b'test_two (tests.sample.Check.test_two) ... ok\n'
        summary=b'Ran 1 test in 0.001s\nOK\n'
        for log in (b'ok\n'+summary,first+b'ok\nok\n'+summary,
            first+second+b'ok\nRan 2 tests in 0.001s\nOK\n',first+summary,
            first+b'ok\nRan 2 tests in 0.001s\nOK\n',first+b'not an outcome\n'):
            with self.subTest(log=log):
                with self.assertRaises(ContractError):unittest_log(log)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):
            unittest_log(first+b'large diagnostic\n'*257+b'ok\n'+summary)
    def test_native_input_identity_capture_and_original_bound_parser(self):
        # This is a DTO fixture exercising report validation, not a native run.
        accepted=dict(id='occurrence',session='session',accepted=1,deadline=10,assignment='synthetic-task')
        observed=dict(id='occurrence',accepted=1,deadline=10,state='complete',payload=dict(assignment='synthetic-task',text='query synthetic'),
            result=dict(projection='parser-fixture',occurrences=['tool-occurrence']))
        row=dict(role='omega-agent',session='session',identity='occurrence',command='query synthetic',accepted=accepted,observed=observed)
        report=dict(classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',inputs=[row])
        self.assertEqual(native_inputs(report)['captured_inputs'],1)
        observed['deadline']=11
        with self.assertRaisesRegex(ContractError,'CONFLICT'):native_inputs(report)
        observed['deadline']=10;report['inputs'].append(copy.deepcopy(row))
        with self.assertRaisesRegex(ContractError,'CONFLICT'):native_inputs(report)

    def test_chain_export_checks_same_actual_bytes_without_observing_runtime(self):
        from tests import test_phase2_chain_observer as fixtures
        fixture=fixtures.ChainObserver();fixture.setUp();self.addCleanup(fixture.doCleanups)
        trace=fixture.trace;artifact=fixture.feed.get(trace['reg']['artifact']).bytes
        result=fixture.feed.get(trace['reg']['approved']['result_ref']).bytes
        with patch('socket.socket',side_effect=AssertionError('no chain observer contact')):
            self.assertEqual(chain_export(trace,artifact,result),'PASS')
            with self.assertRaises(ContractError):chain_export(trace,artifact+b' ',result)
            with self.assertRaises(ContractError):chain_export(trace,artifact,result.replace(b'inspect_atom',b'other_action'))
            failure=dict(profile='synthetic-chain-readback/1',status='FAILED',additional_live_generations=0,error='NOT_AVAILABLE')
            self.assertEqual(chain_export(trace,artifact,result,failure),'PARTIAL')

    def chain_report_case(self):
        from tests import test_phase2_chain_observer as fixtures
        fixture=fixtures.ChainObserver();fixture.setUp();self.addCleanup(fixture.doCleanups)
        trace=fixture.trace
        self.file('chain-trace','trace.json',trace)
        self.file('chain-artifact','artifact.json',fixture.feed.get(trace['reg']['artifact']).bytes)
        self.file('chain-result','result.json',fixture.feed.get(trace['reg']['approved']['result_ref']).bytes)
        execution=dict(status='PASS',registration=trace['reg'],saved_intent=trace['saved_intent'],
            final_observation=trace['final_observation'],images=self.m['candidate']['images'],
            source_manifest_sha256=self.m['candidate']['source_manifest_sha256'],additional_live_generations=0,
            submit_reservations=1,model='RECORDED_FIXTURE')
        self.file('chain-execution','chain-execution.json',execution)
        run=self.run_row('chain','chain-trace','chain-trace')
        run.update(classification='REAL_CHAIN',images=execution['images'],
            image_binding=dict(artifact='chain-execution',pointer='/images'),
            components=dict(chain=dict(kind='REAL',evidence=[dict(artifact='chain-execution',pointer='/final_observation')]),
                model=dict(kind='FIXTURE',evidence=[dict(artifact='chain-execution',pointer='/model')])),
            chain=dict(artifact='chain-artifact',inspection_result='chain-result',readback=None,execution_report='chain-execution'))
        self.m['runs'].append(run);return trace,execution,run

    def test_chain_exact_execution_report_binds_images_without_rewriting_trace(self):
        trace,execution,run=self.chain_report_case();original=(self.root/'trace.json').read_bytes()
        self.assertEqual(self.check()['status'],'VERIFIED_PARTIAL')
        self.assertEqual((self.root/'trace.json').read_bytes(),original)
        plan=json.loads((self.root/'plan.json').read_bytes())
        plan['scenarios'].append(dict(id='one-chain-reservation',run='chain',assertions=[dict(
            artifact='chain-execution',pointer='/submit_reservations',operator='equals',expected=1)]))
        self.file('plan','plan.json',plan);self.m['counts']['workflow_scenarios']+=1
        self.check()

    def test_chain_report_wrong_trace_source_image_digest_and_status_refuse(self):
        trace,execution,run=self.chain_report_case();original=copy.deepcopy(execution)
        artifact_bytes=(self.root/'artifact.json').read_bytes()
        for mode in ('registration','intent','observation','source','image','status','artifact'):
            with self.subTest(mode=mode):
                value=copy.deepcopy(original)
                if mode=='registration':value['registration']['binding']['operation']='different-operation'
                elif mode=='intent':value['saved_intent']['deploy_id']='c'*128
                elif mode=='observation':value['final_observation']['inclusion_block']='c'*64
                elif mode=='source':value['source_manifest_sha256']='c'*64
                elif mode=='image':value['images']={'caller':'sha256:'+'c'*64}
                elif mode=='status':value['status']='FAIL'
                else:self.file('chain-artifact','artifact.json',b'wrong actual bytes')
                self.file('chain-execution','chain-execution.json',value)
                with self.assertRaises(ContractError):self.check()
        # The primary failure stays a real negative, never a trace-level pass.
        self.file('chain-artifact','artifact.json',artifact_bytes)
        value=copy.deepcopy(original);value['status']='FAIL';self.file('chain-execution','chain-execution.json',value)
        run.update(status='FAIL',reason='Later independent execution check failed')
        self.assertIn(dict(run='chain',status='FAIL',phase='candidate'),self.check()['unsuccessful_runs'])
