"""The new binding callback is a declared service edge, never public egress."""
import json,subprocess,tempfile,unittest
from pathlib import Path
import yaml
from integration.single_node.sustained_values import generate
from tests.test_phase2_operator_values import image_manifest_fixture

class AllocatedTaskNetwork(unittest.TestCase):
 def test_messaging_can_only_reach_selected_session_binding_owners(self):
  root=Path(__file__).resolve().parents[1];value=generate(image_manifest_fixture(),'synthetic-network-sustained')
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'values.json';p.write_text(json.dumps(value));raw=subprocess.check_output(['helm','template','omega',str(root/'deploy/helm/omega-fusion'),'-f',str(p),'--namespace','omega-ref-network'],text=True)
  policies={x['metadata']['name']:x['spec'] for x in yaml.safe_load_all(raw) if x and x['kind']=='NetworkPolicy'}
  edges=policies['fusion-messaging-ports']['egress'];targets={t.get('podSelector',{}).get('matchLabels',{}).get('app.kubernetes.io/name') for edge in edges for t in edge['to']}
  self.assertEqual(targets,{None,'fusion-storage','omega-agent','omega-agent-b'})
  for role in ('omega-agent','omega-agent-b'):
   origins={t['podSelector']['matchLabels']['app.kubernetes.io/name'] for edge in policies[role+'-ports']['ingress'] for t in edge['from']}
   self.assertIn('fusion-messaging',origins)
  self.assertNotIn('ipBlock',raw)

 def test_minimal_sustained_chart_without_tasks_has_no_callback_edge(self):
  root=Path(__file__).resolve().parents[1];value=generate(image_manifest_fixture(),'synthetic-network-minimal',mode='minimal')
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'values.json';p.write_text(json.dumps(value));raw=subprocess.check_output(['helm','template','omega',str(root/'deploy/helm/omega-fusion'),'-f',str(p),'--namespace','omega-ref-network'],text=True)
  policies={x['metadata']['name']:x['spec'] for x in yaml.safe_load_all(raw) if x and x['kind']=='NetworkPolicy'}
  targets={t.get('podSelector',{}).get('matchLabels',{}).get('app.kubernetes.io/name') for edge in policies['fusion-messaging-ports']['egress'] for t in edge['to']}
  self.assertEqual(targets,{None,'fusion-storage'})
