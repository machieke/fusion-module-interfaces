"""Generated M3 action on verified Hive Programs 0.1; no shared private payloads."""
from dataclasses import asdict
from contextlib import closing
import json
import os
from pathlib import Path
import signal
import sqlite3
from fusion.contracts import ContractError, canonical, digest, require
from fusion.cognition import open_cognition
from fusion.ports import InferenceRequest, WorkBudget, Mutation
from fusion import delivery_contracts as delivery
from integration.m3_scenario import run_generated


def describe():
    return {'contract':'0.1','kinds':[{'id':'inference','label':'Private generated inference','role':'assessment'}],
        'relations':[],'actions':[{'id':'infer-generated','label':'Run bounded generated inference',
        'params':{'seed':'integer 0..4294967295','prefer':'a or b; generated STI preference',
                  'deadline_ms':'absolute Unix milliseconds; preserved on replay'}},
        {'id':'reconcile-generated','label':'Observe bounded delivery closure',
         'params':{'original_command':'original generated action key','limit':'integer 1..16'}}]}


def view(ctx,focus=None,stage=None):return {'revision':'1','items':[],'links':[]}


def act(ctx,action,items,params):
    try:
        actor,command=ctx.actor or {},ctx.command or {}
        require(not ctx.read_only and actor.get('kind')=='person' and actor.get('route')=='operator' and actor.get('swarm_id')==ctx.swarm_id,'UNAUTHORIZED')
        require(action in ('infer-generated','reconcile-generated') and not items)
        if action=='infer-generated':
            require(set(params)<={'seed','prefer','deadline_ms','base_revision'} and type(params.get('seed')) is int and 0<=params['seed']<=4294967295)
            require(params.get('prefer') in ('a','b') and type(params.get('deadline_ms')) is int and 0<params['deadline_ms']<2**53 and params.get('base_revision') is None)
        else:
            require(set(params)<={'original_command','limit','base_revision'} and type(params.get('original_command')) is str and
                    1<=len(params['original_command'])<=120 and type(params.get('limit')) is int and 1<=params['limit']<=16 and params.get('base_revision') is None)
        key=command.get('idempotency_key');require(type(key) is str and 1<=len(key)<=120)
        config=json.loads(Path(os.environ['FUSION_M3_HIVE_CONFIG']).read_text())
        grants=[g for g in config['grants'] if g['principal']==actor.get('principal') and g['swarm']==ctx.swarm_id]
        require(len(grants)==1,'UNAUTHORIZED');grant=grants[0]
        def hook(stage):
            if config.get('test_pause_at')==stage:
                Path(config['test_marker']).write_text(stage);os.kill(os.getpid(),signal.SIGSTOP)
        modules=open_cognition(config['private_config'],grant['credential'],grant['scope'],hook=hook)
        original_command=key if action=='infer-generated' else params['original_command']
        identity=digest(canonical([actor['principal'],ctx.swarm_id,original_command]))
        if modules.relay is not None:
            # Adapter-owned mapping of authenticated public command to private prepared request.
            journal=modules.root/'hive-inference.sqlite'
            def connect():
                db=sqlite3.connect(journal);db.execute('PRAGMA journal_mode=WAL');db.execute('PRAGMA synchronous=FULL')
                db.execute('CREATE TABLE IF NOT EXISTS prepared(id TEXT PRIMARY KEY,value TEXT)');return db
            def prepared(value):
                record={'request':asdict(value['request']),'episode':value['episode']}
                with closing(connect()) as db,db:
                    row=db.execute('SELECT value FROM prepared WHERE id=?',(identity,)).fetchone()
                    if row:require(json.loads(row[0])==record,'CONFLICT')
                    else:db.execute('INSERT INTO prepared VALUES(?,?)',(identity,canonical(record).decode()))
            if action=='infer-generated':
                private=run_generated(modules,grant['scope'],identity,params['seed'],params['prefer'],params['deadline_ms'],prepared=prepared)
                progress=modules.controller.readProgress(private['request']);episode=private['episode']
            else:
                with closing(connect()) as db:row=db.execute('SELECT value FROM prepared WHERE id=?',(identity,)).fetchone()
                require(row is not None,'NOT_FOUND');record=json.loads(row[0]);value=record['request']
                request=InferenceRequest(**{**value,'command':Mutation(**value['command']),'budget':WorkBudget(**value['budget'])})
                progress=modules.controller.reconcile(Mutation(grant['scope'],'hive-reconcile/'+key),request,params['limit']);episode=record['episode']
            result=progress['execution'];pending=len(modules.episodes.pendingEvidence(episode,16))
            return {'status':'done','receipt':{'state':'committed','id':key},'detail':{
                'scenario':'generated-private-m3','profile':delivery.CONFIG,'execution':{'status':result['status'],'reason':result['reason']},
                'counts':result['counts'],'remaining':result['remaining'],'result_admissions':result['counts']['unique_admissions'],
                'evidence':{'pending':pending,'state':'pending' if pending else 'settled'},
                'feedback':progress['closure'],'closure_version':progress['version'],'derived_observations':0}}
        require(action=='infer-generated','UNSUPPORTED_PROFILE')
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
