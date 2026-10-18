"""Closed-input errors, fresh-journal refusal and local owner independence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import time
import unittest
from fusion import promotion_contracts as c
from fusion.contracts import ContractError,canonical
from fusion.promotion import PromotionOwner
from fusion.adapters.native_promotion import source
from .test_promotion_owner import Harness,OUT

class PromotionGuards(unittest.TestCase):
    def each(self):
        for kind in ('sqlite','file-fixture'):
            h=Harness(kind);self.addCleanup(h.close);yield h
    def test_bound_identity_changed_semantics_is_conflict(self):
        for h in self.each():
            o=h.owner();q=h.request();b=o.bind(q);o.adjust(b)
            changed=copy.deepcopy(q);changed['delta']=-1
            with self.assertRaises(ContractError) as failure:o.bind(changed)
            self.assertEqual(failure.exception.code,'CONFLICT')
            wrong=copy.deepcopy(b);wrong['request']=changed
            with self.assertRaises(ContractError) as failure:o.adjust(wrong)
            self.assertEqual(failure.exception.code,'CONFLICT')
    def test_malformed_bindings_are_contract_errors(self):
        for h in self.each():
            o=h.owner()
            for value in ({},None,dict(request={}),dict(request=h.request(),revision=0,time=float('nan'),clock='other')):
                for op in ('adjust','observe','scores','rank'):
                    with self.subTest(provider=h.kind,value=str(value),operation=op):
                        with self.assertRaises(ContractError):getattr(o,op)(value)
    def test_legacy_sqlite_is_refused_without_modification(self):
        h=Harness('sqlite');self.addCleanup(h.close);path=h.root/'legacy.sqlite'
        with sqlite3.connect(path) as db:db.execute('CREATE TABLE kv(key BLOB PRIMARY KEY,value REAL,lasttime REAL)');db.execute('INSERT INTO kv VALUES(?,?,?)',(b'generated',2.,100.))
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaises(ContractError) as failure:PromotionOwner(path,h.access,h.math)
        self.assertEqual(failure.exception.code,'UNSUPPORTED_PROFILE')
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)
    def test_invalid_clock_and_context_capacity(self):
        for h in self.each():
            o=h.owner()
            for clock in (float('nan'),float('inf'),-1,True,10**1000):
                h.now=clock
                with self.assertRaises(ContractError):o.bind(h.request())
            h.now=2000000000.
            for i in range(c.MAX_CONTEXTS):q=h.request('scores');q['context']=str(i);o.bind(q)
            q=h.request('scores');q['context']='over'
            with self.assertRaises(ContractError) as failure:o.bind(q)
            self.assertEqual(failure.exception.code,'OVERLOADED')
    def test_math_and_owner_do_not_load_cognitive_or_embedding_runtimes(self):
        import sys
        for h in self.each():
            self.assertEqual(h.adjust()['value'],1.)
            self.assertNotIn('lib_nal',source(Path(h.math.runtime['mettaclaw'])))
        missing={name:importlib.util.find_spec(name) is None for name in ('torch','sentence_transformers','transformers')}
        # The explicit minimal-environment gate runs this module under uv 3.11.
        if os.environ.get('S05_REQUIRE_MINIMAL')=='1':self.assertTrue(all(missing.values()))
        self.assertFalse({'fusion.nal_beliefs','fusion.nal_episodes','fusion.inference'} & set(sys.modules))
        OUT.mkdir(parents=True,exist_ok=True);(OUT/'owner-dependencies.json').write_bytes(canonical(dict(absent=missing,
            cognitive_modules_loaded=False,pure_native_dependency='PeTTa/SWI source-checked promotion expressions; no NAL library execution')))

    def test_pure_runtime_with_cognitive_sources_absent(self):
        import shutil
        import tempfile
        from fusion.adapters.native_promotion import NativePromotion
        from .test_promotion_owner import RUNTIME
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=json.loads(RUNTIME.read_text());runtime=copy.deepcopy(original)
            omega=root/'memory-source';(omega/'src').mkdir(parents=True)
            shutil.copyfile(Path(original['mettaclaw'])/'src/memory.metta',omega/'src/memory.metta')
            petta=root/'interpreter';shutil.copytree(Path(original['petta'])/'src',petta/'src')
            runtime.update(mettaclaw=str(omega),petta=str(petta))
            manifest=root/'runtime.json';manifest.write_bytes(canonical(runtime))
            build=json.loads((RUNTIME.parent/'build.json').read_text())
            build['runtime_sha256']=hashlib.sha256(manifest.read_bytes()).hexdigest()
            (root/'build.json').write_bytes(canonical(build))
            # Reuse the exact verified native libraries; install no cognitive libs.
            (root/'swipl').symlink_to(RUNTIME.parent/'swipl',target_is_directory=True)
            self.assertFalse((omega/'lib_nal.metta').exists());self.assertFalse((petta/'lib').exists())
            math=NativePromotion(manifest);results=[]
            for h in self.each():
                h.math=math;first=h.adjust();h.now+=86400.5;second=h.adjust(-1)
                self.assertEqual(first['value'],1.);self.assertEqual(second['value'],0.)
                results.append(dict(provider=h.kind,first=first['value'],second=second['value']))
            # The smaller dependency still refuses changed policy or interpreter.
            memory=omega/'src/memory.metta';before=memory.read_bytes();memory.write_bytes(before+b'\n')
            with self.assertRaises(ContractError) as failure:NativePromotion(manifest)
            self.assertEqual(failure.exception.code,'UNSUPPORTED_PROFILE');memory.write_bytes(before)
            main=petta/'src/main.pl';main.write_bytes(main.read_bytes()+b'\n')
            with self.assertRaises(ContractError) as failure:NativePromotion(manifest)
            self.assertEqual(failure.exception.code,'UNSUPPORTED_PROFILE')
            OUT.mkdir(parents=True,exist_ok=True)
            (OUT/'minimal-native-source.json').write_bytes(canonical(dict(
                mettaclaw_files=['src/memory.metta'],petta_files='src/ interpreter files only',
                nal_source_present=False,pln_library_present=False,source_tampering='rejected',
                runtime='same pinned SWI/Python/libraries; relocated source-only manifest',owners=results)))

if __name__=='__main__':unittest.main()
