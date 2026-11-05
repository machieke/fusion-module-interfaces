"""Opt-in non-work readiness before one unchanged isolated-chain reader.

The eight health attempts are observations, not artifact or effect retries.
This operator composition is absent from historical reader paths by default.
"""
import argparse
import hashlib
import http.client
import json
from pathlib import Path
import time

PROFILE = 'bounded-chain-consumer-readiness/1'
MAX_OBSERVER_SECONDS = 180

def health(config,events):
 import ssl,signal,socket
 end=time.monotonic()+30;count=0
 endpoint=config['atoms']['endpoint'];context=ssl.create_default_context(cafile=endpoint['ca_file']);context.minimum_version=ssl.TLSVersion.TLSv1_2
 def timedout(*_):raise TimeoutError('bounded health observation expired')
 previous=signal.signal(signal.SIGALRM,timedout);signal.setitimer(signal.ITIMER_REAL,30)
 try:
  while count<8 and time.monotonic()<end:
   count+=1;entry=dict(stage='storage-path-health',attempt=count,observed_ms=time.time_ns()//1000000);events.append(entry)
   conn=http.client.HTTPSConnection(endpoint['host'],endpoint['port'],context=context,timeout=min(2,end-time.monotonic()))
   try:
    conn.request('GET','/health/ready',headers={'Connection':'close'});response=conn.getresponse();entry['http_status']=response.status
    raw=b''
    while len(raw)<=4096:
     remaining=end-time.monotonic()
     if remaining<=0:raise TimeoutError('health observation expired')
     if response.fp is not None:response.fp.raw._sock.settimeout(min(2,remaining))
     part=response.read1(min(4097-len(raw),4096))
     if not part:break
     raw+=part
    if len(raw)>4096:raise ValueError('oversized health response')
    value=json.loads(raw);valid=type(value)is dict and set(value)=={'role','ready'} and value['role']=='fusion-storage' and type(value['ready'])is bool
    entry['shape_valid']=valid;entry['ready']=valid and value['ready']
    if not valid:raise ValueError('invalid health response')
    if response.status==200 and value['ready']:
     entry['status']='READY';return
    if response.status!=503 or value['ready']:raise ValueError('inconsistent health response')
    entry['status']='NOT_READY'
   except (OSError,http.client.HTTPException)as error:entry.update(status='TRANSPORT_FAILED',error_class=type(error).__name__,errno=getattr(error,'errno',None))
   finally:conn.close()
   if count<8 and time.monotonic()<end:time.sleep(min(1,end-time.monotonic()))
  raise TimeoutError('bounded consumer-path readiness not established')
 finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)

def observe_with_health(reader, trace, config, events):
    # Validate the existing scope/endpoint/read authority before any contact.
    approved, _ = reader.trace_plan(trace)
    reader.configuration(config, approved.scope_ref)
    health(config, events)
    return reader.observe(trace, config)


def main(reader_source):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', required=True)
    parser.add_argument('--config', required=True)
    args = parser.parse_args()
    events = []
    identity = hashlib.sha256(reader_source.encode()).hexdigest()
    namespace = {'__name__': 'pinned_existing_chain_reader'}
    exec(compile(reader_source, 'pinned_existing_chain_reader.py', 'exec'), namespace)
    from types import SimpleNamespace
    reader = SimpleNamespace(**namespace)
    try:
        trace = reader.strict_json(Path(args.trace).read_bytes())
        config = reader.strict_json(Path(args.config).read_bytes())
        result = observe_with_health(reader, trace, config, events)
    except Exception as error:
        result = dict(status='FAIL', error=dict(type=type(error).__name__,
            code=getattr(error, 'code', None)), submissions=0, signing_performed=False,
            additional_live_generations=0)
    result['consumer_path_readiness'] = dict(profile=PROFILE,
        original_reader_sha256=identity, health_attempts=events,
        maximum_health_attempts=8, maximum_health_seconds=30,
        artifact_retries=0, original_reader_invocations=int(any(x.get('status') == 'READY' for x in events)))
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0 if result['status'] == 'PASS' else 1


def compose(reader_source):
    """Embed exact trusted operator source; runtime images need no examples package."""
    if type(reader_source) is not str or not 1 <= len(reader_source.encode()) <= 65536:
        raise ValueError('bounded original reader source required')
    compile(reader_source, 'pinned_existing_chain_reader.py', 'exec')
    return Path(__file__).read_text() + '\nif __name__ == "__main__":\n    raise SystemExit(main(' + repr(reader_source) + '))\n'
