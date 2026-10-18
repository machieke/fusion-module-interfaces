"""Actual native consumers with real E5/Chroma/DeTTa and separate S04 owners."""
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
from .controlled_run import ControlledRun
from .promotion_composition import configure
from .promotion_oracle import commands
from .promotion_run import execute,report
from .embedding_run import start
from .append_oracle import TEXT,QUERY,CREATED
from .evidence_composition import TEXT as SOURCE_TEXT
from .evidence_oracle import SOURCE_LABEL
from .memory_composition import ROOT

OUT=Path(os.environ.get('S05_EVIDENCE',ROOT/'artifacts/s05/tests'))

def segment(context):return context.split('MOST_PROMOTED_MEMORIES: ',1)[1].split(' TIME: ',1)[0]

class NativePromotionLoop(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.corpus=json.loads((ROOT/'artifacts/s05/corpus.json').read_text());OUT.mkdir(parents=True,exist_ok=True)
    def evidence(self,name,value):(OUT/(name+'.json')).write_bytes(canonical(value))
    def setup_run(self,responses=None,provider='sqlite',sources=None,corpus=None):
        run=ControlledRun('local',responses or commands(self.corpus),search={'boundary':'recorded-response'});self.addCleanup(run.close)
        run.model['expected_feedback']={};run.save();cfg=configure(run,corpus or self.corpus,provider,sources=sources);return run,cfg
    def finish(self,run):
        p=start(run);p.wait(timeout=180);result=run.finish(p)
        self.assertEqual(result,(0,{'status':'BOUNDED_STOP'}),(run.h.root/'native.log').read_text()[-12000:])
    def pause(self,run,stage,minimum_slot=0):
        run.app['pause_at']=stage;run.save();run.operator();p=start(run)
        while True:
            run.h.wait_file(run.app['failpoint_marker'],p,seconds=60)
            with sqlite3.connect(run.h.client['database']) as db:
                count=db.execute('SELECT count(*) FROM app_priority_contexts').fetchone()[0]
            if count>=minimum_slot:return p
            stopped=json.loads(Path(run.app['failpoint_marker']).read_text())['pid']
            Path(run.app['failpoint_marker']).unlink();os.kill(stopped,signal.SIGCONT)
    def resume(self,run):run.app.pop('pause_at',None);run.save();self.finish(run)
    def test_original_primary_independent_native_query_and_global_context(self):
        oracle=json.loads((ROOT/'evidence/s05/native-oracle.json').read_text());traces=[]
        outside=self.corpus['records'][-1]
        for provider in ('sqlite','file-fixture'):
            value=execute(self.corpus,provider)
            self.assertEqual([x['feedback'] for x in value['observations']],[x['feedback'] for x in oracle['observations']])
            self.assertEqual([segment(x['context']) for x in value['observations']],[segment(x['context']) for x in oracle['observations']])
            self.assertEqual(value['output'],oracle['output']);self.assertEqual(len(value['app_priority']),4)
            self.assertEqual([x['receipt']['value'] for x in value['app_priority']],[1.,1.,2.,0.])
            self.assertNotEqual(value['observations'][2]['feedback'],value['observations'][4]['feedback'])
            self.assertIn(outside['content'],str(value['observations'][6]['context']))
            for read in value['read_receipts']:
                self.assertNotIn(outside['uuid'],[x['uuid'] for x in read['candidates']['hits']])
            self.assertEqual(len(value['maintenance_audit']),1);self.assertEqual(len(value['app_memory_vectors']),1)
            traces.append(dict(provider=provider,trace=value))
        self.evidence('three-paths',traces)
    def test_priority_and_belief_independent_same_session(self):
        alias=CREATED;assessment=CREATED.replace(' ','_')+' '+SOURCE_LABEL.replace(' ','_')
        responses=['remember '+TEXT,'promote '+alias,'support '+assessment,'query '+QUERY,
                   'promote '+alias,'contradict '+assessment,'demote '+alias,'query '+QUERY,'']
        sources={'2':dict(text=SOURCE_TEXT,label=SOURCE_LABEL,source='controlled-source-a')}
        value=execute(self.corpus,responses=responses,sources=sources)
        self.assertEqual([r['receipt']['value'] for r in value['app_priority']],[1.,2.,1.])
        self.assertEqual([r['decision']['numerical'] for r in value['app_assessments']],['revised','retained-alternative'])
        self.assertEqual(value['app_assessments'][0]['decision']['snapshot']['truth'],value['app_assessments'][1]['decision']['snapshot']['truth'])
        self.assertIn('0.6666666666666666',str(value['observations'][-1]['context']))
        self.assertEqual(len(value['maintenance_audit']),1);self.assertEqual(len(value['app_memory_vectors']),1)
        self.evidence('belief-independence',value)
    def test_real_kills_independent_commits_and_context_handoff(self):
        stages=['after_priority_acceptance','after_priority_clock','after_priority_evaluation','after_priority_commit',
            'after_priority_visibility','after_priority_result','after_global_selection','after_global_capture'];traces=[]
        for provider in ('sqlite','file-fixture'):
            for stage in stages:
                with self.subTest(provider=provider,stage=stage):
                    run,cfg=self.setup_run(provider=provider);p=self.pause(run,stage,4 if stage.startswith('after_global') else 0)
                    with sqlite3.connect(run.h.client['database']) as db:
                        before=[list(x) for x in db.execute('SELECT id,deadline FROM app_occurrences ORDER BY turn,position')]
                        context=[list(x) for x in db.execute('SELECT slot,view,deadline,binding,result FROM app_priority_contexts ORDER BY slot')]
                    run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL);self.resume(run);value=report(run,cfg)
                    self.assertEqual(before,[[x['id'],x['deadline']] for x in value['occurrences'][:len(before)]])
                    self.assertEqual([x['receipt']['revision'] for x in value['app_priority']],[1,2,3,4])
                    self.assertTrue(all(x['receipt']['time']==self.corpus['clock'] for x in value['app_priority']))
                    for frozen,new in zip(context,value['app_priority_contexts']):
                        self.assertEqual(frozen[:3],[new['slot'],new['view'],new['deadline']])
                        if frozen[3]:self.assertEqual(json.loads(frozen[3]),new['binding'])
                        if frozen[4]:self.assertEqual(json.loads(frozen[4]),new['result'])
                    work=[w for w in value['attention_owner_audit'] if w['binding']['request']['kind']=='adjust']
                    spent=sorted(w['spent'] for w in work)
                    self.assertEqual(spent,[1,1,1,2] if stage=='after_priority_evaluation' else [1,1,1,1])
                    traces.append(dict(provider=provider,stage=stage,signal='SIGKILL',trace=value));run.close()
        self.evidence('native-kills',traces)
    def test_retained_query_context_and_derived_file_repair(self):
        run,cfg=self.setup_run();run.operator();self.finish(run);before=report(run,cfg);app=Application(run.app_path)
        try:
            query=app.db.execute('SELECT o.* FROM app_occurrences o JOIN app_priority_queries p ON p.id=o.id ORDER BY turn LIMIT 1').fetchone()
            self.assertEqual(app._run(query),query['result']);context=app.db.execute('SELECT * FROM app_priority_contexts WHERE slot=4').fetchone()
            # Explicit old accepted context recovery, not a new scheduler iteration.
            app.priority.slot=lambda:4
            old=app.priority.context_replay();output=Path(json.loads(cfg['attention_client'].read_text())['output']);expected=output.read_bytes();output.unlink()
            self.assertEqual(app.priority.context_replay(),old);self.assertEqual(output.read_bytes(),expected)
            self.assertEqual(context['rendered'],old)
        finally:app.close()
        after=report(run,cfg);self.assertEqual(before['attention_owner_audit'],after['attention_owner_audit']);self.assertEqual(before['app_priority'],after['app_priority']);self.assertEqual(before['app_assessments'],after['app_assessments'])
        self.assertEqual(before['publication_audit'],after['publication_audit']);self.evidence('retained-views',dict(before=before,after=after))
    def test_ordered_batch_new_occurrences_and_alias_refusals(self):
        target=self.corpus['records'][5]['time']
        value=execute(self.corpus,responses=['promote '+target+'\npromote '+target,'query '+QUERY,'demote '+target,''])
        self.assertEqual([x['receipt']['value'] for x in value['app_priority']],[1.,2.,1.]);self.assertEqual(len({x['id'] for x in value['app_priority']}),3)
        failures=[]
        corpus=copy.deepcopy(self.corpus);corpus['records'][6]['time']=target
        for label,selected,responses in [('ambiguous',corpus,['promote '+target]),('missing',self.corpus,['promote 2031-01-01 00:00:00']),
            ('underscore',self.corpus,['promote '+target.replace(' ','_')]),('mixed-batch',self.corpus,['promote '+target+'\nquery '+QUERY])]:
            run,cfg=self.setup_run(responses=responses,corpus=selected);run.operator();p=start(run);p.wait(timeout=90);result=run.finish(p)
            self.assertEqual(result[0],2)
            with sqlite3.connect(run.h.client['database']) as db:self.assertEqual(db.execute('SELECT count(*) FROM app_priority').fetchone()[0],0)
            failures.append(dict(case=label,result=result));run.close()
        self.evidence('occurrences-aliases',dict(sequence=value,refusals=failures))
    def test_current_authority_cached_release_no_fallback_and_missing_content(self):
        run,cfg=self.setup_run();run.operator();self.finish(run);app=Application(run.app_path)
        try:
            app.priority.slot=lambda:6
            saved=app.priority.context_replay();policy=json.loads(cfg['attention_policy'].read_text())
            denied=copy.deepcopy(policy);denied['principals']['A']['scopes']['private-s05']=[];cfg['attention_policy'].write_bytes(canonical(denied))
            with self.assertRaises(ContractError):app.priority.context_replay()
            cfg['attention_policy'].write_bytes(canonical(policy))
            class Missing:
                def head(self,*args):return app.priority.atoms.head(*args)
                def get(self,*args):raise ContractError('NOT_AVAILABLE')
            atoms=app.priority.atoms
            class Unavailable:
                def head(self,*args):return atoms.head(*args)
                def get(self,*args):raise ContractError('NOT_AVAILABLE')
            app.priority.atoms=Unavailable()
            with self.assertRaises(ContractError):app.priority.context_replay()
            app.priority.atoms=atoms
            owner=app.priority.owner
            class Bad:
                def authorize(self,*args):return owner.authorize(*args)
                def observe(self,b):
                    value=copy.deepcopy(owner.observe(b));value['scores'][0]['score']=float('nan');return value
            app.priority.owner=Bad()
            with self.assertRaises(ContractError):app.priority.context_replay()
            app.priority.owner=owner;self.assertEqual(app.priority.context_replay(),saved)
        finally:app.close()
        # Private identity and priority selection do not enter shareable providers.
        private=json.loads(cfg['attention_client'].read_text())
        forbidden=[private['context'].encode(),b'wall-clock-promotion/1',b'private-s05']
        for file in Path(run.h.server_root).rglob('*'):
            if file.is_file():
                data=file.read_bytes()
                for marker in forbidden:self.assertNotIn(marker,data,str(file))
        self.evidence('privacy-authority',dict(private_markers_scanned=3,missing_payload='NOT_AVAILABLE',malformed_score='refused',fallback=False))

if __name__=='__main__':unittest.main()
