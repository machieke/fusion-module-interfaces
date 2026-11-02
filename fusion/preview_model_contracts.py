"""Recorded-only preview completion profile on the existing X01 lifecycle.

This is not another live-model allowance or an Ollama numerical/profile change.
The provider has no generative endpoint, runtime path, credentials or fallback.
"""
from dataclasses import dataclass
import re
from . import model_contracts as historical
from .contracts import canonical, digest, require
from .registry import Descriptor, Requirement, resolve, selection_token

INTERFACE, VERSION = historical.INTERFACE, historical.VERSION
PROFILE = 'omega-recorded-native-text/2'
MODEL = 'authored-native-command-proposals'
MODEL_DIGEST = digest(MODEL.encode())
PRIVACY = historical.PRIVACY
TRANSFORM = historical.TRANSFORM
MAX_PROMPT, MAX_TEXT, MAX_WIRE = 32768, historical.MAX_TEXT, 131072
MAX_CALLS, MAX_RPC, MAX_SESSION_CALLS = 128, 8, 32
LIMITS = dict(prompt_bytes=MAX_PROMPT, result_bytes=MAX_TEXT, backend_reservations=1,
              turn_slots=MAX_SESSION_CALLS, counting='utf8-bytes-not-model-tokens')
uid, integer, text, clean = historical.uid, historical.integer, historical.text, historical.clean


def messages(raw): return historical.messages(raw, max_bytes=MAX_PROMPT)


def deadline_limit(profile):
    require(profile == PROFILE, 'UNSUPPORTED_PROFILE')
    return 120000


def descriptor(profile=PROFILE):
    deadline_limit(profile)
    return Descriptor('recorded-native-proposals', INTERFACE, VERSION, '0.1.0', frozenset({PROFILE}),
        frozenset({'complete', 'observe', 'authorize'}), frozenset({'scoped', 'process-restart', 'one-reservation', 'captured-replay'}),
        MAX_WIRE, privacy=PRIVACY, deterministic=True,
        features=frozenset({'recorded-only', 'no-generative-runtime', TRANSFORM, 'native-command-proposals-only','input-window-ms:120000'}))


def select(catalogue, profile=PROFILE):
    d = descriptor(profile)
    selected = resolve(catalogue, Requirement(INTERFACE, VERSION, '1.1.0', PROFILE, d.operations,
        d.guarantees, MAX_WIRE, privacy=PRIVACY, features=d.features))
    require(selected == d, 'UNSUPPORTED_PROFILE')
    return selected


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
    messages: list
    deadline_ms: int
    profile: str
    model: str
    model_digest: str
    transform: str
    limits: dict


def intent(value):
    historical.fields(value, 'id session slot source_id principal scope selection native_prompt messages deadline_ms profile model model_digest transform limits')
    for key in ('id', 'session', 'source_id'): uid(value[key])
    integer(value['slot'], 1, MAX_SESSION_CALLS)
    for key in ('principal', 'scope'):
        require(type(value[key]) is str and re.fullmatch('[A-Za-z0-9_.-]{1,80}', value[key]))
    require(value['scope'].startswith('synthetic-'), 'UNAUTHORIZED')
    require(value['selection'] == selection_token(descriptor()), 'UNSUPPORTED_PROFILE')
    require((value['profile'], value['model'], value['model_digest'], value['transform']) ==
            (PROFILE, MODEL, MODEL_DIGEST, TRANSFORM), 'UNSUPPORTED_PROFILE')
    require(value['limits'] == LIMITS and canonical(value['limits']) == canonical(LIMITS), 'UNSUPPORTED_PROFILE')
    require(value['messages'] == messages(value['native_prompt']), 'CONFLICT')
    integer(value['deadline_ms'], 1)
    require(len(canonical(value)) <= MAX_WIRE)
    return value


def request(value):
    historical.fields(value, 'interface_ref operation intent')
    require(value['interface_ref'] == dict(id=INTERFACE, version=VERSION), 'UNSUPPORTED_VERSION')
    require(value['operation'] in ('complete', 'observe', 'authorize'), 'UNSUPPORTED_OPERATION')
    intent(value['intent'])
    require(len(canonical(value)) <= MAX_WIRE)
    return value


def completion(value):
    require(type(value) is dict and value.get('observed_model') == MODEL, 'NOT_AVAILABLE')
    historical.completion({**value, 'observed_model': historical.MODEL})
    require(all(x is None for x in value['usage'].values()), 'NOT_AVAILABLE')
    return value


def observation(value, accepted):
    # The receipt shape/accounting are exactly the existing owner semantics.
    # Validate preview response first, then reuse historical receipt checks with
    # only the recorded-model label translated for that validator.
    adjusted = value
    if type(value) is dict and value.get('response') is not None:
        completion(value['response'])
        adjusted = {**value, 'response': {**value['response'], 'observed_model': historical.MODEL}}
    historical.observation(adjusted, accepted)
    return value
