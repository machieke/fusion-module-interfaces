"""Existing Chroma engine with an authoritative lifecycle-bound active set.

Membership is applied before indexing/ranking. Retained generations and
captured results are never rewritten. Current withdrawal authority is checked
before releasing a hit from an older view.
"""
from .chroma_vector import ChromaVector
from .. import preview_vector_contracts as c
from ..contracts import canonical, digest, require


class ActiveChroma(ChromaVector):
    def __init__(self, root, atoms, source, access, scope, corpus, embedding, lifecycle, lifecycle_head, hook=lambda _: None):
        self.lifecycle = lifecycle
        self.membership = lifecycle.activeSet(lifecycle_head)
        require(self.membership['at'] == lifecycle_head, 'NOT_AVAILABLE')
        self.active = {x['uuid']: x for x in self.membership['active']}
        require(len(self.active) == len(self.membership['active']), 'CONFLICT')
        super().__init__(root, atoms, source, access, scope, corpus, embedding, hook, contracts=c)

    def _hydrate_commit(self,entry):
        # The authenticated authoritative feed already binds type/ref/size.
        # Read every feed page, hydrate only enrollment records for this profile;
        # administrative history bodies are not indexing source payloads.
        return entry['content_type']==self.c.ENROLLMENT

    def _eligible(self, enrolled, enrollment_ref):
        value = self.active.get(enrolled['uuid'])
        if value is None: return False
        require(value['payload'] == enrolled['payload'] and value['enrollment'] == enrollment_ref, 'CONFLICT')
        return True

    def _complete_membership(self, records):
        require({x['uuid'] for x in records} == self.active.keys(), 'NOT_AVAILABLE')

    def _snapshot_extension(self):
        return dict(lifecycle=self.membership['at'], active_digest=digest(canonical(self.membership)))

    def _select_current(self, current, snapshot):
        if current is None: return True
        require(current['lifecycle']['source'] == snapshot['lifecycle']['source'], 'CONFLICT')
        return (snapshot['head']['sequence'] >= current['head']['sequence'] and
                snapshot['lifecycle']['sequence'] >= current['lifecycle']['sequence'])

    def _verified(self, generation, through):
        value = super()._verified(generation, through)
        require(all(value['snapshot'][k] == v for k, v in self._snapshot_extension().items()), 'CONFLICT')
        self._complete_membership(value['records'])
        return value

    def query(self, request):
        value = super().query(request)
        require(all(value['snapshot'][k] == v for k, v in self._snapshot_extension().items()), 'CONFLICT')
        for hit in value['hits']:
            member = self.active[hit['uuid']]
            self.lifecycle.disclose(member['logical_id'], {k: member[k] for k in ('uuid', 'payload', 'enrollment')}, self.membership['at'])
        return value
