"""Render the delivery artifact: owner isolation, rollout and inert probes."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('helm'),'Helm is required for chart rendering')
class Chart(unittest.TestCase):
    def render(self,*args):
        return subprocess.run(['helm','template','omega',str(ROOT/'deploy/helm/omega-fusion'),
            '--namespace','isolated',*args],capture_output=True,text=True)

    def test_four_separate_pvcs_no_host_mounts_and_no_inline_secrets(self):
        text=self.render().stdout
        self.assertEqual(text.count('kind: StatefulSet'),4)
        self.assertEqual(text.count('replicas: 1'),4)
        self.assertEqual(text.count('volumeClaimTemplates:'),4)
        self.assertEqual(text.count('persistentVolumeClaimRetentionPolicy: {whenDeleted: Retain, whenScaled: Retain}'),4)
        self.assertEqual(text.count('readOnlyRootFilesystem: true'),4)
        self.assertEqual(text.count('automountServiceAccountToken: false'),4)
        self.assertEqual(text.count('updateStrategy: {type: RollingUpdate}'),4)
        self.assertEqual(text.count('path: /health/'),12)
        for word in ('hostPath:','nodePort:','type: LoadBalancer','kind: Secret','credential','127.0.0.1','/home/'):
            self.assertNotIn(word,text)
        for name in ('omega-agent','fusion-execution','fusion-storage','fusion-messaging'):
            self.assertIn('secretName: '+name+'-tls-auth',text)

    def test_configuration_changes_only_selected_rollout_checksum(self):
        def sums(text):return [s.strip() for s in text.splitlines() if 'checksum/config:' in s]
        first=sums(self.render().stdout)
        changed=sums(self.render('--set','components.omega-agent.config.revision=changed').stdout)
        self.assertEqual(len(first),4);self.assertEqual(sum(a!=b for a,b in zip(first,changed)),1)

    def test_schema_rejects_replica_changes_inline_secrets_and_unknown_components(self):
        for override in ['components.fusion-storage.replicas=2','components.omega-agent.credential=secret',
                         'components.another.config.capacity=1','components.omega-agent.config.test.pause_at=unknown']:
            result=self.render('--set',override)
            self.assertNotEqual(result.returncode,0,override)


if __name__=='__main__':unittest.main()
