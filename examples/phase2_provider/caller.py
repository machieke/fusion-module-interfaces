"""Adapted caller example: inject a port; application code has no placement branch."""
from fusion.ports import Mutation
from fusion.responses import envelope


def save_and_consume(atoms, scope, occurrence, content):
    """Persist occurrence before calling; retry only this same semantic mutation."""
    written = atoms.create(Mutation(scope, occurrence), 'application/synthetic', content)
    item = atoms.get(written['ref'])
    envelope(item, written['ref'])
    return {'ref': item.ref, 'content': item.bytes.decode('utf-8')}
