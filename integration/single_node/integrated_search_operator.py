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
    require(type(body) is dict and set(body) in ({'scope','operation','args'}, {'profile','scope','operation','args'}))
    client_type,operations,profile,selected_descriptor=Client,OPS,PROFILE,descriptor
    if 'profile' in body:
        from fusion.pilot_search_maintenance import Client as CleanupClient, OPS as CLEANUP_OPS, descriptor as cleanup_descriptor
        from fusion.pilot_search_cleanup import PROFILE as CLEANUP
        require(body['profile']==CLEANUP,'UNSUPPORTED_PROFILE')
        client_type,operations,profile,selected_descriptor=CleanupClient,CLEANUP_OPS,CLEANUP,cleanup_descriptor
    require(body['operation'] in operations and type(body['args']) is list)
    settings=json.loads(Path(component).read_bytes());cfg=json.loads(Path(owner).read_bytes())
    require(settings['role']=='fusion-search','UNSUPPORTED_OPERATION')
    scopes={settings['preview']['scope'],*cfg.get('scope_routes',{}).get('scopes',{})}
    require(body['scope'] in scopes,'UNAUTHORIZED')
    secret=Path(settings.get('secret_directory','/secrets'))
    client=client_type(dict(profile=profile,scope=body['scope'],descriptor=descriptor_wire(selected_descriptor()),placement='network',fallback=False,
        principal='search-operator',credential=(secret/'search-operator-token').read_text().strip(),
        endpoint=dict(host=settings['peers']['fusion-search'],port=settings['https_port'],ca_file=str(secret/'ca.crt'))))
    return client.call(body['operation'],*body['args'])
