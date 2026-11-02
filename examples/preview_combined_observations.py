"""Read-only checks of already captured native combined-workflow observations.

This operator reads the selected application's own journal inside its own pod.
It submits no inputs, invokes no providers, changes no state and emits no full
prompt, credential or journal. Expected payloads come from actual accepted
native writes; expected notes come from actual committed native pin results.
"""
import argparse
import inspect
import json
from pathlib import Path
import re

from fusion.contracts import canonical, digest, require
from integration.single_node.reference_ops import Operator, PYTHON


SOURCE_FILES = (
    'fusion/preview_application.py', 'fusion/preview_model.py',
    'fusion/preview_native_memory.py', 'fusion/preview_native_relations.py',
    'fusion/preview_native_cognition.py', 'fusion/neoclaw_model.py',
    'fusion/neoclaw_priority.py', 'fusion/neoclaw_memory.py',
    'fusion/preview_native_history.py', 'fusion/preview_history.py',
    'integration/neoclaw/promotion_startup.py', 'integration/neoclaw/preview_startup.py',
    'integration/neoclaw/sources.json',
)


def selection(native, namespace):
    require(native.get('status') == 'PASS' and native.get('mode') == 'combined'
            and native['namespace'] == namespace and native['additional_live_generations'] == 0, 'CONFLICT')
    inventory = native['omega-agent']
    require(inventory['principal'] == 'A' and inventory['scope'].startswith('synthetic-')
            and inventory['model_boundary'] == 'RECORDED_FIXTURE', 'UNAUTHORIZED')
    session = list(inventory['sessions'])[0]
    rows = [x for x in native['inputs'] if x['role'] == 'omega-agent' and x['session'] == session]
    require(1 <= len(rows) <= 32 and all(x['observed']['state'] == 'complete' for x in rows), 'NOT_AVAILABLE')
    memory = native['returned_handles']['memory']
    relation = native['returned_handles']['relation']
    promote = next(i for i, x in enumerate(rows) if x['command'] == 'promote '+memory)
    before = next(x for x in reversed(rows[:promote]) if x['command'].startswith('query '))
    after = next(x for x in rows[promote+1:] if x['command'].startswith('query '))
    pin = next(i for i, x in enumerate(rows) if x['command'].startswith('pin '))
    unlink = next(i for i, x in enumerate(rows) if x['command'] == 'unlink '+relation)
    post = next(x for x in rows[unlink+1:] if x['command'].startswith('query '))
    chosen = dict(remember=next(x for x in rows if x['command'].startswith('remember ')),
        before=before, after=after, pin=rows[pin], next_context=rows[pin+1],
        unlink=rows[unlink], post_unlink=post)
    require(before['observed']['result']['turn'] < after['observed']['result']['turn']
            < chosen['pin']['observed']['result']['turn'] < chosen['unlink']['observed']['result']['turn']
            < post['observed']['result']['turn'], 'CONFLICT')
    return dict(scope=inventory['scope'], session=session, memory_handle=memory, relation_handle=relation,
        selected={key:dict(identity=x['identity'], turn=x['observed']['result']['turn'],
            projection_sha256=digest(x['observed']['result']['projection'].encode()),
            deadline=x['accepted']['deadline'], accepted=x['accepted']['accepted']) for key, x in chosen.items()})


