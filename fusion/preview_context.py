"""Application-owned bounded notes. No evidence, priority or storage authority."""
import json

from .contracts import canonical, digest, require

PROFILE = 'working-task-context/1'
MAX_ITEMS = 8
MAX_BYTES = 4096


class WorkingContext:
    def __init__(self, db, authorize, hook=lambda _: None):
        self.db, self.authorize, self.hook = db, authorize, hook
        db.executescript('''
            CREATE TABLE IF NOT EXISTS preview_context_views (
                revision INTEGER PRIMARY KEY, body TEXT NOT NULL, digest TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_context_receipts (
                occurrence TEXT PRIMARY KEY, intent TEXT NOT NULL, revision INTEGER NOT NULL);
        ''')
        with db:
            body = canonical({}).decode()
            db.execute('INSERT OR IGNORE INTO preview_context_views VALUES(0,?,?)',
                       (body, digest(body.encode())))

    def read(self, revision=None):
        self.authorize('context.read')
        if revision is None:
            row = self.db.execute('SELECT * FROM preview_context_views ORDER BY revision DESC LIMIT 1').fetchone()
        else:
            require(type(revision) is int and revision >= 0)
            row = self.db.execute('SELECT * FROM preview_context_views WHERE revision=?', (revision,)).fetchone()
        require(row is not None, 'NOT_AVAILABLE')
        return dict(profile=PROFILE, revision=row[0], digest=row[2],
                    items=json.loads(row[1]), interpretation='unverified-task-notes')

    def change(self, occurrence, item, note, expected_revision):
        from .preview_tools import Argument
        self.authorize('context.write')
        Argument('item', 'label').validate(item)
        require(type(occurrence) is str and 1 <= len(occurrence) <= 128)
        require(type(expected_revision) is int and expected_revision >= 0)
        if note is not None: Argument('note').validate(note)
        intent = canonical(dict(item=item, note=note, expected_revision=expected_revision)).decode()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            prior = self.db.execute('SELECT intent,revision FROM preview_context_receipts WHERE occurrence=?',
                                    (occurrence,)).fetchone()
            if prior:
                require(prior[0] == intent, 'CONFLICT')
                return self.read(prior[1])
            current = self.read()
            require(current['revision'] == expected_revision, 'CONFLICT')
            items = current['items']
            if note is None: items.pop(item, None)
            else: items[item] = note
            require(len(items) <= MAX_ITEMS and len(canonical(items)) <= MAX_BYTES, 'OVERLOADED')
            revision = expected_revision + 1
            body = canonical(items)
            self.db.execute('INSERT INTO preview_context_views VALUES(?,?,?)',
                            (revision, body.decode(), digest(body)))
            self.db.execute('INSERT INTO preview_context_receipts VALUES(?,?,?)', (occurrence, intent, revision))
        self.hook('after_context_commit')
        return self.read(revision)


def allocate_context(*, system, task, history, input_text, promoted, feedback, maximum_bytes=32768):
    """Required sections never truncate; optional sections omitted as whole data.

    A JSON envelope prevents note delimiters becoming section structure. Native
    text rendering is separate. This is a UTF-8 bound, not model token counting.
    """
    require(type(maximum_bytes) is int and 1024 <= maximum_bytes <= 65536)
    value = dict(schema='omega-context-sections/1', system=system, task=task,
                 input=input_text, feedback=feedback, history=None, promoted=None,
                 omitted=[], bound_unit='utf8-bytes')
    require(len(canonical(value)) <= maximum_bytes, 'OVERLOADED')
    for name, content in (('history', history), ('promoted', promoted)):
        value[name] = content
        if len(canonical(value)) > maximum_bytes - 32:
            value[name] = None
            value['omitted'].append(name)
    require(len(canonical(value)) <= maximum_bytes, 'OVERLOADED')
    return value
