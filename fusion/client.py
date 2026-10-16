"""The same small consumer runs unchanged under either binding."""
import uuid

from .contracts import Binding, PROFILES, decode, encode


class Peer:
    def __init__(self, binding: Binding, scope: str, reply_route: str):
        self.binding, self.scope, self.reply_route = binding, scope, reply_route

    def request(self, interface, operation, body, key=None, correlation=None, **metadata):
        request = {"message_id": str(uuid.uuid4()), "interface_ref": {"id": interface, "version": "1.0.0"},
                   "profile": PROFILES[interface], "operation": operation, "scope_ref": self.scope, "body": body}
        if key is not None:
            request["idempotency_key"] = key
        if correlation is not None:
            request.update(correlation_id=correlation, reply_route=self.reply_route)
        request.update(metadata)
        return request

    def call(self, *args, **kwargs):
        return self.binding.invoke(self.request(*args, **kwargs))

    def store(self, data, key):
        return self.call("atom.storage", "create", {"bytes": encode(data), "content_type": "application/octet-stream",
                                                   "sharing": "non-sensitive-fixture"}, key)

    def retrieve(self, ref):
        return decode(self.call("atom.storage", "get", {"ref": ref})["bytes"])

    def share(self, ref, route, key):
        return self.call("agent.messaging", "send", {"route": route, "ref": ref}, key, key)

    def poll(self):
        return self.call("agent.messaging", "poll", {"route": self.reply_route})["delivery"]

    def ack(self, delivery_id, key):
        return self.call("agent.messaging", "ack", {"route": self.reply_route, "delivery_id": delivery_id}, key)

    def delegate(self, ref, key, **metadata):
        return self.call("execution", "submit", {"ref": ref, "operation": "inspect_atom"}, key, key, **metadata)

    def status(self, job_id):
        return self.call("execution", "status", {"job_id": job_id})

    def result(self, job_id):
        return self.call("execution", "result", {"job_id": job_id})
