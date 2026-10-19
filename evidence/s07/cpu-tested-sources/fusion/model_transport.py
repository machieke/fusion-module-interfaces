"""Selected X01 local/HTTPS placement; same caller and receipt validation."""
import http.client
import json
from pathlib import Path
import time
from . import model_contracts as c
from .contracts import ContractError, canonical, digest, require
from .neoclaw_transport import Network, json_loads
from .registry import descriptor_read, selection_token
from .neoclaw_model_disclosure import disclose


def configuration(path):
    cfg = json.loads(Path(path).read_text())
    c.deadline_limit(cfg['profile'])
    require(cfg['sharing'] == c.PRIVACY and cfg['fallback'] is False, 'UNSUPPORTED_PROFILE')
    chosen = c.select([descriptor_read(d) for d in cfg['catalogue']], cfg['profile'])
    require(type(cfg['commands']) is list and 1 <= len(cfg['commands']) <= 3)
    from .neoclaw_contracts import parse_expression
    for command in cfg['commands']:
        require(type(command) is list and len(command) == 2 and command[0] in ('metta','send'), 'UNSUPPORTED_OPERATION')
        if command[0] == 'metta': parse_expression(command[1])
        else: require(type(command[1]) is str and 1 <= len(command[1].encode()) <= 400)
    frozen = {k:cfg[k] for k in ('profile','sharing','principal','scope','session','placement','disclosure','commands')}
    frozen['selection'] = selection_token(chosen)
    require(cfg['placement'] in ('local','network'), 'UNSUPPORTED_PROFILE')
    if cfg['placement'] == 'local': frozen['provider_config'] = cfg['provider_config']
    else:
        require('provider_config' not in cfg, 'UNSUPPORTED_PROFILE')
        frozen['endpoint'] = {**cfg['endpoint'], 'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
    return cfg, chosen, frozen


def checked(request, reply):
    require(type(reply) is dict, 'NOT_AVAILABLE')
    if 'error' in reply:
        require(set(reply) == {'error'}, 'NOT_AVAILABLE')
        code = reply['error'].get('code') if type(reply['error']) is dict else None
        require(code in ('UNAUTHORIZED','NOT_AVAILABLE','CONFLICT','OVERLOADED','DEADLINE_EXCEEDED',
                         'INVALID_ARGUMENT','UNSUPPORTED_PROFILE','UNSUPPORTED_VERSION','UNSUPPORTED_OPERATION'), 'NOT_AVAILABLE')
        raise ContractError(code)
    require(set(reply) == {'request_sha256','principal','value'}, 'NOT_AVAILABLE')
    require(reply['request_sha256'] == digest(canonical(request)), 'NOT_AVAILABLE')
    require(reply['principal'] == request['intent']['principal'], 'UNAUTHORIZED')
    if request['operation'] == 'authorize': require(reply['value'] == {'authorized':True}, 'UNAUTHORIZED')
    else: c.observation(reply['value'], request['intent'])
    return reply['value']


class Client:
    def __init__(self, path):
        self.path = path; self.cfg, self.chosen, self.frozen = configuration(path)

    def invoke(self, operation, accepted):
        cfg, _, frozen = configuration(self.path); require(frozen == self.frozen, 'CONFLICT')
        request = dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION), operation=operation, intent=accepted)
        c.request(request)
        require(accepted['selection'] == selection_token(self.chosen), 'UNSUPPORTED_PROFILE')
        require((accepted['principal'],accepted['scope'],accepted['session']) ==
                (cfg['principal'],cfg['scope'],cfg['session']), 'UNAUTHORIZED')
        disclose(accepted['native_prompt'], cfg['disclosure'])
        if cfg['placement'] == 'local':
            from .model_service import ModelService
            from .adapters.ollama_completion import OllamaCompletion
            policy = json.loads(Path(cfg['provider_config']).read_text())
            service = ModelService(cfg['provider_config'], OllamaCompletion(policy['model_completion']['runtime_lock']))
            try: reply = service.invoke(cfg['credential'], request)
            finally: service.close()
        else:
            network = Network(cfg['endpoint'], cfg['credential'], {})
            timeout = 2 if operation != 'complete' else max(.05, min(c.deadline_limit(accepted['profile'])/1000, (accepted['deadline_ms']-time.time_ns()//1_000_000)/1000))
            connection = http.client.HTTPSConnection(network.endpoint['host'], network.endpoint['port'], timeout=timeout, context=network.context)
            try:
                connection.request('POST','/s07-model',body=canonical(request),headers={
                    'Content-Type':'application/json','Authorization':'Bearer '+cfg['credential']})
                response = connection.getresponse(); require(response.status == 200, 'NOT_AVAILABLE')
                raw = response.read(c.MAX_WIRE+1); require(len(raw) <= c.MAX_WIRE, 'NOT_AVAILABLE')
                reply = json_loads(raw)
            except (OSError,http.client.HTTPException,ValueError): raise ContractError('NOT_AVAILABLE') from None
            finally: connection.close()
        return checked(request, reply)
