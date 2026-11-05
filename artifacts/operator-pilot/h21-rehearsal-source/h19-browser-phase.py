"""Task-local H browser observer. Runs only in its isolated credential-free client mount."""
import argparse, hashlib, json, os, subprocess, time, urllib.parse
from pathlib import Path
from examples.pilot_browser_qualification import BrowserClient, check

ROOT=Path('/results');BASE='http://127.0.0.1:8878'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('story','visual','close'));a=p.parse_args()
    end=float(os.environ['H19_NATIVE_END']);check(time.monotonic()<end,'ORIGINAL_WINDOW_EXPIRED')
    check(not Path('/credentials').exists() and not Path('/secrets').exists(),'OPERATOR_MATERIAL_MOUNTED')
    check(not Path('/home/purplezky/work').exists() and not os.environ.get('KUBECONFIG'),'AUTHOR_CONFIG_EXPOSED')
    from importlib.util import find_spec
    check(all(find_spec(n)is None for n in ('torch','transformers','chromadb')),'INFERENCE_LIBRARY_IN_CLIENT')
    out=ROOT/(a.phase+'.json');check(not out.exists(),'OUTPUT_EXISTS')
    report=dict(profile='task-local-H-browser-phase/1',phase=a.phase,status='RUNNING',source_sha256=sha(__file__),additional_live_generations=0,native_submissions=0,api_calls=0,source_checkout_mounted=False,kubeconfig_mounted=False,provider_credentials_mounted=False,model_assets_mounted=False,actions=[])
    def record(name,value):report['actions'].append(dict(name=name,value=value));save(out,report)
    def client():return BrowserClient(BASE,'shared',Path('/user/shared.bootstrap').read_text().strip())
    def request(c,path,body=None):
        check(time.monotonic()<end,'ORIGINAL_WINDOW_EXPIRED');report['api_calls']+=1;save(out,report);return c.request(path,body)
    def snapshots(c):
        story=json.loads((ROOT/'shared-story.json').read_bytes());check(story['status']=='PASS'and len(story['inputs'])==14,'STORY_NOT_COMPLETE')
        state=request(c,'/api/state');check(state['namespace']=='omega-ref-pilot-adopter21','NAMESPACE_DRIFT');rows={}
        for role,v in state['agents'].items():
            ids=list(v['sessions']);check(len(ids)==1,'UNEXPECTED_SCOPE_SESSION_COUNT');sid=ids[0]
            observed=request(c,'/api/session?'+urllib.parse.urlencode(dict(role=role,session=sid,after=0)))
            check(all(x['state']=='complete'for x in observed['inputs']),'UNCAPTURED_INPUT')
            rows[role]=dict(session=sid,value=observed)
        check(rows['omega-agent']['session']==story['sessions']['shared']['session'],'SESSION_DRIFT')
        check(len(rows['omega-agent']['value']['inputs'])==15 and len(rows['omega-agent-b']['value']['inputs'])==1,'CAPTURE_COUNT')
        direct={(x['selected']['session'],x['receipt']['id'])for x in story['inputs']}
        observed={(v['session'],x['id']):x for v in rows.values()for x in v['value']['inputs']}
        check(len(direct)==14 and len(observed)==16 and direct<=set(observed),'DIRECT_CAPTURE_IDENTITY')
        internal=[observed[key]for key in set(observed)-direct]
        check(sorted(x['assignment']for x in internal)==['delegated-result','delegated-task'],'INTERNAL_CAPTURE_IDENTITY')
        check(all(observed[(x['selected']['session'],x['receipt']['id'])]==x['observed']for x in story['inputs']),'DIRECT_CAPTURE_CHANGED')
        return rows
    started_proof=False
    try:
        save(out,report)
        if a.phase=='story':
            cmd=['/work/operator/bin/python','-I','/story.py','--root','/user','--plan','/story-plan.json','--phase','shared','--output',str(ROOT/'shared-story.json')]
            record('existing_story_invocation',dict(command=cmd,maximum_seconds=min(900,end-time.monotonic())))
            with (ROOT/'shared-story.stdout').open('xb')as stdout,(ROOT/'shared-story.stderr').open('xb')as stderr:
                result=subprocess.run(cmd,stdout=stdout,stderr=stderr,timeout=min(900,end-time.monotonic()),check=False)
            check(result.returncode==0,'STORY_DRIVER_FAILED')
            d=json.loads((ROOT/'shared-story.json').read_bytes());check(d['status']=='PASS'and len(d['inputs'])==14,'NATIVE_STORY_INCOMPLETE')
            check(d['source_sha256']==sha('/story.py'),'STORY_SOURCE_DRIFT')
            report['native_submissions']=14;report['direct_captures']=14;report['internal_captures']=2
        elif a.phase=='visual':
            c=client();c.login();before=snapshots(c);record('retained_before_UI',before)
            sid=before['omega-agent']['session'];prefix=['/node/bin/proofshot']
            def ui(*args):
                check(time.monotonic()<end,'ORIGINAL_WINDOW_EXPIRED')
                r=subprocess.run([*prefix,*args],cwd=ROOT,env=os.environ,capture_output=True,text=True,timeout=min(40,end-time.monotonic()))
                # Bootstrap arguments stay in the private record; no public logs.
                record('proofshot',dict(args=list(args),returncode=r.returncode,stdout=r.stdout,stderr=r.stderr))
                check(r.returncode==0,'PROOFSHOT_OPERATION_FAILED');return r.stdout.strip()
            def val(expr):return json.loads(json.loads(ui('exec','eval','JSON.stringify('+expr+')')))
            def until(expr):
                stop=min(end,time.monotonic()+35)
                while time.monotonic()<stop:
                    if val(expr):return
                    time.sleep(.3)
                raise AssertionError('UI_OBSERVATION_EXPIRED')
            (ROOT/'proofshot.config.json').write_text(json.dumps(dict(output=str(ROOT/'proof'))))
            # The operator starts the explicitly selected port-forward. There is
            # no --run server command and no general port/process cleanup.
            started_proof=True
            ui('start','--port','8878','--description','Final packet H native capture, scoped history and reconnect')
            ui('exec','fill','#user','shared');ui('exec','fill','#access',Path('/user/shared.bootstrap').read_text().strip());ui('exec','click','#connect')
            until("document.querySelector('#authState').textContent.includes('shared')")
            until("Array.from(document.querySelector('#session').options).some(x=>x.value=="+json.dumps(sid)+")")
            ui('exec','select','#session',sid);until("document.querySelector('#completed').textContent==='15'")
            ui('exec','scrollintoview','#current');ui('exec','click','#current');until("document.querySelector('#currentState').textContent.includes('source_head')")
            ui('exec','scrollintoview','#historyRead');ui('exec','click','#historyRead');until("document.querySelector('#explorerState').textContent.includes('native-session-history')")
            ui('exec','screenshot',str(ROOT/'history-private.png'))
            ui('exec','reload');until("document.querySelector('#authState').textContent.includes('shared')")
            until("Array.from(document.querySelector('#session').options).some(x=>x.value=="+json.dumps(sid)+")")
            ui('exec','select','#session',sid);until("document.querySelector('#completed').textContent==='15'")
            after=snapshots(c);check(after==before,'CAPTURE_CHANGED_ON_RELOAD');record('retained_after_UI_reload',after)
            ui('exec','scrollintoview','#logout');ui('exec','click','#logout');until("document.querySelector('#authState').textContent==='Signed out'")
            check(val("['events','currentState','explorerState'].every(id=>document.getElementById(id).textContent==='')")and val("document.querySelector('#session').options.length===0"),'LOGOUT_VIEW_NOT_CLEARED')
            ui('exec','screenshot',str(ROOT/'signed-out.png'));c.logout();report.update(retained_captures=16,browser_reload_no_submissions=True,scoped_history_visible=True)
            ui('stop');started_proof=False
        else:
            c=client();c.login();before=snapshots(c);record('retained_before_close',before)
            for role,row in before.items():
                if row['value']['state']!='closed':
                    receipt=request(c,'/api/action',dict(role=role,session=row['session'],operation='close',identity='h21-browser-close-'+role));record('close',dict(role=role,receipt=receipt))
                after=request(c,'/api/session?'+urllib.parse.urlencode(dict(role=role,session=row['session'],after=0)))
                check(after['state']=='closed'and after['inputs']==row['value']['inputs'],'CLOSE_CAPTURE_DRIFT');record('retained_after_close',dict(role=role,observation=after))
            c.logout();report['retained_captures']=16
        report['status']='PASS'
    except BaseException as error:
        report.update(status='FAIL_RETAINED',failure=dict(type=type(error).__name__,message=str(error)[:600]));raise
    finally:
        if started_proof:
            try:
                r=subprocess.run(['/node/bin/proofshot','stop'],cwd=ROOT,env=os.environ,capture_output=True,text=True,timeout=min(35,max(.1,end-time.monotonic())))
                report['proof_cleanup']=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
            except BaseException as error:report['proof_cleanup']=dict(status='FAIL',type=type(error).__name__,message=str(error)[:300])
        save(out,report)
    print(json.dumps(dict(status=report['status'],phase=a.phase,additional_live_generations=0)))

if __name__=='__main__':main()
