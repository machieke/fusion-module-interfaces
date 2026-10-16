"""Method-level contracts, including specification-only C1–C4 ports.

No cognitive implementation is instantiated in M0/M1. A model/policy profile is
mandatory wherever numeric or query semantics differ.
"""
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from .contracts import (AtomRef, AtomWrite, InterfaceRef, JSON, JobAcceptance, JobStatus,
                        MessageAcceptance, MessageAck, MessageDelivery)


@dataclass(frozen=True)
class Mutation:
    scope_ref: str
    idempotency_key: str
    # Trusted binding preserves the full wire intent across independent commits.
    intent_digest: str | None = None


@dataclass(frozen=True)
class AtomEnvelope:
    ref: AtomRef
    content_type: str
    bytes: bytes


@runtime_checkable
class AtomStorage(Protocol):
    def create(self, command: Mutation, content_type: str, data: bytes) -> AtomWrite: ...
    def get(self, ref: AtomRef) -> AtomEnvelope: ...
    def getMany(self, refs: tuple[AtomRef, ...]) -> tuple[AtomEnvelope, ...]: ...
    def availability(self, ref: AtomRef) -> JSON: ...


@runtime_checkable
class CompletionDelivery(Protocol):
    """Trusted execution-to-mailbox port, never public dispatch.

    Return only after durable acceptance. Same scope/route/ID/body is replayable;
    changed content conflicts. No shared transaction with the caller is promised.
    """
    def accept(self, scope_ref: str, route: str, delivery_id: str,
               completion: JSON) -> JSON: ...


@dataclass(frozen=True)
class Relation:
    ref: AtomRef
    relation_type: str
    roles: tuple[tuple[str, AtomRef], ...]
    directed: bool
    profile: str = "ordered-roles/1"


class Relations(Protocol):
    def assertRelation(self, command: Mutation, relation_type: str,
                       roles: tuple[tuple[str, AtomRef], ...], directed: bool) -> Relation: ...
    def getRelation(self, ref: AtomRef) -> Relation: ...
    def outgoing(self, ref: AtomRef, limit: int) -> tuple[AtomRef, ...]: ...
    def incoming(self, ref: AtomRef, limit: int) -> tuple[AtomRef, ...]: ...


@dataclass(frozen=True)
class Query:
    scope_ref: str
    profile: str
    expression: str
    limit: int
    minimum_watermark: int


@dataclass(frozen=True)
class SearchResult:
    refs: tuple[AtomRef, ...]
    watermark: int
    projection_version: str
    complete: bool


class Search(Protocol):
    def query(self, query: Query) -> SearchResult: ...


@dataclass(frozen=True)
class EvidenceRef:
    occurrence_id: str
    source_ref: AtomRef
    episode_ref: AtomRef
    sequence: int
    target_claim: AtomRef
    relationship: Literal["supports", "contradicts", "reports"]
    provenance: tuple[AtomRef, ...]
    lineage_roots: tuple[str, ...]


@dataclass(frozen=True)
class EpisodeEvent:
    occurrence_id: str
    kind: Literal["observation", "action", "result"]
    source: str
    observed_time: str
    payload: AtomRef
    causation: tuple[AtomRef, ...]


@dataclass(frozen=True)
class Episode:
    ref: AtomRef
    revision: int
    events: tuple[EpisodeEvent, ...]


class EpisodicMemory(Protocol):
    def recordEpisode(self, command: Mutation, source: str) -> Episode: ...
    def appendEvent(self, command: Mutation, episode: AtomRef, expected_sequence: int,
                    event: EpisodeEvent) -> Episode: ...
    def readEpisode(self, ref: AtomRef, start: int, limit: int) -> Episode: ...
    def findEpisodes(self, query: Query) -> SearchResult: ...


@dataclass(frozen=True)
class ProfileRef:
    id: str
    version: str


@dataclass(frozen=True)
class Truth:
    profile: ProfileRef
    strength: str
    confidence: str
    evidence_count: str | None


