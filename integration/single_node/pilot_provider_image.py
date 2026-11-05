"""Export/verify the independent static Go provider without running a container.

The optional reference artifact composes with the historical Python distribution;
its source manifest remains Go-specific and never masquerades as Python sources.
"""
import argparse,gzip,io,json,shutil,struct,subprocess,tarfile
from pathlib import Path,PurePosixPath
from fusion.contracts import canonical,digest,require
from .reference_artifacts import sha

PROFILE='omega-reference-provider-artifact/1'
KIND='inspect-go'
BINARY='omega-inspect-provider'


def member_path(root,name):
    require(type(name) is str and name and not Path(name).is_absolute() and '..' not in Path(name).parts,'UNAUTHORIZED')
    path=root/name;require(path.resolve().is_relative_to(root) and not path.is_symlink(),'UNAUTHORIZED');return path


def static_elf(raw):
    require(raw[:6]==b'\x7fELF\x02\x01' and len(raw)>64,'UNSUPPORTED_PROFILE')
    machine=struct.unpack_from('<H',raw,18)[0];require(machine==62,'UNSUPPORTED_PROFILE')
    offset=struct.unpack_from('<Q',raw,32)[0];size,count=struct.unpack_from('<HH',raw,54)
    require(0<count<=32 and size>=4 and offset+size*count<=len(raw),'INVALID_ARGUMENT')
    require(all(struct.unpack_from('<I',raw,offset+i*size)[0]!=3 for i in range(count)),'UNSUPPORTED_PROFILE')


def inspect_archive(path,record,kit):
    """Verify exact exported layers, config, embedded build manifest and ELF."""
    with tarfile.open(path) as archive:
        names=[m.name for m in archive.getmembers()];require(len(names)==len(set(names)) and len(names)<=128,'CONFLICT')
        index=json.load(archive.extractfile('index.json'));require(len(index['manifests'])==1 and index['manifests'][0]['digest']==record['manifest'],'CONFLICT')
        def blob(pin):
            require(type(pin) is str and pin.startswith('sha256:') and len(pin)==71,'INVALID_ARGUMENT')
            stream=archive.extractfile('blobs/sha256/'+pin[7:]);require(stream is not None,'NOT_AVAILABLE')
            raw=stream.read(64*1024*1024+1);require(len(raw)<=64*1024*1024 and digest(raw)==pin[7:],'CONFLICT');return raw
        descriptor=json.loads(blob(record['manifest']));require(descriptor['config']['digest']==record['configuration'],'CONFLICT')
        config=json.loads(blob(record['configuration']));require(config['architecture']=='amd64' and config['os']=='linux','UNSUPPORTED_PROFILE')
        selected=config['config'];require(selected['User']=='1000:1000' and selected['Entrypoint']==['/'+BINARY]
            and selected.get('Cmd') in (None,[]) and selected.get('Env') in (None,[],['PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']),'UNSUPPORTED_PROFILE')
        require(1<=len(descriptor['layers'])<=4,'OVERLOADED');found={};diff=[]
        for layer in descriptor['layers']:
            raw=blob(layer['digest']);require(len(raw)==layer['size'],'CONFLICT')
            expanded=gzip.GzipFile(fileobj=io.BytesIO(raw)).read(64*1024*1024+1) if raw[:2]==b'\x1f\x8b' else raw
            require(len(expanded)<=64*1024*1024,'OVERLOADED');diff.append('sha256:'+digest(expanded))
            with tarfile.open(fileobj=io.BytesIO(expanded)) as files:
                for item in files:
                    path=str(PurePosixPath(item.name));require(not path.startswith('/') and '..' not in path.split('/'),'UNAUTHORIZED')
                    if item.isdir():continue
                    require(item.isfile() and path in (BINARY,'provider-build.json') and path not in found,'UNAUTHORIZED')
                    require(item.size<=32*1024*1024,'OVERLOADED');found[path]=files.extractfile(item).read()
                    if path==BINARY:require(item.mode&0o111,'UNAUTHORIZED')
        require(config['rootfs']['diff_ids']==diff and set(found)=={BINARY,'provider-build.json'},'CONFLICT')
        require(json.loads(found['provider-build.json'])==kit,'CONFLICT')
        require(digest(found[BINARY])==kit['binaries'][BINARY]['sha256'] and len(found[BINARY])==kit['binaries'][BINARY]['bytes'],'CONFLICT')
        static_elf(found[BINARY]);return dict(binary_sha256=digest(found[BINARY]),static_linux_amd64=True,files=sorted(found))


