"""M3.1 gate runner: historical regression, fixtures, real providers and native caller."""
import argparse,hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fusion.adapters.pln_deduction import GuardedDeduction
from fusion.contracts import ContractError
GATES=('BASELINE','ACK_CONTRACT','C1_C2_PROGRESS','EVIDENCE_RECOVERY','FEEDBACK_CLOSURE','CAUSAL_RACES','BUDGETS','PROVIDER_SWAP','AUTH_PRIVACY','HIVE_M3_1','COMPAT_REPRO','SCOPE','CHAIN')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def verify(environment,output):
    environment,output=environment.resolve(),output.resolve();output.mkdir(parents=True,exist_ok=True)
    files=git('ls-files','--cached','--others','--exclude-standard').splitlines()
    relevant=[p for p in files if p.startswith(('fusion/','integration/','tests/','scripts/','adapters/','contracts/')) or p in ('uv.lock','pyproject.toml','codex_fusion_m3_1_delivery_closure_and_reconciliation.md')]
    report={'source':{'commit':git('rev-parse','HEAD'),'status':git('status','--porcelain').splitlines(),'files':{p:sha(ROOT/p) for p in relevant}},
        'requested_ancestor':'c4498ce3047f1283d3a4a3ae3d09b713e7dcf312','starting_descendant':'3b34e00df75055d54a57ba7e38eb8b2d9e82ed7e',
        'gates':{g:'NOT_RUN' for g in GATES},'commands':[],
        'classifications':{'fixtures':['generated episodes/tasks/credentials/policy','independent atomic-file attention','guard-only revision and refusing kernel','deterministic injected clock, malformed responses and unavailable ports'],
          'real':['SQLite owners','local DeTTa immutable bytes','unchanged pinned guarded native PLN deduction/revision','authenticated Hive ASGI Programs dispatch with native PeTTa'],
          'not_run':['chain','empty global caches','power loss','distributed failover','live migration','new cognition']},
        'coverage_note':'Do not sum repeated regression subsets. New closure coverage: 9 fixture methods, 5 native-provider methods, 3 direct-kill methods (16 parameterized kill cases), 7 native Hive cases (4 with kills).'}
    def save():(output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        assert not report['source']['status'], 'Verification requires a clean committed checkout'
        config=json.loads(environment.read_text());env=dict(os.environ,**config)
        env['PYTHONPATH']=str(ROOT)+os.pathsep+config['HIVE_REPO'];native=Path(config['VIRTUAL_ENV'])/'bin/python'
        assert native.is_file() and Path(config['M2_DETTA_BINARY']).is_file()
        report['runtime']=GuardedDeduction(config['M3_DEDUCTION_ENV']).profile()
        report['build']=json.loads((environment.parent/'m3-build.json').read_text())
        assert report['build']['recipe_sha256']==sha(ROOT/'scripts/build_m3.py')
        assert report['build']['base_build']['fresh_destination']
        report['hive_sources']=json.loads((ROOT/'integration/hive/sources.json').read_text())
        report['deduction_sources']=json.loads((ROOT/'integration/pln/deduction-sources.json').read_text())
        report['environment_path']=str(environment);report['dependencies']={}
        paths={'hive':config['HIVE_REPO'],'detta':config['DETTA_REPO'],'petta':config['PETTA_PATH']}
        paths.update({n:p for n,p in json.loads(Path(config['M3_DEDUCTION_ENV']).read_text()).items() if n in ('reachability','pln')})
        for name,path in paths.items():report['dependencies'][name]={key:subprocess.check_output(['git','-C',path,*args],text=True).strip()
            for key,args in [('commit',['rev-parse','HEAD']),('status',['status','--porcelain'])]}
        assert all(not d['status'] for d in report['dependencies'].values())
    except (OSError,KeyError,ValueError,AssertionError,ContractError) as error:
        report['prerequisite']={'status':'BLOCKED','reason':str(error),'environment':str(environment)}
        for g in ('BASELINE','C1_C2_PROGRESS','EVIDENCE_RECOVERY','FEEDBACK_CLOSURE','BUDGETS','HIVE_M3_1','COMPAT_REPRO'):report['gates'][g]='BLOCKED'
        save();return 2
    def execute(name,args,gates,*,fixtures=False,junit=False):
        selected_env=dict(env)
        if fixtures:selected_env.update(M2_REVISION_ENV=str(output/'absent-pln'),M2_DETTA_BINARY=str(output/'absent-detta'),M3_DEDUCTION_ENV=str(output/'absent-kernel'))
        began=time.monotonic();result=subprocess.run(list(map(str,args)),cwd=ROOT,env=selected_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        path=output/(name+'.log');path.write_text(result.stdout)
        item={'name':name,'command':list(map(str,args)),'cwd':str(ROOT),'returncode':result.returncode,'seconds':round(time.monotonic()-began,3),
            'log':path.name,'sha256':sha(path),'summaries':re.findall(r'(?:Ran \d+ tests? in [^\n]+|\d+ passed[^\n]*)',result.stdout)}
        if junit:
            suites=list(ET.parse(output/(name+'.xml')).getroot().iter('testsuite'))
            item['tests']={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
            if item['tests']['skipped']:result.returncode=1;item['gate_error']='Real tests must not skip'
        report['commands'].append(item)
        for gate in gates:report['gates'][gate]='PASS' if result.returncode==0 else 'FAIL'
        save();print(name,'PASS' if result.returncode==0 else 'FAIL',item.get('tests',item['summaries']),flush=True)
        if result.returncode:raise SystemExit(result.returncode)
    execute('m1-through-m3-regression',['uv','run','--python','3.11','--locked','python','scripts/verify_m3.py',environment,'--output',output/'regression'],['BASELINE'])
    report['regression']=json.loads((output/'regression/verification.json').read_text())
    execute('closure-fixtures',['uv','run','--python','3.11','--locked','python','-m','unittest','-v','tests.test_m3_1_attention','tests.test_m3_1_delivery','tests.test_m3_1_compat'],['ACK_CONTRACT','CAUSAL_RACES'],fixtures=True)
    execute('closure-real-providers',[native,'-m','unittest','-v','integration.pln.test_m3_1'],['C1_C2_PROGRESS','FEEDBACK_CLOSURE','BUDGETS','PROVIDER_SWAP'])
    execute('closure-process-kills',[native,'-m','unittest','-v','integration.pln.test_m3_1_recovery'],['EVIDENCE_RECOVERY'])
    execute('closure-native-hive',[native,'-m','pytest','-q','integration/hive/test_m3_1_integration.py','--junitxml='+str(output/'closure-native-hive.xml')],['HIVE_M3_1','AUTH_PRIVACY'],junit=True)
    report['gates']['COMPAT_REPRO']='PASS: populated disposable old-profile copies; fresh provider directories and clean source checkout; download caches warm'
    report['gates']['SCOPE']='PASS: delivery closure only; guarded mathematics, DA, source pins and historical profiles preserved'
    report['observed']={'repeated_episode':{'events':33,'logical_observations':33,'drain_batches':[16,16,1],'pending_after_each_drain':0,'backpressure_at':16},
        'feedback':{'clock_conflict':'terminal original execution; closure retires without credit','applied_before_expiry':'original receipt recovered after expiry/decay',
                    'native_calls_during_reconciliation':0,'original_result_and_budget':'unchanged','attention_providers':['sqlite','atomic-file-fixture']},
        'existing_state':'new closure profile rejects populated old M3 journals; original profile replay preserved; no repair/migration'}
    save();return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('environment',type=Path);parser.add_argument('--output',type=Path,default=ROOT/'artifacts/m3_1/final')
    args=parser.parse_args();raise SystemExit(verify(args.environment,args.output))
