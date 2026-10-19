"""X01: one bounded text completion; no tools, cognition or backend SDK imports."""
from dataclasses import dataclass, field
from typing import Protocol
import re
import uuid

from .contracts import canonical, digest, require
from .neoclaw_contracts import fields
from .registry import Descriptor, Requirement, resolve, selection_token

INTERFACE, VERSION = 'model.inference', '1.0.0'
PROFILE, APPLICATION = 'neoclaw-ollama-qwen38-text/1', 'controlled-native-loop/9'
CPU_PROFILE = 'neoclaw-ollama-qwen38-text/2'
MODEL = 'qwen3.8:27b'
MODEL_DIGEST = '9a8921f5b297f01451509b60e4a7e754674fe40d4a64dd9f89fc4a56c4fc5ee1'
TRANSFORM = 'neoclaw-chat-marker-split-clean/1'
PRIVACY = 'explicit-synthetic-prompt-only'
MAX_PROMPT, MAX_TEXT, MAX_WIRE = 12288, 32768, 98304
MAX_CALLS, MAX_RPC, MAX_SESSION_CALLS = 12, 8, 4
OPTIONS = dict(num_ctx=32768, num_predict=6000, temperature=1, top_k=20,
               top_p=.95, min_p=0, repeat_penalty=1, presence_penalty=0,
               draft_num_predict=0)
LIMITS = dict(prompt_bytes=MAX_PROMPT, result_bytes=MAX_TEXT, output_tokens=6000,
              context_tokens=32768, backend_reservations=1)


def uid(value):
    require(type(value) is str)
    try: require(str(uuid.UUID(value)) == value)
    except ValueError: require(False)
    return value


def integer(value, low=0, high=2**63-1):
    require(type(value) is int and low <= value <= high)
    return value


def text(value, limit=MAX_PROMPT):
    require(type(value) is str)
    try: size = len(value.encode('utf-8', errors='strict'))
    except UnicodeError: require(False)
    require(size <= limit)
    return value


def hash_value(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None)


def messages(raw):
    # Definition of the checked native transformation; parity is executed against
    # the original source and the independently extracted native adapter.
    text(raw)
    require(':-:-:-:' in raw)
    transformed = raw.replace('<tool_call>', '').replace('<arg_value>', ' ').replace('</tool_call>', ' ').replace('</arg_value>', '')
    system, user = transformed.split(':-:-:-:', 1)
    return [dict(role='system', content=system),
            dict(role='user', content=user if user.strip() else 'EMPTY / NO NEW USER INPUT.')]


def clean(raw):
    return text(raw, MAX_TEXT).replace('_quote_', '"').replace('_apostrophe_', "'")


def deadline_limit(profile):
    require(profile in (PROFILE, CPU_PROFILE), 'UNSUPPORTED_PROFILE')
    return 30000 if profile == PROFILE else 300000


def limits(profile):
    deadline_limit(profile)
    return dict(LIMITS) if profile == PROFILE else dict(LIMITS, input_deadline_ms=300000)


def descriptor(profile=PROFILE):
    deadline_limit(profile)
    extra = set() if profile == PROFILE else {'input-deadline-ms:300000'}
    return Descriptor('ollama-qwen38-text', INTERFACE, VERSION, '0.1.0', frozenset({profile}),
        frozenset({'complete', 'observe', 'authorize'}), frozenset({'scoped', 'process-restart', 'one-reservation', 'captured-replay'}),
        MAX_WIRE, privacy=PRIVACY, deterministic=False,
        features=frozenset({MODEL_DIGEST, TRANSFORM, digest(canonical(OPTIONS)), 'nonstreaming', 'think:false', 'truncate:false'} | extra))


def select(catalogue, profile=PROFILE):
    d = descriptor(profile)
    chosen = resolve(catalogue, Requirement(INTERFACE, VERSION, '1.1.0', profile,
        d.operations, d.guarantees, MAX_WIRE, privacy=PRIVACY, features=d.features))
    require(chosen == d, 'UNSUPPORTED_PROFILE')
    return chosen


@dataclass(frozen=True)
class CompletionInput:
    id: str
    session: str
    slot: int
    source_id: str
    principal: str
    scope: str
    selection: str
    native_prompt: str
    messages: list[dict[str, str]]
    deadline_ms: int
    profile: str = PROFILE
    model: str = MODEL
    model_digest: str = MODEL_DIGEST
    transform: str = TRANSFORM
    limits: dict = field(default_factory=lambda: dict(LIMITS))


