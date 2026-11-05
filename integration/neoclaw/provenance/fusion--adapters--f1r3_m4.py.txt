"""Fresh-journal F1R3 profile: exact approved generated effect, single operation.

The old M1 adapter/profile is unchanged. This owner implements ConsensusFinality;
Hive owns no signing, submission SQL or chain state. Observations are node evidence.
"""
from dataclasses import asdict
from contextlib import closing, contextmanager
import json
from pathlib import Path
import re
import sqlite3
import time

from .f1r3 import F1R3HTTP
from ..contracts import ContractError, canonical, digest, label, require
from ..ports import ApprovedCommitment, ChainObservation, Mutation
from ..registry import Descriptor, Requirement, resolve, selection_token

PROFILE = "f1r3-generated-post-state/2"
NAMESPACE = "fusion:m4:commitment/1"
SOURCE = "9ec1096e10774926ea8e72f0823482f0bf9213e1"
GUARANTEES = frozenset({"process-restart", "scoped", "idempotent", "exact-post-state"})
DESCRIPTOR = Descriptor("f1r3-local", "consensus.finality", "1.0.0", "0.4.0",
    frozenset({PROFILE}), frozenset({"submit", "observe"}), GUARANTEES, 65536)


def select_chain(descriptor):
    chosen = resolve([descriptor], Requirement("consensus.finality", "1.0.0", "1.0.1", PROFILE,
        frozenset({"submit", "observe"}), GUARANTEES))
    require(selection_token(chosen) == selection_token(DESCRIPTOR), "UNSUPPORTED_PROFILE")
    return chosen


def hex64(value):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value) is not None


def chain_identity(api):
    status = api.request("/api/status")
    genesis = api.request("/api/blocks/0/0?view=summary")
    require(isinstance(status, dict) and status.get("isReady") is True and
            type(status.get("peers")) is int and status["peers"] == 0 and
            type(status.get("nodes")) is int and status["nodes"] == 0 and
            status.get("version") == {"api": "1", "node": "F1r3node Rust 0.4.15 (9ec1096)"}, "NOT_AVAILABLE")
    require(isinstance(genesis, list) and len(genesis) == 1 and isinstance(genesis[0], dict), "NOT_AVAILABLE")
    block = genesis[0].get("blockInfo", {})
    require(isinstance(block, dict) and type(block.get("blockNumber")) is int and block["blockNumber"] == 0 and hex64(block.get("blockHash")) and
            block.get("shardId") == status.get("shardId") and block.get("isFinalized") is True, "NOT_AVAILABLE")
    return {"network": status["networkId"], "shard": status["shardId"], "genesis": block["blockHash"],
            "source": SOURCE, "profile": PROFILE}


def expected_expr(operation, value):
    return [{"ExprTuple": {"data": [{"ExprString": {"data": x}} for x in (NAMESPACE, operation, value)]}}]


