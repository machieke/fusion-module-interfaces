"""Generate portable JSON Schema from the explicitly supported M1 wire shapes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def obj(properties, required=None):
    return {"type": "object", "properties": properties,
            "required": list(properties) if required is None else required,
            "additionalProperties": False}


def schema():
    label = {"type": "string", "pattern": "^[a-zA-Z0-9_.:/-]{1,128}$"}
    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    ref = obj({"scope_ref": label, "id": label, "revision": {"const": 1, "type": "integer"}, "digest": digest})
    base = {"message_id": label, "scope_ref": label, "idempotency_key": label,
            "correlation_id": label, "reply_route": label, "causation_id": label,
            "deadline_ms": {"type": "integer", "minimum": 1},
            "required_features": {"type": "array", "maxItems": 0},
            "extensions": {"type": "object"}}
    bodies = {
        "create": {"content_type": label, "sharing": {"const": "non-sensitive-fixture"},
                   "bytes": {"type": "string", "minLength": 4, "maxLength": 87384,
                             "contentEncoding": "base64"}},
        "get": {"ref": ref}, "getMany": {"refs": {"type": "array", "minItems": 1, "maxItems": 32, "items": ref}},
        "availability": {"ref": ref}, "send": {"route": label, "ref": ref},
        "poll": {"route": label}, "ack": {"route": label, "delivery_id": label},
        "submit": {"operation": {"const": "inspect_atom"}, "ref": ref},
        "status": {"job_id": label}, "result": {"job_id": label},
    }
    variants = []
    for interface, profile, operations in (
        ("atom.storage", "immutable-bytes/1", ("create", "get", "getMany", "availability")),
        ("agent.messaging", "durable-mailbox/1", ("send", "poll", "ack")),
        ("agent.messaging", "durable-mailbox/2", ("send", "poll", "ack")),
        ("execution", "inspect-atom/1", ("submit", "status", "result")),
        ("execution", "inspect-atom/2", ("submit", "status", "result"))):
        for op in operations:
            fields = {**base, "interface_ref": obj({"id": {"const": interface}, "version": {"const": "1.0.0"}}),
                      "profile": {"const": profile}, "operation": {"const": op}, "body": obj(bodies[op])}
            required = ["message_id", "scope_ref", "interface_ref", "profile", "operation", "body"]
            if op in {"create", "send", "ack", "submit"}:
                required += ["idempotency_key"]
            if op in {"send", "submit"}:
                required += ["correlation_id", "reply_route"]
            variants.append(obj(fields, required))
    error = obj({"code": {"enum": ["UNSUPPORTED_VERSION", "UNSUPPORTED_PROFILE", "UNSUPPORTED_OPERATION",
                                   "INVALID_ARGUMENT", "UNAUTHORIZED", "NOT_FOUND", "CONFLICT", "NOT_AVAILABLE",
                                   "OVERLOADED", "DEADLINE_EXCEEDED", "INTERNAL"]}, "retryable": {"type": "boolean"}})
    receipt = obj({"provider": label, "durability": label, "evidence": {"type": "object"}})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:fusion:invocation:1.0.0", "title": "M1 invocation",
            "description": "Scope equality, base64 canonicality, live authorization and deadlines require semantic validation.",
            "oneOf": variants, "$defs": {"AtomRef": ref, "Error": error, "StorageReceipt": receipt,
                "AtomWrite": obj({"ref": ref, "receipt": receipt}),
                "AtomEnvelope": obj({"ref": ref, "content_type": label, "bytes": {"type": "string", "contentEncoding": "base64"}}),
                "InspectResult": obj({"operation": {"const": "inspect_atom"}, "provider_version": {"const": "0.1.0"},
                                      "digest": digest, "length": {"type": "integer", "minimum": 1, "maximum": 65536}})}}


def response_key(profile, operation):
    return profile.replace("/", "_") + "." + operation


def response_schema():
    """Portable shapes; request matching/descriptor ceilings remain semantic checks."""
    invocation = schema()
    label = {"type": "string", "pattern": "^[a-zA-Z0-9_.:/-]{1,128}$"}
    ref = invocation["$defs"]["AtomRef"]
    errors = invocation["$defs"]["Error"]["properties"]["code"]["enum"]
    error = {"oneOf": [obj({"code": {"enum": codes}, "retryable": {"const": retry}})
                        for retry, codes in ((True, ["NOT_AVAILABLE", "OVERLOADED"]),
                           (False, [c for c in errors if c not in {"NOT_AVAILABLE", "OVERLOADED"}]))]}
    write = obj({"ref": ref, "receipt": obj({"provider": label,
        "durability": {"const": "local-files-process-restart"}, "evidence": {"type": "object"}})})
    envelope = obj({"ref": ref, "content_type": label, "bytes": {"type": "string",
        "minLength": 4, "maxLength": 87384, "contentEncoding": "base64"}})
    reference_body = obj({"ref": ref, "correlation_id": label, "reply_route": label, "causation_id": label})
    completion_body = {"oneOf": [obj({"job_id": label, "correlation_id": label, "causation_id": label,
                                     "result": write, "error": {"type": "null"}}),
                                 obj({"job_id": label, "correlation_id": label, "causation_id": label,
                                     "result": {"type": "null"}, "error": {"enum": errors}})]}
    defs, variants = {}, []
    for request in invocation["oneOf"]:
        props = request["properties"]
        profile, op = props["profile"]["const"], props["operation"]["const"]
        legacy = profile in {"durable-mailbox/1", "inspect-atom/1"}
        evidence = {} if legacy else {"evidence": {"type": "object"}}
        guarantee = {"const": "sqlite-full" if legacy else "process-restart"}
        context = {} if legacy else {"scope_ref": label}
        if op in {"create", "result"}:
            success = write
        elif op == "get":
            success = envelope
        elif op == "getMany":
            success = obj({"atoms": {"type": "array", "minItems": 1, "maxItems": 32, "items": envelope}})
        elif op == "availability":
            success = obj({"bytes": {"type": "null"}, "available": {"type": "boolean"},
                "present_shares": {"type": "integer", "minimum": 0}, "threshold": {"type": "integer", "minimum": 1},
                "content_hash": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})
        elif op == "submit":
            success = obj({"job_id": label, "execution": {"const": "queued"}, "acceptance": guarantee,
                "completion_delivery": {"const": "not-observed"}, "chain": {"type": "null"}, **evidence, **context,
                **({} if legacy else {"correlation_id": label, "reply_route": label})})
        elif op == "status":
            common = {"job_id": label, "chain": {"type": "null"}, **context,
                      **({} if legacy else {"correlation_id": label})}
            states = []
            for state in ("queued", "succeeded", "failed"):
                states.append(obj({**common, "execution": {"const": state},
                    "error": {"enum": errors} if state == "failed" else {"type": "null"},
                    "result_persistence": {"const": "local-files-process-restart"} if state == "succeeded" else {"type": "null"},
                    "completion_delivery": {"enum": ["not-observed"] if state == "queued" else ["not-observed", "mailbox-accepted"]}}))
            success = {"oneOf": states}
        elif op == "send":
            success = obj({"delivery_id": label, "acceptance": guarantee, "delivery": {"const": "not-observed"},
                           **evidence, **context, **({} if legacy else {"correlation_id": label, "route": label})})
        elif op == "ack":
            success = obj({"delivery_id": label, "delivery": {"const": "acknowledged"}, "persistence": guarantee,
                           **evidence, **context, **({} if legacy else {"route": label})})
        elif op == "poll":
            delivered = obj({"delivery_id": label, "body": {"oneOf": [reference_body, completion_body]},
                             "order": {"type": "integer", "minimum": 1},
                             "delivery": {"const": "observed-unacknowledged"}, **context,
                             **({} if legacy else {"route": label})})
            success = obj({"delivery": {"oneOf": [{"type": "null"}, delivered]}})
        key = response_key(profile, op)
        defs[key] = {"oneOf": [obj({"ok": success, "provider": {"type": "string", "pattern": "^[0-9a-f]{64}$"}}),
                               obj({"error": error})]}
        variants.append({"$ref": "#/$defs/" + key})
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "urn:fusion:responses:1.0.0:m1.1",
            "title": "M1.1 per-operation responses", "description":
            "Select $defs by requested profile and operation. Runtime validation additionally matches the selected descriptor, request, bytes digest, scope, reference order and known job correlation. Provider tokens check local binding consistency, not remote truth.",
            "anyOf": variants, "$defs": defs}


if __name__ == "__main__":
    for name, value in (("wire", schema()), ("responses", response_schema())):
        target = ROOT / ("contracts/" + name + ".schema.json")
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(value, indent=2) + "\n")
