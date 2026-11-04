"""Portable named NAL: actual native loop/kernel/DeTTa and authenticated TLS.

External model/channel/context fixtures propose/observe only; no tool answer
injection. Same caller source under local and same-host network placement.
"""
import json,os,sqlite3,unittest
from pathlib import Path
from fusion.contracts import canonical,digest
from fusion.nal_envelope import PROFILE
from .controlled_run import ControlledRun
from tests.neoclaw_support import COMMAND,GOLDEN,RUNTIME,DETTA,ROOT
from integration.single_node.placement import freeze_local,compile_local


class NativePortableNal(unittest.TestCase):
    def test_native_original_local_and_https_two_occurrences_and_context(self):
        self.assertTrue(RUNTIME.is_file());self.assertTrue(DETTA.is_file())
        reports=[]
        for placement in ('local','network'):
            with self.subTest(placement=placement):
                run=ControlledRun(placement,[COMMAND,COMMAND,''],expected={'1':[[GOLDEN,1]],'2':[[GOLDEN,1]]})
                self.addCleanup(run.close)
                run.h.config['portable_execution']=PROFILE;run.h.save()
                run.h.client['portable_execution']=PROFILE;run.h.save_client()
                plan=freeze_local(run.app_path,run.h.config_path);compiled=compile_local(plan)
                self.assertFalse(compiled['effects_started'])
                original=run.h.native(COMMAND,original=True)['values'];self.assertEqual(original,[GOLDEN])
                run.operator();outcome=run.finish(run.spawn(compiled['native_argv'][1],compiled['native_argv'][2:],'native'))
                self.assertEqual(outcome,(0,{'status':'BOUNDED_STOP'}),(outcome,(run.h.root/'native.log').read_text()[-2200:]))
                rows=run.rows('app_occurrences');selected=[x for x in rows if x['premises'] is not None]
                self.assertEqual(len(selected),2);self.assertNotEqual(selected[0]['id'],selected[1]['id'])
                self.assertTrue(all(x['result']==GOLDEN and x['done']==1 for x in selected))
                with sqlite3.connect(run.h.client['database']) as db:
                    envelopes=[json.loads(x[0]) for x in db.execute('SELECT envelope FROM integrated_execution_envelopes ORDER BY rowid')]
                self.assertEqual(len(envelopes),2)
                self.assertEqual({x['task'] for x in envelopes},{x['id'] for x in selected})
                self.assertEqual(run.h.counts()['jobs'],2)
                reports.append(dict(placement=placement,placement_plan=plan,compiled_recipe=compiled,real_native_original=original,counts=run.h.counts(),
                    envelope_profiles=[x['profile'] for x in envelopes],envelopes=envelopes,
                    native_occurrences=selected,contexts=run.observations(),same_host=True,
                    additional_live_generations=0,external_substitutions='authored model/channel/context fixtures'))
                run.close()
        output=os.environ.get('INTEGRATED_NAL_EVIDENCE')
        if output:
            p=Path(output);p.mkdir(parents=True,exist_ok=False)
            files=['fusion/nal_envelope.py','fusion/execution_envelope.py','fusion/neoclaw.py','fusion/neoclaw_client.py',
                'fusion/neoclaw_transport.py','fusion/neoclaw_application.py','integration/neoclaw/native_loop.py','integration/neoclaw/host.py',__file__]
            source={str(Path(f).relative_to(ROOT)) if Path(f).is_absolute() else f:digest(Path(f).read_bytes()) for f in files}
            (p/'report.json').write_bytes(canonical(dict(status='PASS',reports=reports,runtime_sha256=digest(RUNTIME.read_bytes()),
                detta_sha256=digest(DETTA.read_bytes()),source=source,additional_live_generations=0)))

if __name__=='__main__':unittest.main()
