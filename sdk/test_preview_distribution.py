"""Offline preview/legacy verifier fixtures, never runnable role images.

The OCI descriptors, source packages, chart and wheel ZIPs below are tiny
authored fixtures. Nothing is installed, imported from a wheel, extracted into
an owner, executed in a container, or submitted to a runtime/cluster.
"""
import copy
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import zipfile

from fusion.contracts import ContractError, canonical, digest
from fusion.preview_deployment_contracts import COMPOSITION
from integration.single_node.reference_artifacts import verify


class FixtureDistribution:
    def __init__(self, root, *, legacy=False, chain=False):
        self.root = Path(root)
        self.root.mkdir(parents=True)
        self.manifest = dict(schema='omega-single-node-distribution/1' if legacy else
            'omega-single-node-preview-distribution/1', files=[], images={}, tested_source={},
            image_archive='images.tar')
        self.source_bytes = {role: ('# explicit ' + role + ' fixture bytes\n').encode()
                             for role in ('client','operator','provider')}
        self.source_paths = {role: ('integration/single_node/' if role == 'operator' else 'fusion/')
                             + 'fixture_' + role + '.py' for role in self.source_bytes}
        self.manifest['tested_source'] = {self.source_paths[k]:digest(v) for k,v in self.source_bytes.items()}
        kinds = ('base','caller','embedding') + (('chain',) if chain else ())
        self.blobs = {}
        imported = []
        for kind in kinds:
            config = canonical(dict(architecture='amd64',fixture_only=kind))
            descriptor = canonical(dict(config=dict(digest='sha256:'+digest(config)),layers=[]))
            config_id, descriptor_id = 'sha256:'+digest(config), 'sha256:'+digest(descriptor)
            self.blobs[digest(config)], self.blobs[digest(descriptor)] = config, descriptor
            package = 'source/'+kind+'.json'
            self.write(package, canonical(dict(source=self.manifest['tested_source'])))
            self.manifest['images'][kind] = dict(repository='fixture-only/'+kind,manifest=descriptor_id,
                configuration=config_id,source_package=package,
                source_manifest_sha256=digest(canonical(self.manifest['tested_source'])))
            imported.append(dict(kind=kind,repository='fixture-only/'+kind,
                local_tag='fixture-only/'+kind+':fixture',manifest_digest=descriptor_id,configuration_digest=config_id))
        with tarfile.open(self.root/'images.tar','w') as tar:
            for checksum,raw in self.blobs.items():
                entry=tarfile.TarInfo('blobs/sha256/'+checksum);entry.size=len(raw)
                tar.addfile(entry,io.BytesIO(raw))
        self.register('images.tar')
        self.write('images.json',canonical(dict(archive_sha256=digest((self.root/'images.tar').read_bytes()),images=imported)))
        image=self.manifest['images']['base']
        self.values=dict(image=dict(repository=image['repository'],digest=image['manifest']),
            components={},preview=dict(profile=COMPOSITION,enabled=True,model_boundary='RECORDED_FIXTURE'))
        if chain:self.values['preview']['chain']=dict(enabled=True,nodeEnabled=False,isolationVerified=False,registration=None)
        if legacy:
            self.manifest['profile_directory']='profiles'
            for name in ('deterministic','memory','workflow','cognitive','chain'):
                self.write('profiles/'+name+'.yaml',canonical(dict(image=self.values['image'])))
            self.write('profiles/generative-image.json',canonical(self.values['image']))
        else:
            self.manifest.update(model_boundary='RECORDED_FIXTURE',live_generation_authorization=0,
                profile_files=['profiles/preview.yaml'],chart='chart/fixture-chart.tgz',
                sdk_build_manifest='wheelhouse/build-manifest.json',wheel_inventory='wheelhouse/inventory.json')
            self.write('profiles/preview.yaml',canonical(self.values))
            self.write('chart/fixture-chart.tgz',b'explicit unused chart fixture bytes')
            self.build=dict(schema='fusion-preview-sdk-build/1',live_generations=0)
            for role in self.source_bytes:
                self.set_wheel(role,self.source_bytes[role])
            self.save_wheels()
        self.save()

    def write(self, relative, raw):
        path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        self.register(relative)

    def register(self, relative):
        raw=(self.root/relative).read_bytes()
        self.manifest['files']=[x for x in self.manifest['files'] if x['path'] != relative]
        self.manifest['files'].append(dict(path=relative,bytes=len(raw),sha256=digest(raw)))

    def read(self, relative):
        return json.loads((self.root/relative).read_bytes())

    def set_wheel(self, role, raw, *, metadata_raw=None):
        name='fixture_'+role+'-0.0.0-py3-none-any.whl'
        target=self.source_paths[role]
        bound=raw if metadata_raw is None else metadata_raw
        sources={target:dict(source=target,bytes=len(bound),sha256=digest(bound))}
        path=self.root/'wheelhouse'/name;path.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(path,'w') as archive:
            archive.writestr(target,raw)
            archive.writestr('fixture_'+role+'-0.0.0.dist-info/source-manifest.json',
                canonical(dict(schema='byte-exact-source-wheel/1',sources=sources)))
        self.register('wheelhouse/'+name)
        self.build[role]=dict(file=name,sha256=digest(path.read_bytes()),sources=sources)

    def save_wheels(self):
        self.write('wheelhouse/build-manifest.json',canonical(self.build))
        self.write('wheelhouse/inventory.json',canonical(dict(schema='fusion-wheel-dependency-license-inventory/1',
            packages=[dict(artifact=self.build[r]['file'],sha256=self.build[r]['sha256'])
                      for r in ('client','operator','provider')])))

    def save(self):
        path=self.root/'distribution.json';raw=canonical(self.manifest)
        path.write_bytes(raw);path.with_suffix('.sha256').write_text(digest(raw)+'\n')
        return path


