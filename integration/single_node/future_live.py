"""Offline connection for a NEW provider-owned, two-slot k3s experiment.

Not selected by the recorded chart. No effects occur at import or plan inspection.
The old four-slot host campaign contract and its spent ledgers remain unchanged.
"""
from dataclasses import asdict
import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.neoclaw import retrieval_campaign as historical

SCHEMA='single-node-model-channel-live-plan/1'


def authority(path,approval):
    require(not Path('/state/restore-fence.json').exists(),'UNAUTHORIZED')
    raw=Path(path).read_bytes();value=json.loads(raw)
    require(raw==canonical(value) and value['schema']==SCHEMA,'UNSUPPORTED_PROFILE')
    checksum=digest(raw);require(Path(path).with_suffix('.sha256').read_text().strip()==checksum,'CONFLICT')
    require(value['kind']=='live' and value['freeze']=='COMPLETE','NOT_AVAILABLE')
    require(approval is not None and Path(approval).is_file(),'UNAUTHORIZED')
    authority=json.loads(Path(approval).read_bytes())
    require(authority.get('authority')=='EXPLICIT_USER_APPROVAL' and authority.get('user_statement'),'UNAUTHORIZED')
    require(authority.get('campaign_id')==value['campaign_id'] and authority.get('manifest_sha256')==checksum,'UNAUTHORIZED')
    require(authority.get('slots')==[s['name'] for s in value['slots']] and authority.get('max_generations')==2,'UNAUTHORIZED')
    now=time.time_ns()//1000000
    require(authority['not_before_ms']<=now<authority['expires_ms'] and 0<authority['expires_ms']-authority['not_before_ms']<=3600000,'UNAUTHORIZED')
    require(len(value['slots'])==2 and [s['slot'] for s in value['slots']]==[1,2],'UNSUPPORTED_PROFILE')
    require(value['provider_state']=='/state/live-campaign' and value['runtime_lock']['path'].startswith('/opt/generative/'),'UNSUPPORTED_PROFILE')
    require(value['campaign_id']!='retrieval-grounded-20261026-02','UNAUTHORIZED')
    return value,checksum


def approve(path,approval,*,assets=True):
    value,checksum=authority(path,approval)
    for item in value['sources']+value['bindings']+(value['runtime_required_files'] if assets else []):
        file=Path(item['path'])
        if item.get('directory') is True:
            require(file.is_dir() and not file.is_symlink(),'CONFLICT')
        elif 'symlink' in item:
            require(file.is_symlink() and str(file.readlink())==item['symlink'] and file.is_file(),'CONFLICT')
        else:
            # Projected Kubernetes ConfigMap bindings are symlinks through
            # ..data. Their resolved exact bytes are the approved binding.
            require(file.is_file() and historical.sha(file)==item['sha256'],'CONFLICT')
    return value,checksum


def claim(path,approval,accepted):
    value,checksum=approve(path,approval,assets=False)
    slot=next((s for s in value['slots'] if s['id']==accepted['id']),None)
    require(slot is not None and (slot['session'],slot['slot'])==(accepted['session'],accepted['slot']),'UNAUTHORIZED')
    # Same write-once/fsynced claim primitive as the host campaign. Colocated
    # with ModelService on its single-writer PVC; never mounted in the caller.
    with historical.locked(value['provider_state']) as root:
        claims=root/'claims';claims.mkdir(mode=0o700,exist_ok=True)
        require(set(p.stem for p in claims.glob('*.json'))<={s['id'] for s in value['slots']},'CONFLICT')
        file=claims/(accepted['id']+'.json');require(not file.exists(),'OVERLOADED')
        record=dict(campaign_id=value['campaign_id'],manifest_sha256=checksum,id=accepted['id'],intent_sha256=digest(canonical(accepted)),deadline_ms=accepted['deadline_ms'])
        historical.atomic(file,record)


class Backend:
    """Future ModelPorts backend; guard precedes constructor/readiness/evaluation."""
    def __init__(self,manifest,approval):
        self.manifest,self.approval=manifest,approval
        value,_=approve(manifest,approval)
        from fusion.adapters.ollama_completion import OllamaCompletion
        self.backend=OllamaCompletion(value['runtime_lock'])
    def complete(self,accepted):
        approve(self.manifest,self.approval,assets=False)
        claim(self.manifest,self.approval,asdict(accepted))
        return self.backend.complete(accepted)


def inspect(path):
    value=json.loads(Path(path).read_bytes())
    ledger=Path(path).parent/'execution-ledger.json'
    return dict(campaign_id=value['campaign_id'],freeze=value['freeze'],runtime_availability='NOT_CHECKED',authority='immutable plan grants no live allowance',planned_slots=[s['name'] for s in value['slots']],execution=json.loads(ledger.read_bytes()) if ledger.is_file() else 'UNKNOWN: execution ledger not provided')




def connect(manifest,approval,owner_config,hook=lambda _:None):
    """Provider startup connection after separately supplied, frozen approval."""
    value,_=approve(manifest,approval)
    cfg=json.loads(Path(owner_config).read_bytes())['model_completion']
    require(cfg['runtime_lock']==value['runtime_lock'] and cfg['max_calls']==2,'CONFLICT')
    require(cfg['sessions']==[value['slots'][0]['session']],'CONFLICT')
    from fusion.retrieval_services import ModelPorts
    return ModelPorts(owner_config,Backend(manifest,approval),hook)