@dataclass(frozen=True)
class BeliefSnapshot:
    claim: AtomRef
    revision: int
    truth: Truth | None
    evidence: tuple[EvidenceRef, ...]
    alternatives: tuple[AtomRef, ...]


@dataclass(frozen=True)
class EvidenceSubmission:
    command: Mutation
    evidence: EvidenceRef
    expected_revision: int
    profile: ProfileRef
    independence_assumption: AtomRef | None


class BeliefRevision(Protocol):
    def submitEvidence(self, submission: EvidenceSubmission) -> BeliefSnapshot: ...
    def readBelief(self, claim: AtomRef, revision: int | None) -> BeliefSnapshot: ...


@dataclass(frozen=True)
class Derivation:
    proposed_claim: AtomRef
    proposed_truth: Truth
    rule: ProfileRef
    premises: tuple[BeliefSnapshot, ...]
    evidence: tuple[EvidenceRef, ...]
    assumptions: tuple[AtomRef, ...]


class PLNKernel(Protocol):
    def profiles(self) -> tuple[ProfileRef, ...]: ...
    def applyRule(self, rule: ProfileRef, premises: tuple[BeliefSnapshot, ...]) -> Derivation: ...


@dataclass(frozen=True)
class Stimulus:
    command: Mutation
    target: AtomRef
    amount: str
    cause: str
    generation: int
    policy: ProfileRef


@dataclass(frozen=True)
class AttentionSnapshot:
    target: AtomRef
    sti: str
    logical_step: int
    policy: ProfileRef
    revision: int


class Attention(Protocol):
    def submitStimulus(self, stimulus: Stimulus) -> AttentionSnapshot: ...
    def readAttention(self, target: AtomRef) -> AttentionSnapshot: ...
    def select(self, scope_ref: str, policy: ProfileRef, limit: int) -> tuple[AttentionSnapshot, ...]: ...
    def advance(self, command: Mutation, policy: ProfileRef, expected_step: int, steps: int) -> int: ...


@dataclass(frozen=True)
class WorkBudget:
    max_candidates: int
    max_rule_applications: int
    max_feedback_generation: int
    deadline_ms: int


@dataclass(frozen=True)
class StepReceipt:
    candidates: int
    rule_applications: int
    feedback_generation: int
    proposals: tuple[AtomRef, ...]
    stopped_because: Literal["budget", "deadline", "exhausted", "unavailable"]


class InferenceControl(Protocol):
    def step(self, command: Mutation, budget: WorkBudget) -> StepReceipt: ...


@runtime_checkable
class DelegatedExecution(Protocol):
    def submit(self, command: Mutation, operation: Literal["inspect_atom"], ref: AtomRef,
               correlation_id: str, reply_route: str, deadline_ms: int | None) -> JobAcceptance: ...
    def status(self, scope_ref: str, job_id: str) -> JobStatus: ...
    def result(self, scope_ref: str, job_id: str) -> AtomWrite: ...


@runtime_checkable
class Messaging(Protocol):
    def send(self, command: Mutation, ref: AtomRef, route: str,
             correlation_id: str, reply_route: str) -> MessageAcceptance: ...
    def poll(self, scope_ref: str, route: str) -> MessageDelivery | None: ...
    def ack(self, command: Mutation, route: str, delivery_id: str) -> MessageAck: ...


@dataclass(frozen=True)
class ApprovedCommitment:
    scope_ref: str
    result_ref: AtomRef
    commitment_digest: str
    approval_record: str


@dataclass(frozen=True)
class ChainObservation:
    deploy_id: str | None
    inclusion_block: str | None
    effect_finality: Literal["not-observed", "pending", "included", "finalized", "rejected"]
    evidence: JSON


class ConsensusFinality(Protocol):
    def submit(self, command: Mutation, commitment: ApprovedCommitment) -> ChainObservation: ...
    def observe(self, deploy_id: str) -> ChainObservation: ...


class Authorization(Protocol):
    def authorize(self, authenticated_context: object, scope_ref: str,
                  interface: InterfaceRef, operation: str) -> None: ...
