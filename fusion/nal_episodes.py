"""S04 C1 source identity and bounded append policy on the existing episode owner."""
from contextlib import closing
import json
import time
from .episodes import EpisodeOwner
from . import nal_memory_contracts as c
from .contracts import canonical,digest,require


class NalEpisodeOwner(EpisodeOwner):
    def __init__(self,*args,**kwargs):super().__init__(*args,contracts=c,**kwargs)

    @c.boundary
    def appendEvent(self,command,episode,expected_sequence,event):
        episode,event=c.detached(episode),c.detached(event)
        c.event(event,command.scope_ref)
        # The historical owner allows another request key to observe an existing
        # occurrence. S04 binds issuance to this key, including receipt replay.
        # Time guards still apply only to new effects, not committed observation.
        require(event['occurrence_id']==self.occurrenceIdentity(command,episode),'CONFLICT')
        return super().appendEvent(command,episode,expected_sequence,event)

    @c.boundary
    def occurrenceIdentity(self,command,episode):
        c.mutation(command); c.episode_ref(episode,command.scope_ref)
        principal=self.access.authorize(command.scope_ref,'occurrenceIdentity')
        with closing(self._connect()) as db:self._episode(db,episode,principal)
        return 'source-occurrence/'+digest(canonical([principal,episode,command.idempotency_key]))

    @c.boundary
    def readOccurrence(self,episode,occurrence):
        c.episode_ref(episode);c.identifier(occurrence)
        principal=self.access.authorize(episode['scope_ref'],'readOccurrence')
        with closing(self._connect()) as db:
            self._episode(db,episode,principal)
            row=db.execute('SELECT record,receipt FROM events WHERE episode=? AND occurrence=?',(episode['id'],occurrence)).fetchone()
            if row is None:return None
            record=json.loads(row['record']);self._record(db,record['evidence'],principal)
            return dict(record=record,receipt=json.loads(row['receipt']))

    def _append_guard(self,command,episode,event):
        require(event['occurrence_id']==self.occurrenceIdentity(command,episode),'CONFLICT')
        require(time.time_ns()//1_000_000<=event['deadline_ms'],'DEADLINE_EXCEEDED')

    def _origin(self,command,event):
        # Only new, authorized observations mint roots. Assessment action and copy
        # provenance always inherit roots; a new credential/label is insufficient.
        if event['kind']!='observation':return None
        origin=self.access.origin(command.scope_ref,event['source'])
        if origin is None:return None
        return digest(canonical([command.scope_ref,origin,event['occurrence_id']]))
