"""Real gate/handler concurrency with explicit owner and transport fixtures.

No HTTP listener, TLS connection, DeTTa runtime, native application or cluster
starts. Handler setup is captured through a fixture server and fixture owners.
Real locks, admission slots and the actual two-second queue timeout are used.
"""
import copy
from email.message import Message
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fusion.contracts import ContractError, canonical
from integration.single_node import server


class ObservedLock:
    """Observe entry into the real lock wait without changing its timeout."""
    def __init__(self, lock):
        self.lock = lock
        self.condition = threading.Condition()
        self.attempts = []

    def acquire(self, *, timeout):
        with self.condition:
            self.attempts.append(timeout)
            self.condition.notify_all()
        return self.lock.acquire(timeout=timeout)

    def release(self): self.lock.release()
    def locked(self): return self.lock.locked()

    def wait_attempts(self, count):
        with self.condition:
            return self.condition.wait_for(lambda: len(self.attempts) >= count, timeout=1)


class StorageGateTests(unittest.TestCase):
    def gate(self):
        gate = server.StorageGate()
        gate.writer = ObservedLock(gate.writer)
        return gate

    def assert_free_slots(self, gate, expected=4):
        held = 0
        try:
            while gate.slots.acquire(blocking=False): held += 1
            self.assertEqual(held, expected)
        finally:
            for _ in range(held): gate.slots.release()

    def test_one_writer_and_three_waiters_refuse_fifth_then_progress_without_overlap(self):
        gate = self.gate(); gate.enter()
        observations = {'active': 1, 'peak': 1, 'entered': 0}
        lock = threading.Lock(); failures = []
        def worker():
            entered = False
            try:
                gate.enter(); entered = True
                with lock:
                    observations['active'] += 1
                    observations['peak'] = max(observations['peak'], observations['active'])
                    observations['entered'] += 1
                threading.Event().wait(.005)
                with lock: observations['active'] -= 1
            except BaseException as error: failures.append(error)
            finally:
                if entered: gate.leave()
        threads = [threading.Thread(target=worker, daemon=True) for _ in range(3)]
        try:
            for thread in threads: thread.start()
            self.assertTrue(gate.writer.wait_attempts(4))
            self.assertEqual(observations['entered'], 0)
            before = time.monotonic()
            for _ in range(20):
                with self.assertRaises(ContractError) as caught: gate.enter()
                self.assertEqual(caught.exception.code, 'OVERLOADED')
            self.assertLess(time.monotonic()-before, .5)
            self.assertEqual(gate.writer.attempts, [2]*4)
        finally:
            with lock: observations['active'] -= 1
            gate.leave()
            for thread in threads: thread.join(3)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        self.assertEqual(observations, {'active': 0, 'peak': 1, 'entered': 3})
        self.assert_free_slots(gate)

    def test_real_queue_timeouts_release_slots_without_releasing_active_writer(self):
        gate = self.gate(); gate.enter(); outcomes = []
        def waiter():
            started = time.monotonic()
            try:
                gate.enter()
            except ContractError as error:
                outcomes.append((error.code, time.monotonic()-started))
            else:
                outcomes.append(('UNEXPECTED_ADMISSION', time.monotonic()-started))
                gate.leave()
        threads = [threading.Thread(target=waiter, daemon=True) for _ in range(3)]
        try:
            for thread in threads: thread.start()
            self.assertTrue(gate.writer.wait_attempts(4))
            for thread in threads: thread.join(3)
            self.assertTrue(all(not thread.is_alive() for thread in threads))
            self.assertEqual(len(outcomes), 3)
            for code, duration in outcomes:
                self.assertEqual(code, 'OVERLOADED')
                self.assertGreaterEqual(duration, 1.8)
                self.assertLess(duration, 3)
            self.assertTrue(gate.writer.locked())
            self.assert_free_slots(gate, 3)
        finally:
            gate.leave()
            for thread in threads: thread.join(3)
        gate.enter(); gate.leave()
        self.assert_free_slots(gate)