def owned_observation(directory, selected, source_root, source_hashes, configuration=None):
    """Standard-library-only observer; safe to transmit to the owning image."""
    import hashlib
    import json
    import math
    from pathlib import Path
    import sqlite3
    import uuid

    def wire(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()

    def sha(value):
        return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()

    def native_safe(value):
        # preview_render_context escapes its delimiter, then native getContext
        # applies pinned utils.metta:string-safe. Compare forwards: reversing
        # tokens would confuse literal user data with transformed punctuation.
        return value.replace(':-:-:-:', '\\u003a-\\u003a-\\u003a-\\u003a').replace('"','_quote_').replace('\n','_newline_').replace("'",'_apostrophe_')

    def one(db, sql, args=()):
        rows = list(db.execute(sql, args))
        assert len(rows) == 1
        return rows[0]

    assert str(uuid.UUID(selected['session'])) == selected['session']
    assert selected['scope'].startswith('synthetic-')
    if configuration is not None:
        cfg = json.loads(Path(configuration).read_text())
        p = cfg['preview']
        assert cfg['role'] == 'omega-agent' and p['scope'] == selected['scope']
        assert p['model_boundary'] == 'RECORDED_FIXTURE'
        assert selected['session'] in p['agents']['omega-agent']['sessions']
    checked_sources = {}
    for relative, expected in source_hashes.items():
        path = Path(relative)
        assert not path.is_absolute() and '..' not in path.parts and path.parts[0] in ('fusion','integration')
        actual = sha((Path(source_root)/path).read_bytes())
        assert actual == expected
        checked_sources[relative] = actual
    normalization = dict(name='native-string-safe-after-preview-delimiter-escape', source_boundary='EXPLICIT_FIXTURE')
    if configuration is not None:
        pinned = json.loads((Path(source_root)/'integration/neoclaw/sources.json').read_text())['sources']['mettaclaw']
        actual = sha(Path('/opt/native/sources/mettaclaw/src/utils.metta').read_bytes())
        assert actual == pinned['files']['src/utils.metta']
        normalization.update(source_boundary='PINNED_NATIVE_SOURCE', source_sha256=actual, commit=pinned['commit'])
    path = Path(directory)/'sessions'/selected['session']/'caller.sqlite'
    assert path.is_file()
    result = dict(session=selected['session'], scope=selected['scope'], source_hashes=checked_sources,
        normalization=normalization, inputs={}, query_views={}, priority_queries={}, contexts={})
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.5) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        selected_rows = {}
        for label, bound in selected['selected'].items():
            native = one(db, 'SELECT i.*,t.projection FROM preview_native_inputs i JOIN app_turns t ON t.id=i.turn WHERE i.identity=?', (bound['identity'],))
            source = json.loads(native['source'])
            assert native['turn'] == bound['turn'] and native['acknowledged'] == 1
            assert source['session'] == selected['session'] and source['deadline'] == bound['deadline'] and source['accepted'] == bound['accepted']
            assert sha(native['projection']) == bound['projection_sha256']
            row = one(db, 'SELECT * FROM app_occurrences WHERE turn=?', (native['turn'],))
            assert row['done'] == 1 and row['result'] is not None and row['deadline'] <= source['deadline']
            selected_rows[label] = row
            result['inputs'][label] = dict(identity=bound['identity'], turn=row['turn'], occurrence=row['id'],
                source_occurrence=source['occurrence'],
                deadline=source['deadline'], tool_deadline=row['deadline'], projection_sha256=sha(native['projection']),
                result_sha256=sha(row['result']), acknowledged=True)
        remembered = selected_rows['remember']
        written = one(db, 'SELECT * FROM app_memory_writes WHERE id=?', (remembered['id'],))
        intent = json.loads(written['intent'])
        payload = {key:intent[key] for key in ('scope','corpus','uuid','time','content')}
        receipts = json.loads(written['receipts'])
        ref = receipts['payload']['ref']
        assert payload['scope'] == selected['scope'] and ref['scope_ref'] == selected['scope'] and sha(wire(payload)) == ref['digest']
        remembered_result = json.loads(remembered['result'])
        assert remembered_result['memory']['handle'] == selected['memory_handle']
        assert remembered_result['memory']['target']['payload'] == ref
        uid = written['uuid']
        assert uid == payload['uuid']
        result['memory'] = dict(uuid=uid, ref=ref, content_sha256=sha(payload['content']), payload_sha256=sha(wire(payload)))
        for label in ('before','after','post_unlink'):
            occurrence = selected_rows[label]
            view = one(db, 'SELECT q.view,v.value FROM app_query_views q JOIN app_read_views v ON v.id=q.view WHERE q.id=?', (occurrence['id'],))
            assert sha(view['value']) == view['view']
            value = json.loads(view['value'])
            handle = value['handles'][uid]
            assert handle['envelope']['handle'] == selected['memory_handle'] and handle['envelope']['target']['payload'] == ref
            assert value['snapshot']['head']['scope_ref'] == selected['scope']
            metadata = [item for item in value['metadata']['records'] if item['uuid'] == uid]
            beliefs = [item for item in value['beliefs'] if item['uuid'] == uid]
            assert len(metadata) == len(beliefs) == 1
            read = one(db, 'SELECT * FROM app_memory_reads WHERE id=?', (occurrence['id'],))
            assert read['queries'] == 1 and read['payloads'] is not None
            hydrated = [item for item in json.loads(read['payloads']) if item[0] == uid]
            candidates = json.loads(read['candidates'])
            hits = [item for item in candidates['hits'] if item['uuid'] == uid]
            assert len(hits) == 1 and hits[0]['ref'] == ref
            distance = hits[0]['distance']
            assert type(distance) in (int,float) and math.isfinite(distance) and distance >= 0
            # MemoryRead.retrieve captures four columns; the separate native
            # promoted-context capture below intentionally has only three.
            assert wire(hydrated) == wire([[uid,payload['time'],payload['content'],distance]])
            result['query_views'][label] = dict(view_id=view['view'], view_sha256=sha(view['value']),
                snapshot=value['snapshot'], structure=handle['structure'], stv=metadata[0]['stv'],
                belief=beliefs[0], payloads_sha256=sha(read['payloads']), queries=read['queries'], target_hydrated=True,
                captured_target_sha256=sha(wire(hydrated[0])), captured_distance=distance,
                exact_four_column_candidate_binding=True)
            if label != 'post_unlink':
                priority = one(db, 'SELECT result FROM app_priority_queries WHERE id=?', (occurrence['id'],))
                scores = json.loads(priority['result'])
                score = [item for item in scores['scores'] if item['target'] == uid]
                assert len(score) == 1
                result['priority_queries'][label] = dict(score=score[0]['score'], result_sha256=sha(priority['result']), binding=scores['binding'])
        for label in ('after','next_context'):
            turn = selected_rows[label]['turn']
            model = one(db, 'SELECT * FROM app_model_calls WHERE slot=?', (turn,))
            intent = json.loads(model['intent'])
            assert intent['session'] == selected['session'] and intent['deadline_ms'] == result['inputs'][label]['deadline']
            assert intent['source_id'] == result['inputs'][label]['source_occurrence']
            assert model['result'] is not None and model['admission'] is not None
            prompt = intent['native_prompt']
            def section(marker, following):
                assert prompt.count(marker) == prompt.count(following) == 1
                return prompt.split(marker,1)[1].split(following,1)[0]
            promoted_wire = section(' MOST_PROMOTED_MEMORIES: ', ' CONTEXT_ALLOCATION: ')
            task_wire = section(' UNVERIFIED_TASK_CONTEXT_JSON: ', ':-:-:-:')
            allocation_wire = section(' CONTEXT_ALLOCATION: ', ' UNVERIFIED_TASK_CONTEXT_JSON: ')
            # Only the closed allocator metadata is decoded. Neither note nor
            # memory content is reconstructed by replacing native data tokens.
            allocation = json.loads(allocation_wire.replace('_quote_', '"'))
            assert set(allocation) == {'bound_unit','maximum_bytes','omitted'} and allocation['bound_unit'] == 'utf8-bytes' and allocation['maximum_bytes'] == 28000
            assert type(allocation['omitted']) is list and set(allocation['omitted']) <= {'history','promoted'}
            priority = one(db, 'SELECT * FROM app_priority_contexts WHERE slot=?', (turn,))
            ranks, hydrated = json.loads(priority['result']), json.loads(priority['payloads'])
            matches = [item for item in hydrated if item[0] == uid]
            assert len(matches) == 1 and matches[0] == [uid,payload['time'],payload['content']]
            assert uid in ranks['selected'] and priority['rendered'] is not None
            promoted = priority['rendered']
            assert promoted_wire == native_safe(wire(promoted).decode()) and payload['content'] in promoted
            assert priority['deadline'] == intent['deadline_ms']
            context = one(db, 'SELECT view FROM preview_context_captures WHERE turn=?', (turn,))
            task = json.loads(context['view'])
            assert task_wire == native_safe(context['view']) and 'promoted' not in allocation['omitted']
            result['contexts'][label] = dict(turn=turn, model_occurrence=model['id'], prompt_sha256=sha(prompt),
                model_result_sha256=sha(model['result']), admission_sha256=sha(model['admission']),
                promoted_sha256=sha(promoted), selected=ranks['selected'], ranking_sha256=sha(priority['result']),
                encoded_promoted_sha256=sha(promoted_wire), encoded_task_sha256=sha(task_wire),
                hydrated_payload_sha256=sha(wire(matches[0])), content_sha256=sha(matches[0][2]),
                task=task, task_capture_sha256=sha(context['view']), allocation=allocation,
                actual_promoted_context_bound=True, actual_task_context_bound=True)
        pin = json.loads(selected_rows['pin']['result'])
        assert result['contexts']['next_context']['task'] == pin
        result['pin'] = dict(result_sha256=sha(selected_rows['pin']['result']), view=pin)
        removed = json.loads(selected_rows['unlink']['result'])
        assert removed['relation']['handle'] == selected['relation_handle']
        assert removed['status'] == 'STRUCTURALLY_RETRACTED' and removed['receipt']['evidence_changed'] is False and removed['receipt']['payload_erased'] is False
        result['unlink'] = dict(relation=removed['relation'], receipt=removed['receipt'], result_sha256=sha(selected_rows['unlink']['result']))
        # Reread every old selected view within this read-only snapshot. No
        # replacement projection or rewritten result is manufactured here.
        for view in result['query_views'].values():
            raw = one(db, 'SELECT value FROM app_read_views WHERE id=?', (view['view_id'],))[0]
            assert sha(raw) == view['view_sha256']
    return result