def projection(manifest,owner_config):
    """Read-only union: owner reservations remain spent even before a claim."""
    value=json.loads(Path(manifest).read_bytes())
    from fusion.model_service import ModelService
    rows=ModelService.inspect(owner_config)
    claims={p.stem:json.loads(p.read_bytes()) for p in (Path(value['provider_state'])/'claims').glob('*.json')}
    slots={s['id']:s for s in value['slots']};require(set(claims)<=set(slots),'CONFLICT')
    for row in rows:
        require(row['id'] in slots and row['session']==slots[row['id']]['session'],'CONFLICT')
        if row['id'] in claims:require(claims[row['id']]['intent_sha256']==digest(row['intent'].encode()),'CONFLICT')
    reserved={r['id'] for r in rows if r['reserved']}
    require(set(claims)<=reserved,'CONFLICT')
    captured=[r['id'] for r in rows if r['response'] is not None]
    usage={r['id']:json.loads(r['response'])['usage'] for r in rows if r['response'] is not None}
    return dict(spent=sorted(reserved),claim_records=sorted(claims),reservation_without_claim=sorted(reserved-set(claims)),captured=captured,provider_usage=usage,backend_calls=len(captured) if set(captured)==reserved else 'UNKNOWN_WITHOUT_BACKEND_OBSERVATION',refunded=0)


def serve(manifest,approval,component):
    # The independent entrypoint validates authority before host configuration,
    # sockets, backend construction, work reservations or runtime activity.
    value,_=approve(manifest,approval)
    require(str(Path(component))==value['component_configuration'],'CONFLICT')
    def configure(path):
        value,_=approve(manifest,approval,assets=False)
        settings=json.loads(Path(path).read_bytes())
        require(settings['role']=='fusion-model' and settings['workflow']['mode']=='live','UNSUPPORTED_PROFILE')
        require(settings['workflow']['liveEnabled'] is True,'UNAUTHORIZED')
        from .workflow_configure import configure as selected
        return selected(settings,live_authority=(value,json.loads(Path(approval).read_bytes())))
    import sys
    from .server import main
    sys.argv=[sys.argv[0],component]
    main(config_resolver=configure,model_factory=lambda path,hook:connect(manifest,approval,path,hook))


def runtime(manifest,approval):
    value,_=approve(manifest,approval)
    lock=value['runtime_lock'];require(historical.sha(lock['path'])==lock['sha256'],'CONFLICT')
    runtime=json.loads(Path(lock['path']).read_bytes())
    require(runtime['port']==48173 and runtime['asset_root']=='/opt/generative/models','UNSUPPORTED_PROFILE')
    # Relocation of the published isolated recipe. No readiness generation,
    # download, model pull, warm-up, or arbitrary operator command dispatch.
    from fusion.adapters.ollama_completion import BINARY_SHA256
    require(runtime['binary']=='/opt/generative/bin/ollama' and historical.sha(runtime['binary'])==BINARY_SHA256,'CONFLICT')
    import os
    env=dict(PATH='/usr/bin:/bin',HOME='/tmp',OLLAMA_HOST='127.0.0.1:48173',OLLAMA_MODELS=runtime['asset_root'],OLLAMA_NO_CLOUD='true',OLLAMA_NOPRUNE='true',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_NUM_PARALLEL='1',OLLAMA_KEEP_ALIVE='10m',OLLAMA_CONTEXT_LENGTH='32768')
    os.execve(runtime['binary'],[runtime['binary'],'serve'],env)



def supervised(manifest,approval,component):
    """Approval-first process tree; no child or socket exists before validation.

    One provider owns the PVC. The runtime child has no journal protocol and
    listens only on pod loopback. Expiry, parent termination or either child exit
    stops both children. Restart can observe captures but cannot refund claims.
    """
    value,_=approve(manifest,approval)
    require(str(Path(component))==value['component_configuration'],'CONFLICT')
    import os,signal,subprocess,sys,threading
    stop=threading.Event();children=[]
    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    expiry=json.loads(Path(approval).read_bytes())['expires_ms']
    try:
        base=[sys.executable,'-m','integration.single_node.future_live',manifest,'--approval',approval]
        children.append(subprocess.Popen(base+['--runtime'],start_new_session=True))
        children.append(subprocess.Popen(base+['--serve','--component',component],start_new_session=True))
        while not stop.wait(.2):
            if time.time_ns()//1000000>=expiry or any(p.poll() is not None for p in children):break
    finally:
        for p in children:
            if p.poll() is None:os.killpg(p.pid,signal.SIGTERM)
        until=time.monotonic()+5
        for p in children:
            try:p.wait(timeout=max(.1,until-time.monotonic()))
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()


def main():
    import argparse
    p=argparse.ArgumentParser(description='Offline inspection or independently approved future connection.')
    p.add_argument('plan');p.add_argument('--approval');p.add_argument('--component')
    group=p.add_mutually_exclusive_group();group.add_argument('--serve',action='store_true');group.add_argument('--runtime',action='store_true');group.add_argument('--supervise',action='store_true');a=p.parse_args()
    if a.supervise:supervised(a.plan,a.approval,a.component)
    elif a.serve:serve(a.plan,a.approval,a.component)
    elif a.runtime:runtime(a.plan,a.approval)
    else:print(json.dumps(inspect(a.plan),indent=2))
if __name__=='__main__':main()
