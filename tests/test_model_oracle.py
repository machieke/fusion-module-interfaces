"""Native request compatibility only; all SDK responses here are explicit fixtures."""
from pathlib import Path
import tempfile
import unittest

from fusion.contracts import ContractError
from fusion.adapters.neoclaw_model_text import NativeChatText
from integration.neoclaw.model_oracle import observe

SOURCE = Path(__file__).resolve().parents[1] / 'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py'


class NativeModelOracle(unittest.TestCase):
    def test_actual_effective_wrappers_and_transforms(self):
        for wrapper, model in [('useClaude', 'claude-opus-4-6'), ('useMiniMax', 'minimax/minimax-m2.7'),
                               ('useOpenRouter', 'z-ai/glm-5.2')]:
            with self.subTest(wrapper=wrapper):
                result = observe(SOURCE, wrapper,
                    'system<tool_call>x</tool_call><arg_value>Ω</arg_value>:-:-:-:user:-:-:-:tail',
                    ['((send _quote_Ω_apostrophe_s_quote_))'])
                self.assertEqual(result['requests'], [dict(model=model,
                    messages=[dict(role='system', content='systemx  Ω'),
                              dict(role='user', content='user:-:-:-:tail')],
                    max_tokens=6000, extra_body=dict(enable_thinking=True, thinking_budget=6000))])
                self.assertEqual(result['rendered'], '((send "Ω\'s"))')
                self.assertFalse(result['sdk_executed'])
                self.assertFalse(result['live_generation'])
                adapter = NativeChatText(SOURCE)
                self.assertEqual(adapter.request(result['input'], model), result['requests'][0])
                self.assertEqual(adapter.render(result['recorded_texts'][0]), result['rendered'])

    def test_native_empty_input_and_helper_null_retries_are_visible(self):
        result = observe(SOURCE, 'useClaude', 'policy:-:-:-: \t\n', [None, '()'])
        self.assertEqual(len(result['requests']), 2)
        self.assertEqual(result['requests'][0]['messages'][1]['content'], 'EMPTY / NO NEW USER INPUT.')
        self.assertEqual(result['helper_sleeps'], [1])
        exhausted = observe(SOURCE, 'useClaude', 'policy:-:-:-:input', [None] * 5)
        self.assertEqual(len(exhausted['requests']), 5)
        self.assertEqual(exhausted['error'], 'NATIVE_NULL_RETRY_EXHAUSTED')
        self.assertIsNone(exhausted['rendered'])
        adapter = NativeChatText(SOURCE)
        self.assertEqual(adapter.request('policy:-:-:-: \t\n', 'claude-opus-4-6'), result['requests'][0])
        with self.assertRaises(ContractError):
            adapter.render(None)

    def test_no_eager_clients_or_unchecked_source_or_function(self):
        # No API SDK is required by this interpreter. The unchanged native file
        # contains eager clients/media imports but only five checked defs execute.
        self.assertEqual(observe(SOURCE, 'useClaude', 'p:-:-:-:u', ['()'])['rendered'], '()')
        with self.assertRaises(ContractError):
            observe(SOURCE, 'useClaudeYoutubeImage', 'p:-:-:-:u', ['()'])
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / 'native.py'
            changed.write_bytes(SOURCE.read_bytes() + b'\n# drift\n')
            with self.assertRaises(ContractError):
                observe(changed, 'useClaude', 'p:-:-:-:u', ['()'])
            with self.assertRaises(ContractError):
                NativeChatText(changed)

    def test_unicode_placeholders_and_first_separator_match_native(self):
        adapter = NativeChatText(SOURCE)
        for content in ('s:-:-:-:u', ':-:-:-:', 's<tool_call>x</tool_call>:-:-:-:Ω😃',
                        's<arg_value>_quote_</arg_value>:-:-:-:a:-:-:-:b'):
            for raw in ('', '()', '((send _quote_Ω_apostrophe_s_quote_))', 'unbalanced ((send x'):
                with self.subTest(content=content, raw=raw):
                    original = observe(SOURCE, 'useClaude', content, [raw])
                    self.assertEqual(adapter.request(content, 'claude-opus-4-6'), original['requests'][0])
                    self.assertEqual(adapter.render(raw), original['rendered'])
        # This helper does not parse, repair or authorize the returned text.
        self.assertEqual(adapter.render('unbalanced ('), 'unbalanced (')


if __name__ == '__main__':
    unittest.main()
