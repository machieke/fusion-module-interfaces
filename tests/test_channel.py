"""Closed S06 contract/owner tests. File atoms are explicit fixtures here."""
import copy
import json
from pathlib import Path
import sqlite3
import time
import unittest
import uuid
from fusion import channel_contracts as c
from fusion.adapters.irc_socket import Frames,message
from fusion.channel_transport import Client,configuration,checked
from fusion.channel_service import ChannelService
from fusion.contracts import ContractError,canonical,encode,PROFILES
from fusion.irc_bridge import Bridge
from integration.neoclaw.channel_composition import ChannelRun,write


def ingress(run,sequence=1,text='synthetic hello'):
    cfg=run.base;epoch=str(uuid.uuid4());now=time.time_ns()//1_000_000
    return dict(profile=c.PROFILE,kind='ingress',scope=cfg['scope'],route=cfg['ingress_route'],bridge=cfg['bridge'],session=cfg['session'],
        id=str(uuid.uuid5(uuid.UUID(epoch),str(sequence))),epoch=epoch,sequence=sequence,observed_ms=now,nick='peer',target=cfg['target'],text=text,deadline_ms=now+30000)


def egress(run):
    v=ingress(run);v.update(kind='egress',route=run.base['egress_route'],id=str(uuid.uuid4()),epoch=None,nick=None,text='synthetic reply');return v


