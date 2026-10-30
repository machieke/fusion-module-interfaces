"""Closed query/send composition. Receipts are trusted application output, not consent.

The operator approves exact generated record components. The application checks
those against its retained, owner-authorized read capture before issuing a receipt.
The model owner receives only the receipt, never the corpus or application journal.
"""
import ast
import uuid
import json
import os
from pathlib import Path

from . import model_contracts as m
from .contracts import canonical, digest, require

APPLICATION = 'controlled-native-loop/10'
SERVICE_APPLICATION = 'controlled-native-loop/11'
POLICY = 'synthetic-retrieval-query-send/1'
PRIOR = 'neoclaw-fresh-memory-compatibility-prior/1:not-registered'
MAX_BODIES = 8


def safe_data(text):
    require(type(text) is str and 0 < len(text.encode()) <= 2048, 'UNAUTHORIZED')
    require(not any(x in text for x in (
        '\n', '\r', '"', "'", '_quote_', '_apostrophe_', ':-:-:-:',
        ' LAST_SKILL_USE_RESULTS:', ' HISTORY:', ' MOST_PROMOTED_MEMORIES:', ' TIME:',
        'COMMAND_RETURN:', '<tool_call>', '</tool_call>', '<arg_value>', '</arg_value>')),
        'UNAUTHORIZED')
    return text


def configuration(cfg):
    policy = cfg['disclosure']
    require(policy.get('policy') == POLICY, 'UNSUPPORTED_PROFILE')
    require(set(policy) == {'policy', 'scaffold', 'memories', 'users', 'query', 'receipt_root',
                            'recipient', 'consent_sha256', 'view_sha256', 'authority_policy'}, 'UNSUPPORTED_PROFILE')
    require(policy['memories'] == ['()'] and len(policy['users']) == 2, 'UNAUTHORIZED')
    safe_data(policy['query'])
    require(type(policy['recipient']) is str and 1 <= len(policy['recipient']) <= 100, 'UNAUTHORIZED')
    require(type(cfg['commands']) is list and 3 <= len(cfg['commands']) <= MAX_BODIES + 1)
    require(cfg['commands'][0] == ['query', policy['query']], 'UNSUPPORTED_OPERATION')
    bodies = cfg['commands'][1:]
    require(all(type(x) is list and len(x) == 2 and x[0] == 'send' for x in bodies), 'UNSUPPORTED_OPERATION')
    for _, body in bodies:
        safe_data(body)
        require(len(body.encode()) <= 400, 'INVALID_ARGUMENT')
    require(len({body for _, body in bodies}) == len(bodies), 'INVALID_ARGUMENT')


def admit(cfg, slot, commands):
    require(type(commands) is list and len(commands) == 1, 'UNSUPPORTED_OPERATION')
    allowed = cfg['commands'][:1] if slot == 1 else cfg['commands'][1:] if slot == 2 else []
    require(commands[0] in allowed, 'UNSUPPORTED_OPERATION')


def structural(raw, policy):
    from .neoclaw_model_disclosure import dissect, check_time_and_transform
    parts = dissect(raw)
    require(parts['scaffold'] == policy['scaffold'] and parts['history'] == '', 'UNAUTHORIZED')
    require(parts['memories'] == '()' and parts['user'] in policy['users'], 'UNAUTHORIZED')
    check_time_and_transform(raw, parts)
    return parts


def preflight(cfg, intent, operation='disclose'):
    """Trusted same-host issuer reads the owner's public authorization policy.

    This is the very same Policy used by ModelService, not a copied permission
    cache or another authority. It contains no corpus, journal or backend secrets.
    Recipient/credential checks precede even an observe/authorize HTTPS body.
    The owner independently rechecks when it receives the request.
    """
    from .policy import Policy
    from .registry import descriptor_read, selection_token
    policy = Policy(cfg['disclosure']['authority_policy'])
    owner = policy.current()['model_completion']
    principal = policy.authenticate(cfg['credential'])
    require(principal == intent['principal'] == cfg['principal'] and
            owner['scope'] == intent['scope'] == cfg['scope'] and
            intent['session'] in owner['sessions'], 'UNAUTHORIZED')
    require(owner['disclosure'] == cfg['disclosure'], 'UNAUTHORIZED')
    require(selection_token(m.select([descriptor_read(x) for x in owner['catalogue']], intent['profile'])) ==
            intent['selection'], 'UNSUPPORTED_PROFILE')
    for method in {'disclose', operation}: policy.check(principal, intent['scope'], 'model.'+method)


