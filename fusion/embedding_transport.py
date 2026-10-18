"""Local / certificate-verified loopback HTTPS bindings. No hidden retries or fallback."""
import http.client
import time

from . import embedding_contracts as c
from .contracts import ContractError, canonical, digest, require
from .neoclaw_transport import Network, json_loads
from .responses import error


def checked(request, reply):
    if type(reply) is dict and set(reply) == {'error'}:
        error(reply['error']); raise ContractError(reply['error']['code'])
    require(type(reply) is dict and set(reply) == {'request_sha256', 'principal', 'value'}, 'NOT_AVAILABLE')
    require(reply['request_sha256'] == digest(canonical(request)), 'NOT_AVAILABLE')
    require(reply['principal'] == request['intent']['principal'], 'UNAUTHORIZED')
    if request['operation'] == 'encode': return c.result(reply['value'], request['intent'])
    require(reply['value'] == {'authorized': True}, 'NOT_AVAILABLE')
    return reply['value']


class EmbeddingNetwork(Network):
    def invoke(self, request):
        c.request(request, self.chosen)
        timeout = 2. if request['operation'] != 'encode' else min(6., (request['intent']['deadline_ms']-time.time()*1000)/1000)
        require(timeout > 0, 'DEADLINE_EXCEEDED')
        conn = http.client.HTTPSConnection(self.endpoint['host'], self.endpoint['port'], timeout=timeout, context=self.context)
        started = time.monotonic(); sent = canonical(request)
        try:
            conn.request('POST', '/s03-encode', body=sent,
                headers={'Authorization': 'Bearer '+self.credential, 'Content-Type': 'application/json'})
            response = conn.getresponse(); require(response.status == 200, 'NOT_AVAILABLE')
            raw = response.read(c.MAX_WIRE_BYTES+1); require(len(raw) <= c.MAX_WIRE_BYTES, 'NOT_AVAILABLE')
            self.last_measurement = dict(request_body_bytes=len(sent), response_body_bytes=len(raw), elapsed_ms=(time.monotonic()-started)*1000)
            reply = json_loads(raw)
        except (OSError, http.client.HTTPException, ValueError): raise ContractError('NOT_AVAILABLE') from None
        finally: conn.close()
        return checked(request, reply)


class EmbeddingLocal:
    def __init__(self, service, credential): self.service, self.credential = service, credential
    def invoke(self, request):
        return checked(request, self.service.invoke(self.credential, json_loads(canonical(request))))
