"""Recorded-response fixtures for X01; no live Ollama calls in this suite."""
from dataclasses import asdict
import copy
import json
import multiprocessing
from pathlib import Path
import signal
import sqlite3
import tempfile
import time
import unittest
import uuid
from fusion import model_contracts as c
from fusion.contracts import canonical,ContractError
from fusion.model_service import ModelService
from fusion.model_transport import checked
from fusion.neoclaw_model_disclosure import disclose
from fusion.adapters.ollama_completion import convert
from fusion.registry import descriptor_wire,selection_token


def recorded(text='((send "synthetic reply"))',**changes):
    return dict(model=c.MODEL,done=True,done_reason='stop',message=dict(role='assistant',content=text),
        eval_count=8,prompt_eval_count=40,**changes)


class Backend:
    def __init__(self,call=lambda:None): self.calls=0; self.call=call
    def complete(self,accepted): self.calls+=1;self.call();return convert(recorded())


def prompt(user='synthetic input'):
    return 'public scaffold LAST_SKILL_USE_RESULTS:  HISTORY:  MOST_PROMOTED_MEMORIES: () TIME: 2031-01-01 00:00:00:-:-:-:'+user


def setup(root):
    session=str(uuid.uuid4());scope='synthetic-model'
    cfg=dict(principals={'A':dict(credential='generated-token',scopes={scope:['model.'+x for x in ('disclose','complete','observe','authorize')]})},
        model_completion=dict(database=str(root/'model.sqlite'),scope=scope,sharing=c.PRIVACY,sessions=[session],max_calls=3,
        expires_ms=time.time_ns()//1_000_000+30000,catalogue=[descriptor_wire(c.descriptor())],runtime_lock={'fixture':True},
        disclosure=dict(scaffold='public scaffold',memories=['()'],users=['synthetic input'],feedback_expressions=[])))
    path=root/'policy.json';path.write_bytes(canonical(cfg))
    accepted=asdict(c.CompletionInput(id=str(uuid.uuid4()),session=session,slot=1,source_id=str(uuid.uuid4()),principal='A',
        scope=scope,selection=selection_token(c.descriptor()),native_prompt=prompt(),messages=c.messages(prompt()),
        deadline_ms=time.time_ns()//1_000_000+20000))
    return path,cfg,accepted


def request(accepted,operation='complete'):
    return dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation=operation,intent=accepted)


def child(path,accepted,stage,marker):
    import os
    def hook(value):
        if value==stage:
            Path(marker).write_text(value);os.kill(os.getpid(),signal.SIGSTOP)
    service=ModelService(path,Backend(),hook)
    try:service.invoke('generated-token',request(accepted))
    finally:service.close()


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path,self.cfg,self.accepted=setup(self.root)
    def service(self,backend=None,hook=lambda _:None):
        s=ModelService(self.path,backend or Backend(),hook);self.addCleanup(s.close);return s
    def invoke(self,service,op='complete',accepted=None,credential='generated-token'):
        r=request(accepted or self.accepted,op);return checked(r,service.invoke(credential,r))
    def code(self,code,call):
        with self.assertRaises(ContractError) as got:call()
        self.assertEqual(got.exception.code,code)
    def test_capture_and_duplicate_exact_bytes_no_regeneration(self):
        backend=Backend();service=self.service(backend);first=self.invoke(service)
        self.assertEqual(first,self.invoke(service));self.assertEqual(first,self.invoke(service,'observe'));self.assertEqual(backend.calls,1)
    def test_equal_prompt_new_occurrence_and_slot_conflict(self):
        backend=Backend();s=self.service(backend);self.invoke(s)
        other=dict(self.accepted,id=str(uuid.uuid4()))
        self.code('CONFLICT',lambda:self.invoke(s,accepted=other))
        other['slot']=2;self.invoke(s,accepted=other);self.assertEqual(backend.calls,2)
    def test_changed_input_deadline_profile_and_descriptor_refused(self):
        s=self.service();self.invoke(s)
        for key,value in [('deadline_ms',self.accepted['deadline_ms']+1),('source_id',str(uuid.uuid4()))]:
            self.code('CONFLICT',lambda:self.invoke(s,accepted=dict(self.accepted,**{key:value})))
        for key,value in [('profile','elsewhere'),('selection','0'*64),('model','qwen3'),('limits',{})]:
            with self.subTest(key=key),self.assertRaises(ContractError):self.invoke(s,accepted=dict(self.accepted,**{key:value}))
    def test_authorization_rechecked_on_cached_capture(self):
        s=self.service();self.invoke(s)
        self.code('UNAUTHORIZED',lambda:self.invoke(s,credential='wrong'))
        self.cfg['principals']['A']['scopes'][self.accepted['scope']].remove('model.disclose');self.path.write_bytes(canonical(self.cfg))
        self.code('UNAUTHORIZED',lambda:self.invoke(s,'observe'));self.code('UNAUTHORIZED',lambda:self.invoke(s,'authorize'))
    def test_context_private_sections_refused_before_backend(self):
        backend=Backend();s=self.service(backend)
        for old,new in [('public scaffold','private scaffold'),('HISTORY: ','HISTORY: secret'),('MEMORIES: ()','MEMORIES: (private)'),('synthetic input','secret'),('TIME: 2031','TIME: broken')]:
            raw=prompt().replace(old,new)
            with self.subTest(old=old),self.assertRaises(ContractError):self.invoke(s,accepted=dict(self.accepted,native_prompt=raw,messages=c.messages(raw)))
        self.assertEqual(backend.calls,0)
    def test_deadline_not_reset_on_resume(self):
        s=self.service();self.accepted['deadline_ms']=1
        self.code('DEADLINE_EXCEEDED',lambda:self.invoke(s));self.assertEqual(self.invoke(s,'observe')['state'],'absent')
    def test_cpu_deadline_requires_distinct_profile_and_keeps_spent_identity(self):
        backend=Backend();s=self.service(backend)
        long=dict(self.accepted,deadline_ms=time.time_ns()//1_000_000+299000)
        self.code('INVALID_ARGUMENT',lambda:self.invoke(s,accepted=long))
        self.assertEqual(backend.calls,0);s.close();self._cleanups.pop()
        # The old owner seal cannot be rebound. Select a fresh owner explicitly.
        self.cfg['model_completion']['database']=str(self.root/'cpu.sqlite')
        self.cfg['model_completion']['catalogue']=[descriptor_wire(c.descriptor(c.CPU_PROFILE))]
        self.cfg['model_completion']['expires_ms']=time.time_ns()//1_000_000+600000
        self.path.write_bytes(canonical(self.cfg))
        long.update(profile=c.CPU_PROFILE,selection=selection_token(c.descriptor(c.CPU_PROFILE)),limits=c.limits(c.CPU_PROFILE))
        s=self.service(backend);first=self.invoke(s,accepted=long)
        self.assertEqual(first,self.invoke(s,accepted=long));self.assertEqual(backend.calls,1)
        self.code('CONFLICT',lambda:self.invoke(s,accepted=dict(long,deadline_ms=long['deadline_ms']+1)))
        self.code('UNSUPPORTED_PROFILE',lambda:self.invoke(s,accepted=self.accepted))
        self.code('INVALID_ARGUMENT',lambda:self.invoke(s,accepted=dict(long,id=str(uuid.uuid4()),slot=2,deadline_ms=time.time_ns()//1_000_000+301000)))
        self.assertEqual(backend.calls,1)
    def test_failure_after_reservation_remains_spent(self):
        def fail():raise ContractError('NOT_AVAILABLE')
        backend=Backend(fail);s=self.service(backend)
        self.code('NOT_AVAILABLE',lambda:self.invoke(s));self.assertEqual(self.invoke(s)['state'],'unknown');self.assertEqual(backend.calls,1)
    def test_session_budget_no_refund_and_no_configuration_reset(self):
        backend=Backend();s=self.service(backend)
        for slot in range(1,4):self.invoke(s,accepted=dict(self.accepted,id=str(uuid.uuid4()),slot=slot))
        self.code('OVERLOADED',lambda:self.invoke(s,accepted=dict(self.accepted,id=str(uuid.uuid4()),slot=4)))
        self.cfg['model_completion']['max_calls']=4;self.path.write_bytes(canonical(self.cfg))
        self.code('CONFLICT',lambda:self.invoke(s,'observe'))
        self.assertEqual(backend.calls,3)
    def test_late_capture_is_observable_and_labelled(self):
        self.accepted['deadline_ms']=time.time_ns()//1_000_000+100
        s=self.service(Backend(lambda:time.sleep(.15)));result=self.invoke(s)
        self.assertTrue(result['late']);self.assertEqual(result,self.invoke(s,'observe'))
    def test_malformed_receipt_bindings_and_state(self):
        s=self.service();r=request(self.accepted);reply=s.invoke('generated-token',r)
        for key,value in [('id','wrong'),('intent_sha256','0'*64),('selection','wrong'),('principal','B'),('reserved',0),('late',True),('state','accepted')]:
            bad=copy.deepcopy(reply);bad['value'][key]=value
            with self.subTest(key=key),self.assertRaises(ContractError):checked(r,bad)
    def test_text_cleaning_and_unknown_usage(self):
        result=convert(recorded('_quote_Ω_apostrophe_'));self.assertEqual(result['native_text'],'"Ω\'')
        value=recorded();value.pop('eval_count');self.assertIsNone(convert(value)['usage']['output_tokens'])
    def test_empty_truncated_invalid_tool_media_and_usage(self):
        self.assertEqual(convert(recorded(' '))['outcome'],'empty')
        v=recorded();v['done_reason']='length';self.assertEqual(convert(v)['outcome'],'truncated')
        for key,value in [('tool_calls',[{}]),('images',['data']),('thinking','hidden'),('content',None),('role','user')]:
            v=recorded();v['message'][key]=value
            with self.subTest(key=key),self.assertRaises(ContractError):convert(v)
        for key,value in [('eval_count',True),('eval_count',6001),('prompt_eval_count',40000),('done_reason','unknown'),('model','other'),('choices',[{}])]:
            v=recorded();v[key]=value
            with self.subTest(key=key),self.assertRaises(ContractError):convert(v)
    def test_unsealed_journal_rejected_without_mutation(self):
        with sqlite3.connect(self.cfg['model_completion']['database']) as db:db.execute('CREATE TABLE unrelated(x)')
        self.code('UNSUPPORTED_PROFILE',lambda:ModelService(self.path,Backend()))
        with sqlite3.connect(self.cfg['model_completion']['database']) as db:self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[('unrelated',)])
    def test_process_kill_independent_commits_and_recovery(self):
        for stage,state in [('after_model_acceptance','accepted'),('after_model_reservation','unknown'),('after_model_backend_response','unknown'),('after_model_provider_capture','captured')]:
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);path,cfg,accepted=setup(root);marker=root/'pause'
                process=multiprocessing.Process(target=child,args=(path,accepted,stage,str(marker)));process.start()
                try:
                    deadline=time.monotonic()+5
                    while not marker.exists() and process.is_alive() and time.monotonic()<deadline:time.sleep(.01)
                    self.assertTrue(marker.exists());process.kill();process.join(3)
                    backend=Backend();service=ModelService(path,backend)
                    try:
                        r=request(accepted,'observe');self.assertEqual(checked(r,service.invoke('generated-token',r))['state'],state)
                        r=request(accepted);value=checked(r,service.invoke('generated-token',r))
                        self.assertEqual(backend.calls,1 if state=='accepted' else 0)
                        self.assertEqual(value['reserved'],1)
                    finally:service.close()
                finally:
                    if process.is_alive():process.kill()
                    process.join(3)
