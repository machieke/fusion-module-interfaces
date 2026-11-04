"""One resident pinned E5 process; fixed protocol, no caller-selected code or paths."""
import ctypes
import json
import os
from pathlib import Path
import signal
import sys
import time

from fusion import embedding_contracts as c
from fusion.contracts import canonical, digest, require


def main():
    parent = int(sys.argv[2])
    ctypes.CDLL(None).prctl(1, signal.SIGKILL)
    require(os.getppid() == parent, 'NOT_AVAILABLE')
    # Only operator configuration selects files. No runtime/model path on the wire.
    cfg = json.loads(Path(sys.argv[1]).read_text())['embedding']
    if cfg.get('denied_canary'):
        try:
            with open(cfg['denied_canary'], 'rb') as stream: stream.read(1)
        except OSError: pass
        else: require(False, 'UNAUTHORIZED')
    from .memory_build import validate_runtime
    from .memory_embedding import load
    from fusion.native_telemetry import configure,span
    diagnostics=os.environ.get('FUSION_ENCODER_DIAGNOSTICS')
    if diagnostics:
        configure(dict(workdir=diagnostics,native_telemetry=dict(profile='bounded-native-stage-timing/1',max_bytes=4194304)))
    start = time.monotonic()
    path = Path(cfg['runtime'])
    require(digest(path.read_bytes()) == cfg['runtime_sha256'], 'UNSUPPORTED_PROFILE')
    runtime = validate_runtime(path)
    encode = load(cfg['native_source'], runtime['model'], runtime['model_spec']['files'])
    model = encode.__globals__['_embedding_model']
    require(str(model.device) == 'cpu' and model.max_seq_length == 512, 'UNSUPPORTED_PROFILE')
    # Reserve stdout for the bounded protocol; third-party diagnostics stay private.
    print(canonical(dict(ready=True, model=c.v.EMBEDDING, max_tokens=model.max_seq_length,
        device=str(model.device), caller_canary_inaccessible=bool(cfg.get('denied_canary')),
        readiness_ms=(time.monotonic()-start)*1000)).decode(), flush=True)
    for line in sys.stdin.buffer:
        require(len(line) <= c.MAX_WIRE_BYTES)
        value = c.intent(json.loads(line))
        require(time.time_ns()//1_000_000 <= value['deadline_ms'], 'DEADLINE_EXCEEDED')
        with span('provider.e5_encode',request_bytes=len(value['text'].encode())) as meter:
            result = c.encoded(value, encode(value['text']))
            meter['response_bytes']=len(canonical(result))
        print(canonical(result).decode(), flush=True)


if __name__ == '__main__': main()