def receipt_path(policy, intent):
    m.uid(intent['id'])
    return Path(policy['receipt_root']) / (intent['id'] + '.json')


def validate_receipt(raw, policy, intent):
    require(intent is not None and raw == intent['native_prompt'], 'UNAUTHORIZED')
    parts = structural(raw, policy)
    require(intent['slot'] in (1, 2) and parts['user'] == policy['users'][intent['slot'] - 1], 'UNAUTHORIZED')
    path = receipt_path(policy, intent)
    require(path.is_file() and path.stat().st_size <= 100000, 'UNAUTHORIZED')
    receipt = json.loads(path.read_bytes())
    require(set(receipt) == {'policy', 'recipient', 'consent_sha256', 'intent', 'query', 'context_view'}, 'UNAUTHORIZED')
    require(receipt['policy'] == POLICY and receipt['recipient'] == policy['recipient'] and
            receipt['consent_sha256'] == policy['consent_sha256'] and receipt['context_view'] == policy['view_sha256'] and receipt['intent'] == intent, 'UNAUTHORIZED')
    if intent['slot'] == 1:
        require(parts['feedback'] == '' and receipt['query'] is None, 'UNAUTHORIZED')
    else:
        query = receipt['query']
        require(type(query) is dict and set(query) == {'occurrence', 'view', 'projection', 'result', 'capture_sha256'}, 'UNAUTHORIZED')
        require(parts['feedback'] == query['projection'] and query['projection'], 'UNAUTHORIZED')
        require(query['occurrence'] == str(uuid.uuid5(uuid.UUID(intent['session']), '1/0')) and
                query['view'] == policy['view_sha256'], 'UNAUTHORIZED')
        require(query['projection'] == projection(policy['query'], query['result']), 'UNAUTHORIZED')
    return parts


def projection(query, result):
    # On this closed domain no embedded quotes/newlines/markers are admitted.
    # Native string-safe maps the Python list representation's apostrophes once.
    require(type(result) is str and not any(x in result for x in ('"', '\n', '_apostrophe_', '_quote_', ':-:-:-:')), 'UNAUTHORIZED')
    return ('(RESULTS: ((COMMAND_RETURN: ((query '+query+') '+result+'))))').replace("'", '_apostrophe_')


def presentation(result, payloads, consent):
    try: rendered = ast.literal_eval(result)
    except (SyntaxError, ValueError, TypeError): require(False, 'UNAUTHORIZED')
    require(type(rendered) is list and len(rendered) <= 6, 'UNAUTHORIZED')
    allowed = []
    for uid, timestamp, content, distance in payloads:
        approved = consent[uid]
        allowed.append([['id:', timestamp], ['linkedEpisodes:', approved['metadata']['links']],
                        ['stv', *approved['metadata']['stv']], content])
    require(all(record in allowed for record in rendered), 'UNAUTHORIZED')
    require(len({repr(x) for x in rendered}) == len(rendered), 'UNAUTHORIZED')


def binding(app):
    require(app.config['composition'] == APPLICATION, 'UNSUPPORTED_PROFILE')
    value = app.config['retrieval']
    require(set(value) == {'initial_view', 'consent'}, 'UNSUPPORTED_PROFILE')
    consent = value['consent']
    require(set(consent) == {'recipient', 'records'}, 'UNSUPPORTED_PROFILE')
    require(type(consent['records']) is list and 2 <= len(consent['records']) <= 8, 'UNAUTHORIZED')
    view = value['initial_view']
    require(set(view) == {'snapshot', 'metadata', 'metadata_seal', 'defaults'}, 'UNSUPPORTED_PROFILE')
    require(view['snapshot'] == app.binding['memory']['snapshot'] and
            view['metadata_seal'] == app.binding['memory']['metadata_seal'] ==
            digest(canonical(view['metadata'])), 'CONFLICT')
    require(set(view['defaults']) == {r['uuid'] for r in view['metadata']['records']} and
            set(view['defaults'].values()) == {PRIOR}, 'UNAUTHORIZED')
    for record in consent['records']:
        require(set(record) == {'uuid', 'time', 'content', 'metadata', 'default'}, 'UNAUTHORIZED')
        m.uid(record['uuid'])
        safe_data(record['content']); safe_data(record['time'])
        require(record['metadata'] in view['metadata']['records'] and record['metadata']['uuid'] == record['uuid'] and
                record['default'] == PRIOR and record['metadata']['stv'] == [1.0, .5] and
                record['metadata']['links'] == [record['time']] and record['metadata']['promotion'] == 0., 'UNAUTHORIZED')
    require(len({r['uuid'] for r in consent['records']}) == len(view['metadata']['records']) == len(consent['records']), 'UNAUTHORIZED')
    return value


