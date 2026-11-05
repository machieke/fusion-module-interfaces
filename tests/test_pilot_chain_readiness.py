"""Explicit transport/reader fixtures; no provider, node or native-work claims."""
import contextlib
import http.client
import io
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch
from fusion.contracts import ContractError,canonical,digest
from examples import pilot_chain_readiness as module
from examples.sustained_chain_qualification import Qualification

class BoundedHealth(unittest.TestCase):
 def run_health(self,mode):
  events=[];requests=[];clock=[0.0]
  class Response:
   status=503 if mode=='not-ready'else 200;fp=None
   def __init__(self):self.parts=[canonical(dict(role='wrong'if mode=='malformed'else'fusion-storage',ready=mode!='not-ready')),b'']
   def read1(self,_):return self.parts.pop(0)
  class HealthConnection:
   def __init__(self,*args,**kwargs):pass
   def request(self,method,path,headers):
    requests.append((method,path,headers));assert method=='GET'and path=='/health/ready'and'Authorization'not in headers
    if mode=='refused'or(mode=='transient'and len(requests)==1):raise ConnectionRefusedError(111,'fixture service unavailable')
   def getresponse(self):return Response()
   def close(self):pass
  with patch.object(http.client,'HTTPSConnection',HealthConnection),patch('ssl.create_default_context',return_value=SimpleNamespace()),patch.object(module.time,'monotonic',side_effect=lambda:clock[0]),patch.object(module.time,'sleep',side_effect=lambda n:clock.__setitem__(0,clock[0]+n)):
   try:module.health({'atoms':{'endpoint':{'host':'fixture.invalid','port':8443,'ca_file':'unused'}}},events);error=None
   except Exception as exc:error=exc
  return events,requests,error
 def test_transient_health_refusal_then_ready_does_not_read_artifact(self):
  events,requests,error=self.run_health('transient');self.assertIsNone(error);self.assertEqual(len(requests),2);self.assertEqual([x['status']for x in events],['TRANSPORT_FAILED','READY'])
 def test_eight_health_attempts_exhaust_without_reader(self):
  events,requests,error=self.run_health('refused');self.assertIsInstance(error,TimeoutError);self.assertEqual(len(requests),8);self.assertEqual(len(events),8)
 def test_bad_health_shape_refuses_immediately(self):
  events,requests,error=self.run_health('malformed');self.assertIsInstance(error,ValueError);self.assertEqual(len(requests),1)
 def test_provider_not_ready_is_finite(self):
  events,requests,error=self.run_health('not-ready');self.assertIsInstance(error,TimeoutError);self.assertEqual(len(requests),8);self.assertTrue(all(x['status']=='NOT_READY'for x in events))
