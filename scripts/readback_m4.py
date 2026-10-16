"""Separate read-only verification: permitted DA credential + node RPC, no signer."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fusion.adapters.f1r3 import F1R3HTTP
from fusion.adapters.f1r3_m4 import observe_effect
from fusion.bindings import Subprocess
from fusion.client import Peer
from fusion.contracts import canonical, digest


def verify(access, trace):
    config, evidence = json.loads(access.read_text()), json.loads(trace.read_text())
    peer = Peer(Subprocess(config["service_config"], config["read_credential"]), "shared-test", "unused-read-only-route")
    raw = peer.retrieve(evidence["approved"]["result_ref"])
    assert digest(raw) == evidence["approved"]["commitment_digest"]
    observed = observe_effect(F1R3HTTP(config["endpoint"]), evidence["signed"], evidence["read_name"],
        evidence["operation"], digest(raw), evidence["chain_instance"])
    assert observed.effect_finality == "finalized", observed
    return {"status": "PASS", "result_bytes": len(raw), "result_digest": digest(raw), "deploy_id": observed.deploy_id,
        "inclusion_block": observed.inclusion_block, "effect": observed.evidence["value"],
        "post_state": observed.evidence["effect"]["block"]["postStateHash"], "effect_finality": observed.effect_finality,
        "authority": "atom.storage.get only; node read RPC; no signing key or caller journal opened"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("access", type=Path); parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    print(canonical(verify(args.access, args.trace)).decode())