def verify(path,registered=None):
    path=Path(path).resolve();root=path.parent;raw=path.read_bytes();manifest=json.loads(raw)
    require(raw==canonical(manifest) and path.with_suffix('.sha256').read_text().strip()==digest(raw),'CONFLICT')
    require(set(manifest)=={'profile','kind','image','archive','kit','files','source_manifest_sha256','contract','container_starts','additional_live_generations'},'INVALID_ARGUMENT')
    require(manifest['profile']==PROFILE and manifest['kind']==KIND and type(manifest['container_starts']) is int
        and manifest['container_starts']==0 and type(manifest['additional_live_generations']) is int and manifest['additional_live_generations']==0,'UNSUPPORTED_PROFILE')
    indexed={}
    for item in manifest['files']:
        require(type(item) is dict and set(item)=={'path','bytes','sha256'} and item['path'] not in indexed,'CONFLICT')
        file=member_path(root,item['path']);require(file.is_file() and file.stat().st_size==item['bytes'] and sha(file)==item['sha256'],'CONFLICT')
        if registered:registered(file)
        indexed[item['path']]=file
    if registered:registered(path);registered(path.with_suffix('.sha256'))
    def member(name):require(name in indexed,'NOT_AVAILABLE');return indexed[name]
    fields=manifest['kit'];require(set(fields)=={'manifest','source_archive','provider_binary','client_binary'},'INVALID_ARGUMENT')
    kit=json.loads(member(fields['manifest']).read_bytes())
    require(kit['profile']=='omega-go-provider-starter-kit/1' and kit['status']=='PASS' and kit['external_modules']==[]
        and kit['additional_live_generations']==0 and kit['source_manifest_sha256']==digest(canonical(kit['source']))==manifest['source_manifest_sha256'],'CONFLICT')
    require(kit['contract']==manifest['contract'] and type(kit['source']) is dict and 1<=len(kit['source'])<=512,'CONFLICT')
    require(sha(member(fields['source_archive']))==kit['archive_sha256'],'CONFLICT')
    seen={}
    with tarfile.open(member(fields['source_archive'])) as archive:
        for item in archive:
            require(item.isfile() and item.name.startswith('omega-go-provider-kit/') and '..' not in item.name.split('/'),'UNAUTHORIZED')
            relative=item.name.removeprefix('omega-go-provider-kit/');require(relative in kit['source'] and relative not in seen and item.size<=1024*1024,'CONFLICT')
            seen[relative]=digest(archive.extractfile(item).read())
    require(seen==kit['source'],'CONFLICT')
    for field,name in (('provider_binary',BINARY),('client_binary','omega-client')):
        file=member(fields[field]);require(sha(file)==kit['binaries'][name]['sha256'] and file.stat().st_size==kit['binaries'][name]['bytes'],'CONFLICT')
        static_elf(file.read_bytes())
    image=manifest['image'];require(set(image)=={'repository','local_tag','manifest','configuration'},'INVALID_ARGUMENT')
    checked=inspect_archive(member(manifest['archive']),image,kit)
    return dict(status='OFFLINE_VERIFIED',profile=PROFILE,kind=KIND,repository=image['repository'],manifest=image['manifest'],
        configuration=image['configuration'],source_package=str(fields['manifest']),source_manifest_sha256=manifest['source_manifest_sha256'],
        source_kind='independent-go',contract=manifest['contract'],archive_sha256=sha(member(manifest['archive'])),
        manifest_sha256=digest(raw),exported_image=checked,container_starts=0,additional_live_generations=0)


def export(destination,tag,kit_path):
    root=Path(destination).resolve();root.mkdir(parents=True,exist_ok=False)
    kitroot=Path(kit_path).resolve();kit=json.loads((kitroot/'manifest.json').read_bytes())
    require(kit['profile']=='omega-go-provider-starter-kit/1' and kit['status']=='PASS','CONFLICT')
    copied=[]
    for filename in ('manifest.json','omega-go-provider-kit-source.tar.gz',BINARY,'omega-client','tests.log'):
        target=root/'kit'/filename;target.parent.mkdir(exist_ok=True);shutil.copyfile(kitroot/filename,target)
        copied.append(str(target.relative_to(root)))
    archive=root/'image.tar';subprocess.run(['docker','save','-o',str(archive),tag],check=True,timeout=120);copied.append('image.tar')
    with tarfile.open(archive) as tar:
        index=json.load(tar.extractfile('index.json'));require(len(index['manifests'])==1,'CONFLICT');entry=index['manifests'][0]
        descriptor=json.load(tar.extractfile('blobs/sha256/'+entry['digest'][7:]))
    actual=json.loads(subprocess.check_output(['docker','image','inspect',tag],timeout=20))[0]
    require(actual['Id']==descriptor['config']['digest'],'CONFLICT')
    local=entry['annotations']['io.containerd.image.name'];repository=local.rsplit(':',1)[0]
    manifest=dict(profile=PROFILE,kind=KIND,image=dict(repository=repository,local_tag=local,manifest=entry['digest'],configuration=descriptor['config']['digest']),
        archive='image.tar',kit=dict(manifest='kit/manifest.json',source_archive='kit/omega-go-provider-kit-source.tar.gz',
        provider_binary='kit/'+BINARY,client_binary='kit/omega-client'),files=[dict(path=p,bytes=(root/p).stat().st_size,sha256=sha(root/p)) for p in copied],
        source_manifest_sha256=kit['source_manifest_sha256'],contract=kit['contract'],container_starts=0,additional_live_generations=0)
    path=root/'provider-image.json';raw=canonical(manifest);path.write_bytes(raw);path.with_suffix('.sha256').write_text(digest(raw)+'\n')
    result=verify(path);(root/'verification.json').write_bytes(canonical(result));return result


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='operation',required=True)
    a=sub.add_parser('export');a.add_argument('destination');a.add_argument('--tag',required=True);a.add_argument('--kit',required=True)
    a=sub.add_parser('verify');a.add_argument('manifest');args=p.parse_args()
    result=export(args.destination,args.tag,args.kit) if args.operation=='export' else verify(args.manifest)
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
