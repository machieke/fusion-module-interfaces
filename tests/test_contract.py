from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from fusion.contracts import ContractError, canonical, decode, digest, encode, validate
from fusion.registry import Requirement, descriptors, resolve
from tests.support import Harness


class ContractCases:
    binding = "inprocess"
    atom_provider = "detta"

    def setUp(self):
        self.h = Harness(self.binding, atom_provider=self.atom_provider)
        self.addCleanup(self.h.close)
        self.a, self.b = self.h.a, self.h.b

    def error(self, code, call):
        with self.assertRaises(ContractError) as cm:
            call()
        self.assertEqual(cm.exception.code, code)

    def atom(self):
        return self.a.store(b"non-sensitive fixture\x00\xff\n", "atom-1")["ref"]

    def test_slice_and_delayed_restart_completion(self):
        ref = self.atom()
        receipt = self.a.share(ref, "reply-B", "share-1")
        self.assertEqual(receipt["delivery"], "not-observed")
        delivered = self.b.poll()
        self.assertEqual(delivered, self.b.poll())
        self.assertEqual(self.b.retrieve(delivered["body"]["ref"]), b"non-sensitive fixture\x00\xff\n")
        self.b.ack(delivered["delivery_id"], "ack-1")
        self.assertIsNone(self.b.poll())
        job = self.a.delegate(ref, "job-1")
        self.error("NOT_AVAILABLE", lambda: self.a.result(job["job_id"]))
        self.assertTrue(self.h.command("work")["ok"]["worked"])
        self.assertEqual(self.a.status(job["job_id"])["completion_delivery"], "not-observed")
        self.assertIsNone(self.a.poll())
        self.assertEqual(self.h.command("flush")["ok"]["sent"], 1)
        restarted = self.h.peer("A")
        result = restarted.result(job["job_id"])
        body = json.loads(restarted.retrieve(result["ref"]))
        self.assertEqual(body["digest"], ref["digest"])
        self.assertEqual(body["length"], len(b"non-sensitive fixture\x00\xff\n"))
        completion = restarted.poll()
        self.assertEqual(completion["body"]["correlation_id"], "job-1")
        self.assertEqual(completion["body"]["result"], result)
        self.assertIsNone(restarted.status(job["job_id"])["chain"])

    def test_idempotency_conflict_and_occurrence_identity(self):
        ref = self.atom()
        self.assertEqual(self.atom(), ref)
        self.error("CONFLICT", lambda: self.a.store(b"changed", "atom-1"))
        other = self.a.store(b"non-sensitive fixture\x00\xff\n", "atom-2")["ref"]
        self.assertNotEqual(other["id"], ref["id"])
        first = self.a.delegate(ref, "once")
        self.assertEqual(first, self.a.delegate(ref, "once"))
        self.error("CONFLICT", lambda: self.a.delegate(other, "once"))
        self.h.command("work")
        self.assertEqual(first, self.a.delegate(ref, "once"))
        self.assertFalse(self.h.command("work")["ok"]["worked"])
        self.h.command("flush")
        self.h.command("flush")
        counts = self.h.counts()
        self.assertEqual((counts["jobs"], counts["outbox"], counts["messages"]), (1, 1, 1))

    def test_scope_routes_authentication_revocation_and_state_ownership(self):
        ref = self.atom()
        self.error("UNAUTHORIZED", lambda: self.h.outsider.retrieve(ref))
        self.error("UNAUTHORIZED", lambda: self.a.retrieve({**ref, "scope_ref": "elsewhere"}))
        self.error("UNAUTHORIZED", lambda: self.a.call("agent.messaging", "poll", {"route": "reply-B"}))
        self.error("UNAUTHORIZED", lambda: self.a.delegate(ref, "redirect", reply_route="reply-B"))
        request = self.a.request("atom.storage", "get", {"ref": ref}, sender="B")
        self.error("INVALID_ARGUMENT", lambda: self.a.binding.invoke(request))
        for name, operation in (("execution", "setStatus"), ("belief.revision", "submitEvidence"),
                                ("attention", "setAttention"), ("episodic.memory", "appendEvent")):
            request = {"message_id": "x", "interface_ref": {"id": name, "version": "1.0.0"},
                       "profile": "inspect-atom/1", "scope_ref": "shared-test", "operation": operation, "body": {}}
            self.error("UNSUPPORTED_OPERATION", lambda: self.a.binding.invoke(request))
        job = self.a.delegate(ref, "owner-check")
        self.error("NOT_FOUND", lambda: self.b.status(job["job_id"]))
        self.h.config["principals"]["A"]["scopes"] = {}
        self.h.save()
        self.error("UNAUTHORIZED", lambda: self.a.retrieve(ref))
        self.error("UNAUTHORIZED", lambda: self.a.store(b"non-sensitive fixture\x00\xff\n", "atom-1"))
        self.assertEqual(self.h.command("work")["ok"]["execution"], "failed")

    def test_reference_integrity_missing_and_unavailable_are_distinct(self):
        ref = self.atom()
        self.error("NOT_FOUND", lambda: self.a.retrieve({**ref, "id": "absent"}))
        self.error("CONFLICT", lambda: self.a.retrieve({**ref, "digest": "0" * 64}))
        self.assertTrue(self.a.call("atom.storage", "availability", {"ref": ref})["available"])
        self.assertEqual(len(self.a.call("atom.storage", "getMany", {"refs": [ref, ref]})["atoms"]), 2)
        # Remove actual DA files; the journal cannot answer from cached bytes.
        import shutil
        shutil.rmtree(self.h.config["da_root"])
        self.error("NOT_AVAILABLE", lambda: self.a.retrieve(ref))

    def test_wire_validation_versions_features_deadlines(self):
        ref = self.atom()
        for field, value, code in (("interface_ref", {"id": "atom.storage", "version": "2.0.0"}, "UNSUPPORTED_VERSION"),
                                   ("profile", "unknown/1", "UNSUPPORTED_PROFILE"),
                                   ("required_features", ["owner-bypass"], "UNSUPPORTED_PROFILE"),
                                   ("deadline_ms", 1, "DEADLINE_EXCEEDED")):
            request = self.a.request("atom.storage", "get", {"ref": ref})
            request[field] = value
            self.error(code, lambda: self.a.binding.invoke(request))
        self.a.call("atom.storage", "get", {"ref": ref}, extensions={"future-optional": 1})
        for payload in ("", "!!!", "Zg===", encode(b"x" * 65537)):
            self.error("INVALID_ARGUMENT", lambda: self.a.call("atom.storage", "create", {
                "bytes": payload, "sharing": "non-sensitive-fixture", "content_type": "text/plain"}, "bad"))
        self.error("UNAUTHORIZED", lambda: self.a.call("atom.storage", "create", {
            "bytes": encode(b"x"), "sharing": "private", "content_type": "text/plain"}, "private"))
        self.error("UNSUPPORTED_OPERATION", lambda: self.a.call("execution", "submit", {
            "ref": ref, "operation": "shell"}, "no-shell", "no-shell"))

    def test_backpressure_keeps_outbox_until_consumer_ack(self):
        self.h.config["capacity"] = 1
        self.h.save()
        ref = self.atom()
        self.b.share(ref, "reply-A", "fill-inbox")
        first = self.a.delegate(ref, "first")
        self.error("OVERLOADED", lambda: self.a.delegate(ref, "second"))
        self.h.command("work")
        self.assertEqual(self.h.command("flush")["ok"], {"sent": 0, "pending": 1})
        self.error("OVERLOADED", lambda: self.a.delegate(ref, "second"))
        self.a.ack(self.a.poll()["delivery_id"], "free-space")
        self.assertEqual(self.h.command("flush")["ok"], {"sent": 1, "pending": 0})
        self.assertEqual(self.a.poll()["body"]["job_id"], first["job_id"])
        self.a.delegate(ref, "second")

    def test_durable_acceptance_survives_sigkill_before_ack(self):
        ref = self.atom()
        request = self.a.request("execution", "submit", {"operation": "inspect_atom", "ref": ref}, "killed-accept", "killed-accept")
        self.h.kill_at("rpc", "after_acceptance", request)
        accepted = self.a.binding.invoke(request)
        self.assertEqual(self.a.status(accepted["job_id"])["execution"], "queued")
        self.h.command("work")
        self.assertEqual(self.a.status(accepted["job_id"])["execution"], "succeeded")

    def test_lost_ack_can_replay_after_deadline_but_worker_will_not_start(self):
        ref = self.atom()
        deadline = time.time_ns() // 1_000_000 + 500
        accepted = self.a.delegate(ref, "deadline-replay", deadline_ms=deadline)
        time.sleep(.55)
        self.assertEqual(self.a.delegate(ref, "deadline-replay", deadline_ms=deadline), accepted)
        self.assertEqual(self.h.command("work")["ok"]["execution"], "failed")
        self.assertEqual(self.a.status(accepted["job_id"])["error"], "DEADLINE_EXCEEDED")
        self.error("DEADLINE_EXCEEDED", lambda: self.a.result(accepted["job_id"]))

    def test_result_da_write_replay_and_completion_outbox_crashes(self):
        ref = self.atom()
        job = self.a.delegate(ref, "crash-result")
        self.h.kill_at("work", "after_result_persist")
        self.assertEqual(self.a.status(job["job_id"])["execution"], "queued")
        self.h.kill_at("work", "after_completion_commit")
        self.assertEqual(self.a.status(job["job_id"])["execution"], "succeeded")
        self.assertIsNone(self.a.poll())
        self.h.command("work")
        self.h.command("flush")
        self.assertEqual(self.a.poll()["body"]["job_id"], job["job_id"])
        counts = self.h.counts()
        self.assertEqual(counts["atoms"], 2)
        self.assertEqual(counts["outbox"], 1)


