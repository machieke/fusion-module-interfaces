"""Read-only, bounded per-owner samples and authenticated-service health RTT.

Health returns no task output and consumes no work budget. It is deliberately
not reported as operation throughput. Owner CPU/RSS includes native children.
"""
import json
from pathlib import Path
from .reference_ops import Operator,PYTHON

def measure(operator):
 operator.owned();roles=[x['metadata']['name'] for x in operator.workloads()];samples={}
 source=(Path(__file__).with_name('measure.py')).read_text()
 for role in roles:
  try:samples[role]=json.loads(operator.k('exec',role+'-0','--',PYTHON,'-c',source))
  except Exception as e:samples[role]=dict(error=str(e)[-300:])
 code="""import http.client,ssl,json,time
ctx=ssl.create_default_context(cafile='/secrets/ca.crt');out={}
for role in ROLES:
 plain=role in ('omega-agent','fusion-channel-bridge','irc-server','irc-peer','f1r3node');rows=[]
 for _ in range(10):
  start=time.monotonic_ns();c=None
  try:
   c=(http.client.HTTPConnection(role,8443,timeout=2) if plain else http.client.HTTPSConnection(role,8443,timeout=2,context=ctx));c.request('GET','/health/ready');r=c.getresponse();data=r.read(4096);rows.append(dict(ns=time.monotonic_ns()-start,bytes=len(data),http=r.status))
  except Exception as e:rows.append(dict(ns=time.monotonic_ns()-start,error=type(e).__name__))
  finally:
   if c:c.close()
 out[role]=rows
print(json.dumps(out))""".replace('ROLES',repr(roles))
 rtt=json.loads(operator.k('exec','omega-agent-0','--',PYTHON,'-c',code,timeout=240))
 return dict(samples=samples,health_rtt=rtt,sample_count_per_role=10,concurrency=1,cache='warm after workflow; cold start reported separately',limitations=['health RTT is not accepted-operation latency','ten samples do not establish an SLA','operator sampling overhead included','NetworkPolicy may deliberately deny non-dependency edges'])
