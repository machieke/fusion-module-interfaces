"""S01 operator entrypoints. HTTPS serves fixed public operations, never work/flush."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import signal
import sqlite3
import ssl
import sys

from fusion.contracts import ContractError, canonical, require
from fusion.neoclaw import NalService
from fusion.neoclaw_transport import json_loads


def failpoint(config, stage):
    if config.get('pause_at') == stage:
        require(config.get('test_failpoints') is True, 'UNAUTHORIZED')
        Path(config['failpoint_marker']).write_text(json.dumps(dict(stage=stage, pid=os.getpid())))
        os.kill(os.getpid(), signal.SIGSTOP)


def serve(config_path, port, ready):
    config = json.loads(Path(config_path).read_text())
    encoder_service = None
    if config.get('embedding'):
        from fusion.adapters.native_e5 import NativeE5
        from fusion.embedding_service import EmbeddingService
        encoder_service = EmbeddingService(config_path, NativeE5(config_path), lambda stage: failpoint(config, stage))

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log credentials, raw request bodies or provider errors.

        def do_POST(self):
            service = None
            try:
                require(self.path in ('/s01', '/s03-read', '/s03-encode','/s03-append','/s06-mailbox'), 'UNSUPPORTED_OPERATION')
                auth = self.headers.get_all('Authorization', [])
                require(len(auth) == 1 and auth[0].startswith('Bearer '), 'UNAUTHORIZED')
                require(self.headers.get('Content-Type') == 'application/json')
                require(not self.headers.get('Transfer-Encoding'))
                lengths = self.headers.get_all('Content-Length', [])
                require(len(lengths) == 1 and lengths[0].isdigit())
                length = int(lengths[0])
                require(0 < length <= (98304 if self.path == '/s03-read' else 65536 if self.path in ('/s03-encode','/s03-append') else 16384 if self.path=='/s06-mailbox' else 4096))
                raw = self.rfile.read(length)
                require(len(raw) == length)
                request = json_loads(raw)
                if self.path=='/s06-mailbox':
                    require(config.get('channel_store') is not None,'UNSUPPORTED_OPERATION')
                    from fusion.channel_service import ChannelService
                    service=ChannelService(config_path,lambda stage:failpoint(config,stage))
                    reply=service.invoke(auth[0][7:],request)
                elif self.path=='/s03-append':
                    require(config.get('memory_append') is not None,'UNSUPPORTED_OPERATION')
                    from fusion.append_composition import AppendService
                    reply=AppendService(config_path,auth[0][7:],lambda stage:failpoint(config,stage)).invoke(request)
                elif self.path == '/s03-encode':
                    require(encoder_service is not None, 'UNSUPPORTED_OPERATION')
                    reply = encoder_service.invoke(auth[0][7:], request)
                elif self.path == '/s03-read':
                    from fusion.vector_composition import ReadService
                    reply = ReadService(config_path, auth[0][7:], lambda stage: failpoint(config, stage)).invoke(request)
                else:
                    service = NalService(config_path, lambda stage: failpoint(config, stage))
                    reply = dict(ok=service.invoke(auth[0][7:], request), provider=request['selection'])
            except ContractError as exc:
                reply = dict(error=exc.wire())
            except (TypeError, KeyError, ValueError):
                reply = dict(error=ContractError('INVALID_ARGUMENT').wire())
            except (OSError, sqlite3.Error):
                reply = dict(error=ContractError('NOT_AVAILABLE').wire())
            finally:
                if service is not None:
                    service.close()
            data = canonical(reply)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Acceptance is durable even when the reply is lost.

    class Server(HTTPServer):
        allow_reuse_address = True

        def get_request(self):
            sock, address = super().get_request()
            sock.settimeout(2)
            try:
                return context.wrap_socket(sock, server_side=True), address
            except BaseException:
                sock.close()
                raise

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(config['tls_certificate'], config['tls_key'])
    with Server(('127.0.0.1', port), Handler) as server:
        Path(ready).write_text(json.dumps(dict(host='127.0.0.1', port=server.server_port,
            placement='same-host loopback HTTPS; not multi-host', pid=os.getpid(),
            denied_paths_visible=[p for p in config.get('memory_read',{}).get('denied_paths',[]) if Path(p).exists() and any(Path(p).iterdir())],
            **({'encoder':encoder_service.encoder.readiness,'encoder_pid':encoder_service.encoder.process.pid} if encoder_service else {}))))
        server.serve_forever(poll_interval=.05)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['serve', 'work', 'flush'])
    parser.add_argument('config')
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--ready')
    parser.add_argument('--pause-at')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    if args.mode == 'serve':
        denied = config.get('memory_read', {}).get('denied_paths', [])
        if denied and os.environ.get('NEOCLAW_READ_ISOLATED') != '1':
            env = dict(os.environ, NEOCLAW_READ_ISOLATED='1')
            command = ['bwrap', '--die-with-parent', '--ro-bind', '/', '/', '--bind', '/tmp', '/tmp', '--proc', '/proc', '--dev', '/dev',
                       *[v for p in denied for v in ('--tmpfs', str(Path(p).resolve()))], '--', sys.executable, '-m', 'integration.neoclaw.host', *sys.argv[1:]]
            os.execvpe(command[0], command, env)
        if config.get('memory_read',{}).get('runtime'):
            from .memory_build import validate_runtime
            from fusion.contracts import digest
            runtime_path=Path(config['memory_read']['runtime'])
            require(digest(runtime_path.read_bytes())==config['memory_read']['runtime_sha256'],'UNSUPPORTED_PROFILE')
            runtime=validate_runtime(runtime_path)
            require(Path(sys.prefix).resolve()==Path(runtime['sdk']).resolve(),'UNSUPPORTED_PROFILE')
            import chromadb  # Warm the pinned SDK before announcing read readiness.
        require(args.ready is not None)
        serve(args.config, args.port, args.ready)
        return
    if args.pause_at:
        config['pause_at'] = args.pause_at
    service = NalService(args.config, lambda stage: failpoint(config, stage))
    try:
        print(canonical(dict(ok=getattr(service, args.mode)())).decode())
    finally:
        service.close()


if __name__ == '__main__':
    main()
