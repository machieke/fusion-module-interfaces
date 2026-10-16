"""Isolated single-validator commitment experiment using the inspected node.

Run with uv --with cryptography --with pycryptodome --with grpcio-tools.
Private keys remain only in the ignored, mode-0700 runtime directory.
"""
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from fusion.adapters.f1r3 import F1R3HTTP, F1R3Commitments
from fusion.contracts import ContractError, canonical, digest
from fusion.ports import ApprovedCommitment, Mutation


def address(public):
    from Crypto.Hash import keccak
    def keccak256(data):
        return keccak.new(digest_bits=256, data=data).digest()
    payload = bytes(4) + keccak256(keccak256(public[1:])[-20:])
    raw = payload + hashlib.blake2b(payload, digest_size=32).digest()[:4]
    n, encoded = int.from_bytes(raw, "big"), ""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    while n:
        n, remainder = divmod(n, 58)
        encoded = alphabet[remainder] + encoded
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + encoded


def signing_proto(repo, directory):
    from grpc_tools import protoc
    source = (repo / "models/src/main/protobuf/CasperMessage.proto").read_text()
    message = re.search(r"message DeployDataProto \{.*?\n\}", source, re.S).group()
    (directory / "signing.proto").write_text('syntax = "proto3";\n' + message)
    assert protoc.main(["protoc", "-I" + str(directory), "--python_out=" + str(directory),
                        str(directory / "signing.proto")]) == 0
    spec = importlib.util.spec_from_file_location("signing_pb2", directory / "signing_pb2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DeployDataProto


def run():
    from cryptography.hazmat.primitives.asymmetric import ec, utils
    from cryptography.hazmat.primitives import hashes, serialization
    repo = Path(os.environ.get("F1R3_REPO", "/home/purplezky/work/asi/f1r3node-rust"))
    binary = repo / "target/debug/node"
    demo = json.loads((ROOT / "artifacts/demo.json").read_text())
    result_ref = demo["runs"][-1]["result"]["ref"]
    commitment = result_ref["digest"]
    assert re.fullmatch("[0-9a-f]{64}", commitment)
    directory = Path(tempfile.mkdtemp(prefix="chain-", dir=ROOT / "artifacts"))
    directory.chmod(0o700)
    key = ec.generate_private_key(ec.SECP256K1())
    private = key.private_numbers().private_value.to_bytes(32, "big").hex()
    public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    (directory / "bonds.txt").write_text(public.hex() + " 1000\n")
    (directory / "wallets.txt").write_text(address(public) + ",9000000000000\n")
    config = (repo / "docker/conf/standalone-dev.conf").read_text()
    config += '\ncasper.validator-private-key = "' + private + '"\nmetrics.prometheus = false\n'
    (directory / "node.conf").write_text(config)
    (directory / "node.conf").chmod(0o600)
    sockets, ports = [], []
    for _ in range(6):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        sockets.append(s)
        ports.append(s.getsockname()[1])
    command = [str(binary), "--log-level", "warn", "run", "--standalone", "--config-file", str(directory / "node.conf"),
               "--data-dir", str(directory / "data"), "--host", "127.0.0.1", "--api-host", "127.0.0.1", "--no-upnp",
               "--allow-private-addresses", "--bonds-file", str(directory / "bonds.txt"), "--wallets-file", str(directory / "wallets.txt"),
               "--shard-name", "fusion-m1", "--network-id", "fusion-m1-isolated", "--heartbeat-enabled",
               "--heartbeat-check-interval", "2 seconds", "--heartbeat-max-lfb-age", "4 seconds"]
    for flag, port in zip(["--protocol-port", "--api-port-grpc-external", "--api-port-grpc-internal", "--api-port-http",
                          "--discovery-port", "--api-port-admin-http"], ports):
        command.extend([flag, str(port)])
    for s in sockets:
        s.close()
    evidence = {"provider": "real-local-single-validator-f1r3node", "source": str(repo),
                "commit": subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip(),
                "binary_sha256": digest(binary.read_bytes()), "runtime_directory": str(directory),
                "approved_scope": "generated non-sensitive M1 result only, authorized by task brief",
                "result_ref": result_ref, "commitment": commitment, "observations": [], "command": command}
    log = open(directory / "node.log", "wb")
    evidence["runtime_environment"] = {"RUST_MIN_STACK": "8388608"}
    process = subprocess.Popen(command, stdout=log, stderr=log, start_new_session=True,
                               env={**os.environ, "RUST_MIN_STACK": "8388608"})
    api = F1R3HTTP(f"http://127.0.0.1:{ports[3]}")
    try:
        start = time.monotonic()
        deadline = start + 90
        while True:
            if process.poll() is not None:
                raise RuntimeError("node exited during startup; inspect private runtime log")
            try:
                evidence["status"] = api.request("/api/status")
                api.request("/api/last-finalized-block")
                break
            except ContractError:
                if time.monotonic() > deadline:
                    raise RuntimeError("genesis readiness timeout")
                time.sleep(.5)
        evidence["startup_seconds"] = time.monotonic() - start
        Proto = signing_proto(repo, directory)
        def signer(approved_digest):
            term = '@"fusion:m1:commitment"!("' + approved_digest + '")'
            timestamp = time.time_ns() // 1_000_000
            data = {"term": term, "timestamp": timestamp, "phloPrice": 1, "phloLimit": 10000000,
                    "validAfterBlockNumber": 0, "shardId": "fusion-m1", "expiration_timestamp": None}
            proto = Proto(term=term, timestamp=timestamp, phloPrice=1, phloLimit=10000000,
                          validAfterBlockNumber=0, shardId="fusion-m1")
            hashed = hashlib.blake2b(proto.SerializeToString(), digest_size=32).digest()
            sig = key.sign(hashed, ec.ECDSA(utils.Prehashed(hashes.SHA256())))
            r, s = utils.decode_dss_signature(sig)
            order = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
            sig = utils.encode_dss_signature(r, min(s, order - s)).hex()
            return {"data": data, "deployer": public.hex(), "signature": sig, "sigAlgorithm": "secp256k1"}

        approved = ApprovedCommitment("shared-test", result_ref, commitment, "user-brief-generated-M1-result")
        owner = F1R3Commitments(api, signer, str(directory / "intents.db"), approved)
        observation = owner.submit(Mutation("shared-test", "result-commitment"), approved)
        assert owner.submit(Mutation("shared-test", "result-commitment"), approved) == observation
        signature = observation.deploy_id
        evidence["observations"].append(asdict(observation))
        inclusion_started = time.monotonic()
        admin = F1R3HTTP(f"http://127.0.0.1:{ports[5]}")
        # Admin propose returns plain text, so use the inspected HTTP route directly.
        import urllib.request
        try:
            with urllib.request.urlopen(urllib.request.Request(admin.endpoint + "/api/propose", data=b""), timeout=30) as r:
                evidence["propose_response"] = r.read().decode()
        except Exception as exc:
            evidence["propose_error_type"] = type(exc).__name__
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            observation = owner.observe(signature)
            evidence["observations"].append(asdict(observation))
            if observation.effect_finality in {"finalized", "rejected"}:
                break
            time.sleep(1)
        evidence["observation_seconds"] = time.monotonic() - inclusion_started
        evidence["inclusion"] = api.request("/api/deploy/" + signature)
        evidence["gate"] = "passed" if (observation.effect_finality == "finalized"
            and evidence["inclusion"].get("errored") is False
            and evidence["inclusion"].get("blockHash") == observation.inclusion_block
            and evidence["inclusion"].get("deployId") == signature) else "blocked"
    except Exception as exc:
        evidence["gate"] = "blocked"
        evidence["reason"] = str(exc).replace(private, "<redacted>")
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        log.close()
        evidence["node_exit"] = process.returncode
        (ROOT / "artifacts/chain-demo.json").write_bytes(canonical(evidence))
    print(json.dumps({"chain_gate": evidence["gate"], "reason": evidence.get("reason"),
                      "evidence": "artifacts/chain-demo.json"}))
    return 0 if evidence["gate"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(run())
