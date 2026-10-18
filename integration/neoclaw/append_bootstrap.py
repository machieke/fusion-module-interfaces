"""Native compatibility hooks for generated metadata and creation-time selection."""
from fusion.contracts import digest,canonical,require
from fusion.adapters.neoclaw_metadata import collection


def creation_clock(observed):
    from .memory_bootstrap import _config
    fixture=_config.get('creation_clock_fixture')
    return observed if fixture is None else fixture


def select_view(application):
    import lib_chromadb
    row=application.memory.current();view=application.write.view_for(row)
    require(digest(canonical(view['metadata']))==view['metadata_seal'],'CONFLICT')
    cfg,_=application.write.settings()
    if getattr(application,'evidence_enabled',False) and view.get('beliefs'):
        lib_chromadb.COLLECTION=application.evidence.projection(view)
    else:lib_chromadb.COLLECTION=collection(cfg['metadata_root'],view['metadata'])
