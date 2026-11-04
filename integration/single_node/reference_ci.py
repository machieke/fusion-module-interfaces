"""Safe lanes: fast fixtures by default; native/cluster require explicit assets.

No lane starts or contacts a generative runtime. Missing prerequisites fail with
an explicit result; a real gate is never replaced by a fixture.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
from fusion.contracts import require
FAST=('tests.test_reference_boundaries','tests.test_m5_boundaries','tests.test_cognitive_services','tests.test_reference_chain_services','tests.test_reference_restore','tests.test_reference_ownership','tests.test_reference_diagnostics','tests.test_reference_live','tests.test_reference_schema','tests.test_model_channel_services')
INTEGRATED=('tests.test_reference_live','tests.test_integrated_capacity',
 'tests.test_integrated_chain_continuation','tests.test_integrated_composition',
 'tests.test_integrated_continuation','tests.test_integrated_continuation_startup','tests.test_integrated_distribution',
 'tests.test_integrated_envelope','tests.test_integrated_history',
 'tests.test_integrated_hydration','tests.test_integrated_journal_integrity',
 'tests.test_integrated_layers','tests.test_integrated_nal_envelope',
 'tests.test_integrated_model_startup','tests.test_integrated_test_barrier',
 'tests.test_integrated_measurements',
 'tests.test_integrated_task_registry',
 'tests.test_integrated_permissions','tests.test_integrated_placement',
 'tests.test_integrated_pool','tests.test_integrated_preparation',
 'tests.test_integrated_registry','tests.test_integrated_registry_configuration',
 'tests.test_integrated_restore_observation','tests.test_integrated_search_repair',
 'tests.test_integrated_search_config','tests.test_integrated_workbench',
 'tests.test_integrated_worker_controls','tests.test_integrated_workers',
 'tests.test_integrated_archive_config','tests.test_integrated_archive_restore',
 'sdk.test_image_inventory','sdk.test_preview_distribution')
def main():
 p=argparse.ArgumentParser();p.add_argument('lane',choices=('fast','chart','native','cluster','chain','artifacts','preview-fast','preview-native','preview-cluster','sustained-fast','integrated-fast','integrated-native','integrated-cluster','integrated-chain'));p.add_argument('--output',default='artifacts/reference-ci');a,remaining=p.parse_known_args();a.arguments=remaining[1:] if remaining[:1]==['--'] else remaining;out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 # deny_live has no backend side effects. Its sentinel contract test is always
 # in fast. Native uses the stronger namespace/mount-denied preparation guard.
 denial=subprocess.run([sys.executable,'-c',"from integration.single_node.recorded_model import deny_live;print(deny_live('recorded'))"],capture_output=True,text=True)
 require(denial.returncode==0,'UNAUTHORIZED');(out/'denial.log').write_text(denial.stdout+denial.stderr)
 if a.lane=='integrated-fast':command=[sys.executable,'-m','unittest','-v',*INTEGRATED]
 elif a.lane=='integrated-native':command=[sys.executable,'-m','integration.neoclaw.preparation_guard','--guard-evidence',str(out/'native-denial.json'),'--',sys.executable,'-m','unittest','-v','integration.neoclaw.test_integrated_nal','integration.neoclaw.test_integrated_worker','integration.neoclaw.test_integrated_provider']
 elif a.lane=='sustained-fast':command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_phase3_*.py','-v']
 elif a.lane=='preview-fast':command=[sys.executable,'-m','unittest','discover','-s','tests','-p','test_phase2_*.py','-v']
 elif a.lane=='preview-native':command=[sys.executable,'-m','integration.neoclaw.preparation_guard','--guard-evidence',str(out/'native-denial.json'),'--',sys.executable,'-m','unittest','-v','integration.neoclaw.test_preview_context','integration.neoclaw.test_preview_session']
 elif a.lane=='fast':command=[sys.executable,'-m','unittest','-v',*FAST]
 elif a.lane=='chart':command=[sys.executable,'-m','unittest','-v','tests.test_single_node_chart','tests.test_reference_network_policy','tests.test_reference_schema']
 elif a.lane=='native':
  require('FUSION_NATIVE_TEST_COMMAND' in os.environ,'NOT_AVAILABLE')
  requested=json.loads(os.environ['FUSION_NATIVE_TEST_COMMAND']);require(type(requested) is list and requested,'INVALID_ARGUMENT')
  command=[sys.executable,'-m','integration.neoclaw.preparation_guard','--guard-evidence',str(out/'native-denial.json'),'--',*requested]
 else:
  require(a.arguments,'INVALID_ARGUMENT')
  # Required later entrypoints run only on the operator-selected trusted host.
  # No workflow event or CI default can supply cluster authority implicitly.
  module={'cluster':'integration.single_node.reference_qualification','preview-cluster':'integration.single_node.preview_qualification','chain':'integration.single_node.test_chain_cluster','artifacts':'integration.single_node.reference_artifacts','integrated-cluster':'examples.integrated_sustained','integrated-chain':'examples.integrated_chain_continuation'}[a.lane]
  command=[sys.executable,'-m',module,*a.arguments]
 with (out/(a.lane+'.log')).open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 (out/(a.lane+'.json')).write_text(json.dumps(dict(lane=a.lane,returncode=result.returncode,classification='fixture contracts' if a.lane=='fast' else 'explicit lane; inspect individual real/fixture gates',additional_live_generations=0))+'\n')
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
