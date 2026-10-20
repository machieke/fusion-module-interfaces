"""Synthetic disclosure adversaries, separate from native integration evidence."""
import copy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch

from fusion import neoclaw_retrieval_disclosure as r, model_contracts as m
from fusion.contracts import canonical
from fusion.model_transport import Client
from tests import test_retrieval_disclosure as helpers


class ReceiptEdges(unittest.TestCase):
    setUp = helpers.RetrievalDisclosure.setUp
    rejected = helpers.RetrievalDisclosure.rejected

    def second(self):
        result = repr([[['id:', '2032-10-20 12:00:00'], ['linkedEpisodes:', ['2032-10-20 12:00:00']],
                        ['stv', 1.0, .5], 'Synthetic approved fact.']])
        feedback = r.projection(self.policy['query'], result)
        raw = self.raw.replace('LAST_SKILL_USE_RESULTS:  HISTORY:', 'LAST_SKILL_USE_RESULTS: '+feedback+' HISTORY:').replace(':-:-:-:first', ':-:-:-:second')
        self.accepted.update(slot=2, native_prompt=raw, messages=m.messages(raw))
        self.receipt.update(intent=self.accepted, query=dict(occurrence=str(uuid.uuid5(uuid.UUID(self.accepted['session']), '1/0')),
            view='b'*64, projection=feedback, result=result, capture_sha256='c'*64))
        self.path.write_bytes(canonical(self.receipt))
        return raw

    def test_retained_second_occurrence_view_recipient_and_projection_bindings(self):
        raw = self.second()
        r.validate_receipt(raw, self.policy, self.accepted)
        cases = [('context_view', 'c'*64), ('recipient', 'B'), ('consent_sha256', 'd'*64),
                 ('query.view', 'c'*64), ('query.occurrence', str(uuid.uuid4())),
                 ('query.projection', 'invented expected answer'), ('query.result', '[]')]
        for key, value in cases:
            changed = copy.deepcopy(self.receipt)
            if key.startswith('query.'): changed['query'][key.split('.')[1]] = value
            else: changed[key] = value
            self.path.write_bytes(canonical(changed))
            with self.subTest(field=key): self.rejected(lambda:r.validate_receipt(raw, self.policy, self.accepted))

    def test_timestamps_labels_stvs_content_and_record_order_are_exact(self):
        raw = self.second()
        variants = [raw.replace('12:00:00', '12:00:01', 1), raw.replace('linkedEpisodes:', 'linkedEvidence:'),
                    raw.replace('1.0, 0.5', '0.1, 0.5'), raw.replace('approved fact.', 'invented answer.')]
        for changed in variants:
            intent = dict(self.accepted, native_prompt=changed, messages=m.messages(changed))
            self.rejected(lambda:r.validate_receipt(changed, self.policy, intent))
        a = copy.deepcopy(self.receipt)
        a['query']['projection'] += '(extra record)'
        self.path.write_bytes(canonical(a))
        self.rejected(lambda:r.validate_receipt(raw, self.policy, self.accepted))

    def test_presentation_requires_explicit_component_consent(self):
        uid = str(uuid.uuid4()); timestamp = '2032-10-20 12:00:00'
        payloads = [[uid, timestamp, 'Synthetic approved fact.', .12]]
        consent = {uid:dict(metadata=dict(links=[timestamp], stv=[1.0, .5]))}
        result = [[['id:', timestamp], ['linkedEpisodes:', [timestamp]], ['stv', 1.0, .5], 'Synthetic approved fact.']]
        r.presentation(repr(result), payloads, consent)
        for field, value in [(0, ['id:', 'different']), (1, ['linkedEpisodes:', ['invented source']]),
                             (2, ['stv', .8, .5]), (3, 'private canary')]:
            altered = copy.deepcopy(result); altered[0][field] = value
            with self.subTest(field=field): self.rejected(lambda:r.presentation(repr(altered), payloads, consent))
        self.rejected(lambda:r.presentation(repr(result+result), payloads, consent))
        self.rejected(lambda:r.presentation('not a native list', payloads, consent))

    def owner(self):
        value = dict(model_completion=dict(scope=self.cfg['scope'], sessions=[self.cfg['session']],
                                           catalogue=self.cfg['catalogue'], disclosure=self.policy),
                     principals={'A':dict(credential='generated', scopes={self.cfg['scope']:
                                  ['model.'+x for x in ('complete', 'observe', 'authorize', 'disclose')]})})
        Path(self.policy['authority_policy']).write_bytes(canonical(value))
        return value

    def test_revoked_or_substituted_credential_stops_before_prompt_transport(self):
        owner = self.owner()
        path = self.root/'client.json'; path.write_bytes(canonical(self.cfg))
        client = Client(path)
        for mutation in ('revoke', 'wrong-credential', 'other-principal', 'wrong-recipient'):
            value = copy.deepcopy(owner); cfg = copy.deepcopy(self.cfg)
            if mutation == 'revoke': value['principals']['A']['scopes'][cfg['scope']].remove('model.disclose')
            if mutation == 'wrong-credential': cfg['credential'] = 'wrong'
            if mutation == 'other-principal': value['principals'] = {'B':value['principals']['A']}
            if mutation == 'wrong-recipient': value['model_completion']['disclosure']['recipient'] = 'B'
            Path(self.policy['authority_policy']).write_bytes(canonical(value)); path.write_bytes(canonical(cfg))
            with self.subTest(mutation=mutation), patch('fusion.adapters.ollama_completion.OllamaCompletion') as backend:
                self.rejected(lambda:client.invoke('observe', self.accepted), 'UNAUTHORIZED')
                backend.assert_not_called()

    def test_equal_hash_flag_and_unknown_receipt_fields_do_not_grant_permission(self):
        changed = dict(self.receipt, synthetic=True)
        self.path.write_bytes(canonical(changed))
        self.rejected(lambda:r.validate_receipt(self.raw, self.policy, self.accepted))
        policy = dict(self.policy, synthetic=True)
        cfg = dict(self.cfg, disclosure=policy)
        self.rejected(lambda:r.configuration(cfg))

    def test_native_projection_placeholder_transform_occurs_once(self):
        result = repr([[['id:', '2032-10-20 12:00:00'], ['linkedEpisodes:', []], ['stv', 1.0, .5], 'Synthetic data.']])
        projected = r.projection(self.policy['query'], result)
        self.assertIn('_apostrophe_id:_apostrophe_', projected)
        self.assertNotIn("'", projected)
        self.rejected(lambda:r.projection(self.policy['query'], result.replace("'", '_apostrophe_')))

    def test_initial_prompt_replay_accepts_only_its_pending_query(self):
        db = sqlite3.connect(':memory:'); self.addCleanup(db.close); db.row_factory = sqlite3.Row
        db.execute('CREATE TABLE app_turns(id INTEGER,commands TEXT,projection TEXT)')
        app = SimpleNamespace(db=db)
        r.initial_history(app, self.policy['query'])
        db.execute('INSERT INTO app_turns VALUES(1,?,NULL)', (canonical([['query', self.policy['query']]]).decode(),))
        r.initial_history(app, self.policy['query'])  # accepted before vector/result capture
        db.execute("UPDATE app_turns SET projection='completed'")
        self.rejected(lambda:r.initial_history(app, self.policy['query']))
        db.execute("UPDATE app_turns SET projection=NULL,commands='[[\"remember\",\"synthetic setup\"]]'")
        self.rejected(lambda:r.initial_history(app, self.policy['query']))
        db.execute('DELETE FROM app_turns')
        db.executemany('INSERT INTO app_turns VALUES(?,?,NULL)', [(1, '[]'), (2, '[]')])
        self.rejected(lambda:r.initial_history(app, self.policy['query']))
