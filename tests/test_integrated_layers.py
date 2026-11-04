"""Archive algorithm fixtures; actual final-image verification is a build gate."""
import io,json,tarfile,tempfile,unittest
from pathlib import Path
from fusion.contracts import ContractError
from integration.single_node.image_layers import select_overlay,combine,Layers,base_selection
from integration.single_node.reference_artifacts import sha

def archive(entries):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w') as tar:
        for name,value in entries.items():
            row=tarfile.TarInfo(name);row.size=len(value);tar.addfile(row,io.BytesIO(value))
    return out.getvalue()

class ImageLayers(unittest.TestCase):
    def test_delta_resolves_base_and_combined_stream_replaces_only_final_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'base.tar';overlay=root/'images.tar'
            base.write_bytes(archive({'blobs/sha256/aa':b'large-assets','index.json':b'old'}))
            full=io.BytesIO(archive({'blobs/sha256/aa':b'large-assets','blobs/sha256/bb':b'new-source','index.json':b'new'}))
            out=io.BytesIO();select_overlay(full,out,{'blobs/sha256/aa'});overlay.write_bytes(out.getvalue())
            with tarfile.open(overlay) as tar:self.assertNotIn('blobs/sha256/aa',tar.getnames())
            with Layers(overlay,base) as layers:
                self.assertEqual(layers.extractfile('blobs/sha256/aa').read(),b'large-assets')
                self.assertEqual(layers.extractfile('index.json').read(),b'new')
            out=io.BytesIO();combine(base,overlay,out)
            with tarfile.open(fileobj=io.BytesIO(out.getvalue())) as tar:
                self.assertEqual(tar.extractfile('index.json').read(),b'new')
                self.assertEqual(len(tar.getmembers()),3)
    def test_changed_base_is_refused_before_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'base.tar';manifest=root/'images.json'
            base.write_bytes(archive({'blobs/sha256/aa':b'assets'}))
            manifest.write_text(json.dumps(dict(source_export_verification='PASS',archive_sha256=sha(base))))
            self.assertEqual(base_selection(base,manifest)[1],{'blobs/sha256/aa'})
            base.write_bytes(base.read_bytes()+b'drift')
            with self.assertRaisesRegex(ContractError,'CONFLICT'):base_selection(base,manifest)
    def test_unsafe_archive_name_is_refused_without_extraction(self):
        with self.assertRaisesRegex(ContractError,'INVALID_ARGUMENT'):
            select_overlay(io.BytesIO(archive({'../owner.sqlite':b'bad'})),io.BytesIO(),set())

if __name__=='__main__':unittest.main()
