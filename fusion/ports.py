"""Method-level contracts: M1, private C1/C2 v2, and bounded C3/C4 local ports.

No cognitive implementation is instantiated in M0/M1. A model/policy profile is
mandatory wherever numeric or query semantics differ.
"""
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

from .contracts import (AtomRef, AtomWrite, InterfaceRef, JSON, JobAcceptance, JobStatus,
                        MessageAcceptance, MessageAck, MessageDelivery)
from .memory_types import (EpisodeRef, EvidenceRef, EpisodeEvent, Episode, AppendReceipt,
                           EvidenceRecord, EvidenceDelivery,
                           BeliefSnapshot, RevisionDecision, Support, Independence)


@dataclass(frozen=True)
class Mutation:
    scope_ref: str
    idempotency_key: str
    # Trusted binding preserves the full wire intent across independent commits.
    intent_digest: str | None = None


@dataclass(frozen=True)
class EvidenceSubmission:
    command: Mutation
    claim: AtomRef
    context: str
    evidence: EvidenceRef | None
    support_id: str | None
    expected_revision: int
    profile: str
    runtime_selection: str
    independence: Independence | None = None


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


@runtime_checkable
class EpisodicMemory(Protocol):
    def recordEpisode(self, command: Mutation, source: str) -> Episode: ...
    def appendEvent(self, command: Mutation, episode: EpisodeRef, expected_sequence: int,
                    event: EpisodeEvent) -> AppendReceipt: ...
    def readEpisode(self, ref: EpisodeRef, start: int, limit: int) -> Episode: ...
    def readEvidence(self, ref: EvidenceRef) -> EvidenceRecord: ...
    def pendingEvidence(self, ref: EpisodeRef, limit: int) -> tuple[EvidenceDelivery, ...]: ...
    def acknowledgeEvidence(self, command: Mutation, delivery_id: str,
                            decision: RevisionDecision) -> JSON: ...


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


@runtime_checkable
class BeliefRevision(Protocol):
    def submitEvidence(self, submission: EvidenceSubmission) -> RevisionDecision: ...
    def readBelief(self, claim: AtomRef, context: str, revision: int | None) -> BeliefSnapshot: ...


class PrivateAuthority(Protocol):
    def authorize(self, scope: str, operation: str) -> str: ...
    def origin(self, scope: str, source: str) -> str | None: ...
    def selection(self) -> str: ...


class RevisionMath(Protocol):
    def profile(self) -> JSON: ...
    def revise(self, existing: Support, incoming: Support, revision: int,
               independence: Independence | None) -> JSON: ...


@dataclass(frozen=True)
class DerivationSubmission:
    command: Mutation
    task: AtomRef
    context: str
    premises: tuple[JSON, ...]
    expected_revision: int
    profile: str
    kernel_selection: str
    deadline_ms: int


class DerivedBeliefRevision(Protocol):
    """Version 3 tagged-support responses; not the M2 snapshot schema."""
    def submitEvidence(self, submission: EvidenceSubmission) -> JSON: ...
    def readBelief(self, claim: AtomRef, context: str, revision: int | None) -> JSON: ...
    def submitDerivation(self, request: DerivationSubmission) -> JSON: ...
    def readDerivation(self, scope: str, idempotency_key: str) -> JSON | None: ...


class PLNKernel(Protocol):
    def profile(self) -> JSON: ...
    def applyRule(self, task: JSON, premises: tuple[JSON, ...], deadline_ms: int) -> JSON: ...


@dataclass(frozen=True)
class Stimulus:
    command: Mutation
    context: str
    target: AtomRef
    amount: str
    cause: str
    generation: int
    policy: str
    expected_step: int
    kind: Literal['ingress', 'feedback']
    parent: str | None = None


class Attention(Protocol):
    def profile(self) -> JSON: ...
    def submitStimulus(self, stimulus: Stimulus) -> JSON: ...
    def readAttention(self, target: AtomRef, context: str) -> JSON: ...
    def select(self, scope: str, context: str, eligible: tuple[AtomRef, ...], limit: int) -> JSON: ...
    def advance(self, command: Mutation, context: str, expected_step: int, steps: int) -> JSON: ...


@dataclass(frozen=True)
class WorkBudget:
    max_candidates: int
    max_rule_applications: int
    max_feedback_generation: int
    deadline_ms: int  # absolute Unix milliseconds, never renewed by replay


@dataclass(frozen=True)
class InferenceRequest:
    command: Mutation
    context: str
    workset: AtomRef
    selections: JSON
    budget: WorkBudget


class InferenceControl(Protocol):
    def step(self, request: InferenceRequest) -> JSON: ...


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
