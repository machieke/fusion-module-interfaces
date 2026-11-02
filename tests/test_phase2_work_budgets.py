"""Real inbox/SQLite budget transitions, with explicit application/clock fixtures."""
import json,sqlite3,tempfile,time,unittest,uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from fusion.contracts import ContractError,canonical,require
from fusion.preview_application import PreviewAdoption
from fusion.preview_context import WorkingContext
from fusion.preview_handles import make
from fusion.preview_native_memory import SharedMemory
from fusion.preview_native_relations import NativeRelations
from fusion.preview_sessions import SessionStore,PROFILE
from fusion.preview_tools import SessionAuthority,context_tools,task_tools

class WorkBudgets(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def binding(self):return dict(catalogue='explicit-selected-catalogue',policy='synthetic-policy',model_boundary='RECORDED_FIXTURE',limits=dict(inputs=8,pending=4,timeout_ms=120000))
 def test_input_window_is_captured_once_and_deadline_does_not_move_on_retry(self):
  now=[1000000];db=SessionStore(self.root/'inbox.sqlite',lambda *_:None,clock=lambda:now[0]);self.addCleanup(db.close)
  sid=str(uuid.uuid4());db.create('A',sid,'synthetic-work',self.binding())
  first=db.submit('A',sid,'one','Synthetic task','synthetic');self.assertEqual(first['deadline'],1120000)
  now[0]+=90000
  self.assertEqual(first,db.submit('A',sid,'one','Synthetic task','synthetic'))
  second=db.submit('A',sid,'two','Synthetic task','synthetic');self.assertEqual(second['deadline'],1210000)
  self.assertEqual(context_tools()[0].timeout_ms,30000);self.assertEqual(task_tools()[0].timeout_ms,120000)
  binding=self.binding();binding['limits']['timeout_ms']=120001
  with self.assertRaises(ContractError):db.create('A',str(uuid.uuid4()),'synthetic-work',binding)
 def test_populated_development_profile_without_marker_is_rejected_without_mutation(self):
  path=self.root/'old.sqlite'
  with sqlite3.connect(path) as db:db.executescript('CREATE TABLE preview_sessions(id TEXT); INSERT INTO preview_sessions VALUES("old");')
  before=path.read_bytes()
  with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):SessionStore(path,lambda *_:None)
  self.assertEqual(path.read_bytes(),before)
 def test_dispatch_reservations_survive_reopen_and_saved_result_does_not_refund(self):
  path=self.root/'app.sqlite'
  def adoption(hook):
   p=PreviewAdoption.__new__(PreviewAdoption);p.db=sqlite3.connect(path);p.db.row_factory=sqlite3.Row
   p.db.execute('CREATE TABLE IF NOT EXISTS preview_dispatch_budget(occurrence TEXT PRIMARY KEY,attempts INTEGER NOT NULL)')
   p.app=SimpleNamespace(hook=hook);p.catalogue=SimpleNamespace(tools={'pin':context_tools()[0]})
   p.authorize=lambda _:SimpleNamespace(tools={'pin'})
   return p
  def crash(_):raise InterruptedError('explicit kill-after-commit fixture')
  p=adoption(crash);row=dict(id='occurrence',done=0,deadline=2000)
  with patch('fusion.preview_application.time.time_ns',return_value=1000_000_000):
   with self.assertRaises(InterruptedError):p.reserve_dispatch(row,'pin')
  p.db.close();p=adoption(lambda _:None);self.addCleanup(p.db.close)
  with patch('fusion.preview_application.time.time_ns',return_value=1000_000_000):
   p.reserve_dispatch(row,'pin')
   with self.assertRaisesRegex(ContractError,'OVERLOADED'):p.reserve_dispatch(row,'pin')
  with patch('fusion.preview_application.time.time_ns',return_value=3000_000_000):
   p.reserve_dispatch(dict(row,done=1),'pin')
   with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):p.reserve_dispatch(dict(row,id='new'),'pin')
  self.assertEqual(p.db.execute('SELECT attempts FROM preview_dispatch_budget').fetchone()[0],2)
  p.authorize=lambda _:SimpleNamespace(tools=set())
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.reserve_dispatch(dict(row,done=1),'pin')

