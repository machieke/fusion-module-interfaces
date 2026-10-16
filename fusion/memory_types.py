"""C1/C2 version 2 local DTOs. No runtime, backend or provider imports.

Records are immutable at their owner; returned dictionaries are detached values.
AtomRef revision is immutable storage identity, never an episode stream head.
"""
from typing import Literal, TypedDict

from .contracts import AtomRef, JSON


class EpisodeRef(TypedDict):
    scope_ref: str
    id: str


class EvidenceRef(TypedDict):
    episode: EpisodeRef
    occurrence_id: str
    sequence: int
    event_ref: AtomRef


class NumericalTruth(TypedDict):
    model: str
    strength: str
    confidence: str
    evidence_count: None


class NumericalObservation(TypedDict):
    claim: AtomRef
    context: str
    relationship: Literal['supports', 'contradicts', 'reports']
    truth: NumericalTruth | None
    ingestion_profile: str


class EpisodeEvent(TypedDict):
    occurrence_id: str
    kind: Literal['observation', 'action', 'result']
    source: str
    observed_time: str
    payload: AtomRef
    causation: list[AtomRef]
    provenance: list[EvidenceRef]
    numerical: NumericalObservation | None


class EvidenceRecord(TypedDict):
    evidence: EvidenceRef
    event: EpisodeEvent
    lineage_roots: list[str]


class Episode(TypedDict):
    ref: EpisodeRef
    head: int
    events: list[EvidenceRecord]
    next_sequence: int | None
    complete: bool


class AppendReceipt(TypedDict):
    evidence: EvidenceRef
    head: int
    delivery_id: str | None
    persistence: Literal['process-restart']


class EvidenceDelivery(TypedDict):
    delivery_id: str
    evidence: EvidenceRef


class Independence(TypedDict):
    model_id: str
    supports: list[str]
    status: Literal['assumption']


class Support(TypedDict):
    id: str
    claim: AtomRef
    context: str
    truth: NumericalTruth
    evidence_ids: list[str]
    lineage_roots: list[str]
    coverage: list[str]
    premises: list[str]
    formula: str | None
    assumptions: list[str]


class BeliefSnapshot(TypedDict):
    claim: AtomRef
    context: str
    revision: int
    truth: NumericalTruth | None
    aggregate: str | None
    covered_supports: list[str]
    alternatives: list[str]
    supports: list[Support]
    observations: list[JSON]
    model: str
    runtime_selection: str


class RevisionDecision(TypedDict):
    decision_id: str
    evidence: EvidenceRef | None
    support_id: str | None
    admission: Literal['admitted', 'duplicate']
    numerical: Literal['initialized', 'revised', 'no-change', 'retained-alternative', 'model-inapplicable']
    detail: str
    snapshot: BeliefSnapshot

