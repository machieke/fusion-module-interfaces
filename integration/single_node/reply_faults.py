"""Opt-in, one-shot deployment-test faults after a real owner returns.

This does not implement an owner operation or retry. The marker is a consumed
test identity, not proof that response bytes reached the client. Crash after
claim remains spent. No request/result, caller identity or content hash is saved.
"""
import json
import os
from pathlib import Path
import re
import socket
import threading
import time

from fusion.contracts import canonical, require

PROFILE = 'deployment-reply-fault/1'
MAX_IDENTITIES = 16
PATHS = ('/s01','/s01-envelope','/s03-encode','/s03-read','/s03-append','/memory-source',
         '/preview/session','/preview/memory','/preview/tasks','/preview/inspection',
         '/reference-cognition')
OPERATIONS = ('submit','create','get','getMany','head','status','result','observe',
              'binding','ready','build','published','encode','query','complete',
              'send','ack','assertRelation')
READS = frozenset(('get','getMany','head','status','result','observe','binding','ready','published'))


def selection(settings):
    test = settings.get('test', {})
    if 'reply_fault' not in test:
        return None
    require(settings.get('enable_test_faults') is True, 'UNAUTHORIZED')
    require(set(test) == {'reply_fault'}, 'INVALID_ARGUMENT')
    value = test['reply_fault']
    require(type(value) is dict and set(value) == {
        'profile','identity','path','operation','mode','delay_ms','observer_deadline_ms'})
    require(value['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    require(type(value['identity']) is str and re.fullmatch('[a-z][a-z0-9-]{0,63}', value['identity']))
    require(value['path'] in PATHS and value['operation'] in OPERATIONS, 'UNSUPPORTED_OPERATION')
    require(value['mode'] in ('partial-body','delay'))
    require(type(value['delay_ms']) is int and value['delay_ms'] in (
        (0,) if value['mode'] == 'partial-body' else (250,1000,5000)))
    require(type(value['observer_deadline_ms']) is int and 0 < value['observer_deadline_ms'] <= 9007199254740991)
    return dict(value)


def operation(request):
    if type(request) is not dict:
        return None
    if 'operation' in request:
        return request['operation']
    for field in ('request','invocation'):
        inner = request.get(field)
        if type(inner) is dict and 'operation' in inner:
            return inner['operation']
    return None


def earliest_deadline(value, maximum, depth=0):
    """Existing wire deadlines can only shorten the trusted observer bound."""
    if depth > 8:
        return maximum
    if type(value) is dict:
        for key, child in value.items():
            if key in ('deadline','deadline_ms') and type(child) is int and child > 0:
                maximum = min(maximum, child)
            elif type(child) in (dict,list):
                maximum = earliest_deadline(child, maximum, depth+1)
    elif type(value) is list:
        for child in value:
            maximum = earliest_deadline(child, maximum, depth+1)
    return maximum


class ReplyFaults:
    def __init__(self, selected, state):
        self.selected = selected
        self.state = Path(state)
        self.lock = threading.Lock()
        if selected is None:
            return
        require(not self.state.is_symlink() and self.state.is_dir(), 'UNAUTHORIZED')
        self.path = self.state / ('reply-fault-'+selected['identity']+'.json')
        if self.path.exists() or self.path.is_symlink():
            self._existing()
        else:
            require(len(list(self.state.glob('reply-fault-*.json'))) < MAX_IDENTITIES, 'OVERLOADED')

    def _existing(self):
        require(not self.path.is_symlink() and self.path.is_file() and self.path.stat().st_size <= 2048, 'UNAUTHORIZED')
        try:
            record = json.loads(self.path.read_bytes())
        except (ValueError,UnicodeError):
            require(False, 'NOT_AVAILABLE')
        require(type(record) is dict and set(record) == {'selection','state','claimed_ms'} and
                record['selection'] == self.selected and record['state'] == 'claimed' and
                type(record['claimed_ms']) is int, 'CONFLICT')
        return record

    def claim(self, path, request, result):
        selected = self.selected
        if selected is None or path != selected['path'] or operation(request) != selected['operation']:
            return None
        if type(result) is dict and 'error' in result:
            return None
        deadline = selected['observer_deadline_ms']
        if selected['operation'] not in READS:
            deadline = earliest_deadline(request, deadline)
            # A returned acceptance may carry the original bound. Historical
            # nested captures inside an observation are never a new deadline.
            if type(result) is dict:
                deadline = earliest_deadline({k:result[k] for k in ('deadline','deadline_ms') if k in result}, deadline)
        with self.lock:
            return self._claim(deadline)

    def _claim(self, deadline):
        selected = self.selected
        started = time.monotonic()
        now = time.time_ns()//1000000
        if now >= deadline:
            return None
        record = canonical(dict(selection=selected, state='claimed', claimed_ms=now))
        try:
            fd = os.open(self.path, os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            self._existing()
            return None
        with os.fdopen(fd, 'wb') as output:
            output.write(record); output.flush(); os.fsync(output.fileno())
        directory = os.open(self.state, os.O_RDONLY|os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        # Both origins are captured once. Clock regression cannot lengthen a
        # sleep, while a forward jump or shutdown may shorten it.
        seconds = min(selected['delay_ms']/1000, max(0,(deadline-now)/1000))
        return dict(mode=selected['mode'], deadline_ms=deadline, until=started+seconds)


def before_reply(plan, stop):
    if plan is None or plan['mode'] != 'delay':
        return True
    while True:
        remaining = min(plan['until']-time.monotonic(), (plan['deadline_ms']-time.time_ns()//1000000)/1000)
        if remaining <= 0:
            return not stop.is_set()
        if stop.wait(min(remaining,.05)):
            return False


def write_body(plan, connection, output, data):
    if plan is None or plan['mode'] != 'partial-body':
        output.write(data)
        return
    require(len(data) > 1, 'NOT_AVAILABLE')
    # The original full Content-Length is already sent. No synthetic result or
    # altered byte is inserted: only a strict prefix of the actual reply leaves.
    output.write(data[:min(32,len(data)-1)]); output.flush()
    connection.shutdown(socket.SHUT_RDWR)
    connection.close()