class ExactExpiryTests(unittest.TestCase):
 """Real reservation/context code; application, authorization and ports are fixtures."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='phase2-expiry-');self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.now=1999;self.deadline=2000;self.allowed=True
  timer=patch('time.time_ns',side_effect=lambda:self.now*1000000);timer.start();self.addCleanup(timer.stop)
  self.db=sqlite3.connect(self.root/'application-fixture.sqlite');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
  self.db.executescript('''CREATE TABLE preview_dispatch_budget(occurrence TEXT PRIMARY KEY,attempts INTEGER NOT NULL);
   CREATE TABLE preview_context_acceptance(occurrence TEXT PRIMARY KEY,expected_revision INTEGER NOT NULL);
   CREATE TABLE preview_file_acceptances(occurrence TEXT PRIMARY KEY,revision INTEGER NOT NULL);''')
  self.p=PreviewAdoption.__new__(PreviewAdoption);self.p.db=self.db;self.p.app=SimpleNamespace(hook=Mock())
  tools={'pin','unpin','task-context','read-file','write-file','append-file'}
  self.authority=SimpleNamespace(tools=tools,revision='fixture-policy')
  def authorize(operation):require(self.allowed,'UNAUTHORIZED');return self.authority
  self.p.authorize=authorize;self.p.catalogue=SimpleNamespace(identity='fixture-selection',tools={t.native_name:t for t in context_tools()})
  self.p.context=WorkingContext(self.db,authorize)
  self.workspace=Mock();self.p.facets={'execution.workspace':self.workspace}
  def respond(operation,*args,**kwargs):
   if operation=='authorize':return {'authorized':True}
   if operation=='version':return dict(profile='fixture-workspace',path=args[0],revision=0,digest=None)
   if operation in ('write','append'):return dict(identity=args[0],revision=1,outcome='committed')
   if operation=='read':return dict(text='Synthetic file fixture')
   raise AssertionError(operation)
  self.workspace.call.side_effect=respond
 def row(self,operation,args,identity='input-one',result=None):
  return dict(id=identity,done=int(result is not None),deadline=self.deadline,result=result,premises=canonical(dict(operation=operation,
   arguments=dict(selection='fixture-selection',policy='fixture-policy',arguments=args))).decode())
 def test_exact_expiry_cannot_reserve_new_dispatch_but_done_observation_keeps_spend(self):
  row=self.row('pin',{'item':'task','note':'Synthetic note'})
  self.p.reserve_dispatch(row,'pin');self.now=self.deadline
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.p.reserve_dispatch(row,'pin')
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.p.reserve_dispatch(dict(row,id='new'),'pin')
  self.p.reserve_dispatch(dict(row,done=1),'pin')
  self.assertEqual([tuple(r) for r in self.db.execute('SELECT * FROM preview_dispatch_budget')],[('input-one',1)])
  self.allowed=False
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.p.reserve_dispatch(dict(row,done=1),'pin')
 def test_exact_expiry_cannot_change_context_but_captured_result_rechecks_authority(self):
  row=self.row('pin',{'item':'task','note':'Synthetic note'})
  with self.db:self.db.execute('INSERT INTO preview_context_acceptance VALUES(?,0)',(row['id'],))
  saved=self.p.replay(row);self.assertEqual(self.p.context.read()['revision'],1)
  self.now=self.deadline
  self.assertEqual(self.p.replay(dict(row,result=saved)),saved)
  fresh=self.row('pin',{'item':'other','note':'New effect'},identity='new')
  with self.db:self.db.execute('INSERT INTO preview_context_acceptance VALUES(?,1)',(fresh['id'],))
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):self.p.replay(fresh)
  self.assertEqual(self.p.context.read()['items'],{'task':'Synthetic note'})
  self.assertEqual(self.db.execute('SELECT count(*) FROM preview_context_receipts').fetchone()[0],1)
  self.allowed=False
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.p.replay(dict(row,result=saved))
 def test_workspace_effect_and_version_calls_forward_original_deadline(self):
  for operation in ('read-file','write-file','append-file'):
   self.workspace.call.reset_mock()
   args={'path':'synthetic.txt'}
   if operation!='read-file':args['text']='Synthetic content'
   self.p.replay(self.row(operation,args,identity=operation))
   calls=[c for c in self.workspace.call.call_args_list if c.args[0]!='authorize']
   self.assertTrue(calls)
   for call in calls:self.assertEqual(call.kwargs,{'deadline':self.deadline})
  self.now=self.deadline;self.workspace.call.reset_mock()
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):
   self.p.replay(self.row('write-file',{'path':'new.txt','text':'Expired effect'},identity='expired'))
  self.assertEqual([c.args[0] for c in self.workspace.call.call_args_list],['authorize'])
 def test_shared_memory_expiry_preserves_calls_and_original_deadline(self):
  memory=SharedMemory.__new__(SharedMemory);memory.db=self.db;memory.app=SimpleNamespace(hook=Mock())
  port=Mock();port.call.return_value={'observed':True};memory.clients={'search':port}
  self.db.execute('CREATE TABLE preview_memory_plans(identity TEXT PRIMARY KEY,deadline INTEGER,calls INTEGER DEFAULT 0)')
  memory.open_plan('view-one',self.deadline)
  memory.call('view-one','search','current','bound-view')
  port.call.assert_called_once_with('current','bound-view',deadline=self.deadline)
  self.now=self.deadline
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):memory.call('view-one','search','build','bound-view')
  self.assertEqual(tuple(self.db.execute('SELECT deadline,calls FROM preview_memory_plans').fetchone()),(self.deadline,1))
  port.call.side_effect=ContractError('UNAUTHORIZED')
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):memory.call('view-one','search','authorize','bound-view',bounded=False)
  self.assertEqual(tuple(self.db.execute('SELECT deadline,calls FROM preview_memory_plans').fetchone()),(self.deadline,2))
  port.call.assert_called_with('authorize','bound-view',deadline=None)
 def test_relation_expiry_blocks_rpc_reservation_and_endpoint_creation_but_saved_result_observes(self):
  scope='synthetic-expiry';ref=lambda name:dict(scope_ref=scope,id=name,revision=1,digest='a'*64)
  history=make('episode',scope,'A',dict(scope_ref=scope,id='fixture-episode'))
  memory=dict(logical_id=str(uuid.uuid4()),uuid=str(uuid.uuid4()),envelope=make('memory',scope,'A',dict(payload=ref('payload'),enrollment=ref('enrollment'))))
  lifecycle=Mock();lifecycle.call.return_value={'authorized':True}
  app=SimpleNamespace(db=self.db,preview_config={'scope':scope},binding={'principal':'A'},hook=Mock(),
   preview=SimpleNamespace(history=SimpleNamespace(resolve=Mock(return_value=history)),
    memory=SimpleNamespace(clients={'memory.lifecycle':lifecycle},atoms=Mock())))
  port=Mock();port.call.return_value={'authorized':True};relations=NativeRelations(app,port)
  with self.db:self.db.execute('INSERT INTO preview_link_acceptances VALUES(?,?)',('link-one',canonical(dict(memory=memory,history=history)).decode()))
  row=dict(id='link-one',deadline=self.deadline,result=None)
  self.now=self.deadline
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):relations.call(row,'assertRelation')
  self.assertEqual(self.db.execute('SELECT count(*) FROM preview_link_calls').fetchone()[0],0)
  with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):relations.replay(row,'link')
  app.preview.memory.atoms.assert_not_called()
  saved='{"status":"LINKED","boundary":"CAPTURED_RESULT_FIXTURE"}'
  self.assertEqual(relations.replay(dict(row,result=saved),'link'),saved)
  lifecycle.call.side_effect=ContractError('UNAUTHORIZED')
  with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):relations.replay(dict(row,result=saved),'link')
  app.preview.memory.atoms.assert_not_called()

if __name__=='__main__':unittest.main()
