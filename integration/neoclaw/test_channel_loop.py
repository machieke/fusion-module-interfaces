"""Real isolated IRC -> real native Omega loop; only the external model is scripted."""
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
from .channel_composition import configure,ROOT
from .channel_composition import write
from .embedding_run import start
from .promotion_run import report as promotion_report
from .append_oracle import CREATED
from tests.neoclaw_support import COMMAND,GOLDEN

OUT=Path(os.environ.get('S06_EVIDENCE',ROOT/'artifacts/s06/tests'));OUT.mkdir(parents=True,exist_ok=True)
INPUTS=['Synthetic calculate Ω "quoted" (send fake-tool).','Synthetic calculate Ω "quoted" (send fake-tool).',
        'Synthetic priority request.','Synthetic reply request.','Synthetic finish.']
OUTPUT='Synthetic channel reply Ω: calculation observed.'


def report(run,cfg):
    channel=cfg['channel'];value=promotion_report(run,cfg)
    for table in ('app_channel_inputs','app_channel_outputs','app_sources'):
        value[table]=channel.rows(run.h.client['database'],table)
    for table in ('channel_epochs','channel_ingress','channel_egress'):
        value[table]=channel.rows(channel.bridge_config['database'],table)
    value.update(irc=channel.isolation,traffic=channel.traffic(),mailbox_placement=channel.placement,
        mailbox=channel.rows(channel.config['messages_database'],'messages'),
        channel_boundary=json.loads((Path(run.app['workdir'])/'channel-boundary.json').read_text()),
        bridge_boundary=json.loads((channel.bridge_root/'ready.json').read_text()),
        fixtures=['scripted external model','synthetic initial memory and comparison clock','unused history','unused web responses'],
        real=['ngIRCd','independent socket peer','IRC transport','native Omega loop/parser/context','native NAL','DeTTa','Chroma metadata'],same_host=True)
    if channel.placement=='network':value['mailbox_boundary']=json.loads((channel.provider/'ready.json').read_text())
    return value


