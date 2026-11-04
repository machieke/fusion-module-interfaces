"""Offline second-language artifact build in a checkout-free mount namespace."""
import argparse,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
import hashlib

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build(destination,toolchain='/usr/local/go'):
    root=Path(destination).resolve();root.mkdir(parents=True,exist_ok=False)
    sources=ROOT/'sdk/go';mapping={str(p.relative_to(sources)):sha(p) for p in sorted(sources.rglob('*')) if p.is_file()}
    archive=root/'fusion-go-client-source.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for name in mapping:tar.add(sources/name,arcname='fusion-go-client/'+name,recursive=False)
    with tempfile.TemporaryDirectory(prefix='omega-go-package-') as directory:
        temp=Path(directory);src=temp/'source';src.mkdir()
        with tarfile.open(archive) as tar:tar.extractall(src,filter='data')
        src=src/'fusion-go-client'
        assert {str(p.relative_to(src)):sha(p) for p in src.rglob('*') if p.is_file()}==mapping
        cache=Path.home()/'.cache/go-build';cache.mkdir(parents=True,exist_ok=True)
        libraries=['/lib64/ld-linux-x86-64.so.2','/lib/x86_64-linux-gnu/libc.so.6','/lib/x86_64-linux-gnu/libpthread.so.0']
        mounts=[part for name in libraries for part in ('--ro-bind',str(Path(name).resolve()),name)]
        command=['bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts','--unshare-net',*mounts,
            '--ro-bind',str(src),'/source','--ro-bind',toolchain,'/toolchain',
            '--bind',str(cache),'/cache','--bind',str(root),'/output','--tmpfs','/tmp',
            '--proc','/proc','--dev','/dev','--clearenv','--setenv','PATH','/toolchain/bin',
            '--setenv','HOME','/nonexistent','--setenv','GOROOT','/toolchain','--setenv','GOCACHE','/cache',
            '--setenv','GOENV','off','--setenv','GOPROXY','off','--setenv','GOSUMDB','off',
            '--setenv','CGO_ENABLED','0','--chdir','/source','/toolchain/bin/go']
        # Unit tests use loopback TLS; a disconnected network namespace still
        # permits its own loopback and cannot contact any external runtime.
        for name,args in [('tests',['test','./...']),('build',['build','-trimpath','-o','/output/omega-client','./cmd/omega-client'])]:
            result=subprocess.run(command+args,capture_output=True,timeout=180)
            (root/(name+'.log')).write_bytes(result.stdout+result.stderr)
            if result.returncode:raise RuntimeError(name+' failed; retained log')
    version=subprocess.check_output([toolchain+'/bin/go','version']).decode().strip()
    buildinfo=subprocess.check_output([toolchain+'/bin/go','version','-m',str(root/'omega-client')]).decode()
    result=dict(profile='fusion-go-artifacts/1',status='PASS',toolchain=version,toolchain_binary_sha256=sha(Path(toolchain)/'bin/go'),
        source=mapping,source_manifest_sha256=hashlib.sha256(json.dumps(mapping,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        binary_sha256=sha(root/'omega-client'),archive_sha256=sha(archive),buildinfo=buildinfo,
        build_isolation='extracted source, pinned Go toolchain, build cache; no checkout/Python/provider state; network namespace isolated',
        build_runtime_libraries={name:sha(Path(name)) for name in libraries},external_modules=[],additional_live_generations=0)
    (root/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('destination');a=p.parse_args()
    print(json.dumps(build(a.destination)))
