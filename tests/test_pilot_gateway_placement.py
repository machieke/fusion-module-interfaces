"""Actual rendered gateway graph and negative ownership/credential mutations."""
import copy
import unittest
from fusion.contracts import ContractError
from integration.single_node import placement
from tests.test_pilot_workbench_chart import Chart,ROOT
from tests.test_phase2_operator_values import image_manifest_fixture


class GatewayPlacement(unittest.TestCase):
    def setUp(self):
        self.chart=ROOT/'deploy/helm/omega-fusion';self.namespace='omega-ref-pilot-chart'
        self.values=Chart().overlay();self.images=image_manifest_fixture()
    def test_gateway_has_no_owner_and_only_explicit_https_egress(self):
        plan=placement.freeze(self.chart,self.namespace,self.values,self.images)
        node=plan['graph']['nodes']['omega-workbench']
        self.assertIsNone(node['owner_pvc']);self.assertEqual(node['workload_kind'],'Deployment')
        edges=[e for e in plan['graph']['edges'] if e['caller']=='omega-workbench']
        self.assertEqual({e['provider'] for e in edges},{'omega-agent','omega-agent-b','fusion-search'})
        self.assertTrue(all(e['transport']=='authenticated-https' for e in edges))
        self.assertNotIn('omega_workbench_state',placement.diagram(plan))
        self.assertEqual(placement.compile(plan,self.chart)['values'],self.values)
    def test_foreign_mount_provider_secret_and_unknown_deployment_refuse(self):
        original=placement.render(self.chart,self.namespace,self.values)
        for kind in ('pvc','credential','name'):
            objects=copy.deepcopy(original);pod=next(o for o in objects if o['kind']=='Deployment')
            if kind=='pvc':pod['spec']['template']['spec']['volumes'].append(dict(name='foreign',persistentVolumeClaim=dict(claimName='state-omega-agent-0')))
            elif kind=='credential':next(v for v in pod['spec']['template']['spec']['volumes'] if 'secret' in v)['secret']['items'].append(dict(key='operator-token',path='operator-token'))
            else:pod['metadata']['name']='another-service'
            with self.assertRaises(ContractError):placement.graph(objects,self.namespace,self.images)

if __name__=='__main__':unittest.main()
