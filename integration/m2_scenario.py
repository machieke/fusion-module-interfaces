"""Bounded GENERATED demonstration, application policy outside C1/C2 owners.

The fixture is the observation scenario, not the Hive/DeTTa/PLN providers.
No source text is parsed into a truth value. All assessments are explicit.
"""
from fusion import memory_contracts as c
from fusion.contracts import canonical, digest, require
from fusion.evidence_relay import EvidenceRelay
from fusion.ports import Mutation, EvidenceSubmission
from fusion.responses import envelope


def run_generated(modules, scope, identity, seed, *, hook=lambda stage: None):
    atoms, episodes, beliefs = modules.atoms, modules.episodes, modules.beliefs
    intent = canonical({'kind': 'generated-private-m2', 'seed': seed})
    stored = atoms.create(Mutation(scope, 'intent/' + identity), 'application/fusion-intent', intent)
    c.response(c.atom_write, stored, scope)
    value = atoms.get(stored['ref']); envelope(value, stored['ref'])
    require(value.bytes == intent, 'NOT_AVAILABLE')
    claim = atoms.create(Mutation(scope, 'claim/' + identity), 'application/fusion-claim', canonical({
        'predicate': 'available', 'arguments': ['generated-resource-' + str(seed)], 'positive': True}))['ref']
    relay = EvidenceRelay(modules.root / 'relay.sqlite', episodes, beliefs, hook=hook)

    def episode(suffix):
        return episodes.recordEpisode(Mutation(scope, suffix + '/' + identity), 'sensor-a')['ref']

    def append(ep, context, n, kind, source, strength, provenance=None):
        occurrence = digest(canonical([identity, context, n]))
        payload = atoms.create(Mutation(scope, 'payload/' + occurrence), 'text/plain',
            f'Generated private source report {seed}; assessment is separately declared.'.encode())['ref']
        numeric = {'claim': claim, 'context': context, 'relationship': kind,
            'truth': None if kind == 'reports' else {'model': c.MODEL, 'strength': strength,
                'confidence': '0.5', 'evidence_count': None}, 'ingestion_profile': c.INGESTION}
        event = {'occurrence_id': occurrence, 'kind': 'observation', 'source': source,
            'observed_time': '2026-10-16T00:00:00Z', 'payload': payload, 'causation': [],
            'provenance': provenance or [], 'numerical': numeric}
        receipt = episodes.appendEvent(Mutation(scope, 'append/' + occurrence), ep, n, event)
        # A new transport key cannot create a new occurrence or advance the head.
        require(episodes.appendEvent(Mutation(scope, 'retry/' + occurrence), ep, n, event) == receipt, 'NOT_AVAILABLE')
        relay.drain(ep)
        return receipt['evidence']

    story = episode('story')
    append(story, 'story', 0, 'reports', 'sensor-a', None)
    observation = append(story, 'story', 1, 'supports', 'sensor-a', '0.75')
    append(story, 'story', 2, 'supports', 'speaker-a', '0.75', [observation])
    append(story, 'story', 3, 'contradicts', 'sensor-b', '0.25')
    story_snapshot = beliefs.readBelief(claim, 'story', None)
    require(len(story_snapshot['observations']) == 4 and len(story_snapshot['alternatives']) == 2, 'NOT_AVAILABLE')

    independent = episode('independent')
    append(independent, 'independent', 0, 'supports', 'sensor-a', '0.75')
    append(independent, 'independent', 1, 'contradicts', 'sensor-b', '0.25')
    admitted = beliefs.readBelief(claim, 'independent', 2)
    support_ids = [o['support_id'] for o in admitted['observations']]
    request = EvidenceSubmission(Mutation(scope, 'assume/' + identity), claim, 'independent', None, support_ids[1],
        2, c.BELIEF_PROFILE, admitted['runtime_selection'],
        {'model_id': 'generated-independent-sensors/v1', 'supports': support_ids, 'status': 'assumption'})
    revised = beliefs.submitEvidence(request)
    c.response(c.decision, revised, claim, 'independent', admitted['runtime_selection'])
    aggregate = revised['snapshot']['aggregate']
    ancestor = beliefs.submitEvidence(EvidenceSubmission(Mutation(scope, 'ancestor/' + identity), claim,
        'independent', None, support_ids[0], 3, c.BELIEF_PROFILE, admitted['runtime_selection'],
        {'model_id': 'generated-ancestor-overlap/v1', 'supports': [aggregate, support_ids[0]], 'status': 'assumption'}))
    require(ancestor['snapshot'] == revised['snapshot'] and ancestor['numerical'] == 'retained-alternative', 'NOT_AVAILABLE')
    # Private diagnostic result for local verifier only; the native plugin emits counts.
    return {'story': story, 'independent': independent, 'claim': claim,
        'story_snapshot': story_snapshot, 'revision': revised, 'ancestor': ancestor,
        'story_decisions': relay.decisions(story), 'independent_decisions': relay.decisions(independent)}
