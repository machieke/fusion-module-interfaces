"""Finite LIVE S07 recipe. Operator must explicitly authorize local generation.

No response is resampled. A failed or uncertain case terminates this campaign.
"""
import argparse
import json
from pathlib import Path
import signal
import sqlite3
import time
from fusion import model_contracts as c
from fusion.adapters.ollama_completion import OllamaCompletion,exchange
from fusion.contracts import canonical,require
from .controlled_run import ControlledRun
from .model_composition import configure,runtime_lock,INPUTS,OUTPUT
from .embedding_run import start
from .channel_composition import ROOT


def case(corpus,output,placement,mailbox,recover=False,*,profile=c.PROFILE,turns=2):
    run=ControlledRun('local',['',''],search={'boundary':'recorded-response'});cfg=None
    try:
        cfg=configure(run,corpus,placement,mailbox,runtime_lock=runtime_lock(output),profile=profile,turns=turns);ch=cfg['channel']
        if recover:run.app['pause_at']='after_model_application_capture';run.save()
        seconds=turns*c.deadline_limit(profile)//1000+90
        run.operator(seconds=seconds);ch.start_bridge(seconds=seconds);ch.start_peer(seconds=seconds);p=start(run)
        ch.send(INPUTS[0])
        before=None
        if recover:
            run.h.wait_file(run.app['failpoint_marker'],p,seconds=c.deadline_limit(profile)//1000+30)
            before=ch.rows(run.h.client['database'],'app_model_calls')
            run.kill(p);require(p.returncode==-signal.SIGKILL,'NOT_AVAILABLE')
            run.app.pop('pause_at');run.save();p=start(run)
        if turns==2:
            # A new real IRC event is sent only after the first native command
            # finishes. Do not leave it queued beyond the S06 ingress TTL.
            until=time.monotonic()+c.deadline_limit(profile)/1000+30
            completed=[]
            while p.poll() is None and time.monotonic()<until:
                try:completed=run.rows('app_turns')
                except sqlite3.OperationalError as exc:
                    if 'no such table: app_turns' not in str(exc):raise
                if completed and completed[0]['projection'] is not None:break
                time.sleep(.05)
            require(p.poll() is None and completed and completed[0]['projection'] is not None,'NOT_AVAILABLE')
            ch.send(INPUTS[1])
        p.wait(timeout=c.deadline_limit(profile)//1000+45)
        require(run.finish(p)==(0,{'status':'BOUNDED_STOP'}),'NOT_AVAILABLE')
        if turns==2:
            until=time.monotonic()+5
            while time.monotonic()<until and not any(' :'+OUTPUT in x.get('received','') for x in ch.traffic()):time.sleep(.05)
            require(any(' :'+OUTPUT in x.get('received','') for x in ch.traffic()),'NOT_AVAILABLE')
        rows=ch.rows(run.h.client['database'],'app_model_calls');provider=ch.rows(cfg['completion_root']/'model.sqlite','model_calls')
        require(len(rows)==len(provider)==turns and all(r['reserved']==1 for r in provider),'NOT_AVAILABLE')
        if before:
            for old,new in zip(before,rows):
                require(all(old[k]==new[k] for k in ('id','intent','context_view','result')),'CONFLICT')
        # Assert the next prompt contains the native tool result from this run.
        native_turns=run.rows('app_turns')
        require('COMMAND_RETURN' in native_turns[0]['projection'],'NOT_AVAILABLE')
        if turns==2:require(native_turns[0]['projection'] in json.loads(rows[1]['intent'])['native_prompt'],'NOT_AVAILABLE')
        result=dict(classification='REAL_OLLAMA_GENERATION',model_placement=placement,mailbox_placement=mailbox,
            same_host=True,model_calls=rows,provider_calls=provider,turns=native_turns,traffic=ch.traffic(),
            occurrences=run.rows('app_occurrences'),recovery_before=before,profile=profile,
            boundary=json.loads((Path(run.app['workdir'])/'model-boundary.json').read_text()),
            recovered_after_sigkill=recover,fixtures=['unused web responses','unused history','synthetic corpus and attention clock'],
            invocation_limit=turns,output_token_reservation=6000*turns,automatic_retries=0)
        (output/'result.json').write_bytes(canonical(result));return result
    finally:
        # Keep evidence even on failure; these fresh inputs are approved synthetic.
        if cfg:
            ch=cfg['channel']
            log=run.h.root/'native.log'
            if log.exists():(output/'native.log').write_bytes(log.read_bytes())
            status=Path(run.app['status_file'])
            if status.exists():(output/'status.json').write_bytes(status.read_bytes())
            for name,path in [('provider',cfg['completion_root']/'model.sqlite'),('application',Path(run.h.client['database']))]:
                try:rows=ch.rows(path,'model_calls' if name=='provider' else 'app_model_calls')
                except Exception:rows=[]
                (output/(name+'-calls.json')).write_bytes(canonical(rows))
            (output/'channel-inputs.json').write_bytes(canonical(ch.rows(run.h.client['database'],'app_channel_inputs')))
            ch.close()
        run.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approve-local-generation',action='store_true')
    p.add_argument('--approved-calls',type=int,choices=[6,12],required=True)
    p.add_argument('--prior-campaign',type=Path)
    p.add_argument('--cpu-deadline',action='store_true')
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    require(a.approve_local_generation,'UNAUTHORIZED');require(not a.out.exists(),'CONFLICT');a.out.mkdir(parents=True,mode=0o700)
    spent=0
    if a.prior_campaign:
        rows=json.loads((a.prior_campaign/'provider-calls.json').read_text())
        require(len(rows)==1 and rows[0]['reserved']==1 and rows[0]['response'] is None,'CONFLICT');spent=1
    profile=c.CPU_PROFILE if a.cpu_deadline else c.PROFILE
    require(not spent or a.cpu_deadline,'UNSUPPORTED_PROFILE')
    count=a.approved_calls-spent
    cases=[]
    placements=[('local','local',False),('network','local',True),('network','network',False),('local','network',False),('network','network',True),('local','local',False)]
    for placement,mailbox,recover in placements:
        if count==0:break
        turns=min(2,count);cases.append([placement,mailbox,recover,turns]);count-=turns
    require(count==0,'OVERLOADED')
    plan=dict(backend=c.MODEL,model_digest=c.MODEL_DIGEST,approved_calls=a.approved_calls,prior_spent_calls=spent,planned_calls=a.approved_calls-spent,
        prior_campaign=None if not a.prior_campaign else str(a.prior_campaign),profile=profile,
        per_call_output_tokens=6000,per_input_deadline_ms=c.deadline_limit(profile),load_timeout_seconds=600 if a.cpu_deadline else 120,
        automatic_retries=0,started_ms=time.time_ns()//1_000_000,
        cases=cases)
    (a.out/'plan.json').write_bytes(canonical(plan))
    lock=runtime_lock(a.out);OllamaCompletion(lock).readiness()
    # A single bounded empty-chat load before any channel input is accepted.
    # Verified source returns done_reason=load without token generation.
    loaded=exchange('/api/chat',dict(model=c.MODEL,messages=[],stream=False,think=False,truncate=False,options=dict(c.OPTIONS)),timeout=plan['load_timeout_seconds'])
    require(loaded.get('done') is True and loaded.get('done_reason')=='load','NOT_AVAILABLE')
    (a.out/'readiness.json').write_bytes(canonical({k:v for k,v in loaded.items() if k!='message'}))
    corpus=json.loads((ROOT/'artifacts/s07/corpus.json').read_text())
    for index,(placement,mailbox,recover,turns) in enumerate(plan['cases']):
        root=a.out/str(index+1);root.mkdir(mode=0o700)
        # No automatic new identity, repeat, or changed backend after failure.
        print(json.dumps(dict(case=index+1,placement=placement,mailbox=mailbox,recover=recover,calls=turns)),flush=True)
        case(corpus,root,placement,mailbox,recover,profile=profile,turns=turns)
        print(json.dumps(dict(case=index+1,status='PASS')),flush=True)
    (a.out/'complete.json').write_bytes(canonical(dict(completed_cases=len(cases),live_calls=a.approved_calls-spent,total_spent_calls=a.approved_calls)))


if __name__=='__main__':main()
