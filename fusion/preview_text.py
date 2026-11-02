"""Explicit bounded synthetic text authority, opt-in beside historical lists.

The admitted text domain is unchanged by native string-safe. This avoids
guessing a preprocessing result; native parity is still exercised. Authority
and purpose are configuration, never model-controlled command arguments.
"""
import unicodedata
from .contracts import canonical, require, label

PROFILE = 'synthetic-session-text/1'


def policy(cfg):
    value = cfg.get('text_policy')
    require(type(value) is dict and set(value) == {'profile', 'scope', 'principals', 'purposes', 'max_utf8_bytes', 'revision'})
    require(value['profile'] == PROFILE and value['scope'] == cfg['scope'] and value['scope'].startswith('synthetic-'), 'UNSUPPORTED_PROFILE')
    require(type(value['principals']) is list and 1 <= len(value['principals']) <= 8 and len(set(value['principals'])) == len(value['principals']))
    require(all(label(x) for x in value['principals']) and label(value['revision']))
    require(type(value['purposes']) is list and set(value['purposes']) <= {'query', 'remember'} and value['purposes'])
    require(type(value['max_utf8_bytes']) is int and 1 <= value['max_utf8_bytes'] <= 1024)
    return value


def check(cfg, raw, purpose, principal=None):
    value = policy(cfg)
    require((principal or cfg.get('principal')) in value['principals'] and purpose in value['purposes'], 'UNAUTHORIZED')
    require(type(raw) is str and 0 < len(raw.encode()) <= value['max_utf8_bytes'])
    require(not any(unicodedata.category(x).startswith('C') for x in raw), 'INVALID_ARGUMENT')
    require(not any(x in raw for x in ('"', "'", '_quote_', '_newline_', '_apostrophe_', ':-:-:-:')), 'INVALID_ARGUMENT')
    return raw


def helper(cfg, raw, purpose, principal=None):
    if 'text_policy' in cfg: return check(cfg, raw, purpose, principal)
    require(raw in cfg['inputs'], 'UNAUTHORIZED')
    return cfg['inputs'][raw]


def query(cfg, raw, principal=None):
    if 'text_policy' in cfg: return check(cfg, raw, 'query', principal)
    require(raw in cfg['queries'], 'UNAUTHORIZED')
    return raw


def freeze(cfg, frozen):
    if 'text_policy' in cfg: frozen['text_policy'] = policy(cfg)
    return frozen
