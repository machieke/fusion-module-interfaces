"""Real ngIRCd/peer/DeTTa bridge process kills; no channel fixture."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import unittest
from fusion.channel_transport import Client
from fusion.contracts import canonical,ContractError
from fusion.irc_bridge import Bridge
from .channel_composition import ChannelRun,write,ROOT
from tests.test_channel import egress

OUT=Path(os.environ.get('S06_EVIDENCE',ROOT/'artifacts/s06/tests'));OUT.mkdir(parents=True,exist_ok=True)

class BridgeRecovery(unittest.TestCase):
    def setup_run(self,placement='network',stage=None):
        r=ChannelRun(placement,True);self.addCleanup(r.close);r.start_server();r.start_bridge()
        if stage:
            r.kill(r.bridge);r.bridge_config['pause_at']=stage;r.start_bridge()
        r.start_peer();return r,Client(r.clients['application'])
    def until(self,call,seconds=15):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            value=call()
            if value:return value
            time.sleep(.03)
        self.fail('real-server/owner observation timeout')
    def marker(self,r):r.wait(r.bridge_root/'pause.json',r.bridge,15)
    def resume(self,r):
        r.kill(r.bridge);self.assertEqual(r.bridge.returncode,-signal.SIGKILL)
        r.bridge_config.pop('pause_at',None);r.start_bridge()
    def rows(self,r,table):return r.rows(r.bridge_config['database'],table)
    def test_ingress_kills_capture_payload_and_mailbox_commits(self):
        traces=[]
        for stage in ('after_bridge_capture','after_channel_payload_reply','after_channel_mailbox_reply'):
            with self.subTest(stage=stage):
                r,a=self.setup_run(stage=stage);r.send('synthetic hello');self.marker(r);before=self.rows(r,'channel_ingress');self.resume(r)
                d=self.until(a.poll);v=a.get(d['body']['ref']);self.assertEqual(v,json.loads(before[0]['envelope']));a.ack(d)
                self.until(lambda:self.rows(r,'channel_ingress')[0]['acceptance'])
                self.assertIsNone(a.poll());after=self.rows(r,'channel_ingress');self.assertEqual(len(after),1)
                self.assertGreaterEqual(after[0]['put_calls'],before[0]['put_calls']);self.assertGreaterEqual(after[0]['send_calls'],before[0]['send_calls'])
                traces.append(dict(stage=stage,signal='SIGKILL',before=before,after=after,delivery=d,epochs=self.rows(r,'channel_epochs')));r.close()
        (OUT/'bridge-ingress-kills.json').write_bytes(canonical(traces))
    def test_egress_handoff_and_ambiguous_socket_kills_never_resend(self):
        traces=[]
        for stage in ('after_bridge_egress_commit','after_bridge_egress_ack','after_socket_reservation','after_socket_write','after_socket_outcome'):
            with self.subTest(stage=stage):
                r,a=self.setup_run(stage=stage);v=egress(r);p=a.put(v);receipt=a.send(v,p['ref']);self.marker(r)
                before=self.rows(r,'channel_egress');self.resume(r)
                self.until(lambda:self.rows(r,'channel_egress')[0]['ack'])
                if stage not in ('after_socket_reservation','after_socket_write'):
                    self.until(lambda:self.rows(r,'channel_egress')[0]['outcome']=='socket-write-returned')
                time.sleep(.3)
                traffic=[x for x in r.traffic() if 'received' in x and ' PRIVMSG '+r.base['target']+' :synthetic reply' in x['received']]
                if stage=='after_socket_reservation':self.assertEqual(len(traffic),0)
                else:self.assertEqual(len(traffic),1)
                after=self.rows(r,'channel_egress');self.assertEqual(len(after),1);self.assertEqual(after[0]['reserved'],1)
                self.assertEqual(after[0]['outcome'],'unknown' if stage in ('after_socket_reservation','after_socket_write') else 'socket-write-returned')
                r.kill(r.bridge);r.start_bridge();time.sleep(.2)
                self.assertEqual(traffic,[x for x in r.traffic() if 'received' in x and ' PRIVMSG '+r.base['target']+' :synthetic reply' in x['received']])
                r.kill(r.bridge);owner=Bridge(r.bridge_config_path)
                try:status=owner.observe(v['id'])
                finally:owner.close()
                self.assertEqual(status['recipient'],'not-observed-by-provider')
                traces.append(dict(stage=stage,signal='SIGKILL',acceptance=receipt,before=before,after=after,observation=status,peer=traffic));r.close()
        (OUT/'bridge-egress-kills.json').write_bytes(canonical(traces))
    def test_real_burst_capacity_disconnect_and_reuse(self):
        r,a=self.setup_run();[r.send('synthetic hello') for _ in range(9)]
        self.until(lambda:any(x['reason']=='capacity' for x in self.rows(r,'channel_epochs')))
        before=self.rows(r,'channel_ingress');self.assertLessEqual(len(before),6);self.assertEqual(len(before),6)
        consumed=[]
        for _ in range(len(before)):
            item=self.until(a.poll);consumed.append(a.get(item['body']['ref'])['id']);a.ack(item)
        self.assertEqual(set(consumed),{x['id'] for x in before});self.assertIsNone(a.poll())
        # At least three frames are outside the durable capture guarantee; no
        # manufactured missing-message count is recorded by the bridge.
        r.kill(r.bridge);r.start_bridge();r.send('synthetic hello');item=self.until(a.poll);a.ack(item)
        self.assertNotIn(item['body']['correlation_id'],consumed)
        (OUT/'capacity-discontinuity.json').write_bytes(canonical(dict(captured=before,consumed=consumed,epochs=self.rows(r,'channel_epochs'),after=self.rows(r,'channel_ingress'),attempted_peer_frames=10)))
    def test_spent_rpc_budget_and_expired_effect_remain_spent(self):
        r,a=self.setup_run(stage='after_bridge_capture');r.send('synthetic hello');self.marker(r);r.kill(r.bridge)
        owner=Bridge(r.bridge_config_path)
        try:
            ident=owner.db.execute('SELECT id FROM channel_ingress').fetchone()[0]
            for _ in range(32):owner.reserve_rpc('channel_ingress',ident,'put_calls')
        finally:owner.close()
        owner=Bridge(r.bridge_config_path)
        try:
            with self.assertRaises(ContractError):owner.reserve_rpc('channel_ingress',ident,'put_calls')
            self.assertEqual(owner.db.execute('SELECT put_calls FROM channel_ingress').fetchone()[0],32)
        finally:owner.close()
        # Separate fresh real outbound acceptance expires while bridge is stopped.
        v=egress(r);v['deadline_ms']=time.time_ns()//1_000_000+300;p=a.put(v);a.send(v,p['ref']);time.sleep(.4)
        owner=Bridge(r.bridge_config_path)
        try:
            self.assertTrue(owner.take_egress());self.assertFalse(owner.effect());status=owner.observe(v['id']);self.assertEqual(status['outcome'],'expired-before-reservation');self.assertEqual(status['reserved'],0)
        finally:owner.close()
        (OUT/'spent-budgets.json').write_bytes(canonical(dict(put_calls=32,refused_33=True,expired=status,real_capture_kill=True)))
    def test_revocation_after_reservation_and_server_discontinuity(self):
        r,a=self.setup_run(stage='after_socket_reservation');v=egress(r);p=a.put(v);a.send(v,p['ref']);self.marker(r)
        r.config['principals']['bridge']['scopes'][r.base['scope']]=[];write(r.config_path,r.config)
        pid=json.loads((r.bridge_root/'pause.json').read_text())['pid'];os.kill(pid,signal.SIGCONT);r.bridge.wait(timeout=10)
        self.assertNotEqual(r.bridge.returncode,0);rows=self.rows(r,'channel_egress');self.assertEqual(rows[0]['reserved'],1);self.assertEqual(rows[0]['outcome'],'rejected-before-write')
        self.assertEqual([x for x in r.traffic() if 'received' in x and ' PRIVMSG ' in x['received']],[])
        (OUT/'reservation-revocation.json').write_bytes(canonical(dict(rows=rows,peer=r.traffic())))

    def test_real_provider_kill_after_payload_and_mailbox_acceptance(self):
        traces=[]
        for stage in ('after_atom_persist','after_channel_send'):
            r,a=self.setup_run();r.kill(r.host);r.config['pause_at']=stage;r.start_host();r.send('synthetic hello')
            r.wait(r.provider/'pause.json',r.host,15);before=self.rows(r,'channel_ingress')
            r.kill(r.host);self.assertEqual(r.host.returncode,-signal.SIGKILL)
            r.config.pop('pause_at');r.start_host();item=self.until(a.poll);value=a.get(item['body']['ref']);a.ack(item)
            self.until(lambda:self.rows(r,'channel_ingress')[0]['acceptance']);after=self.rows(r,'channel_ingress')
            self.assertEqual(len(after),1);self.assertEqual(value,json.loads(before[0]['envelope']));self.assertIsNone(a.poll())
            self.assertGreaterEqual(after[0]['put_calls']+after[0]['send_calls'],3)
            traces.append(dict(stage=stage,signal='SIGKILL',before=before,after=after,delivery=item));r.close()
        (OUT/'provider-kills.json').write_bytes(canonical(traces))

    def test_pre_capture_loss_is_not_claimed_as_recoverable_input(self):
        r,a=self.setup_run();r.kill(r.bridge)
        self.until(lambda:any('QUIT' in x.get('received','') and x['received'].startswith(':omega!') for x in r.traffic()))
        r.send('synthetic hello');time.sleep(.2);r.start_bridge();time.sleep(.2)
        self.assertIsNone(a.poll());self.assertEqual(self.rows(r,'channel_ingress'),[])
        r.send('synthetic hello');item=self.until(a.poll);a.ack(item)
        self.assertEqual(len(self.rows(r,'channel_ingress')),1)
        epochs=self.rows(r,'channel_epochs');self.assertTrue(any(x['state']=='discontinuous' for x in epochs))
        (OUT/'pre-capture-loss.json').write_bytes(canonical(dict(peer=r.traffic(),epochs=epochs,
            accepted=self.rows(r,'channel_ingress'),claim='Only the post-reconnect captured occurrence is recoverable; no IRC history replay or missing-count estimate')))

if __name__=='__main__':unittest.main()
