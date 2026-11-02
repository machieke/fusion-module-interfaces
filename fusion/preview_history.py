"""Chronological native history profile on the existing C1 owner transitions.

Administrative history has no numerical assessment, origin root or implicit
independence. Its distinct event-kind wrapper is immutable AtomStorage data.
"""
from contextlib import closing
import json

from .contracts import canonical, digest, require, validate_ref
from .episodes import EpisodeOwner
from . import memory_contracts as c
from .ports import Mutation
from .responses import envelope

PROFILE = 'native-session-history/1'
CONTENT_TYPE = 'application/omega-session-history-v1'
KINDS = {'input-receipt', 'model-proposal', 'command-admitted', 'tool-result', 'external-observation', 'external-effect'}


class SessionHistoryOwner(EpisodeOwner):
    def _origin(self, command, event): return None

    def _append_guard(self, command, episode, event):
        require(event['numerical'] is None and event['provenance'] == [], 'UNSUPPORTED_PROFILE')
        item = self.atoms.get(event['payload'])
        envelope(item, event['payload'])
        require(item.content_type == CONTENT_TYPE, 'UNSUPPORTED_PROFILE')
        body = json.loads(item.bytes)
        require(set(body) == {'profile', 'kind', 'payload'} and body['profile'] == PROFILE)
        require(body['kind'] in KINDS)
        validate_ref(body['payload'], command.scope_ref)
        envelope(self.atoms.get(body['payload']), body['payload'])

    def appendHistory(self, command, episode, expected_head, occurrence, kind, payload, causation, observed_time):
        self.access.authorize(command.scope_ref, 'appendEvent')
        require(kind in KINDS, 'UNSUPPORTED_OPERATION')
        c.mutation(command, episode['scope_ref']); c.identifier(occurrence)
        validate_ref(payload, command.scope_ref)
        envelope(self.atoms.get(payload), payload)
        wrapper = canonical(dict(profile=PROFILE, kind=kind, payload=payload))
        written = self.atoms.create(Mutation(command.scope_ref, 'history-wrapper/'+digest(wrapper)), CONTENT_TYPE, wrapper)
        event = dict(occurrence_id=occurrence, kind='result' if kind in ('tool-result', 'external-observation', 'external-effect') else 'action',
                     source='native-session-history', observed_time=observed_time, payload=written['ref'],
                     causation=causation, provenance=[], numerical=None)
        return self.appendEvent(command, episode, expected_head, event)

    def historySnapshot(self, episode):
        c.episode_ref(episode)
        principal = self.access.authorize(episode['scope_ref'], 'readEpisode')
        with closing(self._connect()) as db:
            head = self._episode(db, episode, principal)['head']
        return dict(profile=PROFILE, episode=episode, through=head, selection=self.access.selection())

    def readHistory(self, snapshot, start, limit):
        require(type(snapshot) is dict and set(snapshot) == {'profile', 'episode', 'through', 'selection'})
        require(snapshot['profile'] == PROFILE and snapshot['selection'] == self.access.selection(), 'UNSUPPORTED_PROFILE')
        episode = snapshot['episode']; c.episode_ref(episode)
        c.integer(snapshot['through'], 0, c.MAX_EVENTS); c.integer(start, 1, snapshot['through']+1)
        c.integer(limit, 1, c.MAX_PAGE)
        principal = self.access.authorize(episode['scope_ref'], 'readEpisode')
        with closing(self._connect()) as db:
            db.execute('BEGIN')
            require(snapshot['through'] <= self._episode(db, episode, principal)['head'], 'NOT_AVAILABLE')
            rows = db.execute('SELECT record FROM events WHERE episode=? AND sequence>=? AND sequence<=? ORDER BY sequence LIMIT ?',
                              (episode['id'], start, snapshot['through'], limit)).fetchall()
            entries = []
            for row in rows:
                record = self._record(db, json.loads(row['record'])['evidence'], principal)
                item = self.atoms.get(record['event']['payload']); envelope(item, record['event']['payload'])
                require(item.content_type == CONTENT_TYPE, 'NOT_AVAILABLE')
                wrapper = json.loads(item.bytes)
                validate_ref(wrapper['payload'], episode['scope_ref'])
                payload = self.atoms.get(wrapper['payload']); envelope(payload, wrapper['payload'])
                entries.append(dict(event=record, kind=wrapper['kind'], payload=wrapper['payload']))
        self.access.authorize(episode['scope_ref'], 'readEpisode')
        next_sequence = start+len(entries)
        return dict(snapshot=snapshot, events=entries, next_sequence=next_sequence if next_sequence <= snapshot['through'] else None,
                    complete=next_sequence > snapshot['through'], ordering='owner-commit-sequence', evidence_weight_created=False)
