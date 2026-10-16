"""Response schemas and semantic checks; adversarial replies are protocol fixtures."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from fusion.bindings import InProcess, Subprocess
from fusion.composition import service
from fusion.contracts import ContractError, ERRORS, encode
from fusion.registry import selection_token
from fusion.responses import validate_reply
from scripts.schema import schema, response_schema, response_key
from tests.support import Harness, ROOT


class ResponseConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.samples = []
        cls.h = Harness("inprocess", atom_provider="fixture-files")
        cls.addClassCleanup(cls.h.close)
        a, b = cls.h.a, cls.h.b
        def call(peer, name, op, body, key=None, correlation=None, **meta):
            req = peer.request(name, op, body, key, correlation, **meta)
            result = peer.binding.invoke(req)
            descriptor = peer.binding.selected[name]
            cls.samples.append((req, {"ok": result, "provider": selection_token(descriptor)},
                                descriptor, copy.deepcopy(peer.binding.correlations)))
            return result
        ref = call(a, "atom.storage", "create", {"content_type": "text/plain", "bytes": encode(b"wire"),
                   "sharing": "non-sensitive-fixture"}, "wire")["ref"]
        ref2 = a.store(b"second", "second")["ref"]
        call(a, "atom.storage", "get", {"ref": ref})
        call(a, "atom.storage", "getMany", {"refs": [ref, ref2]})
        call(a, "atom.storage", "availability", {"ref": ref})
        for version in (1, 2):
            mp, ep = "durable-mailbox/"+str(version), "inspect-atom/"+str(version)
            call(b, "agent.messaging", "poll", {"route": "reply-B"}, profile=mp)
            sent = call(a, "agent.messaging", "send", {"ref": ref, "route": "reply-B"},
                        "send"+str(version), "corr"+str(version), profile=mp)
            call(b, "agent.messaging", "poll", {"route": "reply-B"}, profile=mp)
            call(b, "agent.messaging", "ack", {"route": "reply-B", "delivery_id": sent["delivery_id"]},
                 "ack"+str(version), profile=mp)
            job = call(a, "execution", "submit", {"ref": ref, "operation": "inspect_atom"},
                       "job"+str(version), "jobcorr"+str(version), profile=ep)
            call(a, "execution", "status", {"job_id": job["job_id"]}, profile=ep)
            cls.h.command("work")
            call(a, "execution", "status", {"job_id": job["job_id"]}, profile=ep)
            call(a, "execution", "result", {"job_id": job["job_id"]}, profile=ep)
            cls.h.command("flush")
            call(a, "agent.messaging", "poll", {"route": "reply-A"}, profile=mp)
            a.ack(job["job_id"], "completion-ack"+str(version))
        # Failed terminal response/completion, including the absence of a result.
        job = a.delegate(ref, "failed")
        cls.h.config["principals"]["worker"]["scopes"] = {}
        cls.h.save()
        cls.h.command("work")
        call(a, "execution", "status", {"job_id": job["job_id"]})
        cls.h.command("flush")
        call(a, "agent.messaging", "poll", {"route": "reply-A"})

    def validator(self, request):
        return Draft202012Validator(response_schema()["$defs"][response_key(request["profile"], request["operation"])])

    def reject(self, sample, reply):
        request, _, descriptor, correlations = sample
        with self.assertRaises(ContractError) as cm:
            validate_reply(request, reply, descriptor, copy.deepcopy(correlations))
        self.assertEqual(cm.exception.code, "NOT_AVAILABLE")

    def test_generated_schemas_match_checked_in_contracts(self):
        for name, generated in (("wire", schema()), ("responses", response_schema())):
            self.assertEqual(json.loads((ROOT / ("contracts/"+name+".schema.json")).read_text()), generated)
            Draft202012Validator.check_schema(generated)

    def test_all_operations_and_profiles_validate_real_fixture_replies(self):
        covered = set()
        for request, reply, descriptor, correlations in self.samples:
            with self.subTest(profile=request["profile"], operation=request["operation"]):
                Draft202012Validator(schema()).validate(request)
                self.validator(request).validate(reply)
                self.assertEqual(validate_reply(request, reply, descriptor, copy.deepcopy(correlations)), reply["ok"])
                covered.add(response_key(request["profile"], request["operation"]))
        self.assertEqual(covered, set(response_schema()["$defs"]))

    def test_every_operation_rejects_missing_malformed_and_unselected_replies(self):
        for sample in self.samples:
            request, original, _, _ = sample
            with self.subTest(profile=request["profile"], operation=request["operation"]):
                malformed = copy.deepcopy(original)
                del malformed["ok"][next(iter(malformed["ok"]))]
                for reply in (None, {}, [], {"ok": None, "provider": original["provider"]}, malformed,
                              {**original, "unexpected": True}):
                    self.reject(sample, reply)
                    with self.assertRaises(ValidationError): self.validator(request).validate(reply)
                self.reject(sample, {**original, "provider": "0"*64})

    def test_all_error_responses_and_retryability_are_closed(self):
        for sample in self.samples:
            request, _, descriptor, _ = sample
            for code in ERRORS:
                reply = {"error": {"code": code, "retryable": code in {"NOT_AVAILABLE", "OVERLOADED"}}}
                self.validator(request).validate(reply)
                with self.assertRaises(ContractError) as cm: validate_reply(request, reply, descriptor)
                self.assertEqual(cm.exception.code, code)
                reply["error"]["retryable"] = not reply["error"]["retryable"]
                self.reject(sample, reply)
            for value in ({}, {"code": "NEW_UNNEGOTIATED_ERROR", "retryable": False},
                          {"code": [], "retryable": False}, {"code": "NOT_FOUND", "retryable": 0}):
                self.reject(sample, {"error": value})

    def test_request_scope_reference_order_correlation_and_guarantees_are_checked(self):
        for sample in self.samples:
            request, original, _, _ = sample
            reply = copy.deepcopy(original)
            value, op = reply["ok"], request["operation"]
            if "scope_ref" in value:
                value["scope_ref"] = "wrong-scope"
                self.reject(sample, reply)
            reply = copy.deepcopy(original); value = reply["ok"]
            if op in {"create", "result"}:
                value["receipt"]["durability"] = "globally-final"
            elif op == "get":
                value["bytes"] = encode(b"wrong-bytes")
            elif op == "getMany":
                value["atoms"].reverse()
            elif op == "availability":
                value["content_hash"] = "0"*64
            elif op in {"submit", "send"}:
                value["acceptance"] = "globally-final"
            elif op == "status":
                value["execution"] = "new-unnegotiated-state"
            elif op == "ack":
                value["delivery_id"] = "wrong-id"
            elif op == "poll":
                if value["delivery"] is None: continue
                value["delivery"]["body"]["correlation_id"] = []
            self.reject(sample, reply)
            if "correlation_id" in original["ok"]:
                reply = copy.deepcopy(original); reply["ok"]["correlation_id"] = "different-correlation"
                self.reject(sample, reply)
            if op in {"create", "result"}:
                reply = copy.deepcopy(original); reply["ok"]["receipt"]["provider"] = "unselected-provider"
                self.reject(sample, reply)
            if op == "poll" and original["ok"]["delivery"] and "job_id" in original["ok"]["delivery"]["body"]:
                reply = copy.deepcopy(original)
                reply["ok"]["delivery"]["body"]["correlation_id"] = "different-correlation"
                self.reject(sample, reply)

    def test_both_bindings_apply_response_checks_before_returning_success(self):
        sample = next(x for x in self.samples if x[0]["operation"] == "get")
        request, reply, _, _ = sample
        bad = copy.deepcopy(reply); bad["ok"]["bytes"] = encode(b"corruption")
        catalogue = list(self.h.a.binding.selected.values())
        factory = lambda: SimpleNamespace(catalogue=catalogue, close=lambda: None,
                                           invoke=lambda credential, request: bad["ok"])
        binding = InProcess(factory, "fixture-credential")
        with self.assertRaises(ContractError) as cm: binding.invoke(request)
        self.assertEqual(cm.exception.code, "NOT_AVAILABLE")
        binding = Subprocess(self.h.path, "fixture-credential", self.h.a.binding.selected)
        for malformed in (None, bad, {"error": {"code": "UNKNOWN", "retryable": False}}):
            with patch.object(binding, "_run", return_value=malformed):
                with self.assertRaises(ContractError) as cm: binding.invoke(request)
                self.assertEqual(cm.exception.code, "NOT_AVAILABLE")

    def test_invalid_completion_acceptance_does_not_mark_outbox_sent(self):
        h = Harness("inprocess", atom_provider="fixture-files")
        self.addCleanup(h.close)
        job = h.a.delegate(h.a.store(b"port", "input")["ref"], "job")
        h.command("work")
        owner = service(h.path)
        try:
            real = owner.worker.messages
            for malformed in (None, {}, {"delivery_id": job["job_id"], "acceptance": "globally-final"}):
                owner.worker.messages = SimpleNamespace(accept=lambda *args: malformed)
                self.assertEqual(owner.flush(), {"sent": 0, "pending": 1})
            owner.worker.messages = real
            self.assertEqual(owner.flush(), {"sent": 1, "pending": 0})
        finally:
            owner.close()
