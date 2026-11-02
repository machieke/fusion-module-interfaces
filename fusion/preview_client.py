"""Small stdlib client for the existing typed AtomStorage/commit-feed ports.

This module imports contracts only. It never instantiates a provider, retries a
request, changes a deadline, or implies that a timeout cancelled an effect.
"""
from dataclasses import asdict, dataclass
import http.client
import json
from pathlib import Path
import re
import ssl
import time
import uuid

from . import lookup_contracts as c
from .contracts import ContractError, canonical, decode, digest, encode, label, require
from .ports import AtomEnvelope, Mutation
from .registry import Descriptor, Requirement, resolve, selection_token
from .responses import atom_write, availability, envelope, error

OPERATIONS = frozenset({'create', 'get', 'getMany', 'availability', 'head', 'readCommits'})
COMPOSITION = 'typed-atom-feed-https/1'
MAX_WIRE_BYTES = 131072


def strict_json(raw):
    """Reject duplicate keys, non-finite numbers and oversized/deep input."""
    require(type(raw) is bytes and len(raw) <= MAX_WIRE_BYTES, 'NOT_AVAILABLE')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'NOT_AVAILABLE')
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ContractError('NOT_AVAILABLE')))
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            require(depth <= 64, 'NOT_AVAILABLE')
            if type(item) is float:
                import math
                require(math.isfinite(item), 'NOT_AVAILABLE')
            if type(item) in (dict, list):
                pending.extend((x, depth + 1) for x in (item.values() if type(item) is dict else item))
        return value
    except (ValueError, UnicodeError, RecursionError):
        raise ContractError('NOT_AVAILABLE') from None


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int
    ca_file: str
    path: str = '/reference-cognition'
    timeout_seconds: float = 5.0

    def __post_init__(self):
        require(type(self.host) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]{0,252}', self.host))
        require(type(self.port) is int and 1 <= self.port <= 65535)
        require(type(self.path) is str and re.fullmatch(r'/[A-Za-z0-9/_-]{1,127}', self.path))
        require(type(self.timeout_seconds) in (int, float) and 0 < self.timeout_seconds <= 30)


def retry_classification(operation, code):
    """Advice only. Every retry retains identity, budget and the original deadline."""
    require(operation in OPERATIONS)
    error({'code': code, 'retryable': code in {'NOT_AVAILABLE', 'OVERLOADED'}})
    if code == 'NOT_AVAILABLE':
        return 'unknown-effect-observe-or-replay-same-mutation' if operation == 'create' else 'bounded-read-retry'
    if code == 'OVERLOADED':
        return 'bounded-retry-same-identity'
    return 'stop'


