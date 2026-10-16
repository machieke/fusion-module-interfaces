"""Inspected F1R3node HTTP seam; node observations remain explicit evidence."""
import json
import re
import sqlite3
import urllib.error
import urllib.request

from dataclasses import asdict
from ..contracts import ContractError, canonical, digest, label, require
from ..ports import ChainObservation, ApprovedCommitment, Mutation


class F1R3HTTP:
    def __init__(self, endpoint):
        self.endpoint = endpoint.rstrip("/")

    def request(self, path, body=None):
        request = urllib.request.Request(self.endpoint + path,
                    data=canonical(body) if body is not None else None,
                    headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read(4 * 1024 * 1024 + 1)
                require(len(raw) <= 4 * 1024 * 1024, "NOT_AVAILABLE")
                return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise ContractError("NOT_AVAILABLE") from None

    def submit_signed(self, request):
        # Signing and eligible-commitment policy are trusted composition responsibilities.
        signature = request.get("signature")
        require(isinstance(signature, str) and bool(re.fullmatch("[0-9a-f]{128,144}", signature)))
        receipt = self.request("/api/deploy", request)
        require(isinstance(receipt, str) and signature in receipt, "NOT_AVAILABLE")
        return ChainObservation(signature, None, "pending", {"submission_response": receipt})

    def observe(self, deploy_id):
        require(isinstance(deploy_id, str) and bool(re.fullmatch("[0-9a-f]{128,144}", deploy_id)))
        result = self.request("/api/deploy-finalization-status/" + deploy_id)
        require(isinstance(result, dict), "NOT_AVAILABLE")
        state, block = result.get("state"), result.get("latest_block_hash")
        require(state in {"Pending", "Finalized", "Failed", "Expired"}, "NOT_AVAILABLE")
        require(type(result.get("rejection_count")) is int and result["rejection_count"] >= 0, "NOT_AVAILABLE")
        require(block is None or (isinstance(block, str) and bool(re.fullmatch("[0-9a-f]{64}", block))), "NOT_AVAILABLE")
        require(state != "Finalized" or block is not None, "NOT_AVAILABLE")
        observed = ("finalized" if state == "Finalized" else "rejected" if state in {"Failed", "Expired"}
                    else "included" if block else "pending")
        return ChainObservation(deploy_id, block, observed, result)


class F1R3Commitments:
    """A bounded commitment owner, pinned to one operator-approved fixture.

    The signer is injected by composition. The approval is registered here;
    caller-supplied approval-record strings alone confer no authority.
    """
    def __init__(self, api, signer, journal, approved: ApprovedCommitment):
        self.api, self.signer, self.journal = api, signer, journal
        self.approved = canonical(asdict(approved))
        with sqlite3.connect(journal) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS intents (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, signed TEXT NOT NULL, receipt TEXT)")

    def submit(self, command: Mutation, commitment: ApprovedCommitment) -> ChainObservation:
        require(canonical(asdict(commitment)) == self.approved and command.scope_ref == commitment.scope_ref, "UNAUTHORIZED")
        require(label(command.idempotency_key) and label(command.scope_ref))
        require(commitment.commitment_digest == commitment.result_ref["digest"] and
                commitment.scope_ref == commitment.result_ref["scope_ref"], "INVALID_ARGUMENT")
        require(bool(re.fullmatch("[0-9a-f]{64}", commitment.commitment_digest)))
        key = canonical([command.scope_ref, command.idempotency_key]).decode()
        fingerprint = digest(canonical(asdict(commitment)))
        with sqlite3.connect(self.journal) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT fingerprint,signed,receipt FROM intents WHERE key=?", (key,)).fetchone()
            if row:
                require(row[0] == fingerprint, "CONFLICT")
                signed = json.loads(row[1])
                if row[2]:
                    return ChainObservation(**json.loads(row[2]))
            else:
                signed = self.signer(commitment.commitment_digest)
                db.execute("INSERT INTO intents VALUES(?,?,?,NULL)", (key, fingerprint, canonical(signed).decode()))
        # Any uncertain retry uses the same durably recorded signature/transaction.
        observation = self.api.submit_signed(signed)
        with sqlite3.connect(self.journal) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("UPDATE intents SET receipt=? WHERE key=?", (canonical(asdict(observation)).decode(), key))
        return observation

    def observe(self, deploy_id: str) -> ChainObservation:
        return self.api.observe(deploy_id)