class PreviewDistributionFixtures(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='fusion-distribution-fixture-')
        self.root=Path(self.temporary.name)
        self.serial=0

    def tearDown(self):
        self.temporary.cleanup()

    def fixture(self, **kwargs):
        self.serial+=1
        return FixtureDistribution(self.root/str(self.serial),**kwargs)

    def refuses(self, fixture, code='CONFLICT'):
        with self.assertRaises(ContractError) as error:verify(fixture.save())
        self.assertEqual(error.exception.code,code)

    def test_preview_accepts_declared_fixtures_without_generative_artifacts(self):
        for chain in (False,True):
            with self.subTest(isolated_chain_image=chain):
                f=self.fixture(chain=chain);value=verify(f.save())
                self.assertEqual(value['status'],'OFFLINE_VERIFIED')
                self.assertEqual(value['manifest_sha256'],digest(f.save().read_bytes()))
                self.assertEqual(value['additional_live_generations'],0)
                self.assertEqual(value['generative_runtime_availability'],'NOT_CHECKED')
                self.assertFalse((f.root/'profiles/generative-image.json').exists())

    def test_legacy_schema_still_verifies_its_historical_profile_layout(self):
        f=self.fixture(legacy=True)
        self.assertEqual(verify(f.save())['status'],'OFFLINE_VERIFIED')
        (f.root/'profiles/memory.yaml').write_bytes(b'changed without registered digest')
        self.refuses(f)

    def test_manifest_canonical_bytes_and_external_digest_are_bound(self):
        f=self.fixture();path=f.save();path.with_suffix('.sha256').write_text('0'*64+'\n')
        with self.assertRaises(ContractError):verify(path)
        path=f.save();path.write_text(json.dumps(f.manifest,indent=2))
        path.with_suffix('.sha256').write_text(digest(path.read_bytes())+'\n')
        with self.assertRaises(ContractError):verify(path)

    def test_files_are_unique_contained_and_digest_bound(self):
        for mode in ('digest','duplicate','absolute','traversal','symlink-outside'):
            with self.subTest(mode=mode):
                f=self.fixture();record=copy.deepcopy(f.manifest['files'][0])
                if mode=='digest':record['sha256']='0'*64;f.manifest['files'][0]=record
                elif mode=='duplicate':f.manifest['files'].append(record)
                else:
                    outside=self.root/('outside-'+str(self.serial));outside.write_bytes(b'fixture external file')
                    relative=str(outside) if mode=='absolute' else '../'+outside.name
                    if mode=='symlink-outside':
                        relative='linked-fixture';(f.root/relative).symlink_to(outside)
                    f.manifest['files'].append(dict(path=relative,bytes=outside.stat().st_size,sha256=digest(outside.read_bytes())))
                self.refuses(f)

    def test_secondary_artifact_references_must_be_registered(self):
        for field in ('image_archive','chart','sdk_build_manifest','wheel_inventory','source_package','profile_files'):
            with self.subTest(field=field):
                f=self.fixture();unregistered='unregistered-fixture.json'
                (f.root/unregistered).write_bytes(b'{}')
                if field=='source_package':f.manifest['images']['base'][field]=unregistered
                elif field=='profile_files':f.manifest[field]=[unregistered]
                else:f.manifest[field]=unregistered
                self.refuses(f)

    def test_preview_schema_profile_and_authority_are_closed(self):
        cases=[('schema','UNSUPPORTED_PROFILE'),('profile','UNSUPPORTED_PROFILE'),
            ('model-boundary','UNSUPPORTED_PROFILE'),('authority','UNAUTHORIZED'),
            ('bool-authority','UNAUTHORIZED'),('future-live','UNAUTHORIZED'),
            ('top-live','UNAUTHORIZED'),('workflow-live','UNAUTHORIZED'),
            ('chain-node','UNAUTHORIZED')]
        for case,code in cases:
            with self.subTest(case=case):
                f=self.fixture(chain=True);v=copy.deepcopy(f.values)
                if case=='schema':f.manifest['schema']='omega-single-node-preview-distribution/99'
                elif case=='profile':v['preview']['profile']='foreign/1'
                elif case=='model-boundary':v['preview']['model_boundary']='LIVE'
                elif case=='authority':f.manifest['live_generation_authorization']=1
                elif case=='bool-authority':f.manifest['live_generation_authorization']=False
                elif case=='future-live':v['futureLive']=dict(enabled=True,activated=False)
                elif case=='top-live':v['liveEnabled']=True
                elif case=='workflow-live':v['workflow']=dict(mode='live',liveEnabled=True)
                else:v['preview']['chain']['nodeEnabled']=True
                f.write('profiles/preview.yaml',canonical(v));self.refuses(f,code)

    def test_profile_files_and_image_selections_are_bound(self):
        for case in ('empty-profiles','duplicate-profiles','foreign-image','missing-kind','duplicate-kind'):
            with self.subTest(case=case):
                f=self.fixture()
                if case=='empty-profiles':f.manifest['profile_files']=[]
                elif case=='duplicate-profiles':f.manifest['profile_files']*=2
                elif case=='foreign-image':
                    v=copy.deepcopy(f.values);v['image']['digest']='sha256:'+'f'*64
                    f.write('profiles/preview.yaml',canonical(v))
                else:
                    imported=f.read('images.json')
                    if case=='missing-kind':imported['images']=imported['images'][1:]
                    else:imported['images'].append(imported['images'][0])
                    f.write('images.json',canonical(imported))
                self.refuses(f)

    def test_source_package_binding_is_not_an_unchecked_label(self):
        f=self.fixture();package=f.read('source/base.json');package['source']={}
        f.write('source/base.json',canonical(package))
        f.manifest['images']['base']['source_manifest_sha256']=digest(canonical({}))
        self.refuses(f)

    def test_preview_image_import_repository_must_match_selection(self):
        f=self.fixture();imported=f.read('images.json')
        imported['images'][0]['repository']='fixture-only/other-import-name'
        f.write('images.json',canonical(imported));self.refuses(f)
        # Historical records did not require this optional import label.
        legacy=self.fixture(legacy=True);imported=legacy.read('images.json')
        for item in imported['images']:item.pop('repository')
        legacy.write('images.json',canonical(imported))
        self.assertEqual(verify(legacy.save())['status'],'OFFLINE_VERIFIED')

    def test_oci_configuration_link_and_bytes_are_bound(self):
        f=self.fixture();f.manifest['images']['base']['configuration']='sha256:'+'f'*64
        imported=f.read('images.json');imported['images'][0]['configuration_digest']='sha256:'+'f'*64
        f.write('images.json',canonical(imported));self.refuses(f)

    def test_wheel_payload_and_tested_source_are_independently_checked(self):
        for stale_metadata in (False,True):
            with self.subTest(stale_embedded_metadata=stale_metadata):
                f=self.fixture();changed=b'# different fixture implementation\n'
                f.set_wheel('operator',changed,metadata_raw=f.source_bytes['operator'] if stale_metadata else None)
                f.save_wheels();self.refuses(f)

    def test_inventory_duplicate_or_changed_wheel_digest_refuses(self):
        for case in ('duplicate','digest'):
            with self.subTest(case=case):
                f=self.fixture();inventory=f.read('wheelhouse/inventory.json')
                if case=='duplicate':inventory['packages'].append(inventory['packages'][0])
                else:inventory['packages'][0]['sha256']='f'*64
                f.write('wheelhouse/inventory.json',canonical(inventory));self.refuses(f)


if __name__=='__main__':unittest.main()
