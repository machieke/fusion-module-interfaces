"""Preparation integration only. Every model completion is an authored fixture."""
import copy
import json
import os
from pathlib import Path
import signal
import time
import unittest

from fusion.contracts import canonical, digest
from . import retrieval_preparation as p
from .embedding_run import start, observed_finish
from .memory_composition import ROOT

OUT = Path(os.environ.get('RETRIEVAL_PREPARATION_EVIDENCE', ROOT/'artifacts/retrieval-preparation/tests'))


class RetrievalPreparation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p.verify(os.environ['FUSION_PREP_PARENT_NET'])
        OUT.mkdir(parents=True, exist_ok=True)
        cls.corpus = p.generated()
        p.write(OUT/'corpus.json', cls.corpus)

    def evidence(self, name, value):
        p.write(OUT/(name+'.json'), value)

    def capture(self, run, cfg):
        db = run.h.client['database']
        return {name:p.rows(db, name) for name in ('app_occurrences', 'app_model_calls', 'app_memory_reads',
            'app_query_vectors', 'app_query_views', 'app_priority_contexts', 'app_read_views')}

    def case(self, name, *, corpus=None, placement='local', commands=None, stage=None,
             second=False, provider=False, fault=None, rejection=None, ambiguous=False):
        run, cfg = p.setup(corpus or self.corpus)
        try:
            p.measured(run, cfg, placement=placement, responses=commands)
            ch = cfg['channel']; ch.start_bridge(); ch.start_peer()
            before = None
            if stage and not provider:
                run.app['pause_at'] = stage
                if second: run.app['pause_slot'] = 2
                run.save()
            if provider:
                owner = json.loads(cfg['policy'].read_bytes()); owner['pause_at'] = stage; p.write(cfg['policy'], owner)
                # The host's failpoint selector is read at startup. Current
                # authorization is dynamic, but this test hook deliberately is not.
                ready = cfg['completion']/'ready.json'; port = json.loads(ready.read_bytes())['port']
                run.kill(cfg['host']); ready.unlink()
                cfg['host'] = run.spawn('integration.neoclaw.retrieval_fixture',
                    ['serve', cfg['policy'], port, ready], 'paused-completion-fixture')
                run.h.wait_file(ready, cfg['host'])
            if ambiguous:
                ch.kill(ch.bridge); ch.bridge_config['pause_at'] = 'after_socket_reservation'; ch.start_bridge()
            process = start(run)
            p.wait_for(lambda:(Path(run.app['workdir'])/'embedding-ready.json').exists(), process, 45)
            ch.send(p.QUESTION)

            def interrupt():
                nonlocal process, before
                marker = cfg['completion']/'pause.json' if provider else Path(run.app['failpoint_marker'])
                p.wait_for(marker.exists, seconds=35)
                before = self.capture(run, cfg)
                run.kill(process); self.assertEqual(process.returncode, -signal.SIGKILL)
                if provider:
                    cfg['provider_before'] = p.rows(cfg['completion']/'model.sqlite', 'model_calls')
                    run.kill(cfg['host'])
                    owner = json.loads(cfg['policy'].read_bytes()); owner.pop('pause_at'); p.write(cfg['policy'], owner)
                    ready = cfg['completion']/'ready.json'; port = json.loads(ready.read_bytes())['port']; ready.unlink()
                    cfg['host'] = run.spawn('integration.neoclaw.retrieval_fixture',
                        ['serve', cfg['policy'], port, ready], 'restarted-completion-fixture')
                    run.h.wait_file(ready, cfg['host'])
                if fault: fault(run, cfg)
                run.app.pop('pause_at', None); run.save(); marker.unlink()
                process = start(run)

            if stage and not second: interrupt()
            if not (rejection and (fault or not commands or commands[0] != 'query '+p.QUERY)):
                p.wait_for(lambda:any(x['projection'] is not None for x in p.rows(run.h.client['database'], 'app_turns')),
                           process, 40)
                ch.send(p.FOLLOWUP)
                if stage and second: interrupt()
            code, status = run.finish(process)
            if rejection:
                self.assertEqual(code, 2)
                self.assertEqual(status['code'], rejection)
                self.assertFalse(any('PRIVMSG' in x.get('received', '') and ' :'+p.BODIES[0] in x['received'] for x in ch.traffic()))
                trace = self.capture(run, cfg)
                self.assertFalse(any(x.get('admission') == 'authorized' for x in trace['app_model_calls'][1:]))
                if fault:
                    self.assertEqual(len(trace['app_model_calls']), 1)
                    self.assertEqual(before['app_occurrences'][0]['deadline'], trace['app_occurrences'][0]['deadline'])
                trace.update(status=status, peer=ch.traffic(), before=before)
                self.evidence(name, trace)
                return trace
            self.assertEqual((code, status), (0, {'status':'BOUNDED_STOP'}))
            body = (commands or ['', 'send '+p.BODIES[0]])[1][5:]
            if ambiguous:
                marker = Path(ch.bridge_config['failpoint_marker'])
                p.wait_for(marker.exists, ch.bridge, 10)
                before_bridge = p.rows(ch.bridge_root/'bridge.sqlite', 'channel_egress')
                ch.kill(ch.bridge); ch.bridge_config.pop('pause_at'); ch.start_bridge()
                time.sleep(.3)  # bounded observation of recovery, not retrying an effect
                after_bridge = p.rows(ch.bridge_root/'bridge.sqlite', 'channel_egress')
                self.assertEqual(before_bridge, after_bridge)
                self.assertEqual(after_bridge[0]['reserved'], 1)
                self.assertEqual(after_bridge[0]['outcome'], 'unknown')
                self.assertFalse(any(' :'+body in x.get('received', '') for x in ch.traffic()))
                cfg['bridge_recovery'] = dict(before=before_bridge, after=after_bridge, delivery='UNKNOWN_NO_AUTOMATIC_RESEND')
            else:
                p.wait_for(lambda:any(' :'+body in x.get('received', '') for x in ch.traffic()), seconds=10)
            trace = p.export(run, cfg)
            self.assertEqual(len(trace['fixture_evaluations']), 2)
            self.assertEqual(sum(x['reserved'] for x in trace['model_provider']), 2)
            self.assertTrue(all(x['admission'] == 'authorized' for x in trace['app_model_calls']))
            initial, following = [json.loads(x['intent'])['native_prompt'] for x in trace['app_model_calls']]
            for location in p.LOCATIONS: self.assertNotIn(location, initial)
            self.assertNotIn('REMEMBER-SUCCESS', initial)
            self.assertIn('MOST_PROMOTED_MEMORIES: ()', initial)
            projection = trace['app_turns'][0]['projection']
            self.assertIn('LAST_SKILL_USE_RESULTS: '+projection+' HISTORY: ', following)
            self.assertNotEqual(trace['setup_session'], json.loads(trace['app_model_calls'][0]['intent'])['session'])
            fact = next((x for x in (corpus or self.corpus)['approved_append_inputs'] if 'project Aster ' in x), None)
            evaluation = p.evaluate(projection, body, not ambiguous, fact)
            trace.update(evaluation=evaluation, kill_stage=stage, before=before, bridge_recovery=cfg.get('bridge_recovery'),
                         provider_before=cfg.get('provider_before'))
            if before:
                for table in ('app_occurrences', 'app_model_calls', 'app_query_vectors', 'app_memory_reads', 'app_priority_contexts'):
                    for old, new in zip(before[table], trace[table]):
                        for field in ('id', 'deadline', 'intent', 'context_view', 'view', 'request'):
                            if field in old: self.assertEqual(old[field], new[field])
                        for field in ('result', 'candidates', 'payloads'):
                            if old.get(field) is not None: self.assertEqual(old[field], new[field])
                        for field in ('calls', 'attempts', 'queries'):
                            if field in old: self.assertGreaterEqual(new[field], old[field])
                        if table == 'app_query_vectors' and old['result'] is not None:
                            self.assertEqual(old['attempts'], new['attempts'])
                        if table == 'app_memory_reads' and old['candidates'] is not None:
                            self.assertEqual(old['queries'], new['queries'])
                trace['recovery_assertions'] = 'identities/views/captures/deadlines retained; reservations never refunded; captured evaluation stages not repeated'
            self.evidence(name, trace)
            return trace
        except BaseException:
            if (run.h.root/'native.log').exists(): (OUT/(name+'-failure.log')).write_bytes((run.h.root/'native.log').read_bytes())
            if Path(run.app['status_file']).exists(): (OUT/(name+'-status.json')).write_bytes(Path(run.app['status_file']).read_bytes())
            raise
        finally:
            if 'channel' in cfg: cfg['channel'].close()
            run.close()

    def test_real_irc_local_and_https_fixture_model_placement(self):
        results = [self.case('workflow-'+placement, placement=placement) for placement in ('local', 'network')]
        self.assertEqual(results[0]['app_turns'][0]['projection'], results[1]['app_turns'][0]['projection'])
        self.assertTrue(all(x['evaluation']['task'] == 'PASS' for x in results))

    def test_original_and_https_native_remember_query_parity(self):
        from .append_oracle import original
        from .append_composition import configure
        from .append_run import report
        from .controlled_run import ControlledRun
        commands = ['remember '+x for x in self.corpus['approved_append_inputs']]+['query '+p.QUERY, '']
        oracle = original(self.corpus, responses=commands)
        expected = oracle['observations'][-1]['feedback']
        result = {}
        for placement in ('local', 'network'):
            run = ControlledRun(placement, commands, search={'boundary':'recorded-response'})
            try:
                run.model['expected_feedback'] = {}; run.save()
                cfg = configure(run, self.corpus, placement, inputs={x:x for x in self.corpus['approved_append_inputs']})
                timing = observed_finish(run)
                value = report(run, cfg)
                self.assertEqual(run.observations()[-1]['feedback'], expected)
                self.assertTrue(all(value['caller_dependencies']['absent'].values()))
                native = [x for x in oracle['events'] if x['event'] == 'query'][0]['candidates']
                actual = value['read_receipts'][0]['payloads']
                self.assertEqual([x[1:3] for x in native], [x[1:3] for x in actual])
                for a,b in zip(native,actual): self.assertAlmostEqual(a[3], b[3], places=6)
                value.update(timing=timing, exact_feedback_match=True, candidate_order_match=True)
                result[placement] = value
            finally: run.close()
        self.evidence('original-local-https-parity', dict(oracle=oracle, paths=result,
                      disclosure='explicit generated corpus only; no S04/S05 private providers in /5 HTTPS composition'))

    def test_changed_target_and_inconclusive_native_results(self):
        changed = self.case('variant-changed', corpus=p.generated(1), commands=['query '+p.QUERY, 'send '+p.BODIES[1]])
        self.assertIn('project Aster keeps its calibration card in violet drawer.', changed['app_turns'][0]['projection'])
        self.assertNotIn('project Aster keeps its calibration card in amber cabinet.', changed['app_turns'][0]['projection'])
        self.assertEqual(changed['evaluation']['task'], 'PASS')
        absent = self.case('variant-target-absent', corpus=p.generated(2), commands=['query '+p.QUERY, 'send '+p.BODIES[-1]])
        self.assertEqual(absent['evaluation']['task'], 'PASS')
        self.assertFalse(absent['evaluation']['retrieval_decisive'])

    def test_wrong_permitted_and_unnecessary_refusal_are_task_failures(self):
        for name, body in [('wrong-permitted', p.BODIES[1]), ('unnecessary-refusal', p.BODIES[-1])]:
            trace = self.case(name, commands=['query '+p.QUERY, 'send '+body])
            self.assertTrue(trace['evaluation']['output_permitted'])
            self.assertTrue(trace['evaluation']['peer_observed'])
            self.assertEqual(trace['evaluation']['task'], 'FAIL')

    def test_native_batch_stage_private_and_malformed_refusals(self):
        for name, commands, code in [
            ('stage-refusal', ['send '+p.BODIES[0], 'send '+p.BODIES[0]], 'UNSUPPORTED_OPERATION'),
            ('batch-refusal', ['query '+p.QUERY+'\nshell echo generated', 'send '+p.BODIES[0]], 'UNSUPPORTED_OPERATION'),
            ('private-refusal', ['query '+p.QUERY, 'send PRIVATE_OUTPUT_CANARY'], 'UNSUPPORTED_OPERATION'),
            ('parser-refusal', ['((query "'+p.QUERY+'"))', 'send '+p.BODIES[0]], 'INVALID_ARGUMENT')]:
            with self.subTest(name=name): self.case(name, commands=commands, rejection=code)

    def test_query_process_kills_retained_capture_stages(self):
        for stage in ('after_occurrence_bind', 'after_vector_capture', 'after_candidate_capture', 'after_native_result_capture'):
            with self.subTest(stage=stage): self.case('kill-'+stage, stage=stage)

    def test_next_prompt_and_application_capture_process_kills(self):
        for stage in ('after_model_prompt_bind', 'after_model_application_capture', 'after_occurrence_bind'):
            with self.subTest(stage=stage): self.case('kill-second-'+stage, stage=stage, second=True)

    def test_provider_capture_recovered_without_fixture_regeneration(self):
        self.case('kill-provider-capture', stage='after_model_provider_capture', placement='network', provider=True)

    def test_uncertain_send_never_automatically_retried(self):
        trace = self.case('kill-socket-reservation', ambiguous=True)
        self.assertEqual(trace['evaluation']['task'], 'FAIL')
        self.assertFalse(trace['evaluation']['peer_observed'])

    def test_unavailable_generation_hydration_and_revocation_stop_answer_stage(self):
        def unavailable(run, cfg):
            selected = Path(run.h.config['memory_read']['root'])/'search'/cfg['view']['snapshot']['generation']
            selected.rename(selected.with_name(selected.name+'-injected-unavailable'))
        def hydration(run, cfg):
            selected = Path(run.h.config['memory_read']['root'])/'payloads'
            selected.rename(selected.with_name('injected-unavailable-payloads'))
        def revoked(run, cfg):
            encoder = json.loads(Path(cfg['encoder_config']).read_bytes())
            encoder['principals']['A']['scopes']['generated-s03'].remove('embedding.disclose')
            p.write(cfg['encoder_config'], encoder)
        for name, stage, fault, code in [
            ('unavailable-generation', 'after_vector_capture', unavailable, 'NOT_AVAILABLE'),
            ('failed-hydration', 'after_candidate_capture', hydration, 'NOT_AVAILABLE'),
            ('captured-query-revoked', 'after_native_result_capture', revoked, 'UNAUTHORIZED')]:
            with self.subTest(name=name):
                self.case(name, stage=stage, fault=fault, rejection=code)


if __name__ == '__main__': unittest.main()
