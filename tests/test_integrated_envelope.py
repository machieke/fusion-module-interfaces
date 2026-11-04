"""Real execution/mailbox SQLite and process kills; payload/wire fixtures.

Native, DeTTa, HTTPS and chain are NOT exercised by this unit lane.
"""
import copy,json,multiprocessing,os,time,unittest,uuid
from unittest.mock import patch
from fusion import execution_envelope as e,preview_inspect as p
from fusion.client import Peer
from fusion.contracts import canonical,ContractError,require
from fusion.registry import selection_token
from tests import test_phase2_inspect_ports as baseline


class Envelopes(baseline.InspectPorts):
    def setUp(self):
        super().setUp()
        for path in [*self.paths.values(),self.client_path]:
            value=json.loads(path.read_bytes());value['envelopes']=e.PROFILE;path.write_bytes(canonical(value))
        self.client=p.Client(self.client_path);self.peer=Peer(self.client,baseline.SCOPE,'inspect-A')
        self.deadline=time.time_ns()//1000000+60000

    def wire(self,key='envelope-test'):
        request=self.peer.request('execution','submit',dict(operation='inspect_atom',ref=self.input['ref']),key,key,deadline_ms=self.deadline)
        envelope=e.build(request,'A',self.client.selected['execution'])
        return dict(profile=p.PROFILE,selection=selection_token(self.client.selected['execution']),request=request,envelope=envelope)

    def send(self,q,hook=lambda _:None):
        return self.owner(hook=hook).invoke(p.ROUTE,self.token('inspect-caller-A-token'),q)['ok']

    def test_full_typed_result_and_current_authority_scoped_commit_cursor(self):
        q=self.wire();job=self.send(q)['job_id']
        first=self.client.events(job);self.assertEqual([x['kind'] for x in first['events']],['accepted'])
        self.run_owner('work');second=self.client.events(job,first['source'],first['next'])
        self.assertEqual([x['kind'] for x in second['events']],['result-committed'])
        result=self.peer.result(job);self.assertEqual(json.loads(self.atoms.get(result['ref']).bytes)['digest'],self.input['ref']['digest'])
        self.run_owner('flush');third=self.client.events(job,second['source'],second['next'])
        self.assertEqual([x['kind'] for x in third['events']],['completion-delivered'])
        self.assertEqual(self.client.events(job,second['source'],second['next']),third)
        delivery=self.peer.poll();self.assertEqual(delivery['body']['result'],result)
        self.peer.ack(delivery['delivery_id'],'ack-test')
        self.assertTrue(self.client.events(job,'foreign-source',0)['gap'])
        self.assertTrue(self.client.events(job,third['source'],4)['gap'])
        self.revoke('fusion-execution','A','execution.status')
        self.denied('UNAUTHORIZED',self.client.events,job)

    def test_envelope_rejections_before_effect_and_current_principal_binding(self):
        original=self.wire()
        for key,value in [('inputs',dict(ref=dict(self.input['ref'],digest='0'*64))),('task','changed'),
            ('limits',dict(e.LIMITS,recursive=True)),('delegation',dict(service='shell',actor='worker',authority='current-scoped-policy')),
            ('deadline_ms',self.deadline+1),('completion',dict(owner='B',route='inspect-B',profile='durable-mailbox/2')),
            ('operation',dict(interface={'id':'execution','version':'1.0.0'},profile='wrong',name='evaluate')),
            ('guarantee','exactly-once-physical-execution')]:
            q=copy.deepcopy(original);q['envelope'][key]=value
            with self.subTest(key=key):self.denied('CONFLICT',self.send,q)
        q=copy.deepcopy(original);q['envelope']['provider']['selection']='0'*64
        self.denied('UNSUPPORTED_PROFILE',self.send,q)
        q=copy.deepcopy(original);q.pop('envelope');self.denied('INVALID_ARGUMENT',self.send,q)
        self.assertEqual(self.rows('fusion-execution','jobs'),[])

    def test_same_task_new_delivery_deduplicates_changed_semantics_conflict(self):
        q=self.wire();accepted=self.send(q)
        replay=copy.deepcopy(q);replay['request']['message_id']=str(uuid.uuid4())
        self.assertEqual(self.send(replay),accepted)
        changed=copy.deepcopy(replay);changed['request']['deadline_ms']+=1
        changed['envelope']=e.build(changed['request'],'A',self.client.selected['execution'])
        self.denied('CONFLICT',self.send,changed)
        self.assertEqual(len(self.rows('fusion-execution','jobs')),1)
        self.assertNotEqual(self.send(self.wire('new-intention'))['job_id'],accepted['job_id'])

    def test_process_kill_intent_acceptance_result_and_outbox_recovery(self):
        q=self.wire()
        def killed(stage,operation):
            def hook(value):
                if value==stage:os._exit(72)
            child=multiprocessing.get_context('fork').Process(target=lambda:operation(hook))
            child.start();child.join(10)
            if child.is_alive():child.kill();child.join();self.fail('kill boundary not reached')
            self.assertEqual(child.exitcode,72)
        killed('after_execution_envelope_bind',lambda hook:self.send(q,hook))
        self.assertEqual(len(self.rows('fusion-execution','integrated_execution_envelopes')),1)
        self.assertEqual(self.rows('fusion-execution','jobs'),[])
        killed('after_acceptance',lambda hook:self.send(q,hook))
        job=self.send(q)['job_id'];self.assertEqual(self.client.events(job)['head'],1)
        killed('after_result_persist',lambda hook:self.run_owner('work',hook))
        self.assertEqual(self.client.events(job)['head'],1)
        self.run_owner('work');self.assertEqual(self.client.events(job)['head'],2)
        self.assertEqual(self.atoms.head(baseline.SCOPE)['sequence'],2)
        killed('after_delivery_accept',lambda hook:self.run_owner('flush',hook))
        self.assertEqual(self.client.events(job)['head'],2)
        self.assertEqual(len(self.rows('fusion-messaging','messages',mailbox=True)),1)
        self.run_owner('flush');self.assertEqual(self.client.events(job)['head'],3)
        self.assertEqual(len(self.rows('fusion-messaging','messages',mailbox=True)),1)

    def test_expired_unaccepted_envelope_not_charged_but_accepted_replay_retained(self):
        q=self.wire();accepted=self.send(q)
        with patch('time.time_ns',return_value=(self.deadline+1)*1000000):
            self.assertEqual(self.send(q),accepted)
            self.denied('DEADLINE_EXCEEDED',self.send,self.wire('too-late'))
        self.assertEqual(len(self.rows('fusion-execution','integrated_execution_envelopes')),1)

    def test_other_owner_event_identity_does_not_leak_counts(self):
        q=self.wire();job=self.send(q)['job_id']
        request=dict(profile=p.PROFILE,selection=q['selection'],events=dict(job_id=job,source=None,after=0,limit=3))
        self.denied('NOT_FOUND',self.owner().invoke,p.ROUTE,self.token('inspect-caller-B-token'),request)
        request['events']['limit']=999;self.denied('INVALID_ARGUMENT',self.owner().invoke,p.ROUTE,self.token('inspect-caller-A-token'),request)


def load_tests(loader,tests,pattern):
    return unittest.TestSuite(Envelopes(name) for name in Envelopes.__dict__ if name.startswith('test_'))
