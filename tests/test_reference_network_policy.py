import json,subprocess,unittest
from pathlib import Path
import yaml
class NetworkPolicy(unittest.TestCase):
 def test_irc_health_and_tcp_are_explicit_and_no_public_egress(self):
  root=Path(__file__).resolve().parents[1]
  text=subprocess.check_output(['helm','template','omega',str(root/'deploy/helm/omega-fusion'),'-f',str(root/'deploy/single-node/workflow-values.yaml'),'--set','networkPolicy.enabled=true','--namespace','omega-ref-policy'],text=True)
  policies={x['metadata']['name']:x for x in yaml.safe_load_all(text) if x and x['kind']=='NetworkPolicy'}
  self.assertEqual(policies['reference-default-deny']['spec']['podSelector'],{})
  for role in ('fusion-channel-bridge','irc-peer'):
   edges=policies[role+'-ports']['spec']['egress']
   ports={p['port'] for e in edges if any(t.get('podSelector',{}).get('matchLabels',{}).get('app.kubernetes.io/name')=='irc-server' for t in e['to']) for p in e['ports']}
   self.assertEqual(ports,{8443,6667})
  self.assertNotIn('ipBlock',json.dumps(policies))
if __name__=='__main__':unittest.main()
