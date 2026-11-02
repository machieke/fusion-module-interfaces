"""Session API size/replay/pagination regressions with fresh synthetic journals.

The worker's native projection is explicit authored test data here. This suite
executes the actual SessionPorts/SessionStore commits and authorization checks;
it performs no native, model, channel, HTTPS or cluster work.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import uuid

from fusion.contracts import ContractError, canonical, digest
from fusion.preview_session_service import SessionPorts
from fusion.preview_sessions import PROFILE


PAGE_BYTES = 98304
RESULT_BYTES = 65536
OPERATOR, WORKER = 'synthetic-operator-token', 'synthetic-worker-token'


class SessionBounds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-session-bounds-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root/'policy.json'
        self.scope, self.sid = 'synthetic-session-bounds', str(uuid.uuid4())
        self.config = dict(principals={
            'operator': dict(credential=OPERATOR, scopes={self.scope: ['sessions.'+op for op in
                ('create', 'submit', 'observe', 'disclose', 'pause', 'resume', 'close')]}),
            'worker': dict(credential=WORKER, scopes={self.scope: ['sessions.next', 'sessions.complete']}),
        }, native_sessions=dict(profile=PROFILE, model_boundary='RECORDED_FIXTURE', scope=self.scope,
            principal='A', database=str(self.root/'sessions.sqlite'), assignments=['native'], session_templates={
                self.sid: dict(catalogue='selected-preview-catalogue', policy='synthetic-preview-policy',
                    model_boundary='RECORDED_FIXTURE', limits=dict(inputs=32, pending=4, timeout_ms=30000))}))
        self.save()
        self.wakes = []
        self.ports = SessionPorts(self.path, self.wakes.append)
        self.call('create')

    def save(self):
        temporary = self.path.with_suffix('.new')
        temporary.write_bytes(canonical(self.config))
        temporary.replace(self.path)

    def request(self, operation, **body):
        return dict(id=str(uuid.uuid4()), profile=PROFILE, operation=operation,
            body=dict(session=self.sid, **body))

    def reply(self, operation, token=OPERATOR, **body):
        request = json.loads(canonical(self.request(operation, **body)))
        response = self.ports.invoke(token, request)
        self.assertEqual(set(response), {'id', 'profile', 'request_digest', 'actor', 'principal', 'value'})
        self.assertEqual(response['id'], request['id'])
        self.assertEqual(response['profile'], PROFILE)
        self.assertEqual(response['request_digest'], digest(canonical(request)))
        self.assertEqual(response['actor'], 'worker' if token == WORKER else 'operator')
        self.assertEqual(response['principal'], 'A')
        return response

    def call(self, operation, token=OPERATOR, **body):
        return self.reply(operation, token, **body)['value']

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    @staticmethod
    def result(number, size):
        value = dict(turn=number, projection='', occurrences=['occurrence-'+str(number)])
        remaining = size-len(canonical(value))
        if remaining < 0: raise AssertionError('test result bound too small')
        value['projection'] = 'x'*remaining
        if len(canonical(value)) != size: raise AssertionError('incorrect test byte size')
        return value

    def submit(self, number, text='identical synthetic input'):
        return self.call('submit', identity='input-'+str(number), text=text, assignment='native')

    def finish(self, number, value):
        return self.call('complete', WORKER, identity='input-'+str(number), result=value)

    def test_projection_above_old_16k_wire_cap_and_exact_store_limit(self):
        for number, size in enumerate((20000, 65536), 1):
            with self.subTest(result_bytes=size):
                accepted = self.submit(number)
                value = self.result(number, size)
                request = self.request('complete', identity='input-'+str(number), result=value)
                self.assertGreater(len(canonical(request)), 16384)
                self.assertLess(len(canonical(request)), PAGE_BYTES)
                receipt = self.finish(number, value)
                self.assertEqual(receipt['result_digest'], digest(canonical(value)))
                self.assertEqual(receipt['deadline'], accepted['deadline'])
                self.assertEqual(receipt['state'], 'complete')
                self.ports = SessionPorts(self.path, self.wakes.append)
                self.assertEqual(self.finish(number, value), receipt)
                page = self.call('observe', content=True, after=number-1)
                self.assertEqual(page['inputs'][0]['result'], value)
                self.assertEqual(page['inputs'][0]['deadline'], accepted['deadline'])

    def test_result_over_store_bound_refused_without_completion(self):
        accepted = self.submit(1)
        self.error('INVALID_ARGUMENT', self.finish, 1, self.result(1, RESULT_BYTES+1))
        page = self.call('observe', content=True)
        self.assertEqual(page['inputs'][0]['state'], 'accepted')
        self.assertIsNone(page['inputs'][0]['result'])
        self.assertEqual(page['inputs'][0]['deadline'], accepted['deadline'])
        receipt = self.finish(1, self.result(1, RESULT_BYTES))
        self.assertEqual(receipt['state'], 'complete')
        changed = self.result(1, RESULT_BYTES)
        changed['projection'] = 'y'+changed['projection'][1:]
        self.error('CONFLICT', self.finish, 1, changed)

    def test_utf8_result_bytes_are_preserved_without_repair_or_truncation(self):
        self.submit(1)
        value = dict(turn=1, projection=('Ω\n"_quote_"'*2000), occurrences=['occurrence-1'])
        self.assertGreater(len(canonical(value)), 16384)
        self.assertLessEqual(len(canonical(value)), RESULT_BYTES)
        receipt = self.finish(1, value)
        self.assertEqual(receipt['result_digest'], digest(canonical(value)))
        observed = self.call('observe', content=True)
        self.assertEqual(observed['inputs'][0]['result'], value)
        self.assertEqual(canonical(observed['inputs'][0]['result']), canonical(value))

    def test_observe_complete_response_budget_includes_binding_and_envelope(self):
        # Two entries totaling 98,300 bytes fit an entry-only accumulator but
        # exceed 98 KiB after session metadata and the API envelope are included.
        for number in (1, 2):
            accepted = self.submit(number)
            result = dict(turn=number, projection='', occurrences=['occurrence-'+str(number)])
            entry = dict(accepted, state='complete', payload=dict(text='identical synthetic input', assignment='native'), result=result)
            result['projection'] = 'x'*(49150-len(canonical(entry)))
            self.assertEqual(len(canonical(entry)), 49150)
            self.finish(number, result)
        response = self.reply('observe', content=True)
        self.assertLessEqual(len(canonical(response)), PAGE_BYTES)
        self.assertFalse(response['value']['complete'])
        self.assertEqual([item['sequence'] for item in response['value']['inputs']], [1])
        self.assertEqual(response['value']['next_after'], 1)
        tail = self.reply('observe', content=True, after=1)
        self.assertLessEqual(len(canonical(tail)), PAGE_BYTES)
        self.assertEqual([item['sequence'] for item in tail['value']['inputs']], [2])
        self.assertTrue(tail['value']['complete'])

    def test_pagination_order_equal_text_and_replay_have_no_skips_or_duplicates(self):
        results, deadlines = {}, {}
        for number in range(1, 8):
            accepted = self.submit(number)
            deadlines[number] = accepted['deadline']
            result = self.result(number, RESULT_BYTES if number % 2 else 20000)
            results[number] = result
            finished = self.finish(number, result)
            self.assertEqual(self.finish(number, result), finished)
            replayed_input = self.submit(number)
            self.assertEqual(replayed_input['sequence'], number)
            self.assertEqual(replayed_input['deadline'], accepted['deadline'])
        after, collected, pages = 0, [], 0
        while True:
            response = self.reply('observe', content=True, after=after)
            self.assertLessEqual(len(canonical(response)), PAGE_BYTES)
            page = response['value']
            self.assertEqual(self.call('observe', content=True, after=after), page)
            self.assertTrue(page['inputs'])
            collected.extend(page['inputs'])
            pages += 1
            self.assertLessEqual(pages, 7)
            if page['complete']:
                self.assertIsNone(page['next_after'])
                break
            self.assertEqual(page['next_after'], page['inputs'][-1]['sequence'])
            self.assertGreater(page['next_after'], after)
            after = page['next_after']
        self.assertGreater(pages, 1)
        self.assertEqual([row['sequence'] for row in collected], list(range(1, 8)))
        self.assertEqual(len({row['id'] for row in collected}), 7)
        for row in collected:
            self.assertEqual(row['result'], results[row['sequence']])
            self.assertEqual(row['deadline'], deadlines[row['sequence']])
        empty = self.call('observe', content=True, after=7)
        self.assertEqual(empty['inputs'], [])
        self.assertTrue(empty['complete'])
        self.assertIsNone(empty['next_after'])

    def test_revoked_disclosure_blocks_following_pages_and_completion_replay(self):
        for number in (1, 2):
            self.submit(number)
            self.finish(number, self.result(number, RESULT_BYTES))
        first = self.call('observe', content=True)
        self.assertIsNotNone(first['next_after'])
        self.config['principals']['operator']['scopes'][self.scope].remove('sessions.disclose')
        self.save()
        self.error('UNAUTHORIZED', self.call, 'observe', content=True, after=first['next_after'])
        metadata = self.call('observe', content=False)
        self.assertEqual([row['sequence'] for row in metadata['inputs']], [1, 2])
        self.assertTrue(all('result' not in row and 'payload' not in row for row in metadata['inputs']))
        self.config['principals']['worker']['scopes'][self.scope].remove('sessions.complete')
        self.save()
        self.error('UNAUTHORIZED', self.finish, 1, self.result(1, RESULT_BYTES))
        self.config['principals']['operator']['scopes'][self.scope].remove('sessions.observe')
        self.save()
        self.error('UNAUTHORIZED', self.call, 'observe', content=False)

    def test_malformed_operation_session_assignment_are_contract_errors(self):
        cases = []
        for malformed in ([], {}):
            operation = self.request('observe', content=False)
            operation['operation'] = malformed
            cases.append(operation)
            session = self.request('observe', content=False)
            session['body']['session'] = malformed
            cases.append(session)
            cases.append(self.request('submit', identity='malformed', text='synthetic', assignment=malformed))
        for request in cases:
            with self.subTest(request=request), self.assertRaises(ContractError):
                self.ports.invoke(OPERATOR, json.loads(canonical(request)))
        self.assertEqual(self.call('observe', content=False)['inputs'], [])
        self.assertEqual(self.wakes, [])

    def test_pagination_parameters_require_exact_bounded_types(self):
        for after in (-1, 33, True, [], {}, '0'):
            with self.subTest(after=after): self.error('INVALID_ARGUMENT', self.call, 'observe', content=True, after=after)
        for content in (1, 'yes', [], {}):
            with self.subTest(content=content): self.error('INVALID_ARGUMENT', self.call, 'observe', content=content)
        self.assertTrue(self.call('observe', content=False, after=32)['complete'])

    def test_completion_capacity_does_not_expand_operator_submission_limit(self):
        request = self.request('submit', identity='huge', text='x'*17000, assignment='native')
        self.error('INVALID_ARGUMENT', self.ports.invoke, OPERATOR, request)
        self.assertEqual(self.call('observe', content=False)['inputs'], [])
        self.assertEqual(self.wakes, [])


if __name__ == '__main__': unittest.main()
