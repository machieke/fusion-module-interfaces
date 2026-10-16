"""Disposable real node helper. Refuses the host network namespace."""
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from fusion.adapters.f1r3 import F1R3HTTP
from fusion.adapters.f1r3_m4 import chain_identity
from fusion.contracts import ContractError, canonical
from scripts.chain_demo import address, signing_proto


def isolation():
    current, host = os.readlink("/proc/self/ns/net"), os.environ["M4_HOST_NETNS"]
    assert current != host, "Refusing to start a node in the host network namespace"
    subprocess.run(["ip", "link", "set", "lo", "up"], check=True)
    interfaces = json.loads(subprocess.check_output(["ip", "-j", "address"], text=True))
    routes = json.loads(subprocess.check_output(["ip", "-j", "route"], text=True))
    routes6 = json.loads(subprocess.check_output(["ip", "-j", "-6", "route"], text=True))
    assert [i["ifname"] for i in interfaces] == ["lo"] and not routes
    assert all(r.get("dev") == "lo" for r in routes6)
    with socket.socket() as probe:
        probe.settimeout(1)
        error = probe.connect_ex(("192.0.2.1", 443))
    assert error == 101, error
    return {"host_netns": host, "run_netns": current, "interfaces": ["lo"], "routes": routes,
            "ipv6_routes": routes6, "external_connect_errno": error}


class Node:
    def __init__(self, directory, repo, binary):
        self.directory, self.repo, self.binary = Path(directory), Path(repo), Path(binary)
        self.isolation = isolation()
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        key = ec.generate_private_key(ec.SECP256K1())
        secret = key.private_numbers().private_value.to_bytes(32, "big").hex()
        self.public = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint).hex()
        self.secret_file = self.directory / "test-signing-secret"
        self.secret_file.write_text(secret)
        self.secret_file.chmod(0o600)
        (self.directory / "bonds.txt").write_text(self.public + " 1000\n")
        (self.directory / "wallets.txt").write_text(address(bytes.fromhex(self.public)) + ",9000000000000\n")
        config = (self.repo / "docker/conf/standalone-dev.conf").read_text()
        config += '\ncasper.validator-private-key = "' + secret + '"\nmetrics.prometheus = false\n'
        (self.directory / "node.conf").write_text(config)
        (self.directory / "node.conf").chmod(0o600)
        signing_proto(self.repo, self.directory)
        holders, self.ports = [], []
        for _ in range(6):
            sock = socket.socket(); sock.bind(("127.0.0.1", 0))
            holders.append(sock); self.ports.append(sock.getsockname()[1])
        self.command = [str(self.binary), "--log-level", "warn", "run", "--standalone", "--config-file", str(self.directory / "node.conf"),
            "--data-dir", str(self.directory / "data"), "--host", "127.0.0.1", "--api-host", "127.0.0.1", "--no-upnp",
            "--allow-private-addresses", "--bonds-file", str(self.directory / "bonds.txt"), "--wallets-file", str(self.directory / "wallets.txt"),
            "--shard-name", "fusion-m4", "--network-id", "fusion-m4-isolated", "--heartbeat-enabled",
            "--heartbeat-check-interval", "2 seconds", "--heartbeat-max-lfb-age", "4 seconds"]
        for flag, port in zip(("--protocol-port", "--api-port-grpc-external", "--api-port-grpc-internal", "--api-port-http",
                              "--discovery-port", "--api-port-admin-http"), self.ports):
            self.command.extend([flag, str(port)])
        for sock in holders: sock.close()
        self.api = F1R3HTTP("http://127.0.0.1:" + str(self.ports[3]))
        self.process, self.log, self.identity = None, None, None

    def start(self):
        began = time.monotonic()
        self.log = open(self.directory / "node.log", "ab")
        self.process = subprocess.Popen(self.command, stdout=self.log, stderr=self.log, start_new_session=True,
            env={**os.environ, "RUST_MIN_STACK": "8388608"})
        deadline = began + 90
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("real node exited during startup: " + str(self.process.returncode))
            try:
                identity = chain_identity(self.api)
                assert identity["network"] == "fusion-m4-isolated" and identity["shard"] == "fusion-m4"
                assert self.identity is None or self.identity == identity, "Restart changed genesis"
                self.identity = identity
                self.isolation["bound_sockets"] = subprocess.check_output(["ss", "-lntup"], text=True)
                # The host verifier connects while these ports are known to be live.
                if os.environ.get("M4_SOCKET_CHALLENGE"):
                    path = Path(os.environ["M4_SOCKET_CHALLENGE"])
                    path.write_bytes(canonical({"ports": self.ports, "namespace": self.isolation["run_netns"]}))
                return round(time.monotonic() - began, 3)
            except ContractError:
                time.sleep(.5)
        raise TimeoutError("OBSERVATION_TIMEOUT: real genesis readiness after 90 seconds")

    def propose(self):
        try:
            with urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:" + str(self.ports[5]) + "/api/propose", data=b""), timeout=30) as response:
                return response.read().decode()
        except (OSError, TimeoutError) as error:
            return {"error": type(error).__name__}  # Observation still has its own deadline.

    def stop(self, kill=False):
        if self.process and self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGKILL if kill else signal.SIGTERM)
            try: self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL); self.process.wait(timeout=10)
        if self.log: self.log.close()
