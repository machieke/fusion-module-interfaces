"""Physical layout tests; explicit byte/native fixture except standalone recipe."""
import fcntl
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fusion.adapters import detta_layout as d
from fusion.contracts import ContractError, canonical, digest


class NativeFixture:
    values = {}
    calls = []
    fail = False
    def __init__(self,binary,root,*,owner_fds=()):self.root=root;self.owner_fds=owner_fds
    def put(self,scope,coordinate,data):
        self.calls.append(('put',self.root));key=digest(canonical([scope,coordinate,digest(data)]))
        self.values[(self.root,key)]=data
        if self.fail:raise ContractError('NOT_AVAILABLE')
        return key,dict(provider='detta-local-rs/1',durability='local-files-process-restart',evidence={'fixture':True})
    def get(self,scope,key):self.calls.append(('get',self.root));return self.values[(self.root,key)]
    def availability(self,scope,key):return dict(content_hash=digest(self.get(scope,key)),available=True)


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'payloads'
        NativeFixture.values={};NativeFixture.calls=[];NativeFixture.fail=False
        self.mock=patch('fusion.adapters.detta.DettaStorage',NativeFixture);self.mock.start();self.addCleanup(self.mock.stop)
        self.owner=d.storage('FIXTURE',self.root,d.LAYOUT)
    def reject(self,code,fn,*args):
        with self.assertRaises(ContractError) as got:fn(*args)
        self.assertEqual(got.exception.code,code)
    def test_distinct_opaque_coordinates_and_scopes_have_independent_native_roots(self):
        entries=[(s,k,self.owner.put(s,k,b'generated')[0]) for s,k in [('A','key'),('A','second'),('B','key')]]
        self.assertEqual(len({r for op,r in NativeFixture.calls}),3)
        for s,k,locator in entries:self.assertEqual(self.owner.get(s,locator),b'generated')
    def test_reopen_preserves_locator_receipt_and_bytes(self):
        value=self.owner.put('A','key',b'generated');owner=d.storage('FIXTURE',self.root,d.LAYOUT)
        self.assertEqual(owner.put('A','key',b'generated'),value)
        self.assertEqual(owner.get('A',value[0]),b'generated')
        self.assertEqual(value[1]['evidence']['storage_layout'],d.LAYOUT)
    def test_changed_intent_after_native_commit_before_acceptance_refuses(self):
        NativeFixture.fail=True;self.reject('NOT_AVAILABLE',self.owner.put,'A','key',b'first')
        NativeFixture.fail=False;calls=len(NativeFixture.calls)
        self.reject('CONFLICT',self.owner.put,'A','key',b'changed')
        self.assertEqual(len(NativeFixture.calls),calls)
        locator,_=self.owner.put('A','key',b'first');self.assertEqual(self.owner.get('A',locator),b'first')
    def test_foreign_scope_denied_before_native_read(self):
        locator,_=self.owner.put('A','key',b'data');calls=len(NativeFixture.calls)
        for fn in (self.owner.get,self.owner.availability):self.reject('UNAUTHORIZED',fn,'B',locator)
        self.assertEqual(len(NativeFixture.calls),calls)
    def test_closed_locator_does_not_resolve_paths_or_extra_fields(self):
        locator,_=self.owner.put('A','key',b'data');value=json.loads(locator)
        for bad in ('../escape',locator+' ',canonical(dict(value,extra='path')).decode(),canonical(dict(value,coordinate='../escape')).decode()):
            self.reject('NOT_AVAILABLE',self.owner.get,'A',bad)
    def test_missing_partition_does_not_recreate_it(self):
        locator,_=self.owner.put('A','key',b'data');v=json.loads(locator);v['coordinate']='0'*64
        self.reject('NOT_AVAILABLE',self.owner.get,'A',canonical(v).decode())
        self.assertFalse((self.root/v['scope']/v['coordinate']).exists())
    def test_native_content_hash_remains_verified(self):
        locator,_=self.owner.put('A','key',b'data');v=json.loads(locator);key=(str(self.root/v['scope']/v['coordinate']),v['manifest'])
        NativeFixture.values[key]=b'corrupt'
        self.reject('NOT_AVAILABLE',self.owner.get,'A',locator)
        self.reject('NOT_AVAILABLE',self.owner.availability,'A',locator)
    def test_manifest_seal_checked_before_native_read(self):
        locator,_=self.owner.put('A','key',b'data');v=json.loads(locator);v['manifest']='0'*64
        self.reject('NOT_AVAILABLE',self.owner.get,'A',canonical(v).decode())
    def test_global_lock_rejects_other_partition_operations(self):
        with (self.root/'.port.lock').open('a+b') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            self.reject('OVERLOADED',self.owner.put,'B','new',b'data')
            self.reject('OVERLOADED',d.storage,'FIXTURE',self.root,d.LAYOUT)
    def test_legacy_selection_refuses_new_layout(self):
        self.reject('UNSUPPORTED_PROFILE',d.storage,'FIXTURE',self.root)
    def test_new_layout_refuses_populated_unsealed_root(self):
        root=Path(self.tmp.name)/'legacy';root.mkdir();(root/'native-record').write_bytes(b'retained')
        self.reject('UNSUPPORTED_PROFILE',d.storage,'FIXTURE',root,d.LAYOUT)
        self.assertEqual((root/'native-record').read_bytes(),b'retained')
    def test_unknown_layout_refuses_without_creating_root(self):
        root=Path(self.tmp.name)/'unknown';self.reject('UNSUPPORTED_PROFILE',d.storage,'FIXTURE',root,'unknown/1');self.assertFalse(root.exists())
    def test_pending_seal_recovers_only_identical_selection(self):
        root=Path(self.tmp.name)/'pending';root.mkdir();(root/'layout.pending').write_bytes(canonical(dict(layout=d.LAYOUT,locator='scope-coordinate-manifest/1')))
        d.storage('FIXTURE',root,d.LAYOUT);self.assertTrue((root/'layout.json').is_file())
    def test_linked_partition_refused(self):
        root=self.root/digest(b'A');root.symlink_to(self.tmp.name,target_is_directory=True)
        self.reject('UNSUPPORTED_PROFILE',self.owner.put,'A','key',b'data')

    def test_linked_metadata_refused_before_hydration(self):
        locator,_=self.owner.put('A','key',b'data');v=json.loads(locator)
        path=self.root/v['scope']/v['coordinate']/'record.json';outside=Path(self.tmp.name)/'outside'
        outside.write_bytes(path.read_bytes());path.unlink();path.symlink_to(outside)
        self.reject('NOT_AVAILABLE',self.owner.get,'A',locator)

    def test_outer_lock_is_given_to_native_backend(self):
        original=NativeFixture.put
        def observed(backend,*args):
            self.assertEqual(len(backend.owner_fds),1)
            import os
            self.assertEqual(os.fstat(backend.owner_fds[0]).st_ino,(self.root/'.port.lock').stat().st_ino)
            return original(backend,*args)
        with patch.object(NativeFixture,'put',observed):self.owner.put('A','key',b'data')

    def test_real_parent_kill_leaves_global_lock_with_running_backend_fixture(self):
        # Real subprocess/FD inheritance; the sleeping native executable is an
        # explicit fixture and does not establish a real DeTTa write result.
        import os,signal,subprocess,sys,time
        marker=Path(self.tmp.name)/'backend.pid';binary=Path(self.tmp.name)/'sleeping-native'
        binary.write_text('#!'+sys.executable+'\nimport os,time,json,sys\nfrom pathlib import Path\njson.load(sys.stdin)\nPath('+repr(str(marker))+').write_text(str(os.getpid()))\ntime.sleep(30)\n')
        binary.chmod(0o700);root=Path(self.tmp.name)/'inherited'
        code='from fusion.adapters.detta_layout import CoordinateStorage\nCoordinateStorage('+repr(str(binary))+','+repr(str(root))+').put("A","key",b"synthetic")'
        child=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        native=None
        try:
            until=time.monotonic()+5
            while not marker.exists() and time.monotonic()<until:time.sleep(.01)
            self.assertTrue(marker.exists());native=int(marker.read_text())
            child.kill();child.wait(timeout=5)
            self.reject('OVERLOADED',d.storage,'FIXTURE',root,d.LAYOUT)
        finally:
            if native:
                try:os.kill(native,signal.SIGKILL)
                except ProcessLookupError:pass
            if child.poll() is None:child.kill()
            child.communicate(timeout=5)

if __name__=='__main__':unittest.main()
