"""Explicit historical/current identity distinction for the reviewed DA adapter.

This check does not establish behavior. Its separately executed native and
failure tests do that. No mutable allowlist or automatic pin refresh is used.
"""
import json
from fusion.contracts import digest, require


def owner_extension(root, name, historical_digest, selected_bytes):
    if name == 'fusion/policy.py':
        return policy(root, historical_digest, selected_bytes)
    manifest = json.loads((root/'integration/neoclaw/provenance/owner-extensions.json').read_bytes())
    entry = manifest['files'].get(name)
    if entry is None:
        return historical_digest
    historical = (root/entry['historical']['path']).read_bytes()
    require(digest(historical) == historical_digest == entry['historical']['sha256'], 'CONFLICT')
    require(digest(selected_bytes) == entry['selected']['sha256'], 'CONFLICT')
    return entry['selected']['sha256']


def policy(root, historical_digest, selected_bytes=None):
    manifest = json.loads((root/'integration/neoclaw/provenance/policy.json').read_bytes())
    historical = (root/manifest['historical']['path']).read_bytes()
    selected = selected_bytes if selected_bytes is not None else (root/manifest['selected']['path']).read_bytes()
    require(digest(historical) == historical_digest == manifest['historical']['sha256'], 'CONFLICT')
    require(digest(selected) == manifest['selected']['sha256'], 'CONFLICT')
    expected = historical.replace(
        b'        methods = self.current()["principals"].get(principal, {}).get("scopes", {}).get(scope, [])\n',
        b'        current = self.current()\n'
        b"        if 'writer_fence' in current:\n"
        b'            from .pilot_writer_fence import check\n'
        b"            check(current, 'writer.request')\n"
        b'        methods = current["principals"].get(principal, {}).get("scopes", {}).get(scope, [])\n')
    require(selected == expected, 'CONFLICT')
    return manifest['selected']['sha256']


def detta(root, historical_digest, selected_bytes=None):
    manifest = json.loads((root/'integration/neoclaw/provenance/detta.json').read_bytes())
    historical = (root/manifest['historical']['path']).read_bytes()
    selected = selected_bytes if selected_bytes is not None else (root/manifest['selected']['path']).read_bytes()
    require(digest(historical) == historical_digest == manifest['historical']['sha256'], 'CONFLICT')
    require(digest(selected) == manifest['selected']['sha256'], 'CONFLICT')
    # The entire reviewed delta, not an unrestricted AST exclusion. This also
    # rejects weakening the inherited owner lock while refreshing a pin alone.
    expected = historical.replace(b'def __init__(self, binary: str, root: str):',
        b'def __init__(self, binary: str, root: str, *, owner_fds=()):').replace(
        b'        self.binary, self.root = binary, root\n',
        b'        self.binary, self.root = binary, root\n        self.owner_fds = tuple(owner_fds)\n').replace(
        b'pass_fds=(lock.fileno(),)', b'pass_fds=(lock.fileno(), *self.owner_fds)')
    require(selected == expected, 'CONFLICT')
    return manifest['selected']['sha256']
