"""Explicit plan/apply/observe through the Search owner's HTTPS port.

Runs inside the operator-selected Search pod. The secret is local to this owner;
no agent receives maintenance permission. Only the closed request reaches the
service. This client never opens a provider journal or chooses a deadline.
"""
import json
from pathlib import Path
from fusion.contracts import require
from fusion.registry import descriptor_wire
from fusion.search_maintenance import Client,OPS
from fusion.search_repair import PROFILE,descriptor


def request(body,component='/config/component.json',owner='/run/fusion/owner.json'):
    require(type(body) is dict and set(body)=={'scope','operation','args'})
    require(body['operation'] in OPS and type(body['args']) is list)
    settings=json.loads(Path(component).read_bytes());cfg=json.loads(Path(owner).read_bytes())
    require(settings['role']=='fusion-search','UNSUPPORTED_OPERATION')
    scopes={settings['preview']['scope'],*cfg.get('scope_routes',{}).get('scopes',{})}
    require(body['scope'] in scopes,'UNAUTHORIZED')
    secret=Path(settings.get('secret_directory','/secrets'))
    client=Client(dict(profile=PROFILE,scope=body['scope'],descriptor=descriptor_wire(descriptor()),placement='network',fallback=False,
        principal='search-operator',credential=(secret/'search-operator-token').read_text().strip(),
        endpoint=dict(host=settings['peers']['fusion-search'],port=settings['https_port'],ca_file=str(secret/'ca.crt'))))
    return client.call(body['operation'],*body['args'])