class AtomFeedClient:
    """AtomStorage + immutable-commit-feed/1, selected before any submission.

    ``deadline_ms`` is an absolute transport/observation deadline; the historical
    synchronous port has no provider-side durable work budget or cancel method.
    Do not interpret this client-side bound as one of those guarantees.
    """
    def __init__(self, endpoint: Endpoint, credential: str, principal: str,
                 scope: str, descriptor: Descriptor, *, deadline_ms: int,
                 composition: str = COMPOSITION, privacy: str = 'generated-shareable'):
        require(type(endpoint) is Endpoint and label(principal) and label(scope))
        require(type(credential) is str and credential.isascii() and 1 <= len(credential) <= 256 and
                '\r' not in credential and '\n' not in credential, 'UNAUTHORIZED')
        require(type(deadline_ms) is int and deadline_ms > 0)
        require(label(composition) and label(privacy))
        require(privacy != 'private-local-only', 'UNSUPPORTED_PROFILE')
        resolve([descriptor], Requirement('atom.storage', '1.0.0', '1.2.0', c.FEED,
                OPERATIONS, frozenset({'process-restart', 'scoped'}),
                privacy=privacy))
        self.endpoint, self.credential, self.principal = endpoint, credential, principal
        self.scope, self.descriptor = scope, descriptor
        self.deadline_ms, self.composition = deadline_ms, composition
        self.context = ssl.create_default_context(cafile=str(Path(endpoint.ca_file)))
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2

    def _remaining(self):
        remaining = (self.deadline_ms - time.time_ns() // 1_000_000) / 1000
        require(remaining > 0, 'DEADLINE_EXCEEDED')
        return min(remaining, self.endpoint.timeout_seconds)

    def _invoke(self, operation, args):
        require(operation in OPERATIONS and operation in self.descriptor.operations, 'UNSUPPORTED_OPERATION')
        request = dict(id=str(uuid.uuid4()), composition=self.composition,
                       scope=self.scope, interface='atom.storage',
                       selection=selection_token(self.descriptor), operation=operation, args=args)
        body = canonical(request)
        require(len(body) <= MAX_WIRE_BYTES)
        conn = http.client.HTTPSConnection(self.endpoint.host, self.endpoint.port,
                    timeout=self._remaining(), context=self.context)
        try:
            conn.request('POST', self.endpoint.path, body,
                         {'Authorization': 'Bearer ' + self.credential, 'Content-Type': 'application/json'})
            if conn.sock is not None:
                conn.sock.settimeout(self._remaining())
            response = conn.getresponse()
            require(response.status in (200, 400, 401, 403, 503), 'NOT_AVAILABLE')
            chunks, size = [], 0
            while size <= MAX_WIRE_BYTES:
                # read1 performs at most one underlying read; a slow peer cannot
                # renew the original deadline by dripping a response forever.
                if response.fp is not None:
                    response.fp.raw._sock.settimeout(self._remaining())
                chunk = response.read1(min(16384, MAX_WIRE_BYTES + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
            value = strict_json(b''.join(chunks))
        except (OSError, ValueError, http.client.HTTPException):
            raise ContractError('NOT_AVAILABLE') from None
        finally:
            conn.close()
        if type(value) is dict and set(value) == {'error'}:
            error(value['error'])
            raise ContractError(value['error']['code'])
        require(type(value) is dict and set(value) == {'id', 'request_digest', 'selection', 'principal', 'value'}, 'NOT_AVAILABLE')
        require(value['id'] == request['id'] and value['request_digest'] == digest(body) and
                value['selection'] == request['selection'] and value['principal'] == self.principal, 'NOT_AVAILABLE')
        self._remaining()
        return value['value']

    def create(self, command: Mutation, content_type: str, data: bytes):
        require(type(command) is Mutation)
        c.mutation(command)
        require(command.scope_ref == self.scope, 'UNAUTHORIZED')
        require(label(content_type) and type(data) is bytes)
        c.integer(len(data), 1, min(c.MAX_BYTES, self.descriptor.max_payload_bytes))
        value = self._invoke('create', [asdict(command), content_type, {'bytes': encode(data)}])
        atom_write(value, self.scope, self.descriptor)
        require(value['ref']['digest'] == digest(data), 'NOT_AVAILABLE')
        return value

    def _envelope(self, value, ref):
        try:
            require(type(value) is dict and set(value) == {'ref', 'content_type', 'data'}, 'NOT_AVAILABLE')
            item = AtomEnvelope(value['ref'], value['content_type'], decode(value['data']))
            envelope(item, ref)
            require(len(item.bytes) <= self.descriptor.max_payload_bytes, 'NOT_AVAILABLE')
            return item
        except (ContractError, TypeError, KeyError):
            raise ContractError('NOT_AVAILABLE') from None

    def get(self, ref):
        c.ref(ref, self.scope)
        return self._envelope(self._invoke('get', [ref]), ref)

    def getMany(self, refs):
        require(type(refs) is tuple and 1 <= len(refs) <= c.BATCH)
        for ref in refs:
            c.ref(ref, self.scope)
        value = self._invoke('getMany', [list(refs)])
        require(type(value) is list and len(value) == len(refs), 'NOT_AVAILABLE')
        return tuple(self._envelope(item, ref) for item, ref in zip(value, refs))

    def availability(self, ref):
        c.ref(ref, self.scope)
        value = self._invoke('availability', [ref])
        availability(value)
        require(value['content_hash'] == ref['digest'], 'NOT_AVAILABLE')
        return value

    def head(self, scope):
        require(scope == self.scope, 'UNAUTHORIZED')
        value = self._invoke('head', [scope])
        try:
            return c.head(value, scope)
        except (ContractError, TypeError, KeyError):
            raise ContractError('NOT_AVAILABLE') from None

    def readCommits(self, scope, after, through, limit):
        require(scope == self.scope, 'UNAUTHORIZED')
        c.head(through, scope)
        c.integer(after, 0, through['sequence'])
        c.integer(limit, 1, c.PAGE)
        value = self._invoke('readCommits', [scope, after, through, limit])
        try:
            return c.commits(value, scope, after, through, limit)
        except (ContractError, TypeError, KeyError):
            raise ContractError('NOT_AVAILABLE') from None
