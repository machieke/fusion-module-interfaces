"""Fixed generation-denied native conformance lane from an extracted packet.

The historical native manifest pins a PYTHONPATH layout. Mount the extracted
distribution read-only at that virtual path, hiding the developer checkout.
Mount exact native/DeTTa assets separately. This does not rewrite runtime pins,
download assets, run a model backend or accept an arbitrary execution command.
Reports may contain synthetic private state: keep the output directory private.
"""
import argparse,json,os,subprocess,time
from pathlib import Path
from fusion.contracts import canonical,digest,require

TESTS=('integration.neoclaw.test_integrated_nal',
       'integration.neoclaw.test_integrated_worker',
       'integration.neoclaw.test_integrated_provider')

def qualify(source,native,detta,python,directory):
    source,native,detta,python=map(lambda p:Path(p).absolute(),(source,native,detta,python))
    out=Path(directory).absolute();require(not out.exists(),'CONFLICT')
    require((source/'fusion/contracts.py').is_file() and not (source/'.git').exists(),'CONFLICT')
    runtime=json.loads((native/'runtime.json').read_bytes());build=json.loads((native/'build.json').read_bytes())
    require(digest((native/'runtime.json').read_bytes())==build['runtime_sha256'],'UNSUPPORTED_PROFILE')
    legacy=Path(runtime['environment']['PYTHONPATH'])
    require(legacy.is_absolute() and len(legacy.parts)>3 and ':' not in str(legacy),'UNSUPPORTED_PROFILE')
    require(native.is_relative_to(legacy) and not source.is_relative_to(legacy) and
            not out.is_relative_to(legacy) and detta.is_file() and python.is_file(),'CONFLICT')
    out.mkdir(parents=True,mode=0o700)
    # Empty mount targets are derived extraction layout, not packaged content.
    (source/native.relative_to(legacy)).mkdir(parents=True,exist_ok=True)
    target=source/'artifacts/detta-build/target/debug/fusion-detta-adapter'
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():require(target.is_file() and target.stat().st_size==0,'CONFLICT')
    else:target.touch()
    check=("import pathlib,runpy,sys; assert not pathlib.Path("+repr(str(legacy/'.git'))+").exists(); "
           "assert pathlib.Path("+repr(str(legacy/'fusion/contracts.py'))+").read_bytes()==pathlib.Path("+
           repr(str(source/'fusion/contracts.py'))+").read_bytes(); sys.argv=['unittest','-v',*"+repr(TESTS)+"]; "
           "runpy.run_module('unittest',run_name='__main__')")
    args=['bwrap','--die-with-parent','--ro-bind','/','/','--bind','/tmp','/tmp','--dev','/dev','--proc','/proc',
          '--ro-bind',str(source),str(legacy),'--ro-bind',str(native),str(native),
          '--ro-bind',str(detta),str(out/'detta'),'--ro-bind',str(detta),str(target),
          '--chdir',str(source),'--setenv','S01_RUNTIME',str(native/'runtime.json'),
          '--setenv','S01_DETTA',str(out/'detta'),'--setenv','INTEGRATED_EVIDENCE',str(out/'evidence'),
          '--setenv','INTEGRATED_NAL_EVIDENCE',str(out/'nal'),'--setenv','PHASE2_EVIDENCE',str(out/'private'),
          '--unsetenv','PYTHONPATH','--',str(python),'-m','integration.neoclaw.preparation_guard',
          '--guard-evidence',str(out/'generation-denial.json'),'--',str(python),'-c',check]
    report=dict(status='RUNNING',additional_live_generations=0,tests=TESTS,commands=args,
                runtime_sha256=build['runtime_sha256'],detta_sha256=digest(detta.read_bytes()),
                source='EXTRACTED_DISTRIBUTION_READ_ONLY',developer_checkout='HIDDEN',
                model='RECORDED_PROPOSALS',independent_storage='ATOMIC_FILE_CONTRACT_FIXTURE',
                started_ms=time.time_ns()//1000000)
    def save():(out/'execution.json').write_bytes(canonical(report))
    save()
    try:
        with (out/'tests.log').open('x') as log:
            result=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=900,
                env={k:v for k,v in os.environ.items() if k!='PYTHONPATH'})
        report.update(exit_code=result.returncode,status='PASS' if result.returncode==0 else 'FAIL')
        # Child reports are supplementary. A failed unittest lane is never a
        # pass even if a subtest's best-effort exporter wrote a success label.
        require(result.returncode==0,'NOT_AVAILABLE')
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:report['finished_ms']=time.time_ns()//1000000;save()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','native','detta','python','directory'):p.add_argument('--'+name,required=True)
    a=p.parse_args();r=qualify(a.source,a.native,a.detta,a.python,a.directory)
    print(json.dumps(dict(status=r['status'],additional_live_generations=0)))