class NativeChannel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.corpus=json.loads((ROOT/'artifacts/s05/corpus.json').read_text())
    def setup_run(self,placement='local',responses=None,inputs=None):
        responses=responses or [COMMAND,COMMAND,'promote '+self.corpus['records'][-1]['time'],'send '+OUTPUT,'']
        run=ControlledRun('local',responses,search={'boundary':'recorded-response'});self.addCleanup(run.close)
        run.model['expected_feedback']={};run.save();cfg=configure(run,self.corpus,placement,inputs=inputs or INPUTS,outputs=[OUTPUT]);self.addCleanup(cfg['channel'].close)
        run.operator();cfg['channel'].start_bridge();cfg['channel'].start_peer();return run,cfg
    def finish(self,run,p):
        p.wait(timeout=100);self.assertEqual(run.finish(p),(0,{'status':'BOUNDED_STOP'}),(run.h.root/'native.log').read_text()[-18000:])
    def traffic_until(self,ch,count,run=None,p=None):
        until=time.monotonic()+90
        while time.monotonic()<until:
            rows=[x for x in ch.traffic() if 'received' in x and ' PRIVMSG '+ch.base['target']+' :'+OUTPUT in x['received']]
            if len(rows)>=count:return rows
            if p is not None and p.poll() is not None:
                self.fail('native exited before peer observation: '+(run.h.root/'native.log').read_text()[-18000:])
            time.sleep(.05)
        self.fail('real IRC recipient observation timeout')
    def test_local_and_https_native_consumption_equal_text_burst_and_send(self):
        values=[]
        for placement in ('local','network'):
            with self.subTest(placement=placement):
                run,cfg=self.setup_run(placement);ch=cfg['channel'];p=start(run)
                # Four real messages are a burst; only two fit in the mailbox.
                for text in INPUTS[:4]:ch.send(text)
                self.traffic_until(ch,1,run,p);ch.send(INPUTS[4]);self.finish(run,p);value=report(run,cfg)
                self.assertEqual(len(value['app_channel_inputs']),5);self.assertEqual(len({r['id'] for r in value['app_channel_inputs']}),5)
                self.assertEqual(len(value['app_sources']),5);self.assertEqual(len(value['channel_ingress']),5)
                self.assertEqual(len(value['app_assessments']),0)
                oracle=json.loads((ROOT/'evidence/s06/native-oracle-unicode.json').read_text())
                self.assertEqual(oracle['values'][0],'peer: '+json.loads(value['app_channel_inputs'][0]['envelope'])['text'])
                self.assertTrue(oracle['peer'][0]['received'].endswith(' :'+OUTPUT))
                for i,text in enumerate(INPUTS):self.assertIn('peer: '+text.replace('"','_quote_'),value['observations'][i]['context'])
                self.assertIn(GOLDEN,value['observations'][1]['feedback']);self.assertIn('SEND-ACCEPTED',value['observations'][4]['feedback'])
                self.assertIn(self.corpus['records'][-1]['content'],value['observations'][3]['context'])
                self.assertEqual(value['channel_egress'][0]['outcome'],'socket-write-returned');self.assertEqual(value['channel_egress'][0]['reserved'],1)
                self.assertEqual(sum(r['acknowledged'] for r in value['mailbox']),6)
                self.assertEqual(value['channel_boundary']['denied_paths_visible'],[]);self.assertTrue(value['channel_boundary']['direct_irc_connect_refused'])
                self.assertEqual(value['bridge_boundary']['denied_paths_visible'],[])
                if placement=='network':self.assertEqual(value['mailbox_boundary']['denied_paths_visible'],[])
                values.append(value);ch.close();run.close()
        (OUT/'native-paths.json').write_bytes(canonical(values))

    def test_native_process_kills_input_result_and_outbound_acceptance(self):
        traces=[]
        stages=('after_application_input_commit','after_application_input_ack_reply','after_application_input_ack',
                'after_source_acceptance','after_caller_completion','after_output_mailbox_reply','after_channel_native_result')
        for stage in stages:
            with self.subTest(stage=stage):
                run,cfg=self.setup_run('network',responses=[COMMAND,'send '+OUTPUT,''],inputs=INPUTS[:3]);ch=cfg['channel']
                run.app['pause_at']=stage;run.save();p=start(run)
                for text in INPUTS[:3]:ch.send(text)
                run.h.wait_file(run.app['failpoint_marker'],p,seconds=75)
                before=ch.rows(run.h.client['database'],'app_channel_inputs');commands=run.rows('app_occurrences')
                sources=ch.rows(run.h.client['database'],'app_sources');observed=len(run.observations())
                run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL);run.app.pop('pause_at');run.save()
                restarted=start(run);self.finish(run,restarted);self.traffic_until(ch,1)
                value=report(run,cfg)
                for old,new in zip(before,value['app_channel_inputs']):
                    for key in ('slot','id','envelope','delivery','wait_deadline','deadline','polls'):self.assertEqual(old[key],new[key])
                    self.assertGreaterEqual(new['ack_calls'],old['ack_calls'])
                for old,new in zip(commands,value['occurrences']):self.assertEqual((old['id'],old['deadline']),(new['id'],new['deadline']))
                self.assertEqual(len(value['app_sources']),3);self.assertEqual(len(value['app_channel_inputs']),3)
                self.assertEqual(len(value['app_channel_outputs']),1);self.assertEqual(len(value['channel_egress']),1)
                self.assertEqual(len(value['observations']),3);self.assertIn('SEND-ACCEPTED',value['observations'][2]['feedback'])
                self.assertEqual(len({json.loads(r['accepted'])['spec']['message_id'] for r in value['app_sources']}),3)
                traces.append(dict(stage=stage,signal='SIGKILL',before=before,commands_before=commands,sources_before=sources,model_calls_before=observed,trace=value))
                ch.close();run.close()
        (OUT/'native-kills.json').write_bytes(canonical(traces))

    def test_native_private_output_and_identifying_hash_refused_before_remote_storage(self):
        traces=[];private=self.corpus['records'][-1]['content']
        for forbidden in (private,digest(private.encode())):
            run,cfg=self.setup_run('network',responses=['send '+forbidden],inputs=INPUTS[:1]);ch=cfg['channel'];p=start(run);ch.send(INPUTS[0]);p.wait(timeout=75)
            self.assertEqual(run.finish(p),(2,{'status':'PENDING_OR_FAILED','code':'UNAUTHORIZED'}))
            self.assertEqual(ch.rows(run.h.client['database'],'app_channel_outputs'),[])
            self.assertEqual(ch.rows(ch.bridge_config['database'],'channel_egress'),[])
            markers=[private.encode(),digest(private.encode()).encode(),b'private-s04',b'private-s05',b'S05_LOCAL_PRIORITY']
            scanned=0
            for root in (ch.provider,ch.bridge_root,ch.peer_root):
                for path in root.rglob('*'):
                    if path.is_file():
                        data=path.read_bytes();scanned+=1
                        for marker in markers:self.assertNotIn(marker,data,str(path))
            self.assertEqual([x for x in ch.traffic() if ' PRIVMSG ' in x.get('received','')],[])
            traces.append(dict(kind='content' if forbidden==private else 'identifying-hash',scanned_files=scanned,
                result='UNAUTHORIZED before output identity/storage/RPC',status=json.loads(Path(run.app['status_file']).read_text())))
            ch.close();run.close()
        (OUT/'private-refusal.json').write_bytes(canonical(traces))

    def test_native_empty_poll_budget_persists_across_kill(self):
        run,cfg=self.setup_run('network',responses=[COMMAND],inputs=INPUTS[:1]);ch=cfg['channel']
        run.app.update(channel_poll_limit=1,pause_at='after_channel_poll_reservation');run.save();p=start(run)
        run.h.wait_file(run.app['failpoint_marker'],p,seconds=75);before=ch.rows(run.h.client['database'],'app_channel_inputs')
        run.kill(p);run.app.pop('pause_at');run.save();p=start(run);p.wait(timeout=75);code,status=run.finish(p)
        self.assertEqual(code,2);self.assertIn(status['code'],('OVERLOADED','DEADLINE_EXCEEDED'))
        after=ch.rows(run.h.client['database'],'app_channel_inputs');self.assertEqual(before,after)
        self.assertEqual(run.observations(),[]);self.assertEqual(after[0]['polls'],1);self.assertIsNone(after[0]['id'])
        (OUT/'native-empty-budget.json').write_bytes(canonical(dict(before=before,after=after,status=status,signal='SIGKILL')))

    def test_revocation_after_acceptance_blocks_native_capture_then_recovers(self):
        run,cfg=self.setup_run('network',responses=['send '+OUTPUT,''],inputs=INPUTS[:2]);ch=cfg['channel']
        run.app['pause_at']='after_output_acceptance';run.save();p=start(run)
        for text in INPUTS[:2]:ch.send(text)
        run.h.wait_file(run.app['failpoint_marker'],p,seconds=75)
        before=ch.rows(run.h.client['database'],'app_channel_outputs');commands=run.rows('app_occurrences')
        methods=ch.config['principals']['A']['scopes'][ch.base['scope']]
        ch.config['principals']['A']['scopes'][ch.base['scope']]=[m for m in methods if m!='atom.storage.get'];write(ch.config_path,ch.config)
        stopped=json.loads(Path(run.app['failpoint_marker']).read_text())['pid'];os.kill(stopped,signal.SIGCONT)
        p.wait(timeout=20);self.assertEqual(run.finish(p),(2,{'status':'PENDING_OR_FAILED','code':'UNAUTHORIZED'}))
        self.assertIsNone(run.rows('app_occurrences')[0]['result'])
        ch.config['principals']['A']['scopes'][ch.base['scope']]=methods;write(ch.config_path,ch.config)
        run.app.pop('pause_at');run.save();p=start(run);self.finish(run,p);self.traffic_until(ch,1)
        after=ch.rows(run.h.client['database'],'app_channel_outputs');self.assertEqual(before,after)
        self.assertEqual(commands[0]['deadline'],run.rows('app_occurrences')[0]['deadline'])
        self.assertEqual(len(run.observations()),2);self.assertIn('SEND-ACCEPTED',run.observations()[1]['feedback'])
        (OUT/'capture-revocation.json').write_bytes(canonical(dict(before=before,after=after,
            original_deadline=commands[0]['deadline'],blocked_capture='UNAUTHORIZED',recovered_without_new_send=True,
            peer=[x for x in ch.traffic() if ' PRIVMSG ' in x.get('received','')],
            note='Revoking caller release does not retroactively cancel an already accepted bridge intent.')))

    def test_identical_intentional_sends_in_two_positions_survive_result_kill(self):
        run,cfg=self.setup_run('network',responses=['send '+OUTPUT+'\nsend '+OUTPUT,''],inputs=INPUTS[:2]);ch=cfg['channel']
        run.app['pause_at']='after_channel_native_result';run.save();p=start(run)
        for text in INPUTS[:2]:ch.send(text)
        run.h.wait_file(run.app['failpoint_marker'],p,seconds=75);before=run.rows('app_occurrences')
        self.assertEqual(len(before),2);self.assertEqual(before[0]['result'],'SEND-ACCEPTED');self.assertIsNone(before[1]['result'])
        run.kill(p);self.assertEqual(p.returncode,-signal.SIGKILL);run.app.pop('pause_at');run.save();self.finish(run,start(run))
        traffic=self.traffic_until(ch,2);time.sleep(.1);outputs=ch.rows(run.h.client['database'],'app_channel_outputs')
        after=run.rows('app_occurrences');self.assertEqual([(x['id'],x['deadline']) for x in before],[(x['id'],x['deadline']) for x in after])
        self.assertEqual(len({x['id'] for x in outputs}),2);self.assertTrue(all(x['put_calls']==x['send_calls']==1 for x in outputs))
        states=ch.rows(ch.bridge_config['database'],'channel_egress');self.assertEqual(len(states),2);self.assertTrue(all(x['reserved']==1 for x in states))
        self.assertEqual(len(run.observations()),2);self.assertEqual(run.observations()[1]['feedback'].count('SEND-ACCEPTED'),2)
        self.assertEqual(len([x for x in ch.traffic() if ' PRIVMSG ' in x.get('received','')]),2)
        (OUT/'intentional-sends.json').write_bytes(canonical(dict(signal='SIGKILL',bound=[dict(id=x['id'],deadline=x['deadline'],position=x['position']) for x in before],
            outputs=outputs,bridge=states,peer=traffic,model_calls=2,next_context_acceptances=2)))

if __name__=='__main__':unittest.main()