def owned_effects(directory, session, scope):
    """Observe publication and C1 delivery receipts from this agent only."""
    import hashlib
    import json
    from pathlib import Path
    import sqlite3
    import uuid
    assert str(uuid.UUID(session)) == session and scope.startswith('synthetic-')
    path = Path(directory)/'sessions'/session/'caller.sqlite'
    effects, missing = [], []
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.5) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
        rows = list(db.execute('SELECT * FROM app_occurrences ORDER BY turn,position LIMIT 161'))
        assert len(rows) <= 160
        for row in rows:
            intent = json.loads(row['premises'])
            if intent.get('operation') != 'delegate':
                continue
            assert row['done'] == 1
            publication = db.execute('SELECT * FROM preview_task_outbox WHERE id=?', ('task/'+row['id'],)).fetchone()
            assert publication is not None
            task, ref, receipt = (json.loads(publication[key]) for key in ('record','ref','receipt'))
            assert task['scope'] == scope and ref['scope_ref'] == scope
            source = json.loads(db.execute('SELECT source FROM preview_native_inputs WHERE turn=?', (row['turn'],)).fetchone()[0])
            identity = publication['id']+'/external-effect'
            found = list(db.execute('SELECT * FROM preview_history_outbox WHERE identity=?', (identity,)))
            if not found:
                missing.append(identity); continue
            assert len(found) == 1 and found[0]['receipt'] is not None
            event = json.loads(found[0]['intent'])
            expected = dict(observed_ms=source['accepted'], source_id=source['occurrence'],
                effect='durable-task-mailbox-acceptance', task=task['id'], kind=task['kind'],
                sender=task['sender'], recipient=task['recipient'], payload=ref,
                acceptance=receipt, recipient_consumption='NOT_OBSERVED', independent_corroboration=False)
            assert event == dict(kind='external-effect', body=expected, deadline=task['deadline'])
            previous = db.execute('SELECT receipt FROM preview_history_outbox WHERE ordinal=?', (found[0]['ordinal']-1,)).fetchone()
            assert previous is not None
            c1 = json.loads(found[0]['receipt'])
            assert c1['delivery_id'] is None
            effects.append(dict(session=session, identity=identity, task=task['id'], scope=scope,
                evidence=c1['evidence'], previous_event=json.loads(previous[0])['evidence']['event_ref'],
                original_deadline=event['deadline'], original_observed_ms=expected['observed_ms'],
                publication_receipt_sha256=hashlib.sha256(publication['receipt'].encode()).hexdigest(),
                history_intent_sha256=hashlib.sha256(found[0]['intent'].encode()).hexdigest(),
                exact_mailbox_acceptance=True, recipient_consumption='NOT_OBSERVED', independent_corroboration=False))
    return dict(session=session, effects=effects, missing=missing)


