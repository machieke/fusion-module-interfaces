"""Per-operation response conformance, including selected-provider guarantees.

Validation establishes protocol consistency, not independent proof of truth.
All malformed responses fail as NOT_AVAILABLE; no damaged reply becomes empty.
"""
from .contracts import (ERRORS, LEGACY_PROFILES, ContractError, canonical, decode,
                        digest, encode, label, require, validate_ref)
from .ports import AtomEnvelope
from .registry import selection_token


def check(condition):
    require(condition, "NOT_AVAILABLE")


def fields(value, names):
    check(isinstance(value, dict) and set(value) == set(names.split()))


def evidence(value):
    check(isinstance(value, dict))
    try:
        canonical(value)
    except (ContractError, TypeError, ValueError):
        raise ContractError("NOT_AVAILABLE") from None


def completion_acceptance(value, scope, route, delivery_id, correlation_id):
    """Trusted delivery port still validates the acknowledgement before marking sent."""
    fields(value, "delivery_id acceptance delivery evidence scope_ref route correlation_id")
    check(value["delivery_id"] == delivery_id and value["scope_ref"] == scope
          and value["route"] == route and value["correlation_id"] == correlation_id)
    check(value["acceptance"] == "process-restart" and value["delivery"] == "not-observed")
    evidence(value["evidence"])


def reference(value, scope):
    try:
        validate_ref(value, scope)
    except ContractError:
        raise ContractError("NOT_AVAILABLE") from None


def atom_write(value, scope, descriptor):
    fields(value, "ref receipt")
    reference(value["ref"], scope)
    receipt = value["receipt"]
    fields(receipt, "provider durability evidence")
    check(isinstance(receipt["provider"], str) and receipt["provider"] in descriptor.receipt_providers)
    check(isinstance(receipt["durability"], str) and receipt["durability"] in descriptor.durabilities)
    check("process-restart" in descriptor.guarantees)
    evidence(receipt["evidence"])


def envelope(value, expected):
    check(isinstance(value, AtomEnvelope))
    check(value.ref == expected and label(value.content_type) and isinstance(value.bytes, bytes))
    check(0 < len(value.bytes) <= 65536 and digest(value.bytes) == expected["digest"])


def availability(value):
    fields(value, "bytes available present_shares threshold content_hash")
    check(value["bytes"] is None and type(value["available"]) is bool)
    check(type(value["threshold"]) is int and value["threshold"] > 0)
    check(type(value["present_shares"]) is int and value["present_shares"] >= 0)
    check(value["available"] == (value["present_shares"] >= value["threshold"]))
    check(isinstance(value["content_hash"], str) and len(value["content_hash"]) == 64)


def error(value):
    fields(value, "code retryable")
    check(isinstance(value["code"], str) and value["code"] in ERRORS)
    check(type(value["retryable"]) is bool and value["retryable"] == (value["code"] in {"NOT_AVAILABLE", "OVERLOADED"}))


def _wire_envelope(value, expected, descriptor):
    fields(value, "ref content_type bytes")
    reference(value["ref"], expected["scope_ref"])
    data = decode(value["bytes"])
    check(len(data) <= descriptor.max_payload_bytes)
    envelope(AtomEnvelope(value["ref"], value["content_type"], data), expected)


def _persistence(value, key, legacy, descriptor):
    check(value[key] == ("sqlite-full" if legacy else "process-restart"))
    check("process-restart" in descriptor.guarantees)
    if legacy:
        check(descriptor.provider in {"local-mailbox", "local-inspect"})
    else:
        evidence(value["evidence"])


