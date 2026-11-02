"""Fresh single-agent composition using the existing preview values/profile.

Run from the verified public source archive with:
  python -m examples.preview_single_agent_values --images IMAGES --scope SCOPE
      --mode minimal --output NEW_VALUES

Only selection changes: A keeps its own sessions/private synthetic scope and
the existing owners. Two-agent handoff, its derived-artifact inspection and
chain are not selected. No runtime, provider, credential or journal is opened.
"""
import argparse
import json
from pathlib import Path

from fusion.contracts import require
from integration.single_node.preview_values import generate as existing_generate


def generate(manifest, scope, *, mode='minimal'):
    values = existing_generate(manifest, scope, mode=mode)
    preview = values['preview']
    del preview['agents']['omega-agent-b']
    values['components']['omega-agent-b']['enabled'] = False
    agent = preview['agents']['omega-agent']
    agent['tools'] = [name for name in agent['tools'] if name not in ('delegate', 'inspect-atom')]
    sessions = set(agent['sessions'])
    preview['responses'] = {key: value for key, value in preview['responses'].items()
                            if key.partition('/')[0] in sessions}
    preview['tasks'] = {'enabled': False}
    preview['inspection'] = {'enabled': False}
    return values


def main():
    import yaml
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', required=True)
    parser.add_argument('--scope', required=True)
    parser.add_argument('--mode', choices=('minimal', 'memory', 'combined'), default='minimal')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    destination = Path(args.output)
    require(not destination.exists(), 'CONFLICT')
    values = generate(json.loads(Path(args.images).read_text()), args.scope, mode=args.mode)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('x') as file:
        yaml.safe_dump(values, file, sort_keys=False)


if __name__ == '__main__':
    main()