def observe_effect(api, signed, read_name, operation, value, chain):
    """One bounded observation, including non-consuming inclusion-post-state read.

    Retain incompatible responses as evidence; never promote them to finality.
    A transport failure remains unknown, not rejection or absence.
    """
    signature = signed["signature"]
    require(isinstance(signature, str) and re.fullmatch("[0-9a-f]{128,144}", signature) is not None and
            hex64(read_name) and hex64(value) and label(operation))
    evidence = {"source": "isolated-node-http", "observed_at_ms": time.time_ns() // 1000000,
                "profile": PROFILE, "validation": "not-observed"}
    block = None
    try:
        require(chain_identity(api) == chain, "CONFLICT")
        finality = api.request("/api/deploy-finalization-status/" + signature)
        evidence["deploy_effect_finality"] = finality
        require(isinstance(finality, dict) and finality.get("state") in {"Pending", "Finalized", "Failed", "Expired"}
                and type(finality.get("rejection_count")) is int and finality["rejection_count"] >= 0, "NOT_AVAILABLE")
        block = finality.get("latest_block_hash")
        require(block is None or hex64(block), "NOT_AVAILABLE")
        if finality["state"] in {"Failed", "Expired"}:
            evidence["validation"] = "typed-rejection"
            return ChainObservation(signature, block, "rejected", evidence)
        if block is None:
            require(finality["state"] == "Pending", "NOT_AVAILABLE")
            return ChainObservation(signature, None, "pending", evidence)
        inclusion = api.request("/api/deploy/" + signature)
        evidence["inclusion"] = inclusion
        require(isinstance(inclusion, dict) and inclusion.get("deployId") == signature and
                inclusion.get("blockHash") == block and inclusion.get("errored") is False and
                inclusion.get("deployer") == signed["deployer"] and
                all(inclusion.get(k) == signed["data"][k] for k in
                    ("term", "timestamp", "phloPrice", "phloLimit", "validAfterBlockNumber")) and
                inclusion.get("sigAlgorithm") == signed["sigAlgorithm"] and
                type(inclusion.get("cost")) is int and 0 <= inclusion["cost"] <= signed["data"]["phloLimit"] and
                type(inclusion.get("blockNumber")) is int and inclusion["blockNumber"] > 0 and
                inclusion.get("finalizationState") == finality["state"] and
                inclusion.get("rejectionCount") == finality["rejection_count"], "NOT_AVAILABLE")
        query = {"name": {"UnforgPrivate": {"data": read_name}}, "blockHash": block, "usePreStateHash": False}
        evidence["effect_query"] = query
        effect = api.request("/api/data-at-name-by-block-hash", query)
        evidence["effect"] = effect
        require(isinstance(effect, dict) and effect.get("expr") == expected_expr(operation, value), "NOT_AVAILABLE")
        effect_block = effect.get("block", {})
        require(isinstance(effect_block, dict) and effect_block.get("blockHash") == block and effect_block.get("shardId") == chain["shard"] and
                effect_block.get("blockNumber") == inclusion["blockNumber"] and
                hex64(effect_block.get("postStateHash")), "NOT_AVAILABLE")
        finalized = finality["state"] == "Finalized"
        require(not finalized or (inclusion.get("isFinalized") is True and effect_block.get("isFinalized") is True), "NOT_AVAILABLE")
        evidence.update(validation="verified", value={"namespace": NAMESPACE, "operation": operation, "digest": value})
        return ChainObservation(signature, block, "finalized" if finalized else "included", evidence)
    except ContractError as error:
        if error.code != "NOT_AVAILABLE":
            raise
        evidence.update(validation="unavailable-or-incompatible", error=error.wire())
        return ChainObservation(signature, block if hex64(block) else None, "not-observed", evidence)


