"""Finite browser story through the installed stdlib BrowserClient.

Native commands execute only at the selected application owner. Recorded model
responses propose commands; this operator test never supplies a tool result.
The private plan contains approved generated corpus/evaluator data. Query text
cannot contain its expected answer. Returned native handles drive composition.
No cluster credential, provider secret, model asset or author checkout is needed.

Use the packet script with the installed operator Python -I. Reports contain
private inputs/handles and must stay private until separately sanitized. A run
never resumes by resubmitting: an existing output path is refused, and an unknown
submission remains recorded under its original identity for owner observation.
"""
import argparse,copy,hashlib,json,os,sys,time,urllib.parse,urllib.error,re
from pathlib import Path
from examples.pilot_browser_qualification import BrowserClient,fingerprint,check

def refusal_observation(client,path,body,record):
    """A failed transport observation is neither disclosure nor denial proof."""
    try:value=client.request(path,body)
    except RuntimeError as error:
        record(dict(path=path,state='REFUSED',code=str(error)))
        if str(error)!='UNAUTHORIZED':raise
        return True
    record(dict(path=path,state='RETURNED_BODY',body=value));return False

def resume_report(previous,plan,phase,source):
    """Resume only acknowledged effects; unknown submission outcomes stay blocked."""
    check(previous.get('profile')=='pilot-browser-deployed-native-story/1' and previous.get('status')=='FAILED_RETAINED','RESUME_STATE')
    check(previous.get('phase')==phase and previous.get('namespace')==plan['namespace'] and previous.get('plan_sha256')==fingerprint(plan),'RESUME_BINDING')
    check(previous.get('additional_live_generations')==0 and previous.get('model')=='RECORDED_FIXTURE','RESUME_BINDING')
    check(len(previous.get('resumptions',[]))<4,'RESUME_BOUND')
    check(previous.get('allocation_attempts') and all(x.get('state')=='ACCEPTANCE_OBSERVED' and x.get('receipt') for x in previous['allocation_attempts']),'UNKNOWN_ALLOCATION_OUTCOME')
    check(all(x.get('state') in ('ACCEPTED','OBSERVED') and x.get('receipt') for x in previous['inputs']),'UNKNOWN_SUBMISSION_OUTCOME')
    result=copy.deepcopy(previous);result.setdefault('resumptions',[]).append(dict(previous_canonical_sha256=fingerprint(previous),previous_source_sha256=previous['source_sha256'],previous_failure=previous.get('failure'),source_sha256=source))
    result.update(status='RUNNING',source_sha256=source);result.pop('failure',None);return result

