"""Trusted shared-scope task routing into durably allocated native sessions."""
import json
from pathlib import Path
from fusion.contracts import require
from .configure import write

PROFILE='allocated-native-task-routing/1'

def configure(settings,cfg,state,run):
    p=settings['preview']
    if not p.get('tasks',{}).get('enabled'):return
    role=settings['role'];secret=Path(settings.get('secret_directory','/secrets'))
    def token(name):
        value=(secret/name).read_text().strip();require(32<=len(value)<=256,'UNAUTHORIZED');return value
    if role=='fusion-messaging':
        file=run/'task-owner.json';value=json.loads(file.read_bytes())
        value['session_authority']=dict(profile=PROFILE,principals={a['principal']:dict(
            endpoint=dict(host=settings['peers'][name],port=settings['https_port'],ca_file=str(secret/'ca.crt')),
            credential=token('task-binding-'+a['principal']+'-token')) for name,a in p['agents'].items()})
        value.pop('sessions');write(file,value)
    elif role in p['agents']:
        cfg['principals']['task-router']=dict(credential=token('task-binding-token'),scopes={p['scope']:['sessions.binding']})
        cfg['task_ingress'].update(allocation_profile=PROFILE,template='shared')
        cfg['task_ingress'].pop('session')
