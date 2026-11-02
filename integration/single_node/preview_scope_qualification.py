"""Real private-scope denials and service rotation on a fresh preview namespace.

Only two generated opaque AtomStorage records are created. No native answers,
private user data, application occurrences or model reservations are supplied.
Run after native qualification; the operator may rotate this namespace's keys.
"""
import argparse,base64,json,secrets,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .reference_ops import Operator,PYTHON


class Qualification:
    def __init__(self,op,output,private_material):
        self.op=op;self.root=Path(output);self.root.mkdir(parents=True,exist_ok=False)
        self.material=Path(private_material).resolve()
        self.report=dict(namespace=op.namespace,classification='REAL_DEPLOYED_ATOMSTORAGE_DETTA_HTTPS',
            additional_live_generations=0,synthetic_private_records=2,cases=[])
    def save(self): (self.root/'report.json').write_bytes(canonical(self.report))
    def pod(self,role):
        value=json.loads(self.op.k('get','pod',role+'-0','-o','json'))
        return dict(uid=value['metadata']['uid'],images=[x['imageID'] for x in value['status']['containerStatuses']],
            claims=[x['persistentVolumeClaim']['claimName'] for x in value['spec']['volumes'] if 'persistentVolumeClaim' in x])
    def call(self,role,operation,*,scope=None,ref=None,through=None,wrong=False):
        source="""import json,time
from pathlib import Path
from fusion.preview_atoms import client
from fusion.ports import Mutation
from fusion.contracts import ContractError,digest
cfg=json.loads(Path('/run/fusion/private-atoms.json').read_text())
cfg['endpoint']['timeout_seconds']=25
if SCOPE is not None:cfg['scope']=SCOPE
if WRONG:cfg['credential']='wrong-synthetic-qualification-token'
port=client(cfg,time.time_ns()//1000000+30000)
try:
 if OP=='create':value=port.create(Mutation(cfg['scope'],'phase2-private-scope-record'), 'text/plain',('Generated private denial scope for '+cfg['principal']).encode())
 elif OP=='get':value=dict(digest=digest(port.get(REF).bytes))
 elif OP=='getMany':value=dict(digests=[digest(x.bytes) for x in port.getMany((REF,))])
 elif OP=='availability':value=port.availability(REF)
 elif OP=='head':value=port.head(cfg['scope'])
 elif OP=='readCommits':value=port.readCommits(cfg['scope'],0,THROUGH,8)
 else:raise RuntimeError('Unsupported qualification operation')
 print(json.dumps(dict(value=value)))
except ContractError as error:print(json.dumps(dict(error=error.code)))
"""
        for name,value in [('SCOPE',scope),('WRONG',wrong),('OP',operation),('REF',ref),('THROUGH',through)]:source=source.replace(name,repr(value))
        return json.loads(self.op.k('exec','-i',role+'-0','--',PYTHON,'-',data=source,timeout=40))
    def case(self,name,result,expected=None):
        passed=result.get('error')==expected if expected else 'value' in result
        self.report['cases'].append(dict(name=name,result=result,expected_error=expected,passed=passed));self.save()
        require(passed,'CONFLICT');return result.get('value')
    def replace(self,role):
        before=self.pod(role);self.op.k('delete','pod',role+'-0','--grace-period=1','--wait=true',timeout=45)
        self.op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=120s',timeout=130)
        after=self.pod(role);require(before['uid']!=after['uid'] and before['claims']==after['claims'] and before['images']==after['images'],'CONFLICT')
        return dict(before=before,after=after)
    def secret(self,role):return json.loads(self.op.k('get','secret',role+'-tls-auth','-o','json'))
    def put_secret(self,value):
        self.op.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name=value['metadata']['name']),type='Opaque',data=value['data']))
    def idle(self):
        from .preview_qualification import Runner
        api=Runner.__new__(Runner);api.op=self.op;result={}
        for role in ('omega-agent','omega-agent-b'):
            inventory=api.call(role,'inventory');result[role]={}
            for sid in inventory['sessions']:
                page=api.call(role,'observe',sid);rows=list(page['inputs'])
                while page['next_after'] is not None:
                    page=api.call(role,'observe',sid,'--after',str(page['next_after']));rows+=page['inputs']
                require(all(row['state']=='complete' for row in rows),'CONFLICT')
                result[role][sid]=dict(completed_inputs=len(rows),pending_inputs=0)
        return result
    def models(self):
        source="""import json,sqlite3,hashlib
from pathlib import Path
p=Path('/state/model.sqlite');result=[]
if p.exists():
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
  if db.execute("SELECT 1 FROM sqlite_master WHERE name='model_calls'").fetchone():
   result=[dict(id=r[0],reserved=r[1],captured_ms=r[2],response_sha256=hashlib.sha256(r[3].encode()).hexdigest() if r[3] else None) for r in db.execute('SELECT id,reserved,captured_ms,response FROM model_calls ORDER BY id')]
print(json.dumps(result))
"""
        return json.loads(self.op.k('exec','-i','fusion-model-0','--',PYTHON,'-',data=source,timeout=30))
    def run(self):
        self.op.owned();records={};heads={}
        self.report.update(initial_pods={r:self.pod(r) for r in ('omega-agent','omega-agent-b','fusion-storage','fusion-model')},
            idle_before=self.idle(),model_accounting_before=self.models());self.save()
        for role in ('omega-agent','omega-agent-b'):
            records[role]=self.case(role+'-private-create',self.call(role,'create'))['ref']
            self.case(role+'-private-get',self.call(role,'get',ref=records[role]))
            heads[role]=self.case(role+'-private-head',self.call(role,'head'))
            page=self.case(role+'-private-feed',self.call(role,'readCommits',through=heads[role]))
            require(heads[role]['sequence']==1 and page['complete'] is True and len(page['records'])==1
                and page['records'][0]['ref']==records[role],'CONFLICT')
            self.case(role+'-wrong-credential',self.call(role,'head',wrong=True),'UNAUTHORIZED')
        require(records['omega-agent']['scope_ref']!=records['omega-agent-b']['scope_ref'],'CONFLICT')
        for actor,target in [('omega-agent','omega-agent-b'),('omega-agent-b','omega-agent')]:
            for method in ('create','get','getMany','availability','head','readCommits'):
                self.case(actor+'-denied-'+target+'-'+method,self.call(actor,method,scope=records[target]['scope_ref'],
                    ref=records[target],through=heads[target]),'UNAUTHORIZED')
        self.report['records']=records;self.save()
        # Outage is an observation failure. It does not submit/replay any write.
        try:
            self.op.k('scale','statefulset/fusion-storage','--replicas=0')
            self.op.k('wait','--for=delete','pod/fusion-storage-0','--timeout=90s',timeout=100)
            self.case('storage-outage',self.call('omega-agent','head'),'NOT_AVAILABLE')
        finally:
            self.op.k('scale','statefulset/fusion-storage','--replicas=1')
            self.op.k('wait','--for=condition=Ready','pod/fusion-storage-0','--timeout=120s',timeout=130)
        require(self.case('storage-return',self.call('omega-agent','head'))==heads['omega-agent'],'CONFLICT')
        # Rotate the A storage credential, leaving old caller authority rejected
        # until its own Secret and process configuration are deliberately changed.
        storage=self.secret('fusion-storage');caller=self.secret('omega-agent')
        token=base64.b64encode(secrets.token_hex(32).encode()).decode()
        storage['data']['cog-caller-A-token']=token;self.put_secret(storage)
        self.report['storage_credential_replacement']=self.replace('fusion-storage');self.save()
        self.case('revoked-old-A-credential',self.call('omega-agent','head'),'UNAUTHORIZED')
        self.case('B-unaffected-by-A-revocation',self.call('omega-agent-b','head'))
        caller['data']['atom-A-token']=token;self.put_secret(caller)
        self.report['caller_credential_replacement']=self.replace('omega-agent');self.save()
        require(self.case('new-A-credential',self.call('omega-agent','head'))==heads['omega-agent'],'CONFLICT')
        # Fresh leaf certificate, same pinned CA and DNS. No CA substitution or
        # weakened hostname checks, and no private material enters the report.
        role='fusion-storage';certdir=self.material/'scope-rotation';certdir.mkdir(mode=0o700)
        def ssl(*args):subprocess.run(['openssl',*map(str,args)],cwd=certdir,check=True,capture_output=True)
        ssl('req','-newkey','rsa:2048','-nodes','-keyout','server.key','-out','server.csr','-subj','/CN='+role)
        (certdir/'extensions').write_text('subjectAltName=DNS:'+role+'.'+self.op.namespace+'.svc.cluster.local\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n')
        ssl('x509','-req','-in','server.csr','-CA',self.material/'ca.crt','-CAkey',self.material/'ca.key',
            '-set_serial',str(secrets.randbits(120)),'-out','server.crt','-days','7','-extfile','extensions')
        storage=self.secret(role);old=digest(base64.b64decode(storage['data']['tls.crt']))
        for key,file in [('tls.crt','server.crt'),('tls.key','server.key')]:storage['data'][key]=base64.b64encode((certdir/file).read_bytes()).decode()
        self.put_secret(storage);self.report['tls_replacement']=self.replace(role)
        self.report['certificate_sha256']=dict(before=old,after=digest((certdir/'server.crt').read_bytes()))
        require(self.report['certificate_sha256']['before']!=self.report['certificate_sha256']['after'],'CONFLICT')
        self.case('same-CA-rotated-leaf',self.call('omega-agent','get',ref=records['omega-agent']))
        self.report.update(idle_after=self.idle(),model_accounting_after=self.models())
        require(self.report['idle_before']==self.report['idle_after']
            and self.report['model_accounting_before']==self.report['model_accounting_after'],'CONFLICT')
        self.report.update(status='PASS',automatic_write_retries=0,application_occurrences_submitted=0)
        self.save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','output','private-material'):p.add_argument('--'+name,required=True)
    a=p.parse_args();q=Qualification(Operator(a.kubeconfig,a.context,a.namespace),a.output,a.private_material)
    try:q.run()
    except Exception as error:
        q.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1024:]));raise
    finally:q.save()
if __name__=='__main__':main()
