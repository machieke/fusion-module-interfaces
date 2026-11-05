"""Operator NetworkPolicy fixtures; no deployed or native result claims."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError
from examples.pilot_network_edges import blocked_spec,EdgeFault

def spec(source='fusion-inspect-go',target='fusion-messaging'):
    def edge(name):return dict(to=[dict(podSelector=dict(matchLabels={'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':name}))],ports=[dict(protocol='TCP',port=40403 if name=='f1r3node' else 8443)])
    return dict(podSelector=dict(matchLabels={'app.kubernetes.io/instance':'omega','app.kubernetes.io/name':source}),policyTypes=['Ingress','Egress'],ingress=[],egress=[dict(to=[dict(namespaceSelector={})],ports=[dict(protocol='UDP',port=53)]),edge('fusion-storage'),edge(target)])

class EdgeFixtures(unittest.TestCase):
    def test_only_selected_edge_removed_source_unchanged(self):
        for source,target in [('fusion-inspect-go','fusion-messaging'),('fusion-commitment','f1r3node')]:
            with self.subTest(source=source):
                original=spec(source,target);before=copy.deepcopy(original)
                blocked=blocked_spec(original,source,target)
                self.assertEqual(original,before);self.assertEqual(blocked['egress'],before['egress'][:-1])
                self.assertEqual(blocked['ingress'],before['ingress'])
    def test_arbitrary_duplicate_or_missing_edges_refused(self):
        with self.assertRaises(ContractError):blocked_spec(spec(),'omega-agent','fusion-storage')
        for mode in ('duplicate','missing','missing-storage'):
            with self.subTest(mode=mode):
                value=spec()
                if mode=='duplicate':value['egress'].append(value['egress'][-1])
                elif mode=='missing':value['egress'].pop()
                else:value['egress'].pop(1)
                with self.assertRaises(ContractError):blocked_spec(value,'fusion-inspect-go','fusion-messaging')
    def test_exact_cas_restore_and_foreign_edit_refusal(self):
        class Operator:
            namespace='omega-ref-fixture'
            def owned(self):pass
            def k(self,*args,**kw):
                if args[0]=='get':return json.dumps(self.value)
                incoming=json.loads(kw['data']);assert incoming['metadata']['resourceVersion']==self.value['metadata']['resourceVersion']
                incoming['metadata']['resourceVersion']=str(int(incoming['metadata']['resourceVersion'])+1);self.value=incoming;return ''
        op=Operator();value=spec();op.value=dict(spec=value,metadata=dict(namespace=op.namespace,uid='fixture',resourceVersion='1',annotations={'meta.helm.sh/release-name':'omega'}))
        with tempfile.TemporaryDirectory() as d,patch('examples.pilot_network_edges.compile',return_value=dict(objects=[dict(kind='NetworkPolicy',metadata=dict(name='fusion-inspect-go-ports'),spec=value)])):
            fault=EdgeFault(op,dict(namespace=op.namespace,scope='synthetic-fixture'),'fixture-chart','fusion-inspect-go','fusion-messaging',Path(d)/'fault')
            fault.block();self.assertEqual(op.value['spec'],fault.blocked);fault.restore();self.assertEqual(op.value['spec'],value)
            fault.block();op.value['spec']['ingress']=[{'foreign':True}]
            with self.assertRaises(ContractError):fault.restore()
            self.assertEqual(op.value['spec']['ingress'],[{'foreign':True}])

if __name__=='__main__':unittest.main()
