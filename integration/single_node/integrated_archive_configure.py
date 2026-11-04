"""Select the existing storage owner's optional archive for fresh state only."""
import json
from pathlib import Path
from fusion import archive_contracts as a,cognitive_services as c
from fusion.contracts import require
from fusion.registry import descriptor_wire
from .configure import write

def configure(settings,cfg,state,run):
    selected=settings['preview']['sustained'].get('storage_archive')
    if selected is None:return cfg
    selected=a.policy(selected)
    if settings['role']!='fusion-storage':return cfg
    # Every protocol implemented by this same owner must select the same feed
    # format. Consumers receive no backend paths or archive-write authority.
    for name in ('memory_read','memory_append'):
        if name in cfg:cfg[name]['archive']=selected
    file=run/'cognitive-owner.json';require(file.is_file(),'NOT_AVAILABLE')
    owned=json.loads(file.read_bytes());owned['archive']=selected
    owned['catalogue']=[descriptor_wire(d) for d in c.descriptors(owned.get('attention_provider','sqlite'),owned.get('feed_profile','immutable-commit-feed/1'),archive=True)]
    secret=Path(settings.get('secret_directory','/secrets'))/'archive-operator-token'
    token=secret.read_text().strip();require(token.isascii() and 32<=len(token)<=256,'UNAUTHORIZED')
    scope=settings['preview']['scope']
    owned['actors']['archive-operator']='archive-operator'
    owned['principals']['archive-operator']=dict(credential=token,scopes={scope:['atom.storage.'+op for op in (*a.OPERATIONS,'get','getMany','availability','head','readCommits')]})
    write(file,owned)
    return cfg
