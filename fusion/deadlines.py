"""Cooperative same-host absolute deadline; no scheduling or clock discipline."""
import time
from .contracts import require


def remaining(deadline_ms, ceiling=10):
    if deadline_ms is None:return ceiling
    left=deadline_ms/1000-time.time()
    require(left>0,'NOT_AVAILABLE')
    return min(ceiling,left)
