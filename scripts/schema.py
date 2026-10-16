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
        ("execution", "inspect-atom/1", ("submit", "status", "result"))):
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


if __name__ == "__main__":
    target = ROOT / "contracts/wire.schema.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(schema(), indent=2) + "\n")
