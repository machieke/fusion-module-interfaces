"""Scoped kubectl/Helm operations for this single-node reference distribution.

Explicit context/namespace; no controller, scheduler or inferred active cluster.
"""
import json,os,subprocess,time
from pathlib import Path
from fusion.contracts import require,canonical,digest
OWNER='omega-asi-single-node-reference-1'
LABEL='omega.reference/owner'
PYTHON='/opt/native/python/bin/python3.12'
class Operator:
 def __init__(self,kubeconfig,context,namespace,release='omega'):
  require(namespace.startswith('omega-ref-') and len(namespace)<=63 and namespace!='omega-demo' and release=='omega','UNAUTHORIZED')
  self.kubeconfig=str(Path(kubeconfig).resolve());self.context=context;self.namespace=namespace;self.release=release
 def command(self,args,*,data=None,binary=False,timeout=120):
  result=subprocess.run(args,input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=not binary,timeout=timeout)
  if result.returncode:
   secret_input=False
   if isinstance(data,str):
    try:secret_input=json.loads(data).get('kind')=='Secret'
    except (ValueError,AttributeError):pass
   diagnostic='Secret update failed; material suppressed' if secret_input else (result.stderr.decode(errors='replace') if binary else result.stderr)[-2000:]
   raise RuntimeError(str(args[:3])+' '+diagnostic)
  return result.stdout
 def k(self,*args,**kw):return self.command(['kubectl','--kubeconfig',self.kubeconfig,'--context',self.context,'-n',self.namespace,*args],**kw)
 def apply(self,value):return self.k('apply','-f','-',data=json.dumps(value))
 def preflight(self):
  nodes=json.loads(self.k('get','nodes','-o','json'))['items'];require(len(nodes)==1,'UNSUPPORTED_PROFILE')
  node=nodes[0];require(any(c['type']=='Ready' and c['status']=='True' for c in node['status']['conditions']),'NOT_AVAILABLE')
  return dict(context=self.context,node=node['metadata']['name'],node_uid=node['metadata']['uid'],allocatable=node['status']['allocatable'],architecture=node['status']['nodeInfo']['architecture'],generative_runtime='NOT_CONTACTED')
 def owned(self):
  ns=json.loads(self.k('get','namespace',self.namespace,'-o','json'));require(ns['metadata'].get('labels',{}).get(LABEL)==OWNER,'UNAUTHORIZED');return ns
 def create(self):
  self.preflight();self.k('create','namespace',self.namespace);self.k('label','namespace',self.namespace,LABEL+'='+OWNER)
 def workloads(self):
  self.owned();all_items=json.loads(self.k('get','statefulsets','-o','json'))['items']
  items=[x for x in all_items if x['metadata'].get('annotations',{}).get('meta.helm.sh/release-name')==self.release and x['metadata']['annotations'].get('meta.helm.sh/release-namespace')==self.namespace and x['spec']['template']['metadata']['labels'].get('app.kubernetes.io/instance')==self.release]
  require(items and len(items)==len(all_items),'UNAUTHORIZED');return items
 def quiesce(self):
  items=self.workloads();before=dict(namespace=self.namespace,namespace_uid=self.owned()['metadata']['uid'],workloads={x['metadata']['name']:dict(uid=x['metadata']['uid'],replicas=x['spec']['replicas'],image=x['spec']['template']['spec']['containers'][0]['image']) for x in items},pods=json.loads(self.k('get','pods','-l','app.kubernetes.io/instance='+self.release,'-o','json'))['items'],pvcs=json.loads(self.k('get','pvc','-l','app.kubernetes.io/instance='+self.release,'-o','json'))['items'])
  # Stop external admission/egress and the caller first. No forced timeout
  # changes or repeat submissions; unresolved states stay in owner journals.
  roles=[x['metadata']['name'] for x in items]
  for role in ('omega-agent','fusion-channel-bridge','irc-peer'):
   if role in roles:self.k('scale','statefulset',role,'--replicas=0')
  for role in roles:
   if role not in ('omega-agent','fusion-channel-bridge','irc-peer'):self.k('scale','statefulset',role,'--replicas=0')
  if json.loads(self.k('get','pods','-l','app.kubernetes.io/instance='+self.release,'-o','json'))['items']:
   try:self.k('wait','--for=delete','pod','-l','app.kubernetes.io/instance='+self.release,'--timeout=90s',timeout=100)
   except RuntimeError:
    # The final pod may disappear after the list but before kubectl selects
    # resources for wait. Only an authoritative empty follow-up is success;
    # an error with any remaining writer must still fail closed.
    if json.loads(self.k('get','pods','-l','app.kubernetes.io/instance='+self.release,'-o','json'))['items']:raise
  require(not json.loads(self.k('get','pods','-l','app.kubernetes.io/instance='+self.release,'-o','json'))['items'],'NOT_AVAILABLE')
  return before
 def helper(self,role,image,pvc,readonly=False):
  self.owned();name='reference-copy-'+role
  value=dict(apiVersion='v1',kind='Pod',metadata=dict(name=name,namespace=self.namespace,labels={LABEL:OWNER}),spec=dict(restartPolicy='Never',terminationGracePeriodSeconds=2,automountServiceAccountToken=False,securityContext=dict(runAsUser=1000,runAsGroup=1000,runAsNonRoot=True,fsGroup=1000),containers=[dict(name='copy',image=image,imagePullPolicy='Never',command=[PYTHON,'-c','import signal,sys,time;signal.signal(signal.SIGTERM,lambda *_:sys.exit(0));time.sleep(600)'],resources=dict(requests=dict(cpu='25m',memory='32Mi'),limits=dict(cpu='500m',memory='256Mi')),securityContext=dict(allowPrivilegeEscalation=False,readOnlyRootFilesystem=True,capabilities=dict(drop=['ALL'])),volumeMounts=[dict(name='state',mountPath='/state',readOnly=readonly)])],volumes=[dict(name='state',persistentVolumeClaim=dict(claimName=pvc,readOnly=readonly))]))
  self.apply(value);self.k('wait','--for=condition=Ready','pod/'+name,'--timeout=60s');return name
 def backup(self,destination):
  root=Path(destination).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False);os.chmod(root,0o700)
  before=self.quiesce();started=time.time();manifest=dict(schema='synthetic-quiesced-backup/1',consistency='all selected StatefulSet pods terminated; each owner locked/checkpointed independently; not a distributed transaction',before=before,owners={},authority_excluded=True)
  # A standard-library maintenance tool is independent of the stopped owner's
  # inference dependencies. Pin it to the selected caller image, and retain the
  # original owner image separately as part of the consistency cut.
  maintenance_image=before['workloads']['omega-agent']['image']
  manifest['maintenance_image']=maintenance_image
  for role,entry in before['workloads'].items():
   name=self.helper(role,maintenance_image,'state-'+role+'-0')
   try:
    raw=self.k('exec',name,'--',PYTHON,'-m','integration.single_node.backup_payload','export','--role',role,binary=True)
    file=root/(role+'.tar.gz');file.write_bytes(raw);file.chmod(0o600);manifest['owners'][role]=dict(file=file.name,sha256=digest(raw),bytes=len(raw),image=entry['image'])
   finally:self.k('delete','pod',name,'--wait=true')
  manifest.update(seconds=time.time()-started,original_remains_quiesced=True);(root/'manifest.json').write_bytes(canonical(manifest));(root/'manifest.sha256').write_text(digest(canonical(manifest))+'\n');return manifest
 def restore(self,source):
  root=Path(source).resolve();raw=(root/'manifest.json').read_bytes();require(digest(raw)==(root/'manifest.sha256').read_text().strip(),'CONFLICT');manifest=json.loads(raw)
  require(manifest['schema']=='synthetic-quiesced-backup/1' and manifest['authority_excluded'] is True and self.namespace!=manifest['before']['namespace'],'UNAUTHORIZED')
  self.owned();require(not json.loads(self.k('get','pods','-o','json'))['items'],'CONFLICT')
  # The original's controlled workloads must remain stopped before this clone
  # is populated. Fencing remains mandatory even if original later resumes.
  original=Operator(self.kubeconfig,self.context,manifest['before']['namespace'],self.release);require(original.owned()['metadata']['uid']==manifest['before']['namespace_uid'],'CONFLICT');require(all(x['spec']['replicas']==0 for x in original.workloads()),'UNAUTHORIZED')
  results=[]
  for role,entry in manifest['owners'].items():
   data=(root/entry['file']).read_bytes();require(digest(data)==entry['sha256'],'CONFLICT')
   source_pvc=next(x for x in manifest['before']['pvcs'] if x['metadata']['name']=='state-'+role+'-0')
   self.apply(dict(apiVersion='v1',kind='PersistentVolumeClaim',metadata=dict(name=source_pvc['metadata']['name'],namespace=self.namespace,labels={'app.kubernetes.io/instance':self.release,'app.kubernetes.io/name':role,LABEL:OWNER}),spec={k:v for k,v in source_pvc['spec'].items() if k in ('accessModes','resources','storageClassName','volumeMode')}))
   name=self.helper(role,manifest['maintenance_image'],source_pvc['metadata']['name'])
   try:results.append(json.loads(self.k('exec','-i',name,'--',PYTHON,'-m','integration.single_node.backup_payload','restore','--role',role,'--namespace',self.namespace,data=data,binary=True)))
   finally:self.k('delete','pod',name,'--wait=true')
  return dict(status='RESTORED_FENCED',namespace=self.namespace,roles=results,automatic_resume=False,backup_sha256=digest(raw))
