"""Declared external-model fixture. It checks received contexts, never supplies results."""
import json
import os
from pathlib import Path


def settings():
    app = json.loads(Path(os.environ['NEOCLAW_S01_APPLICATION']).read_text())
    return json.loads(Path(app['model_fixture']).read_text())


def useClaude(context):
    config = settings()
    log = Path(config['log'])
    previous = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
    index = len(previous)
    if index >= len(config['responses']):
        raise RuntimeError('MODEL_FIXTURE_EXHAUSTED')
    # Exact observation assertions, separate from response generation. Strip other
    # context sections so command/history text cannot satisfy a result assertion.
    feedback = context.split('LAST_SKILL_USE_RESULTS: ', 1)[1].split(' HISTORY:', 1)[0]
    for value, count in config.get('expected_feedback', {}).get(str(index), []):
        if feedback.count(value) != count:
            raise RuntimeError('MODEL_FIXTURE_CONTEXT_MISMATCH')
    with log.open('a') as stream:
        stream.write(json.dumps(dict(index=index, context=context, feedback=feedback))+'\n')
    return config['responses'][index]


def memory_init(): return True
def history_noop(): return True
