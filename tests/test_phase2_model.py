"""Recorded-only preview DTO and existing ModelService lifecycle tests.

Authored proposals are data; this backend runs no tools, opens no network
connections, and imports no generative runtime. The clock and disclosure rule
are explicit test fixtures. Owner state uses real SQLite durability. Commit
interruptions are simulated exceptions/reopen, not process-kill evidence.
"""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from fusion import model_contracts as historical
from fusion import preview_model_contracts as c
from fusion.contracts import ContractError, canonical, digest, require
from fusion.model_service import ModelService
from fusion.registry import descriptor_wire, selection_token


SCOPE = 'synthetic-preview-model-tests'
CREDENTIAL = 'synthetic-recorded-owner-token'
PROPOSAL = 'query synthetic project location'
PROMPT = 'Synthetic selected native tools and actual feedback:-:-:-:synthetic operator input'


def recorded(proposal=PROPOSAL):
    return dict(raw_text=proposal, native_text=c.clean(proposal), observed_model=c.MODEL,
        provider_request_id=None, usage=dict(input_tokens=None, output_tokens=None, reasoning_tokens=None),
        finish_reason='stop', outcome='complete' if proposal.strip() else 'empty',
        durations_ns=dict(total=None, load=None, prompt=None, generation=None))


class RecordedProposals:
    def __init__(self, response=None, action=lambda: None):
        self.response = copy.deepcopy(recorded() if response is None else response)
        self.action, self.calls = action, []

    def complete(self, accepted):
        require(isinstance(accepted, c.CompletionInput), 'UNSUPPORTED_PROFILE')
        self.calls.append(asdict(accepted))
        self.action()
        return copy.deepcopy(self.response)


class PreviewModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='phase2-recorded-model-')
        self.addCleanup(self.temp.cleanup)
        self.root, self.now = Path(self.temp.name), 1000000
        clock = patch('fusion.model_service.now', side_effect=lambda: self.now)
        clock.start()
        self.addCleanup(clock.stop)
        self.session = str(uuid.uuid4())
        self.path = self.root/'policy.json'
        self.cfg = dict(principals={'A': dict(credential=CREDENTIAL, scopes={SCOPE:
            ['model.'+op for op in ('disclose', 'complete', 'observe', 'authorize')]})},
            model_completion=dict(database=str(self.root/'model.sqlite'), scope=SCOPE, sharing=c.PRIVACY,
                sessions=[self.session], max_calls=2, expires_ms=self.now+60000,
                catalogue=[descriptor_wire(c.descriptor())], runtime_lock={'boundary': 'AUTHORED_FIXTURE_ONLY'},
                disclosure=dict(boundary='EXACT_SYNTHETIC_PROMPT_FIXTURE', prompts=[PROMPT])))
        self.save()
        self.accepted = asdict(c.CompletionInput(id=str(uuid.uuid4()), session=self.session, slot=1,
            source_id=str(uuid.uuid4()), principal='A', scope=SCOPE, selection=selection_token(c.descriptor()),
            native_prompt=PROMPT, messages=c.messages(PROMPT), deadline_ms=self.now+20000,
            profile=c.PROFILE, model=c.MODEL, model_digest=c.MODEL_DIGEST, transform=c.TRANSFORM, limits=dict(c.LIMITS)))
        self.owners = []
        self.addCleanup(self.close_owners)

    def save(self):
        temporary = self.path.with_suffix('.new')
        temporary.write_bytes(canonical(self.cfg))
        temporary.replace(self.path)

    def close_owners(self):
        while self.owners: self.owners.pop().close()

    @staticmethod
    def disclosure(accepted, policy):
        require(policy['boundary'] == 'EXACT_SYNTHETIC_PROMPT_FIXTURE', 'UNSUPPORTED_PROFILE')
        require(accepted['native_prompt'] in policy['prompts'], 'UNAUTHORIZED')

    def owner(self, backend=None, hook=lambda _: None):
        owner = ModelService(self.path, RecordedProposals() if backend is None else backend, hook,
            disclosure=self.disclosure, contracts=c)
        self.owners.append(owner)
        return owner

    def request(self, operation='complete', accepted=None):
        return dict(interface_ref=dict(id=c.INTERFACE, version=c.VERSION), operation=operation,
            intent=copy.deepcopy(self.accepted if accepted is None else accepted))

    def invoke(self, owner, operation='complete', accepted=None, credential=CREDENTIAL):
        request = self.request(operation, accepted)
        reply = owner.invoke(credential, request)
        self.assertEqual(set(reply), {'request_sha256', 'principal', 'value'})
        self.assertEqual(reply['request_sha256'], digest(canonical(request)))
        self.assertEqual(reply['principal'], request['intent']['principal'])
        if operation == 'authorize': self.assertEqual(reply['value'], {'authorized': True})
        else: c.observation(reply['value'], request['intent'])
        return reply['value']

    def error(self, code, callback, *args, **kwargs):
        with self.assertRaises(ContractError) as caught: callback(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def test_preview_profile_is_distinct_and_historical_limits_stay_exact(self):
        self.assertEqual(c.select([c.descriptor()]), c.descriptor())
        self.assertIn('recorded-only', c.descriptor().features)
        self.assertEqual(historical.MAX_SESSION_CALLS, 4)
        self.assertEqual(historical.MAX_PROMPT, 12288)
        self.assertEqual(c.deadline_limit(c.PROFILE), 120000)
        self.error('UNSUPPORTED_PROFILE', c.deadline_limit, historical.CPU_PROFILE)
        self.error('UNSUPPORTED_PROFILE', c.intent, dict(self.accepted, profile=historical.PROFILE))
        self.error('UNSUPPORTED_PROFILE', historical.select, [c.descriptor()])
        self.error('UNSUPPORTED_PROFILE', c.select, [historical.descriptor()])
        c.intent(dict(self.accepted, slot=32))
        self.error('INVALID_ARGUMENT', c.intent, dict(self.accepted, slot=33))

    def test_request_fields_selection_messages_and_operation_are_bound(self):
        valid = self.request()
        self.assertEqual(c.request(valid), valid)
        for field, value, code in (
            ('interface_ref', {'id': c.INTERFACE, 'version': '2.0.0'}, 'UNSUPPORTED_VERSION'),
            ('operation', 'run-arbitrary-tool', 'UNSUPPORTED_OPERATION'),
        ):
            with self.subTest(field=field): self.error(code, c.request, dict(valid, **{field: value}))
        self.error('INVALID_ARGUMENT', c.request, dict(valid, unrecognized_required_field=True))
        for field, value, code in (
            ('selection', '0'*64, 'UNSUPPORTED_PROFILE'), ('model', historical.MODEL, 'UNSUPPORTED_PROFILE'),
            ('messages', [{'role': 'user', 'content': 'different prompt'}], 'CONFLICT'),
            ('limits', {}, 'UNSUPPORTED_PROFILE'), ('deadline_ms', True, 'INVALID_ARGUMENT'),
        ):
            with self.subTest(field=field): self.error(code, c.intent, dict(self.accepted, **{field: value}))

    def test_malformed_principal_and_scope_fail_as_contract_errors(self):
        for field, value in [('scope', None), ('scope', 7), ('principal', ''), ('principal', 'A\nforged'), ('scope', 'synthetic-invalid\nscope')]:
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                c.intent(dict(self.accepted, **{field: value}))

    def test_boolean_limit_cannot_alias_integer_reservation(self):
        limits = dict(c.LIMITS, backend_reservations=True)
        self.error('UNSUPPORTED_PROFILE', c.intent, dict(self.accepted, limits=limits))

    def test_request_total_wire_bound_includes_outer_envelope(self):
        # JSON escaping can make a valid 32 KiB native prompt approach the wire
        # ceiling. The enclosing request must fit as well as its inner intent.
        low, high = 0, c.MAX_PROMPT-16
        candidate = None
        while low <= high:
            middle = (low+high)//2
            raw = '\n'*middle+':-:-:-:input'
            value = dict(self.accepted, native_prompt=raw, messages=c.messages(raw))
            if len(canonical(value)) <= c.MAX_WIRE:
                candidate, low = value, middle+1
            else: high = middle-1
        self.assertIsNotNone(candidate)
        c.intent(candidate)
        request = self.request(accepted=candidate)
        self.assertGreater(len(canonical(request)), c.MAX_WIRE)
        self.error('INVALID_ARGUMENT', c.request, request)

    def test_large_preview_prompt_keeps_historical_bound_and_native_transform(self):
        raw = 'synthetic '+('x'*14000)+':-:-:-:<tool_call>query<arg_value>generated</arg_value></tool_call>'
        value = dict(self.accepted, native_prompt=raw, messages=c.messages(raw))
        c.intent(value)
        self.assertEqual(value['messages'][1]['content'], 'query generated ')
        self.error('INVALID_ARGUMENT', historical.messages, raw)
        self.error('INVALID_ARGUMENT', c.messages, 'x'*c.MAX_PROMPT+':-:-:-:input')

    def test_capture_replay_and_restart_never_repeats_backend(self):
        backend = RecordedProposals(recorded('_quote_Ω_apostrophe_'))
        owner = self.owner(backend)
        captured = self.invoke(owner)
        self.assertEqual(captured['response']['native_text'], '"Ω\'')
        self.assertTrue(all(v is None for v in captured['response']['usage'].values()))
        self.assertEqual(self.invoke(owner), captured)
        self.assertEqual(self.invoke(owner, 'observe'), captured)
        self.assertEqual(len(backend.calls), 1)
        self.close_owners()
        replacement = RecordedProposals(recorded('send this must never replace capture'))
        reopened = self.owner(replacement)
        self.now += 30000  # Saved-result observation survives the original deadline.
        self.assertEqual(self.invoke(reopened), captured)
        self.assertEqual(self.invoke(reopened, 'observe'), captured)
        self.assertEqual(replacement.calls, [])

    def test_equal_prompt_new_occurrence_and_original_input_are_distinct(self):
        backend = RecordedProposals()
        owner = self.owner(backend)
        first = self.invoke(owner)
        another = dict(self.accepted, id=str(uuid.uuid4()))
        self.error('CONFLICT', self.invoke, owner, accepted=another)
        another['slot'] = 2
        second = self.invoke(owner, accepted=another)
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(backend.calls), 2)
        for field, value in [('deadline_ms', self.accepted['deadline_ms']+1), ('source_id', str(uuid.uuid4()))]:
            with self.subTest(field=field):
                self.error('CONFLICT', self.invoke, owner, accepted=dict(self.accepted, **{field: value}))

    def test_current_authorization_and_prompt_disclosure_before_any_call(self):
        backend = RecordedProposals()
        owner = self.owner(backend)
        self.error('UNAUTHORIZED', self.invoke, owner, credential='wrong-token')
        self.error('UNAUTHORIZED', self.invoke, owner, accepted=dict(self.accepted, principal='B'))
        self.error('UNAUTHORIZED', self.invoke, owner, accepted=dict(self.accepted, scope='synthetic-other'))
        raw = 'private history:-:-:-:unapproved input'
        self.error('UNAUTHORIZED', self.invoke, owner,
            accepted=dict(self.accepted, native_prompt=raw, messages=c.messages(raw)))
        self.assertEqual(backend.calls, [])
        self.assertEqual(self.invoke(owner, 'observe')['state'], 'absent')

    def test_revocation_blocks_capture_recovery_without_erasing_capture(self):
        backend = RecordedProposals()
        owner = self.owner(backend)
        captured = self.invoke(owner)
        self.cfg['principals']['A']['scopes'][SCOPE].remove('model.disclose')
        self.save()
        for operation in ('complete', 'observe', 'authorize'):
            with self.subTest(operation=operation): self.error('UNAUTHORIZED', self.invoke, owner, operation)
        self.assertEqual(len(backend.calls), 1)
        rows = ModelService.inspect(self.path)
        self.assertEqual(json.loads(rows[0]['response']), captured['response'])
        self.assertEqual(rows[0]['reserved'], 1)

    def test_captured_observation_rejects_malformed_binding_and_usage(self):
        captured = self.invoke(self.owner())
        for field, value in [('id', str(uuid.uuid4())), ('intent_sha256', '0'*64), ('selection', 'stale'),
            ('principal', 'B'), ('reserved', 0), ('late', True), ('state', 'accepted'), ('failure_code', 'NOT_AVAILABLE')]:
            bad = copy.deepcopy(captured)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError): c.observation(bad, self.accepted)
        for mutate in (
            lambda value: value.update(observed_model=historical.MODEL),
            lambda value: value.update(native_text='fabricated output'),
            lambda value: value['usage'].update(output_tokens=1),
            lambda value: value['usage'].update(reasoning_tokens=0),
            lambda value: value.update(extra='unknown'),
        ):
            bad = copy.deepcopy(captured)
            mutate(bad['response'])
            with self.assertRaises(ContractError): c.observation(bad, self.accepted)

    def test_malformed_recorded_response_spends_reservation_without_retry(self):
        bad = recorded()
        bad['usage']['output_tokens'] = 8
        backend = RecordedProposals(bad)
        owner = self.owner(backend)
        self.error('NOT_AVAILABLE', self.invoke, owner)
        observed = self.invoke(owner, 'observe')
        self.assertEqual((observed['state'], observed['reserved']), ('unknown', 1))
        self.assertEqual(observed['failure_code'], 'NOT_AVAILABLE')
        self.assertEqual(self.invoke(owner), observed)
        self.assertEqual(len(backend.calls), 1)
        self.close_owners()
        replacement = RecordedProposals()
        self.assertEqual(self.invoke(self.owner(replacement)), observed)
        self.assertEqual(replacement.calls, [])

    def test_budget_stays_spent_and_configuration_cannot_refund_it(self):
        backend = RecordedProposals()
        owner = self.owner(backend)
        for slot in (1, 2):
            self.invoke(owner, accepted=dict(self.accepted, id=str(uuid.uuid4()), slot=slot))
        third = dict(self.accepted, id=str(uuid.uuid4()), slot=3)
        self.error('OVERLOADED', self.invoke, owner, accepted=third)
        self.assertEqual(len(backend.calls), 2)
        self.close_owners()
        reopened_backend = RecordedProposals()
        reopened = self.owner(reopened_backend)
        self.error('OVERLOADED', self.invoke, reopened, accepted=third)
        self.cfg['model_completion']['max_calls'] = 3
        self.save()
        self.error('CONFLICT', self.invoke, reopened, 'observe')
        self.assertEqual(reopened_backend.calls, [])

    def test_independent_acceptance_reservation_response_and_capture_recovery(self):
        stages = [('after_model_acceptance', 'accepted', 0, 1),
            ('after_model_reservation', 'unknown', 0, 0),
            ('after_model_backend_response', 'unknown', 1, 0),
            ('after_model_provider_capture', 'captured', 1, 0)]
        for index, (stage, state, before_calls, recovery_calls) in enumerate(stages):
            with self.subTest(stage=stage):
                self.close_owners()
                self.cfg['model_completion']['database'] = str(self.root/('model-'+str(index)+'.sqlite'))
                self.save()
                def interrupt(observed):
                    if observed == stage: raise RuntimeError('simulated '+stage)
                backend = RecordedProposals()
                with self.assertRaises(RuntimeError): self.invoke(self.owner(backend, interrupt))
                self.assertEqual(len(backend.calls), before_calls)
                self.close_owners()
                replacement = RecordedProposals()
                reopened = self.owner(replacement)
                self.assertEqual(self.invoke(reopened, 'observe')['state'], state)
                result = self.invoke(reopened)
                self.assertEqual(len(replacement.calls), recovery_calls)
                self.assertEqual(result['reserved'], 1)
                self.assertEqual(json.loads(ModelService.inspect(self.path)[0]['intent']), self.accepted)

    def test_deadline_expiry_preserves_accepted_intent_without_reservation(self):
        def interrupt(stage):
            if stage == 'after_model_acceptance': raise RuntimeError('accepted only')
        backend = RecordedProposals()
        with self.assertRaises(RuntimeError): self.invoke(self.owner(backend, interrupt))
        self.close_owners()
        self.now = self.accepted['deadline_ms']
        reopened = self.owner(backend)
        self.error('DEADLINE_EXCEEDED', self.invoke, reopened)
        self.assertEqual(self.invoke(reopened, 'observe')['state'], 'accepted')
        self.assertEqual(self.invoke(reopened, 'observe')['reserved'], 0)
        self.error('CONFLICT', self.invoke, reopened, accepted=dict(self.accepted, deadline_ms=self.now+1000))
        self.assertEqual(backend.calls, [])

    def test_invalid_or_expired_deadline_does_not_create_acceptance(self):
        backend = RecordedProposals()
        owner = self.owner(backend)
        self.error('DEADLINE_EXCEEDED', self.invoke, owner,
            accepted=dict(self.accepted, deadline_ms=self.now))
        self.error('INVALID_ARGUMENT', self.invoke, owner,
            accepted=dict(self.accepted, deadline_ms=self.now+120001))
        self.assertEqual(self.invoke(owner, 'observe')['state'], 'absent')
        self.assertEqual(backend.calls, [])

    def test_late_recorded_response_remains_captured_and_labelled(self):
        def late(): self.now = self.accepted['deadline_ms']+1
        backend = RecordedProposals(action=late)
        owner = self.owner(backend)
        result = self.invoke(owner)
        self.assertEqual(result['state'], 'captured')
        self.assertTrue(result['late'])
        self.assertEqual(self.invoke(owner), result)
        self.assertEqual(len(backend.calls), 1)


if __name__ == '__main__': unittest.main()
