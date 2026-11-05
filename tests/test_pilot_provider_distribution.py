"""Authored tiny ELF/OCI/Go-kit byte fixtures, never executable provider evidence."""
import io,json,struct,tarfile,tempfile,unittest
from pathlib import Path
from fusion.contracts import ContractError,canonical,digest
from integration.single_node.pilot_provider_image import verify,PROFILE
from integration.single_node.reference_artifacts import verify as verify_distribution
from sdk.test_preview_distribution import FixtureDistribution


def archive(entries):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w') as tar:
        for name,raw in entries.items():
            item=tarfile.TarInfo(name);item.size=len(raw);item.mode=0o755
            tar.addfile(item,io.BytesIO(raw))
    return stream.getvalue()


def elf():
    raw=bytearray(120);raw[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',raw,18,62)
    struct.pack_into('<Q',raw,32,64);struct.pack_into('<HH',raw,54,56,1);struct.pack_into('<I',raw,64,1)
    return bytes(raw)

class ProviderBundle:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True);self.files=[]
        self.source={'go/main.go':digest(b'// explicit non-runnable fixture')}
        source=archive({'omega-go-provider-kit/go/main.go':b'// explicit non-runnable fixture'});binary=elf()
        self.kit=dict(profile='omega-go-provider-starter-kit/1',status='PASS',source=self.source,
            source_manifest_sha256=digest(canonical(self.source)),contract='a'*64,archive_sha256=digest(source),external_modules=[],
            additional_live_generations=0,binaries={name:dict(sha256=digest(binary),bytes=len(binary)) for name in ('omega-client','omega-inspect-provider')})
        for path,raw in [('kit/manifest.json',canonical(self.kit)),('kit/source.tar.gz',source),
            ('kit/omega-client',binary),('kit/omega-inspect-provider',binary)]:self.file(path,raw)
        layer=archive({'omega-inspect-provider':binary,'provider-build.json':canonical(self.kit)})
        config=canonical(dict(architecture='amd64',os='linux',config=dict(User='1000:1000',Entrypoint=['/omega-inspect-provider']),rootfs=dict(diff_ids=['sha256:'+digest(layer)])))
        descriptor=canonical(dict(config=dict(digest='sha256:'+digest(config)),layers=[dict(digest='sha256:'+digest(layer),size=len(layer))]))
        self.blobs={'blobs/sha256/'+digest(v):v for v in (config,descriptor,layer)}
        self.blobs['index.json']=canonical(dict(manifests=[dict(digest='sha256:'+digest(descriptor))]))
        self.file('image.tar',archive(self.blobs))
        self.manifest=dict(profile=PROFILE,kind='inspect-go',image=dict(repository='fixture-only/inspect-go',local_tag='fixture-only/inspect-go:fixture',
            manifest='sha256:'+digest(descriptor),configuration='sha256:'+digest(config)),archive='image.tar',kit=dict(manifest='kit/manifest.json',
            source_archive='kit/source.tar.gz',provider_binary='kit/omega-inspect-provider',client_binary='kit/omega-client'),files=self.files,
            source_manifest_sha256=self.kit['source_manifest_sha256'],contract=self.kit['contract'],container_starts=0,additional_live_generations=0)
        self.save()
    def file(self,path,raw):
        target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        self.files[:]=[x for x in self.files if x['path']!=path]+[dict(path=path,bytes=len(raw),sha256=digest(raw))]
    def save(self):
        path=self.root/'provider-image.json';raw=canonical(self.manifest);path.write_bytes(raw);path.with_suffix('.sha256').write_text(digest(raw)+'\n');return path


class Distribution(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def test_independent_source_archive_binary_and_layer_bound(self):
        f=ProviderBundle(self.root/'provider');value=verify(f.save())
        self.assertEqual(value['source_kind'],'independent-go');self.assertEqual(value['container_starts'],0)
        self.assertEqual(value['source_manifest_sha256'],digest(canonical(f.source)))
    def test_outer_distribution_accepts_explicit_separate_go_binding(self):
        f=FixtureDistribution(self.root/'distribution');go=ProviderBundle(f.root/'go-provider')
        for p in go.root.rglob('*'):
            if p.is_file():f.register(str(p.relative_to(f.root)))
        f.manifest['reference_providers']={'inspect-go':'go-provider/provider-image.json'}
        f.values['components']['fusion-inspect-go']=dict(image={k:go.manifest['image'][v] for k,v in [('repository','repository'),('digest','manifest')]})
        f.write('profiles/preview.yaml',canonical(f.values));result=verify_distribution(f.save())
        self.assertEqual(result['images']['inspect-go']['source_manifest_sha256'],go.kit['source_manifest_sha256'])
        self.assertNotEqual(go.source,f.manifest['tested_source'])
        self.assertEqual(set(result['images']),{'base','caller','embedding','inspect-go'})
    def test_outer_registration_cannot_hide_unregistered_kit_bytes(self):
        f=FixtureDistribution(self.root/'distribution');go=ProviderBundle(f.root/'go-provider')
        for p in go.root.rglob('*'):
            if p.is_file() and p.name!='omega-client':f.register(str(p.relative_to(f.root)))
        f.manifest['reference_providers']={'inspect-go':'go-provider/provider-image.json'}
        with self.assertRaises(ContractError):verify_distribution(f.save())
    def test_rebinding_outer_file_cannot_replace_compiled_binary(self):
        f=ProviderBundle(self.root/'provider');f.file('kit/omega-inspect-provider',elf()+b'tamper')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):verify(f.save())
    def test_rebound_archive_with_missing_or_wrong_layer_refused(self):
        f=ProviderBundle(self.root/'provider');key=next(k for k,v in f.blobs.items() if len(v)>4096);f.blobs[key]=b'wrong'
        f.file('image.tar',archive(f.blobs))
        with self.assertRaises(ContractError):verify(f.save())
    def test_private_or_executing_metadata_refused(self):
        f=ProviderBundle(self.root/'provider');f.manifest['additional_live_generations']=True
        with self.assertRaises(ContractError):verify(f.save())
        f.manifest['additional_live_generations']=0;f.manifest['container_starts']=1
        with self.assertRaises(ContractError):verify(f.save())
