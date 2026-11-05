"""Provision distinct scoped browser actors in the existing native owner policy.

Called by trusted composition after the sustained owner is configured. Browser
settings are non-secret; each credential is a separately referenced Secret key.
This never copies the broad operator credential or grants a live model action.
"""
from pathlib import Path
from fusion.contracts import require

READ = ('observe','disclose','binding')
DEVELOP = ('allocate','submit','pause','resume','close','archive','cancel','reconcile')


def configure(settings, cfg, secret_directory):
    selected=settings.get('pilot_browser')
    if selected is None:return
    require(type(selected) is dict and set(selected)=={'profile','users'}, 'INVALID_ARGUMENT')
    require(selected['profile']=='synthetic-browser-sessions/1', 'UNSUPPORTED_PROFILE')
    require(type(selected['users']) is dict and 1<=len(selected['users'])<=16)
    require('native_sessions' in cfg and cfg['native_sessions']['profile']=='omega-native-sessions/3', 'UNSUPPORTED_PROFILE')
    templates=cfg['native_sessions']['allocation']['templates'];allowed_scopes={x['scope'] for x in templates.values()}
    for user,record in selected['users'].items():
        import re
        require(type(user) is str and re.fullmatch('[a-z][a-z0-9-]{0,31}',user))
        require(type(record) is dict and set(record)=={'role','scopes','credential_key'})
        require(record['role'] in ('viewer','developer','operator') and type(record['scopes']) is list and 1<=len(record['scopes'])<=8)
        require(all(type(s) is str and s.startswith('synthetic-') for s in record['scopes']), 'UNAUTHORIZED')
        scopes=set(record['scopes'])&allowed_scopes
        if not scopes:continue
        require(type(record['credential_key']) is str and re.fullmatch('browser-[a-z0-9-]+-token',record['credential_key']))
        path=Path(secret_directory)/record['credential_key'];require(path.is_file() and path.stat().st_size<=257, 'UNAUTHORIZED')
        credential=path.read_text().strip();require(32<=len(credential)<=256 and credential.isascii(), 'UNAUTHORIZED')
        require(all(value['credential']!=credential for name,value in cfg['principals'].items() if name!='browser-'+user), 'UNAUTHORIZED')
        methods=['sessions.'+op for op in READ+(DEVELOP if record['role']!='viewer' else ())]
        # Registry-enabled capability inspection follows this session's exact
        # provider bindings. Allocation additionally selects already trusted
        # providers from the configured template; neither operation manages
        # providers or extends the user's selected application scope.
        methods.append('providers.inspect')
        if record['role']!='viewer':methods.append('providers.select')
        if record['role']=='operator':
            methods.extend(('providers.seal','sessions.workflows-observe','sessions.workflows-decide'))
        cfg['principals']['browser-'+user]=dict(credential=credential,scopes={scope:methods for scope in sorted(scopes)})


def configure_search(settings,cfg,secret_directory):
    """Distinct Search maintenance credential; no payload/read/write authority."""
    selected=settings.get('pilot_browser')
    if selected is None:return
    require(selected['profile']=='synthetic-browser-sessions/1' and 'active_memory' in cfg,'UNSUPPORTED_PROFILE')
    from fusion.pilot_search_cleanup import PROFILE as cleanup_profile
    require(cfg['active_memory'].get('cleanup_profile')==cleanup_profile,'UNSUPPORTED_PROFILE')
    scope=cfg['active_memory']['scope']
    for user,record in selected['users'].items():
        if record['role']!='operator' or scope not in record['scopes']:continue
        import re
        require(re.fullmatch('[a-z][a-z0-9-]{0,31}',user) and scope.startswith('synthetic-'),'UNAUTHORIZED')
        path=Path(secret_directory)/('browser-'+user+'-search-token')
        require(path.is_file() and path.stat().st_size<=257,'UNAUTHORIZED')
        credential=path.read_text().strip();require(32<=len(credential)<=256 and credential.isascii(),'UNAUTHORIZED')
        require(all(value['credential']!=credential for name,value in cfg['principals'].items() if name!='browser-'+user),'UNAUTHORIZED')
        cfg['principals']['browser-'+user]=dict(credential=credential,scopes={scope:[
            'search.maintenance.'+op for op in ('planCleanup','applyCleanup','observeCleanup')]})
