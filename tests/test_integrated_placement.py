"""Real Helm renderer over synthetic artifact/config metadata; no deployment."""
import copy,json,unittest
from pathlib import Path
from fusion.contracts import ContractError
from integration.single_node import placement as p
from integration.single_node.integrated_values import generate

ROOT=Path(__file__).resolve().parents[1]
class Placement(unittest.TestCase):
    def setUp(self):
        self.images=dict(source_export_verification='PASS',source_manifest_sha256='a'*64,
            images=[dict(kind=k,repository='synthetic-'+k,local_tag='synthetic-'+k+':fixture',manifest_digest='sha256:'+str(i)*64) for i,k in enumerate(('base','caller','embedding'),1)])
        self.chart=ROOT/'deploy/helm/omega-fusion';self.namespace='omega-ref-plan-fixture'
        self.values=generate(self.images,'synthetic-placement',registry=True,archive=True,history='compact')
    def test_compile_unchanged_values_real_graph_and_no_cross_owner_mounts(self):
        plan=p.freeze(self.chart,self.namespace,self.values,self.images)
        compiled=p.compile(plan,self.chart);self.assertEqual(compiled['values'],self.values)
        self.assertFalse(compiled['business_admission']);self.assertEqual(len(plan['graph']['nodes']),12)
        edges={(e['caller'],e['provider']) for e in plan['graph']['edges']}
        self.assertIn(('fusion-search','fusion-storage'),edges);self.assertIn(('fusion-storage','fusion-storage'),edges)
        self.assertNotIn(('fusion-search','fusion-embedding'),edges)
        self.assertIn('fusion_storage_state',p.diagram(plan))
    def test_modified_graph_missing_provider_foreign_mount_and_unsafe_image_refuse(self):
        plan=p.freeze(self.chart,self.namespace,self.values,self.images)
        changed=copy.deepcopy(plan);changed['graph']['nodes']['fusion-storage']['owner_pvc']='state-fusion-search-0'
        with self.assertRaisesRegex(ContractError,'CONFLICT'):p.compile(changed,self.chart)
        objects=p.render(self.chart,self.namespace,self.values)
        sts=next(x for x in objects if x['kind']=='StatefulSet' and x['metadata']['name']=='fusion-storage')
        sts['spec']['template']['spec']['volumes'].append(dict(name='foreign',persistentVolumeClaim={'claimName':'state-fusion-search-0'}))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.graph(objects,self.namespace,self.images)
        values=copy.deepcopy(self.values);values['components']['omega-agent']['image']['digest']='sha256:'+'f'*64
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.freeze(self.chart,self.namespace,values,self.images)
    def test_live_binding_wrong_model_and_profile_drift_refuse_offline(self):
        values=copy.deepcopy(self.values);values['preview']['model_boundary']='LIVE'
        with self.assertRaises(ContractError):p.freeze(self.chart,self.namespace,values,self.images)
        values=copy.deepcopy(self.values);values['preview']['sustained']['model_binding']={'profile':'omega-preview-model-binding/1','kind':'approved-pinned-ollama','manifest':'/config/live-plan.json','approval':'/approvals/approval.json','runtime_lock':{'path':'/opt/generative/runtime.json','sha256':'a'*64}}
        with self.assertRaises(ContractError):p.freeze(self.chart,self.namespace,values,self.images)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.freeze(self.chart,'omega-demo',self.values,self.images)
    def test_exact_isolated_native_chain_edge_is_not_labelled_https(self):
        images=copy.deepcopy(self.images)
        images['images'].append(dict(kind='chain',repository='synthetic-chain',local_tag='synthetic-chain:fixture',manifest_digest='sha256:'+'4'*64))
        values=generate(images,'synthetic-chain-placement',chain=True,envelopes=True,chain_continuation=True)
        plan=p.freeze(self.chart,self.namespace,values,images)
        edge=next(e for e in plan['graph']['edges'] if e['provider']=='f1r3node')
        self.assertEqual(edge,dict(caller='fusion-commitment',provider='f1r3node',transport='isolated-native-http',owner_files=False))
        objects=p.render(self.chart,self.namespace,values)
        policy=next(o for o in objects if o['kind']=='NetworkPolicy' and o['metadata']['name']=='fusion-commitment-ports')
        policy['spec']['egress'][-1]['ports'][0]['port']=40404
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):p.graph(objects,self.namespace,images)
        values['preview']['chain']['nodeEnabled']=True
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):p.freeze(self.chart,self.namespace,values,images)

if __name__=='__main__':unittest.main()
