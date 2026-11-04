"""Bounded committed hints in the existing execution journal, not an event bus.

All 384 possible events (128 admissions, results and delivered outboxes) are
retained. No global ordering, payload disclosure or execution authority follows
from a cursor. Consumers re-read the owning result under current permission.
"""
import uuid
from .contracts import canonical, require

PROFILE='execution-commit-cursor/1'


class Events:
    def __init__(self,db):
        self.db=db
        db.executescript('''CREATE TABLE IF NOT EXISTS integrated_execution_source(id TEXT PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS integrated_execution_events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT,job TEXT NOT NULL,kind TEXT NOT NULL,
            UNIQUE(job,kind));''')
        with db:
            db.execute('BEGIN IMMEDIATE')
            if not db.execute('SELECT 1 FROM integrated_execution_source').fetchone():
                db.execute('INSERT INTO integrated_execution_source VALUES(?)',(str(uuid.uuid4()),))
        self.source=db.execute('SELECT id FROM integrated_execution_source').fetchone()[0]

    def commit(self,job,kind):
        require(kind in ('accepted','result-committed','completion-delivered'))
        require(self.db.in_transaction,'CONFLICT')
        self.db.execute('INSERT OR IGNORE INTO integrated_execution_events(job,kind) VALUES(?,?)',(job,kind))
        require(self.db.execute('SELECT count(*) FROM integrated_execution_events').fetchone()[0]<=384,'OVERLOADED')

    def read(self,principal,scope,job,source,after,limit):
        require(type(after) is int and 0<=after<=384 and type(limit) is int and 1<=limit<=16)
        require(source is None or type(source) is str)
        # Filter to the requesting owner AND this task before returning even
        # counts. A global sequence can reveal another principal's activity.
        require(self.db.execute('SELECT 1 FROM jobs WHERE id=? AND scope=? AND owner=?',
            (job,scope,principal)).fetchone() is not None,'NOT_FOUND')
        rows=self.db.execute('SELECT kind FROM integrated_execution_events WHERE job=? ORDER BY seq',(job,)).fetchall()
        head=len(rows)
        gap=source not in (None,self.source) or after>head or (source is None and after!=0)
        values=[] if gap else [dict(sequence=i+1,kind=rows[i][0],job_id=job) for i in range(after,min(head,after+limit))]
        return dict(profile=PROFILE,source=self.source,scope=scope,job_id=job,head=head,
            after=after,next=after if gap else min(head,after+limit),gap=gap,
            ordering='per-task-owner-commit',events=values)


def validate(value,scope,job,source,after,limit):
    require(type(value) is dict and set(value)==set('profile source scope job_id head after next gap ordering events'.split()),'NOT_AVAILABLE')
    require(value['profile']==PROFILE and value['scope']==scope and value['job_id']==job and value['after']==after and
            value['ordering']=='per-task-owner-commit' and type(value['source']) is str,'NOT_AVAILABLE')
    require(type(value['gap']) is bool and type(value['head']) is int and 0<=value['head']<=3 and
            type(value['next']) is int and type(value['events']) is list and len(value['events'])<=limit,'NOT_AVAILABLE')
    require(source in (None,value['source']) or value['gap'],'NOT_AVAILABLE')
    if value['gap']:require(value['next']==after and value['events']==[],'NOT_AVAILABLE')
    else:
        require(after<=value['next']<=value['head'] and len(value['events'])==value['next']-after,'NOT_AVAILABLE')
        for i,event in enumerate(value['events'],after+1):
            require(event==dict(sequence=i,kind=('accepted','result-committed','completion-delivered')[i-1],job_id=job),'NOT_AVAILABLE')
    return value
