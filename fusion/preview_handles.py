"""Pure stable-handle vocabulary for the opt-in Omega developer preview.

A handle names an exact typed target. It is neither an access capability nor
proof of owner acceptance, active lifecycle state, payload content or existence.
Consumers must resolve through declared owner ports and check current authority.
No aliases, registry, owner transitions, lookup, I/O or runtime live here.
"""
from dataclasses import dataclass
import json
import re
from typing import Literal, TypedDict
import uuid

from .contracts import AtomRef, canonical, label, require
from .lookup_contracts import ref as atom_ref
from .memory_contracts import episode_ref, evidence_ref
from .memory_types import EpisodeRef, EvidenceRef

PROFILE = 'omega-preview-handles/1'
PREFIX = 'oh1'
Kind = Literal['memory', 'episode', 'event', 'relation', 'task', 'result']
KINDS = frozenset({'memory', 'episode', 'event', 'relation', 'task', 'result'})
# One public, fixed domain separator; never an application secret or authority.
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, 'urn:omega:developer-preview:handles:1')
MAX_ENVELOPE_BYTES = 4096


class MemoryTarget(TypedDict):
    """An immutable memory revision, not its mutable logical lifecycle head."""
    enrollment: AtomRef
    payload: AtomRef


class TaskTarget(TypedDict):
    """An application task occurrence; mutable task state is not embedded."""
    session: str
    id: str


class ResultTarget(TypedDict):
    """A saved immutable result payload bound to its producing occurrence."""
    occurrence: str
    payload: AtomRef


Target = MemoryTarget | EpisodeRef | EvidenceRef | AtomRef | TaskTarget | ResultTarget


class HandleEnvelope(TypedDict):
    profile: str
    handle: str
    kind: Kind
    scope: str
    principal: str
    target: Target


@dataclass(frozen=True)
class ParsedHandle:
    kind: Kind
    identity: str


def _label(value):
    require(type(value) is str and label(value))
    return value


def _uuid(value, version=None):
    require(type(value) is str)
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        require(False)
    require(str(parsed) == value)
    if version is not None:
        require(parsed.version == version and parsed.variant == uuid.RFC_4122)
    return value


def _fields(value, names):
    require(type(value) is dict and set(value) == set(names.split()))


def parse(value: str, kind: Kind | None = None) -> ParsedHandle:
    """Syntax/type only. A bare UUID, alias or history page selector is invalid."""
    require(type(value) is str and len(value) <= 64)
    match = re.fullmatch(r'oh1:([a-z]+):([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', value)
    require(match is not None and match[1] in KINDS)
    if kind is not None:
        require(type(kind) is str and kind in KINDS and match[1] == kind)
    return ParsedHandle(match[1], _uuid(match[2], version=5))


def target(kind: Kind, value: Target, scope: str) -> Target:
    """Validate exact declared DTOs and return a detached canonical copy.

    AtomRefs remain opaque; no provider IDs or EpisodeRefs are reinterpreted.
    Structural endpoints for episodes/events need separately stored handle atoms.
    """
    require(type(kind) is str and kind in KINDS)
    _label(scope)
    require(type(value) is dict)
    if kind == 'memory':
        _fields(value, 'enrollment payload')
        atom_ref(value['enrollment'], scope)
        atom_ref(value['payload'], scope)
    elif kind == 'episode':
        episode_ref(value, scope)
    elif kind == 'event':
        evidence_ref(value, scope)
    elif kind == 'relation':
        atom_ref(value, scope)
    elif kind == 'task':
        _fields(value, 'session id')
        _uuid(value['session'])
        _label(value['id'])
    else:
        _fields(value, 'occurrence payload')
        _label(value['occurrence'])
        atom_ref(value['payload'], scope)
    require(len(canonical(value)) <= MAX_ENVELOPE_BYTES)
    return json.loads(canonical(value))


def derive(kind: Kind, scope: str, value: Target) -> str:
    """Public deterministic identity; principal is deliberately not a name input."""
    checked = target(kind, value, scope)
    name = canonical([scope, kind, checked]).decode('utf-8')
    return PREFIX + ':' + kind + ':' + str(uuid.uuid5(NAMESPACE, name))


def make(kind: Kind, scope: str, principal: str, value: Target) -> HandleEnvelope:
    """Build a presentation binding after the caller obtains an actual target.

    The supplied principal is an explicit recipient binding, not an authenticated
    assertion. This function cannot establish authorization or source acceptance.
    """
    _label(principal)
    checked = target(kind, value, scope)
    result = dict(profile=PROFILE, handle=derive(kind, scope, checked), kind=kind,
                  scope=scope, principal=principal, target=checked)
    require(len(canonical(result)) <= MAX_ENVELOPE_BYTES)
    return result


def envelope(value: HandleEnvelope, *, kind: Kind | None = None,
             scope: str | None = None, principal: str | None = None) -> HandleEnvelope:
    """Check typed correlation with trusted caller bindings; never grant access.

    Callers use ``scope`` and ``principal`` from authenticated composition. The
    shape-only form is useful for trusted DTO construction, never for access.
    """
    _fields(value, 'profile handle kind scope principal target')
    require(value['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    require(type(value['kind']) is str and value['kind'] in KINDS)
    _label(value['scope'])
    _label(value['principal'])
    if kind is not None:
        require(type(kind) is str and kind in KINDS and value['kind'] == kind)
    if scope is not None:
        _label(scope)
        require(value['scope'] == scope, 'UNAUTHORIZED')
    if principal is not None:
        _label(principal)
        require(value['principal'] == principal, 'UNAUTHORIZED')
    parse(value['handle'], value['kind'])
    expected = derive(value['kind'], value['scope'], value['target'])
    require(value['handle'] == expected, 'CONFLICT')
    require(len(canonical(value)) <= MAX_ENVELOPE_BYTES)
    return json.loads(canonical(value))
