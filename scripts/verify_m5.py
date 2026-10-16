"""M5 independently selectable gates; historical M4 scope guard stays unchanged."""
import argparse,concurrent.futures,hashlib,json,os,re,shutil,socket,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
GATES=('BASELINE_AND_SCOPE','RELATIONS_CONTRACT','RELATIONS_REAL','COMMITTED_SOURCE','SEARCH_CONTRACT','SEARCH_REAL_REBUILD','SUBSTITUTION','RECOVERY','AUTH_PRIVACY','HIVE_LOOKUP','REPRO_AND_LEDGER','LEGACY_REGRESSION')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def verify(args):
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    selected=set(args.gates.split(','));assert selected<={'fixtures','storage','hive','legacy','all'}
    if 'all' in selected:selected={'fixtures','storage','hive','legacy'}
    relevant=[p for p in git('ls-files','--cached','--others','--exclude-standard').splitlines() if p.startswith(('fusion/','integration/','scripts/','tests/','adapters/','contracts/')) or p in ('uv.lock','pyproject.toml')]
    source={'commit':git('rev-parse','HEAD'),'status':git('status','--porcelain').splitlines(),'files':{p:sha(ROOT/p) for p in relevant}}
    report={'schema':'fusion-m5-gates/1','source':source,'requested_ancestor':'05b1c52cfa6ced6e263700753e82ad6038a3b0dd',
        'gates':{g:'NOT_RUN' for g in GATES},'suites':{},'commands':[],'missing_prerequisites':[], 'executed_failures':[],'observation_timeouts':[],
        'classification':{'real':['SQLite AtomStorage/Relations/Search owner journals','local pinned DeTTa','authenticated native Hive ASGI + PeTTa'],
            'fixtures':['generated corpus and test oracle','independent atomic-file AtomStorage and Search','malformed-source/response/corruption injections','deterministic SIGSTOP failpoints followed by real SIGKILL'],
            'unrun':['power loss','distributed failover','public network','empty global caches','live populated-state migration','new chain workloads','diagnostic code coverage']}}
    def save():(output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    def command(name,argv,env=None,timeout=3600):
        began=time.monotonic();status='FAIL';code=None
        try:
            with open(output/(name+'.log'),'w') as log:
                result=subprocess.run(list(map(str,argv)),cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            code=result.returncode;status='PASS' if code==0 else 'FAIL'
        except subprocess.TimeoutExpired:status='OBSERVATION_TIMEOUT'
        item={'name':name,'argv':[str(v).replace(str(ROOT),'<FUSION>') for v in argv],'returncode':code,'status':status,'seconds':round(time.monotonic()-began,3),'log_sha256':sha(output/(name+'.log'))}
        log=(output/(name+'.log')).read_text();item['summaries']=re.findall(r'(?:Ran \d+ tests? in [^\n]+|\d+ passed[^\n]*)',log)
        junit=output/(name+'.xml')
        if junit.exists():
            cases=[]
            for case in ET.parse(junit).getroot().iter('testcase'):
                failure=next((x for x in case if x.tag in ('error','failure','skipped')),None)
                state='PASS' if failure is None else 'NOT_RUN' if failure.tag=='skipped' else 'OBSERVATION_TIMEOUT' if 'OBSERVATION_TIMEOUT:' in (failure.text or '') else 'FAIL'
                cases.append({'name':case.get('name'),'status':state,'seconds':float(case.get('time'))})
            item['cases']=cases
            if cases:
                status=item['status']=next((state for state in ('FAIL','OBSERVATION_TIMEOUT','NOT_RUN') if any(x['status']==state for x in cases)),status)
            report['observation_timeouts'].extend(x for x in cases if x['status']=='OBSERVATION_TIMEOUT')
        report['commands'].append(item);report['suites'][name]=status
        if status=='FAIL':report['executed_failures'].append({'suite':name,'returncode':code})
        if status=='OBSERVATION_TIMEOUT':report['observation_timeouts'].append({'suite':name})
        save();print(name,status,flush=True);return status
    def blocked(names,reason):
        report['missing_prerequisites'].append({'suites':names,'reason':reason})
        for name in names:report['suites'][name]='BLOCKED'
        save()
    save()
    if source['status'] and not args.development:raise SystemExit('Final M5 verification requires a clean committed source checkout')
    # Historical implementations and numerical/source pins stay byte-identical. Ports may only append.
    changed=git('diff','--name-only','4093301ea6b34bb8de487a4e4d9aae8a9ee6e61d','--','fusion','integration','scripts','tests','adapters','contracts','uv.lock','pyproject.toml').splitlines()
    historical=set(git('ls-tree','-r','--name-only','4093301ea6b34bb8de487a4e4d9aae8a9ee6e61d').splitlines())
    violations=[p for p in changed if p in historical and p!='fusion/ports.py']
    old_ports=subprocess.check_output(['git','show','4093301ea6b34bb8de487a4e4d9aae8a9ee6e61d:fusion/ports.py'])
    if not (ROOT/'fusion/ports.py').read_bytes().startswith(old_ports):violations.append('fusion/ports.py: non-additive change')
    report['scope']={'historical_changes':violations,'historical_m4_guard_unchanged':sha(ROOT/'scripts/verify_m4.py')==hashlib.sha256(subprocess.check_output(['git','show','4093301:scripts/verify_m4.py'])).hexdigest()}
    baseline=json.loads((ROOT/'evidence/m5/baseline/summary.json').read_text())
    report['baseline']=baseline
    report['gates']['BASELINE_AND_SCOPE']='PASS' if not violations and baseline['result']=='PASS' and baseline['source_check'] else 'FAIL'
    if 'fixtures' in selected:
        env=dict(os.environ,M2_DETTA_BINARY='/nonexistent/m5-detta',M2_REVISION_ENV='/nonexistent/m5-pln',M3_DEDUCTION_ENV='/nonexistent/m5-kernel')
        command('fixtures',['uv','run','--python','3.11','--locked','python','-m','unittest','-v','tests.test_m5','tests.test_m5_boundaries'],env)
    config=None;env=None;native=None
    if selected & {'storage','hive','legacy'}:
        try:
            config=json.loads(args.environment.resolve().read_text());native=Path(config['VIRTUAL_ENV'])/'bin/python'
            assert native.is_file() and Path(config['M2_DETTA_BINARY']).is_file(),'Native Python or DeTTa binary missing'
            report['dependencies']={}
            pins=json.loads((ROOT/'integration/hive/sources.json').read_text())['repositories']
            pin_names={'hive':'omegahive','detta':'secured-contract-spaces','petta':'PeTTa'}
            for name,key in [('hive','HIVE_REPO'),('detta','DETTA_REPO'),('petta','PETTA_PATH')]:
                path=config[key];revision=subprocess.check_output(['git','-C',path,'rev-parse','HEAD'],text=True).strip()
                status=subprocess.check_output(['git','-C',path,'status','--porcelain'],text=True).strip();assert not status,name+' source dirty'
                assert revision==pins[pin_names[name]]['commit'],name+' revision mismatch'
                report['dependencies'][name]={'commit':revision,'status':status}
            # Build recipe validates the pinned sources and source hashes; do not accept an unrelated build.
            build=json.loads((args.environment.parent/'m3-build.json').read_text())
            assert build['recipe_sha256']==sha(ROOT/'scripts/build_m3.py') and build['base_build']['fresh_destination']
            report['provider_build']=build;report['detta_binary_sha256']=sha(config['M2_DETTA_BINARY'])
            env=dict(os.environ,**config)
            env.update(PYTHONPATH=str(ROOT)+os.pathsep+config['HIVE_REPO'],FUSION_M5_EVIDENCE=str(output/'traces'))
        except (OSError,KeyError,AssertionError,ValueError,AttributeError,subprocess.CalledProcessError) as error:
            blocked(sorted(selected&{'storage','hive','legacy'}),str(error).replace(str(ROOT),'<FUSION>'))
    if config and env:
        if 'storage' in selected:command('storage',[native,'-m','unittest','-v','integration.test_m5_real'],env)
        if 'hive' in selected:command('hive',[native,'-m','pytest','-q','--tb=short','integration/hive/test_m5_integration.py','--basetemp='+str(output/'private-hive'),'--junitxml='+str(output/'hive.xml')],env)
        if 'legacy' in selected:
            # These are unchanged behavioral suites; do not call or weaken M4's historical scope guard.
            command('legacy-m1-m3_1',['uv','run','--python','3.11','--locked','python','scripts/verify_m3_1.py',args.environment.resolve(),'--output',output/'legacy'],env)
            command('legacy-m4-fixtures',['uv','run','--python','3.11','--locked','python','-m','unittest','-v','tests.test_m4_chain'],env)
            try:
                assert args.chain_build,'--chain-build is required for the real M4 behavioral regression'
                build=args.chain_build.resolve();repo=build/'source';binary=build/'target/debug/node'
                chain_pin=json.loads((ROOT/'integration/chain/sources.json').read_text())
                revision=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
                assert revision=='9ec1096e10774926ea8e72f0823482f0bf9213e1' and binary.is_file(),'Pinned chain build unavailable'
                assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
                assert all(shutil.which(x) for x in ('unshare','ip','ss')),'Isolation utilities missing'
                probe=subprocess.run(['unshare','--user','--map-root-user','--net','sh','-c','ip link set lo up'],capture_output=True)
                assert probe.returncode==0,'Route-free network namespace unavailable'
                chain_output=output/'chain';chain_output.mkdir(exist_ok=True)
                chain_env=dict(env,M4_HOST_NETNS=os.readlink('/proc/self/ns/net'),M4_NODE_SOURCE=str(repo),M4_NODE_BINARY=str(binary),M4_OUTPUT=str(chain_output),M4_SOCKET_CHALLENGE=str(chain_output/'socket-challenge.json'))
                report['chain_reuse']={'commit':revision,'binary_sha256':sha(binary),'build_reused':True,'new_chain_operations':False}
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(command,'legacy-m4-real',['unshare','--user','--map-root-user','--net',native,'-m','pytest','-q','--tb=short','integration/chain/test_m4.py','--basetemp='+str(chain_output/'private-tests'),'--junitxml='+str(output/'legacy-m4-real.xml')],chain_env)
                    checks=None
                    while not future.done():
                        challenge=chain_output/'socket-challenge.json'
                        if challenge.exists() and checks is None:
                            checks=[]
                            for port in json.loads(challenge.read_text())['ports']:
                                with socket.socket() as sock:sock.settimeout(.5);checks.append(sock.connect_ex(('127.0.0.1',port)))
                        time.sleep(.2)
                    future.result()
                report['host_isolation']={'connection_errors':checks,'status':'PASS' if checks and all(c==111 for c in checks) else 'FAIL'}
                if report['host_isolation']['status']!='PASS':report['suites']['legacy-m4-real']='FAIL'
            except (OSError,AssertionError,ValueError,subprocess.CalledProcessError) as error:blocked(['legacy-m4-real'],str(error).replace(str(ROOT),'<FUSION>'))
    def together(*names):
        values=[report['suites'].get(n,'NOT_RUN') for n in names]
        return next((s for s in ('FAIL','OBSERVATION_TIMEOUT','BLOCKED','NOT_RUN') if s in values),'PASS')
    mapping={'RELATIONS_CONTRACT':['fixtures'],'RELATIONS_REAL':['storage'],'COMMITTED_SOURCE':['fixtures','storage'],
        'SEARCH_CONTRACT':['fixtures'],'SEARCH_REAL_REBUILD':['storage','hive'],'SUBSTITUTION':['fixtures','hive'],
        'RECOVERY':['storage','hive'],'AUTH_PRIVACY':['fixtures','hive'],'HIVE_LOOKUP':['hive'],
        'LEGACY_REGRESSION':['legacy-m1-m3_1','legacy-m4-fixtures','legacy-m4-real']}
    for gate,suites in mapping.items():report['gates'][gate]=together(*suites)
    report['source']['end_commit']=git('rev-parse','HEAD')
    report['source']['end_runtime_matches_start']=all((ROOT/p).exists() and sha(ROOT/p)==v for p,v in source['files'].items())
    stable=report['source']['end_runtime_matches_start'] and report['source']['end_commit']==source['commit'] and (args.development or not git('status','--porcelain'))
    report['gates']['REPRO_AND_LEDGER']='PASS' if stable and not args.development and together('fixtures','storage','hive')=='PASS' and (ROOT/'docs/module-interfaces/m5-capability-ledger.json').is_file() else 'NOT_RUN'
    if not stable:report['gates']['BASELINE_AND_SCOPE']='FAIL'
    if args.development:report['gates']['BASELINE_AND_SCOPE']='NOT_RUN'
    report['result']='PASS' if all(s=='PASS' for s in report['gates'].values()) else 'PARTIAL'
    save();return 0 if all(report['suites'].get(s) in ('PASS',None) for s in report['suites']) and stable and not violations else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--environment',type=Path);parser.add_argument('--chain-build',type=Path)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--gates',default='all',help='fixtures,storage,hive,legacy or all');parser.add_argument('--development',action='store_true')
    raise SystemExit(verify(parser.parse_args()))