def _success(request, value, descriptor, correlations):
    name, op, scope = request["interface_ref"]["id"], request["operation"], request["scope_ref"]
    check(descriptor.interface == name and request["profile"] in descriptor.profiles)
    check(request["interface_ref"]["version"] == descriptor.version and op in descriptor.operations)
    legacy = request["profile"] in LEGACY_PROFILES.values()
    body = request["body"]
    if op in {"create", "result"}:
        atom_write(value, scope, descriptor)
        if op == "create":
            check(value["ref"]["digest"] == digest(decode(body["bytes"])))
    elif op == "get":
        _wire_envelope(value, body["ref"], descriptor)
    elif op == "getMany":
        fields(value, "atoms")
        check(isinstance(value["atoms"], list) and len(value["atoms"]) == len(body["refs"]))
        for item, ref in zip(value["atoms"], body["refs"]):
            _wire_envelope(item, ref, descriptor)
    elif op == "availability":
        availability(value)
        check(value["content_hash"] == body["ref"]["digest"])
    elif op == "submit":
        fields(value, "job_id execution acceptance completion_delivery chain" +
               ("" if legacy else " evidence scope_ref correlation_id reply_route"))
        check(label(value["job_id"]) and value["execution"] == "queued" and value["chain"] is None)
        check(value["completion_delivery"] == "not-observed")
        _persistence(value, "acceptance", legacy, descriptor)
        if not legacy:
            check(value["scope_ref"] == scope and value["correlation_id"] == request["correlation_id"] and
                  value["reply_route"] == request["reply_route"])
        correlations[value["job_id"]] = (scope, request["correlation_id"], request["reply_route"])
    elif op == "status":
        fields(value, "job_id execution error result_persistence completion_delivery chain" +
               ("" if legacy else " scope_ref correlation_id"))
        check(value["job_id"] == body["job_id"] and value["chain"] is None)
        state = value["execution"]
        check(state in {"queued", "succeeded", "failed"})
        check(value["completion_delivery"] in {"not-observed", "mailbox-accepted"})
        if state == "succeeded":
            check(value["error"] is None and value["result_persistence"] in descriptor.durabilities)
            check("process-restart" in descriptor.guarantees)
        else:
            check(value["result_persistence"] is None)
            check(value["error"] in ERRORS if state == "failed" else value["error"] is None)
        if state == "queued":
            check(value["completion_delivery"] == "not-observed")
        if not legacy:
            check(value["scope_ref"] == scope and label(value["correlation_id"]))
            previous = correlations.get(value["job_id"])
            if previous:
                check(previous[:2] == (scope, value["correlation_id"]))
            else:
                correlations[value["job_id"]] = (scope, value["correlation_id"], None)
    elif op == "send":
        fields(value, "delivery_id acceptance delivery" + ("" if legacy else " evidence scope_ref route correlation_id"))
        check(label(value["delivery_id"]) and value["delivery"] == "not-observed")
        _persistence(value, "acceptance", legacy, descriptor)
        if not legacy:
            check(value["scope_ref"] == scope and value["route"] == body["route"] and
                  value["correlation_id"] == request["correlation_id"])
    elif op == "ack":
        fields(value, "delivery_id delivery persistence" + ("" if legacy else " evidence scope_ref route"))
        check(value["delivery_id"] == body["delivery_id"] and value["delivery"] == "acknowledged")
        _persistence(value, "persistence", legacy, descriptor)
        if not legacy:
            check(value["scope_ref"] == scope and value["route"] == body["route"])
    elif op == "poll":
        fields(value, "delivery")
        delivered = value["delivery"]
        if delivered is None:
            return
        fields(delivered, "delivery_id body order delivery" + ("" if legacy else " scope_ref route"))
        check(label(delivered["delivery_id"]) and type(delivered["order"]) is int and delivered["order"] > 0)
        check(delivered["delivery"] == "observed-unacknowledged")
        if not legacy:
            check(delivered["scope_ref"] == scope and delivered["route"] == body["route"])
        payload = delivered["body"]
        check(isinstance(payload, dict))
        if "ref" in payload:
            fields(payload, "ref correlation_id reply_route causation_id")
            reference(payload["ref"], scope)
            check(label(payload["reply_route"]))
        else:
            fields(payload, "job_id correlation_id causation_id result error")
            check(label(payload["job_id"]) and delivered["delivery_id"] == payload["job_id"])
            if payload["error"] is None:
                atom_write(payload["result"], scope, descriptor)
            else:
                check(payload["error"] in ERRORS and payload["result"] is None)
            previous = correlations.get(payload["job_id"])
            if previous:
                check(previous[:2] == (scope, payload["correlation_id"]))
                check(previous[2] is None or previous[2] == body["route"])
        check(label(payload["correlation_id"]) and label(payload["causation_id"]))
    else:
        check(False)


def validate_reply(request, reply, descriptor, correlations=None):
    correlations = {} if correlations is None else correlations
    try:
        check(isinstance(reply, dict))
        if "error" in reply:
            fields(reply, "error")
            error(reply["error"])
        else:
            fields(reply, "ok provider")
            check(reply["provider"] == selection_token(descriptor))
            canonical(reply)
            _success(request, reply["ok"], descriptor, correlations)
    except (ContractError, TypeError, KeyError, ValueError, AttributeError):
        raise ContractError("NOT_AVAILABLE") from None
    if "error" in reply:
        raise ContractError(reply["error"]["code"])
    return reply["ok"]
