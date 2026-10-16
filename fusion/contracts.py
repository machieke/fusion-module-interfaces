"""Types and validation shared by every binding; no provider imports."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import time
from typing import Any, Literal, NewType, Protocol, TypedDict

JSON = dict[str, Any]
ScopeRef = NewType("ScopeRef", str)
MAX_BYTES = 65536
ERRORS = frozenset({"UNSUPPORTED_VERSION", "UNSUPPORTED_PROFILE", "UNSUPPORTED_OPERATION",
                    "INVALID_ARGUMENT", "UNAUTHORIZED", "NOT_FOUND", "CONFLICT",
                    "NOT_AVAILABLE", "OVERLOADED", "DEADLINE_EXCEEDED", "INTERNAL"})


class ContractError(Exception):
    def __init__(self, code: str):
        assert code in ERRORS
        self.code = code
        super().__init__(code)

    def wire(self) -> JSON:
        return {"code": self.code, "retryable": self.code in {"NOT_AVAILABLE", "OVERLOADED"}}


def require(condition: bool, code: str = "INVALID_ARGUMENT") -> None:
    if not condition:
        raise ContractError(code)


def canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError):
        raise ContractError("INVALID_ARGUMENT") from None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def decode(value: Any) -> bytes:
    require(isinstance(value, str) and len(value) <= 4 * ((MAX_BYTES + 2) // 3))
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise ContractError("INVALID_ARGUMENT") from None
    require(0 < len(data) <= MAX_BYTES and encode(data) == value)
    return data


def label(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[a-zA-Z0-9_.:/-]{1,128}", value))


def version(value: str) -> tuple[int, int, int]:
    require(isinstance(value, str) and bool(re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value)))
    return tuple(int(x) for x in value.split("."))


class InterfaceRef(TypedDict):
    id: str
    version: str


class AtomRef(TypedDict):
    scope_ref: str
    id: str
    revision: int
    digest: str


class PayloadRef(TypedDict):
    scope_ref: str
    id: str
    digest: str
    revision: int


class PayloadReceipt(TypedDict):
    provider: str
    durability: str
    evidence: JSON


class AtomWrite(TypedDict):
    ref: AtomRef
    receipt: PayloadReceipt


class JobAcceptance(TypedDict):
    job_id: str
    execution: Literal["queued"]
    acceptance: Literal["sqlite-full"]
    completion_delivery: Literal["not-observed"]
    chain: None


class JobStatus(TypedDict):
    job_id: str
    execution: Literal["queued", "succeeded", "failed"]
    error: str | None
    result_persistence: str | None
    completion_delivery: Literal["not-observed", "mailbox-accepted"]
    chain: None


class MessageAcceptance(TypedDict):
    delivery_id: str
    acceptance: Literal["sqlite-full"]
    delivery: Literal["not-observed"]


class MessageAck(TypedDict):
    delivery_id: str
    delivery: Literal["acknowledged"]
    persistence: Literal["sqlite-full"]


class ReferenceMessage(TypedDict):
    ref: AtomRef
    correlation_id: str
    reply_route: str
    causation_id: str


class CompletionMessage(TypedDict):
    job_id: str
    correlation_id: str
    causation_id: str
    result: AtomWrite | None
    error: str | None


class MessageDelivery(TypedDict):
    delivery_id: str
    body: ReferenceMessage | CompletionMessage
    order: int
    delivery: Literal["observed-unacknowledged"]


class Invocation(TypedDict, total=False):
    message_id: str
    interface_ref: InterfaceRef
    profile: str
    operation: str
    scope_ref: str
    idempotency_key: str
    body: JSON
    correlation_id: str
    reply_route: str
    causation_id: str
    deadline_ms: int
    required_features: list[str]
    extensions: JSON


class Storage(Protocol):
    """Trusted internal opaque port; the owner enforces scope before invoking it."""
    def put(self, scope_ref: str, coordinate: str, data: bytes) -> tuple[str, PayloadReceipt]: ...
    def get(self, scope_ref: str, payload_id: str) -> bytes: ...
    def availability(self, scope_ref: str, payload_id: str) -> JSON: ...


class Binding(Protocol):
    def invoke(self, request: Invocation) -> JSON: ...


OPERATIONS = {
    "atom.storage": {"create", "get", "getMany", "availability"},
    "agent.messaging": {"send", "poll", "ack"},
    "execution": {"submit", "status", "result"},
}
PROFILES = {"atom.storage": "immutable-bytes/1", "agent.messaging": "durable-mailbox/1",
            "execution": "inspect-atom/1"}
MUTATIONS = {"create", "send", "ack", "submit"}


def validate_ref(ref: Any, scope: str) -> None:
    require(isinstance(ref, dict) and set(ref) == {"scope_ref", "id", "revision", "digest"})
    require(label(ref["id"]) and ref["scope_ref"] == scope, "UNAUTHORIZED")
    require(type(ref["revision"]) is int and ref["revision"] == 1)
    require(isinstance(ref["digest"], str) and bool(re.fullmatch("[0-9a-f]{64}", ref["digest"])))


def validate(request: Any, *, check_deadline: bool = True) -> tuple[str, str]:
    require(isinstance(request, dict))
    required = {"message_id", "interface_ref", "operation", "scope_ref", "profile", "body"}
    optional = {"idempotency_key", "correlation_id", "reply_route", "causation_id",
                "deadline_ms", "required_features", "extensions"}
    require(required <= request.keys() and request.keys() <= required | optional)
    for field in ("message_id", "scope_ref", "operation"):
        require(label(request[field]))
    iface = request["interface_ref"]
    require(isinstance(iface, dict) and set(iface) == {"id", "version"})
    name, op = iface["id"], request["operation"]
    require(isinstance(name, str) and name in OPERATIONS, "UNSUPPORTED_OPERATION")
    # An invocation uses an explicitly selected supported wire version.
    require(version(iface["version"]) == (1, 0, 0), "UNSUPPORTED_VERSION")
    require(request["profile"] == PROFILES[name], "UNSUPPORTED_PROFILE")
    require(op in OPERATIONS[name], "UNSUPPORTED_OPERATION")
    require(request.get("required_features", []) == [], "UNSUPPORTED_PROFILE")
    require(isinstance(request.get("extensions", {}), dict))
    for field in ("idempotency_key", "correlation_id", "reply_route", "causation_id"):
        if field in request:
            require(label(request[field]))
    if op in MUTATIONS:
        require(label(request.get("idempotency_key")))
    if "deadline_ms" in request:
        require(type(request["deadline_ms"]) is int and request["deadline_ms"] > 0)
        if check_deadline:
            require(time.time_ns() // 1_000_000 < request["deadline_ms"], "DEADLINE_EXCEEDED")
    body = request["body"]
    require(isinstance(body, dict))
    fields = {"create": {"content_type", "bytes", "sharing"}, "get": {"ref"},
              "getMany": {"refs"}, "availability": {"ref"},
              "send": {"route", "ref"}, "poll": {"route"}, "ack": {"route", "delivery_id"},
              "submit": {"operation", "ref"}, "status": {"job_id"}, "result": {"job_id"}}
    require(set(body) == fields[op])
    if op == "create":
        require(label(body["content_type"]))
        require(body["sharing"] == "non-sensitive-fixture", "UNAUTHORIZED")
        decode(body["bytes"])
    if op in {"get", "availability", "send", "submit"}:
        validate_ref(body["ref"], request["scope_ref"])
    if op == "getMany":
        require(isinstance(body["refs"], list) and 1 <= len(body["refs"]) <= 32)
        for ref in body["refs"]:
            validate_ref(ref, request["scope_ref"])
    for field in ("route", "delivery_id", "job_id"):
        if field in body:
            require(label(body[field]))
    if op in {"submit", "send"}:
        require(label(request.get("correlation_id")) and label(request.get("reply_route")))
    if op == "submit":
        require(body["operation"] == "inspect_atom", "UNSUPPORTED_OPERATION")
    require(len(canonical(request)) <= 100000)
    return name, op
