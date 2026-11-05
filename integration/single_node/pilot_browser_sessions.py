"""Opt-in, finite synthetic browser sessions; no provider secrets reach the client.

Authentication state is ephemeral. Restart/log out requires signing in again,
while all native work remains in the application owner. Policy is reread on
every request, including already authenticated connections. No expiry renewal.
"""
from dataclasses import dataclass
from hashlib import sha256
from http.cookies import SimpleCookie
import hmac
from pathlib import Path
import re
import secrets
import threading
import time

from fusion.contracts import canonical, digest, require
from fusion.preview_client import strict_json

PROFILE = 'synthetic-browser-sessions/1'
COOKIE = 'omega_pilot'
ROLES = frozenset(('viewer', 'developer', 'operator'))


def configuration(path):
    path = Path(path)
    require(path.is_file() and path.stat().st_size <= 131072, 'UNAUTHORIZED')
    cfg = strict_json(path.read_bytes())
    require(type(cfg) is dict and {'profile', 'namespace', 'users'}<=set(cfg)<={'profile', 'namespace', 'users','handover'}, 'UNAUTHORIZED')
    require(cfg['profile'] == PROFILE and type(cfg['namespace']) is str and
            cfg['namespace'].startswith('omega-ref-') and cfg['namespace'] not in ('omega-ref-live01',), 'UNAUTHORIZED')
    require(type(cfg['users']) is dict and 1 <= len(cfg['users']) <= 16, 'UNAUTHORIZED')
    if 'handover' in cfg:
        from .pilot_browser_handover import selection
        selection(cfg['handover'],cfg['namespace'])
    for name, user in cfg['users'].items():
        require(type(name) is str and re.fullmatch('[a-z][a-z0-9-]{0,31}', name), 'UNAUTHORIZED')
        require(type(user) is dict and set(user) == {'bootstrap_sha256', 'revision', 'role', 'enabled', 'session_seconds', 'targets'}, 'UNAUTHORIZED')
        require(type(user['bootstrap_sha256']) is str and re.fullmatch('[a-f0-9]{64}', user['bootstrap_sha256']), 'UNAUTHORIZED')
        require(type(user['revision']) is int and user['revision'] > 0 and user['role'] in ROLES and type(user['enabled']) is bool, 'UNAUTHORIZED')
        require(type(user['session_seconds']) is int and 30 <= user['session_seconds'] <= 3600, 'UNAUTHORIZED')
        require(type(user['targets']) is dict and 1 <= len(user['targets']) <= 2, 'UNAUTHORIZED')
        for role, target in user['targets'].items():
            require(role in ('omega-agent', 'omega-agent-b') and type(target) is dict and
                    {'principal', 'scope', 'endpoint', 'credential_file'} <= set(target) <= {'principal', 'scope', 'endpoint', 'credential_file', 'search_maintenance'}, 'UNAUTHORIZED')
            require(target['principal'] in ('A', 'B') and type(target['scope']) is str and
                    target['scope'].startswith('synthetic-'), 'UNAUTHORIZED')
            require(type(target['credential_file']) is str and Path(target['credential_file']).is_absolute(), 'UNAUTHORIZED')
            if 'search_maintenance' in target:
                maintenance=target['search_maintenance']
                require(user['role']=='operator' and type(maintenance) is dict and set(maintenance)=={'profile','endpoint','credential_file'} and
                    maintenance['profile']=='expired-unpublished-search-reclamation/1','UNAUTHORIZED')
                require(type(maintenance['credential_file']) is str and Path(maintenance['credential_file']).is_absolute(),'UNAUTHORIZED')
                ep=maintenance['endpoint']
                require(type(ep) is dict and set(ep)=={'host','port','ca_file'} and ep['host'] in
                    ('127.0.0.1','fusion-search.'+cfg['namespace']+'.svc.cluster.local') and type(ep['port']) is int and
                    1<=ep['port']<=65535 and type(ep['ca_file']) is str and Path(ep['ca_file']).is_absolute(),'UNAUTHORIZED')
            ep = target['endpoint']
            require(type(ep) is dict and set(ep) == {'host', 'port', 'ca_file'}, 'UNAUTHORIZED')
            require(type(ep['host']) is str and (ep['host'] == '127.0.0.1' or
                    ep['host'] == role+'.'+cfg['namespace']+'.svc.cluster.local'), 'UNAUTHORIZED')
            require(type(ep['port']) is int and 1 <= ep['port'] <= 65535 and
                    type(ep['ca_file']) is str and Path(ep['ca_file']).is_absolute(), 'UNAUTHORIZED')
    return cfg


@dataclass(frozen=True)
class Session:
    user: str
    policy: str
    csrf: str
    until: float
    expires_ms: int


class Sessions:
    def __init__(self, path, *, clock=time.monotonic, wall=lambda: time.time_ns()//1000000):
        self.path = Path(path); self.clock = clock; self.wall = wall
        self.lock = threading.Lock(); self.sessions = {}; self.last_clock = self.clock()
        configuration(self.path)

    def _now(self):
        now = self.clock()
        require(now >= self.last_clock, 'UNAUTHORIZED')
        self.last_clock = now
        self.sessions = {k: v for k, v in self.sessions.items() if v.until > now}
        return now

    def login(self, user, credential):
        require(type(user) is str and type(credential) is str and 32 <= len(credential) <= 256, 'UNAUTHORIZED')
        cfg = configuration(self.path); selected = cfg['users'].get(user)
        expected = selected['bootstrap_sha256'] if selected else '0'*64
        require(hmac.compare_digest(sha256(credential.encode()).hexdigest(), expected) and
                selected is not None and selected['enabled'], 'UNAUTHORIZED')
        with self.lock:
            now = self._now()
            require(len(self.sessions) < 64 and sum(s.user == user for s in self.sessions.values()) < 4, 'OVERLOADED')
            token = secrets.token_urlsafe(32)
            session = Session(user, digest(canonical(selected)), secrets.token_urlsafe(32),
                              now+selected['session_seconds'], self.wall()+1000*selected['session_seconds'])
            self.sessions[token] = session
        return token, self.public(session, selected)

    def authenticate(self, cookies, csrf=None, mutation=False):
        require(type(cookies) is str and len(cookies) <= 512, 'UNAUTHORIZED')
        parsed = SimpleCookie()
        try: parsed.load(cookies)
        except Exception: require(False, 'UNAUTHORIZED')
        require(set(parsed) == {COOKIE} and cookies.count(COOKIE+'=') == 1, 'UNAUTHORIZED')
        token = parsed[COOKIE].value
        with self.lock:
            self._now(); session = self.sessions.get(token)
            require(session is not None, 'UNAUTHORIZED')
            selected = configuration(self.path)['users'].get(session.user)
            require(selected is not None and selected['enabled'] and digest(canonical(selected)) == session.policy, 'UNAUTHORIZED')
            if mutation:
                require(type(csrf) is str and hmac.compare_digest(csrf, session.csrf), 'UNAUTHORIZED')
            return token, session, selected

    def logout(self, token):
        with self.lock: self.sessions.pop(token, None)

    @staticmethod
    def public(session, selected):
        return dict(profile=PROFILE, user=session.user, role=selected['role'], csrf=session.csrf,
                    expires_ms=session.expires_ms, expiry_renewal=False,
                    authority='CURRENT_SCOPE_POLICY_RECHECKED_BY_OWNER')
