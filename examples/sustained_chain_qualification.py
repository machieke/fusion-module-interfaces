"""Read back the same Phase 3 workflow using its explicit source profile.

Reuses the existing isolated exact-result/signed-intent qualification. This
operator example belongs to the source artifact; it adds no chain semantics.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_chain_qualification import Qualification as Existing

class Qualification(Existing):
    def run(self,qualification):
        from integration.single_node.chain_address import address
        chain=self.values['preview']['chain'];public=chain['public_key']
        require(len(public)==130 and public.startswith('04') and public!='04'+'0'*128,'NOT_AVAILABLE')
        require(chain['wallet_address']==address(bytes.fromhex(public)),'CONFLICT')
        return super().run(qualification)

    def independent(self,observer):
        from fusion import cognitive_services as cs, lookup_contracts as source
        from fusion.registry import descriptor_wire
        feed=source.SUSTAINED_FEED if self.values['preview']['profile']=='omega-single-node-sustained-preview/1' else source.FEED
        reg=self.report['registration'];scope=reg['approved']['scope_ref'];namespace=self.op.namespace
        trace=dict(reg=reg,saved_intent=self.report['saved_intent'],final_observation=self.report['final_observation'])
        source=Path(observer).read_text()
        config=dict(profile='synthetic-chain-readback/1',node_endpoint='http://f1r3node.'+namespace+'.svc.cluster.local:40403',
            atoms=dict(composition=cs.COMPOSITION,feed_profile=feed,principal='commit-observer',scope=scope,
                endpoint=dict(host='fusion-storage.'+namespace+'.svc.cluster.local',port=8443,path=cs.ROUTE,ca_file='/secrets/ca.crt'),
                credential_file='/secrets/storage-token',descriptor=descriptor_wire(cs.descriptors(feed_profile=feed)[0])))
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

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','output','qualification','observer'):p.add_argument('--'+name,required=True)
    a=p.parse_args();q=Qualification(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.output)
    try:
        q.run(a.qualification)
        q.report['approval_basis']='Assigned Phase 3 R12: exact generated shared artifact inspected in this native workflow; existing historical registration label is retained'
        q.save();q.independent(a.observer)
    except Exception as error:q.report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:q.save()
if __name__=='__main__':main()