class ReaderAdmission(unittest.TestCase):
    def reader(self, failure=None):
        calls=[]
        def observe(trace,config):
            calls.append('observe')
            if failure:raise failure
            return dict(status='PASS',captured='explicit fixture')
        reader=SimpleNamespace(trace_plan=lambda trace:(SimpleNamespace(scope_ref='synthetic-test'),None),
            configuration=lambda config,scope:calls.append('configuration'),observe=observe)
        return reader,calls
    def test_one_original_reader_after_readiness(self):
        reader,calls=self.reader();events=[]
        with patch.object(module,'health',side_effect=lambda config,e:calls.append('health')):
            value=module.observe_with_health(reader,{}, {},events)
        self.assertEqual(calls,['configuration','health','observe']);self.assertEqual(value['captured'],'explicit fixture')
    def test_failed_health_never_invokes_reader(self):
        reader,calls=self.reader()
        with patch.object(module,'health',side_effect=TimeoutError('fixture unavailable')):
            with self.assertRaises(TimeoutError):module.observe_with_health(reader,{}, {},[])
        self.assertEqual(calls,['configuration'])
    def test_original_read_failure_not_retried_or_repaired(self):
        reader,calls=self.reader(ContractError('NOT_AVAILABLE'))
        with patch.object(module,'health',return_value=None):
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):module.observe_with_health(reader,{}, {},[])
        self.assertEqual(calls,['configuration','observe'])
    def test_original_validation_precedes_health(self):
        reader,calls=self.reader();reader.configuration=lambda *args:(_ for _ in ()).throw(ContractError('UNAUTHORIZED'))
        with patch.object(module,'health')as health:
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):module.observe_with_health(reader,{}, {},[])
        health.assert_not_called();self.assertEqual(calls,[])
    def test_composed_source_embeds_unchanged_reader_and_calls_it_once(self):
        original='from types import SimpleNamespace\nimport json\ndef strict_json(raw):return json.loads(raw)\ndef trace_plan(trace):return SimpleNamespace(scope_ref="synthetic-test"),None\ndef configuration(config,scope):return None\ndef observe(trace,config):return {"status":"PASS","capture":trace["actual"]}\n'
        code=module.compose(original);namespace={'__name__':'composed_fixture','__file__':module.__file__};exec(compile(code,'composed','exec'),namespace)
        calls=[];namespace['health']=lambda config,events:(calls.append('health'),events.append(dict(status='READY')))
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);(root/'trace').write_text('{"actual":"recorded fixture"}');(root/'config').write_text('{}')
            with patch('sys.argv',['reader','--trace',str(root/'trace'),'--config',str(root/'config')]),contextlib.redirect_stdout(io.StringIO())as output:
                self.assertEqual(namespace['main'](original),0)
        result=json.loads(output.getvalue());self.assertEqual(result['capture'],'recorded fixture');self.assertEqual(calls,['health']);self.assertEqual(result['consumer_path_readiness']['original_reader_sha256'],digest(original.encode()));self.assertEqual(result['consumer_path_readiness']['original_reader_invocations'],1)
    def test_invalid_original_source_refused(self):
        for source in ['',None,'a'*65537,'this is invalid python !!!']:
            with self.subTest(source_type=type(source).__name__):
                with self.assertRaises((ValueError,SyntaxError)):module.compose(source)

class OptInComposition(unittest.TestCase):
    def composition(self, enabled):
        class Operator:
            namespace='fixture-namespace'
            def __init__(self):self.applied=[]
            def apply(self,value):self.applied.append(value)
            def k(self,*args):
                if args[:2]==('get','secret'):return json.dumps(dict(data={'ca.crt':'fixture','commit-storage-token':'fixture'}))
                if args[:1]==('logs',):return '{"status":"PASS"}'
                if args[:2]==('get','pod'):return 'Succeeded'if args[-1]=='jsonpath={.status.phase}'else '{}'
                return ''
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory);original='print("historical fixture source")';path=root/'reader.py';path.write_text(original)
            q=object.__new__(Qualification);q.op=Operator();q.root=root;q.values={'preview':{'profile':'omega-single-node-sustained-preview/1'},'components':{'fusion-commitment':{'image':{'repository':'fixture','digest':'sha256:'+'0'*64}}}};q.report={'registration':{'approved':{'scope_ref':'synthetic-test'}},'saved_intent':{},'final_observation':{}}
            bounds=[];q.wait=lambda fn,seconds:(bounds.append(seconds),fn());q.independent(path,consumer_path_health=enabled)
            source=next(x for x in q.op.applied if x['kind']=='ConfigMap')['data']['observer.py']
            return original,source,bounds,q.report
    def test_historical_default_source_and_bound_preserved(self):
        original,source,bounds,report=self.composition(False);self.assertEqual(source,original);self.assertEqual(bounds,[60]);self.assertNotIn('original_observer_source_sha256',report)
    def test_explicit_selection_uses_composed_source_and_bounded_observer(self):
        original,source,bounds,report=self.composition(True);self.assertEqual(bounds,[180]);self.assertIn(repr(original),source);self.assertEqual(report['original_observer_source_sha256'],digest(original.encode()))

if __name__=='__main__':unittest.main(verbosity=2)