class ChannelContract(unittest.TestCase):
    def setup_run(self,placement='local'):
        r=ChannelRun(placement,False);self.addCleanup(r.close);return r,Client(r.clients['application']),Client(r.clients['bridge'])
    def assertCode(self,code,call):
        with self.assertRaises(ContractError) as got:call()
        self.assertEqual(got.exception.code,code)
    def test_split_utf8_coalesced_frames_and_crlf(self):
        data=':peer!u@h PRIVMSG #s06-generated :Ω\r\n:peer!u@h PRIVMSG #s06-generated :again\r\n'.encode()
        for cut in range(len(data)+1):
            f=Frames();lines=f.feed(data[:cut])+f.feed(data[cut:]);self.assertEqual(len(lines),2)
            self.assertEqual(message(lines[0],'#s06-generated','omega'),('peer','Ω'))
        f=Frames();self.assertEqual(f.feed(b'PING :x\r'),[]);self.assertEqual(f.feed(b'\n'),['PING :x'])
    def test_frame_and_text_refusals(self):
        for data in (b'x'*511,b'bad\n',b'bad\rxx',b'bad\0',b'\xff\r\n',b'x'*511+b'\r\n'):
            with self.subTest(data=data[:8]),self.assertRaises(ContractError):Frames().feed(data)
        for value in ('','a\n','a\r','a\x00','x'*401,'Ω'*201,'\ud800'):
            with self.subTest(value=repr(value)),self.assertRaises(ContractError):c.text(value)
    def test_filter_notices_echo_and_target_changed_nick(self):
        self.assertIsNone(message(':s NOTICE omega :hi','#s06-generated','omega'))
        self.assertIsNone(message(':OMEGA!u@h PRIVMSG #s06-generated :hi','#s06-generated','omega'))
        self.assertIsNone(message(':peer!u@h PRIVMSG #other :hi','#s06-generated','omega'))
        self.assertEqual(message(':changed!u@h PRIVMSG #s06-generated :admin','#s06-generated','omega'),('changed','admin'))
    def test_output_domain_private_refusal(self):
        for body in (' a','a ','a\\nb','x'*401,'Ω'*201,'a\t','PRIVMSG #other :private'):
            with self.subTest(body=body[:16]),self.assertRaises(ContractError):c.output(body,['safe'],'#s06-generated')
        self.assertEqual(c.output('Ω quoted "text"',['Ω quoted "text"'],'#s06-generated'),'Ω quoted "text"')
    def test_replay_equal_text_distinct_occurrences_and_ack(self):
        r,a,b=self.setup_run();v=ingress(r);p=b.put(v);receipt=b.send(v,p['ref'])
        self.assertEqual(p,b.put(v));self.assertEqual(receipt,b.send(v,p['ref']))
        d=a.poll();self.assertEqual(a.get(d['body']['ref']),v);self.assertEqual(a.ack(d),a.ack(d));self.assertIsNone(a.poll())
        self.assertCode('CONFLICT',lambda:a.invoke('agent.messaging','ack',dict(route=d['route'],delivery_id=d['delivery_id']),'invented-ack-key'))
        new=ingress(r);self.assertNotEqual(new['id'],v['id']);q=b.put(new);self.assertNotEqual(receipt,b.send(new,q['ref']))
    def test_capacity_drain_and_reuse(self):
        r,a,b=self.setup_run();items=[ingress(r) for _ in range(6)];receipts=[]
        for i,v in enumerate(items):
            p=b.put(v)
            if i>=2:
                self.assertCode('OVERLOADED',lambda:b.send(v,p['ref']));a.ack(a.poll())
            receipts.append(b.send(v,p['ref']))
        while (d:=a.poll()) is not None:a.ack(d)
        self.assertEqual(len({x['delivery_id'] for x in receipts}),6)
    def test_current_authority_role_and_credential_rotation(self):
        r,a,b=self.setup_run();v=ingress(r);p=b.put(v);b.send(v,p['ref']);d=a.poll()
        config=copy.deepcopy(r.config);r.config['principals']['A']['scopes'][r.base['scope']].remove('agent.messaging.send');write(r.config_path,r.config)
        self.assertCode('UNAUTHORIZED',lambda:a.get(p['ref']));self.assertCode('UNAUTHORIZED',lambda:a.ack(d))
        write(r.config_path,config)
        client=json.loads(r.clients['application'].read_text());client['credential']=config['principals']['bridge']['credential'];write(r.clients['application'],client)
        self.assertCode('UNAUTHORIZED',a.poll)
        config['principals']['A']['credential']='rotated-generated';write(r.config_path,config);client['credential']='rotated-generated';write(r.clients['application'],client)
        self.assertEqual(a.poll(),d)
    def test_wrong_role_route_scope_and_identity(self):
        r,a,b=self.setup_run();v=ingress(r)
        self.assertCode('UNAUTHORIZED',lambda:a.put(v))
        for key,value in [('scope','elsewhere'),('route','elsewhere'),('session',str(uuid.uuid4())),('id',str(uuid.uuid4()))]:
            malformed=dict(v,**{key:value})
            with self.subTest(key=key),self.assertRaises(ContractError):b.put(malformed)
        p=b.put(v)
        self.assertCode('UNAUTHORIZED',lambda:a.invoke('agent.messaging','ack',dict(route=r.base['egress_route'],delivery_id=str(uuid.uuid4())),'bad'))
        self.assertCode('CONFLICT',lambda:b.invoke('agent.messaging','send',dict(ref=p['ref'],route=v['route']),'mail/'+v['id'],v['deadline_ms'],str(uuid.uuid4())))
    def test_conflicting_replay_and_deadline(self):
        r,a,b=self.setup_run();v=ingress(r);p=b.put(v);changed=dict(v,observed_ms=v['observed_ms']-1)
        self.assertCode('CONFLICT',lambda:b.put(changed))
        expired=ingress(r);expired.update(observed_ms=1,deadline_ms=2)
        self.assertCode('DEADLINE_EXCEEDED',lambda:b.put(expired))
    def test_selection_changed_endpoint_and_unsealed_state(self):
        r,a,b=self.setup_run();cfg=json.loads(r.clients['application'].read_text());cfg['catalogue'][0]['provider']='wrong';write(r.clients['application'],cfg)
        with self.assertRaises(ContractError):a.poll()
        r2,_,_=self.setup_run()
        with sqlite3.connect(r2.config['database']) as db:db.execute('CREATE TABLE old(x)')
        self.assertCode('UNSUPPORTED_PROFILE',lambda:ChannelService(r2.config_path))
    def test_malformed_replies_bound_to_exact_request(self):
        r,a,b=self.setup_run();v=ingress(r)
        q=dict(message_id='payload/'+v['id'],idempotency_key='payload/'+v['id'],interface_ref=dict(id='atom.storage',version='1.0.0'),operation='create',scope_ref=v['scope'],profile=PROFILES['atom.storage'],deadline_ms=v['deadline_ms'],body=dict(content_type=c.CONTENT,bytes=encode(canonical(v)),sharing='non-sensitive-fixture'))
        wire=dict(channel_profile=c.PROFILE,selections=c.selection(b.chosen),principal='bridge',invocation=q)
        service=ChannelService(r.config_path)
        try:reply=service.invoke(b.cfg['credential'],wire)
        finally:service.close()
        for key in ('request_id','request_digest','principal','selection'):
            bad=copy.deepcopy(reply);bad[key]='wrong'
            with self.subTest(key=key),self.assertRaises(ContractError):checked(wire,bad,b.chosen)
        bad=copy.deepcopy(reply);bad['reply']['ok']['ref']['digest']='0'*64
        with self.assertRaises(ContractError):checked(wire,bad,b.chosen)
    def test_https_bad_certificate_no_fallback_and_binding(self):
        r,a,b=self.setup_run('network');v=ingress(r);p=b.put(v);b.send(v,p['ref']);self.assertIsNotNone(a.poll())
        r.kill(r.host);self.assertCode('NOT_AVAILABLE',a.poll);r.start_host();self.assertIsNotNone(a.poll())
        cfg=json.loads(r.clients['application'].read_text());cfg['endpoint']['port']+=1;write(r.clients['application'],cfg)
        self.assertCode('CONFLICT',a.poll)
        other,_,_=self.setup_run('network');cfg['endpoint']['port']-=1;cfg['endpoint']['ca_file']=str(other.provider/'server.pem');write(r.clients['application'],cfg)
        wrong=Client(r.clients['application']);self.assertCode('NOT_AVAILABLE',wrong.poll)

if __name__=='__main__':unittest.main()