class GeneratedCommitments:
    """Trusted exact approval + live authority, one fresh independent owner journal.

    `authorize` reloads operator and service authority on every call, including
    cached replies and immediately before sending. Keys never appear in this DB.
    Signing is local; nothing signed escapes before its FULL synchronous commit.
    """
    def __init__(self, api, signer, journal, approved: ApprovedCommitment, binding,
                 authorize, hook=lambda _: None):
        # Frozen dataclasses do not freeze their nested dictionaries. Capture the
        # registered values before a caller can mutate an alias retained at entry.
        approved = ApprovedCommitment(**json.loads(canonical(asdict(approved))))
        binding = json.loads(canonical(binding))
        self.api, self.signer, self.journal = api, signer, str(journal)
        self.approved, self.binding, self.authorize, self.hook = approved, binding, authorize, hook
        require(hex64(approved.commitment_digest) and approved.result_ref["digest"] == approved.commitment_digest and
                approved.result_ref["scope_ref"] == approved.scope_ref and label(binding["operation"]), "INVALID_ARGUMENT")
        require(binding["profile"] == PROFILE and binding["selection"] == selection_token(DESCRIPTOR), "UNSUPPORTED_PROFILE")
        require(binding["chain"]["profile"] == PROFILE and binding["chain"]["source"] == SOURCE, "UNSUPPORTED_PROFILE")
        require(binding["chain"]["network"] == "fusion-m4-isolated" and binding["chain"]["shard"] == "fusion-m4", "UNSUPPORTED_PROFILE")
        require(binding["limits"] == {"phloPrice": 1, "phloLimit": 10000000, "validAfterBlockNumber": 0}, "UNSUPPORTED_PROFILE")
        require(re.fullmatch("04[0-9a-f]{128}", binding["signer"]) is not None)
        self.identity = canonical({"schema": 1, "approval": asdict(approved), "binding": binding}).decode()
        self.authorize()
        if Path(self.journal).is_file():
            # Reject historical journals before even changing their journal mode.
            with closing(sqlite3.connect(Path(self.journal).resolve().as_uri() + "?mode=ro", uri=True)) as db:
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                require(not tables or tables == {"m4_binding", "m4_intent", "m4_observations"}, "UNSUPPORTED_PROFILE")
        with self.db() as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            require(not tables or tables == {"m4_binding", "m4_intent", "m4_observations"}, "UNSUPPORTED_PROFILE")
            db.execute("CREATE TABLE IF NOT EXISTS m4_binding(id INTEGER PRIMARY KEY CHECK(id=1), value TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS m4_intent(id INTEGER PRIMARY KEY CHECK(id=1), command TEXT NOT NULL, plan TEXT NOT NULL, signed TEXT, read_name TEXT, receipt TEXT, signing_seconds REAL)")
            db.execute("CREATE TABLE IF NOT EXISTS m4_observations(id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT value FROM m4_binding WHERE id=1").fetchone()
            require(old is None or old[0] == self.identity, "CONFLICT")
            db.execute("INSERT OR IGNORE INTO m4_binding VALUES(1,?)", (self.identity,))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.journal, timeout=30)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def submit(self, command: Mutation, commitment: ApprovedCommitment) -> ChainObservation:
        self.authorize()
        require(canonical(asdict(commitment)) == canonical(asdict(self.approved)) and
                command.scope_ref == commitment.scope_ref, "UNAUTHORIZED")
        require(command.idempotency_key == self.binding["operation"] and command.intent_digest is None, "CONFLICT")
        command_text = canonical(asdict(command)).decode()
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT command,plan,signed,read_name,receipt FROM m4_intent WHERE id=1").fetchone()
            if row:
                require(row[0] == command_text, "CONFLICT")
            else:
                term = 'new commitment in { commitment!(("' + NAMESPACE + '", "' + self.binding["operation"] + '", "' + commitment.commitment_digest + '")) }'
                plan = {"term": term, "timestamp": time.time_ns() // 1000000, **self.binding["limits"],
                        "shardId": self.binding["chain"]["shard"], "expiration_timestamp": None}
                db.execute("INSERT INTO m4_intent VALUES(1,?,?,NULL,NULL,NULL,NULL)", (command_text, canonical(plan).decode()))
        self.hook("after_logical_intent")
        # The logical identity and timestamp are durable before signing begins.
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT plan,signed,read_name,receipt,signing_seconds FROM m4_intent WHERE id=1").fetchone()
            plan = json.loads(row[0])
            if row[1] is None:
                self.authorize()
                require(chain_identity(self.api) == self.binding["chain"], "CONFLICT")
                prepared = self.api.request("/api/prepare-deploy", {"deployer": self.binding["signer"],
                    "timestamp": plan["timestamp"], "nameQty": 1})
                require(isinstance(prepared, dict) and isinstance(prepared.get("names"), list) and
                        len(prepared["names"]) == 1 and hex64(prepared["names"][0]), "NOT_AVAILABLE")
                began = time.monotonic()
                signed = self.signer(plan)
                signing_seconds = round(time.monotonic() - began, 6)
                require(signed["data"] == plan and signed["deployer"] == self.binding["signer"] and
                        signed["sigAlgorithm"] == "secp256k1" and
                        re.fullmatch("[0-9a-f]{128,144}", signed["signature"]) is not None, "NOT_AVAILABLE")
                db.execute("UPDATE m4_intent SET signed=?,read_name=?,signing_seconds=? WHERE id=1",
                           (canonical(signed).decode(), prepared["names"][0], signing_seconds))
            else:
                signed = json.loads(row[1])
                signing_seconds = row[4]
            receipt = json.loads(row[3]) if row[3] else None
        self.hook("after_signed_intent")
        self.authorize()
        require(chain_identity(self.api) == self.binding["chain"], "CONFLICT")
        if receipt is not None:
            return ChainObservation(**receipt)
        self.authorize()
        began = time.monotonic()
        received = self.api.submit_signed(signed)
        observation = ChainObservation(received.deploy_id, received.inclusion_block, received.effect_finality,
            {**received.evidence, "signing_seconds": signing_seconds, "submission_rpc_seconds": round(time.monotonic() - began, 6)})
        self.hook("after_node_submission")
        with self.db() as db:
            db.execute("UPDATE m4_intent SET receipt=? WHERE id=1", (canonical(asdict(observation)).decode(),))
        return observation

    def observe(self, deploy_id: str) -> ChainObservation:
        self.authorize()
        with self.db() as db:
            row = db.execute("SELECT signed,read_name FROM m4_intent WHERE id=1").fetchone()
            require(db.execute("SELECT count(*) FROM m4_observations").fetchone()[0] < 256, "OVERLOADED")
        require(row is not None and row[0] is not None, "NOT_FOUND")
        signed = json.loads(row[0])
        require(signed["signature"] == deploy_id, "UNAUTHORIZED")
        result = observe_effect(self.api, signed, row[1], self.binding["operation"],
                                self.approved.commitment_digest, self.binding["chain"])
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            require(db.execute("SELECT count(*) FROM m4_observations").fetchone()[0] < 256, "OVERLOADED")
            db.execute("INSERT INTO m4_observations(value) VALUES(?)", (canonical(asdict(result)).decode(),))
        self.hook("after_chain_observation")
        return result
