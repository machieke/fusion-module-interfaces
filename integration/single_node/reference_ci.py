"""Safe lanes: fast fixtures by default; native/cluster require explicit assets.

No lane starts or contacts a generative runtime. Missing prerequisites fail with
an explicit result; a real gate is never replaced by a fixture.
"""
import argparse,json,os,subprocess,sys
from pathlib import Path
from fusion.contracts import require
FAST=('tests.test_reference_boundaries','tests.test_m5_boundaries','tests.test_cognitive_services','tests.test_reference_chain_services','tests.test_reference_restore','tests.test_reference_ownership','tests.test_reference_diagnostics','tests.test_reference_live','tests.test_reference_schema','tests.test_model_channel_services')
def main():
 p=argparse.ArgumentParser();p.add_argument('lane',choices=('fast','chart','native','cluster','chain','artifacts'));p.add_argument('--output',default='artifacts/reference-ci');a,remaining=p.parse_known_args();a.arguments=remaining[1:] if remaining[:1]==['--'] else remaining;out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
 # deny_live has no backend side effects. Its sentinel contract test is always
 # in fast. Native uses the stronger namespace/mount-denied preparation guard.
 denial=subprocess.run([sys.executable,'-c',"from integration.single_node.recorded_model import deny_live;print(deny_live('recorded'))"],capture_output=True,text=True)
 require(denial.returncode==0,'UNAUTHORIZED');(out/'denial.log').write_text(denial.stdout+denial.stderr)
 if a.lane=='fast':command=[sys.executable,'-m','unittest','-v',*FAST]
 elif a.lane=='chart':command=[sys.executable,'-m','unittest','-v','tests.test_single_node_chart','tests.test_reference_network_policy','tests.test_reference_schema']
 elif a.lane=='native':
  require('FUSION_NATIVE_TEST_COMMAND' in os.environ,'NOT_AVAILABLE')
  requested=json.loads(os.environ['FUSION_NATIVE_TEST_COMMAND']);require(type(requested) is list and requested,'INVALID_ARGUMENT')
  command=[sys.executable,'-m','integration.neoclaw.preparation_guard','--guard-evidence',str(out/'native-denial.json'),'--',*requested]
 else:
  require(a.arguments,'INVALID_ARGUMENT')
  # Required later entrypoints run only on the operator-selected trusted host.
  # No workflow event or CI default can supply cluster authority implicitly.
  module={'cluster':'integration.single_node.reference_qualification','chain':'integration.single_node.test_chain_cluster','artifacts':'integration.single_node.reference_artifacts'}[a.lane]
  command=[sys.executable,'-m',module,*a.arguments]
 with (out/(a.lane+'.log')).open('w') as log:result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
 (out/(a.lane+'.json')).write_text(json.dumps(dict(lane=a.lane,returncode=result.returncode,classification='fixture contracts' if a.lane=='fast' else 'explicit lane; inspect individual real/fixture gates',additional_live_generations=0))+'\n')
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
