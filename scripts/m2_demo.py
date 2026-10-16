"""Deterministic generated C1/C2 story with real local providers. No publication."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests.m2_support import MemoryHarness, SCOPE
from integration.m2_scenario import run_generated


def main(environment, output):
    config = json.loads(environment.read_text())
    os.environ.update({k: config[k] for k in ('M2_DETTA_BINARY', 'M2_REVISION_ENV')})
    h = MemoryHarness(real=True)
    try:
        a = run_generated(h.modules, SCOPE, 'generated-demo-2026', 12)
        h.reopen()
        b = run_generated(h.modules, SCOPE, 'generated-demo-2026', 12)
        assert a == b
        # Export ONLY generated test summaries, never the private history itself.
        report = {'scenario': 'generated fixture, real DeTTa and native PLN; this CLI is not the Hive gate',
            'story_events': len(a['story_snapshot']['observations']),
            'story_decisions': [d['numerical'] for d in a['story_decisions']],
            'retained_alternatives': len(a['story_snapshot']['alternatives']),
            'independent_observations': len(a['revision']['snapshot']['observations']),
            'native_revision': a['revision']['snapshot']['truth'],
            'ancestor_outcome': a['ancestor']['numerical'], 'restart_exact_results': a == b}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally: h.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('environment', type=Path); parser.add_argument('output', type=Path)
    args = parser.parse_args(); main(args.environment, args.output)
