"""Pinned old/current code over actual HTTPS + DeTTa; no model runtime.

The old server is exported from the programme baseline, not a compatibility flag
on new code. Old clients are the immutable published SDK wheel. Only synthetic
configuration/certificates are test scaffolding; storage and wire calls are real.
"""
from dataclasses import replace
import io,json,os,subprocess,sys,tarfile,tempfile,time,unittest,venv
from pathlib import Path
from fusion import cognitive_services as cs,archive_contracts as a
from fusion.contracts import canonical,digest,ContractError
from fusion.ports import Mutation
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_wire
from tests.test_phase2_sdk import prepare

ROOT=Path(__file__).resolve().parents[1]
BASE='bf8e87d7416cab6954a702d64d12cdfcf7b976d1'
SCOPE='synthetic-integrated-archive-wire'
SERVER='''import json,sys,ssl
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from http.server import ThreadingHTTPServer
from fusion.cognitive_services import Ports,ROUTE
from examples.phase2_provider.server import handler
cfg=json.loads(Path(sys.argv[2]).read_bytes());ports=Ports(sys.argv[2],'fusion-storage')
class Adapter:
 def invoke(self,credential,q):return ports.invoke(ROUTE,credential,q)
server=ThreadingHTTPServer(('127.0.0.1',0),handler(Adapter()))
tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.load_cert_chain(cfg['tls_certificate'],cfg['tls_key'])
server.socket=tls.wrap_socket(server.socket,server_side=True)
Path(sys.argv[3]).write_text(json.dumps({'port':server.server_port}))
server.serve_forever()
'''
OLD_CALL='''import json,sys
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_read
from fusion.ports import Mutation
cfg=json.load(open(sys.argv[1]));c=AtomFeedClient(Endpoint(**cfg['endpoint']),cfg['credential'],'A',cfg['scope'],descriptor_read(cfg['descriptor']),deadline_ms=cfg['deadline'],composition=cfg['composition'])
if 'ref' in cfg:r=cfg['ref']
else:r=c.create(Mutation(cfg['scope'],cfg['identity']),'application/synthetic',b'actual compatible payload')['ref']
assert c.get(r).bytes==b'actual compatible payload'
print(json.dumps({'ref':r,'head':c.head(cfg['scope'])}))
'''


