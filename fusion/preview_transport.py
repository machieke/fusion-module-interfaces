"""Bounded authenticated JSON transport. No retries or discovery/failover."""
import http.client
from pathlib import Path
import time
from .contracts import ContractError, canonical, require
from .neoclaw_transport import Network, json_loads


def invoke(cfg, path, request, deadline=None):
    network = Network(cfg['endpoint'], cfg['credential'], {}, service_dns=cfg['endpoint']['host']!='127.0.0.1')
    seconds = 5 if deadline is None else min(30, (deadline-time.time_ns()//1_000_000)/1000)
    require(seconds > 0, 'DEADLINE_EXCEEDED')
    conn = http.client.HTTPSConnection(network.endpoint['host'], network.endpoint['port'],
                                      timeout=seconds, context=network.context)
    until = time.monotonic()+seconds
    try:
        conn.request('POST', path, body=canonical(request), headers={
            'Content-Type': 'application/json', 'Authorization': 'Bearer '+cfg['credential']})
        response = conn.getresponse(); require(response.status == 200, 'NOT_AVAILABLE')
        chunks, size = [], 0
        while True:
            remaining = until-time.monotonic(); require(remaining > 0, 'DEADLINE_EXCEEDED')
            if response.fp is not None: response.fp.raw._sock.settimeout(remaining)
            block = response.read1(min(8192, 131073-size))
            if not block: break
            chunks.append(block); size += len(block); require(size <= 131072, 'NOT_AVAILABLE')
        reply = json_loads(b''.join(chunks))
        if type(reply) is dict and set(reply) == {'error'}:
            code = reply['error'].get('code') if type(reply['error']) is dict else None
            require(code in ('UNAUTHORIZED','NOT_AVAILABLE','NOT_FOUND','CONFLICT','OVERLOADED',
                'DEADLINE_EXCEEDED','INVALID_ARGUMENT','UNSUPPORTED_PROFILE','UNSUPPORTED_OPERATION'), 'NOT_AVAILABLE')
            raise ContractError(code)
        return reply
    except (OSError, http.client.HTTPException, ValueError): raise ContractError('NOT_AVAILABLE') from None
    finally: conn.close()
