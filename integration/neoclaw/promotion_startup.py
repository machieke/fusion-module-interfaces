"""S05 only checked native state seams. Native sorting/uniqueness/rendering retained."""
from .memory_oracle import function
from .startup_overlay import replace_once


def extend(source,omega):
    source=replace_once(source,function(omega,'get-promotion'),'''(= (get-promotion $current_time $uuid)
    (py-call (loop_bridge.priority_score $current_time $uuid)))''')
    source=replace_once(source,'(= (best-promoted-memories) "")','(= (mostPromotedMemories) 10)')
    for name,delta in [('promote',1),('demote',-1)]:
        # Parser vocabulary unchanged; resolution and atomic effect replace legacy helper writes.
        function(omega,name)
        source+='\n(= ('+name+' $time) (py-call (loop_bridge.priority_adjust $time '+str(delta)+')))\n'
    source+='''
(= (best-promoted-memory-ids) (py-call (loop_bridge.context_ids)))
(= (best-promoted-memories)
    (if (py-call (loop_bridge.context_captured))
        (py-call (loop_bridge.context_replay))
        (py-call (loop_bridge.context_capture (render-promoted-memories)))))
'''
    render=function(omega,'best-promoted-memories')
    render=replace_once(render,'(best-promoted-memories)','(render-promoted-memories)')
    render=replace_once(render,'lib_chromadb.query_by_ids','loop_bridge.context_payloads')
    render=replace_once(render,'(write-file ./repos/mettaclaw/memory/promoted_memories.metta "")','True')
    render=replace_once(render,'(append-file ./repos/mettaclaw/memory/promoted_memories.metta (repr ($t $c)))',
        '(py-call (loop_bridge.promoted_line (repr ($t $c))))')
    return source+'\n'+render


def select_context(app):
    import lib_chromadb
    from fusion.adapters.neoclaw_metadata import collection
    row=app.priority.context();view=app.priority.view(row['view']);cfg,_=app.write.settings()
    lib_chromadb.COLLECTION=app.evidence.projection(view) if view.get('beliefs') else collection(cfg['metadata_root'],view['metadata'])
