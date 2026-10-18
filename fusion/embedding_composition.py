"""Trusted selection and placement only; the application imports no model implementation."""
import json
from pathlib import Path

from . import embedding_contracts as c, vector_contracts as v
from .contracts import digest, require
from .registry import descriptor_read, selection_token
from .embedding_transport import EmbeddingLocal, EmbeddingNetwork


def configuration(path,profile=c.PROFILE):
    cfg = json.loads(Path(path).read_text())
    require(cfg['sharing'] == v.PRIVACY and cfg['profile'] == profile and cfg['fallback'] is False, 'UNSUPPORTED_PROFILE')
    require(cfg['model'] == v.EMBEDDING and cfg['preprocessing'] == c.PREPROCESSING, 'UNSUPPORTED_PROFILE')
    require(type(cfg['inputs']) is dict and 1 <= len(cfg['inputs']) <= 32)
    for command, helper in cfg['inputs'].items(): v.query_text(command); c.text(helper)
    chosen = c.select([descriptor_read(d) for d in cfg['catalogue']],profile)
    frozen = {k:cfg[k] for k in ('principal', 'scope', 'sharing', 'profile', 'model', 'preprocessing', 'inputs', 'placement')}
    frozen['selection'] = selection_token(chosen)
    if cfg['placement'] == 'network':
        require('provider_config' not in cfg, 'UNSUPPORTED_PROFILE')
        endpoint = cfg['endpoint']
        frozen['endpoint'] = {**endpoint, 'ca_sha256': digest(Path(endpoint['ca_file']).read_bytes())}
    else:
        require(cfg['placement'] == 'local', 'UNSUPPORTED_PROFILE')
        frozen['provider_config'] = cfg['provider_config']
    return cfg, chosen, frozen


def binding(cfg, chosen):
    if cfg['placement'] == 'network':
        return EmbeddingNetwork(cfg['endpoint'], cfg['credential'], chosen)
    from .adapters.native_e5 import NativeE5
    from .embedding_service import EmbeddingService
    encoder = NativeE5(cfg['provider_config'])
    try: service = EmbeddingService(cfg['provider_config'], encoder)
    except BaseException: encoder.close(); raise
    return EmbeddingLocal(service, cfg['credential'])
