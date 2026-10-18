"""Read-only compatibility projection. Authority remains at local C1/C2 ports."""
from ..contracts import require
from .neoclaw_metadata import expected


class Projection:
    def __init__(self,manifest):self.records=expected(manifest)
    def get(self,*,ids,include):
        require(include==['metadatas'],'UNAUTHORIZED')
        require(all(x in self.records for x in ids),'NOT_AVAILABLE')
        return dict(ids=list(ids),metadatas=[dict(self.records[x]) for x in ids])
    def __getattr__(self,name):raise RuntimeError('BELIEF_PROJECTION_READ_ONLY')