class ArchiveWire(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='integrated-archive-wire-');cls.root=Path(cls.temp.name)
        cls.binary=ROOT/'artifacts/detta-build/target/debug/fusion-detta-adapter'
        if not cls.binary.is_file():raise unittest.SkipTest('Pinned real DeTTa adapter unavailable')
        old=cls.root/'old';old.mkdir()
        raw=subprocess.check_output(['git','archive',BASE,'fusion','integration','examples/phase2_provider'],cwd=ROOT)
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:tar.extractall(old,filter='data')
        cls.old_source=old
        wheel=ROOT/'sdk/compatibility/0.1.0/fusion_module_client-0.1.0-py3-none-any.whl'
        assert digest(wheel.read_bytes())=='3db7d4c879634c92c0cdf5bef22fe9fab6f47c4bc0f0e8033e961be580b57938'
        venv.create(cls.root/'old-client',with_pip=True);cls.old_python=cls.root/'old-client/bin/python'
        subprocess.run([str(cls.old_python),'-I','-m','pip','install','--no-index','--no-deps',str(wheel)],cwd=cls.root,check=True,capture_output=True)
        (cls.root/'server.py').write_text(SERVER)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def start(self,name,*,old=False,archive=False,state=None):
        root=self.root/name;root.mkdir();base=prepare(root)
        catalogue=cs.descriptors(archive=archive)
        cfg=dict(composition=cs.COMPOSITION,privacy=cs.PRIVACY,scope=SCOPE,root=str(state or root/'state'),
            tls_certificate=base['tls_certificate'],tls_key=base['tls_key'],detta_binary=str(self.binary),
            catalogue=[descriptor_wire(x) for x in catalogue],actors={'A':'A'},
            principals={'A':dict(credential='generated-archive-token',scopes={SCOPE:['atom.storage.'+x for x in catalogue[-1 if archive else 0].operations]})})
        if archive:cfg['archive']=a.DEFAULT
        (root/'config.json').write_bytes(canonical(cfg));ready=root/'ready.json'
        proc=subprocess.Popen([sys.executable,'-I',str(self.root/'server.py'),str(self.old_source if old else ROOT),str(root/'config.json'),str(ready)],
            cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        def stop():
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
            proc.stderr.close()
        self.addCleanup(stop)
        until=time.monotonic()+5
        while not ready.exists() and proc.poll() is None and time.monotonic()<until:time.sleep(.02)
        self.assertTrue(ready.exists(),proc.stderr.read().decode() if proc.poll() is not None else 'server not ready')
        ep=Endpoint('127.0.0.1',json.loads(ready.read_bytes())['port'],str(root/'cert.pem'))
        return root,ep,proc
    def client(self,ep,archive=False):
        return AtomFeedClient(ep,'generated-archive-token','A',SCOPE,cs.descriptors(archive=archive)[-1 if archive else 0],
                              deadline_ms=time.time_ns()//1000000+30000,composition=cs.COMPOSITION)
    def old_call(self,ep,identity,ref=None):
        file=self.root/(identity+'.json')
        cfg=dict(endpoint=ep.__dict__,scope=SCOPE,identity=identity,composition=cs.COMPOSITION,descriptor=descriptor_wire(cs.descriptors()[0]),
                 deadline=time.time_ns()//1000000+30000,credential='generated-archive-token')
        if ref:cfg['ref']=ref
        file.write_bytes(canonical(cfg))
        result=subprocess.run([str(self.old_python),'-I','-c',OLD_CALL,str(file)],cwd=self.root,capture_output=True,text=True,timeout=35)
        self.assertEqual(result.returncode,0,result.stderr);return json.loads(result.stdout)

    def test_actual_old_and_new_client_server_core_matrix_and_new_capability(self):
        for old in (True,False):
            with self.subTest(server='baseline-1.0' if old else 'archive-1.1-plus-1.0'):
                root,ep,_=self.start('server-baseline' if old else 'server-current',old=old,archive=not old)
                historical=self.old_call(ep,'historical-'+str(old))
                current=self.client(ep);write=current.create(Mutation(SCOPE,'current-'+str(old)),'application/synthetic',b'actual compatible payload')
                self.assertEqual(current.get(historical['ref']).bytes,b'actual compatible payload')
                self.assertEqual(self.old_call(ep,'old-read-'+str(old),write['ref'])['ref'],write['ref'])
                head=current.head(SCOPE)
                new=self.client(ep,archive=True)
                if old:
                    with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):new.planArchive(SCOPE,0,head,2)
                    self.assertEqual(current.head(SCOPE),head)
                else:
                    plan=new.planArchive(SCOPE,0,head,2);self.assertFalse(plan['admission_reserved'])
                    command=Mutation(SCOPE,'publish');sealed=new.publishArchive(command,0,head,2)
                    self.assertEqual(sealed['state'],'sealed');self.assertEqual(new.publishArchive(command,0,head,2),sealed)
                    self.assertEqual(new.observeArchive(command)['archive'],sealed)
                    self.assertEqual(self.old_call(ep,'old-archived-read',write['ref'])['head'],head)
                    self.assertEqual(current.get(write['ref']).bytes,b'actual compatible payload')
                    with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):current.planArchive(SCOPE,0,head,2)

    def test_current_revocation_and_unsafe_old_binary_reopen_refusal(self):
        root,ep,proc=self.start('rollback-source',archive=True)
        client=self.client(ep,archive=True);write=client.create(Mutation(SCOPE,'one'),'application/synthetic',b'actual compatible payload');head=client.head(SCOPE)
        command=Mutation(SCOPE,'sealed');client.publishArchive(command,0,head,1)
        cfg=json.loads((root/'config.json').read_bytes());cfg['principals']['A']['scopes'][SCOPE].remove('atom.storage.get');(root/'config.json').write_bytes(canonical(cfg))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):client.get(write['ref'])
        proc.terminate();proc.wait(timeout=5)
        before=digest((root/'state/cognitive-atoms.sqlite').read_bytes())
        _,old_ep,_=self.start('rollback-denied',old=True,state=root/'state')
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):self.client(old_ep).get(write['ref'])
        self.assertEqual(digest((root/'state/cognitive-atoms.sqlite').read_bytes()),before)

if __name__=='__main__':unittest.main()
