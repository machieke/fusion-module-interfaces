"""Static descriptor registry and shared compatibility resolution."""
from dataclasses import dataclass, field

from .contracts import ContractError, PROFILES, OPERATIONS, version


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


def descriptors(binding: str) -> list[Descriptor]:
    return [Descriptor(f"local-{name}-{binding}", name, "1.0.0", "0.1.0",
                       frozenset({PROFILES[name]}), frozenset(operations),
                       frozenset({"process-restart", "scoped", "idempotent"}), 65536)
            for name, operations in OPERATIONS.items()]
