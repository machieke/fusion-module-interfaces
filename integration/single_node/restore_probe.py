"""Operator read-only qualification inside the fenced synthetic caller pod."""
import json,sqlite3,time,uuid
from pathlib import Path
from fusion.contracts import require,decode,digest
from fusion import vector_contracts as c
from fusion.vector_composition import descriptors,select
from fusion.vector_transport import ReadNetwork
from fusion.registry import selection_token
from fusion.responses import envelope
from fusion.ports import AtomEnvelope

def query(snapshot=None):
 require((Path('/state')/'restore-fence.json').is_file(),'UNAUTHORIZED')
 # This is an explicitly NEW read-only audit request using the retained vector,
 # not a retry with a renewed deadline or a restarted native command.
 with sqlite3.connect('file:/state/measured.sqlite?mode=ro',uri=True) as db:
  original=json.loads(db.execute('SELECT request FROM app_memory_reads').fetchone()[0])
 request={**original,'request_id':str(uuid.uuid4()),'deadline_ms':time.time_ns()//1000000+30000}
 if snapshot is not None:request['snapshot']=snapshot
 chosen=select(descriptors(c.EMBEDDING,True),c.EMBEDDING,True);cfg=json.loads(Path('/config/component.json').read_text())
 def network(role):
  port=ReadNetwork(dict(host=cfg['peers'][role],port=8443,ca_file='/secrets/ca.crt'),Path('/secrets/measured-'+role+'-token').read_text().strip(),chosen,'M',service_dns=True)
  port.timeout=25.0 # NEW audit request has its own 30s deadline; old occurrences stay unchanged.
  return port
 def wire(name,op,body):
  d=chosen[name];return dict(request_id=request['request_id'],interface_ref=dict(id=name,version=d.version),profile=next(iter(d.profiles)),selection=selection_token(d),scope=request['scope'],operation=op,body=body)
 hits=network('fusion-search').invoke(wire('search','query',request));c.result(hits,request)
 refs=[h['ref'] for h in hits['hits']];require(refs,'NOT_FOUND');payloads=network('fusion-storage').invoke(wire('atom.storage','getMany',dict(refs=refs)))
 for ref,p in zip(refs,payloads):envelope(AtomEnvelope(p['ref'],p['content_type'],decode(p['data'])),ref)
 return dict(snapshot=hits['snapshot'],payloads=[decode(p['data']).decode() for p in payloads],refs=refs,request_id=request['request_id'],original_deadline_preserved=original['deadline_ms'],audit_deadline_ms=request['deadline_ms'])

def rebuild():
 require(Path('/state/restore-fence.json').is_file(),'UNAUTHORIZED')
 from fusion.memory_services import SearchPorts
 from fusion.vector_composition import ReadService
 from fusion.policy import Policy
 path='/run/fusion/owner.json';cfg=Policy(path).current();ports=SearchPorts(path);service=ReadService(path,cfg['principals']['A']['credential'],atoms=ports.atoms())
 head=service.atoms.head(ports.scope);snapshot=service.search().build(ports.scope,head);return snapshot
