"""Finite LIVE S07 recipe. Operator must explicitly authorize local generation.

No response is resampled. A failed or uncertain case terminates this campaign.
"""
import argparse
import json
from pathlib import Path
import signal
import time
from fusion import model_contracts as c
from fusion.adapters.ollama_completion import OllamaCompletion,exchange
from fusion.contracts import canonical,require
from .controlled_run import ControlledRun
from .model_composition import configure,runtime_lock,INPUTS,OUTPUT
from .embedding_run import start
from .channel_composition import ROOT


def case(corpus,output,placement,mailbox,recover=False):
    run=ControlledRun('local',['',''],search={'boundary':'recorded-response'});cfg=None
    try:
        cfg=configure(run,corpus,placement,mailbox,runtime_lock=runtime_lock(output));ch=cfg['channel']
        if recover:run.app['pause_at']='after_model_application_capture';run.save()
        run.operator();ch.start_bridge();ch.start_peer();p=start(run)
        for text in INPUTS:ch.send(text)
        before=None
        if recover:
            run.h.wait_file(run.app['failpoint_marker'],p,seconds=45)
            before=ch.rows(run.h.client['database'],'app_model_calls')
            run.kill(p);require(p.returncode==-signal.SIGKILL,'NOT_AVAILABLE')
            run.app.pop('pause_at');run.save();p=start(run)
        p.wait(timeout=75)
        require(run.finish(p)==(0,{'status':'BOUNDED_STOP'}),'NOT_AVAILABLE')
        until=time.monotonic()+5
        while time.monotonic()<until and not any(' :'+OUTPUT in x.get('received','') for x in ch.traffic()):time.sleep(.05)
        require(any(' :'+OUTPUT in x.get('received','') for x in ch.traffic()),'NOT_AVAILABLE')
        rows=ch.rows(run.h.client['database'],'app_model_calls');provider=ch.rows(cfg['completion_root']/'model.sqlite','model_calls')
        require(len(rows)==len(provider)==2 and all(r['reserved']==1 for r in provider),'NOT_AVAILABLE')
        if before:
            for old,new in zip(before,rows):
                require(all(old[k]==new[k] for k in ('id','intent','context_view','result')),'CONFLICT')
        # Assert the next prompt contains the native tool result from this run.
        turns=run.rows('app_turns');second=json.loads(rows[1]['intent'])['native_prompt']
        require(turns[0]['projection'] in second and 'COMMAND_RETURN' in turns[0]['projection'],'NOT_AVAILABLE')
        result=dict(classification='REAL_OLLAMA_GENERATION',model_placement=placement,mailbox_placement=mailbox,
            same_host=True,model_calls=rows,provider_calls=provider,turns=turns,traffic=ch.traffic(),
            boundary=json.loads((Path(run.app['workdir'])/'model-boundary.json').read_text()),
            recovered_after_sigkill=recover,fixtures=['unused web responses','unused history','synthetic corpus and attention clock'],
            invocation_limit=2,output_token_reservation=12000,automatic_retries=0)
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
            ch.close()
        run.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--approve-local-generation',action='store_true')
    p.add_argument('--approved-calls',type=int,choices=[6,12],required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    require(a.approve_local_generation,'UNAUTHORIZED');require(not a.out.exists(),'CONFLICT');a.out.mkdir(parents=True,mode=0o700)
    plan=dict(backend=c.MODEL,model_digest=c.MODEL_DIGEST,approved_calls=a.approved_calls,planned_calls=6,
        per_call_output_tokens=6000,per_input_deadline_ms=30000,automatic_retries=0,started_ms=time.time_ns()//1_000_000,
        cases=[['local','local',False],['network','local',True],['network','network',False]])
    (a.out/'plan.json').write_bytes(canonical(plan))
    lock=runtime_lock(a.out);OllamaCompletion(lock).readiness()
    # A single bounded empty-chat load before any channel input is accepted.
    # Verified source returns done_reason=load without token generation.
    loaded=exchange('/api/chat',dict(model=c.MODEL,messages=[],stream=False,think=False,truncate=False,options=dict(c.OPTIONS)),timeout=120)
    require(loaded.get('done') is True and loaded.get('done_reason')=='load','NOT_AVAILABLE')
    (a.out/'readiness.json').write_bytes(canonical({k:v for k,v in loaded.items() if k!='message'}))
    corpus=json.loads((ROOT/'artifacts/s07/corpus.json').read_text())
    for index,(placement,mailbox,recover) in enumerate(plan['cases']):
        root=a.out/str(index+1);root.mkdir(mode=0o700)
        # No automatic new identity, repeat, or changed backend after failure.
        case(corpus,root,placement,mailbox,recover)
    (a.out/'complete.json').write_bytes(canonical(dict(completed_cases=3,live_calls=6)))


if __name__=='__main__':main()
