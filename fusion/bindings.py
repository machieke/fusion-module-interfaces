"""Selected provider identities and checked responses under both transports."""
import json
import subprocess
import sys

from .contracts import ContractError, canonical, require, validate
from .registry import descriptor_read, select, selected_for, selection_token
from .responses import validate_reply


class InProcess:
    def __init__(self, factory, credential, selected=None):
        self.factory, self.credential = factory, credential
        self.bytes_sent = self.bytes_received = self.calls = 0
        self.correlations = {}
        owner = factory()
        try:
            self.selected = select(owner.catalogue) if selected is None else selected
        finally:
            owner.close()

    def invoke(self, request):
        name, _ = validate(request, check_deadline=False)
        descriptor = self.selected[name]
        owner = self.factory()
        try:
            self.calls += 1
            self.bytes_sent += len(canonical({"credential": self.credential, "request": request,
                                              "selection": selection_token(descriptor)}))
            try:
                actual = selected_for(owner.catalogue, request)
                require(selection_token(actual) == selection_token(descriptor), "UNSUPPORTED_PROFILE")
                result = owner.invoke(self.credential, json.loads(canonical(request)))
                reply = {"provider": selection_token(actual), "ok": result}
            except ContractError as error:
                reply = {"error": error.wire()}
            reply = json.loads(canonical(reply))
            self.bytes_received += len(canonical(reply)) + 1
            return validate_reply(request, reply, descriptor, self.correlations)
        finally:
            owner.close()


class Subprocess:
    def __init__(self, config, credential, selected=None):
        self.config, self.credential = str(config), credential
        self.bytes_sent = self.bytes_received = self.calls = 0
        self.correlations = {}
        if selected is None:
            reply = self._run("describe", b"")
            try:
                self.selected = select([descriptor_read(p) for p in reply["ok"]])
            except (KeyError, TypeError, ValueError):
                raise ContractError("NOT_AVAILABLE") from None
        else:
            self.selected = selected

    def _run(self, mode, data):
        try:
            result = subprocess.run([sys.executable, "-m", "fusion.host", mode, self.config],
                                    input=data, capture_output=True, timeout=25, check=True)
            reply = json.loads(result.stdout)
            if mode == "rpc":
                self.bytes_received += len(result.stdout)
            return reply
        except (OSError, subprocess.SubprocessError, ValueError):
            raise ContractError("NOT_AVAILABLE") from None

    def invoke(self, request):
        name, _ = validate(request, check_deadline=False)
        descriptor = self.selected[name]
        data = canonical({"credential": self.credential, "request": request,
                          "selection": selection_token(descriptor)})
        self.bytes_sent += len(data)
        self.calls += 1
        return validate_reply(request, self._run("rpc", data), descriptor, self.correlations)


def configured_binding(config, credential, selected):
    """Trusted composition only; historical local transports stay unchanged."""
    from pathlib import Path
    settings=json.loads(Path(config).read_text())
    if settings.get('service_composition')=='generated-inspect-services/1':
        from .inspect_services import Network
        return Network(settings,selected)
    return Subprocess(config,credential,selected=selected)
