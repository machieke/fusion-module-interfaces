"""Actual native S04 loop with real E5/Chroma/DeTTa/NAL; declared model/channel fixtures."""
import copy
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import unittest
from fusion.contracts import canonical,digest,ContractError
from fusion.neoclaw_application import Application
from fusion import nal_memory_contracts as c
from .controlled_run import ControlledRun
from .evidence_composition import configure,SCOPE,TEXT as SOURCE_TEXT
from .evidence_oracle import SOURCE_LABEL
from .evidence_run import commands,report,execute
from .append_oracle import TEXT,QUERY,CREATED
from .embedding_run import start
from .memory_composition import ROOT

EVIDENCE=Path(os.environ.get('S04_EVIDENCE',ROOT/'artifacts/s04/tests'))


class NativeEvidenceLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus=json.loads((ROOT/'artifacts/s04/corpus.json').read_text());EVIDENCE.mkdir(parents=True,exist_ok=True)
    def setup_run(self,responses=None,sources=None):
        run=ControlledRun('local',responses or commands(),search={'boundary':'recorded-response'});self.addCleanup(run.close)
        run.model['expected_feedback']={};run.save();cfg=configure(run,self.corpus,sources=sources);return run,cfg
    def evidence(self,name,value):(EVIDENCE/(name+'.json')).write_bytes(canonical(value))
    def finish(self,run):
        p=start(run);p.wait(timeout=120);result=run.finish(p)
        self.assertEqual(result,(0,{'status':'BOUNDED_STOP'}),(run.h.root/'native.log').read_text()[-14000:])
    def pause(self,run,stage):
        run.app['pause_at']=stage;run.save();run.operator();p=start(run)
        run.h.wait_file(run.app['failpoint_marker'],p,seconds=45);return p
    def resume(self,run):run.app.pop('pause_at',None);run.save();self.finish(run)

    def test_native_dispatch_duplicate_contrary_readback_and_no_vector_rebuild(self):
        value=execute(self.corpus)
        old,new=value['read_receipts'][0:2]
        self.assertEqual(old['request']['snapshot'],new['request']['snapshot'])
        self.assertNotEqual(value['app_query_views'][0]['view'],value['app_query_views'][1]['view'])
        self.assertIn('_apostrophe_stv_apostrophe_, 1.0, 0.5',value['observations'][2]['feedback'])
        self.assertIn('_apostrophe_stv_apostrophe_, 1.0, 0.6666666666666666',value['observations'][4]['feedback'])
        self.assertIn(SOURCE_LABEL.replace(' ','_'),str(value['observations'][1]['context']))
        self.assertEqual(len(value['owner_budget_audit']),2);self.assertTrue(all(x['evaluations']==1 for x in value['owner_budget_audit']))
        self.assertIn('_apostrophe_stv_apostrophe_, 0.6666666666666666, 0.75',value['observations'][10]['feedback'])
        oracle=json.loads((ROOT/'evidence/s04/native-oracle-fresh.json').read_text())
        self.assertEqual(oracle['observations'][3]['feedback'],value['observations'][4]['feedback'])
        self.evidence('native-loop',value)

    def test_real_process_kills_across_independent_commits(self):
        stages=['after_source_acceptance','after_assessment_acceptance','after_formula','after_evidence_decision_commit',
                'after_evidence_ack_commit','after_belief_view_selection','after_assessment_result_capture']
        traces=[]
        responses=commands()[:4]+['']
        for stage in stages:
            with self.subTest(stage=stage):
                run,cfg=self.setup_run(responses);p=self.pause(run,stage)
                # Application audit while paused cannot acquire its exclusive lock.
                with sqlite3.connect(run.h.client['database']) as db:
                    before=[list(x) for x in db.execute('SELECT id,deadline FROM app_occurrences ORDER BY turn,position')]
                    sources=[list(x) for x in db.execute('SELECT slot,accepted,receipt FROM app_sources ORDER BY slot')]
                run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL);self.resume(run);after=report(run,cfg)
                self.assertEqual(before,[[x['id'],x['deadline']] for x in after['occurrences'][:len(before)]])
                self.assertEqual(sources[0][1],canonical(after['app_sources'][0]['accepted']).decode())
                self.assertEqual(after['pending'],());self.assertEqual(len(after['app_assessments']),1)
                decision=after['app_assessments'][0]['decision'];self.assertEqual(len(decision['snapshot']['observations']),1)
                self.assertEqual(len(decision['snapshot']['supports']),3)
                evaluations=after['owner_budget_audit'][0]['evaluations'];self.assertEqual(evaluations,2 if stage=='after_formula' else 1)
                self.assertIn('_apostrophe_stv_apostrophe_, 1.0, 0.6666666666666666',after['observations'][4]['feedback'])
                traces.append(dict(stage=stage,signal='SIGKILL',before=before,after=after));run.close()
        self.evidence('native-kills',traces)

    def test_old_view_replay_and_deleted_presentation_rebuild(self):
        run,cfg=self.setup_run();run.operator();self.finish(run);before=report(run,cfg)
        app=Application(run.app_path)
        try:
            queries=app.db.execute("SELECT o.* FROM app_occurrences o JOIN app_query_views v ON v.id=o.id ORDER BY turn").fetchall()
            old=app.write.view_for(queries[0]);new=app.write.view_for(queries[1])
            self.assertEqual(app._run(queries[0]),queries[0]['result']);self.assertNotEqual(old['metadata_seal'],new['metadata_seal'])
            path=app.evidence.modules.root/'presentation'/digest(canonical(new));path.unlink()
            with self.assertRaises(ContractError):app.evidence.projection(new)
            repaired=app.evidence.materialize(new,int(time.time()*1000)+10000)
            self.assertEqual(repaired.read_bytes(),canonical(new));app.evidence.projection(new)
            self.assertEqual(app._run(queries[1]),queries[1]['result']);self.assertEqual(app.write.view_for(queries[0]),old)
        finally:app.close()
        after=report(run,cfg)
        self.assertEqual(before['publication_audit'],after['publication_audit']);self.assertEqual(before['owner_budget_audit'],after['owner_budget_audit'])
        self.evidence('view-repair',dict(before=before,after=after,repair='explicit authorized derived-only reconstruction; original query view retained'))

    def test_ambiguous_memory_source_and_missing_source_refused_before_effects(self):
        target=CREATED.replace(' ','_');source=SOURCE_LABEL.replace(' ','_');traces=[]
        cases=[('ambiguous-memory',['remember '+TEXT,'remember '+TEXT,'support '+target+' '+source,''],None,'CONFLICT'),
            ('missing-source',['remember '+TEXT,'support '+target+' 2031-04-05_23:59:59',''],None,'NOT_FOUND'),
            ('ambiguous-source',['remember '+TEXT,'query '+QUERY,'support '+target+' '+source,''],
             {'2':dict(text=SOURCE_TEXT,label=SOURCE_LABEL,source='controlled-source-a'),
              '3':dict(text='Second generated source with deliberately ambiguous label.',label=SOURCE_LABEL,source='controlled-source-b')},'CONFLICT')]
        for name,responses,sources,expected in cases:
            run,cfg=self.setup_run(responses,sources);run.operator();p=start(run);p.wait(timeout=100);code,status=run.finish(p)
            self.assertEqual((code,status['code']),(2,expected))
            with sqlite3.connect(run.h.client['database']) as db:self.assertEqual(db.execute('SELECT count(*) FROM app_assessments').fetchone()[0],0)
            traces.append(dict(case=name,status=status,occurrences=run.rows('app_occurrences'),no_assessment=True));run.close()
        self.evidence('ambiguous-or-missing-target',traces)

    def test_current_authority_revoked_after_c1_and_private_scope_stays_local(self):
        run,cfg=self.setup_run(commands()[:4]+['']);p=self.pause(run,'after_assessment_acceptance');run.kill(p)
        policy=json.loads(cfg['evidence_policy'].read_text());policy['principals']['A']['scopes'][SCOPE].remove('belief.revision.submitEvidence')
        cfg['evidence_policy'].write_bytes(canonical(policy));run.app.pop('pause_at');run.save()
        process=start(run);process.wait(timeout=100);code,status=run.finish(process)
        self.assertEqual((code,status['code']),(2,'UNAUTHORIZED'))
        # Test-side scan of all generated non-cognitive provider configuration and
        # network-facing state: the canary never becomes an encoder/search input.
        self.assertNotIn(SOURCE_TEXT,canonical(run.h.config).decode())
        for key in ('embedding_config','memory_embedding_config','memory_read_config','memory_append_config'):
            self.assertNotIn(SOURCE_TEXT,Path(run.app[key]).read_text())
        with sqlite3.connect(run.h.client['database']) as db:
            receipt=json.loads(db.execute('SELECT receipt FROM app_sources ORDER BY slot LIMIT 1').fetchone()[0])
        private_markers=[SOURCE_TEXT.encode(),receipt['evidence']['occurrence_id'].encode(),receipt['evidence']['event_ref']['digest'].encode()]
        scanned=0
        for root in (run.h.server_root,Path(cfg['encoder_database']).parent):
            for path in root.rglob('*'):
                if path.is_file():
                    data=path.read_bytes();scanned+=1
                    for marker in private_markers:self.assertNotIn(marker,data,str(path.relative_to(run.h.root)))
        cfgclient=json.loads(cfg['evidence_client'].read_text());cfgclient['placement']='network';cfg['evidence_client'].write_bytes(canonical(cfgclient))
        with self.assertRaises(ContractError):Application(run.app_path)
        self.evidence('privacy-revocation',dict(status=status,canary_in_memory_or_embedding_configuration=False,
            cognitive_network_placement='UNSUPPORTED_PROFILE',outbound_cognitive_routes=[],private_scope=SCOPE,
            provider_files_scanned=scanned,source_canary_and_source_identity_markers=3,markers_found=0))

    def test_expiry_after_decision_observes_but_does_not_construct_presentation(self):
        run,cfg=self.setup_run(commands()[:4]+['']);run.app['invocation_timeout_ms']=12000
        p=self.pause(run,'after_evidence_decision_commit');run.kill(p)
        with sqlite3.connect(run.h.client['database']) as db:deadline=db.execute('SELECT max(deadline) FROM app_occurrences').fetchone()[0]
        time.sleep(max(0,(deadline-time.time()*1000)/1000)+.05)
        run.app.pop('pause_at');run.save();process=start(run);process.wait(timeout=100);code,status=run.finish(process)
        self.assertEqual((code,status['code']),(2,'DEADLINE_EXCEEDED'))
        value=report(run,cfg);self.assertIsNone(value['app_assessments'][0]['view']);self.assertEqual(value['pending'],())
        self.assertEqual(value['owner_budget_audit'][0]['evaluations'],1);self.assertEqual(value['occurrences'][-1]['deadline'],deadline)
        self.evidence('expired-partial',value)

    def test_identical_support_positions_share_one_contribution(self):
        target=CREATED.replace(' ','_');source=SOURCE_LABEL.replace(' ','_');support='support '+target+' '+source
        run,cfg=self.setup_run(['remember '+TEXT,'query '+QUERY,support+'\n'+support,'query '+QUERY,''])
        run.operator();self.finish(run);value=report(run,cfg)
        rows=value['app_assessments'];self.assertEqual(len(rows),2);self.assertNotEqual(rows[0]['id'],rows[1]['id'])
        self.assertEqual([r['decision']['numerical'] for r in rows],['revised','no-change'])
        self.assertEqual(len(rows[1]['decision']['snapshot']['observations']),1)
        self.assertEqual(value['owner_budget_audit'][0]['evaluations'],1)
        self.evidence('same-turn-positions',value)
