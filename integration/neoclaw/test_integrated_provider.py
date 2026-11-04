"""Extracted independent file-fixture provider with an unchanged native consumer.

The provider's atomic-document algorithm is the already shipped independent
implementation. Model proposals are recorded; the native loop, C1, HTTPS and
history tool are real. This lane does not relabel fixture storage as DeTTa/DA.
"""
import json,os,subprocess,time,unittest
from pathlib import Path
from fusion.contracts import canonical,digest
from fusion.model_service import ModelService
from tests import test_phase2_sdk as kit
from . import test_preview_session as native
from .preview_history_qualification import attach


class InstalledNativeFeed(unittest.TestCase):
    fresh=native.NativeSessions.fresh
    finish=native.NativeSessions.finish
    @classmethod
    def setUpClass(cls):kit.InstalledKit.setUpClass.__func__(cls)
    @classmethod
    def tearDownClass(cls):kit.InstalledKit.tearDownClass.__func__(cls)

    def test_extracted_provider_selected_by_actual_native_history(self):
        evidence={}
        def provider(run,scope):
            root=self.root/'independent-native';root.mkdir()
            config=kit.prepare(root)
            config['synthetic_scopes']=[scope]
            config['principals']={'A':dict(credential='generated-native-provider',scopes={scope:['atom.storage.'+op for op in kit.server.OPERATIONS]})}
            (root/'config.json').write_bytes(canonical(config))
            process,endpoint=kit.start_installed(self.python,root,self.environment)
            def stop():
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            self.addCleanup(stop)
            selected=json.loads((root/'ready.json').read_bytes())['descriptor']
            atom=dict(composition='typed-atom-feed-https/1',principal='A',scope=scope,
                      credential='generated-native-provider',endpoint=endpoint.__dict__,descriptor=selected)
            attach(run,scope,atom)
            client=root/'conformance.json';client.write_bytes(canonical(dict(atom,deadline_ms=time.time_ns()//1000000+30000)))
            conformance=subprocess.run([str(self.python),'-I','-m','phase2_provider.conformance','--client-config',str(client)],
                cwd=root,env=self.environment,capture_output=True,text=True,timeout=35)
            self.assertEqual(conformance.returncode,0,conformance.stderr)
            evidence.update(conformance=json.loads(conformance.stdout),descriptor=selected,
                            wheel_build=json.loads((self.root/'wheels/build-manifest.json').read_bytes()))
            from .prepared_startup import source_map
            evidence['native_source']=source_map();evidence['native_source_sha256']=digest(canonical(evidence['native_source']))
            return lambda:None
        run,client,model=self.fresh(['pin task Native independent storage note','episodes current'],history=True,history_provider=provider)
        # Select the new representation once, before admission. Caller logic
        # remains NativeHistory and the same pinned native parser/tool loop.
        run.app.update(history_representation='immutable-administrative-captures/1',history_hydration='bounded-history-hydration/1');run.save()
        frozen=run.app_path.read_bytes()
        for number in range(2):
            accepted=client.invoke('submit',identity='independent-'+str(number),text='Synthetic independent history input '+str(number),assignment='notes')
            self.finish(run,run.start())
            observed=client.invoke('observe',content=True)['inputs'][number]
            self.assertEqual(observed['deadline'],accepted['deadline']);self.assertEqual(observed['state'],'complete')
        self.assertEqual(run.app_path.read_bytes(),frozen)
        captures=ModelService.inspect(model);self.assertEqual(len(captures),2)
        self.assertIn('Native independent storage note',json.loads(captures[1]['intent'])['native_prompt'])
        self.assertIn('input-receipt',observed['result']['projection'])
        self.assertIn('administrative-history-not-empirical-evidence',observed['result']['projection'])
        if os.environ.get('INTEGRATED_EVIDENCE'):
            root=Path(os.environ['INTEGRATED_EVIDENCE']);root.mkdir(parents=True,exist_ok=True)
            evidence.update(status='PASS',native_inputs=2,classification='Independent atomic-file CONTRACT FIXTURE storage; real native/C1/HTTPS; recorded model',
                            unchanged_consumer=True,next_context=True,additional_live_generations=0)
            (root/'independent-native-provider.json').write_bytes(canonical(evidence))

if __name__=='__main__':unittest.main()
