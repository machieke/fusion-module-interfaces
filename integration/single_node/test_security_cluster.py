"""Same-principal rotation, real TLS refusal and compatible S01 rollouts."""
import argparse,base64,json,secrets,subprocess,sys,traceback,hashlib,time
from pathlib import Path
from .test_cluster import Cluster,ROOT,ROLES
from .test_memory_cluster import MemoryCluster
class Security(Cluster):
 ended=MemoryCluster.ended
 def run(self):
  self.values['networkPolicy']=dict(enabled=True);self.install();self.ended(70);before=self.snapshot('completed');self.success(before)
  job=before['fusion-execution']['jobs'][0]['id'];request=json.loads(before['omega-agent']['caller_requests'][0]['request']);request={k:v for k,v in request.items() if k in ('message_id','interface_ref','profile','selection','scope_ref')};request.update(operation='status',body=dict(job_id=job))
  def probe(expected=None):
   code="""import json
from pathlib import Path
from fusion.neoclaw_transport import binding
from fusion import neoclaw_contracts as c
from fusion.registry import descriptor_read
from fusion.contracts import ContractError
cfg=json.loads(Path('/run/fusion/caller.json').read_text());selected=c.selected([descriptor_read(x) for x in cfg['catalogue']]);q=REQUEST
try:
 v=binding(cfg,selected).invoke(q);print(json.dumps(dict(status=v['execution'])))
except ContractError as e:print(json.dumps(dict(error=e.code)))
""".replace('REQUEST',repr(request))
   v=json.loads(self.exec('omega-agent',code));assert v==({'error':expected} if expected else {'status':'succeeded'}),v;return v
  probe();root=self.root/'private-secrets';original=json.loads((root/'fusion-execution.secret.json').read_text());agent=json.loads((root/'omega-agent.secret.json').read_text())
  def secret(name,patch):
   # Secret content travels on stdin and is never written to test reports.
   current=json.loads(self.k('get','secret',name,'-o','json'));current['data'].update(patch);current['metadata'].pop('managedFields',None)
   self.k('replace','-f','-',input=json.dumps(current))
  def restart(role):
   self.replace(role);self.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=40s');self.wait(lambda:self.file(role,'process.json'),30)
   if role=='omega-agent':self.ended(35)
  # Leaf changes preserve the CA/endpoint binding of already accepted calls.
  dns='fusion-execution.'+self.name+'.svc.cluster.local'
  def certificate(san,days,stem):
   def ssl(*args):subprocess.run(['openssl',*map(str,args)],cwd=root,check=True,capture_output=True)
   ssl('req','-newkey','rsa:2048','-nodes','-keyout',stem+'.key','-out',stem+'.csr','-subj','/CN=fusion-execution')
   (root/(stem+'.ext')).write_text('subjectAltName=DNS:'+san+'\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n')
   ssl('x509','-req','-in',stem+'.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial','-out',stem+'.crt','-days',days,'-extfile',stem+'.ext')
   return {k:base64.b64encode((root/(stem+ext)).read_bytes()).decode() for k,ext in [('tls.crt','.crt'),('tls.key','.key')]}
  self.report['tls_negatives']={}
  for stem,san,days in [('wrong-host','not-this-service.invalid','7'),('expired',dns,'-1')]:
   patch=certificate(san,days,stem);secret('fusion-execution-tls-auth',patch);restart('fusion-execution');self.report['tls_negatives'][stem]=probe('NOT_AVAILABLE')
  leaf=certificate(dns,'7','rotated');new=secrets.token_hex(32);encoded=base64.b64encode(new.encode()).decode()
  secret('fusion-execution-tls-auth',{**leaf,'caller-token':encoded});restart('fusion-execution');probe('UNAUTHORIZED')
  # Wrong service principal has a valid credential but lacks execution status.
  secret('omega-agent-tls-auth',{'fusion-execution-token':original['data']['worker-token']});restart('omega-agent');probe('UNAUTHORIZED')
  secret('omega-agent-tls-auth',{'fusion-execution-token':encoded});restart('omega-agent');probe()
  rotated=self.snapshot('rotated');self.success(rotated);self.same_identity(before,rotated)
  self.report['rotation']=dict(same_principal='A',CA_unchanged=True,leaf_changed=True,old_credential_refused=True,wrong_principal_refused=True,private_keys_published=False)
  # Same validated state schema/profile, reversible ConfigMap revision only.
  for role in ROLES:self.config(role,revision='compatible-rollout-2')
  self.upgrade()
  for role in ROLES:self.wait(lambda:self.file(role,'process.json')['configuration_revision']=='compatible-rollout-2',45)
  self.ended(40);upgraded=self.snapshot('upgraded');self.success(upgraded);self.same_identity(before,upgraded)
  self.command(['helm','rollback','omega','1','--kubeconfig',self.args.kubeconfig,'--namespace',self.name,'--wait','--timeout','120s'])
  for role in ROLES:self.wait(lambda:self.file(role,'process.json')['configuration_revision']=='initial',45)
  self.ended(40);rolled=self.snapshot('rolled-back');self.success(rolled);self.same_identity(before,rolled)
  # Refuse a mismatched owner seal before opening or migrating its journal.
  cfg=json.loads(self.k('get','configmap','fusion-execution','-o','json'));saved=cfg['data']['component.json'];wrong=json.loads(saved);wrong['service_composition']='incompatible-owner/99';cfg['data']['component.json']=json.dumps(wrong)
  self.k('replace','-f','-',input=json.dumps(cfg));self.replace('fusion-execution')
  self.wait(lambda:'UNSUPPORTED_PROFILE' in self.k('logs','fusion-execution-0'),30)
  cfg=json.loads(self.k('get','configmap','fusion-execution','-o','json'));cfg['data']['component.json']=saved;self.k('replace','-f','-',input=json.dumps(cfg));restart('fusion-execution');probe()
  final=self.snapshot('after-incompatible-refusal');assert final['fusion-execution']['jobs']==before['fusion-execution']['jobs'];assert final['fusion-execution']['s01_work']==before['fusion-execution']['s01_work']
  self.report.update(status='PASS',upgrade_rollback='PASS same validated profile/schema only; incompatible composition refused',live_generations=0)
def main():
 p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--prefix',required=True);p.add_argument('--output',required=True);p.add_argument('--image-tag',required=True);a=p.parse_args();assert a.prefix.startswith('omega-ref-');a.chart=ROOT/'deploy/helm/omega-fusion';test=Security(a,'security')
 try:test.run()
 except Exception as e:
  test.report.update(status='FAIL',failure=str(e),traceback=traceback.format_exc())
  try:test.snapshot('failure')
  except Exception:pass
 finally:
  for role in ROLES:
   try:(test.root/(role+'.log')).write_text(test.k('logs',role+'-0'))
   except Exception:pass
  test.finish()
 print(test.report['status'],test.report.get('failure',''));raise SystemExit(test.report['status']!='PASS')
if __name__=='__main__':main()
