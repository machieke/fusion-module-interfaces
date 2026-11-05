"""Private owner-local dependency observation for quiesced backup exports.

This is a retained manifest, not a second knowledge store. Unknown table meaning
is explicitly retained. File closure is complete; cross-owner references remain
unverified until resolved through the named owners. No identifier is disclosed
before the supplied current-authority check. Historical retention is never freed.
"""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from fusion.contracts import canonical, digest, require

PROFILE = 'quiesced-owner-dependency-inventory/1'
MAX_ROWS = 65536
MAX_BYTES = 32 * 1024 * 1024
MAX_FILES = 150000
REASONS = {
    'app_occurrences': 'accepted-input', 'preview_inputs': 'accepted-input',
    'app_read_views': 'retained-view', 'app_query_views': 'accepted-input',
    'preview_history_outbox': 'history-chunk', 'preview_history_contexts': 'history-chunk',
    'preview_history_materializations': 'history-chunk',
    'preview_context_views': 'working-context-snapshot', 'preview_context_receipts': 'effect-receipt',
    'snapshots': 'belief-snapshot', 'history': 'priority-snapshot', 'bindings': 'priority-snapshot',
    'feed_archive_intents': 'archive-segment', 'feed_archive_members': 'archive-segment',
    'preview_relation_events': 'relations-epoch', 'lifecycle_events': 'lifecycle-epoch',
    'integrated_inspection_continuations': 'continuation-prerequisite',
    'integrated_inspection_steps': 'continuation-prerequisite',
    'integrated_chain_continuations': 'effect-receipt',
    'model_calls': 'effect-receipt', 'channel_egress': 'effect-receipt',
    'workspace_effects': 'effect-receipt', 'app_channel_outputs': 'effect-receipt',
    'app_turns': 'application-capture', 'app_memory_reads': 'application-capture',
    'app_query_vectors': 'application-capture', 'app_model_calls': 'application-capture',
}


def dependencies(value, found, depth=0):
    require(depth <= 48 and len(found) <= MAX_ROWS, 'OVERLOADED')
    if type(value) is dict:
        if {'scope_ref', 'id', 'revision', 'digest'} <= set(value) and all(type(value[x]) is str for x in ('scope_ref', 'id', 'digest')):
            if re.fullmatch('[0-9a-f]{64}', value['digest']):
                ref = {k: value[k] for k in ('scope_ref', 'id', 'revision', 'digest')}
                from fusion.contracts import validate_ref
                validate_ref(ref,ref['scope_ref'])
                found[digest(canonical(ref))] = dict(kind='source-ref', reference=ref, resolution='OWNER_PORT_REQUIRED')
        if type(value.get('generation')) is str and {'head','profile','corpus','embedding','index','logical'} <= set(value):
            ref = {k: value[k] for k in ('generation', 'head', 'profile','corpus','embedding','index','logical','lifecycle','active_digest') if k in value}
            found[digest(canonical(ref))] = dict(kind='search-generation', reference=ref, resolution='RETAINED_VIEW_PIN')
        for child in value.values(): dependencies(child, found, depth + 1)
    elif type(value) is list:
        for child in value: dependencies(child, found, depth + 1)