def intent(value):
    fields(value, 'id session slot source_id principal scope selection native_prompt messages deadline_ms profile model model_digest transform limits')
    for key in ('id', 'session', 'source_id'): uid(value[key])
    integer(value['slot'], 1, MAX_SESSION_CALLS)
    for key in ('principal', 'scope'):
        require(type(value[key]) is str and re.fullmatch('[A-Za-z0-9_.-]{1,80}', value[key]))
    profile = value['profile']; deadline_limit(profile)
    require(value['selection'] == selection_token(descriptor(profile)), 'UNSUPPORTED_PROFILE')
    require((value['profile'], value['model'], value['model_digest'], value['transform']) ==
            (profile, MODEL, MODEL_DIGEST, TRANSFORM), 'UNSUPPORTED_PROFILE')
    require(value['limits'] == limits(profile) and canonical(value['limits']) == canonical(limits(profile)), 'UNSUPPORTED_PROFILE')
    require(value['messages'] == messages(value['native_prompt']), 'CONFLICT')
    integer(value['deadline_ms'], 1)
    require(len(canonical(value)) <= MAX_WIRE)
    return value


def request(value):
    fields(value, 'interface_ref operation intent')
    require(value['interface_ref'] == dict(id=INTERFACE, version=VERSION), 'UNSUPPORTED_VERSION')
    require(value['operation'] in ('complete', 'observe', 'authorize'), 'UNSUPPORTED_OPERATION')
    intent(value['intent'])
    require(len(canonical(value)) <= MAX_WIRE)
    return value


def completion(value):
    fields(value, 'raw_text native_text observed_model provider_request_id usage finish_reason outcome durations_ns')
    text(value['raw_text'], MAX_TEXT)
    require(value['native_text'] == clean(value['raw_text']), 'NOT_AVAILABLE')
    require(value['observed_model'] == MODEL, 'NOT_AVAILABLE')
    require(value['provider_request_id'] is None or type(value['provider_request_id']) is str and
            0 < len(value['provider_request_id']) <= 200, 'NOT_AVAILABLE')
    fields(value['usage'], 'input_tokens output_tokens reasoning_tokens')
    for name, maximum in [('input_tokens', 32768), ('output_tokens', 6000), ('reasoning_tokens', 6000)]:
        if value['usage'][name] is not None: integer(value['usage'][name], 0, maximum)
    require(value['usage']['reasoning_tokens'] is None, 'NOT_AVAILABLE')
    require(value['finish_reason'] in ('stop', 'length', 'refusal', 'invalid'), 'NOT_AVAILABLE')
    expected = 'truncated' if value['finish_reason'] == 'length' else 'refused' if value['finish_reason'] == 'refusal' else 'invalid' if value['finish_reason'] == 'invalid' else 'empty' if not value['raw_text'].strip() else 'complete'
    require(value['outcome'] == expected, 'NOT_AVAILABLE')
    fields(value['durations_ns'], 'total load prompt generation')
    for duration in value['durations_ns'].values():
        if duration is not None: integer(duration)
    return value


def observation(value, accepted):
    fields(value, 'id intent_sha256 principal selection state reserved response captured_ms late failure_code')
    require(value['id'] == accepted['id'] and value['intent_sha256'] == digest(canonical(accepted)), 'NOT_AVAILABLE')
    require(value['principal'] == accepted['principal'], 'UNAUTHORIZED')
    require(value['selection'] == accepted['selection'], 'UNSUPPORTED_PROFILE')
    require(value['state'] in ('absent', 'accepted', 'unknown', 'captured'), 'NOT_AVAILABLE')
    require(type(value['reserved']) is int and value['reserved'] in (0, 1) and type(value['late']) is bool)
    require(value['failure_code'] is None or value['state']=='unknown' and value['failure_code'] in
            ('NOT_AVAILABLE','INVALID_ARGUMENT','UNSUPPORTED_PROFILE','DEADLINE_EXCEEDED'), 'NOT_AVAILABLE')
    if value['state'] == 'captured':
        completion(value['response']); integer(value['captured_ms'], 1)
        require(value['reserved'] == 1 and value['late'] == (value['captured_ms'] > accepted['deadline_ms']), 'NOT_AVAILABLE')
    else:
        require(value['response'] is None and value['captured_ms'] is None and value['late'] is False, 'NOT_AVAILABLE')
        require(value['reserved'] == (1 if value['state'] == 'unknown' else 0), 'NOT_AVAILABLE')
    return value


class ModelInference(Protocol):
    def complete(self, accepted: CompletionInput) -> dict: ...
    def observe(self, accepted: CompletionInput) -> dict: ...
