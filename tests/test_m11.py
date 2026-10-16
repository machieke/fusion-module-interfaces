"""M1.1 module-swap and independent-commit regressions; fixtures stay labelled."""
import ast
import copy
from dataclasses import replace
import inspect
import json
from pathlib import Path
import shutil
import sqlite3
import time
import typing
import unittest

from fusion.atoms import AtomOwner, AuthorizedAtoms
from fusion.adapters.fixture_atoms import FileAtomFixture
from fusion.bindings import InProcess, Subprocess
from fusion.composition import service
from fusion.contracts import ContractError, canonical, digest, encode, LEGACY_PROFILES
from fusion.execution import ExecutionOwner, ExecutionSession
from fusion.messaging import MessageOwner, MessagingSession
from fusion.ports import AtomStorage, CompletionDelivery, DelegatedExecution, Messaging, Mutation
from fusion.registry import descriptors, select, selection_token
from fusion.responses import validate_reply
from tests.support import Harness, ROOT


class RecoveryCases:
    binding = "inprocess"
    atom_provider = "detta"

    def setUp(self):
        self.h = Harness(self.binding, atom_provider=self.atom_provider)
        self.addCleanup(self.h.close)
        self.a = self.h.a
        self.ref = self.a.store(b"m11-independent-ownership", "input")["ref"]

    def test_result_commits_before_job_and_public_port_replay_is_stable(self):
        job = self.a.delegate(self.ref, "result-replay")
        self.h.kill_at("work", "after_result_persist")
        self.assertEqual(self.a.status(job["job_id"])["execution"], "queued")
        self.assertEqual(self.h.counts()["atoms"], 2)
        output = canonical({"digest": self.ref["digest"], "length": len(b"m11-independent-ownership"),
                            "operation": "inspect_atom", "provider_version": "0.1.0"})
        owner = service(self.h.path)
        try:
            # Only the public AtomStorage port is used to replay the worker-owned mutation.
            durable = owner.atoms_for("worker").create(Mutation("shared-test", "result/"+job["job_id"]),
                                                        "application/json", output)
        finally:
            owner.close()
        self.assertEqual(self.h.counts()["atoms"], 2)
        self.h.command("work")
        self.assertEqual(self.a.result(job["job_id"]), durable)
        self.assertEqual(self.h.counts()["atoms"], 2)

    def test_mailbox_acceptance_survives_outbox_marking_crash(self):
        job = self.a.delegate(self.ref, "delivery-replay")
        self.h.command("work")
        self.h.kill_at("flush", "after_delivery_accept")
        message = self.a.poll()
        self.assertEqual(message["body"]["job_id"], job["job_id"])
        self.assertEqual(self.a.status(job["job_id"])["completion_delivery"], "not-observed")
        self.a.ack(message["delivery_id"], "already-acknowledged")
        self.assertEqual(self.h.command("flush")["ok"], {"sent": 1, "pending": 0})
        self.assertIsNone(self.a.poll())
        self.assertEqual(self.h.counts()["messages"], 1)

    def test_atom_persistence_before_admission_commit_retains_full_intent(self):
        request = self.a.request("atom.storage", "create", {"content_type": "text/plain",
            "bytes": encode(b"new-payload"), "sharing": "non-sensitive-fixture"}, "create-crash",
            deadline_ms=time.time_ns()//1_000_000+60000)
        self.h.kill_at("rpc", "after_atom_persist", request)
        changed = copy.deepcopy(request)
        changed["deadline_ms"] += 1
        with self.assertRaises(ContractError) as cm:
            self.a.binding.invoke(changed)
        self.assertEqual(cm.exception.code, "CONFLICT")
        accepted = self.a.binding.invoke(request)
        self.assertEqual(self.a.binding.invoke(request), accepted)
        self.assertEqual(self.h.counts()["atoms"], 2)

    def test_unavailable_input_keeps_accepted_job_for_recovery(self):
        job = self.a.delegate(self.ref, "temporary-input-loss")
        backup = self.h.root / "payload-backup"
        shutil.copytree(self.h.config["da_root"], backup)
        shutil.rmtree(self.h.config["da_root"])
        self.assertEqual(self.h.command("work")["error"]["code"], "NOT_AVAILABLE")
        self.assertEqual(self.a.status(job["job_id"])["execution"], "queued")
        shutil.rmtree(self.h.config["da_root"])
        shutil.copytree(backup, self.h.config["da_root"])
        self.h.command("work")
        self.assertEqual(self.a.status(job["job_id"])["execution"], "succeeded")

    def test_worker_revocation_is_effective_at_restart(self):
        job = self.a.delegate(self.ref, "worker-revoked")
        self.h.config["principals"]["worker"]["scopes"]["shared-test"].remove("atom.storage.create")
        self.h.save()
        self.assertEqual(self.h.command("work")["ok"]["execution"], "failed")
        self.assertEqual(self.a.status(job["job_id"])["error"], "UNAUTHORIZED")
        self.assertEqual(self.h.counts()["atoms"], 1)
        self.h.config["principals"]["worker"]["scopes"] = {}
        self.h.save()
        with self.assertRaises(ContractError) as cm:
            self.a.delegate(self.ref, "read-revoked")
        self.assertEqual(cm.exception.code, "UNAUTHORIZED")

    def test_ack_replay_rechecks_current_route_ownership(self):
        sent = self.a.share(self.ref, "reply-B", "route-replay")
        self.h.b.ack(sent["delivery_id"], "ack-replay")
        self.h.config["routes"]["reply-B"]["owner"] = "A"
        self.h.save()
        with self.assertRaises(ContractError) as cm:
            self.h.b.ack(sent["delivery_id"], "ack-replay")
        self.assertEqual(cm.exception.code, "UNAUTHORIZED")

    def test_revoked_reply_route_retains_outbox_until_restored(self):
        self.a.delegate(self.ref, "reply-revoked")
        self.h.command("work")
        route = self.h.config["routes"].pop("reply-A")
        self.h.save()
        self.assertEqual(self.h.command("flush")["ok"], {"sent": 0, "pending": 1})
        self.h.config["routes"]["reply-A"] = route
        self.h.save()
        self.assertEqual(self.h.command("flush")["ok"], {"sent": 1, "pending": 0})
        self.assertEqual(self.a.poll()["body"]["correlation_id"], "reply-revoked")

    def test_legacy_profiles_remain_explicit_and_neutral_profiles_are_distinct(self):
        sent = self.a.call("agent.messaging", "send", {"ref": self.ref, "route": "reply-B"},
                           "legacy-send", "legacy-send", profile=LEGACY_PROFILES["agent.messaging"])
        self.assertEqual(set(sent), {"delivery_id", "delivery", "acceptance"})
        self.assertEqual(sent["acceptance"], "sqlite-full")
        delivery = self.h.b.call("agent.messaging", "poll", {"route": "reply-B"}, profile="durable-mailbox/1")["delivery"]
        self.assertEqual(set(delivery), {"delivery_id", "body", "order", "delivery"})
        ack = self.h.b.call("agent.messaging", "ack", {"route": "reply-B", "delivery_id": delivery["delivery_id"]},
                           "legacy-ack", profile="durable-mailbox/1")
        self.assertEqual(ack["persistence"], "sqlite-full")
        job = self.a.delegate(self.ref, "legacy-job", profile="inspect-atom/1")
        self.assertEqual(job["acceptance"], "sqlite-full")
        self.h.command("work")
        status = self.a.call("execution", "status", {"job_id": job["job_id"]}, profile="inspect-atom/1")
        self.assertNotIn("correlation_id", status)
        modern = self.a.delegate(self.ref, "neutral-job")
        self.assertEqual(modern["acceptance"], "process-restart")
        self.assertEqual(modern["evidence"]["backend"], "sqlite")


class DettaInProcessRecovery(RecoveryCases, unittest.TestCase):
    pass


class DettaSubprocessRecovery(RecoveryCases, unittest.TestCase):
    binding = "subprocess"


class FixtureInProcessRecovery(RecoveryCases, unittest.TestCase):
    atom_provider = "fixture-files"


class FixtureSubprocessRecovery(RecoveryCases, unittest.TestCase):
    binding = "subprocess"
    atom_provider = "fixture-files"


class PortStructure(unittest.TestCase):
    def test_fixture_opaque_id_never_resolves_as_a_filesystem_path(self):
        for binding in ("inprocess", "subprocess"):
            h = Harness(binding, atom_provider="fixture-files")
            self.addCleanup(h.close)
            ref = h.a.store(b"path-boundary", "input")["ref"]
            ref["id"] = "../config"
            for operation in ("get", "availability"):
                with self.assertRaises(ContractError) as cm:
                    h.a.call("atom.storage", operation, {"ref": ref})
                self.assertEqual(cm.exception.code, "NOT_FOUND")

    def test_combined_legacy_journal_is_rejected_without_dropping_it(self):
        h = Harness("inprocess", atom_provider="fixture-files")
        self.addCleanup(h.close)
        with sqlite3.connect(h.config["database"]) as db:
            db.execute("CREATE TABLE atoms (preserved TEXT)")
            db.execute("INSERT INTO atoms VALUES ('old-metadata')")
        with self.assertRaises(ContractError) as cm:
            service(h.path)
        self.assertEqual(cm.exception.code, "UNSUPPORTED_PROFILE")
        with sqlite3.connect(h.config["database"]) as db:
            self.assertEqual(db.execute("SELECT preserved FROM atoms").fetchone()[0], "old-metadata")

    def test_published_signatures_match_exercised_providers(self):
        for protocol, providers in ((AtomStorage, (AtomOwner, FileAtomFixture, AuthorizedAtoms)),
                                    (Messaging, (MessagingSession,)), (DelegatedExecution, (ExecutionSession,)),
                                    (CompletionDelivery, (MessageOwner,))):
            methods = [(name, method) for name, method in vars(protocol).items()
                       if not name.startswith("_") and inspect.isfunction(method)]
            for name, method in methods:
                for provider in providers:
                    actual = getattr(provider, name)
                    self.assertEqual(tuple(inspect.signature(actual).parameters), tuple(inspect.signature(method).parameters))
                    self.assertEqual(typing.get_type_hints(actual), typing.get_type_hints(method), (provider.__name__, name))

    def test_execution_uses_only_declared_foreign_ports_and_own_sql(self):
        tree = ast.parse((ROOT / "fusion/execution.py").read_text())
        atom_calls, message_calls, sql = set(), set(), []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute):
                if node.value.attr == "atoms": atom_calls.add(node.attr)
                if node.value.attr == "messages": message_calls.add(node.attr)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if any(word in node.value.upper() for word in ("SELECT ", "INSERT ", "UPDATE ")): sql.append(node.value)
        self.assertEqual(atom_calls, {"get", "create"})
        self.assertEqual(message_calls, {"accept"})
        self.assertFalse(any(word in statement.lower() for statement in sql for word in (" atoms ", " messages ")))
        self.assertFalse(issubclass(FileAtomFixture, AtomOwner))
        for filename in ("ports.py", "contracts.py", "service.py", "execution.py", "messaging.py", "client.py"):
            tree = ast.parse((ROOT / "fusion" / filename).read_text())
            self.assertFalse(any(isinstance(node, ast.ImportFrom) and node.module and "adapters" in node.module for node in ast.walk(tree)))

    def test_hostile_port_denies_every_undeclared_attribute_at_runtime(self):
        h = Harness("inprocess", atom_provider="fixture-files")
        self.addCleanup(h.close)
        ref = h.a.store(b"hostile-boundary", "input")["ref"]
        job = h.a.delegate(ref, "job")
        class Hostile:
            def __init__(self, port, allowed):
                object.__setattr__(self, "_target", port)
                object.__setattr__(self, "_allowed", allowed)
            def __getattribute__(self, name):
                if name not in object.__getattribute__(self, "_allowed"):
                    raise AssertionError("Private access: "+name)
                return getattr(object.__getattribute__(self, "_target"), name)
        owner = service(h.path)
        try:
            owner.worker.atoms = Hostile(owner.worker.atoms, {"create", "get", "getMany", "availability"})
            owner.worker.messages = Hostile(owner.worker.messages, {"accept"})
            owner.work(); owner.flush()
        finally:
            owner.close()
        self.assertEqual(h.a.poll()["body"]["job_id"], job["job_id"])

    def test_weaker_guarantees_and_changed_selected_provider_are_rejected(self):
        offered = descriptors(atom_provider="fixture-files")
        with self.assertRaises(ContractError):
            select([replace(p, guarantees=frozenset({"scoped"})) if p.interface=="atom.storage" else p for p in offered])
        for binding_name in ("inprocess", "subprocess"):
            with self.subTest(binding=binding_name):
                h = Harness(binding_name, atom_provider="fixture-files")
                self.addCleanup(h.close)
                selected = dict(h.a.binding.selected)
                selected["atom.storage"] = replace(selected["atom.storage"], provider="not-the-selected-provider")
                credential = h.config["principals"]["A"]["credential"]
                binding = InProcess(lambda: service(h.path), credential, selected) if binding_name=="inprocess" else Subprocess(h.path, credential, selected)
                req = h.a.request("atom.storage", "create", {"content_type":"text/plain", "bytes":encode(b"x"), "sharing":"non-sensitive-fixture"}, "x")
                with self.assertRaises(ContractError) as cm: binding.invoke(req)
                self.assertEqual(cm.exception.code, "UNSUPPORTED_PROFILE")
