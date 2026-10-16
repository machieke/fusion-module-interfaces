"""Generated M3 action on verified Hive Programs 0.1; no shared private payloads."""
import json
import os
from pathlib import Path
import signal
import sqlite3
from fusion.contracts import ContractError, canonical, digest, require
from fusion.cognition import open_cognition
from integration.m3_scenario import run_generated


def describe():
    return {'contract':'0.1','kinds':[{'id':'inference','label':'Private generated inference','role':'assessment'}],
        'relations':[],'actions':[{'id':'infer-generated','label':'Run bounded generated inference',
        'params':{'seed':'integer 0..4294967295','prefer':'a or b; generated STI preference',
                  'deadline_ms':'absolute Unix milliseconds; preserved on replay'}}]}


def view(ctx,focus=None,stage=None):return {'revision':'1','items':[],'links':[]}


def act(ctx,action,items,params):
    try:
        actor,command=ctx.actor or {},ctx.command or {}
        require(not ctx.read_only and actor.get('kind')=='person' and actor.get('route')=='operator' and actor.get('swarm_id')==ctx.swarm_id,'UNAUTHORIZED')
        require(action=='infer-generated' and not items)
        require(set(params)<={'seed','prefer','deadline_ms','base_revision'} and type(params.get('seed')) is int and 0<=params['seed']<=4294967295)
        require(params.get('prefer') in ('a','b') and type(params.get('deadline_ms')) is int and 0<params['deadline_ms']<2**53 and params.get('base_revision') is None)
        key=command.get('idempotency_key');require(type(key) is str and 1<=len(key)<=120)
        config=json.loads(Path(os.environ['FUSION_M3_HIVE_CONFIG']).read_text())
        grants=[g for g in config['grants'] if g['principal']==actor.get('principal') and g['swarm']==ctx.swarm_id]
        require(len(grants)==1,'UNAUTHORIZED');grant=grants[0]
        def hook(stage):
            if config.get('test_pause_at')==stage:
                Path(config['test_marker']).write_text(stage);os.kill(os.getpid(),signal.SIGSTOP)
        modules=open_cognition(config['private_config'],grant['credential'],grant['scope'],hook=hook)
        identity=digest(canonical([actor['principal'],ctx.swarm_id,key]))
        private=run_generated(modules,grant['scope'],identity,params['seed'],params['prefer'],params['deadline_ms'])
        result=private['result']
        return {'status':'done' if result['status']=='complete' else 'error',
            'receipt':{'state':'committed' if result['status']=='complete' else 'pending','id':key},
            'detail':{'scenario':'generated-private-m3','reason':result['reason'],'counts':result['counts'],
                      'remaining':result['remaining'],'derived_observations':0}}
    except ContractError as error:
        return {'status':'error' if error.wire()['retryable'] else 'refused','detail':{'error':error.wire()}}
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        return {'status':'error','detail':{'error':ContractError('NOT_AVAILABLE').wire()}}
