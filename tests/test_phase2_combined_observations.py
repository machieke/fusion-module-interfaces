"""Read-only SQLite observer tests; all native/model captures are authored.

No provider, native runtime, cluster or generation runs. These fixtures test
correlation and refusal, not the tool semantics represented by captured rows.
"""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid

from examples import preview_combined_observations as q
from fusion.contracts import ContractError, canonical, digest


class CombinedObservations(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='combined-observer-fixture-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.scope = 'synthetic-combined-observer'
        self.sid = str(uuid.uuid4())
        self.uid = str(uuid.uuid4())
        self.source_root = self.root/'sources'
        self.source_root.mkdir()
        path = self.source_root/'fusion'/'fixture.py'
        path.parent.mkdir(); path.write_text('EXPLICIT SOURCE FIXTURE\n')
        self.hashes = {'fusion/fixture.py':digest(path.read_bytes())}
        self.payload = dict(scope=self.scope, corpus='fixture-corpus', uuid=self.uid,
            time='2026-11-02 00:00:00', content='Actual authored capture, never an evaluator-supplied body')
        self.ref = dict(scope_ref=self.scope,id='payload-fixture',revision=1,digest=digest(canonical(self.payload)))
        self.relation = dict(handle='oh1:relation:'+str(uuid.uuid4()), target=dict(scope_ref=self.scope,id='relation',revision=1,digest='a'*64))
        self.memory = dict(handle='oh1:memory:'+str(uuid.uuid4()), target=dict(payload=self.ref))
        self.pin = dict(profile='working-task-context/1', revision=1, items={'evidence':'Unverified authored note'}, interpretation='unverified-task-notes')
        self.pin['digest'] = digest(canonical(self.pin['items']))
        self.selected = dict(session=self.sid,scope=self.scope,memory_handle=self.memory['handle'],relation_handle=self.relation['handle'],selected={})
        folder = self.root/'sessions'/self.sid
        folder.mkdir(parents=True)
        self.db_path = folder/'caller.sqlite'
        with sqlite3.connect(self.db_path) as db:
            db.executescript('''
                CREATE TABLE preview_native_inputs(turn INTEGER,identity TEXT,source TEXT,acknowledged INTEGER);
                CREATE TABLE app_turns(id INTEGER,projection TEXT);
                CREATE TABLE app_occurrences(turn INTEGER,id TEXT,position INTEGER,premises TEXT,deadline INTEGER,result TEXT,done INTEGER);
                CREATE TABLE app_memory_writes(id TEXT,uuid TEXT,intent TEXT,receipts TEXT);
                CREATE TABLE app_query_views(id TEXT,view TEXT);
                CREATE TABLE app_read_views(id TEXT,value TEXT);
                CREATE TABLE app_memory_reads(id TEXT,queries INTEGER,payloads TEXT,candidates TEXT);
                CREATE TABLE app_priority_queries(id TEXT,result TEXT);
                CREATE TABLE app_model_calls(slot INTEGER,id TEXT,intent TEXT,result TEXT,admission TEXT);
                CREATE TABLE app_priority_contexts(slot INTEGER,result TEXT,payloads TEXT,rendered TEXT,deadline INTEGER);
                CREATE TABLE preview_context_captures(turn INTEGER,view TEXT);
                CREATE TABLE preview_task_outbox(id TEXT,record TEXT,ref TEXT,receipt TEXT);
                CREATE TABLE preview_history_outbox(ordinal INTEGER,identity TEXT,intent TEXT,receipt TEXT);
                CREATE TABLE unrelated_secrets(value TEXT);
            ''')
            db.execute('INSERT INTO unrelated_secrets VALUES(?)',('DO-NOT-PUBLISH-PRIVATE-SENTINEL',))
            labels = ('remember','before','after','pin','next_context','unlink','post_unlink')
            for turn,label in enumerate(labels,1):
                identity = 'input-'+label
                result = canonical(dict(memory=self.memory)).decode() if label=='remember' else canonical(self.pin).decode() if label=='pin' else canonical(dict(status='STRUCTURALLY_RETRACTED',relation=self.relation,receipt=dict(evidence_changed=False,payload_erased=False))).decode() if label=='unlink' else 'native captured '+label
                projection = 'native-projection '+result
                source = dict(session=self.sid,occurrence='source-'+label,deadline=121000,accepted=1000)
                db.execute('INSERT INTO preview_native_inputs VALUES(?,?,?,1)',(turn,identity,canonical(source).decode()))
                db.execute('INSERT INTO app_turns VALUES(?,?)',(turn,projection))
                db.execute('INSERT INTO app_occurrences VALUES(?,?,0,?,31000,?,1)',(turn,label,canonical(dict(operation=label)).decode(),result))
                self.selected['selected'][label] = dict(identity=identity,turn=turn,projection_sha256=digest(projection.encode()),deadline=121000,accepted=1000)
            db.execute('INSERT INTO app_memory_writes VALUES(?,?,?,?)',('remember',self.uid,canonical(self.payload).decode(),canonical(dict(payload=dict(ref=self.ref))).decode()))
            for label in ('before','after','post_unlink'):
                links = [] if label=='post_unlink' else [dict(relation=self.relation)]
                value = dict(snapshot=dict(head=dict(scope_ref=self.scope,sequence=1),generation='fixture-'+label),
                    handles={self.uid:dict(envelope=self.memory,structure=dict(links=links))},
                    metadata=dict(records=[dict(uuid=self.uid,stv=[.75,.6])]),
                    beliefs=[dict(uuid=self.uid,revision=3,snapshot_digest='b'*64,sources=[{'fixture':'retained actual source'}])])
                raw = canonical(value).decode(); key = digest(raw.encode())
                db.execute('INSERT INTO app_read_views VALUES(?,?)',(key,raw))
                db.execute('INSERT INTO app_query_views VALUES(?,?)',(label,key))
                hydrated = [[self.uid,self.payload['time'],self.payload['content'],0.125]]
                db.execute('INSERT INTO app_memory_reads VALUES(?,1,?,?)',(label,canonical(hydrated).decode(),canonical(dict(hits=[dict(uuid=self.uid,ref=self.ref,distance=0.125)])).decode()))
                if label!='post_unlink':
                    db.execute('INSERT INTO app_priority_queries VALUES(?,?)',(label,canonical(dict(scores=[dict(target=self.uid,score=0. if label=='before' else 1.)],binding={'fixture':label})).decode()))
            for label in ('after','next_context'):
                turn = self.selected['selected'][label]['turn']
                promoted = 'Native rendered '+self.payload['content']
                task = self.pin if label=='next_context' else dict(items={})
                prompt = 'PRIVATE-PROMPT-SCAFFOLD MOST_PROMOTED_MEMORIES: '+canonical(promoted).decode()+' CONTEXT_ALLOCATION: '+canonical(dict(omitted=[],bound_unit='utf8-bytes',maximum_bytes=28000)).decode()+' UNVERIFIED_TASK_CONTEXT_JSON: '+canonical(task).decode()
                prompt = prompt.replace('"','_quote_').replace('\n','_newline_').replace("'",'_apostrophe_')+':-:-:-:[synthetic user envelope]'
                model = dict(session=self.sid,deadline_ms=121000,source_id='source-'+label,native_prompt=prompt)
                db.execute('INSERT INTO app_model_calls VALUES(?,?,?,?,?)',(turn,'model-'+label,canonical(model).decode(),'captured-response-fixture','admission-fixture'))
                db.execute('INSERT INTO app_priority_contexts VALUES(?,?,?,?,121000)',(turn,canonical(dict(selected=[self.uid])).decode(),canonical([[self.uid,self.payload['time'],self.payload['content']]]).decode(),promoted))
                db.execute('INSERT INTO preview_context_captures VALUES(?,?)',(turn,canonical(task).decode()))

    def observe(self):
        return q.owned_observation(self.root,self.selected,self.source_root,self.hashes)

    def mutate(self,sql,args=()):
        with sqlite3.connect(self.db_path) as db:
            db.execute(sql,args)

    def test_actual_sqlite_capture_correlation_and_sanitized_output_no_mutation(self):
        before = self.db_path.read_bytes()
        observed = self.observe()
        self.assertTrue(q.verify(observed,self.selected)['actual_native_promoted_context'])
        self.assertEqual(observed['contexts']['next_context']['task'],self.pin)
        wire = canonical(observed).decode()
        for secret in ('DO-NOT-PUBLISH-PRIVATE-SENTINEL','PRIVATE-PROMPT-SCAFFOLD',self.payload['content']):
            self.assertNotIn(secret,wire)
        self.assertEqual(before,self.db_path.read_bytes())

    def test_changed_actual_prompt_or_missing_target_hydration_is_not_repaired(self):
        with sqlite3.connect(self.db_path) as db:
            raw = db.execute('SELECT intent FROM app_model_calls WHERE id=?',('model-after',)).fetchone()[0]
        changed = json.loads(raw); changed['native_prompt'] = changed['native_prompt'].replace('Native rendered','Evaluator replacement')
        self.mutate('UPDATE app_model_calls SET intent=? WHERE id=?',(canonical(changed).decode(),'model-after'))
        with self.assertRaises(AssertionError):self.observe()
        self.mutate('UPDATE app_model_calls SET intent=? WHERE id=?',(raw,'model-after'))
        self.mutate('UPDATE app_memory_reads SET payloads=? WHERE id=?',('[]','post_unlink'))
        with self.assertRaises(AssertionError):self.observe()

    def test_source_drift_and_changed_original_receipt_refuse(self):
        (self.source_root/'fusion'/'fixture.py').write_text('changed source')
        with self.assertRaises(AssertionError):self.observe()
        (self.source_root/'fusion'/'fixture.py').write_text('EXPLICIT SOURCE FIXTURE\n')
        self.selected['selected']['after']['deadline'] += 1
        with self.assertRaises(AssertionError):self.observe()

    def test_query_capture_distance_matches_candidate_and_exact_four_column_bytes(self):
        observed = self.observe()
        self.assertEqual(observed['query_views']['after']['captured_distance'],0.125)
        self.assertTrue(observed['query_views']['after']['exact_four_column_candidate_binding'])
        original = [self.uid,self.payload['time'],self.payload['content'],0.125]
        for changed in (original[:3], original+[0], original[:3]+[0.5]):
            with self.subTest(payload=changed):
                self.mutate('UPDATE app_memory_reads SET payloads=? WHERE id=?',(canonical([changed]).decode(),'after'))
                with self.assertRaises(AssertionError):self.observe()
        self.mutate('UPDATE app_memory_reads SET payloads=? WHERE id=?',(canonical([original]).decode(),'after'))
        candidates = dict(hits=[dict(uuid=self.uid,ref=self.ref,distance=0.5)])
        self.mutate('UPDATE app_memory_reads SET candidates=? WHERE id=?',(canonical(candidates).decode(),'after'))
        with self.assertRaises(AssertionError):self.observe()

    def test_retained_link_or_changed_c2_cannot_be_reported_as_safe_unlink(self):
        observed = self.observe()
        original = copy.deepcopy(observed)
        observed['query_views']['post_unlink']['structure'] = observed['query_views']['before']['structure']
        with self.assertRaises(ContractError):q.verify(observed,self.selected)
        observed = original
        observed['query_views']['post_unlink']['belief']['revision'] += 1
        with self.assertRaises(ContractError):q.verify(observed,self.selected)

    def test_zero_priority_effect_and_wrong_pin_capture_fail(self):
        observed = self.observe()
        observed['priority_queries']['after']['score'] = 0.
        with self.assertRaises(ContractError):q.verify(observed,self.selected)
        self.mutate('UPDATE preview_context_captures SET view=? WHERE turn=?',('{}',self.selected['selected']['next_context']['turn']))
        with self.assertRaises(AssertionError):self.observe()

    def test_native_tokens_in_note_data_are_forward_compared_without_inverse_decoding(self):
        self.pin['items']['evidence'] = 'Literal _quote_ and "quote", _apostrophe_ and apostrophe\', _newline_ and newline\n'
        self.pin['digest'] = digest(canonical(self.pin['items']))
        turn = self.selected['selected']['next_context']['turn']
        raw = canonical(self.pin).decode()
        self.mutate('UPDATE preview_context_captures SET view=? WHERE turn=?',(raw,turn))
        self.mutate('UPDATE app_occurrences SET result=? WHERE id=?',(raw,'pin'))
        projection = 'native-projection '+raw
        self.mutate('UPDATE app_turns SET projection=? WHERE id=?',(projection,self.selected['selected']['pin']['turn']))
        self.selected['selected']['pin']['projection_sha256'] = digest(projection.encode())
        with sqlite3.connect(self.db_path) as db:
            intent = json.loads(db.execute('SELECT intent FROM app_model_calls WHERE slot=?',(turn,)).fetchone()[0])
        prefix = intent['native_prompt'].split(' UNVERIFIED_TASK_CONTEXT_JSON: ',1)[0]
        encoded = raw.replace('"','_quote_').replace('\n','_newline_').replace("'",'_apostrophe_')
        intent['native_prompt'] = prefix+' UNVERIFIED_TASK_CONTEXT_JSON: '+encoded+':-:-:-:[synthetic user envelope]'
        self.mutate('UPDATE app_model_calls SET intent=? WHERE slot=?',(canonical(intent).decode(),turn))
        observed = self.observe()
        self.assertEqual(observed['contexts']['next_context']['task'],self.pin)
        self.assertTrue(q.verify(observed,self.selected)['actual_native_pin_context'])
        intent['native_prompt'] = intent['native_prompt'].replace(' UNVERIFIED_TASK_CONTEXT_JSON: ',' UNVERIFIED_TASK_CONTEXT_JSON:  ',1)
        self.mutate('UPDATE app_model_calls SET intent=? WHERE slot=?',(canonical(intent).decode(),turn))
        with self.assertRaises(AssertionError):self.observe()

    def external(self):
        task = dict(id='task-fixture',kind='task',scope=self.scope,sender='A',recipient='B',deadline=120000)
        ref = dict(scope_ref=self.scope,id='task-payload',revision=1,digest='c'*64)
        receipt = {'delivery_id':'authored-mailbox-receipt'}
        source = dict(accepted=1000,occurrence='delegate-source',deadline=121000)
        evidence = dict(occurrence_id='history-occurrence',episode=dict(scope_ref=self.scope,id='episode'),event_ref=dict(scope_ref=self.scope,id='event'))
        previous = dict(scope_ref=self.scope,id='previous-event')
        body = dict(observed_ms=1000,source_id='delegate-source',effect='durable-task-mailbox-acceptance',task=task['id'],kind='task',sender='A',recipient='B',payload=ref,acceptance=receipt,recipient_consumption='NOT_OBSERVED',independent_corroboration=False)
        with sqlite3.connect(self.db_path) as db:
            db.execute('INSERT INTO app_occurrences VALUES(9,?,0,?,120000,?,1)',('delegate',canonical(dict(operation='delegate')).decode(),'native tool-result alone does not prove publication'))
            db.execute('INSERT INTO preview_native_inputs VALUES(9,?,?,1)',('delegate-input',canonical(source).decode()))
            db.execute('INSERT INTO preview_task_outbox VALUES(?,?,?,?)',('task/delegate',canonical(task).decode(),canonical(ref).decode(),canonical(receipt).decode()))
            db.execute('INSERT INTO preview_history_outbox VALUES(1,?,?,?)',('tool-result','{}',canonical(dict(evidence=dict(event_ref=previous))).decode()))
            db.execute('INSERT INTO preview_history_outbox VALUES(2,?,?,?)',('task/delegate/external-effect',canonical(dict(kind='external-effect',body=body,deadline=120000)).decode(),canonical(dict(evidence=evidence,delivery_id=None)).decode()))
        directory = self.root/'preview-facets'; directory.mkdir()
        self.c1 = directory/'session-history.sqlite'
        record = dict(evidence=evidence,event=dict(numerical=None,provenance=[],causation=[previous]),lineage_roots=[])
        with sqlite3.connect(self.c1) as db:
            db.execute('CREATE TABLE events(scope TEXT,occurrence TEXT,record TEXT,receipt TEXT)')
            db.execute('INSERT INTO events VALUES(?,?,?,?)',(self.scope,evidence['occurrence_id'],canonical(record).decode(),canonical(dict(evidence=evidence,delivery_id=None)).decode()))

    def test_external_effect_matches_publication_and_c1_has_no_evidence_roots(self):
        self.external()
        observed = q.owned_effects(self.root,self.sid,self.scope)
        self.assertEqual(observed['missing'],[])
        self.assertEqual(len(observed['effects']),1)
        c1 = q.owned_history(self.root,observed['effects'])
        self.assertTrue(c1[0]['no_lineage_roots'])
        self.assertEqual(observed['effects'][0]['original_deadline'],120000)
        self.assertEqual(observed['effects'][0]['recipient_consumption'],'NOT_OBSERVED')

    def test_external_effect_malformed_receipt_duplicate_event_and_false_empirical_root_refuse(self):
        self.external()
        observed = q.owned_effects(self.root,self.sid,self.scope)
        with sqlite3.connect(self.c1) as db:
            raw = db.execute('SELECT record FROM events').fetchone()[0]
            record = json.loads(raw); record['lineage_roots'] = ['invented-root']
            db.execute('UPDATE events SET record=?',(canonical(record).decode(),))
        with self.assertRaises(AssertionError):q.owned_history(self.root,observed['effects'])
        self.mutate('UPDATE preview_task_outbox SET receipt=?',('{"replacement":"wrong"}',))
        with self.assertRaises(AssertionError):q.owned_effects(self.root,self.sid,self.scope)
        self.mutate('UPDATE preview_task_outbox SET receipt=?',('{"delivery_id":"authored-mailbox-receipt"}',))
        self.mutate('INSERT INTO preview_history_outbox SELECT * FROM preview_history_outbox WHERE ordinal=2')
        with self.assertRaises(AssertionError):q.owned_effects(self.root,self.sid,self.scope)

    def test_historical_missing_effect_is_explicit_never_fabricated(self):
        self.external()
        self.mutate('DELETE FROM preview_history_outbox WHERE ordinal=2')
        value = q.owned_effects(self.root,self.sid,self.scope)
        self.assertEqual(value['effects'],[])
        self.assertEqual(value['missing'],['task/delegate/external-effect'])

    def test_image_or_source_binding_refusal_precedes_any_journal_observer(self):
        package = dict(kind='caller', source={name:'a'*64 for name in q.SOURCE_FILES})
        images = dict(source_export_verification='PASS',source_manifest_sha256=digest(canonical(package['source'])),
            images=[dict(kind='caller',repository='fixture/caller',manifest_digest='sha256:'+'b'*64,configuration_digest='sha256:'+'c'*64)])
        operator = Mock(namespace='omega-ref-fixture')
        with patch.object(q,'selection',return_value=self.selected):
            changed = copy.deepcopy(images); changed['source_manifest_sha256'] = 'd'*64
            with self.assertRaises(ContractError):q.execute(operator,{},changed,package)
            operator.owned.assert_not_called(); operator.k.assert_not_called()
            operator.k.return_value = json.dumps(dict(status=dict(containerStatuses=[dict(imageID='sha256:'+'e'*64)])))
            with self.assertRaises(ContractError):q.execute(operator,{},images,package)
        self.assertEqual(operator.k.call_count,1)
        self.assertEqual(operator.k.call_args.args[:2],('get','pod'))


if __name__ == '__main__':
    unittest.main()
