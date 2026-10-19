"""Selected existing recorded-response checks, inside a network-isolated bwrap.

No native stack, HTTP host, runtime readiness or generation recipe is invoked.
The only child processes are forked recorded-backend fault-test children.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import unittest

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
assert os.readlink('/proc/self/ns/net') != os.environ['S07_REVIEW_PARENT_NET']
denied = []


def guard(event, args):
    if event in ('socket.connect', 'socket.bind', 'subprocess.Popen', 'os.system', 'os.exec', 'os.posix_spawn'):
        denied.append(event)
        raise PermissionError('S07 closeout: no network or executable launch')


sys.addaudithook(guard)
# Demonstrate the guard before importing the inspected test entrypoints.
with socket.socket() as probe:
    try:
        probe.connect(('127.0.0.1', 48173))
    except PermissionError:
        pass
    else:
        raise AssertionError('Guard failed')
assert denied == ['socket.connect']
denied.clear()
suite = unittest.defaultTestLoader.loadTestsFromNames(['tests.test_model', 'tests.test_model_oracle'])


class Result(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passing = []
        self.subcases = 0

    def addSuccess(self, test):
        self.passing.append(test.id())
        super().addSuccess(test)

    def addSubTest(self, test, subtest, error):
        self.subcases += 1
        super().addSubTest(test, subtest, error)


result = unittest.TextTestRunner(verbosity=2, resultclass=Result).run(suite)
assert not denied, denied
sources = {}
for path in json.loads((root / 'evidence/s07/remaining-live-source.json').read_text())['files']:
    sources[path] = hashlib.sha256((root / path).read_bytes()).hexdigest()
source = 'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py'
sources[source] = hashlib.sha256((root / source).read_bytes()).hexdigest()
print(json.dumps(dict(classification='ISOLATED_RECORDED_RESPONSE_TESTS',
    status='PASS' if result.wasSuccessful() else 'FAIL', python=sys.version,
    network_namespace_isolated=True, network_guard_probed=True,
    forbidden_network_or_exec_attempts_during_tests=denied, passing_methods=result.passing,
    methods_run=result.testsRun, subcase_observations=result.subcases,
    provider_sigkill_fixture_stages=4, real_native_stack_started=False,
    sources=sources, ADDITIONAL_LIVE_GENERATIONS=0), indent=2))
sys.exit(0 if result.wasSuccessful() else 1)
