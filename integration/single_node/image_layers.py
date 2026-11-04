"""Verified layered OCI export for disks that cannot hold a second asset copy.

The base archive is immutable and explicitly bound, never inferred from cache.
Installers can stream the complete OCI set into ctr/docker without materializing
another multi-gigabyte tar. Only blobs are shared; final tags/index come from
the tested overlay. This packages existing images, not another image builder.
"""
import argparse,hashlib,json,subprocess,sys,tarfile
from pathlib import Path
from fusion.contracts import require
from .reference_artifacts import sha


def base_selection(path,manifest):
    path=Path(path);meta=json.loads(Path(manifest).read_bytes())
    require(meta.get('source_export_verification')=='PASS','CONFLICT')
    require(sha(path)==meta['archive_sha256'],'CONFLICT')
    with tarfile.open(path) as archive:
        blobs={x.name for x in archive if x.isfile() and x.name.startswith('blobs/sha256/')}
    return dict(archive_sha256=meta['archive_sha256'],archive_bytes=path.stat().st_size),blobs


def select_overlay(source,destination,base_blobs):
    """Stream docker's OCI save. Names, not untrusted extraction paths."""
    with tarfile.open(fileobj=source,mode='r|') as incoming,tarfile.open(fileobj=destination,mode='w|') as outgoing:
        for member in incoming:
            require(not member.issym() and not member.islnk(),'UNSUPPORTED_PROFILE')
            require(not member.name.startswith('/') and '..' not in member.name.split('/'),'INVALID_ARGUMENT')
            if member.isfile() and member.name not in base_blobs:
                outgoing.addfile(member,incoming.extractfile(member))


def export(path,tags,base_blobs):
    process=subprocess.Popen(['docker','save',*tags],stdout=subprocess.PIPE)
    try:
        with Path(path).open('wb') as target:select_overlay(process.stdout,target,base_blobs)
        require(process.wait()==0,'NOT_AVAILABLE')
    except BaseException:
        process.kill();process.wait();raise
    finally:process.stdout.close()


class Layers:
    def __init__(self,path,base=None):
        self.overlay=tarfile.open(path);self.base=tarfile.open(base) if base else None
    def extractfile(self,name):
        try:return self.overlay.extractfile(name)
        except KeyError:
            require(self.base is not None,'NOT_AVAILABLE');return self.base.extractfile(name)
    def close(self):
        self.overlay.close()
        if self.base:self.base.close()
    def __enter__(self):return self
    def __exit__(self,*_):self.close()


def combine(base,overlay,target):
    with tarfile.open(base) as prior,tarfile.open(overlay) as current,tarfile.open(fileobj=target,mode='w|') as output:
        names={x.name for x in current.getmembers()}
        for member in prior:
            if member.isfile() and member.name.startswith('blobs/sha256/') and member.name not in names:
                output.addfile(member,prior.extractfile(member))
        for member in current:
            if member.isfile():output.addfile(member,current.extractfile(member))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('images');p.add_argument('--base',required=True);a=p.parse_args()
    path=Path(a.images);meta=json.loads(path.read_bytes());prior=meta['base_archive'];overlay=path.parent/'images.tar'
    require(sha(a.base)==prior['archive_sha256'] and sha(overlay)==meta['archive_sha256'],'CONFLICT')
    combine(a.base,overlay,sys.stdout.buffer)

if __name__=='__main__':main()
