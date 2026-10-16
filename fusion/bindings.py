import json
import subprocess
import sys

from .contracts import ContractError, canonical


class InProcess:
    def __init__(self, factory, credential):
        self.factory, self.credential = factory, credential
        self.bytes_sent = self.bytes_received = self.calls = 0

    def invoke(self, request):
        owner = self.factory()
        try:
            self.calls += 1
            self.bytes_sent += len(canonical({"credential": self.credential, "request": request}))
            # Encode/decode at both boundaries to enforce the same wire value model.
            result = owner.invoke(self.credential, json.loads(canonical(request)))
            self.bytes_received += len(canonical({"ok": result})) + 1
            return json.loads(canonical(result))
        finally:
            owner.close()


class Subprocess:
    def __init__(self, config, credential):
        self.config, self.credential = str(config), credential
        self.bytes_sent = self.bytes_received = self.calls = 0

    def invoke(self, request):
        data = canonical({"credential": self.credential, "request": request})
        self.bytes_sent += len(data)
        self.calls += 1
        try:
            result = subprocess.run([sys.executable, "-m", "fusion.host", "rpc", self.config],
                                    input=data, capture_output=True, timeout=25, check=True)
            self.bytes_received += len(result.stdout)
            reply = json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            raise ContractError("NOT_AVAILABLE") from None
        if "error" in reply:
            raise ContractError(reply["error"]["code"])
        return reply["ok"]
