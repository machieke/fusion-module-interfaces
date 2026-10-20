"""New contract/negative tests. Explicit synthetic receipts and model fixtures."""
import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import uuid

from fusion import model_contracts as m, neoclaw_retrieval_disclosure as r
from fusion.contracts import canonical, ContractError, digest
from fusion.model_service import ModelService
from fusion.model_transport import configuration
from fusion.neoclaw_model_disclosure import disclose
from fusion.registry import descriptor_wire, selection_token
from integration.neoclaw.retrieval_preparation import QUERY, BODIES, evaluate
from integration.neoclaw.model_startup import retrieval_scaffold
from tests.test_model import Backend, request


class RetrievalDisclosure(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = dict(policy=r.POLICY, scaffold=retrieval_scaffold(), memories=['()'], users=['first', 'second'],
                           query=QUERY, receipt_root=str(self.root), recipient='authored-test-A', consent_sha256='a'*64,
                           view_sha256='b'*64, authority_policy=str(self.root/'policy.json'))
        self.cfg = dict(profile=m.CPU_PROFILE, sharing=m.PRIVACY, principal='A', scope='synthetic-new', session=str(uuid.uuid4()),
                        placement='local', provider_config='not-started', fallback=False, catalogue=[descriptor_wire(m.descriptor(m.CPU_PROFILE))],
                        disclosure=self.policy, commands=[['query', QUERY]]+[['send', x] for x in BODIES], credential='generated')
        self.raw = retrieval_scaffold()+' LAST_SKILL_USE_RESULTS:  HISTORY:  MOST_PROMOTED_MEMORIES: () TIME: 2032-10-20 12:00:00:-:-:-:first'
        self.accepted = asdict(m.CompletionInput(id=str(uuid.uuid4()), session=self.cfg['session'], slot=1,
            source_id=str(uuid.uuid4()), principal='A', scope=self.cfg['scope'], selection=selection_token(m.descriptor(m.CPU_PROFILE)),
            native_prompt=self.raw, messages=m.messages(self.raw), deadline_ms=time.time_ns()//1_000_000+299000,
            profile=m.CPU_PROFILE, limits=m.limits(m.CPU_PROFILE)))
        self.receipt = dict(policy=r.POLICY, recipient=self.policy['recipient'], consent_sha256='a'*64,
                            intent=self.accepted, query=None, context_view='b'*64)
        self.path = r.receipt_path(self.policy, self.accepted)
        self.path.write_bytes(canonical(self.receipt))

    def rejected(self, fn, code=None):
        with self.assertRaises(ContractError) as raised: fn()
        if code: self.assertEqual(raised.exception.code, code)

    def test_closed_selection_and_historical_policy_remain_separate(self):
        path = self.root/'client.json'; path.write_bytes(canonical(self.cfg))
        configuration(path)
        old = copy.deepcopy(self.cfg); old['disclosure'].pop('policy')
        path.write_bytes(canonical(old))
        self.rejected(lambda:configuration(path))
        from tests.test_model import prompt
        historical = dict(scaffold='public scaffold', memories=['()'], users=['synthetic input'], feedback_expressions=[])
        disclose(prompt(), historical)
        self.rejected(lambda:disclose(self.raw, historical))

    def test_stage_and_whole_batch_authority(self):
        r.admit(self.cfg, 1, [['query', QUERY]])
        for body in BODIES: r.admit(self.cfg, 2, [['send', body]])
        cases = [(1, [['send', BODIES[0]]]), (2, [['query', QUERY]]),
                 (1, [['query', QUERY], ['send', BODIES[0]]]), (1, [['query', QUERY], ['query', QUERY]]),
                 (1, [['remember', 'synthetic']]), (2, [['send', 'PRIVATE_CANARY']]), (3, [['send', BODIES[0]]]),
                 (1, [['shell', 'echo synthetic']]), (1, [['metta', '(+ 1 2)']]), (1, [])]
        for slot, commands in cases:
            with self.subTest(slot=slot, commands=commands): self.rejected(lambda:r.admit(self.cfg, slot, commands))

    def test_named_bounded_output_set_not_a_general_command_union(self):
        for change in ('extra-query', 'unknown-policy', 'oversized-set', 'duplicate', 'injection'):
            cfg = copy.deepcopy(self.cfg)
            if change == 'extra-query': cfg['commands'].append(['query', 'different'])
            if change == 'unknown-policy': cfg['disclosure']['policy'] = 'generic'
            if change == 'oversized-set': cfg['commands'] += [['send', str(i)] for i in range(10)]
            if change == 'duplicate': cfg['commands'].append(cfg['commands'][1])
            if change == 'injection': cfg['commands'][1][1] += '\nshell x'
            with self.subTest(change=change): self.rejected(lambda:r.configuration(cfg))

    def test_missing_and_swapped_receipts_fail(self):
        disclose(self.raw, self.policy, self.accepted)
        self.path.unlink()
        self.rejected(lambda:disclose(self.raw, self.policy, self.accepted))
        self.path.write_bytes(canonical(self.receipt))
        for key, value in [('id', str(uuid.uuid4())), ('session', str(uuid.uuid4())), ('source_id', str(uuid.uuid4())),
                           ('scope', 'another-scope'), ('principal', 'B'), ('model', 'another-model'),
                           ('deadline_ms', self.accepted['deadline_ms']+1), ('slot', 2)]:
            altered = dict(self.accepted, **{key:value})
            r.receipt_path(self.policy, altered).write_bytes(canonical(self.receipt))
            with self.subTest(key=key): self.rejected(lambda:disclose(self.raw, self.policy, altered))

    def test_recipient_and_consent_cannot_be_changed_by_matching_prompt(self):
        for key in ('recipient', 'consent_sha256'):
            changed = dict(self.policy, **{key:'another'})
            self.rejected(lambda:disclose(self.raw, changed, self.accepted))
        self.rejected(lambda:disclose(self.raw, self.policy))  # raw hash alone is no authority

    def test_first_prompt_empty_history_context_and_feedback(self):
        for old, new in [(' HISTORY: ', ' HISTORY: remember secret '),
                         ('MOST_PROMOTED_MEMORIES: ()', 'MOST_PROMOTED_MEMORIES: (answer)'),
                         ('LAST_SKILL_USE_RESULTS: ', 'LAST_SKILL_USE_RESULTS: target ') ]:
            raw = self.raw.replace(old, new)
            altered = dict(self.accepted, native_prompt=raw, messages=m.messages(raw))
            self.rejected(lambda:disclose(raw, self.policy, altered))

    def test_delimiters_quote_markers_and_fake_tools_refused_as_data(self):
        for marker in ('\n', '\r', '"', "'", '_quote_', '_apostrophe_', ':-:-:-:', 'COMMAND_RETURN:',
                       ' HISTORY:', '<tool_call>', '<arg_value>'):
            with self.subTest(marker=marker): self.rejected(lambda:r.safe_data('generated '+marker+' text'))
        for marker in ('<tool_call>', '</arg_value>', ':-:-:-:'):
            self.rejected(lambda:r.structural(self.raw+marker, self.policy))

    def test_output_permission_is_independent_of_grounding(self):
        fact = 'Synthetic project Aster keeps its calibration card in amber cabinet.'
        correct = evaluate(fact, BODIES[0], True, fact)
        self.assertEqual(correct['task'], 'PASS')
        for body in (BODIES[1], BODIES[-1]):
            wrong = evaluate(fact, body, True, fact)
            self.assertTrue(wrong['output_permitted']); self.assertEqual(wrong['task'], 'FAIL')
        absent = evaluate('inconclusive retrieved data', BODIES[-1], True, None)
        self.assertEqual(absent['task'], 'PASS')
        self.assertEqual(evaluate(fact, BODIES[0], False, fact)['task'], 'FAIL')
        self.assertFalse(evaluate(fact, 'private canary', False, fact)['output_permitted'])

    def test_owner_rechecks_revocation_on_captured_response(self):
        cfg = dict(model_completion=dict(database=str(self.root/'owner.sqlite'), scope=self.cfg['scope'], sharing=m.PRIVACY,
            sessions=[self.cfg['session']], max_calls=2, expires_ms=self.accepted['deadline_ms'],
            catalogue=self.cfg['catalogue'], disclosure=self.policy, runtime_lock={'fixture':True}),
            principals={'A':dict(credential='generated', scopes={self.cfg['scope']:
                ['model.'+x for x in ('complete', 'observe', 'authorize', 'disclose')]})})
        path = self.root/'policy.json'; path.write_bytes(canonical(cfg))
        backend = Backend(); owner = ModelService(path, backend); self.addCleanup(owner.close)
        first = owner.invoke('generated', request(self.accepted))
        self.assertEqual(first, owner.invoke('generated', request(self.accepted)))
        self.assertEqual(backend.calls, 1)
        cfg['principals']['A']['scopes'][self.cfg['scope']].remove('model.disclose')
        path.write_bytes(canonical(cfg))
        self.rejected(lambda:owner.invoke('generated', request(self.accepted, 'observe')), 'UNAUTHORIZED')
        self.assertEqual(backend.calls, 1)

    def test_guard_blocks_execution_and_host_network_before_tests(self):
        from integration.neoclaw.preparation_guard import verify, BLOCKED_FILES
        parent = os.environ.get('FUSION_PREP_PARENT_NET')
        if not parent: self.skipTest('requires explicitly isolated preparation launcher')
        report = verify(parent)
        self.assertNotEqual(report['namespace'], parent)
        for path in BLOCKED_FILES:
            if Path(path).exists():
                with self.subTest(path=path), self.assertRaises(PermissionError):
                    subprocess.run([path, '--version'], check=True, capture_output=True)
