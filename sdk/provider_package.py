"""Artifact-only Go provider/consumer kit build: no checkout, Python or network."""
import argparse,hashlib,json,subprocess,tarfile,tempfile
from pathlib import Path
from .provider_contracts import generated
from fusion.contracts import canonical

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build(destination,toolchain='/usr/local/go',cache_directory=None):
    root=Path(destination).resolve();root.mkdir(parents=True,exist_ok=False)
    assert (ROOT/'sdk/go/inspectprovider/contract.json').read_bytes()==canonical(generated())+b'\n','contract drift'
    inputs={}
    for directory,prefix in ((ROOT/'sdk/go','go'),(ROOT/'sdk/provider-kit','')):
        for path in sorted(directory.rglob('*')):
            if path.is_file():inputs[str(Path(prefix)/path.relative_to(directory))]=path
    mapping={name:sha(path) for name,path in inputs.items()}
    archive=root/'omega-go-provider-kit-source.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for name,path in inputs.items():
            info=tar.gettarinfo(str(path),arcname='omega-go-provider-kit/'+name)
            info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
            with path.open('rb') as stream:tar.addfile(info,stream)
    with tempfile.TemporaryDirectory(prefix='omega-go-provider-kit-') as temporary:
        extracted=Path(temporary)
        with tarfile.open(archive) as tar:tar.extractall(extracted,filter='data')
        source=extracted/'omega-go-provider-kit'
        assert {str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}==mapping
        cache=Path(cache_directory).resolve() if cache_directory else Path.home()/'.cache/go-build';cache.mkdir(parents=True,exist_ok=True)
        libraries=['/lib64/ld-linux-x86-64.so.2','/lib/x86_64-linux-gnu/libc.so.6','/lib/x86_64-linux-gnu/libpthread.so.0']
        mounts=[part for name in libraries for part in ('--ro-bind',str(Path(name).resolve()),name)]
        command=['bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts','--unshare-net',*mounts,
            '--ro-bind',str(source),'/kit','--ro-bind',toolchain,'/toolchain','--bind',str(cache),'/cache',
            '--bind',str(root),'/output','--tmpfs','/tmp','--proc','/proc','--dev','/dev','--clearenv',
            '--setenv','PATH','/toolchain/bin','--setenv','HOME','/nonexistent','--setenv','GOROOT','/toolchain',
            '--setenv','GOTOOLCHAIN','local','--setenv','GOCACHE','/cache','--setenv','GOENV','off','--setenv','GOPROXY','off','--setenv','GOSUMDB','off',
            '--setenv','CGO_ENABLED','0','--chdir','/kit/go','/toolchain/bin/go']
        jobs=[('tests',['test','./...','-count=1'])]+[(name,['build','-trimpath','-o','/output/'+name,'./cmd/'+name])
            for name in ('omega-client','omega-inspect-provider')]
        for name,args in jobs:
            result=subprocess.run(command+args,capture_output=True,timeout=180)
            (root/(name+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(name+' failed; retained log')
    binaries={name:dict(sha256=sha(root/name),bytes=(root/name).stat().st_size,
        buildinfo=subprocess.check_output([toolchain+'/bin/go','version','-m',str(root/name)],text=True))
        for name in ('omega-client','omega-inspect-provider')}
    result=dict(profile='omega-go-provider-starter-kit/1',status='PASS',source=mapping,
        source_manifest_sha256=hashlib.sha256(canonical(mapping)).hexdigest(),archive_sha256=sha(archive),
        binaries=binaries,toolchain=subprocess.check_output([toolchain+'/bin/go','version'],text=True).strip(),
        toolchain_binary_sha256=sha(Path(toolchain)/'bin/go'),libraries={x:sha(Path(x)) for x in libraries},
        contract=generated()['selection'],external_modules=[],classification='EXTRACTED_KIT_REAL_GO_FIXTURE_PORT_CONFORMANCE',
        isolation='only extracted kit, pinned toolchain, cache, output; no checkout/home/Python/provider journals; disconnected network',
        native_deployed_gate='SEPARATE_REPORT',additional_live_generations=0)
    (root/'manifest.json').write_bytes(canonical(result)+b'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination');p.add_argument('--toolchain',default='/usr/local/go');p.add_argument('--cache');a=p.parse_args()
    print(json.dumps(build(a.destination,a.toolchain,a.cache)))
