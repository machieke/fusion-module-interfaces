"""Operator targeting/cleanup fixtures. No container pause or native-provider claim."""
import copy,json,sqlite3,tempfile,unittest,uuid
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError
from examples.pilot_attention_suspension import selected_task,suspend,freeze_plan,PORT,DIAGNOSTIC,TEMPLATE


class ClosedTemplateSelection(unittest.TestCase):
    """Actual owner allocation/control + SQLite reads; configuration/TLS fixtures."""
    def setUp(self):
        from tests.test_phase3_sessions import policy
        from fusion.contracts import canonical
        from fusion.sustained_sessions import SustainedSessionStore
        from integration.single_node.sustained_runtime import runtime_digest
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.directory=self.root/'run'/'templates'/'shared';self.directory.mkdir(parents=True)
        files={'application.json':{'fixture':'not a native application'},'attention-client.json':{'credential':'fixture-current'},'memory-atoms.json':{'scope':'synthetic'}}
        for name,value in files.items():(self.directory/name).write_bytes(canonical(value))
        self.ca=self.root/'ca.crt';self.ca.write_bytes(b'explicit fixture TLS bytes')
        self.allocation=policy();template=self.allocation['templates'].pop('shared');template['runtime_digest']=runtime_digest(files,self.ca)
        self.allocation['templates']['g2-shared']=template
        self.database=self.root/'inbox.sqlite';store=SustainedSessionStore(self.database,lambda *_:None,self.allocation)
        try:
            self.sid=store.allocate('A','supplement-fixture','g2-shared')['session']
            store.control('A',self.sid,'closed','close')
        finally:store.close()
        self.cfg={'native_sessions':{'principal':'A','scope':template['scope'],'handover':{'generation':2},'database':str(self.database),'allocation':self.allocation,
            'runtime_templates':{'g2-shared':{'directory':str(self.directory),'ca_file':str(self.ca)}}}}
        self.owner=self.root/'owner.json';self.save()
        namespace={};exec(TEMPLATE,namespace);self.select=namespace['selected_template']
    def save(self):self.owner.write_text(json.dumps(self.cfg))
    def snapshot(self):
        # SQLite mode=ro may create/update SHM read locks and an empty WAL.
        # Compare authoritative DB/WAL bytes and configuration; do not call
        # those engine lock/cache files application writes or physical erasure.
        return {str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()
            and not p.name.endswith('-shm') and not (p.name.endswith('-wal') and p.stat().st_size==0)}
    def test_closed_current_template_is_read_without_session_resurrection_or_database_write(self):
        before=self.snapshot();self.assertEqual(self.select(self.owner,self.sid),self.directory)
        self.assertEqual(self.snapshot(),before);self.assertFalse((self.root/'run'/'sessions').exists())
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute('SELECT state FROM preview_sessions').fetchall(),[('closed',)])
            self.assertEqual(db.execute('SELECT count(*) FROM preview_inputs').fetchone()[0],0)
    def test_changed_template_or_ca_refuses_without_database_mutation(self):
        before=self.database.read_bytes();self.allocation['templates']['g2-shared']['runtime_digest']='f'*64;self.save()
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.select(self.owner,self.sid)
        self.assertEqual(self.database.read_bytes(),before)
        with closing(sqlite3.connect(self.database)) as db:
            self.allocation['templates']['g2-shared']['runtime_digest']=json.loads(db.execute('SELECT frozen FROM sustained_allocations').fetchone()[0])['runtime_digest']
        self.save()
        self.ca.write_bytes(b'changed fixture TLS')
        with self.assertRaisesRegex(ContractError,'CONFLICT'):self.select(self.owner,self.sid)
        self.assertEqual(self.database.read_bytes(),before)
    def test_historical_executable_session_is_refused_without_mutation(self):
        with closing(sqlite3.connect(self.database)) as db:
            with db:
                db.execute('CREATE TABLE pilot_historical_sessions(session TEXT PRIMARY KEY)');db.execute('INSERT INTO pilot_historical_sessions VALUES(?)',(self.sid,))
        before=self.snapshot()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.select(self.owner,self.sid)
        self.assertEqual(self.snapshot(),before)
    def test_wrong_generation_or_unknown_session_is_refused(self):
        self.cfg['native_sessions']['handover']['generation']=1;self.save()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.select(self.owner,self.sid)
        self.cfg['native_sessions']['handover']['generation']=2;self.save()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.select(self.owner,str(uuid.UUID(int=2)))
    def test_wrong_principal_scope_or_private_selection_is_refused(self):
        for key,value in [('principal','other'),('scope','private-other')]:
            old=self.cfg['native_sessions'][key];self.cfg['native_sessions'][key]=value;self.save();before=self.snapshot()
            with self.subTest(key=key),self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.select(self.owner,self.sid)
            self.assertEqual(self.snapshot(),before);self.cfg['native_sessions'][key]=old;self.save()
        from fusion.sustained_sessions import SustainedSessionStore
        self.allocation['templates']['private']=copy.deepcopy(self.allocation['templates']['g2-shared'])
        store=SustainedSessionStore(self.database,lambda *_:None,self.allocation)
        try:
            private=store.allocate('A','private-fixture','private')['session'];store.control('A',private,'close','close')
        finally:store.close()
        self.save();before=self.snapshot()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):self.select(self.owner,private)
        self.assertEqual(self.snapshot(),before)


