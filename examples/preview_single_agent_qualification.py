"""Six operator inputs; the existing native service performs every tool.

Run from the verified public source archive after installing fresh single-agent
minimal values. Authored input-command proposals remain explicit fixtures in
the deployed ModelInference owner. This observer never contacts a generative
runtime, invokes tools itself, edits configuration, retries submission or
changes an accepted deadline. A failed/uncertain run is retained and stops.
"""
import argparse
import json
import os
from pathlib import Path
import time
import uuid

from fusion.contracts import canonical, digest, require
from integration.single_node.reference_ops import Operator, PYTHON


COMMANDS = (
    'metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))',
    'pin task Synthetic solo task note',
    'task-context',
    'pin detail Synthetic solo detail note',
    'unpin task',
    'task-context',
)
EXPECTED_ITEMS = (
    None,
    {'task': 'Synthetic solo task note'},
    {'task': 'Synthetic solo task note'},
    {'task': 'Synthetic solo task note', 'detail': 'Synthetic solo detail note'},
    {'detail': 'Synthetic solo detail note'},
    {'detail': 'Synthetic solo detail note'},
)
EXPECTED_REVISIONS = (None, 1, 1, 2, 3, 3)
GOLDEN = '(stv 0.5599999999999999 0.4032)'


class Qualification:
    def __init__(self, operator, values, destination):
        self.op, self.values = operator, values
        self.root = Path(destination)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.end = time.monotonic() + 900
        self.sid = None
        self.report = dict(schema='single-agent-native-qualification/1', status='NOT_RUN',
            namespace=operator.namespace, classification='RECORDED_MODEL_REAL_NATIVE_TOOLS',
            additional_live_generations=0, values_sha256=digest(canonical(values)),
            maximum_operator_inputs=6, maximum_observer_overrun_seconds=8,
            maximum_observation_window_seconds=900, inputs=[],
            recorded_proposal={'proposal': 'input-command'},
            interpretation='Six inputs in one native session, not six workflows; no two-agent or live-model claim')
        self.save()

    def save(self):
        target = self.root/'report.json'
        pending = self.root/'report.json.pending'
        with pending.open('wb') as file:
            os.fchmod(file.fileno(), 0o600)
            file.write(canonical(self.report)+b'\n')
            file.flush()
            os.fsync(file.fileno())
        pending.replace(target)
        directory = os.open(self.root, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def call(self, operation, *args, timeout=35):
        command = [PYTHON, '-m', 'integration.single_node.preview_operator', operation]
        if operation != 'inventory':
            command += ['--session', self.sid]
        return json.loads(self.op.k('exec', 'omega-agent-0', '--', *command, *args, timeout=timeout))

    def setup(self):
        p = self.values['preview']
        require(p['model_boundary'] == 'RECORDED_FIXTURE', 'UNAUTHORIZED')
        require(set(p['agents']) == {'omega-agent'}, 'UNSUPPORTED_PROFILE')
        require(p['agents']['omega-agent']['principal'] == 'A', 'UNAUTHORIZED')
        require(not any(p.get(name, {}).get('enabled') for name in ('memory', 'cognition', 'tasks', 'inspection', 'chain')), 'UNSUPPORTED_PROFILE')
        require(self.values['components']['omega-agent-b']['enabled'] is False, 'UNSUPPORTED_PROFILE')
        require(p['limits'] == dict(inputs=24, pending=4, timeout_ms=120000), 'UNSUPPORTED_PROFILE')
        self.sid = p['agents']['omega-agent']['sessions'][0]
        require(all(p['responses'].get(self.sid+'/'+str(n)) == {'proposal':'input-command'} for n in range(1, 7)), 'UNSUPPORTED_PROFILE')
        self.op.owned()
        self.report['preflight'] = self.op.preflight()
        workloads = self.op.workloads()
        roles = {x['metadata']['name'] for x in workloads}
        require('omega-agent' in roles and 'omega-agent-b' not in roles, 'UNSUPPORTED_PROFILE')
        require(all(x['spec']['replicas'] == 1 for x in workloads), 'CONFLICT')
        self.report['workloads'] = {x['metadata']['name']:dict(uid=x['metadata']['uid'],
            image=x['spec']['template']['spec']['containers'][0]['image']) for x in workloads}
        inventory = self.call('inventory')
        self.report['inventory'] = inventory
        require(inventory['principal'] == 'A' and inventory['scope'] == p['scope'], 'UNAUTHORIZED')
        require(inventory['model_boundary'] == 'RECORDED_FIXTURE' and inventory['additional_live_generations'] == 0, 'UNAUTHORIZED')
        require(set(inventory['sessions']) == set(p['agents']['omega-agent']['sessions']), 'CONFLICT')
        binding = inventory['sessions'][self.sid]
        require(binding['limits'] == p['limits'] and binding['policy'] == p['policy_revision'], 'CONFLICT')
        tools = inventory['catalogues'][self.sid]['tools']
        require({'metta', 'pin', 'unpin', 'task-context'} <= set(tools), 'UNSUPPORTED_OPERATION')
        require('delegate' not in tools and 'inspect-atom' not in tools, 'UNSUPPORTED_PROFILE')
        created = self.call('create')
        self.report['created'] = created
        require(created['state'] == 'active' and created['capacity']['accepted'] == 0 and created['inputs'] == [], 'CONFLICT')
        require(created['binding'] == binding, 'CONFLICT')
        self.report['status'] = 'RUNNING'
        self.save()

    def observe(self, until):
        rows, after = [], 0
        # The public session owner bounds inputs to 32; no unbounded page loop.
        for _ in range(33):
            remaining = until-time.monotonic()
            require(remaining > 0, 'DEADLINE_EXCEEDED')
            page = self.call('observe', '--content', '--after', str(after), timeout=min(35, remaining))
            require(page['session'] == self.sid and page['live_generations'] == 0, 'CONFLICT')
            for row in page['inputs']:
                require(row['sequence'] > after and (not rows or row['sequence'] > rows[-1]['sequence']), 'CONFLICT')
                rows.append(row)
            if page['complete']:
                return rows
            require(page['inputs'] and page['next_after'] == rows[-1]['sequence'] and page['next_after'] > after, 'CONFLICT')
            after = page['next_after']
        require(False, 'OVERLOADED')

    @staticmethod
    def check_projection(index, result):
        require(type(result) is dict and type(result.get('projection')) is str and len(result.get('occurrences', [])) == 1, 'NOT_AVAILABLE')
        projection = result['projection']
        if index == 0:
            require(GOLDEN in projection, 'NOT_AVAILABLE')
            return dict(native_nal_result=GOLDEN)
        text = projection.replace('_quote_', '"')
        require('{' in text, 'NOT_AVAILABLE')
        value = json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
        require(value == dict(profile='working-task-context/1', revision=EXPECTED_REVISIONS[index],
            digest=digest(canonical(EXPECTED_ITEMS[index])), items=EXPECTED_ITEMS[index],
            interpretation='unverified-task-notes'), 'NOT_AVAILABLE')
        return value

    def run(self):
        try:
            self.setup()
            for index, command in enumerate(COMMANDS):
                require(time.monotonic() < self.end, 'DEADLINE_EXCEEDED')
                entry = dict(identity='single-agent-'+str(uuid.uuid4()), command=command,
                    sequence=index+1, started_ms=time.time_ns()//1_000_000)
                self.report['inputs'].append(entry)
                self.save()  # Persist identity before the only submission.
                receipt = self.call('submit', '--identity', entry['identity'], '--text', command,
                    '--assignment', 'synthetic-task')
                entry['accepted'] = receipt
                self.save()
                require(receipt['id'] == entry['identity'] and receipt['session'] == self.sid and
                    receipt['sequence'] == index+1 and receipt['assignment'] == 'synthetic-task', 'CONFLICT')
                require(receipt['deadline']-receipt['accepted'] == 120000, 'CONFLICT')
                until = min(self.end, time.monotonic()+max(0, (receipt['deadline']-time.time_ns()//1_000_000)/1000)+8)
                while True:
                    rows = self.observe(until)
                    matching = [row for row in rows if row['id'] == entry['identity']]
                    require(len(matching) == 1, 'NOT_AVAILABLE')
                    row = matching[0]
                    entry['observed'] = row
                    self.save()
                    require(all(row[key] == receipt[key] for key in ('session', 'id', 'sequence', 'assignment', 'deadline', 'accepted')), 'CONFLICT')
                    if row['state'] == 'complete':
                        break
                    require(time.monotonic() < until, 'DEADLINE_EXCEEDED')
                    time.sleep(min(1, max(0, until-time.monotonic())))
                entry['verified'] = self.check_projection(index, row['result'])
                entry['finished_ms'] = time.time_ns()//1_000_000
                self.save()
            require(len(rows) == 6 and all(row['state'] == 'complete' for row in rows), 'CONFLICT')
            self.report.update(status='PASS', completed_inputs=6,
                native_nal='PASS', native_working_context='PASS', original_receipts_retained=True,
                live_model_workflow='NOT_RUN')
            self.save()
            return self.report
        except Exception as exc:
            self.report.update(status='FAILED', error_code=getattr(exc, 'code', type(exc).__name__),
                automatic_resubmission=False, accepted_effects_and_budgets_retained=True)
            self.save()
            raise


def main():
    import yaml
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig', 'context', 'namespace', 'values', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    values = yaml.safe_load(Path(args.values).read_text())
    report = Qualification(Operator(args.kubeconfig, args.context, args.namespace), values, args.output).run()
    print(json.dumps(dict(status=report['status'], completed_inputs=report['completed_inputs'],
        additional_live_generations=0, report=str(Path(args.output)/'report.json'))))


if __name__ == '__main__':
    main()
