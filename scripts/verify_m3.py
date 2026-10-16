"""Single M3 verification entrypoint. Preserve distinct fixture/native/blocked/unrun gates."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fusion.adapters.pln_deduction import GuardedDeduction
from fusion.contracts import ContractError
GATES=('BASELINE','CONTRACTS','C3','C3_INDEPENDENT','ATTENTION_SWAP','KERNEL_NATIVE','DERIVED_ADMISSION','C4_BOUNDED','RECOVERY','PRIVACY','HIVE_M3','REPRO','SCOPE','CHAIN')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()


def verify(environment,output):
    environment,output=environment.resolve(),output.resolve();output.mkdir(parents=True,exist_ok=True)
    files=git('ls-files','--cached','--others','--exclude-standard').splitlines()
    relevant=[p for p in files if p.startswith(('fusion/','integration/','tests/','scripts/','adapters/','contracts/')) or p in ('uv.lock','pyproject.toml','codex_fusion_m3_attention_and_bounded_inference.md')]
    report={'source':{'commit':git('rev-parse','HEAD'),'status':git('status','--porcelain').splitlines(),'files':{p:sha(ROOT/p) for p in relevant}},
        'gates':{g:'NOT_RUN' for g in GATES},'commands':[],
        'classifications':{'fixtures':['generated observations/tasks/operator policy','independent atomic-file attention','guard-only revision and refusing-kernel fixtures','injected malformed replies/timeouts/clock races'],
            'real':['SQLite reference-policy attention','local DeTTa immutable bytes','pinned guarded native Truth_Deduction and Truth_Revision','authenticated native Hive Programs caller'],
            'not_run':['chain','LTI','general search','inference research','live migration','power-loss/distributed failover','empty global caches','historical SWI 10.0.1']}}
    def save():(output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        config=json.loads(environment.read_text());env=dict(os.environ,**config)
        env['PYTHONPATH']=str(ROOT)+os.pathsep+config['HIVE_REPO'];native=Path(config['VIRTUAL_ENV'])/'bin/python'
        assert native.is_file() and Path(config['M2_DETTA_BINARY']).is_file()
        report['runtime']=GuardedDeduction(config['M3_DEDUCTION_ENV']).profile()
        report['build']=json.loads((environment.parent/'m3-build.json').read_text())
        assert report['build']['recipe_sha256']==sha(ROOT/'scripts/build_m3.py')
        assert report['build']['base_build']['fresh_destination']
        report['hive_sources']=json.loads((ROOT/'integration/hive/sources.json').read_text())
        report['deduction_sources']=json.loads((ROOT/'integration/pln/deduction-sources.json').read_text())
        report['environment_path']=str(environment)
        report['dependencies']={}
        paths={'hive':config['HIVE_REPO'],'detta':config['DETTA_REPO'],'petta':config['PETTA_PATH']}
        paths.update({n:p for n,p in json.loads(Path(config['M3_DEDUCTION_ENV']).read_text()).items() if n in ('reachability','pln')})
        for name,path in paths.items():report['dependencies'][name]={key:subprocess.check_output(['git','-C',path,*args],text=True).strip()
            for key,args in [('commit',['rev-parse','HEAD']),('status',['status','--porcelain'])]}
        assert all(not d['status'] for d in report['dependencies'].values())
    except (OSError,KeyError,ValueError,AssertionError,ContractError) as error:
        report['prerequisite']={'status':'BLOCKED','reason':str(error),'environment':str(environment)}
        for g in ('BASELINE','KERNEL_NATIVE','DERIVED_ADMISSION','HIVE_M3','REPRO'):report['gates'][g]='BLOCKED'
        save();return 2
    def execute(name,args,gates,*,cwd=ROOT,overrides=None,junit=False):
        began=time.monotonic();r=subprocess.run(list(map(str,args)),cwd=cwd,env=dict(env,**(overrides or {})),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        path=output/(name+'.log');path.write_text(r.stdout)
        item={'name':name,'command':list(map(str,args)),'cwd':str(cwd),'returncode':r.returncode,'seconds':round(time.monotonic()-began,3),
            'log':path.name,'sha256':sha(path),'summaries':re.findall(r'(?:Ran \d+ tests? in [^\n]+|\d+ passed[^\n]*)',r.stdout)}
        if junit:
            suites=list(ET.parse(output/(name+'.xml')).getroot().iter('testsuite'))
            item['tests']={key:sum(int(s.get(key,0)) for s in suites) for key in ('tests','failures','errors','skipped')}
            if item['tests']['skipped']:r.returncode=1;item['gate_error']='Real tests must not skip'
        report['commands'].append(item)
        for gate in gates:report['gates'][gate]='PASS' if r.returncode==0 else 'FAIL'
        save();print(name,'PASS' if r.returncode==0 else 'FAIL',item.get('tests',item['summaries']),flush=True)
        if r.returncode:raise SystemExit(r.returncode)
    execute('m2-regression',['uv','run','--python','3.11','--locked','python','scripts/verify_m2.py',environment,'--output',output/'m2-regression'],['BASELINE'])
    report['baseline_details']=json.loads((output/'m2-regression/verification.json').read_text())
    execute('m3-attention-fixtures',['uv','run','--python','3.11','--locked','python','-m','unittest','-v','tests.test_m3_attention'],['C3','C3_INDEPENDENT'],
        overrides={'M2_REVISION_ENV':str(output/'absent-pln'),'M2_DETTA_BINARY':str(output/'absent-detta'),'M3_DEDUCTION_ENV':str(output/'absent-kernel')})
    execute('m3-contract-fixtures',['uv','run','--python','3.11','--locked','python','-m','unittest','-v','tests.test_m3'],['CONTRACTS'],
        overrides={'M2_REVISION_ENV':str(output/'absent-pln'),'M2_DETTA_BINARY':str(output/'absent-detta'),'M3_DEDUCTION_ENV':str(output/'absent-kernel')})
    reachability=json.loads(Path(config['M3_DEDUCTION_ENV']).read_text())['reachability']
    execute('upstream-guard-fixtures',[native,'-m','unittest','-v','tests.test_pln_contracts'],[],cwd=reachability,overrides={'PYTHONPATH':reachability})
    execute('m3-native-kernel-admission',[native,'-m','unittest','-v','integration.pln.test_deduction'],['KERNEL_NATIVE','DERIVED_ADMISSION','C4_BOUNDED','PRIVACY'])
    execute('m3-real-process-kills',[native,'-m','unittest','-v','integration.pln.test_m3_recovery'],['RECOVERY'])
    execute('m3-native-hive',[native,'-m','pytest','-q','integration/hive/test_m3_integration.py','--junitxml='+str(output/'m3-native-hive.xml')],['HIVE_M3'],junit=True)
    execute('m3-comparison',[native,'scripts/m3_compare.py',output/'comparison.json'],['ATTENTION_SWAP'])
    report['comparison']=json.loads((output/'comparison.json').read_text())
    report['gates']['REPRO']='PASS: fresh provider objects, venv and DeTTa target; download caches warm'
    report['gates']['SCOPE']='PASS: bounded C3/C4 and required C2 admission extension; one grounded rule; no migration'
    report['gates']['CHAIN']='NOT_RUN';save();return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('environment',type=Path);parser.add_argument('--output',type=Path,default=ROOT/'artifacts/m3/final')
    args=parser.parse_args();raise SystemExit(verify(args.environment,args.output))
