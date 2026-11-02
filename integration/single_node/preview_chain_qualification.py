"""Commit the actual completed preview workflow through the fixed isolated chain.

Requires the recorded native qualification's inspection, fresh unfunded keys,
and an operator-owned namespace. It neither invokes an agent tool nor generates
an artifact. No generative runtime, private state export or new chain operation.
"""
import argparse,json,time,uuid
from pathlib import Path
import yaml
from fusion.contracts import canonical,digest,require
from fusion.adapters.f1r3_m4 import DESCRIPTOR,PROFILE
from fusion.registry import selection_token
from .reference_ops import Operator,PYTHON


class Qualification:
    def __init__(self,op,values,chart,output):
        self.op,self.values_path,self.chart=op,Path(values),Path(chart)
        self.values=yaml.safe_load(self.values_path.read_text())
        self.root=Path(output);self.root.mkdir(parents=True,exist_ok=False)
        self.report=dict(namespace=op.namespace,additional_live_generations=0,
            classification='REAL_ISOLATED_CHAIN_FROM_RECORDED_MODEL_REAL_NATIVE_WORKFLOW',observations=[])
    def save(self): (self.root/'report.json').write_bytes(canonical(self.report))
    def code(self,role,source,timeout=45):
        return self.op.k('exec','-i',role+'-0','--',PYTHON,'-',data=source,timeout=timeout)
    def read(self,role,name):
        return json.loads(self.code(role,"import json;from pathlib import Path;p=Path('/state')/"+repr(name)+";print(p.read_text() if p.exists() else 'null')"))
    def pods(self):
        return {p['metadata']['name']:dict(uid=p['metadata']['uid'],images=[c['imageID'] for c in p.get('status',{}).get('containerStatuses',[])])
            for p in json.loads(self.op.k('get','pods','-l','app.kubernetes.io/instance=omega','-o','json'))['items']}
    def upgrade(self):
        self.values_path.write_text(yaml.safe_dump(self.values,sort_keys=False))
        out=self.op.command(['helm','upgrade',self.op.release,str(self.chart),'--kubeconfig',self.op.kubeconfig,
            '--kube-context',self.op.context,'--namespace',self.op.namespace,'-f',str(self.values_path),'--wait','--timeout','180s'],timeout=190)
        (self.root/('upgrade-'+str(time.time_ns())+'.log')).write_text(out)
    def wait(self,fn,seconds):
        end=time.monotonic()+seconds;last=None
        while time.monotonic()<end:
            try:
                value=fn()
                if value:return value
            except (RuntimeError,ValueError) as error:last=type(error).__name__
            time.sleep(1)
        raise RuntimeError('BOUNDED_OBSERVER_EXPIRED '+str(last))
    def isolation(self):
        require(not self.values['preview']['chain']['nodeEnabled'],'UNAUTHORIZED')
        process=self.read('f1r3node','process.json')
        require(process['activated'] is False and process['native_pid'] is None,'UNAUTHORIZED')
        source="import socket,time;from pathlib import Path;ss=[]\nfor port in (40401,40402,40403,40404,40405):\n s=socket.socket();s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);s.bind(('0.0.0.0',port));s.listen();ss.append(s)\nPath('/run/fusion/sentinel-ready').write_text('ready');time.sleep(40)"
        self.code('f1r3node',"import subprocess,sys;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c',"+repr(source)+"],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True);Path('/run/fusion/sentinel.pid').write_text(str(p.pid))")
        self.wait(lambda:self.code('f1r3node',"from pathlib import Path;print(Path('/run/fusion/sentinel-ready').exists())").strip()=='True',5)
        def probe(role,host,port):
            return json.loads(self.code(role,"import socket,time,json;s=socket.socket();s.settimeout(1);t=time.monotonic();v=s.connect_ex(("+repr(host)+","+str(port)+"));s.close();print(json.dumps(dict(errno=v,seconds=time.monotonic()-t)))"))
        ip=self.op.k('get','pod','f1r3node-0','-o','jsonpath={.status.podIP}')
        try:
            allowed=probe('fusion-commitment',ip,40403)
            denied={str(p):probe('fusion-commitment',ip,p) for p in (40401,40402,40404,40405)}
            denied['agent-http']=probe('omega-agent',ip,40403);denied['node-external']=probe('f1r3node','192.0.2.1',443)
            self.report['isolation']=dict(allowed=allowed,denied=denied,node_started=False);self.save()
            require(allowed['errno']==0 and all(x['errno']!=0 for x in denied.values()),'UNAUTHORIZED')
        finally:self.code('f1r3node',"import os,signal;from pathlib import Path;os.kill(int(Path('/run/fusion/sentinel.pid').read_text()),signal.SIGTERM)")
    def call(self,operation,body):
        source="""import json,tempfile
from pathlib import Path
from fusion.preview_chain import Client
from fusion.contracts import canonical,ContractError
v=json.loads(Path('/config/component.json').read_text());reg=v['preview']['chain']['registration']
cfg=dict(endpoint=dict(host=v['peers']['fusion-commitment'],port=v['https_port'],ca_file='/secrets/ca.crt'),credential=Path('/secrets/fusion-commitment-token').read_text().strip(),registration=reg)
with tempfile.TemporaryDirectory(dir='/run/fusion') as d:
 p=Path(d)/'client.json';p.write_bytes(canonical(cfg));p.chmod(0o600)
 try:print(json.dumps(dict(value=Client(p).call(OP,BODY))))
 except ContractError as e:print(json.dumps(dict(error=e.code)))
""".replace('OP',repr(operation)).replace('BODY',repr(body))
        return json.loads(self.code('omega-agent',source))
    def observe_final(self,saved):
        # Bounded observations do not authorize a new submit or signed intent.
        for _ in range(20):
            value=self.call('observe',dict(deploy_id=saved['deploy_id']))
            self.report['observations'].append(value);self.save()
            if value.get('value',{}).get('effect_finality')=='finalized':return value['value']
            time.sleep(1)
        raise RuntimeError('CHAIN_OBSERVATION_TIMEOUT')
    def independent(self,observer):
        from fusion import cognitive_services as cs
        from fusion.registry import descriptor_wire
        reg=self.report['registration'];scope=reg['approved']['scope_ref'];namespace=self.op.namespace
        trace=dict(reg=reg,saved_intent=self.report['saved_intent'],final_observation=self.report['final_observation'])
        source=Path(observer).read_text()
        config=dict(profile='synthetic-chain-readback/1',node_endpoint='http://f1r3node.'+namespace+'.svc.cluster.local:40403',
            atoms=dict(composition=cs.COMPOSITION,principal='commit-observer',scope=scope,
                endpoint=dict(host='fusion-storage.'+namespace+'.svc.cluster.local',port=8443,path=cs.ROUTE,ca_file='/secrets/ca.crt'),
                credential_file='/secrets/storage-token',descriptor=descriptor_wire(cs.descriptors()[0])))
        # Copy only read authority. Neither the signing key nor owner PVC is
        # available to this independently scheduled observer process.
        secret=json.loads(self.op.k('get','secret','fusion-commitment-tls-auth','-o','json'))['data']
        name='preview-chain-readback'
        self.op.apply(dict(apiVersion='v1',kind='Secret',metadata=dict(name=name),data={'ca.crt':secret['ca.crt'],'storage-token':secret['commit-storage-token']}))
        self.op.apply(dict(apiVersion='v1',kind='ConfigMap',metadata=dict(name=name),immutable=True,
            data={'observer.py':source,'trace.json':canonical(trace).decode(),'config.json':canonical(config).decode()}))
        image=self.values['components']['fusion-commitment']['image'];image=image['repository']+'@'+image['digest']
        pod=dict(apiVersion='v1',kind='Pod',metadata=dict(name=name,labels={'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':'fusion-commitment'}),
            spec=dict(restartPolicy='Never',automountServiceAccountToken=False,securityContext=dict(runAsNonRoot=True,runAsUser=1000,runAsGroup=1000,fsGroup=1000),
                containers=[dict(name='observer',image=image,imagePullPolicy='Never',command=[PYTHON,'/inputs/observer.py','--trace','/inputs/trace.json','--config','/inputs/config.json'],
                    env=[dict(name='PYTHONPATH',value='/opt/fusion')],resources=dict(requests=dict(cpu='25m',memory='64Mi'),limits=dict(cpu='500m',memory='256Mi')),
                    securityContext=dict(allowPrivilegeEscalation=False,readOnlyRootFilesystem=True,capabilities=dict(drop=['ALL'])),
                    volumeMounts=[dict(name='inputs',mountPath='/inputs',readOnly=True),dict(name='auth',mountPath='/secrets',readOnly=True)])],
                volumes=[dict(name='inputs',configMap=dict(name=name)),dict(name='auth',secret=dict(secretName=name))]))
        try:
            self.op.apply(pod)
            self.wait(lambda:self.op.k('get','pod',name,'-o','jsonpath={.status.phase}') in ('Succeeded','Failed'),60)
            raw=self.op.k('logs',name);(self.root/'independent-reader.json').write_text(raw)
            observed=json.loads(raw);self.report['independent_readback']=observed
            self.report['observer_source_sha256']=digest(source.encode())
            self.report['observer_pod']=json.loads(self.op.k('get','pod',name,'-o','json'))
            require(observed.get('status')=='PASS','NOT_AVAILABLE')
            self.report['status']='PASS';self.save()
        finally:
            for kind in ('pod','secret','configmap'):self.op.k('delete',kind,name,'--ignore-not-found=true','--wait=true')
    def run(self,qualification):
        raw=Path(qualification).read_bytes();native=json.loads(raw)
        require(native['namespace']==self.op.namespace and native.get('status')=='PASS'
            and native.get('inspection',{}).get('caller_acknowledged') is True,'NOT_AVAILABLE')
        directions={x['scenario']:x['passed'] for x in native['scenarios'] if x['scenario'].startswith('two-agent-')}
        require(directions=={'two-agent-A-B':True,'two-agent-B-A':True},'NOT_AVAILABLE')
        inspected=native['inspection'];self.op.owned();self.report.update(native_report_sha256=digest(raw),inspection=inspected,pods_before=self.pods())
        require(self.values['preview']['chain']['registration'] is None,'CONFLICT')
        self.isolation();chain=self.values['preview']['chain'];chain.update(nodeEnabled=True,isolationVerified=True);self.upgrade()
        identity=self.wait(lambda:self.read('f1r3node','chain-identity.json'),90)
        operation='preview-workflow-'+str(uuid.uuid4());scope=self.values['preview']['scope']
        reg=dict(profile='synthetic-workflow-commitment/1',principal='A',artifact=inspected['artifact'],job_id=inspected['job_id'],result=inspected['inspection'],
            approved=dict(scope_ref=scope,result_ref=inspected['inspection']['ref'],commitment_digest=inspected['inspection']['ref']['digest'],approval_record='phase2-generated-exact-result/'+operation),
            binding=dict(profile=PROFILE,selection=selection_token(DESCRIPTOR),chain=identity,signer=chain['public_key'],
                limits=dict(phloPrice=1,phloLimit=10000000,validAfterBlockNumber=0),operation=operation,
                protobuf_sha256='ba9b8ebd44e73cabac064ec00e4f93d9a08a8681bcb3bce3eb5dca6366ba23e6',owner_journal='/state/commitments.sqlite',
                authority=dict(purpose='approved-synthetic-agent-artifact',expires_at_ms=time.time_ns()//1000000+1200000,artifact_digest=inspected['artifact']['digest'])))
        chain['registration']=reg;self.report['registration']=reg
        self.report['approval_basis']='Assigned P13: exact completed generated workflow artifact only; separately registered after native inspection'
        # Lose exactly the first submit reply after the owning commit. The
        # recovery below uses only intent/observe, never automatic resubmission.
        self.values['testFaultsEnabled']=True
        self.values['components']['fusion-commitment'].setdefault('config',{})['test']={'drop_response_operation':'submit'}
        self.upgrade();self.save()
        self.report['submission']=self.call('submit',dict(command=dict(scope_ref=scope,idempotency_key=operation,intent_digest=None)));self.save()
        saved=self.call('intent',{});require(saved.get('value') is not None,'NOT_AVAILABLE');saved=saved['value'];self.report['saved_intent']=saved
        final=self.observe_final(saved);self.report['final_observation']=final
        self.report['response_drop']=self.read('fusion-commitment','response-dropped.json');self.save()
        require(self.report['submission'].get('error')=='NOT_AVAILABLE'
            and self.report['response_drop'] is not None
            and self.report['response_drop'].get('operation')=='submit','NOT_AVAILABLE')
        before=self.pods();self.op.k('delete','pod','omega-agent-0','fusion-commitment-0','f1r3node-0','--grace-period=1','--wait=false')
        for role in ('omega-agent','fusion-commitment','f1r3node'):
            self.wait(lambda: self.pods().get(role+'-0',{}).get('uid') not in (None,before[role+'-0']['uid']),45)
            self.op.k('wait','--for=condition=Ready','pod/'+role+'-0','--timeout=120s',timeout=130)
        restarted_identity=self.wait(lambda:self.read('f1r3node','chain-identity.json'),90)
        require(restarted_identity==identity,'CONFLICT')
        recovered=self.call('intent',{});require(recovered.get('value')==saved,'CONFLICT')
        recovered_final=self.observe_final(saved)
        require(recovered_final['deploy_id']==final['deploy_id'] and recovered_final['inclusion_block']==final['inclusion_block'],'CONFLICT')
        self.report.update(pods_after=self.pods(),recovered_intent=recovered,recovered_final_observation=recovered_final,
            node_identity_unchanged=True,automatic_resubmissions=0,status='CHAIN_FINALIZED_AND_RESTARTED_INDEPENDENT_READBACK_PENDING')
        self.save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','output','qualification','observer'):p.add_argument('--'+name,required=True)
    a=p.parse_args();q=Qualification(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.output)
    try:q.run(a.qualification);q.independent(a.observer)
    except Exception as error:
        q.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[:1024]));raise
    finally:q.save()
if __name__=='__main__':main()