def initial_history(app, query):
    """A captured first prompt may resume its own unfinished query occurrence."""
    turns = app.db.execute('SELECT id,commands,projection FROM app_turns ORDER BY id').fetchall()
    require(not turns or (len(turns) == 1 and turns[0]['id'] == 1 and turns[0]['projection'] is None and
                          json.loads(turns[0]['commands']) == [['query', query]]), 'UNAUTHORIZED')


def issue(app, intent):
    """Only reads the application's own journal plus existing authorizing ports."""
    cfg, _ = app.model.current()
    preflight(cfg, intent)
    policy = cfg['disclosure']; value = binding(app); consent = value['consent']
    require(value == app.binding['retrieval'], 'CONFLICT')
    require(digest(canonical(consent)) == policy['consent_sha256'] and consent['recipient'] == policy['recipient'], 'UNAUTHORIZED')
    parts = structural(intent['native_prompt'], policy)
    require(intent['slot'] in (1, 2) and parts['user'] == policy['users'][intent['slot'] - 1], 'UNAUTHORIZED')
    # restore reauthorizes the saved query via Embedding, Search, C1/C2, Attention.
    require(parts['feedback'] == app.restore() and app.priority.context_replay() == '()', 'CONFLICT')
    query = None
    if intent['slot'] == 1:
        require(parts['feedback'] == '', 'UNAUTHORIZED')
        initial_history(app, policy['query'])
    else:
        turn = app.db.execute('SELECT * FROM app_turns WHERE id=1').fetchone()
        require(turn is not None and json.loads(turn['commands']) == [['query', policy['query']]] and
                turn['projection'] == parts['feedback'], 'UNAUTHORIZED')
        rows = app.db.execute('SELECT * FROM app_occurrences WHERE turn=1 ORDER BY position').fetchall()
        require(len(rows) == 1 and rows[0]['done'] == 1 and rows[0]['result'] is not None, 'NOT_AVAILABLE')
        row = rows[0]; view = app.write.view_for(row)
        require(view == value['initial_view'], 'CONFLICT')
        app.memory.authorize(row)
        capture = app.db.execute('SELECT * FROM app_memory_reads WHERE id=?', (row['id'],)).fetchone()
        require(capture is not None and capture['payloads'] is not None and capture['candidates'] is not None, 'NOT_AVAILABLE')
        permitted = {r['uuid']: r for r in consent['records']}
        for uid, timestamp, content, distance in json.loads(capture['payloads']):
            require(uid in permitted, 'UNAUTHORIZED')
            approved = permitted[uid]
            require([timestamp, content] == [approved['time'], approved['content']], 'UNAUTHORIZED')
        # Native rendering is retained, not reimplemented. Bind its exact saved
        # result and one-command projection. No evaluator text enters this path.
        presentation(row['result'], json.loads(capture['payloads']), permitted)
        expected = projection(policy['query'], row['result'])
        require(parts['feedback'] == expected, 'CONFLICT')
        query = dict(occurrence=row['id'], view=digest(canonical(view)), projection=parts['feedback'],
                     result=row['result'], capture_sha256=digest(canonical({
                         k:capture[k] for k in ('request', 'candidates', 'payloads', 'enrichment')})))
    receipt = dict(policy=POLICY, recipient=policy['recipient'], consent_sha256=policy['consent_sha256'],
                   intent=intent, query=query, context_view=app.priority.context()['view'])
    path = receipt_path(policy, intent)
    raw = canonical(receipt)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists():
        require(path.read_bytes() == raw, 'CONFLICT')
    else:
        # Durable immutable publication before any provider request; interrupted
        # writes leave only an unselected temporary file.
        pending = path.with_suffix('.pending')
        with open(pending, 'wb') as stream:
            os.chmod(pending, 0o600); stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(pending, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    return validate_receipt(intent['native_prompt'], policy, intent)
