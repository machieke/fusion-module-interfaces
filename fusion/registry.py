"""Static descriptor registry and shared compatibility resolution."""
from dataclasses import asdict, dataclass, field

from .contracts import ContractError, PROFILES, LEGACY_PROFILES, OPERATIONS, canonical, digest, require, version


@dataclass(frozen=True)
class Descriptor:
    provider: str
    interface: str
    version: str
    implementation_version: str
    profiles: frozenset[str]
    operations: frozenset[str]
    guarantees: frozenset[str]
    max_payload_bytes: int
    privacy: str = "non-sensitive-fixture-only"
    deterministic: bool = True
    features: frozenset[str] = frozenset()
    verified_evidence: tuple[str, ...] = ()
    verification: str = "none"
    measured_slo: dict = field(default_factory=dict)
    receipt_providers: frozenset[str] = frozenset()
    durabilities: frozenset[str] = frozenset({"local-files-process-restart"})


@dataclass(frozen=True)
class Requirement:
    interface: str
    minimum: str
    maximum_exclusive: str
    profile: str
    operations: frozenset[str]
    guarantees: frozenset[str]
    payload_bytes: int = 1
    privacy: str = "non-sensitive-fixture-only"
    features: frozenset[str] = frozenset()
    verification: str = "none"
    max_latency_ms: int | None = None


def resolve(providers: list[Descriptor], r: Requirement) -> Descriptor:
    candidates = [p for p in providers if p.interface == r.interface]
    lo, hi = version(r.minimum), version(r.maximum_exclusive)
    candidates = [p for p in candidates if version(p.version)[0] == lo[0]
                  and lo <= version(p.version) < hi]
    if not candidates:
        raise ContractError("UNSUPPORTED_VERSION")
    candidates = [p for p in candidates if r.profile in p.profiles and r.features <= p.features]
    if not candidates:
        raise ContractError("UNSUPPORTED_PROFILE")
    candidates = [p for p in candidates if r.operations <= p.operations]
    if not candidates:
        raise ContractError("UNSUPPORTED_OPERATION")
    candidates = [p for p in candidates if r.guarantees <= p.guarantees
                  and r.payload_bytes <= p.max_payload_bytes and r.privacy == p.privacy
                  and r.verification == "none"
                  and (r.max_latency_ms is None or
                       p.measured_slo.get("verified_max_latency_ms", float("inf")) <= r.max_latency_ms)]
    if not candidates:
        raise ContractError("NOT_AVAILABLE")
    return sorted(candidates, key=lambda p: (version(p.version), p.provider), reverse=True)[0]


def descriptors(binding: str = "independent-of-transport", atom_provider: str = "detta") -> list[Descriptor]:
    require(atom_provider in {"detta", "fixture-files"}, "UNSUPPORTED_PROFILE")
    receipt = "detta-local-rs/1" if atom_provider == "detta" else "contract-fixture-files/1"
    names = {"atom.storage": "atom-" + atom_provider, "agent.messaging": "local-mailbox", "execution": "local-inspect"}
    return [Descriptor(names[name], name, "1.0.0", "0.1.1",
                       frozenset({PROFILES[name]} | ({LEGACY_PROFILES[name]} if name in LEGACY_PROFILES else set())),
                       frozenset(operations), frozenset({"process-restart", "scoped", "idempotent"}), 65536,
                       receipt_providers=frozenset({receipt})) for name, operations in OPERATIONS.items()]


def select(catalogue: list[Descriptor]) -> dict[str, Descriptor]:
    """Consumer requirements are fixed independently of what a provider advertises."""
    return {name: resolve(catalogue, Requirement(name, "1.0.0", "1.0.1", PROFILES[name],
            frozenset(ops), frozenset({"process-restart", "scoped", "idempotent"})))
            for name, ops in OPERATIONS.items()}


def descriptor_wire(value: Descriptor) -> dict:
    return {key: sorted(item) if isinstance(item, frozenset) else item for key, item in asdict(value).items()}


def descriptor_read(value: dict) -> Descriptor:
    fields = {key: frozenset(value[key]) for key in ("profiles", "operations", "guarantees", "features", "receipt_providers", "durabilities")}
    return Descriptor(**{**value, **fields, "verified_evidence": tuple(value["verified_evidence"])})


def selection_token(value: Descriptor) -> str:
    return digest(canonical(descriptor_wire(value)))


def selected_for(catalogue: list[Descriptor], request: dict) -> Descriptor:
    return resolve(catalogue, Requirement(request["interface_ref"]["id"], request["interface_ref"]["version"],
        "1.0.1", request["profile"], frozenset({request["operation"]}),
        frozenset({"process-restart", "scoped", "idempotent"})))
