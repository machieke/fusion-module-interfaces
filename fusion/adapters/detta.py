import json
import fcntl
from pathlib import Path
import subprocess

from ..contracts import ContractError, digest


class DettaStorage:
    def __init__(self, binary: str, root: str):
        self.binary, self.root = binary, root

    def _call(self, operation: str, **body):
        try:
            Path(self.root).mkdir(parents=True, exist_ok=True)
            with open(Path(self.root) / ".port.lock", "a+b") as lock:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise ContractError("OVERLOADED") from None
                run = subprocess.run([self.binary], input=json.dumps({"root": self.root,
                                     "operation": operation, **body}), capture_output=True,
                                     text=True, timeout=15, check=True, pass_fds=(lock.fileno(),))
            reply = json.loads(run.stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            raise ContractError("NOT_AVAILABLE") from None
        if "error" in reply:
            raise ContractError(reply["error"])
        return reply["ok"]

    def put(self, scope_ref: str, coordinate: str, data: bytes):
        evidence = self._call("put", scope_hash=digest(scope_ref.encode()), key=digest(coordinate.encode()), bytes=list(data))
        return evidence["manifest"], {"provider": "detta-local-rs/1",
               "durability": "local-files-process-restart", "evidence": evidence}

    def get(self, scope_ref: str, payload_id: str) -> bytes:
        result = self._call("get", scope_hash=digest(scope_ref.encode()), manifest=payload_id)
        data = bytes(result["bytes"])
        if digest(data) != result["content_hash"]:
            raise ContractError("NOT_AVAILABLE")
        return data

    def availability(self, scope_ref: str, payload_id: str):
        return self._call("availability", scope_hash=digest(scope_ref.encode()), manifest=payload_id)