class OwnerFixture:
    namespace='omega-ref-pilot-suspension-fixture'
    def __init__(self):
        self.calls=[];self.paused=False;self.absent=False
        self.pod=dict(metadata=dict(namespace=self.namespace,uid='pod',labels={'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':'fusion-attention'},
            ownerReferences=[dict(controller=True,kind='StatefulSet',name='fusion-attention',uid='owner')]),
            spec=dict(nodeName='omega-fusion-k3s',containers=[dict(name='fusion-attention')]),
            status=dict(containerStatuses=[dict(containerID='containerd://'+'a'*64,image='pinned:test',imageID='pinned@sha256:'+'b'*64,restartCount=0)]))
    def owned(self):return dict(metadata=dict(uid='namespace',labels={'omega.pilot/task':'synthetic-test'}))
    def k(self,*args,**kwargs):
        if args[1]=='statefulset':return json.dumps(dict(metadata=dict(uid='owner',labels=self.pod['metadata']['labels'])))
        return json.dumps(self.pod)
    def command(self,args,**kwargs):
        self.calls.append(args)
        if args[-3:-1]==['containers','info']:
            return json.dumps(dict(Image='pinned:test',Labels={'io.kubernetes.pod.namespace':self.namespace,'io.kubernetes.pod.uid':'pod',
                'io.kubernetes.pod.name':'fusion-attention-0','io.kubernetes.container.name':'fusion-attention'}))
        if args[-3:-1]==['tasks','pause']:self.paused=True
        if args[-3:-1]==['tasks','resume']:self.paused=False
        if args[-2:]==['tasks','list']:return 'TASK PID STATUS\n'+('' if self.absent else 'a'*64+' 10 '+('PAUSED' if self.paused else 'RUNNING')+'\n')
        return ''


class Clock:
    def __init__(self):self.now=100.
    def ns(self):return int(self.now*1000000000)
    def mono(self):return self.now
    def sleep(self,t):self.now+=t


