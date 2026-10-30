"""Closed deployment seams; recorded responses are explicit fixtures."""
from dataclasses import asdict
import copy,json,subprocess,sys,tempfile,time,unittest,uuid
from pathlib import Path
from fusion import model_contracts as m, retrieval_services as s
from fusion.contracts import ContractError,canonical,digest
from fusion.registry import descriptor_wire,selection_token
from integration.neoclaw.model_startup import retrieval_scaffold
from integration.neoclaw.retrieval_preparation import QUERY,QUESTION,FOLLOWUP

class Services(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.session=str(uuid.uuid4());self.policy=dict(policy=s.POLICY,scaffold=retrieval_scaffold(),memories=['()'],users=[str(['HUMAN-MSG:','peer: '+x]) for x in (QUESTION,FOLLOWUP)],query=QUERY,recipient='recorded-k3s-model')
        raw=self.policy['scaffold']+' LAST_SKILL_USE_RESULTS:  HISTORY:  MOST_PROMOTED_MEMORIES: () TIME: 2032-10-20 12:00:00:-:-:-:'+self.policy['users'][0]
        self.intent=asdict(m.CompletionInput(id=str(uuid.uuid4()),session=self.session,slot=1,source_id=str(uuid.uuid4()),principal='M',scope='synthetic-model',selection=selection_token(m.descriptor(m.CPU_PROFILE)),native_prompt=raw,messages=m.messages(raw),deadline_ms=time.time_ns()//1000000+300000,profile=m.CPU_PROFILE,limits=m.limits(m.CPU_PROFILE)))
        a=self.intent;self.receipt=dict(profile=s.RECEIPT,issuer='M',recipient=self.policy['recipient'],consent_sha256='a'*64,view_sha256='b'*64,intent_sha256=digest(canonical(a)),native_prompt_sha256=digest(raw.encode()),messages_sha256=digest(canonical(a['messages'])),principal='M',scope=a['scope'],session=self.session,occurrence=a['id'],source_id=a['source_id'],slot=1,selection=a['selection'],model_profile=a['profile'],deadline_ms=a['deadline_ms'],query=None)
        self.cfg=dict(model_completion=dict(database=str(self.root/'model.sqlite'),scope=a['scope'],sharing=m.PRIVACY,sessions=[self.session],max_calls=2,expires_ms=a['deadline_ms'],catalogue=[descriptor_wire(m.descriptor(m.CPU_PROFILE))],runtime_lock={'fixture':'explicit'},disclosure=self.policy,disclosure_issuers=['M']),principals={'M':dict(credential='test-credential',scopes={a['scope']:['model.'+x for x in ('issue','disclose','authorize','observe','complete')]}),'other':dict(credential='other-credential',scopes={a['scope']:['model.'+x for x in ('issue','disclose','authorize','observe','complete')]})})
        self.path=self.root/'policy.json';self.save();self.calls=[]
        class Backend:
            def complete(_,accepted):
                self.calls.append(accepted.id)
                from fusion.adapters.ollama_completion import convert
                return convert(dict(model=m.MODEL,done=True,done_reason='stop',message=dict(role='assistant',content='query '+QUERY)))
        self.owner=s.ModelPorts(self.path,Backend())
    def save(self):self.path.write_bytes(canonical(self.cfg))
    def wire(self,op='complete'):
        return dict(profile=s.POLICY,request=dict(interface_ref=dict(id=m.INTERFACE,version=m.VERSION),operation=op,intent=self.intent),receipt=self.receipt)
    def meta(self):return s.metadata(dict(principal='M',disclosure={**self.policy,'consent_sha256':'a'*64,'view_sha256':'b'*64}),self.intent,'disclose')
    def test_00_generation_denial_before_construction_contact_or_launch(self):
        code='''from integration.single_node.recorded_model import deny_live
from fusion.contracts import ContractError
try:deny_live('live')
except ContractError as e:assert e.code=='UNAUTHORIZED'
else:raise AssertionError('live allowed')
assert deny_live('recorded')['real_backend_calls']==0
from fusion.adapters.ollama_completion import OllamaCompletion
import socket,subprocess
for action in [lambda:OllamaCompletion({}),lambda:socket.create_connection(('127.0.0.1',11434)),lambda:subprocess.run(['false'])]:
 try:action()
 except PermissionError:pass
 else:raise AssertionError('effect not denied')
print('GENERATION_DENIAL_TESTED=PASS; real runtime never contacted')
'''
        result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
    def test_metadata_only_preflight_and_current_execution_authority(self):
        q=self.meta();self.assertNotIn('native_prompt',q);self.assertNotIn('messages',q)
        self.assertTrue(self.owner.invoke('/model-disclosure','test-credential',q)['authorized']);self.assertEqual(self.calls,[])
        self.cfg['principals']['M']['scopes'][self.intent['scope']].remove('model.disclose');self.save()
        with self.assertRaises(ContractError):self.owner.invoke('/model-disclosure','test-credential',q)
    def test_exact_receipt_binding_and_no_owner_receipt_file(self):
        self.assertNotIn('receipt_root',self.cfg['model_completion']['disclosure'])
        for key,value in [('issuer','other'),('recipient','another'),('occurrence',str(uuid.uuid4())),('source_id',str(uuid.uuid4())),('session',str(uuid.uuid4())),('deadline_ms',1),('native_prompt_sha256','0'*64),('model_profile',m.PROFILE)]:
            q=self.wire();q['receipt']=dict(self.receipt,**{key:value})
            with self.subTest(key=key),self.assertRaises(ContractError):self.owner.invoke('/s07-model-services','test-credential',q)
        self.assertEqual(self.calls,[])
    def test_capture_replay_revocation_and_original_reservation(self):
        a=self.owner.invoke('/s07-model-services','test-credential',self.wire());b=self.owner.invoke('/s07-model-services','test-credential',self.wire())
        self.assertEqual(a,b);self.assertEqual(self.calls,[self.intent['id']]);self.assertEqual(a['value']['reserved'],1)
        self.cfg['model_completion']['disclosure_issuers']=[];self.save()
        with self.assertRaises(ContractError):self.owner.invoke('/s07-model-services','test-credential',self.wire('observe'))
        self.assertEqual(len(self.calls),1)
    def test_principal_profile_and_unknown_receipt_fields_refused(self):
        for change in ('credential','profile','extra'):
            q=self.wire();token='test-credential'
            if change=='credential':token='other-credential'
            elif change=='profile':q['profile']='old-file-policy'
            else:q['receipt']=dict(self.receipt,approved=True)
            with self.subTest(change=change),self.assertRaises(ContractError):self.owner.invoke('/s07-model-services',token,q)
        self.assertEqual(self.calls,[])
    def test_spent_unknown_never_recomputed(self):
        def kill(stage):
            if stage=='after_model_reservation':raise RuntimeError('simulated interrupt; pod kill tested separately')
        self.owner.hook=kill
        with self.assertRaises(RuntimeError):self.owner.invoke('/s07-model-services','test-credential',self.wire())
        self.owner.hook=lambda _:None
        result=self.owner.invoke('/s07-model-services','test-credential',self.wire())
        self.assertEqual(result['value']['state'],'unknown');self.assertEqual(result['value']['reserved'],1);self.assertEqual(self.calls,[])


    def test_receipt_cannot_move_to_another_recipient_occurrence_scope_or_profile(self):
        for key,value in [('recipient','other-service'),('occurrence',str(uuid.uuid4())),('scope','other-scope'),('model_profile',m.PROFILE),('issuer','other')]:
            with self.subTest(key=key):
                request=self.wire();request['receipt']=dict(self.receipt,**{key:value})
                with self.assertRaises(ContractError):self.owner.invoke('/s07-model-services','test-credential',request)
                self.assertEqual(self.calls,[])

    def test_revocation_after_capture_prevents_reuse_without_refunding(self):
        first=self.owner.invoke('/s07-model-services','test-credential',self.wire())
        self.cfg['principals']['M']['scopes'][self.intent['scope']].remove('model.disclose');self.save()
        with self.assertRaises(ContractError) as error:self.owner.invoke('/s07-model-services','test-credential',self.wire('observe'))
        self.assertEqual(error.exception.code,'UNAUTHORIZED');self.assertEqual(len(self.calls),1)
        from fusion.model_service import ModelService
        row=ModelService.inspect(self.path)[0]
        self.assertEqual(row['reserved'],1);self.assertIsNotNone(row['response'])

    def test_deployment_recorded_backend_uses_real_capture_lifecycle(self):
        from integration.single_node.recorded_model import RecordedBackend,BOUNDARY
        fixture=dict(boundary=BOUNDARY,mode='recorded',session=self.session,responses=['query '+QUERY,'send Insufficient retrieved information.'],log=str(self.root/'evaluations.jsonl'))
        file=self.root/'recorded.json';file.write_bytes(canonical(fixture))
        lock=dict(path=str(file),sha256=digest(file.read_bytes()))
        self.cfg['model_completion']['runtime_lock']=lock;self.save()
        owner=s.ModelPorts(self.path,RecordedBackend(lock))
        first=owner.invoke('/s07-model-services','test-credential',self.wire())
        second=owner.invoke('/s07-model-services','test-credential',self.wire())
        self.assertEqual(first,second);self.assertEqual(len((self.root/'evaluations.jsonl').read_text().splitlines()),1)

    def test_future_connection_rejects_absent_approval_before_backend_constructor(self):
        from unittest.mock import patch
        from integration.single_node import future_live as f
        p=self.root/'future.json';v=dict(schema=f.SCHEMA,kind='live',freeze='COMPLETE')
        p.write_bytes(canonical(v));p.with_suffix('.sha256').write_text(digest(p.read_bytes()))
        with patch('fusion.adapters.ollama_completion.OllamaCompletion') as backend:
            with self.assertRaises(ContractError):f.Backend(p,None)
            backend.assert_not_called()

    def test_future_entrypoints_deny_before_host_or_runtime_activity(self):
        from unittest.mock import patch
        from integration.single_node import future_live as f
        path=self.root/'disabled.json';path.write_bytes(canonical(dict(schema=f.SCHEMA,kind='live',freeze='INCOMPLETE')))
        path.with_suffix('.sha256').write_text(digest(path.read_bytes()))
        with patch('integration.single_node.server.main') as host,patch('os.execve') as launch:
            for action in (lambda:f.serve(path,None,None),lambda:f.runtime(path,None)):
                with self.assertRaises(ContractError):action()
            host.assert_not_called();launch.assert_not_called()
