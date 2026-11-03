"""Explicit /2 feed selections in trusted fresh-state configuration only."""
import json
from dataclasses import replace
from fusion import lookup_contracts as c
from fusion.contracts import require
from fusion.registry import descriptor_read,descriptor_wire
from fusion.sustained_feed import capacity_policy
from .configure import write


def configure(settings,cfg,state,run):
    selected=settings['preview']['sustained'].get('feed_capacity')
    if selected is None:return cfg
    require(type(selected) is dict and set(selected)=={'profile','records','bytes'},'UNSUPPORTED_PROFILE')
    p=settings['preview'];scopes=[p['scope'],*[a['private_scope'] for a in p['agents'].values() if 'private_scope' in a]]
    policy=capacity_policy(dict(selected,scopes=scopes))
    def transform(value):
        if type(value) is list:return [transform(x) for x in value]
        if type(value) is not dict:return value
        if 'interface' in value and 'provider' in value and 'profiles' in value:
            d=descriptor_read(value)
            if d.interface=='atom.storage' and c.FEED in d.profiles:
                operations=d.operations|({'capacity','observe'} if d.provider=='synthetic-atom.storage' else set())
                return descriptor_wire(replace(d,profiles=(d.profiles-{c.FEED})|{c.SUSTAINED_FEED},operations=frozenset(operations)))
            return value
        result={k:transform(v) for k,v in value.items()}
        if type(result.get('catalogue')) is list and any(d['interface']=='atom.storage' and c.SUSTAINED_FEED in d['profiles'] for d in result['catalogue']):result['feed_profile']=c.SUSTAINED_FEED
        if 'descriptor' in result and type(result['descriptor']) is dict and result['descriptor'].get('interface')=='atom.storage' and c.SUSTAINED_FEED in result['descriptor']['profiles']:result['feed_profile']=c.SUSTAINED_FEED
        if 'providers' in result and any(d['interface']=='atom.storage' and c.SUSTAINED_FEED in d['profiles'] for d in result['providers']):result['source_profile']=c.SUSTAINED_FEED
        if settings['role']=='fusion-storage':
            if 'root' in result and result.get('feed_profile')==c.SUSTAINED_FEED:result['feed_capacity']=policy
            # Grant only to already scoped payload readers, never new actors or
            # newly reachable scopes. No private totals are mixed into replies.
            principals=result.get('principals',{})
            for principal in (principals.values() if type(principals) is dict else ()):
                for methods in principal.get('scopes',{}).values():
                    if 'atom.storage.head' in methods:
                        for op in ('capacity','observe'):
                            if 'atom.storage.'+op not in methods:methods.append('atom.storage.'+op)
        return result
    for file in run.rglob('*.json'):
        value=json.loads(file.read_bytes());write(file,transform(value))
    return transform(cfg)