def owned_history(directory, effects):
    """Observe nonnumerical C1 records in the C1 owner's own pod only."""
    import hashlib
    import json
    from pathlib import Path
    import sqlite3
    path = Path(directory)/'preview-facets'/'session-history.sqlite'
    results = []
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.5) as db:
        db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
        for selected in effects:
            ref = selected['evidence']
            row = db.execute('SELECT record,receipt FROM events WHERE scope=? AND occurrence=?',
                (selected['scope'],ref['occurrence_id'])).fetchone()
            assert row is not None
            record, receipt = json.loads(row[0]), json.loads(row[1])
            assert record['evidence'] == ref and receipt['evidence'] == ref and receipt['delivery_id'] is None
            event = record['event']
            assert event['numerical'] is None and event['provenance'] == [] and record['lineage_roots'] == []
            assert event['causation'] == [selected['previous_event']]
            results.append(dict(identity=selected['identity'], record_sha256=hashlib.sha256(row[0].encode()).hexdigest(),
                no_numerical_assessment=True, no_provenance=True, no_lineage_roots=True, exact_causal_predecessor=True))
    return results


def verify(observed, selected):
    require(observed['session'] == selected['session'] and observed['scope'] == selected['scope'], 'CONFLICT')
    before, after, post = (observed['query_views'][key] for key in ('before','after','post_unlink'))
    relation = observed['unlink']['relation']['target']
    handle = selected['relation_handle']
    def includes(view):
        return any(item['relation']['handle'] == handle and item['relation']['target'] == relation for item in view['structure']['links'])
    require(includes(before) and includes(after) and not includes(post), 'CONFLICT')
    require(before['stv'] == after['stv'] == post['stv'] and before['belief'] == after['belief'] == post['belief'], 'CONFLICT')
    require(observed['priority_queries']['after']['score'] > observed['priority_queries']['before']['score'], 'CONFLICT')
    require(observed['contexts']['next_context']['task'] == observed['pin']['view'], 'CONFLICT')
    require(all(x['actual_promoted_context_bound'] and x['actual_task_context_bound'] for x in observed['contexts'].values()), 'CONFLICT')
    return dict(priority_changed_without_truth_change=True, actual_native_promoted_context=True,
        actual_native_pin_context=True, native_query_view_excludes_retracted_relation=True,
        retained_old_linked_views=True, retained_c2_binding_and_truth=True,
        observation_only=True, new_inputs=0, new_reservations=0, additional_live_generations=0)


