"""Real Helm render, synthetic values. No cluster/provider/admission claims."""
import copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import yaml
from fusion.registry import selection_token
from fusion.reference_inspect_contracts import descriptor
from integration.single_node.pilot_go_values import initial

ROOT=Path(__file__).resolve().parents[1]
CHART=ROOT/'deploy/helm/omega-fusion'
BLOCK='''  {{- if and (hasKey $.Values.preview "pilot") $.Values.preview.pilot.capacity }}
  {{- $_ := set $principals "capacity-operator" (dict "credential_file" "/secrets/inspect-capacity-token" "scopes" (dict $.Values.preview.scope (list "execution.capacity"))) }}
  {{- end }}
'''
class CapacityComposition(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        images=dict(source_manifest_sha256='a'*64,source_export_verification='PASS',images=[dict(kind=k,repository='fixture/'+k,
            local_tag='fixture/'+k+':fixture',manifest_digest='sha256:'+str(i)*64) for i,k in enumerate(('base','caller','embedding'),1)])
        checked=dict(repository='fixture/go',manifest='sha256:'+'d'*64,configuration='sha256:'+'e'*64,
            source_manifest_sha256='f'*64,contract=selection_token(descriptor()),source_package='kit/manifest.json',manifest_sha256='1'*64)
        with patch('integration.single_node.pilot_go_values.verify',return_value=checked):
            self.values,_=initial(images,'fixture-only','synthetic-capacity-chart','omega-ref-pilot-capacity-chart')
        self.helm='/snap/helm/current/helm' if Path('/snap/helm/current/helm').is_file() else 'helm'
    def render(self,chart,values):
        path=self.root/'values.json';path.write_text(json.dumps(values))
        result=subprocess.run([self.helm,'template','omega',str(chart),'--namespace','omega-ref-pilot-capacity-chart','-f',str(path)],capture_output=True,check=True,timeout=20)
        return result.stdout
    def policy(self,values):
        objs=list(yaml.safe_load_all(self.render(CHART,values)))
        cfg=next(x for x in objs if x and x['kind']=='ConfigMap' and x['metadata']['name']=='fusion-inspect-go')
        return json.loads(cfg['data']['policy.json'])
    def test_opt_in_capacity_is_exact_scope_separate_principal(self):
        enabled=self.policy(self.values)
        self.assertEqual(enabled['principals']['capacity-operator'],dict(credential_file='/secrets/inspect-capacity-token',scopes={'synthetic-capacity-chart':['execution.capacity']}))
        disabled=copy.deepcopy(self.values);disabled['preview'].pop('pilot')
        original=self.policy(disabled);without=copy.deepcopy(enabled);without['principals'].pop('capacity-operator')
        self.assertEqual(without,original)
        self.assertTrue(all('execution.capacity' not in permissions for p in original['principals'].values() for permissions in p['scopes'].values()))
    def test_go_disabled_or_absent_manifest_bytes_unchanged(self):
        old=self.root/'historical-chart';shutil.copytree(CHART,old);source=old/'templates/components.yaml'
        raw=source.read_text();self.assertEqual(raw.count(BLOCK),1);source.write_text(raw.replace(BLOCK,''))
        for present in (True,False):
            with self.subTest(go_component_present=present):
                values=copy.deepcopy(self.values)
                if present:values['components']['fusion-inspect-go']['enabled']=False
                else:values['components'].pop('fusion-inspect-go')
                self.assertEqual(self.render(old,values),self.render(CHART,values))
    def test_opt_out_go_manifest_bytes_unchanged(self):
        old=self.root/'historical-chart';shutil.copytree(CHART,old);source=old/'templates/components.yaml'
        raw=source.read_text();self.assertEqual(raw.count(BLOCK),1);source.write_text(raw.replace(BLOCK,''))
        values=copy.deepcopy(self.values);values['preview'].pop('pilot')
        self.assertEqual(self.render(old,values),self.render(CHART,values))

if __name__=='__main__':unittest.main()
