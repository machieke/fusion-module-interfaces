"""Test composition: real C1 + HTTPS AtomStorage/DeTTa, fresh synthetic data."""
from http.server import ThreadingHTTPServer
import ssl
import subprocess
import threading
from fusion import cognitive_services as cs
from fusion.contracts import canonical
from fusion.preview_ports import COMPOSITION, OPERATIONS, descriptor
from fusion.registry import descriptor_wire
from examples.phase2_provider.server import handler
from .native_loop import ROOT


def configure(run, scope):
    root=run.h.server_root/'history-storage';root.mkdir()
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'key.pem'),
        '-out',str(root/'cert.pem'),'-days','1','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],
        check=True,capture_output=True)
    token='synthetic-history-storage-token'
    config=dict(composition=cs.COMPOSITION,privacy=cs.PRIVACY,scope=scope,root=str(root/'data'),
        detta_binary=str(ROOT/'artifacts/detta-build/target/debug/fusion-detta-adapter'),
        catalogue=[descriptor_wire(d) for d in cs.descriptors()],actors={'A':'A'},
        principals={'A':dict(credential=token,scopes={scope:['atom.storage.'+op for op in cs.OPERATIONS['atom.storage']]})})
    path=root/'policy.json';path.write_bytes(canonical(config))
    owned=cs.Ports(path,'fusion-storage')
    class Adapter:
        def invoke(self,credential,q):return owned.invoke(cs.ROUTE,credential,q)
    httpd=ThreadingHTTPServer(('127.0.0.1',0),handler(Adapter()))
    tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(root/'cert.pem',root/'key.pem')
    httpd.socket=tls.wrap_socket(httpd.socket,server_side=True)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    atom=dict(composition=cs.COMPOSITION,principal='A',scope=scope,credential=token,
        endpoint=dict(host='127.0.0.1',port=httpd.server_port,ca_file=str(root/'cert.pem'),path=cs.ROUTE),
        descriptor=descriptor_wire(cs.descriptors()[0]))
    atom_path=run.h.caller_root/'history-atoms.json';atom_path.write_bytes(canonical(atom))
    selected=descriptor_wire(descriptor('episodic.memory'))
    owner=run.h.server_root/'history-owner.json'
    owner.write_bytes(canonical(dict(composition=COMPOSITION,scope=scope,root=str(run.h.server_root/'history'),
        descriptors={'episodic.memory':selected},atom_clients={'A':atom},principals={'A':dict(credential='history-token',
        scopes={scope:['episodic.memory.'+op for op in (*OPERATIONS['episodic.memory'],'appendEvent','readEpisode')]})})))
    client=run.h.caller_root/'history-client.json'
    client.write_bytes(canonical(dict(composition=COMPOSITION,scope=scope,principal='A',placement='local',fallback=False,
        credential='history-token',provider_config=str(owner),descriptors={'episodic.memory':selected})))
    run.app.setdefault('facet_configs',{})['episodic.memory']=str(client)
    run.app.setdefault('preview',{}).setdefault('providers',[]).append(selected)
    run.app['history_atoms_config']=str(atom_path)
    def stop():httpd.shutdown();thread.join(timeout=5);httpd.server_close()
    return stop