def execute(operator, native, images, package, allow_historical_missing_effects=False):
    selected = selection(native, operator.namespace)
    require(images['source_export_verification'] == 'PASS' and package['kind'] == 'caller', 'CONFLICT')
    require(digest(canonical(package['source'])) == images['source_manifest_sha256'], 'CONFLICT')
    source_hashes = {name:package['source'][name] for name in SOURCE_FILES}
    require(all(re.fullmatch('[0-9a-f]{64}', value) for value in source_hashes.values()), 'CONFLICT')
    image = next(item for item in images['images'] if item['kind'] == 'caller')
    operator.owned()
    pods = {}
    for role in ('omega-agent','omega-agent-b','fusion-episodes'):
        bound = image if role.startswith('omega-agent') else next(item for item in images['images'] if item['kind'] == 'base')
        pod = json.loads(operator.k('get', 'pod', role+'-0', '-o', 'json'))
        statuses = pod['status']['containerStatuses']
        require(len(statuses) == 1 and any(statuses[0]['imageID'].endswith(bound[key]) for key in ('manifest_digest','configuration_digest')), 'CONFLICT')
        require(pod['spec']['containers'][0]['image'] == bound['repository']+'@'+bound['manifest_digest'], 'CONFLICT')
        pods[role] = dict(uid=pod['metadata']['uid'], image=statuses[0]['imageID'], selected_image=bound['repository']+'@'+bound['manifest_digest'],
            pvcs=[v['persistentVolumeClaim']['claimName'] for v in pod['spec']['volumes'] if 'persistentVolumeClaim' in v])
    code = inspect.getsource(owned_observation)+'\nimport json\nprint(json.dumps(owned_observation('+','.join(repr(value) for value in
        ('/state', selected, '/opt/fusion', source_hashes, '/config/component.json'))+')))\n'
    observed = json.loads(operator.k('exec', '-i', 'omega-agent-0', '--', PYTHON, '-', data=code, timeout=30))
    checks = verify(observed, selected)
    effects, missing = [], []
    for role in ('omega-agent','omega-agent-b'):
        session = list(native[role]['sessions'])[0]
        code = inspect.getsource(owned_effects)+'\nimport json\nprint(json.dumps(owned_effects('+','.join(repr(value) for value in ('/state',session,selected['scope']))+')))\n'
        value = json.loads(operator.k('exec','-i',role+'-0','--',PYTHON,'-',data=code,timeout=30))
        require(value['session'] == session, 'CONFLICT')
        effects.extend(value['effects']); missing.extend(value['missing'])
    require(effects or missing, 'NOT_AVAILABLE')
    require(not missing or allow_historical_missing_effects, 'NOT_AVAILABLE')
    code = inspect.getsource(owned_history)+'\nimport json\nprint(json.dumps(owned_history('+repr('/state')+','+repr(effects)+')))\n'
    history = json.loads(operator.k('exec','-i','fusion-episodes-0','--',PYTHON,'-',data=code,timeout=30)) if effects else []
    require(len(history) == len(effects), 'CONFLICT')
    checks['external_effect_history'] = 'HISTORICAL_SOURCE_UNAVAILABLE' if missing else 'PASS'
    return dict(schema='native-combined-captured-observations/1', status='PARTIAL' if missing else 'PASS', namespace=operator.namespace,
        classification='REAL_NATIVE_CAPTURE_OBSERVATION_RECORDED_MODEL', checks=checks,
        qualification_sha256=digest(canonical(native)), source_manifest_sha256=images['source_manifest_sha256'],
        observer_sha256=digest(Path(__file__).read_bytes()), observations=observed,
        pods=pods, external_effects=effects, c1_records=history, missing_external_effects=missing,
        limitations=['Read-only selected captured state; no new provider call or new correctness/model test',
            'View retention is observed within the owning application snapshot, not a distributed transaction'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','qualification','images','source-package','output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--allow-historical-missing-effects', action='store_true', help='Older source may return PARTIAL; never a full pass')
    args = parser.parse_args()
    output = Path(args.output)
    require(not output.exists(), 'CONFLICT')
    output.mkdir(parents=True, mode=0o700)
    report = dict(status='FAILED', additional_live_generations=0, new_inputs=0, new_reservations=0)
    try:
        report = execute(Operator(args.kubeconfig,args.context,args.namespace),
            json.loads(Path(args.qualification).read_text()), json.loads(Path(args.images).read_text()),
            json.loads(Path(args.source_package).read_text()), args.allow_historical_missing_effects)
    except Exception as error:
        report['failure'] = dict(type=type(error).__name__, code=getattr(error,'code',None))
        raise
    finally:
        (output/'report.json').write_bytes(canonical(report)+b'\n')
    print(json.dumps(dict(status=report['status'], report=str(output/'report.json'), additional_live_generations=0)))


if __name__ == '__main__':
    main()