class StorageHandlerGateTests(unittest.TestCase):
    assert_free_slots = StorageGateTests.assert_free_slots

    def run_handler(self, exercise):
        gate = server.StorageGate(); events = []; failures = []; signals = {}
        provider_failure = [None]
        class OwnerFixture:
            def invoke(self, *args):
                events.append(dict(args=copy.deepcopy(args), exclusive=gate.writer.locked()))
                if provider_failure[0] is not None: raise provider_failure[0]
                return dict(boundary='OWNER_RESULT_FIXTURE')
            public = invoke
            private = invoke
        owner = OwnerFixture()
        class ServerFixture:
            def __init__(self, address, handler): self.handler = handler
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def handle_request(self):
                try: exercise(self.handler, gate, events, provider_failure)
                except BaseException as error: failures.append(error)
                finally: signals[server.signal.SIGTERM]()
        with tempfile.TemporaryDirectory(prefix='phase2-storage-handler-') as temporary:
            root = Path(temporary); state = root/'state'; run = root/'run'; run.mkdir()
            for name in ('owner.json', 'facet-owner.json', 'cognitive-owner.json', 'inspect-owner.json'):
                (run/name).write_text('{}')
            settings = dict(role='fusion-storage', state=str(state),
                service_composition='omega-single-node-developer-preview/1', https_port=18443,
                revision='synthetic-handler-fixture', preview=dict(enabled=True, agents={},
                    scope='synthetic-storage-handler', memory={'enabled': True}))
            config = dict(tls_certificate='/fixture/not-read.crt', tls_key='/fixture/not-read.key')
            path = root/'component.json'; path.write_bytes(canonical(settings))
            original_exists = Path.exists
            def exists(selected):
                return False if str(selected) == '/state/restore-fence.json' else original_exists(selected)
            with (patch.object(server.sys, 'argv', ['server-fixture', str(path)]),
                  patch.dict(server.os.environ, {'POD_NAME': 'fusion-storage-0'}),
                  patch.object(Path, 'exists', exists),
                  patch.object(server, 'StorageGate', return_value=gate),
                  patch.object(server, 'ThreadingHTTPServer', ServerFixture),
                  patch.object(server.ssl, 'SSLContext'),
                  patch.object(server.signal, 'signal', side_effect=lambda number, fn: signals.update({number: fn})),
                  patch.object(server, 'OwnerService', return_value=owner),
                  patch('fusion.preview_memory_services.Ports', return_value=owner),
                  patch('fusion.memory_services.StoragePorts', return_value=owner),
                  patch('fusion.preview_ports.Ports', return_value=owner),
                  patch('fusion.cognitive_services.Ports', return_value=owner),
                  patch('fusion.preview_inspect.Ports', return_value=owner)):
                server.main(config_resolver=lambda _: (settings, config, state, run))
        if failures: raise failures[0]

    @staticmethod
    def request(handler, path, request=None, *, method='POST', authorized=True):
        instance = object.__new__(handler)
        instance.path = path; instance.headers = Message()
        if authorized: instance.headers['Authorization'] = 'Bearer SYNTHETIC_PROVIDER_CREDENTIAL'
        raw = canonical(request or {})
        instance.headers['Content-Type'] = 'application/json'
        instance.headers['Content-Length'] = str(len(raw))
        instance.rfile = io.BytesIO(raw)
        replies = []
        instance.reply = lambda value, status=200: replies.append((status, value))
        getattr(instance, 'do_'+method)()
        return replies[0]

    def test_selected_storage_ports_share_gate_and_forward_identity_deadline_and_authority_unchanged(self):
        def exercise(handler, gate, events, failure):
            request = dict(message_id='synthetic-stable-occurrence', deadline_ms=123,
                           attempts=3, operation='fixture-read')
            for path in ('/s01', '/ports/atom-create', '/s03-append', '/s03-read', '/memory-source',
                         '/memory-initial', '/preview/memory', '/preview/facets', '/reference-cognition',
                         '/preview/inspection', '/preview/inspection-completion'):
                with self.subTest(path=path):
                    status, value = self.request(handler, path, request)
                    self.assertEqual((status, value), (200, {'boundary': 'OWNER_RESULT_FIXTURE'}))
                    observed = events[-1]
                    self.assertTrue(observed['exclusive'])
                    self.assertEqual(observed['args'][-1], request)
                    self.assertEqual(observed['args'][:-1].count('SYNTHETIC_PROVIDER_CREDENTIAL'), 1)
                    self.assertFalse(gate.writer.locked())
                    self.assert_free_slots(gate)
        self.run_handler(exercise)

    def test_provider_exceptions_release_gate_for_next_request(self):
        def exercise(handler, gate, events, failure):
            for error, code in ((ContractError('UNAUTHORIZED'), 'UNAUTHORIZED'),
                                (ValueError('sensitive fixture detail'), 'INVALID_ARGUMENT'),
                                (OSError('sensitive fixture detail'), 'NOT_AVAILABLE'),
                                (sqlite3.OperationalError('sensitive fixture detail'), 'NOT_AVAILABLE')):
                with self.subTest(error=type(error).__name__):
                    failure[0] = error
                    _, result = self.request(handler, '/s03-read', {'operation': 'fixture-read'})
                    self.assertEqual(result['error']['code'], code)
                    self.assertNotIn('sensitive', json.dumps(result))
                    self.assertFalse(gate.writer.locked())
                    self.assert_free_slots(gate)
                    failure[0] = None
                    self.assertEqual(self.request(handler, '/s03-read')[1], {'boundary': 'OWNER_RESULT_FIXTURE'})
        self.run_handler(exercise)

    def test_health_never_enters_gate_and_bad_authentication_never_calls_owner(self):
        def exercise(handler, gate, events, failure):
            gate.enter()
            try:
                with patch.object(gate, 'enter', side_effect=AssertionError('Health must not queue')):
                    for path in ('/health/startup', '/health/ready', '/health/live'):
                        self.assertEqual(self.request(handler, path, method='GET', authorized=False),
                                         (200, {'role': 'fusion-storage', 'ready': True}))
                    self.assertEqual(self.request(handler, '/s03-read', authorized=False)[1]['error']['code'],
                                     'UNAUTHORIZED')
                self.assertEqual(events, [])
            finally: gate.leave()
            self.assert_free_slots(gate)
        self.run_handler(exercise)


if __name__ == '__main__':
    unittest.main()
