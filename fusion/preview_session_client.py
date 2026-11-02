"""Session worker/client access through the same authenticated owner port."""
import json
from pathlib import Path
import uuid
from .contracts import canonical, digest, require
from .preview_sessions import PROFILE


class Client:
    def __init__(self, path):
        self.path = Path(path)
        cfg = json.loads(self.path.read_text())
        require(cfg['profile'] == PROFILE and cfg['placement'] in ('local','network'), 'UNSUPPORTED_PROFILE')
        self.binding = {k:v for k,v in cfg.items() if k != 'credential'}
        if cfg['placement'] == 'network':
            self.ca_hash = digest(Path(cfg['endpoint']['ca_file']).read_bytes())

    def invoke(self, operation, **body):
        cfg = json.loads(self.path.read_text())
        require({k:v for k,v in cfg.items() if k != 'credential'} == self.binding, 'CONFLICT')
        request = dict(id=str(uuid.uuid4()), profile=PROFILE, operation=operation,
                       body=dict(session=cfg['session'], **body))
        if cfg['placement'] == 'local':
            from .preview_session_service import SessionPorts
            reply = SessionPorts(cfg['provider_config']).invoke(cfg['credential'], request)
        else:
            from .preview_transport import invoke
            require(digest(Path(cfg['endpoint']['ca_file']).read_bytes()) == self.ca_hash, 'CONFLICT')
            reply = invoke(cfg, '/preview/session', request)
        require(type(reply) is dict and set(reply) == {'id','profile','request_digest','actor','principal','value'}, 'NOT_AVAILABLE')
        require((reply['id'],reply['profile'],reply['request_digest']) ==
                (request['id'],PROFILE,digest(canonical(request))), 'NOT_AVAILABLE')
        require(reply['principal'] == cfg['principal'] and reply['actor'] == cfg['actor'], 'UNAUTHORIZED')
        return reply['value']
