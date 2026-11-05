"""Live local test authorization; principal comes from trusted transport."""
import hmac
import json
from pathlib import Path
from .contracts import ContractError, require


class Policy:
    """Live server-side registered requirements, explicitly a local test policy."""
    def __init__(self, path: str):
        self.path = Path(path)

    def current(self):
        return json.loads(self.path.read_text())

    def authenticate(self, credential: str) -> str:
        require(isinstance(credential, str) and credential.isascii() and 1 <= len(credential) <= 256, "UNAUTHORIZED")
        for principal, record in self.current()["principals"].items():
            if hmac.compare_digest(credential, record["credential"]):
                return principal
        raise ContractError("UNAUTHORIZED")

    def check(self, principal: str, scope: str, method: str):
        methods = self.current()["principals"].get(principal, {}).get("scopes", {}).get(scope, [])
        require(method in methods, "UNAUTHORIZED")

    def route(self, scope: str, route: str, owner: str | None = None):
        registered = self.current()["routes"].get(route)
        require(registered is not None and registered["scope"] == scope, "UNAUTHORIZED")
        if owner is not None:
            require(registered["owner"] == owner, "UNAUTHORIZED")
        self.check(registered["owner"], scope, "agent.messaging.poll")