class SuspensionSafety(unittest.TestCase):
    def test_exact_pod_container_and_controller_are_bound(self):
        op=OwnerFixture();value=selected_task(op)
        self.assertEqual(value['container_id'],'a'*64);self.assertEqual(value['namespace_uid'],'namespace')
        self.assertFalse(any('pause' in x for x in op.calls))

    def test_foreign_controller_and_multiple_containers_refuse_before_mutation(self):
        for change in ('controller','container'):
            op=OwnerFixture()
            if change=='controller':op.pod['metadata']['ownerReferences'][0]['uid']='foreign'
            else:op.pod['spec']['containers'].append(dict(name='second'))
            with self.assertRaises(ContractError):selected_task(op)
            self.assertFalse(any('pause' in x for x in op.calls))

    def test_long_pause_keeps_original_deadline_and_resumes_same_id(self):
        op=OwnerFixture();clock=Clock();bound=selected_task(op);saved=[]
        result=suspend(op,bound,115000,end=200,save=lambda x:saved.append(copy.deepcopy(x)),clock=clock.ns,monotonic=clock.mono,sleep=clock.sleep)
        self.assertEqual(result['selected_deadline_ms'],115000);self.assertGreater(result['after_wait_ms'],115000)
        self.assertGreaterEqual(result['suspended_seconds'],20);self.assertTrue(result['original_resumed'])
        mutations=[x[-3:] for x in op.calls if 'pause' in x or 'resume' in x]
        self.assertEqual(mutations,[['tasks','pause','a'*64],['tasks','resume','a'*64]])

    def test_observer_failure_still_resumes_original_only(self):
        op=OwnerFixture();clock=Clock();bound=selected_task(op)
        def broken(_):raise RuntimeError('observer interrupted')
        with self.assertRaisesRegex(RuntimeError,'observer interrupted'):
            suspend(op,bound,115000,end=200,save=lambda _:None,clock=clock.ns,monotonic=clock.mono,sleep=broken)
        self.assertFalse(op.paused);self.assertEqual(op.calls[-1][-3:],['tasks','resume','a'*64])

    def test_replacement_is_never_pause_or_resume_target(self):
        op=OwnerFixture();clock=Clock();bound=selected_task(op);saved=[]
        def replaced(t):clock.sleep(t);op.absent=True
        with self.assertRaises(ContractError):
            suspend(op,bound,115000,end=200,save=lambda x:saved.append(copy.deepcopy(x)),clock=clock.ns,monotonic=clock.mono,sleep=replaced)
        self.assertFalse(any('resume' in x for x in op.calls));self.assertEqual(saved[-1]['cleanup_original_state'],'ABSENT')
        self.assertFalse(saved[-1]['replacement_targeted'])

    def test_insufficient_window_does_not_extend_pause_or_skip_cleanup(self):
        op=OwnerFixture();clock=Clock();bound=selected_task(op)
        with self.assertRaisesRegex(ContractError,'DEADLINE_EXCEEDED'):
            suspend(op,bound,115000,end=110,save=lambda _:None,clock=clock.ns,monotonic=clock.mono,sleep=clock.sleep)
        self.assertEqual(clock.now,100.);self.assertFalse(op.paused)

    def test_changed_target_refuses_before_pause(self):
        op=OwnerFixture();bound=selected_task(op);bound['pod_uid']='old'
        with self.assertRaisesRegex(ContractError,'CONFLICT'):
            suspend(op,bound,115000,end=200,save=lambda _:None)
        self.assertFalse(any('pause' in x for x in op.calls))

    def test_lost_cleanup_observer_still_attempts_only_original_resume(self):
        op=OwnerFixture();clock=Clock();bound=selected_task(op);saved=[]
        from examples.pilot_attention_suspension import task_state
        def state(owner,cid):
            if clock.now>100:raise RuntimeError('task observation unavailable')
            return task_state(owner,cid)
        with patch('examples.pilot_attention_suspension.task_state',side_effect=state):
            with self.assertRaisesRegex(RuntimeError,'task observation unavailable'):
                suspend(op,bound,115000,end=200,save=lambda x:saved.append(copy.deepcopy(x)),clock=clock.ns,monotonic=clock.mono,sleep=clock.sleep)
        self.assertFalse(op.paused);self.assertEqual(saved[-1]['cleanup_original_state'],'UNKNOWN')
        self.assertEqual(op.calls[-1][-3:],['tasks','resume','a'*64])

    def test_embedded_observers_compile_without_import_or_runtime_execution(self):
        compile(PORT,'typed-owner-client','exec');compile(DIAGNOSTIC,'owner-local-observer','exec')

    def test_plan_requires_completed_handover_and_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'replacement-native').mkdir()
            values=root/'values';values.write_text('{}');images=root/'images';images.write_text(json.dumps(dict(source_manifest_sha256='f'*64)))
            handover=root/'report.json';handover.write_text(json.dumps(dict(status='FAIL',writer_generation=1)))
            with self.assertRaises(ContractError):freeze_plan(handover,values,images,root)
            memory=dict(memory=dict(target=dict(payload={'scope_ref':'synthetic','digest':'a'*64})),snapshot=dict(corpus='synthetic'))
            handover.write_text(json.dumps(dict(status='PASS',writer_generation=2,replacement='omega-ref-pilot-fixture-next',steps=[dict(step='new-memory',value=json.dumps(memory))])))
            native=root/'replacement-native/report.json';native.write_text(json.dumps(dict(inputs=[dict(session='fresh',observed=dict(state='complete'))]*4)))
            plan=freeze_plan(handover,values,images,root)
            self.assertEqual(plan['maximum_seconds'],300);self.assertEqual(plan['maximum_new_omega_inputs'],0)
            self.assertEqual(plan['payload'],memory['memory']['target']['payload']);self.assertFalse(plan['old_plan_changed'])
            self.assertNotIn('deadline',plan);self.assertEqual(plan['operation_deadline_ms'],15000)

if __name__=='__main__':unittest.main()
