"""Disposable S01.1 operator recipe, with declared external model/channel fixtures.

No numerical fixture. Starts bounded worker and verified loopback HTTPS as needed,
then the supported native-loop launcher. Tracks and stops only its own processes.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys

from fusion.contracts import canonical
from tests.neoclaw_support import Harness, ROOT, RUNTIME, COMMAND, GOLDEN


class ControlledRun:
    def __init__(self, placement='network', responses=None, expected=None, capacity=8):
        self.h = Harness(real=True, capacity=capacity)  # Generated credentials/state only.
        self.processes = []
        self.logs = []
        if placement == 'network': self.h.network()
        self.h.client.pop('request_id'); self.h.client.pop('deadline_ms'); self.h.save_client()
        root = self.h.caller_root
        self.app_path = root/'application.json'
        self.model_path = root/'model.json'
        self.app = dict(composition='controlled-native-loop/1', runtime=str(RUNTIME),
            caller_config=str(self.h.client_path), turn_limit=len(responses or [COMMAND, '']),
            invocation_timeout_ms=30000, model_fixture=str(self.model_path), workdir=str(root/'native'),
            status_file=str(root/'status.json'), test_failpoints=True, failpoint_marker=str(root/'pause.json'),
            denied_paths=[str(self.h.server_root), str(Path.home()/'work/takopi/mettaclaw')] if placement == 'network' else [])
        self.model = dict(responses=responses or [COMMAND, ''], expected_feedback=expected or {'1': [[GOLDEN, 1]]},
                          log=str(root/'model.jsonl'))
        self.save()

    def save(self):
        self.app_path.write_bytes(canonical(self.app)); self.app_path.chmod(0o600)
        self.model_path.write_bytes(canonical(self.model)); self.model_path.chmod(0o600)

    def spawn(self, module, args, name):
        log = open(self.h.root/(name+'.log'), 'a')
        self.logs.append(log)
        process = subprocess.Popen([sys.executable, '-m', module, *map(str,args)], cwd=ROOT,
                                   stdout=log, stderr=log, start_new_session=True)
        self.processes.append(process)
        return process

    def operator(self):
        ready = self.h.server_root/'operator-ready.json'
        process = self.spawn('integration.neoclaw.operator', [self.h.config_path, '--ready', ready, '--seconds', '120'], 'operator')
        self.h.wait_file(ready, process)
        assert json.loads(ready.read_text())['pid'] == process.pid
        return process

    def start(self):
        Path(self.app['status_file']).unlink(missing_ok=True)
        return self.spawn('integration.neoclaw.native_loop', [self.app_path], 'native')

    def finish(self, process):
        code = process.wait(timeout=40)
        path = Path(self.app['status_file'])
        return code, json.loads(path.read_text()) if path.exists() else None

    def observations(self):
        path = Path(self.model['log'])
        return [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []

    def rows(self, table):
        assert table in ('app_session', 'app_turns', 'app_occurrences', 'caller_requests')
        with sqlite3.connect(self.h.client['database']) as db:
            db.row_factory = sqlite3.Row
            return [dict(x) for x in db.execute('SELECT * FROM '+table+' ORDER BY rowid')]

    def report(self):
        return dict(placement=self.h.client['placement'], same_host=True,
                    counts=self.h.counts(), occurrences=self.rows('app_occurrences'),
                    requests=[{k:json.loads(v) if k in ('request','receipt','selections') and v else v
                               for k,v in row.items()} for row in self.rows('caller_requests')],
                    turns=self.rows('app_turns'), observations=self.observations(),
                    startup=json.loads((Path(self.app['workdir'])/'startup.json').read_text()),
                    operator_configuration_edits_between_calls=0,
                    lifecycle={name:json.loads((self.h.server_root/file).read_text())
                               for name,file in (('https','ready.json'),('worker','operator-ready.json'))
                               if (self.h.server_root/file).exists()})

    def kill(self, process):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)

    def close(self):
        for process in self.processes:
            self.kill(process)
        for log in self.logs: log.close()
        self.h.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placement', choices=['local','network'], default='network')
    parser.add_argument('--evidence', required=True)
    args = parser.parse_args()
    changed = 'metta (Truth_Deduction (stv 0.6 0.9) (stv 0.7 0.8))'
    run = ControlledRun(args.placement, [COMMAND, changed, COMMAND, COMMAND+'\n'+COMMAND, 'metta (+ 1 2)', ''],
        {'1': [[GOLDEN,1]], '2': [['(stv 0.42 0.3024)',1]], '3': [[GOLDEN,1]], '4': [[GOLDEN,2]], '5': [[' 3)',1]]})
    try:
        run.operator()
        code, status = run.finish(run.start())
        if code != 0 or status != dict(status='BOUNDED_STOP'):
            Path(args.evidence+'.failure.log').write_text((run.h.root/'native.log').read_text())
            raise RuntimeError('native loop failed; see evidence failure log')
        Path(args.evidence).write_bytes(canonical(run.report()))
    finally: run.close()


if __name__ == '__main__': main()
