"""Retrieval campaign: prepare, inspect, explicitly recorded qualify, approved execute.

No command implicitly starts a real generative runtime. Execute requires a separate
user approval and an already available, pinned, isolated backend at the frozen port.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
from fusion.contracts import canonical
from fusion.neoclaw_application import Application
from fusion.irc_bridge import Bridge
from fusion.model_service import ModelService
from . import retrieval_campaign as c
from .channel_composition import write
from .controlled_run import ControlledRun
from .embedding_run import start
from .retrieval_freeze import attach_channel
from .retrieval_preparation import evaluate


class ObserverExpired(RuntimeError): pass


def wait(predicate, deadline_ms, process=None):
    while time.time_ns()//1_000_000 < deadline_ms:
        value=predicate()
        if value:return value
        if process is not None and process.poll() is not None:raise RuntimeError('NATIVE_PROCESS_EXITED')
        time.sleep(.03)
    raise ObserverExpired('OBSERVER_EXPIRED_NO_RESUBMISSION_AUTHORITY')


def peer_received(traffic, body, target):
    # Require the independent peer's received frame, exact sender and route.
    for row in traffic:
        line=row.get('received','')
        prefix,sep,tail=line.partition(' PRIVMSG '+target+' :')
        if sep and prefix.startswith(':omega!') and tail==body:return True
    return False


def attach_run(session):
    run=ControlledRun.__new__(ControlledRun);run.processes=[];run.logs=[]
    run.app_path=Path(session['application']);run.app=c.read(run.app_path)
    root=run.app_path.parent.parent;caller=run.app_path.parent
    run.h=SimpleNamespace(root=root,caller_root=caller,client=c.read(run.app['caller_config']),close=lambda:None)
    return run


def progress(path, session, **values):
    value,_=c.plan(path)
    with c.locked(value['execution_root']) as root:
        state=c.ledger(path);row=state['sessions'].setdefault(session,{})
        row.update(values);c.atomic(root/'ledger.json',state)
        return dict(row)


def observe_session(path,session,*,recorded=False,checkpoint=None):
    """Shared native consumer for both placements; checkpoint is TEST ONLY."""
    value,approval=c.approve(path,Path(path).parent/'approval.json',recorded=recorded,assets=not recorded)
    c.require(checkpoint is None or recorded,'TEST_HOOK_IN_LIVE_RUN')
    s=next(x for x in value['sessions'] if x['id']==session)
    previous=c.ledger(path)['sessions'].get(session,{})
    c.require(not previous.get('finished'),'SESSION_ALREADY_FINISHED')
    # Owner expiry is initialized exactly once, separately from call deadlines.
    policy=c.read(s['policy']);expiry=policy['model_completion']['expires_ms']
    if expiry==1:
        policy['model_completion']['expires_ms']=approval['expires_ms'];write(s['policy'],policy)
    else:c.require(expiry==approval['expires_ms'],'ORIGINAL_EXPIRY_CHANGED')
    run=attach_run(s);ch=attach_channel(s['channel']);process=None;phase='runtime-preparation'
    begun=previous.get('started_ms',time.time_ns()//1_000_000)
    progress(path,session,started_ms=begun)
    evidence=dict(session=session,placement=s['placement'],boundary='RECORDED_RESPONSE' if recorded else 'REAL_MODEL',phases=[],live_memory_workflow='NOT_RUN' if recorded else 'ATTEMPTED')
    def snapshot():return Application.inspect(run.app_path)
    def hook(stage):
        nonlocal process
        if checkpoint:
            replacement=checkpoint(stage,run,ch,process)
            if replacement is not None:process=replacement
    try:
        hook('before-start')
        ch.start_host();ch.start_server();ch.start_bridge(seconds=750);ch.start_peer(seconds=750)
        if s['placement']=='network':
            ready=Path(s['completion_root'])/'ready.json';ready.unlink(missing_ok=True)
            host=run.spawn('integration.neoclaw.retrieval_backend',[s['backend_selection'],s['policy'],s['model_port'],ready],'model-host')
            ch.wait(ready,host)
        process=start(run)
        # On restart, readiness file belongs to the prior process: actual app
        # snapshots and durable inputs remain authoritative. No new deadline.
        wait(lambda:(Path(run.app['workdir'])/'embedding-ready.json').exists(),begun+value['limits']['preparation_observer_ms'],process)
        hook('ready')
        row=c.ledger(path)['sessions'][session]
        if not row.get('first_input_attempted'):
            progress(path,session,first_input_attempted=True,first_input_ms=time.time_ns()//1_000_000)
            ch.send(value['static_inputs']['peer_inputs'][0])
        phase='generation-and-query';row=c.ledger(path)['sessions'][session]
        hook('first-input')
        def query_done():
            state=snapshot();turns=state.get('app_turns',[])
            return state if turns and turns[0]['projection'] is not None else None
        state=wait(query_done,row['first_input_ms']+value['limits']['query_observer_ms'],process)
        evidence['phases'].append(dict(phase=phase,status='CAPTURED',observed_ms=time.time_ns()//1_000_000))
        query=state['app_turns'][0]['projection'];evidence['query_capture']=query
        truth=c.read(value['evaluator']['path'])['target_fact']
        c.require(truth is not None and truth in query,'RETRIEVAL_NOT_DECISIVE')
        hook('query-captured')
        row=c.ledger(path)['sessions'][session]
        if not row.get('second_input_attempted'):
            progress(path,session,second_input_attempted=True,second_input_ms=time.time_ns()//1_000_000)
            ch.send(value['static_inputs']['peer_inputs'][1])
        phase='generation-and-send';row=c.ledger(path)['sessions'][session];hook('second-input')
        def send_accepted():
            state=snapshot();outputs=state.get('app_channel_outputs',[])
            return state if any(x['acceptance'] is not None for x in outputs) else None
        state=wait(send_accepted,row['second_input_ms']+value['limits']['reply_observer_ms'],process)
        outputs=[x for x in state['app_channel_outputs'] if x['acceptance'] is not None]
        c.require(len(outputs)==1,'UNEXPECTED_OUTPUT_COUNT')
        envelope=json.loads(outputs[0]['envelope']);body=envelope['text']
        calls=state['app_model_calls'];c.require(len(calls)==2 and calls[1]['admission']=='authorized','SEND_NOT_ADMITTED')
        c.require(json.loads(calls[1]['proposal'])==[['send',body]],'SEND_PROPOSAL_MISMATCH')
        evidence.update(actual_admitted_send_body=body,next_input=json.loads(calls[1]['intent'])['native_prompt'])
        c.require(query in evidence['next_input'],'QUERY_CONTEXT_NOT_BOUND')
        hook('send-accepted');phase='peer-observation'
        deadline=min(envelope['deadline_ms']+value['limits']['peer_observer_ms'],row['second_input_ms']+value['limits']['reply_observer_ms'])
        wait(lambda:peer_received(ch.traffic(),body,envelope['target']),deadline)
        evidence['evaluation']=evaluate(query,body,True,truth)
        evidence['outcome']=evidence['evaluation']['task']
        # Completion/capture and native bounded stop are separate observations.
        wait(lambda:process.poll() is not None,min(deadline,time.time_ns()//1_000_000+30000))
        evidence['native_exit']=process.returncode
    except Exception as exc:
        evidence.update(outcome='OBSERVER_TIMEOUT' if isinstance(exc,ObserverExpired) else 'FAILED',failure_phase=phase,
                        failure=exc.code if hasattr(exc,'code') else str(exc))
    finally:
        evidence['application']=snapshot();evidence['peer']=ch.traffic();evidence['bridge']=Bridge.inspect(ch.bridge_config_path)
        evidence['model_owner']=ModelService.inspect(s['policy'])
        evidence['disclosure_receipts']=[c.read(p) for p in sorted((Path(path).parent/s['placement']/'receipts').glob('*.json'))]
        evidence['ledger']=c.ledger(path)
        status=Path(run.app['status_file']);evidence['native_status']=c.read(status) if status.exists() else None
        evidence['elapsed_ms']=time.time_ns()//1_000_000-begun
        ch.close();run.close()
    progress(path,session,finished=True,outcome=evidence['outcome'])
    if not recorded:
        with c.locked(value['execution_root']) as root:
            state=c.ledger(path)
            observations=[row for selected in value['sessions'] for row in ModelService.inspect(selected['policy'])]
            state.update(authorized_live_generations=4,reserved_live_generations=sum(x['reserved'] for x in observations),
                observed_generative_backend_calls=len(state['started']),captured_live_responses=sum(x['response'] is not None for x in observations))
            c.atomic(root/'ledger.json',state)
    c.atomic(Path(value['execution_root'])/(session+'-report.json'),evidence)
    return evidence


def execute(path,approval,*,recorded=False,checkpoint=None):
    value,_=c.approve(path,approval,recorded=recorded)
    c.require(Path(approval).resolve()==Path(path).resolve().parent/'approval.json','APPROVAL_LOCATION_MISMATCH')
    root=Path(value['execution_root']);root.mkdir(exist_ok=True)
    c.require(not c.ledger(path).get('campaign_stop'),'CAMPAIGN_STOPPED')
    with open(root/'run.lock','a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('CAMPAIGN_ALREADY_RUNNING') from None
        reports=[]
        for s in value['sessions']:
            if c.ledger(path)['sessions'].get(s['id'],{}).get('finished'):continue
            report=observe_session(path,s['id'],recorded=recorded,checkpoint=checkpoint);reports.append(report)
            status=report.get('native_status') or {}
            if not recorded and status.get('code') in ('UNAUTHORIZED','CONFLICT','UNSUPPORTED_PROFILE'):
                with c.locked(root):
                    state=c.ledger(path);state['campaign_stop']=dict(session=s['id'],reason=status['code']);c.atomic(root/'ledger.json',state)
                break
        return reports


def test_approval(path):
    value,sha=c.plan(path);c.require(value['kind']=='recorded-qualification','TEST_APPROVAL_FOR_LIVE_FORBIDDEN')
    now=time.time_ns()//1_000_000
    c.atomic(Path(path).parent/'approval.json',dict(authority='TEST_ONLY_RECORDED_RESPONSES',campaign_id=value['campaign_id'],manifest_sha256=sha,
        slots=[x['name'] for x in value['slots']],max_generations=4,user_statement='Isolated authored-response test authority; ZERO real generations',
        not_before_ms=now,expires_ms=now+1800000,parent_namespace=os.environ['FUSION_PREP_PARENT_NET']))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','inspect','qualify','execute'])
    p.add_argument('--root');p.add_argument('--manifest');p.add_argument('--approval');p.add_argument('--evidence')
    a=p.parse_args()
    try:
        if a.mode in ('prepare','qualify'):
            from .retrieval_freeze import prepare
            path=prepare(a.root,recorded=a.mode=='qualify')
            if a.mode=='qualify':test_approval(path);result=execute(path,Path(path).parent/'approval.json',recorded=True)
            else:result=c.inspect(path)
        elif a.mode=='inspect':result=c.inspect(a.manifest)
        else:result=execute(a.manifest,a.approval)
        if a.evidence:c.atomic(a.evidence,result)
        print(json.dumps(result if a.mode!='qualify' else [dict(session=x['session'],outcome=x['outcome'],failure=x.get('failure')) for x in result],indent=2))
        if isinstance(result,dict) and result.get('drift'):raise SystemExit(1)
        if isinstance(result,list) and any(x['outcome']!='PASS' for x in result):raise SystemExit(1)
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc),file=sys.stderr);raise SystemExit(2)


if __name__=='__main__':main()
