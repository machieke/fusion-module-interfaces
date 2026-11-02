"""Recover B's captured native query before A consumes its task report.

Run only after ``preview_qualification --mode recovery-setup`` in a separate
fresh task-owned namespace. B's one-use pause marker must be absent: the earlier
five-fault qualification consumes it and is not a suitable starting state.

One new operator input is admitted. The existing native applications perform
delegation, retrieval, publication and context consumption. This example only
arms an existing fault, replaces B, and makes bounded operator observations in
each owner's own pod. It never clears markers, submits replacement work, changes
authority, refreshes a deadline, or contacts a generative backend.
"""
import argparse
import inspect
import json
import time
import uuid

from fusion.contracts import canonical, digest, require
from fusion.preview_tasks import PROFILE as TASK_PROFILE, correlated, record
from fusion.preview_tools import PROFILE as CATALOGUE_PROFILE


STAGE = 'after_task_payload_capture'
QUERY = 'synthetic silver prism storage'


def owned_snapshot(directory, session, task_id=None, identity=None, source_root=None):
    """Bounded read-only observation of this application's journal, no secrets.

    Kept self-contained so the operator can send this observer to the existing
    image without changing its frozen production source or installing a tool.
    """
    import hashlib
    import json
    from pathlib import Path
    import sqlite3
    import uuid

    assert str(uuid.UUID(session)) == session
    path = Path(directory) / 'sessions' / session / 'caller.sqlite'
    result = dict(session=session, outboxes=[], inputs=[], occurrences=[], reads=[], views=[], models=[])
    if not path.exists():
        return result

    def sha(value):
        return None if value is None else hashlib.sha256(value.encode()).hexdigest()

    def native_safe(value):
        # Same forward comparison as preview_combined_observations: the
        # allocator escapes its delimiter, then pinned native string-safe runs.
        # Reversing tokens would corrupt literal _quote_/_newline_ payload data.
        return value.replace(':-:-:-:', '\\u003a-\\u003a-\\u003a-\\u003a').replace('"', '_quote_').replace('\n', '_newline_').replace("'", '_apostrophe_')

    normalization = dict(name='native-string-safe-after-preview-delimiter-escape', source_boundary='EXPLICIT_FIXTURE')
    if source_root is not None:
        pinned = json.loads((Path(source_root)/'integration/neoclaw/sources.json').read_text())['sources']['mettaclaw']
        actual = hashlib.sha256(Path('/opt/native/sources/mettaclaw/src/utils.metta').read_bytes()).hexdigest()
        assert actual == pinned['files']['src/utils.metta']
        normalization.update(source_boundary='PINNED_NATIVE_SOURCE', source_sha256=actual, commit=pinned['commit'])

    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=.5) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'preview_native_inputs', 'app_occurrences', 'app_turns'} <= tables:
            return result
        if identity is not None and task_id is None:
            ids = list(db.execute('SELECT o.id FROM app_occurrences o JOIN preview_native_inputs i '
                'ON i.turn=o.turn WHERE i.identity=? ORDER BY o.position LIMIT 2', (identity,)))
            if len(ids) == 1:
                task_id = ids[0][0]
        result['task_id'] = task_id
        if task_id is None:
            return result
        if 'preview_task_outbox' in tables:
            for row in db.execute('SELECT * FROM preview_task_outbox WHERE id IN (?,?)',
                                  ('task/'+task_id, 'result/'+task_id)):
                value = dict(row)
                for key in ('record', 'ref', 'receipt', 'wake'):
                    value[key] = None if value[key] is None else json.loads(value[key])
                result['outboxes'].append(value)
        native = list(db.execute('SELECT i.*,t.projection FROM preview_native_inputs i '
            'LEFT JOIN app_turns t ON t.id=i.turn ORDER BY i.turn LIMIT 33'))
        assert len(native) <= 32
        for row in native:
            source = json.loads(row['source'])
            origin = source.get('task_origin')
            if not (identity is not None and row['identity'] == identity) and not (
                    origin and origin['record']['id'] == task_id):
                continue
            result['inputs'].append(dict(turn=row['turn'], identity=row['identity'],
                acknowledged=row['acknowledged'], source=source, projection_sha256=sha(row['projection'])))
            occurrences = list(db.execute('SELECT * FROM app_occurrences WHERE turn=? '
                'ORDER BY position LIMIT 6', (row['turn'],)))
            assert len(occurrences) <= 5
            for occurrence in occurrences:
                item = dict(occurrence)
                item['premises'] = json.loads(item['premises'])
                budget = db.execute('SELECT attempts FROM preview_dispatch_budget WHERE occurrence=?',
                                    (item['id'],)).fetchone() if 'preview_dispatch_budget' in tables else None
                item['attempts'] = budget[0] if budget is not None else 0
                result['occurrences'].append(item)
                if 'app_memory_reads' in tables:
                    read = db.execute('SELECT * FROM app_memory_reads WHERE id=?', (item['id'],)).fetchone()
                    if read is not None:
                        read = dict(read)
                        candidates = json.loads(read['candidates']) if read['candidates'] is not None else None
                        read['hit_refs'] = None if candidates is None else [h['ref'] for h in candidates['hits']]
                        for name in ('request', 'candidates', 'payloads'):
                            read[name+'_sha256'] = sha(read.pop(name))
                        result['reads'].append(read)
                if {'app_query_views', 'app_read_views'} <= tables:
                    view = db.execute('SELECT q.view,v.value FROM app_query_views q JOIN app_read_views v '
                        'ON v.id=q.view WHERE q.id=?', (item['id'],)).fetchone()
                    if view is not None:
                        result['views'].append(dict(occurrence=item['id'], view_id=view[0],
                            value_sha256=sha(view[1]), snapshot=json.loads(view[1])['snapshot']))
            if 'app_model_calls' in tables:
                model = db.execute('SELECT * FROM app_model_calls WHERE slot=?', (row['turn'],)).fetchone()
                if model is not None:
                    model = dict(model)
                    intent = json.loads(model.pop('intent'))
                    prompt = intent['native_prompt']
                    model['intent_sha256'] = sha(json.dumps(intent, sort_keys=True, separators=(',', ':')))
                    model.update(source_id=intent['source_id'], deadline_ms=intent['deadline_ms'],
                                 native_prompt_sha256=sha(prompt))
                    if origin and origin['record']['kind'] == 'result':
                        marker, following = ' LAST_SKILL_USE_RESULTS: ', ' HISTORY: '
                        assert prompt.count(marker) == prompt.count(following) == 1
                        assert prompt.index(marker) < prompt.index(following)
                        captured_wire = prompt.split(marker, 1)[1].split(following, 1)[0]
                        # Native &lastresults is the preceding committed turn's
                        # exact projection (startup_overlay also restores it).
                        # These are observations from this owner's journal;
                        # no expected answer, repaired text or fallback is used.
                        previous = db.execute('SELECT id,projection FROM app_turns WHERE id<? '
                            'AND projection IS NOT NULL ORDER BY id DESC LIMIT 1', (row['turn'],)).fetchone()
                        assert previous is not None and type(previous['projection']) is str
                        feedback = dict(native=previous['projection'], delegated_report=origin,
                            interpretation='agent-report-not-independent-corroboration')
                        wire = json.dumps(feedback, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
                        assert captured_wire == native_safe(wire)
                        # Publish interpreted values only after matching the
                        # entire captured native representation byte for byte.
                        model['feedback'] = feedback
                        model['feedback_observation'] = dict(normalization=normalization,
                            encoded_sha256=sha(captured_wire), exact_forward_match=True,
                            prior_turn=previous['id'], prior_projection_sha256=sha(previous['projection']))
                    for key in ('result', 'normalized', 'parse_text', 'proposal', 'admission'):
                        model[key+'_sha256'] = sha(model.pop(key))
                    result['models'].append(model)
    return result


def one(values):
    require(len(values) == 1, 'CONFLICT')
    return values[0]


def captured(before, task, task_ref):
    """Require a real committed query/result boundary; never an expected answer."""
    outbox = one(before['outboxes'])
    body = record(outbox['record'], task['scope'])
    correlated(body, task, task_ref)
    require(body['kind'] == 'result' and outbox['ref'] is not None and outbox['receipt'] is None
            and outbox['wake'] is None, 'CONFLICT')
    source = one(before['inputs'])
    require(source['source']['task_origin']['record'] == task
            and source['source']['task_origin']['ref'] == task_ref
            and source['acknowledged'] == 0 and source['projection_sha256'] is not None, 'CONFLICT')
    occurrence = one(before['occurrences'])
    require(occurrence['done'] == 1 and occurrence['result'] == body['projection']
            and occurrence['deadline'] <= task['deadline'], 'CONFLICT')
    intent = occurrence['premises']
    require(intent['operation'] == 'query_with_ids_and_dists'
            and intent['profile'] == 'semantic-active-memory-view/1'
            and intent['arguments']['query'] == task['query'], 'CONFLICT')
    read, view = one(before['reads']), one(before['views'])
    require(read['id'] == occurrence['id'] and read['queries'] == 1
            and read['payloads_sha256'] is not None and read['enrichment'] is not None
            and read['hit_refs'] == body['payloads'] and len(body['payloads']) > 0, 'CONFLICT')
    require(view['occurrence'] == occurrence['id'] and view['snapshot'] == body['view'], 'CONFLICT')
    model = one(before['models'])
    require(model['result_sha256'] is not None and model['admission_sha256'] is not None, 'CONFLICT')
    return body


def recovered(before, after, recipient, task, task_ref):
    body = captured(before, task, task_ref)
    old, new = one(before['outboxes']), one(after['outboxes'])
    for key in ('id', 'record', 'ref'):
        require(old[key] == new[key], 'CONFLICT')
    require(old['calls'] <= new['calls'] <= 24 and new['receipt'] is not None, 'CONFLICT')
    for group in ('occurrences', 'reads', 'models'):
        a, b = dict(one(before[group])), dict(one(after[group]))
        counter, maximum = ('attempts', 2) if group == 'occurrences' else ('calls', 64 if group == 'reads' else 8)
        require(a[counter] <= b[counter] <= maximum, 'CONFLICT')
        a.pop(counter); b.pop(counter)
        require(a == b, 'CONFLICT')
    require(before['views'] == after['views'], 'CONFLICT')
    require(one(after['inputs'])['acknowledged'] == 1, 'NOT_AVAILABLE')
    incoming = one(recipient['inputs'])
    origin = incoming['source']['task_origin']
    require(origin['record'] == body and origin['ref'] == old['ref']
            and incoming['source']['deadline'] == task['deadline']
            and incoming['acknowledged'] == 1 and incoming['projection_sha256'] is not None, 'CONFLICT')
    model = one(recipient['models'])
    require(model['source_id'] == incoming['source']['occurrence']
            and model['deadline_ms'] == task['deadline']
            and model['result_sha256'] is not None and model['admission_sha256'] is not None, 'CONFLICT')
    feedback = model['feedback']
    require(feedback['delegated_report'] == origin
            and feedback['interpretation'] == 'agent-report-not-independent-corroboration', 'CONFLICT')
    return dict(exact_result_atom=True, exact_query_projection=True, exact_retained_view=True,
        new_search_queries=0, original_deadlines=True, spent_budgets_preserved=True,
        actual_recipient_prompt_binding=True, recipient_native_completion=True,
        independent_corroboration=False)


def preflight(values, native, namespace, marker):
    preview = values['preview']
    require(native['namespace'] == namespace and native['status'] == 'PASS'
            and native['mode'] == 'recovery-setup', 'UNAUTHORIZED')
    require(preview['scope'].startswith('synthetic-') and preview['model_boundary'] == 'RECORDED_FIXTURE'
            and preview['tasks']['enabled'] is True and preview['memory']['enabled'] is True, 'UNAUTHORIZED')
    require(not values.get('futureLive', {}).get('enabled', False)
            and not values.get('futureLive', {}).get('activated', False), 'UNAUTHORIZED')
    require(marker is None, 'CONFLICT')
    require(all(not component.get('config', {}).get('test')
                for component in values.get('components', {}).values()), 'CONFLICT')
    for role in ('omega-agent', 'omega-agent-b'):
        require(native[role]['model_boundary'] == 'RECORDED_FIXTURE'
                and native[role]['scope'] == preview['scope'], 'UNAUTHORIZED')


def session_bindings(values, inventories, sender_session):
    """Select ingress B from configuration, never serialized map key order.

    A is an explicit operator-selected eligible session. B must match
    preview_task_configure.provider's agents[role].sessions[0] binding.
    """
    preview = values['preview']
    require(preview['scope'].startswith('synthetic-')
            and preview['model_boundary'] == 'RECORDED_FIXTURE', 'UNAUTHORIZED')
    selected = {}
    for direction, role, principal in (('sender', 'omega-agent', 'A'), ('recipient', 'omega-agent-b', 'B')):
        configured = preview['agents'][role]
        inventory = inventories[role]
        sessions = configured['sessions']
        require(type(sessions) is list and 1 <= len(sessions) <= 8
                and len(set(sessions)) == len(sessions), 'CONFLICT')
        require(configured['principal'] == inventory['principal'] == principal
                and inventory['scope'] == preview['scope']
                and inventory['model_boundary'] == 'RECORDED_FIXTURE', 'UNAUTHORIZED')
        require(type(inventory['sessions']) is dict and set(sessions) == set(inventory['sessions']), 'CONFLICT')
        sid = sender_session if direction == 'sender' else sessions[0]
        require(sid in sessions and sid in inventory['catalogues'], 'CONFLICT')
        binding, catalogue = inventory['sessions'][sid], inventory['catalogues'][sid]
        require(binding['model_boundary'] == 'RECORDED_FIXTURE'
                and catalogue['profile'] == CATALOGUE_PROFILE, 'UNSUPPORTED_PROFILE')
        tools = {'delegate': TASK_PROFILE, 'task-context': 'working-task-context/1'} if direction == 'sender' else {
            'query': 'semantic-active-memory-view/1'}
        for name, profile in tools.items():
            require(name in catalogue['tools'] and catalogue['tools'][name]['descriptor']['profile'] == profile,
                    'UNSUPPORTED_PROFILE')
        selected[direction] = dict(role=role, principal=principal, session=sid, scope=preview['scope'],
            selection='explicit-operator-session' if direction == 'sender' else 'configured-task-ingress-first-session',
            configured_sessions=sessions, inventory_sessions=sorted(inventory['sessions']),
            session_binding=binding, catalogue_profile=catalogue['profile'], required_tool_profiles=tools)
    return selected


class HandoffRecovery:
    def __init__(self, recovery):
        self.r = recovery
        self.report = dict(namespace=recovery.op.namespace, classification='REAL_DEPLOYED_NATIVE_WITH_RECORDED_MODEL',
            additional_live_generations=0, maximum_new_operator_inputs=1, fault=STAGE,
            fresh_namespace_required=True, fault_marker_resets=0, deadline_renewals=0,
            stale_or_withdrawn_results='FIXTURE_TESTED_ONLY', status='NOT_RUN')

    def save(self):
        (self.r.root/'handoff-report.json').write_bytes(canonical(self.report))

    def state(self, role, sid, task_id=None, identity=None):
        args = ['/state', sid, task_id, identity, '/opt/fusion']
        source = inspect.getsource(owned_snapshot)+'\nprint(json.dumps(owned_snapshot(*'+repr(args)+')))\n'
        return json.loads(self.r.code(role, 'import json\n'+source))

    def run(self):
        r = self.r
        try:
            r.op.owned()
            preflight(r.values, r.native, r.op.namespace, r.read('omega-agent-b', 'pause.json'))
            self.report['native_setup_sha256'] = digest(canonical(r.native))
            self.report['values_before_fault_sha256'] = digest(r.values_path.read_bytes())
            self.report['before_images'] = {role: r.pod(role) for role in ('omega-agent', 'omega-agent-b',
                'fusion-model', 'fusion-storage', 'fusion-search', 'fusion-embedding', 'fusion-messaging')}
            self.report['current_inventory'] = {role: r.api.call(role, 'inventory')
                                               for role in ('omega-agent', 'omega-agent-b')}
            bindings = session_bindings(r.values, self.report['current_inventory'], r.ids['omega-agent'][0])
            self.report['selected_session_bindings'] = bindings
            sid_a, sid_b = bindings['sender']['session'], bindings['recipient']['session']
            self.save()
            for role in ('omega-agent', 'omega-agent-b'):
                for sid in r.ids[role]:
                    page = r.api.call(role, 'observe', sid)
                    while True:
                        require(all(item['state'] == 'complete' for item in page['inputs']), 'NOT_AVAILABLE')
                        if page['next_after'] is None:
                            break
                        page = r.api.call(role, 'observe', sid, '--after', str(page['next_after']))
            marker = r.arm('omega-agent-b', 'pause_at', STAGE)
            self.report['values_with_fault_sha256'] = digest(r.values_path.read_bytes())
            identity = 'handoff-recovery-'+str(uuid.uuid4())
            accepted = r.api.call('omega-agent', 'submit', sid_a, '--identity', identity,
                '--text', 'delegate B '+QUERY, '--assignment', 'synthetic-task')
            self.report['accepted'] = accepted
            self.save()
            until = min(r.end, time.monotonic()+max(0, (accepted['deadline']-time.time()*1000)/1000)+8)
            fired = None
            while time.monotonic() < until:
                fired = r.read('omega-agent-b', marker)
                if fired is not None:
                    break
                time.sleep(.25)
            require(fired is not None, 'NOT_AVAILABLE')
            self.report['fault_marker'] = fired
            sender = self.state('omega-agent', sid_a, identity=identity)
            task_outbox = one(sender['outboxes'])
            task, task_ref = task_outbox['record'], task_outbox['ref']
            require(task['kind'] == 'task' and task['session'] == sid_a
                    and task['deadline'] <= accepted['deadline'], 'CONFLICT')
            self.report['task'] = task_outbox
            before = self.state('omega-agent-b', sid_b, task['id'])
            require(captured(before, task, task_ref)['session'] == sid_b, 'CONFLICT')
            self.report['captured_before_replacement'] = before
            recipient_before = self.state('omega-agent', sid_a, task['id'])
            require(not recipient_before['inputs'], 'CONFLICT')
            self.report['recipient_before_replacement'] = recipient_before
            provider_before = r.model_accounting(sid_b)
            self.report['model_before_replacement'] = provider_before
            self.save()
            # Only B is killed. A stays available for the original task's wake;
            # replacing A is separately covered by the existing input tests.
            self.report['replacement'] = r.replace(['omega-agent-b'])
            self.save()
            while time.monotonic() < until:
                recipient = self.state('omega-agent', sid_a, task['id'])
                after = self.state('omega-agent-b', sid_b, task['id'])
                if recipient['inputs'] and all(x['acknowledged'] for x in recipient['inputs']) \
                        and after['inputs'] and all(x['acknowledged'] for x in after['inputs']):
                    break
                time.sleep(.5)
            after = self.state('omega-agent-b', sid_b, task['id'])
            recipient = self.state('omega-agent', sid_a, task['id'])
            self.report.update(after_replacement=after, recipient=recipient,
                model_after_replacement=r.model_accounting(sid_b))
            self.save()
            require(provider_before == self.report['model_after_replacement'], 'CONFLICT')
            self.report['guarantees'] = recovered(before, after, recipient, task, task_ref)
            source_observed = r.observe('omega-agent', sid_a, identity)
            return_observed = r.observe('omega-agent', sid_a, one(recipient['inputs'])['identity'])
            self.report.update(source_observation=source_observed, recipient_observation=return_observed)
            require(source_observed['state'] == return_observed['state'] == 'complete'
                    and source_observed['deadline'] == accepted['deadline']
                    and return_observed['deadline'] == task['deadline'], 'CONFLICT')
            require(r.read('omega-agent-b', marker) == fired, 'CONFLICT')
            self.report['status'] = 'PASS'
        except Exception as error:
            # Operator stderr can include local paths/configuration; publish
            # only type/code. Owner journals and the one-use marker are retained.
            self.report.update(status='FAILED', failure=dict(type=type(error).__name__, code=getattr(error, 'code', None)))
            raise
        finally:
            self.save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ('kubeconfig', 'context', 'namespace', 'values', 'chart', 'output', 'native'):
        parser.add_argument('--'+field, required=True)
    args = parser.parse_args()
    # Lazy import: fixture checks of the observer need no Helm/PyYAML runtime.
    from integration.single_node.preview_recovery_qualification import Recovery
    from integration.single_node.reference_ops import Operator
    op = Operator(args.kubeconfig, args.context, args.namespace)
    HandoffRecovery(Recovery(op, args.values, args.chart, args.output, args.native)).run()


if __name__ == '__main__':
    main()
