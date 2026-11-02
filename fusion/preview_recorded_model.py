"""Explicit authored proposals through the existing ModelInference owner.

No execution, tool results, generative backend or fallback lives here. Operators
select proposal text as fixtures; native parsing and owner calls evaluate it.
"""
import json
from pathlib import Path
from . import preview_model_contracts as c
from .contracts import canonical, digest, require
from .registry import descriptor_read, selection_token
from .model_service import ModelService
from .model_transport import checked


def disclosure(accepted, policy):
    required={'profile','scope','principals','max_prompt_bytes'}
    require(type(policy) is dict and required<=set(policy)<=required|{'session_principals'})
    require(policy['profile'] == 'synthetic-recorded-prompt/1' and policy['scope'].startswith('synthetic-'), 'UNAUTHORIZED')
    require(accepted['scope'] == policy['scope'] and accepted['principal'] in policy['principals'], 'UNAUTHORIZED')
    require(type(policy['principals']) is list and 1<=len(policy['principals'])<=2,'UNAUTHORIZED')
    if len(policy['principals'])>1 or 'session_principals' in policy:
        owners=policy.get('session_principals')
        require(type(owners) is dict and owners.get(accepted['session'])==accepted['principal'],'UNAUTHORIZED')
    require(type(policy['max_prompt_bytes']) is int and 1 <= policy['max_prompt_bytes'] <= c.MAX_PROMPT)
    c.text(accepted['native_prompt'], policy['max_prompt_bytes'])


class RecordedProposals:
    def __init__(self, policy):
        cfg = json.loads(Path(policy).read_text())['model_completion']
        self.proposals = cfg['recorded_proposals']
        require(type(self.proposals) is dict and len(self.proposals) <= c.MAX_CALLS)
        require(cfg['runtime_lock'] == {'profile': c.PROFILE, 'generative_runtime': 'FORBIDDEN',
            'proposals_sha256':digest(canonical(self.proposals))}, 'UNSUPPORTED_PROFILE')

    def complete(self, accepted):
        key = accepted.session+'/'+str(accepted.slot)
        require(key in self.proposals, 'NOT_AVAILABLE')
        value = self.proposals[key]
        if type(value) is dict:
            # An explicit authored proposal fixture, not a tool implementation.
            # It may repeat the new operator input as command text. Parsing,
            # whole-batch authority and every tool still execute in native Omega.
            require(value=={'proposal':'input-command'},'UNSUPPORTED_PROFILE')
            import ast
            parts=accepted.native_prompt.split(':-:-:-:')
            require(len(parts)==2)
            try:incoming=ast.literal_eval(parts[1].strip())
            except (ValueError,SyntaxError):require(False)
            require(type(incoming) is list and len(incoming)==2 and incoming[0]=='HUMAN-MSG:' and type(incoming[1]) is str)
            value=incoming[1]
        c.text(value, c.MAX_TEXT)
        return c.completion(dict(raw_text=value, native_text=c.clean(value), outcome='complete',
            finish_reason='stop', observed_model=c.MODEL,
            provider_request_id=None, usage=dict(input_tokens=None, output_tokens=None, reasoning_tokens=None),
            durations_ns=dict(total=None, load=None, prompt=None, generation=None)))


def service(path, hook=lambda _: None):
    return ModelService(path, RecordedProposals(path), hook, disclosure=disclosure, contracts=c)


def configuration(path):
    cfg = json.loads(Path(path).read_text())
    require(cfg['profile'] == c.PROFILE and cfg['fallback'] is False, 'UNSUPPORTED_PROFILE')
    require(cfg['placement'] in ('local','network'), 'UNSUPPORTED_PROFILE')
    chosen = c.select([descriptor_read(d) for d in cfg['catalogue']])
    frozen = {k:cfg[k] for k in ('profile','principal','scope','session','placement','disclosure')}
    frozen['selection'] = selection_token(chosen)
    if cfg['placement'] == 'local': frozen['provider_config'] = cfg['provider_config']
    else:
        require('provider_config' not in cfg, 'UNSUPPORTED_PROFILE')
        frozen['endpoint'] = {**cfg['endpoint'], 'ca_sha256':digest(Path(cfg['endpoint']['ca_file']).read_bytes())}
    return cfg, chosen, frozen


class Client:
    def __init__(self, path):
        self.path = path
        self.cfg, self.chosen, self.frozen = configuration(path)

    def invoke(self, operation, accepted):
        cfg, _, frozen = configuration(self.path); require(frozen == self.frozen, 'CONFLICT')
        require((accepted['principal'],accepted['scope'],accepted['session']) ==
                (cfg['principal'],cfg['scope'],cfg['session']), 'UNAUTHORIZED')
        disclosure(accepted, cfg['disclosure'])
        request = dict(interface_ref=dict(id=c.INTERFACE,version=c.VERSION),operation=operation,intent=accepted)
        c.request(request)
        if cfg['placement'] == 'local':
            owner = service(cfg['provider_config'])
            try: reply = owner.invoke(cfg['credential'], request)
            finally: owner.close()
        else:
            from .preview_transport import invoke
            reply = invoke(cfg, '/preview/model', request, accepted['deadline_ms'] if operation=='complete' else None)
        return checked(request, reply, contracts=c)
