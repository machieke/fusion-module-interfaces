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


def approve(path,approval,*,assets=True):
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
    for item in value['sources']+value['bindings']+(value['runtime_required_files'] if assets else []):
        require(Path(item['path']).is_file() and historical.sha(item['path'])==item['sha256'],'CONFLICT')
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
    return dict(campaign_id=value['campaign_id'],freeze=value['freeze'],state='DISABLED_PENDING_NEW_AUTHORIZATION',runtime_availability='NOT_CHECKED',live_allowance=0,slots=[dict(name=s['name'],state='UNRESERVED') for s in value['slots']])




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
    return dict(spent=sorted(reserved),claim_records=sorted(claims),reservation_without_claim=sorted(reserved-set(claims)),captured=[r['id'] for r in rows if r['response'] is not None],backend_calls='UNKNOWN_WITHOUT_BACKEND_OBSERVATION',refunded=0)


def serve(manifest,approval,component):
    # The independent entrypoint validates authority before host configuration,
    # sockets, backend construction, work reservations or runtime activity.
    value,_=approve(manifest,approval)
    require(str(Path(component))==value['component_configuration'],'CONFLICT')
    def configure(path):
        value,_=approve(manifest,approval,assets=False)
        settings=json.loads(Path(path).read_bytes())
        require(settings['role']=='fusion-model' and settings['workflow']['mode']=='live','UNSUPPORTED_PROFILE')
        require(settings['service_composition']=='neoclaw-model-channel-services/1' and settings['state']=='/state','UNSUPPORTED_PROFILE')
        cfg=json.loads(Path(value['owner_configuration']).read_bytes())
        require(cfg['model_completion']['database']=='/state/model.sqlite','UNSUPPORTED_PROFILE')
        require(set(cfg['principals'])=={'M'} and cfg['principals']['M']['credential_secret']=='caller-token','UNAUTHORIZED')
        cfg['principals']['M'].pop('credential_secret')
        cfg['principals']['M']['credential']=Path('/secrets/caller-token').read_text().strip()
        state=Path('/state');run=Path('/run/fusion');run.mkdir(exist_ok=True)
        historical.atomic(run/'owner.json',cfg)
        return settings,cfg,state,run
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
    env=dict(PATH='/usr/bin:/bin',HOME='/tmp',OLLAMA_HOST='127.0.0.1:48173',OLLAMA_MODELS=runtime['asset_root'],OLLAMA_NO_CLOUD='true',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_NUM_PARALLEL='1',OLLAMA_KEEP_ALIVE='10m',OLLAMA_CONTEXT_LENGTH='32768')
    os.execve(runtime['binary'],[runtime['binary'],'serve'],env)


def main():
    import argparse
    p=argparse.ArgumentParser(description='Offline inspection or independently approved future connection.')
    p.add_argument('plan');p.add_argument('--approval');p.add_argument('--component')
    group=p.add_mutually_exclusive_group();group.add_argument('--serve',action='store_true');group.add_argument('--runtime',action='store_true');a=p.parse_args()
    if a.serve:serve(a.plan,a.approval,a.component)
    elif a.runtime:runtime(a.plan,a.approval)
    else:print(json.dumps(inspect(a.plan),indent=2))
if __name__=='__main__':main()
