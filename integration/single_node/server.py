"""Small process host for the four existing owners; no scheduling framework.

One PVC lock spans the process lifetime. The execution pump reuses NalService's
work/flush operations. The agent launches the existing source-checked native loop
once; terminal errors remain observable and are never automatically retried here.
"""
import fcntl
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import socket
import sqlite3
import ssl
import subprocess
import sys
import threading
import time

from fusion import neoclaw_contracts as c
from fusion.adapters.neoclaw_nal import NativeTruthDeduction
from fusion.contracts import ContractError, canonical, require
from fusion.neoclaw import NalService
from fusion.neoclaw_services import OwnerService, PortConnection, RemoteAtoms, RemoteCompletion
from fusion.neoclaw_transport import json_loads
from .configure import configure, write


def main():
    config_path = sys.argv[1] if len(sys.argv)>1 else '/config/component.json'
    initial = json.loads(Path(config_path).read_text())
    require(os.environ.get('POD_NAME') == initial['role']+'-0', 'UNSUPPORTED_PROFILE')
    state = Path(initial.get('state','/state'))
    state.mkdir(parents=True,exist_ok=True)
    lock = open(state/'owner.lock','a')
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit('OWNER_ALREADY_RUNNING') from None
    settings, config, state, run = configure(config_path)
    # This envelope selects the owner, not its current secrets/test knobs. It
    # refuses accidentally mounting a different service's or legacy journal PVC.
    seal = dict(composition=settings['service_composition'],role=settings['role'],scope=settings.get('memory',{}).get('scope',c.SCOPE))
    if (state/'owner-seal.json').exists():
        require(json.loads((state/'owner-seal.json').read_text())==seal,'UNSUPPORTED_PROFILE')
    else:
        require(set(p.name for p in state.iterdir()) <= {'owner.lock','lost+found'}, 'UNSUPPORTED_PROFILE')
        write(state/'owner-seal.json',seal)
    stop = threading.Event(); fatal = threading.Event(); role = settings['role']; child = None; worker = None
    memory=settings['service_composition']=='neoclaw-memory-services/1'
    chosen = c.selected(c.catalogue('detta')); owner = None; kernel = None
    def hook(stage):
        if config.get('test_failpoints') and config.get('pause_at')==stage:
            # Namespace PID 1 ignores self-SIGSTOP. A test-only thread barrier
            # keeps this exact independent commit boundary until kubelet kills
            # the pod; graceful shutdown must not release it and finish work.
            write(state/'pause.json',dict(stage=stage,pid=os.getpid()))
            threading.Event().wait()
    def execution():
        atoms = RemoteAtoms(PortConnection(**config['peers']['fusion-storage']),chosen['atom.storage'])
        mailbox = RemoteCompletion(PortConnection(**config['peers']['fusion-messaging']),chosen['agent.messaging'])
        def atoms_for(principal, selected=None):
            require(principal=='worker','UNAUTHORIZED'); return atoms
        return NalService(run/'owner.json',hook,kernel,atoms_for=atoms_for,mailbox=mailbox)
    if memory and role=='fusion-embedding':
        from fusion.adapters.native_e5 import NativeE5
        kernel=NativeE5(run/'owner.json')
        write(state/'encoder-readiness.json',kernel.readiness)
    elif memory and role=='fusion-search':
        from .memory_host import SearchHost
        owner=SearchHost(run/'owner.json',hook)
    elif memory and role=='fusion-storage':
        from fusion.memory_services import StoragePorts
        owner=StoragePorts(run/'owner.json',hook)
    elif role == 'fusion-execution':
        kernel = NativeTruthDeduction(config['runtime'])  # Hash checks; no numerical evaluation.
        service=execution(); service.close()
    elif role in ('fusion-storage','fusion-messaging'):
        owner=OwnerService(run/'owner.json',role)
    else:
        NativeTruthDeduction('/opt/native/runtime.json')  # Source identity only, no work.
    def pump():
        try:
            while not stop.is_set():
                service=execution()
                try:
                    service.work(); service.flush()
                finally: service.close()
                stop.wait(.05)
        except Exception as exc:
            write(state/'worker-status.json',dict(status='STOPPED',code=exc.code if isinstance(exc,ContractError) else 'NOT_AVAILABLE'))
            fatal.set()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,value,status=200):
            data=canonical(value); self.send_response(status)
            self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass
        def do_GET(self):
            if self.path not in ('/health/startup','/health/ready','/health/live'):
                self.reply(dict(error='NOT_FOUND'),404);return
            healthy=not stop.is_set() and not fatal.is_set()
            self.reply(dict(role=role,ready=healthy),200 if healthy else 503)
        def do_POST(self):
            service=None
            try:
                require(not stop.is_set(),'NOT_AVAILABLE')
                auth=self.headers.get_all('Authorization',[])
                require(len(auth)==1 and auth[0].startswith('Bearer '),'UNAUTHORIZED')
                require(self.headers.get('Content-Type')=='application/json' and not self.headers.get('Transfer-Encoding'))
                sizes=self.headers.get_all('Content-Length',[])
                require(len(sizes)==1 and sizes[0].isdigit() and 0<int(sizes[0])<=(98304 if memory else 8192))
                raw=self.rfile.read(int(sizes[0]));require(len(raw)==int(sizes[0]));request=json_loads(raw)
                if memory:
                    if role=='fusion-embedding':
                        from fusion.embedding_service import EmbeddingService
                        require(self.path=='/s03-encode','UNSUPPORTED_OPERATION')
                        service=EmbeddingService(run/'owner.json',kernel,hook)
                        with encode_lock:result=service.invoke(auth[0][7:],request)
                    else:
                        require(owner is not None,'UNSUPPORTED_OPERATION')
                        result=owner.invoke(self.path,auth[0][7:],request)
                elif role=='fusion-execution':
                    require(self.path=='/s01','UNSUPPORTED_OPERATION')
                    service=execution(); result=dict(ok=service.invoke(auth[0][7:],request),provider=request['selection'])
                else:
                    require(owner is not None,'UNSUPPORTED_OPERATION')
                    result=owner.public(auth[0][7:],request) if self.path=='/s01' else owner.private(auth[0][7:],self.path,request)
                # Explicit deployment-test fault: after owner commit, before reply.
                # Exclusive creation makes this one drop per fresh fault identity.
                fault=settings.get('test',{}).get('drop_response_operation')
                if fault and fault == request.get('operation',self.path):
                    try:
                        with open(state/'response-dropped.json','x') as f:
                            f.write(canonical(dict(operation=fault,message_id=request.get('message_id'))).decode());f.flush();os.fsync(f.fileno())
                    except FileExistsError:pass
                    else:
                        self.connection.shutdown(socket.SHUT_RDWR);self.connection.close();return
            except ContractError as exc:result=dict(error=exc.wire())
            except (ValueError,KeyError,TypeError):result=dict(error=ContractError('INVALID_ARGUMENT').wire())
            except (OSError,sqlite3.Error):result=dict(error=ContractError('NOT_AVAILABLE').wire())
            finally:
                if service is not None:service.close()
            self.reply(result)
    encode_lock=threading.Lock()
    # The memory caller is outbound-only: it mounts no server private key.
    # Its HTTP listener serves only inert kubelet probes; module RPCs stay TLS.
    context=None
    if not (memory and role=='omega-agent'):
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(config['tls_certificate'],config['tls_key'])
    class Server(ThreadingHTTPServer):
        allow_reuse_address=True
        def get_request(self):
            sock,address=super().get_request();sock.settimeout(2)
            try:return (context.wrap_socket(sock,server_side=True) if context else sock),address
            except BaseException:sock.close();raise
    def terminate(*_):
        stop.set()
        if child is not None and child.poll() is None:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    signal.signal(signal.SIGTERM,terminate);signal.signal(signal.SIGINT,terminate)
    with Server(('0.0.0.0',settings['https_port']),Handler) as server:
        server.timeout=.2
        if role=='fusion-execution' and settings['worker_enabled']:
            worker=threading.Thread(target=pump);worker.start()
        if (role=='omega-agent' and settings['native_enabled']) or (memory and role=='fusion-search'):
            # Startup dependency observation only: no invocation identity,
            # occurrence deadline, reservation or POST exists yet. After a
            # bounded failure the process exits; it never substitutes providers.
            until=time.monotonic()+(120 if memory else 60)
            dependencies=(('fusion-storage',) if role=='fusion-search' else ('fusion-storage','fusion-search','fusion-embedding')) if memory else ('fusion-execution','fusion-storage','fusion-messaging')
            for name in dependencies:
                while True:
                    conn=http.client.HTTPSConnection(settings['peers'][name],settings['https_port'],timeout=1,
                        context=ssl.create_default_context(cafile='/secrets/ca.crt'))
                    try:
                        conn.request('GET','/health/ready'); response=conn.getresponse();response.read(4096)
                        if response.status==200:break
                    except (OSError,http.client.HTTPException):pass
                    finally:conn.close()
                    if stop.wait(.2) or time.monotonic()>=until:raise SystemExit('DEPENDENCY_NOT_READY')
            if memory and role=='fusion-search':owner.initialize(state)
        if role=='omega-agent' and settings['native_enabled']:
            if memory:
                from .memory_host import prepare_agent
                prepare_agent(settings,state,run)
            log=open(state/'native.log','ab')
            child=subprocess.Popen([sys.executable,'-m','integration.neoclaw.native_loop',str(run/'application.json')],
                                   stdout=log,stderr=log,start_new_session=True)
        write(state/'process.json',dict(pid=os.getpid(),role=role,configuration_revision=settings['revision'],
                                      native_pid=child.pid if child else None))
        child_observed=False
        while not stop.is_set():
            server.handle_request()
            if child is not None and not child_observed and child.poll() is not None:
                write(state/'native-exit.json',dict(pid=child.pid,returncode=child.returncode))
                child_observed=True
    if worker is not None:worker.join(timeout=16)
    if child is not None:
        try:child.wait(timeout=6)
        except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
        log.close()
    write(state/'shutdown.json',dict(graceful=worker is None or not worker.is_alive(),role=role))
    if memory and role=='fusion-embedding':kernel.close()
    lock.close()


if __name__=='__main__':main()
