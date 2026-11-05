"""Fresh synthetic deployment authority, outside every imported owner PVC.

Called only by the existing fresh-namespace Secret installer. Later authority
transitions use planned handover; an upgrade cannot recreate generation one.
"""
from fusion.contracts import require
from fusion.pilot_writer_fence import selection


def initial(namespace,preview):
    selected=preview.get('pilot',{}).get('writer_fence')
    if selected is None:return None
    selected=selection(selected,deployed=True)
    require(namespace.startswith('omega-ref-pilot-') and selected['deployment']==namespace and selected['generation']==1,'UNAUTHORIZED')
    return dict(profile=selected['profile'],synthetic_only=True,deployment=namespace,incarnation=selected['incarnation'],
        generation=1,state='active',allowed_methods=['writer.start','writer.request'],history=[],handover=None)
