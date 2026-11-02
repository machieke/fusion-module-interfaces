"""Authenticated HTTPS hosting of the existing independent FileFeedFixture.

The only mutable state is this provider's own atomic document and lock. Policy,
TLS assets and bind address are trusted startup inputs, never request arguments.
"""
import argparse
import fcntl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import signal
import ssl
import threading

from fusion.adapters.fixture_feed import FileFeedFixture
from fusion import lookup_contracts as c
from fusion.contracts import ContractError, canonical, decode, digest, encode, label, require
from fusion.policy import Policy
from fusion.ports import Mutation
from fusion.preview_client import COMPOSITION, MAX_WIRE_BYTES, OPERATIONS, strict_json
from fusion.registry import Descriptor, descriptor_wire, selection_token


def descriptor():
    return Descriptor('preview-independent-file-feed', 'atom.storage', '1.1.0', '0.1.0',
        frozenset({c.FEED}), OPERATIONS,
        frozenset({'process-restart', 'scoped', 'idempotent'}), c.MAX_BYTES,
        privacy='generated-shareable', receipt_providers=frozenset({'contract-fixture-files/1'}))


class Access:
    def __init__(self, path, credential):
        self.policy, self.credential = Policy(str(path)), credential
        self.principal = self.policy.authenticate(credential)

    def authorize(self, scope, operation):
        require(operation in OPERATIONS, 'UNSUPPORTED_OPERATION')
        require(self.policy.authenticate(self.credential) == self.principal, 'UNAUTHORIZED')
        config = self.policy.current()
        require(config['composition'] == COMPOSITION and config['privacy'] == 'generated-shareable', 'UNSUPPORTED_PROFILE')
        require(scope in config['synthetic_scopes'], 'UNAUTHORIZED')
        self.policy.check(self.principal, scope, 'atom.storage.' + operation)
        return self.principal


class Ports:
    """Closed current-contract adapter; never getattr on an unvalidated symbol."""
    def __init__(self, config):
        self.config = Path(config)
        cfg = Policy(str(config)).current()
        self.root = Path(cfg['root'])
        self.root.mkdir(parents=True, exist_ok=True)

    def invoke(self, credential, q):
        require(type(q) is dict and set(q) == {'id', 'composition', 'scope', 'interface', 'selection', 'operation', 'args'})
        c.identity(q['id'])
        require(q['composition'] == COMPOSITION, 'UNSUPPORTED_PROFILE')
        require(q['interface'] == 'atom.storage', 'UNSUPPORTED_OPERATION')
        require(q['selection'] == selection_token(descriptor()), 'UNSUPPORTED_PROFILE')
        operation, args, scope = q['operation'], q['args'], q['scope']
        require(type(args) is list and operation in OPERATIONS, 'UNSUPPORTED_OPERATION')
        expected = {'create': 3, 'get': 1, 'getMany': 1, 'availability': 1, 'head': 1, 'readCommits': 4}
        require(len(args) == expected[operation])
        access = Access(self.config, credential)
        access.authorize(scope, operation)
        require(Path(access.policy.current()['root']) == self.root, 'UNSUPPORTED_PROFILE')
        provider = FileFeedFixture(self.root / 'feed.json', access)
        if operation == 'create':
            require(type(args[0]) is dict and set(args[0]) == {'scope_ref', 'idempotency_key', 'intent_digest'})
            command = Mutation(**args[0])
            c.mutation(command)
            require(command.scope_ref == scope, 'UNAUTHORIZED')
            require(label(args[1]) and type(args[2]) is dict and set(args[2]) == {'bytes'})
            data = decode(args[2]['bytes'])
            c.integer(len(data), 1, c.MAX_BYTES)
            value = provider.create(command, args[1], data)
        elif operation in ('get', 'availability'):
            ref = c.ref(args[0], scope)
            value = provider.get(ref) if operation == 'get' else provider.availability(ref)
        elif operation == 'getMany':
            require(type(args[0]) is list and 1 <= len(args[0]) <= c.BATCH)
            value = provider.getMany(tuple(c.ref(ref, scope) for ref in args[0]))
        elif operation == 'head':
            require(args[0] == scope, 'UNAUTHORIZED')
            value = provider.head(scope)
        else:
            require(args[0] == scope, 'UNAUTHORIZED')
            c.head(args[2], scope)
            c.integer(args[1], 0, args[2]['sequence'])
            c.integer(args[3], 1, c.PAGE)
            value = provider.readCommits(*args)
        if operation == 'get':
            value = dict(ref=value.ref, content_type=value.content_type, data=encode(value.bytes))
        elif operation == 'getMany':
            value = [dict(ref=x.ref, content_type=x.content_type, data=encode(x.bytes)) for x in value]
        access.authorize(scope, operation)
        return dict(id=q['id'], request_digest=digest(canonical(q)), selection=q['selection'],
                    principal=access.principal, value=value)


def handler(ports):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'

        def log_message(self, *args):
            pass  # No request content, bearer credentials or private error detail.

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def reply(self, status, value):
            raw = canonical(value)
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path != '/healthz':
                self.reply(404, {'error': ContractError('UNSUPPORTED_OPERATION').wire()})
                return
            self.reply(200, {'ready': True, 'classification': 'contract-test-provider', 'work_executed': False})

        def do_POST(self):
            try:
                require(self.path == '/reference-cognition', 'UNSUPPORTED_OPERATION')
                require(self.headers.get('Transfer-Encoding') is None)
                require(self.headers.get_all('Content-Length') and len(self.headers.get_all('Content-Length')) == 1)
                length = int(self.headers['Content-Length'])
                require(1 <= length <= MAX_WIRE_BYTES)
                auths = self.headers.get_all('Authorization', [])
                require(len(auths) == 1 and auths[0].startswith('Bearer '), 'UNAUTHORIZED')
                raw = self.rfile.read(length)
                require(len(raw) == length)
                value = ports.invoke(auths[0][7:], strict_json(raw))
                self.reply(200, value)
            except ContractError as exc:
                self.reply(403 if exc.code == 'UNAUTHORIZED' else 400, {'error': exc.wire()})
            except (ValueError, KeyError, TypeError):
                self.reply(400, {'error': ContractError('INVALID_ARGUMENT').wire()})
            except OSError:
                self.reply(503, {'error': ContractError('NOT_AVAILABLE').wire()})
    return Handler


def serve(config, bind='127.0.0.1', port=8443, ready_file=None):
    ports = Ports(config)
    cfg = Policy(str(config)).current()
    lock = (ports.root / 'server.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    server = ThreadingHTTPServer((bind, port), handler(ports))
    server.daemon_threads = False
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cfg['tls_certificate'], cfg['tls_key'])
    server.socket = context.wrap_socket(server.socket, server_side=True)
    def stop(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    if ready_file:
        Path(ready_file).write_text(json.dumps({'port': server.server_port, 'descriptor': descriptor_wire(descriptor()),
            'classification': 'contract-test-provider', 'live_generations': 0}) + '\n')
    try:
        server.serve_forever(poll_interval=.1)
    finally:
        server.server_close()
        lock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--ready-file')
    options = parser.parse_args()
    serve(options.config, options.bind, options.port, options.ready_file)
