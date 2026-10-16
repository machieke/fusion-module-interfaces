import copy
import json
from pathlib import Path
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor

from jsonschema import Draft202012Validator

from fusion.contracts import ContractError, validate
from fusion.adapters.f1r3 import F1R3HTTP, F1R3Commitments
from fusion.adapters.detta import DettaStorage
from fusion.ports import ApprovedCommitment, Mutation, ChainObservation
from scripts.schema import schema
from tests.support import Harness, ROOT


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness("subprocess")
        self.addCleanup(self.h.close)

    def test_reconstruct_after_two_missing_shares_and_fail_after_three(self):
        receipt = self.h.a.store(b"reconstruct-this-generated-fixture", "erasure")
        ref = receipt["ref"]
        manifest = receipt["receipt"]["evidence"]["manifest"]
        encoded_id = manifest.encode().hex()
        directory = Path(self.h.config["da_root"]) / "da/applications"
        # Remove both the full cached payload and two shards; require real reconstruction.
        (directory / "payloads" / (encoded_id + ".bin")).unlink()
        shares = directory / "shares" / encoded_id
        for index in (0, 1):
            (shares / f"{index}.bin").unlink()
        self.assertEqual(self.h.b.retrieve(ref), b"reconstruct-this-generated-fixture")
        observation = self.h.b.call("atom.storage", "availability", {"ref": ref})
        self.assertEqual(observation["present_shares"], 4)
        (shares / "2.bin").unlink()
        with self.assertRaises(ContractError) as cm:
            self.h.b.retrieve(ref)
        self.assertEqual(cm.exception.code, "NOT_AVAILABLE")

    def test_corrupt_share_is_never_returned_as_payload(self):
        receipt = self.h.a.store(b"integrity-fixture", "corrupt")
        manifest = receipt["receipt"]["evidence"]["manifest"]
        file = Path(self.h.config["da_root"]) / "da/applications/shares" / manifest.encode().hex() / "0.bin"
        file.write_bytes(b"corrupt")
        with self.assertRaises(ContractError) as cm:
            self.h.b.retrieve(receipt["ref"])
        self.assertEqual(cm.exception.code, "NOT_AVAILABLE")

    def test_generic_storage_scope_binding_rejects_wrong_scope(self):
        import fcntl
        storage = DettaStorage(self.h.config["detta_binary"], self.h.config["da_root"])
        payload, receipt = storage.put("scope-one", "opaque-key", b"opaque-fixture")
        self.assertEqual(storage.get("scope-one", payload), b"opaque-fixture")
        with self.assertRaises(ContractError) as cm:
            storage.get("scope-two", payload)
        self.assertEqual(cm.exception.code, "UNAUTHORIZED")
        with open(Path(self.h.config["da_root"]) / ".port.lock", "a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(ContractError) as cm:
                storage.get("scope-one", payload)
            self.assertEqual(cm.exception.code, "OVERLOADED")

    def test_simultaneous_duplicate_submission_has_one_logical_job(self):
        ref = self.h.a.store(b"concurrent-fixture", "atom")["ref"]
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: self.h.peer("A").delegate(ref, "concurrent"), range(4)))
        self.assertTrue(all(value == results[0] for value in results))
        with sqlite3.connect(self.h.config["database"]) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)

    def test_schema_is_reproducible_and_positive_negative_fixtures_agree(self):
        spec = schema()
        self.assertEqual(spec, json.loads((ROOT / "contracts/wire.schema.json").read_text()))
        Draft202012Validator.check_schema(spec)
        validator = Draft202012Validator(spec)
        ref = self.h.a.store(b"schema-fixture", "atom")["ref"]
        good = self.h.a.request("execution", "submit", {"operation": "inspect_atom", "ref": ref}, "key", "corr")
        validator.validate(good)
        validate(good)
        for mutate in (lambda r: r.pop("idempotency_key"),
                       lambda r: r.update(sender="admin"),
                       lambda r: r["body"].update(operation="shell"),
                       lambda r: r.update(required_features=["unsafe"]),
                       lambda r: r["interface_ref"].update(version="2.0.0")):
            bad = copy.deepcopy(good)
            mutate(bad)
            self.assertTrue(list(validator.iter_errors(bad)))
            with self.assertRaises(ContractError):
                validate(bad)


class ChainObservationTests(unittest.TestCase):
    def test_signed_intent_survives_uncertain_submission_without_resigning(self):
        import tempfile
        from dataclasses import replace
        class TransportFixture:
            def __init__(self):
                self.calls = []
            def submit_signed(self, signed):
                self.calls.append(signed)
                if len(self.calls) == 1:
                    raise ContractError("NOT_AVAILABLE")
                return ChainObservation(signed["signature"], None, "pending", {})
        api, signatures = TransportFixture(), []
        def signer(value):
            signatures.append(value)
            return {"signature": "a" * 140}
        ref = {"scope_ref": "shared", "id": "result", "digest": "d" * 64, "revision": 1}
        approved = ApprovedCommitment("shared", ref, "d" * 64, "registered-fixture")
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "intents.db")
            owner = F1R3Commitments(api, signer, path, approved)
            with self.assertRaises(ContractError):
                owner.submit(Mutation("shared", "once"), approved)
            restarted = F1R3Commitments(api, signer, path, approved)
            observed = restarted.submit(Mutation("shared", "once"), approved)
            self.assertEqual(restarted.submit(Mutation("shared", "once"), approved), observed)
            self.assertEqual(len(signatures), 1)
            self.assertEqual(api.calls[0], api.calls[1])
            with self.assertRaises(ContractError) as cm:
                restarted.submit(Mutation("shared", "forbidden"), replace(approved, approval_record="unregistered"))
            self.assertEqual(cm.exception.code, "UNAUTHORIZED")
            alternate = replace(approved, approval_record="new-registration")
            other_owner = F1R3Commitments(api, signer, path, alternate)
            with self.assertRaises(ContractError) as cm:
                other_owner.submit(Mutation("shared", "once"), alternate)
            self.assertEqual(cm.exception.code, "CONFLICT")
            ref["digest"] = "e" * 64
            with self.assertRaises(ContractError) as cm:
                restarted.submit(Mutation("shared", "mutated"), approved)
            self.assertEqual(cm.exception.code, "UNAUTHORIZED")

    def test_pending_inclusion_and_deploy_effect_finality_stay_distinct(self):
        adapter = F1R3HTTP("http://127.0.0.1:1")
        for state, block, expected in (("Pending", None, "pending"),
                                       ("Pending", "b" * 64, "included"),
                                       ("Finalized", "b" * 64, "finalized"),
                                       ("Failed", "b" * 64, "rejected"),
                                       ("Expired", None, "rejected")):
            adapter.request = lambda _, s=state, b=block: {"state": s, "latest_block_hash": b, "rejection_count": 0}
            self.assertEqual(adapter.observe("a" * 140).effect_finality, expected)
        for malformed in ({"state": "Finalized", "latest_block_hash": None, "rejection_count": 0},
                          {"state": "Finalized", "latest_block_hash": "synthetic", "rejection_count": 0},
                          {"state": "Unknown", "latest_block_hash": None, "rejection_count": 0},
                          {"state": "Pending", "latest_block_hash": None, "rejection_count": True}):
            adapter.request = lambda _, result=malformed: result
            with self.assertRaises(ContractError) as cm:
                adapter.observe("a" * 140)
            self.assertEqual(cm.exception.code, "NOT_AVAILABLE")
