"""Selected SDK AtomStorage/feed client; no physical backend on the caller."""
import time
from .preview_client import AtomFeedClient, Endpoint
from .registry import descriptor_read


def client(cfg, deadline_ms=None):
    return AtomFeedClient(Endpoint(**cfg['endpoint']),cfg['credential'],cfg['principal'],cfg['scope'],
        descriptor_read(cfg['descriptor']),deadline_ms=deadline_ms or time.time_ns()//1_000_000+25000,
        composition=cfg['composition'],feed_profile=cfg.get('feed_profile','immutable-commit-feed/1'))
