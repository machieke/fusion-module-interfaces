"""Observe an already planned native workflow's worker; never submit or warm it.

Run with the installed operator Python -I. The report contains private session
identifiers. The workflow driver remains separate and keeps its original bound.
"""
import argparse,hashlib,json,time,uuid
from pathlib import Path
from examples.pilot_browser_qualification import BrowserClient,check

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('workflow-report','bootstrap-file','user','namespace','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--base',default='http://127.0.0.1:8878');p.add_argument('--seconds',type=int,default=90);a=p.parse_args()
    check(1<=a.seconds<=120 and a.namespace.startswith('omega-ref-pilot-'))
    out=Path(a.output);check(not out.exists());report=dict(status='OBSERVING',observations=[],submissions=0,additional_live_generations=0,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    def save():out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');out.chmod(0o600)
    client=BrowserClient(a.base,a.user,Path(a.bootstrap_file).read_text().strip());end=time.monotonic()+a.seconds;save()
    try:
        client.login();state=client.request('/api/state');check(state['namespace']==a.namespace and state['additional_live_generations']==0)
        check(state['agents']['omega-agent']['model_boundary']==['RECORDED_FIXTURE'])
        for _ in range(120):
            path=Path(a.workflow_report)
            if path.exists():
                check(path.stat().st_size<=1048576);workflow=json.loads(path.read_bytes());sid=workflow.get('session')
                if sid:
                    check(str(uuid.UUID(sid))==sid)
                    value=client.request('/api/worker-control',dict(role='omega-agent',session=sid,operation='observe',identity=None))
                    report['observations'].append(dict(at_ms=time.time_ns()//1000000,value=value));save()
                    if (value.get('current') or {}).get('state') in ('idle','running'):
                        report.update(status='NATIVE_WORKER_READY_OBSERVED',session=sid);save();print('Already planned native worker ready/running observed; no work submitted.');return
            if time.monotonic()>=end:break
            time.sleep(1)
        report['status']='OBSERVER_EXPIRED';save();raise RuntimeError('OBSERVER_EXPIRED_NO_RESUBMISSION')
    except BaseException as error:
        report.update(status='FAILED_RETAINED',failure=dict(type=type(error).__name__,code=str(error)));save();raise
    finally:
        if client.csrf:client.logout()

if __name__=='__main__':main()
