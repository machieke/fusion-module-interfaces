"""Fresh opt-in pilot features composed into existing single-node owners."""
from fusion.contracts import require
from fusion.service_lanes import Lanes

PROFILE='omega-operator-pilot/1'


def configure(settings,cfg):
    selected=settings.get('preview',{}).get('pilot')
    if selected is None:return
    require(type(selected) is dict and {'profile','capacity','subscriptions','workflows','request_lanes'}<=set(selected)<=
        {'profile','capacity','subscriptions','workflows','request_lanes','browser','derived_cleanup','writer_fence','handover','owner_clock'},'UNSUPPORTED_PROFILE')
    require(selected['profile']==PROFILE and selected['capacity'] is True,'UNSUPPORTED_PROFILE')
    require(type(selected['subscriptions']) is bool and type(selected['workflows']) is bool)
    Lanes(selected['request_lanes'])
    cfg['pilot_capacity']='pilot-owner-headroom/1'
    if 'derived_cleanup' in selected:
        require(type(selected['derived_cleanup']) is bool,'UNSUPPORTED_PROFILE')
        if selected['derived_cleanup'] and settings['role']=='fusion-search':
            from fusion.pilot_search_cleanup import PROFILE as cleanup
            require('active_memory' in cfg and 'search-operator' in cfg['principals'],'UNSUPPORTED_PROFILE')
            cfg['active_memory']['cleanup_profile']=cleanup
            for grants in cfg['principals']['search-operator']['scopes'].values():
                for op in ('planCleanup','applyCleanup','observeCleanup'):
                    method='search.maintenance.'+op
                    if method not in grants:grants.append(method)
    if 'writer_fence' in selected:
        from fusion.pilot_writer_fence import selection
        cfg['writer_fence']=selection(selected['writer_fence'],deployed=True)
    if 'browser' in selected and selected.get('derived_cleanup') and settings['role']=='fusion-search':
        from .pilot_browser_configure import configure_search
        configure_search(dict(pilot_browser=selected['browser']),cfg,settings.get('secret_directory','/secrets'))
    if 'owner_clock' in selected and settings['role']=='fusion-model':
        from fusion.pilot_model_clock import selection
        cfg['model_completion']['owner_clock']=selected['owner_clock']
        selection(cfg['model_completion'])
    if 'native_sessions' not in cfg:return
    if selected.get('derived_cleanup'):
        from .pilot_derived_maintenance import PROFILE as application_cleanup
        cfg['native_sessions']['derived_cleanup']=application_cleanup
        for grants in cfg['principals']['operator']['scopes'].values():
            grants.extend('sessions.derived-'+op for op in ('inventory','plan','apply','observe'))
    if selected['subscriptions']:
        from fusion.pilot_subscriptions import PROFILE as subscriptions
        cfg['native_sessions']['pilot_subscriptions']=subscriptions
    if selected['workflows']:
        cfg['native_sessions']['workflow_profile']='guarded-native-continuation/1'
        for grants in cfg['principals']['operator']['scopes'].values():
            grants.extend('sessions.workflows-'+op for op in ('catalogue','admit','advance','observe','amend','checkpoint','decide'))
    if 'browser' in selected:
        from .pilot_browser_configure import configure as browser
        browser(dict(pilot_browser=selected['browser']),cfg,settings.get('secret_directory','/secrets'))