def observe_accepted(client,selected,accepted,entry,save):
    """Bounded explicit observation retries, never an effect submission.

    The existing client has a 35-second per-request transport bound. The window
    may expire with one read in flight; it cannot change an accepted deadline.
    An already expired occurrence gets one final read for retained capture.
    """
    start=time.monotonic();remaining=max(0,(accepted['deadline']-time.time_ns()//1000000)/1000)
    maximum=150 if remaining else 1
    end=start+min(150,remaining+5);window=dict(started_ms=time.time_ns()//1000000,original_deadline_ms=accepted['deadline'],maximum_reads=maximum,request_timeout_seconds=35,attempts=[])
    entry.setdefault('observation_windows',[]).append(window);save();last=None
    for number in range(maximum):
        attempt=dict(read=number+1);window['attempts'].append(attempt);save();read_start=time.monotonic()
        try:
            observed=client.observe(selected['role'],selected['session'])
        except (RuntimeError,urllib.error.URLError,TimeoutError,OSError) as error:
            code=str(error) if isinstance(error,RuntimeError) else 'NOT_AVAILABLE'
            attempt.update(state='REFUSED',code=code,read_ms=round((time.monotonic()-read_start)*1000,3));save()
            if code not in ('OVERLOADED','NOT_AVAILABLE') or time.monotonic()>=end:raise
        else:
            rows=[x for x in observed['inputs'] if x['id']==accepted['id']];check(len(rows)==1,'ACCEPTED_INPUT_MISSING');last=rows[0]
            check(last['deadline']==accepted['deadline'],'DEADLINE_CHANGED')
            attempt.update(state='OBSERVED',owner_state=last['state'],read_ms=round((time.monotonic()-read_start)*1000,3));entry.setdefault('owner_read_latency_ms',[]).append(attempt['read_ms']);save()
            if last['state'] in ('complete','expired-before-start','cancelled-before-start','rejected') or time.monotonic()>=end:break
        if number+1<maximum:time.sleep(min(1,max(0,end-time.monotonic())))
    check(last is not None,'OBSERVATION_EXPIRED')
    if entry.get('observed',{}).get('state')=='complete':check(last==entry['observed'],'CAPTURE_CHANGED')
    entry.update(state='OBSERVED',observed=last,observation_seconds=round(time.monotonic()-start,3));save();return last

def validate_plan(plan):
    check(type(plan) is dict and set(plan)=={'profile','namespace','identity','corpus'})
    check(plan['profile']=='bounded-native-browser-story/1')
    check(type(plan['namespace']) is str and plan['namespace'].startswith('omega-ref-pilot-'))
    check(type(plan['identity']) is str and re.fullmatch('[a-z0-9-]{1,48}',plan['identity']))
    check(type(plan['corpus']) is dict and set(plan['corpus'])=={'alice','bob','shared'})
    for user,entry in plan['corpus'].items():
        check(type(entry) is dict and set(entry)=={'remember','query','expected','disclosure'})
        check(entry['disclosure']==('synthetic-shareable' if user=='shared' else 'synthetic-private'))
        for key in ('remember','query','expected'):
            check(type(entry[key]) is str and 0<len(entry[key].encode())<=2048)
        check(entry['expected'] in entry['remember'] and entry['expected'] not in entry['query'],'ANSWER_IN_QUERY_OR_MISSING_FROM_CORPUS')
    return plan

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--phase',choices=['private','shared'],required=True);p.add_argument('--output',required=True);p.add_argument('--plan',required=True);p.add_argument('--resume-from');p.add_argument('--base',default='http://127.0.0.1:8878');a=p.parse_args();check(Path(a.plan).stat().st_size<=16384,'PLAN_TOO_LARGE');plan=validate_plan(json.loads(Path(a.plan).read_bytes()))
    root=Path(a.root);target=Path(a.output);check(not target.exists(),'OUTPUT_EXISTS');os.umask(0o077);target.parent.mkdir(parents=True,exist_ok=True);target.touch(mode=0o600,exist_ok=False)
    report=dict(profile='pilot-browser-deployed-native-story/1',phase=a.phase,status='RUNNING',namespace=plan['namespace'],
     additional_live_generations=0,model='RECORDED_FIXTURE',transport='BROWSER_API_THEN_SCOPED_OWNER_HTTPS',inputs=[],checks=[],sessions={},allocation_attempts=[],
     client_environment=dict(kubeconfig_present='KUBECONFIG' in os.environ,repository_on_import_path=any((Path(x)/'.git').exists() and (Path(x)/'fusion').is_dir() for x in sys.path if x),provider_credentials_provided=False),
     source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),plan_sha256=fingerprint(plan))
    recovered_count=0;command_cursor=0
    if a.resume_from:
        previous=Path(a.resume_from);check(previous.stat().st_size<=4*1024*1024,'RESUME_TOO_LARGE')
        report=resume_report(json.loads(previous.read_bytes()),plan,a.phase,report['source_sha256']);recovered_count=len(report['inputs'])
        report['resumptions'][-1]['previous_report_sha256']=hashlib.sha256(previous.read_bytes()).hexdigest()
    def save():
        temporary=target.with_suffix('.pending')
        with temporary.open('w') as stream:
            os.chmod(temporary,0o600);json.dump(report,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        temporary.replace(target)
        fd=os.open(target.parent,os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    def client(user):
        c=BrowserClient(a.base,user,(root/(user+'.bootstrap')).read_text().strip());c.login();return c

    def allocate(c,role,template):
        state=c.request('/api/state');check(state['namespace']==plan['namespace'] and state['additional_live_generations']==0,'WRONG_DEPLOYMENT');check(state['agents'][role]['model_boundary']==['RECORDED_FIXTURE'],'LIVE_SELECTION_REFUSED')
        intent=dict(role=role,session='',operation='allocate',identity=plan['identity']+'-'+a.phase+'-'+c.user+'-allocation',template=template)
        if a.resume_from:
            attempts=[x for x in report['allocation_attempts'] if x['intent']==intent];check(len(attempts)==1,'RESUME_ALLOCATION_MISMATCH')
            value=attempts[0]['receipt'];check(report['sessions'][c.user]==dict(role=role,session=value['session'],allocation=value),'RESUME_SESSION_MISMATCH')
            return dict(role=role,session=value['session'])
        attempt=dict(intent=intent,state='BEFORE_SUBMISSION');report['allocation_attempts'].append(attempt);save()
        value=c.request('/api/action',intent);attempt.update(state='ACCEPTANCE_OBSERVED',receipt=value)
        report['sessions'][c.user]=dict(role=role,session=value['session'],allocation=value);save();return dict(role=role,session=value['session'])
    def current(c,selected):return c.request('/api/current?'+urllib.parse.urlencode(dict(selected,operation='current')))
    def explore(c,selected,operation,body):return c.request('/api/explore',dict(selected,operation=operation,body=body))
    def refused(c,path,body):
        def record(value):report.setdefault('refusal_observations',[]).append(dict(user=c.user,**value));save()
        return refusal_observation(c,path,body,record)

    def run(c,selected,command):
        nonlocal command_cursor
        identity=plan['identity']+'-'+a.phase+'-'+c.user+'-'+str(command_cursor);index=command_cursor;command_cursor+=1
        check(index<30,'BOUND');caps=c.request('/api/capabilities?'+urllib.parse.urlencode(selected));check(caps['model_boundary']=='RECORDED_FIXTURE')
        validation=c.request('/api/preflight',dict(selected,commands=[command]));check(validation['preflight']['admissible'],validation['preflight'])
        if index<recovered_count:
            entry=report['inputs'][index];check(entry['identity']==identity and entry['selected']==selected and entry['command']==command,'RESUME_COMMAND_MISMATCH');accepted=entry['receipt']
            entry.setdefault('recoveries',[]).append(dict(mode='OBSERVE_ONLY_NO_SUBMISSION',at_ms=time.time_ns()//1000000));save()
        else:
            check(index==len(report['inputs']),'RESUME_ORDER')
            entry=dict(identity=identity,selected=selected,command=command,state='BEFORE_SUBMISSION',preflight=validation);report['inputs'].append(entry);save()
            accepted=c.request('/api/action',dict(selected,operation='submit',identity=identity,text=' '.join(command),assignment='synthetic-task',catalogue=caps['catalogue']))
            entry.update(state='ACCEPTED',receipt=accepted,owner_read_latency_ms=[],native_completion_latency='NOT_INFERRED_FROM_FIRST_OBSERVATION');save()
        row=observe_accepted(c,selected,accepted,entry,save)
        print(c.user,command[0],row['state'],flush=True);check(row['state']=='complete','NATIVE_INPUT_NOT_COMPLETE')
        result=row['result']['projection'];check('WORKER-ERROR' not in result,'NATIVE_TOOL_ERROR');return result

    def obj(projection):
        text=projection.replace('_quote_','"');return json.JSONDecoder().raw_decode(text[text.index('{'):])[0]
    def retained(c,selected):
        before=c.observe(selected['role'],selected['session']);c.logout();c.login();after=c.observe(selected['role'],selected['session']);check(before==after,'RECONNECT_CHANGED_CAPTURE')
        report['checks'].append(dict(name=c.user+'-exact-read-reconnect',passed=True,admissions=0,inputs_sha256=fingerprint(after['inputs'])));save()

    try:
        check(not report['client_environment']['kubeconfig_present'] and not report['client_environment']['repository_on_import_path'])
        if a.phase=='private':
            ca=client('alice');cb=client('bob');sa=allocate(ca,'omega-agent','private');sb=allocate(cb,'omega-agent-b','private')
            for c,s in [(ca,sa),(cb,sb)]:
                selected_data=plan['corpus'][c.user];fact=selected_data['remember']
                mem=obj(run(c,s,['remember',fact]));answer=run(c,s,['query',selected_data['query']]);check(selected_data['expected'] in answer,'RETRIEVAL_WRONG')
                run(c,s,['episodes','current']);run(c,s,['promote',mem['memory']['handle']]);run(c,s,['query',selected_data['query']])
                now=current(c,s);history=explore(c,s,'history',dict(snapshot=None,start=1));second=None
                if not history['value']['complete']:second=explore(c,s,'history',dict(snapshot=history['value']['snapshot'],start=history['value']['next_sequence']))
                report.setdefault('owners',{})[c.user]=dict(current=now,history=history,second=second);save();retained(c,s)
            for c,foreign in [(ca,sb),(cb,sa)]:
                checks=[refused(c,'/api/current?'+urllib.parse.urlencode(dict(foreign,operation='current')),None),refused(c,'/api/explore',dict(foreign,operation='history',body=dict(snapshot=None,start=1)))]
                checks.append(refused(c,'/api/session?'+urllib.parse.urlencode(dict(foreign,after=0)),None))
                check(all(checks),'PRIVATE_DISCLOSURE');report['checks'].append(dict(name=c.user+'-foreign-scope-refused',passed=True,paths=len(checks)))
            ca.logout();cb.logout()
        elif a.phase=='shared':
            c=client('shared');s=allocate(c,'omega-agent','shared');selected_data=plan['corpus']['shared']
            memory=obj(run(c,s,['remember',selected_data['remember']]))['memory']['handle']
            page=obj(run(c,s,['episodes','current']));source=next(x['body']['source']['handle'] for x in page['events'] if x['kind']=='external-observation')
            relation=obj(run(c,s,['link',memory,source]))['relation']['handle'];run(c,s,['support',memory,source]);before=run(c,s,['query',selected_data['query']])
            check(selected_data['expected'] in before,'QUERY_WRONG');run(c,s,['promote',memory]);after=run(c,s,['query',selected_data['query']]);check(selected_data['expected'] in after,'QUERY_WRONG')
            now=current(c,s);active=now['lifecycle']['membership']['active'];check(len(active)==1,'TARGET_AMBIGUOUS')
            edges=explore(c,s,'relations',dict(logical_id=active[0]['logical_id'],direction='outgoing',cursor=None,snapshot=None));check(edges['value']['records'],'RELATION_NOT_OBSERVED')
            history=explore(c,s,'history',dict(snapshot=None,start=1));report['owners']=dict(current=now,edges=edges,history=history);save()
            run(c,s,['write-file','pilot.txt','Synthetic browser note']);run(c,s,['append-file','pilot.txt','Second bounded line']);text=run(c,s,['read-file','pilot.txt']);check('Second bounded line' in text,'WORKSPACE_WRONG')
            task=obj(run(c,s,['delegate','B',selected_data['query']]));end=time.monotonic()+max(0,(task['deadline']-time.time_ns()//1000000)/1000)+5;returned=[]
            for _ in range(150):
                observed=c.observe(s['role'],s['session']);returned=[x for x in observed['inputs'] if x['assignment']=='delegated-result' and x['deadline']==task['deadline']]
                if returned and returned[0]['state']=='complete' or time.monotonic()>=end:break
                time.sleep(1)
            check(returned and returned[0]['state']=='complete','DELEGATED_RESULT_NOT_COMPLETE');report['delegation']=dict(task=task,returned=returned);save()
            run(c,s,['unlink',relation]);gone=explore(c,s,'relations',dict(logical_id=active[0]['logical_id'],direction='outgoing',cursor=None,snapshot=None));check(not gone['value']['records'],'UNLINK_NOT_OBSERVED')
            retained(c,s);report['retained_query_before_withdrawal']=before;run(c,s,['forget',memory]);excluded=run(c,s,['query',selected_data['query']]);check(selected_data['expected'] not in excluded,'WITHDRAWAL_NOT_OBSERVED')
            check(refused(c,'/api/explore',dict(s,operation='relations',body=dict(logical_id=active[0]['logical_id'],direction='outgoing',cursor=None,snapshot=None))),'WITHDRAWN_TARGET_DISCLOSED')
            report['withdrawal']=dict(physical_erasure=False,query=excluded,current=current(c,s));retained(c,s);c.logout()
        report['status']='PASS'
    except Exception as error:
        report['status']='FAILED_RETAINED';report['failure']=dict(type=type(error).__name__,code=str(error)[:160]);raise
    finally:save()

if __name__=='__main__':main()
