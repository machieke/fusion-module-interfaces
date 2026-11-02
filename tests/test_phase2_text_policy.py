import unittest

from fusion.contracts import ContractError
from fusion.preview_text import check, helper, query, freeze, PROFILE
from fusion.preview_capabilities import manifest, IMPLEMENTATIONS


class TextPolicyTests(unittest.TestCase):
    def cfg(self):
        return dict(scope='synthetic-memory', principal='A', inputs={}, queries=[], text_policy=dict(
            profile=PROFILE, scope='synthetic-memory', principals=['A', 'B'], purposes=['query', 'remember'],
            max_utf8_bytes=1024, revision='policy-1'))

    def test_dynamic_inputs_are_explicit_bounded_and_frozen(self):
        cfg = self.cfg()
        self.assertEqual(helper(cfg, 'New synthetic project locates tools on shelf 17.', 'remember'), 'New synthetic project locates tools on shelf 17.')
        self.assertEqual(query(cfg, 'where are project tools'), 'where are project tools')
        self.assertEqual(freeze(cfg, {})['text_policy'], cfg['text_policy'])
        for text in ('x'*1025, 'quote"injection', 'line\nother', ':-:-:-:', '\x00', '_newline_'):
            with self.assertRaises(ContractError): check(cfg, text, 'remember')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): check(cfg, 'ok', 'query', 'forged')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): check(cfg, 'ok', 'send')
        cfg['text_policy']['unexpected'] = True
        with self.assertRaises(ContractError): check(cfg, 'ok', 'query')

    def test_historical_exact_lists_remain_exact(self):
        cfg = dict(inputs={'approved': 'native-helper'}, queries=['selected'])
        self.assertEqual(helper(cfg, 'approved', 'remember'), 'native-helper')
        self.assertEqual(query(cfg, 'selected'), 'selected')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): helper(cfg, 'not approved', 'remember')
        with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): query(cfg, 'not selected')

    def test_capability_manifest_does_not_invent_native_or_deployed_evidence(self):
        value = manifest()
        self.assertEqual(value['historical_family_denominator'], 15)
        self.assertEqual({x['tool']['tool_id'] for x in value['capabilities']}, set(IMPLEMENTATIONS))
        self.assertTrue(all(not x['native_adopted'] and not x['deployed'] for x in value['capabilities']))


if __name__ == '__main__': unittest.main()