class InProcessContract(ContractCases, unittest.TestCase):
    binding = "inprocess"


class SubprocessContract(ContractCases, unittest.TestCase):
    binding = "subprocess"


class FixtureInProcessContract(ContractCases, unittest.TestCase):
    binding = "inprocess"
    atom_provider = "fixture-files"


class FixtureSubprocessContract(ContractCases, unittest.TestCase):
    binding = "subprocess"
    atom_provider = "fixture-files"


class Compatibility(unittest.TestCase):
    def test_same_major_positive_and_negative_fixtures(self):
        p = descriptors("inprocess")[0]
        r = Requirement(p.interface, "1.0.0", "2.0.0", next(iter(p.profiles)), p.operations, p.guarantees)
        self.assertEqual(resolve([replace(p, version="1.2.3")], r).version, "1.2.3")
        for change, code in (({"version": "2.0.0"}, "UNSUPPORTED_VERSION"),
                             ({"profiles": frozenset()}, "UNSUPPORTED_PROFILE"),
                             ({"operations": frozenset()}, "UNSUPPORTED_OPERATION"),
                             ({"guarantees": frozenset()}, "NOT_AVAILABLE"),
                             ({"max_payload_bytes": 0}, "NOT_AVAILABLE")):
            with self.assertRaises(ContractError) as cm:
                resolve([replace(p, **change)], r)
            self.assertEqual(cm.exception.code, code)
        for requirement in (replace(r, features=frozenset({"unknown"})),
                            replace(r, privacy="private"), replace(r, verification="proof-required"),
                            replace(r, max_latency_ms=1)):
            with self.assertRaises(ContractError):
                resolve([replace(p, verified_evidence=("unverified-proof-string",))], requirement)

    def test_contract_imports_no_backends_or_cognition(self):
        import ast
        root = Path(__file__).resolve().parents[1]
        for name in ("contracts.py", "client.py", "registry.py", "service.py"):
            tree = ast.parse((root / "fusion" / name).read_text())
            imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
            self.assertFalse(any(any(bad in module for bad in ("adapters", "detta", "pln", "ecan", "hyperon")) for module in imports))