def inventory(root, role, files, authorize):
    authorize(role, 'dependencies.export')
    root = Path(root)
    require(type(files) is dict and len(files) <= MAX_FILES, 'OVERLOADED')
    entries = []; foreign = {}; rows_total = 0
    for name, meta in sorted(files.items()):
        path = root / name
        require(not path.is_symlink(), 'UNAUTHORIZED')
        require(path.is_file() and path.stat().st_size == meta['bytes'] and digest(path.read_bytes()) == meta['sha256'], 'CONFLICT')
        entries.append(dict(kind='file', identity=name, sha256=meta['sha256'], bytes=meta['bytes'],
                            retention='minimum-owner-retention', reclaimable=False))
        if path.suffix not in ('.sqlite', '.sqlite3', '.db'):
            if path.suffix == '.json' and meta['bytes'] <= 131072:
                try: dependencies(json.loads(path.read_bytes()), foreign)
                except (ValueError, UnicodeError): pass
            continue
        wal = Path(str(path) + '-wal')
        require(not wal.exists() or wal.stat().st_size == 0, 'NOT_AVAILABLE')
        with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
            db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
            remaining = [5000]
            def progress():
                remaining[0] -= 1
                return int(remaining[0] <= 0)
            db.set_progress_handler(progress, 1000)
            tables = sorted(r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
            require(len(tables) <= 256, 'OVERLOADED')
            for table in tables:
                require(re.fullmatch('[A-Za-z_][A-Za-z_0-9]*', table) is not None, 'UNSUPPORTED_PROFILE')
                columns = [row[1] for row in db.execute('PRAGMA table_info("' + table + '")')]
                rows = db.execute('SELECT * FROM "' + table + '" LIMIT ?', (MAX_ROWS - rows_total + 1,)).fetchall()
                rows_total += len(rows); require(rows_total <= MAX_ROWS, 'OVERLOADED')
                row_digests = []
                for row in rows:
                    encoded = [dict(bytes=len(v), sha256=digest(v)) if isinstance(v, bytes) else v for v in row]
                    row_digests.append(digest(canonical(encoded)))
                    for value in row:
                        if type(value) is str and len(value) <= 2 * 1024 * 1024 and value[:1] in ('{', '['):
                            try: dependencies(json.loads(value), foreign)
                            except (ValueError, UnicodeError): pass
                entries.append(dict(kind='owner-table', identity=name + ':' + table, file=name,
                                    rows=len(rows), semantic_head=digest(canonical(sorted(row_digests))), columns=columns,
                                    retention=REASONS.get(table, 'unknown-semantics-retain'), reclaimable=False))
    value = dict(profile=PROFILE, owner=role, files_sha256=digest(canonical(files)), entries=entries,
                 dependencies=foreign, local_byte_closure='COMPLETE', cross_owner_closure='UNVERIFIED',
                 replay_retention='UNCHANGED', authority='QUIESCED_OWNER_LOCAL_MAINTENANCE')
    require(len(canonical(value)) <= MAX_BYTES, 'OVERLOADED')
    value['head'] = digest(canonical(value))
    authorize(role, 'dependencies.export')
    return value


def page(value, selected_head, after, limit, authorize):
    authorize(value['owner'], 'dependencies.read')
    require(value['profile'] == PROFILE and value['head'] == selected_head and
            digest(canonical({k: v for k, v in value.items() if k != 'head'})) == selected_head, 'CONFLICT')
    require(type(after) is int and 0 <= after <= len(value['entries']) and type(limit) is int and 1 <= limit <= 128, 'INVALID_ARGUMENT')
    rows = value['entries'][after:after + limit]
    authorize(value['owner'], 'dependencies.read')
    return dict(profile=PROFILE, owner=value['owner'], head=selected_head, entries=rows,
                after=after, next=after + len(rows), complete=after + len(rows) == len(value['entries']),
                cross_owner_closure=value['cross_owner_closure'])


def verify_closure(value, atoms, search, authorize):
    """Resolve frozen dependencies through declared, scoped ports only.

    The caller composes actual already-authorized AtomStorage and Search ports.
    No endpoints, queries or databases are accepted in the inventory. Unknown
    table semantics remain conservatively retained, never eligible for deletion.
    Success is a current observation, not a future availability promise.
    """
    authorize(value['owner'], 'dependencies.verify')
    require(value['profile'] == PROFILE and digest(canonical({k:v for k,v in value.items() if k!='head'})) == value['head'], 'CONFLICT')
    from fusion.responses import envelope
    observations = {}; pending=dict(value['dependencies'])
    while pending:
        key=next(iter(pending));item=pending.pop(key)
        if key in observations:continue
        require(len(observations)<MAX_ROWS,'OVERLOADED')
        authorize(value['owner'], 'dependencies.verify')
        require(digest(canonical(item['reference'])) == key, 'CONFLICT')
        if item['kind'] == 'source-ref':
            response = atoms.get(item['reference'])
            envelope(response, item['reference'])
            observations[key] = dict(kind='source-ref', bytes=len(response.bytes), digest=digest(response.bytes))
            # Retained administrative roots can name immutable chunks. Resolve
            # their declared children too, rather than claiming a root read is
            # complete native history reconstruction.
            if response.content_type in ('application/omega-session-data-v1','application/omega-session-chunks-v1','application/omega-session-chunk-v1',
                    'application/omega-session-history-v1','application/omega-structural-assertion-v1','application/fusion-memory-enrollment-v1'):
                if response.content_type=='application/omega-session-chunks-v1':
                    from fusion.preview_native_history import read_body
                    read_body(atoms,item['reference'],item=response)
                try:dependencies(json.loads(response.bytes),pending)
                except (ValueError,UnicodeError):pass
        else:
            require(item['kind'] == 'search-generation', 'UNSUPPORTED_PROFILE')
            snapshot = item['reference']
            response = search.ready(snapshot['head']['scope_ref'],snapshot)
            require(response == {'ready':True}, 'NOT_AVAILABLE')
            observations[key] = dict(kind='search-generation', ready=True)
    authorize(value['owner'], 'dependencies.verify')
    return dict(profile=PROFILE, owner=value['owner'], selected_head=value['head'], status='VERIFIED_REFERENCES',
                observations=observations, semantic_unknowns_retained=True, admission_reserved=False,
                closure_sha256=digest(canonical([value['head'],observations])))
