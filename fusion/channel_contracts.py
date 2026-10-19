"""S06 closed IRC composition profile over existing AtomStorage/Messaging ports."""
import re
import textwrap
import uuid
from .contracts import (canonical, digest, require, validate, PROFILES, encode, decode,
                        validate_ref)
from .neoclaw_contracts import fields
from .registry import descriptors, resolve, Requirement, selection_token

PROFILE = 'isolated-irc-mailbox/1'
APPLICATION = 'controlled-native-loop/8'
CONTENT = 'application/neoclaw-channel'
MAX_EVENTS = 128
PENDING = 4
MAILBOX_CAPACITY = 2
MAX_ATTEMPTS = 32
MAX_FRAME = 512
MAX_BODY = 400
OPERATIONS = {'atom.storage': ('create', 'get'), 'agent.messaging': ('send', 'poll', 'ack')}


def identifier(value):
    require(type(value) is str and len(value) <= 128)
    try: require(str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError): require(False)
    return value


def text(value):
    require(type(value) is str)
    try: size=len(value.encode('utf-8'))
    except UnicodeError: require(False)
    require(0 < size <= MAX_BODY)
    require(all(ord(x) >= 32 and ord(x) != 127 for x in value))
    return value


def output(value, approved, target):
    text(value)
    # Exact original single-chunk domain; no stripping, splitting or wrapping.
    require('\\n' not in value and textwrap.wrap(value, width=400, break_long_words=True,
        break_on_hyphens=False) == [value], 'INVALID_ARGUMENT')
    require(len(('PRIVMSG '+target+' :'+value+'\r\n').encode()) <= MAX_FRAME)
    require(value in approved, 'UNAUTHORIZED')
    return value


def route_config(cfg):
    require(cfg['profile'] == PROFILE and cfg['sharing'] == 'generated-shareable', 'UNSUPPORTED_PROFILE')
    require(type(cfg['target']) is str and re.fullmatch(r'#[a-z0-9-]{1,30}', cfg['target']))
    for key in ('session', 'bridge'): identifier(cfg[key])
    require(cfg['ingress_route'] != cfg['egress_route'], 'UNSUPPORTED_PROFILE')
    require(type(cfg['approved_inputs']) is list and type(cfg['approved_outputs']) is list)
    for value in cfg['approved_inputs']: text(value)
    for value in cfg['approved_outputs']: output(value, cfg['approved_outputs'], cfg['target'])
    return cfg


def record(value, cfg):
    fields(value, 'profile kind scope route bridge session id epoch sequence observed_ms nick target text deadline_ms')
    route_config(cfg)
    require(value['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    for key in ('scope','bridge','session','target'): require(value[key] == cfg[key], 'UNAUTHORIZED')
    identifier(value['id']); text(value['text'])
    require(type(value['sequence']) is int and 1 <= value['sequence'] <= MAX_EVENTS*5)
    for key in ('observed_ms','deadline_ms'): require(type(value[key]) is int and value[key] > 0)
    require(value['deadline_ms'] > value['observed_ms'])
    if value['kind'] == 'ingress':
        identifier(value['epoch']); require(value['route'] == cfg['ingress_route'], 'UNAUTHORIZED')
        require(type(value['nick']) is str and re.fullmatch(r'[A-Za-z_\[\]\\`^{}][A-Za-z0-9_\-\[\]\\`^{}]{0,29}', value['nick']))
        require(value['text'] in cfg['approved_inputs'], 'UNAUTHORIZED')
        expected=str(uuid.uuid5(uuid.UUID(value['epoch']), str(value['sequence'])))
        require(value['id'] == expected, 'CONFLICT')
    else:
        require(value['kind'] == 'egress' and value['route'] == cfg['egress_route'], 'UNAUTHORIZED')
        require(value['epoch'] is None and value['nick'] is None)
        output(value['text'], cfg['approved_outputs'], cfg['target'])
    return value


def selected(catalogue=None):
    return {name:resolve(catalogue or descriptors(), Requirement(name,'1.0.0','1.0.1',PROFILES[name],
        frozenset(ops),frozenset({'process-restart','scoped','idempotent'}))) for name,ops in OPERATIONS.items()}


def selection(chosen): return {name:selection_token(d) for name,d in chosen.items()}


def wire(request, chosen):
    fields(request, 'channel_profile selections principal invocation')
    require(request['channel_profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    require(request['selections'] == selection(chosen), 'UNSUPPORTED_PROFILE')
    require(type(request['principal']) is str)
    name, op = validate(request['invocation'], check_deadline=False)
    require(name in OPERATIONS and op in OPERATIONS[name], 'UNSUPPORTED_OPERATION')
    require(request['invocation']['profile'] == PROFILES[name], 'UNSUPPORTED_PROFILE')
    require('extensions' not in request['invocation'] and 'required_features' not in request['invocation'])
    require(len(canonical(request)) <= 16384)
    return name,op


def delivery(value, cfg, kind):
    require(type(value) is dict and value['scope_ref'] == cfg['scope'], 'NOT_AVAILABLE')
    route=cfg['ingress_route' if kind=='ingress' else 'egress_route']
    require(value['route'] == route and type(value['order']) is int, 'NOT_AVAILABLE')
    body=value['body'];fields(body,'ref correlation_id reply_route causation_id')
    validate_ref(body['ref'],cfg['scope'])
    require(body['reply_route'] == cfg['egress_route' if kind=='ingress' else 'ingress_route'], 'NOT_AVAILABLE')
    identifier(body['correlation_id'])
    return value
