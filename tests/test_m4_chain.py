"""Transport/state fixtures only. These never claim the real CHAIN gate."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest

from fusion.adapters.f1r3_m4 import (GeneratedCommitments, PROFILE, SOURCE, DESCRIPTOR,
    NAMESPACE, select_chain, observe_effect, expected_expr)
from fusion.contracts import ContractError, canonical
from fusion.ports import ApprovedCommitment, ChainObservation, Mutation
from fusion.registry import selection_token


class API:
    def __init__(self):
        self.chain = {"network": "fusion-m4-isolated", "shard": "fusion-m4", "genesis": "a" * 64,
                      "profile": PROFILE, "source": SOURCE}
        self.sent, self.responses, self.drop = [], {}, False

    def request(self, path, body=None):
        if path in self.responses:
            return deepcopy(self.responses[path])
        if path == "/api/status":
            return {"networkId": self.chain["network"], "shardId": self.chain["shard"], "isReady": True,
                    "peers": 0, "nodes": 0, "version": {"api": "1", "node": "F1r3node Rust 0.4.15 (9ec1096)"}}
        if path == "/api/blocks/0/0?view=summary":
            return [{"blockInfo": {"blockNumber": 0, "blockHash": self.chain["genesis"], "shardId": self.chain["shard"], "isFinalized": True}}]
        if path == "/api/prepare-deploy":
            return {"names": ["c" * 64]}
        raise AssertionError(path)

    def submit_signed(self, signed):
        self.sent.append(deepcopy(signed))
        if self.drop:
            raise ContractError("NOT_AVAILABLE")
        return ChainObservation(signed["signature"], None, "pending", {"submission_response": "fixture"})


class ChainFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "chain.db"
        self.api = API()
        self.approved = ApprovedCommitment("shared-test", {"scope_ref": "shared-test", "id": "generated", "revision": 1, "digest": "d" * 64}, "d" * 64, "registered-generated")
        self.binding = {"profile": PROFILE, "chain": deepcopy(self.api.chain), "selection": selection_token(DESCRIPTOR),
            "operation": "generated-m4-12", "signer": "04" + "f" * 128,
            "limits": {"phloPrice": 1, "phloLimit": 10000000, "validAfterBlockNumber": 0}}
        self.command = Mutation("shared-test", "generated-m4-12")
        self.signs, self.allowed = [], True

    def authorize(self):
        if not self.allowed:
            raise ContractError("UNAUTHORIZED")

    def sign(self, plan):
        with sqlite3.connect(self.path) as db:
            assert db.execute("SELECT plan FROM m4_intent").fetchone()[0] == canonical(plan).decode()
        self.signs.append(deepcopy(plan))
        return {"data": plan, "deployer": self.binding["signer"], "signature": "ab" * 70, "sigAlgorithm": "secp256k1"}

    def owner(self, hook=lambda _: None, binding=None):
        return GeneratedCommitments(self.api, self.sign, self.path, self.approved,
                                    binding or self.binding, self.authorize, hook)

    def rejected(self, code, call):
        with self.assertRaises(ContractError) as caught:
            call()
        self.assertEqual(caught.exception.code, code)

    def finalized(self):
        owner = self.owner()
        result = owner.submit(self.command, self.approved)
        signed = self.api.sent[0]
        block = "b" * 64
        self.api.responses["/api/deploy-finalization-status/" + result.deploy_id] = {
            "state": "Finalized", "rejection_count": 0, "latest_block_hash": block}
        self.api.responses["/api/deploy/" + result.deploy_id] = {
            "deployId": result.deploy_id, "blockHash": block, "blockNumber": 1, "errored": False,
            "cost": 603, "isFinalized": True, "finalizationState": "Finalized", "rejectionCount": 0,
            "deployer": signed["deployer"], "sigAlgorithm": "secp256k1", **{k: v for k, v in signed["data"].items() if k != "expiration_timestamp"}}
        self.api.responses["/api/data-at-name-by-block-hash"] = {"expr": expected_expr(self.binding["operation"], "d" * 64),
            "block": {"blockHash": block, "blockNumber": 1, "postStateHash": "e" * 64, "shardId": "fusion-m4", "isFinalized": True}, "cost": 0}
        return owner, result.deploy_id

    def test_durable_logical_intent_precedes_signing_and_exact_replay(self):
        first = self.owner().submit(self.command, self.approved)
        self.assertEqual(self.owner().submit(self.command, self.approved), first)
        self.assertEqual((len(self.signs), len(self.api.sent)), (1, 1))

    def test_mutating_input_aliases_cannot_change_registered_approval_or_binding(self):
        original = deepcopy(self.approved)
        owner = self.owner()
        self.approved.result_ref['digest'] = 'e' * 64
        self.rejected('UNAUTHORIZED', lambda: owner.submit(self.command, self.approved))
        self.binding['chain']['genesis'] = 'b' * 64
        self.binding['limits']['phloLimit'] = 1
        self.binding['operation'] = 'another'
        result = owner.submit(self.command, original)
        self.assertEqual(result.effect_finality, 'pending')
        self.assertEqual(self.signs[0]['phloLimit'], 10000000)
        self.assertIn('generated-m4-12', self.signs[0]['term'])
        self.assertEqual(len(self.signs), 1)

    def test_response_loss_keeps_every_signed_byte_and_timestamp(self):
        self.api.drop = True
        self.rejected("NOT_AVAILABLE", lambda: self.owner().submit(self.command, self.approved))
        first = canonical(self.api.sent[0])
        self.api.drop = False
        self.owner().submit(self.command, self.approved)
        self.assertEqual(canonical(self.api.sent[1]), first)
        self.assertEqual(len(self.signs), 1)

    def test_revocation_before_cached_reply_and_before_send(self):
        owner = self.owner()
        owner.submit(self.command, self.approved)
        self.allowed = False
        self.rejected("UNAUTHORIZED", lambda: owner.submit(self.command, self.approved))
        self.assertEqual(len(self.api.sent), 1)
        self.allowed = True
        self.path = Path(self.temp.name) / "second.db"
        def revoke(stage):
            if stage == "after_signed_intent": self.allowed = False
        self.rejected("UNAUTHORIZED", lambda: self.owner(revoke).submit(self.command, self.approved))
        self.assertEqual(len(self.api.sent), 1)

    def test_wrong_approval_scope_ref_digest_key_and_intent(self):
        owner = self.owner()
        for approved in (replace(self.approved, approval_record="invented"), replace(self.approved, scope_ref="private"),
                         replace(self.approved, commitment_digest="e" * 64),
                         replace(self.approved, result_ref={**self.approved.result_ref, "id": "another"})):
            self.rejected("UNAUTHORIZED", lambda: owner.submit(self.command, approved))
        self.rejected("UNAUTHORIZED", lambda: owner.submit(Mutation("private", self.command.idempotency_key), self.approved))
        self.rejected("CONFLICT", lambda: owner.submit(Mutation("shared-test", "another"), self.approved))
        self.rejected("CONFLICT", lambda: owner.submit(replace(self.command, intent_digest="a" * 64), self.approved))
        self.assertEqual(self.signs, [])

    def test_wrong_chain_binding_signer_and_profile(self):
        self.owner().submit(self.command, self.approved)
        for field, value in (("signer", "04" + "e" * 128), ("operation", "another"),
                             ("chain", {**self.binding["chain"], "genesis": "b" * 64})):
            self.rejected("CONFLICT", lambda: self.owner(binding={**self.binding, field: value}))
        self.rejected("UNSUPPORTED_PROFILE", lambda: self.owner(binding={**self.binding, "profile": "old/1"}))
        self.api.chain["genesis"] = "b" * 64
        self.rejected("CONFLICT", lambda: self.owner().submit(self.command, self.approved))
        self.assertEqual(len(self.api.sent), 1)
        self.rejected("UNSUPPORTED_PROFILE", lambda: select_chain(replace(DESCRIPTOR, implementation_version="9.0.0")))

    def test_concurrent_duplicates_sign_one_durable_deploy(self):
        owner = self.owner()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: owner.submit(self.command, self.approved), range(4)))
        self.assertEqual(len(self.signs), 1)
        self.assertEqual(len({r.deploy_id for r in results}), 1)
        self.assertEqual(len({canonical(s) for s in self.api.sent}), 1)

    def test_matching_actual_effect_required(self):
        owner, deploy = self.finalized()
        self.assertEqual(owner.observe(deploy).effect_finality, "finalized")
        self.assertEqual(len(self.signs), 1)
        self.rejected("UNAUTHORIZED", lambda: owner.observe("cd" * 70))

    def test_malformed_finality_inclusion_and_effect_never_pass(self):
        owner, deploy = self.finalized()
        original = deepcopy(self.api.responses)
        final = "/api/deploy-finalization-status/" + deploy
        inclusion = "/api/deploy/" + deploy
        effect = "/api/data-at-name-by-block-hash"
        changes = [(final, None), (final, {"state": "Finalized", "latest_block_hash": None, "rejection_count": 0}),
            (final, {**original[final], "rejection_count": True}),
            *[(inclusion, {**original[inclusion], k: v}) for k, v in
              (("deployId", "cd" * 70), ("blockHash", "f" * 64), ("errored", True), ("cost", -1), ("isFinalized", False))],
            (effect, {**original[effect], "expr": []}),
            (effect, {**original[effect], "expr": expected_expr("another", "d" * 64)}),
            (effect, {**original[effect], "expr": expected_expr(self.binding["operation"], "e" * 64)}),
            (effect, {**original[effect], "block": {**original[effect]["block"], "blockHash": "f" * 64}})]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                self.api.responses = {**deepcopy(original), path: value}
                observed = owner.observe(deploy)
                self.assertEqual(observed.effect_finality, "not-observed")
                self.assertEqual(observed.evidence["validation"], "unavailable-or-incompatible")
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM m4_observations").fetchone()[0], len(changes))

    def test_typed_rejection_and_pending_are_separate(self):
        owner, deploy = self.finalized()
        path = "/api/deploy-finalization-status/" + deploy
        for state in ("Failed", "Expired", "Pending"):
            self.api.responses[path] = {"state": state, "rejection_count": 1, "latest_block_hash": None}
            result = owner.observe(deploy)
            self.assertEqual(result.effect_finality, "pending" if state == "Pending" else "rejected")
            self.assertEqual(result.evidence["deploy_effect_finality"]["state"], state)

    def test_old_journal_rejected_without_migration(self):
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE intents(key TEXT PRIMARY KEY, signed TEXT)")
            db.execute("INSERT INTO intents VALUES('old','immutable')")
        before = self.path.read_bytes()
        self.rejected("UNSUPPORTED_PROFILE", self.owner)
        self.assertEqual(self.path.read_bytes(), before)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(db.execute("SELECT * FROM intents").fetchall(), [("old", "immutable")])


if __name__ == "__main__":
    unittest.main()
