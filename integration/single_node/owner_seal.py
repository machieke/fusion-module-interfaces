"""Exact startup/restore identity for the existing single-writer PVC owner."""
from fusion.contracts import require
from fusion import neoclaw_contracts as c


def selected(settings):
    role=settings['role'];preview=settings.get('preview',{});sustained=preview.get('sustained',{})
    value=dict(composition=settings['service_composition'],role=role,
        scope=preview.get('scope',settings.get('reference',{}).get('scope',settings.get('memory',{}).get('scope',c.SCOPE))))
    envelope=preview.get('inspection',{}).get('envelopes')
    if envelope and (role in preview.get('agents',{}) or role in ('fusion-execution','fusion-messaging')):
        from fusion.execution_envelope import PROFILE
        require(envelope==PROFILE,'UNSUPPORTED_PROFILE');value['execution_envelope']=envelope
    nal=preview.get('inspection',{}).get('nal_envelopes')
    if nal and (role in preview.get('agents',{}) or role=='fusion-execution'):
        from fusion.nal_envelope import PROFILE
        require(nal==PROFILE,'UNSUPPORTED_PROFILE');value['nal_execution_envelope']=nal
    maintenance=preview.get('memory',{}).get('maintenance_profile')
    if maintenance and role=='fusion-search':
        from fusion.search_repair import PROFILE
        require(maintenance==PROFILE,'UNSUPPORTED_PROFILE');value['search_maintenance']=maintenance
    if role in preview.get('agents',{}):
        continuation=preview.get('chain',{}).get('continuation')
        if continuation:
            from fusion.chain_continuation import PROFILE
            require(continuation==PROFILE,'UNSUPPORTED_PROFILE');value['chain_continuation']=continuation
        if sustained.get('resident_worker'):
            from fusion.resident_workers import selection
            value['resident_worker']=selection(sustained['resident_worker'])
        if sustained.get('history_representation'):
            require(sustained['history_representation']=='immutable-administrative-captures/1','UNSUPPORTED_PROFILE')
            value['history_representation']=sustained['history_representation']
        if sustained.get('provider_registry'):
            require(sustained['provider_registry']['profile']=='trusted-provider-lifecycle/1','UNSUPPORTED_PROFILE')
            value['provider_registry']=sustained['provider_registry']['profile']
    if preview.get('enabled') and role=='fusion-storage':
        from fusion.adapters.detta_layout import LAYOUT
        value['backend_layout']=LAYOUT
        if sustained.get('storage_archive'):
            from fusion.archive_contracts import policy
            value['storage_archive']=policy(sustained['storage_archive'])
    return value
