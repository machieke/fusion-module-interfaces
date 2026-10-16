"""Native Programs 0.1 dispatch; private operator requests, counts-only receipts."""
import json
import os
from pathlib import Path
import signal
import sqlite3
from fusion.contracts import ContractError,canonical,digest,require,label
from fusion.lookup_composition import open_lookup
from fusion.lookup_contracts import AttributeQuery,query
from fusion.lookup import LookupConsumer
from fusion.ports import Mutation

def describe():
    return {'contract':'0.1','kinds':[{'id':'lookup','label':'Private lookup','role':'assessment'}],
            'relations':[],'actions':[{'id':'lookup','label':'Retrieve a bounded private information request',
                'params':{'request':'opaque operator-registered request label; no answer references'}}]}

def view(ctx,focus=None,stage=None):return {'revision':'1','items':[],'links':[]}

def act(ctx,action,items,params):
    try:
        actor,command=ctx.actor or {},ctx.command or {}
        require(not ctx.read_only and actor.get('kind')=='person' and actor.get('route')=='operator' and actor.get('swarm_id')==ctx.swarm_id,'UNAUTHORIZED')
        require(action=='lookup' and not items and type(params) is dict and set(params)<={'request','base_revision'} and params.get('base_revision') is None)
        require(label(params.get('request')));key=command.get('idempotency_key');require(label(key) and len(key)<=120)
        config=json.loads(Path(os.environ['FUSION_M5_HIVE_CONFIG']).read_text())
        grants=[g for g in config['grants'] if g['principal']==actor.get('principal') and g['swarm']==ctx.swarm_id]
        require(len(grants)==1,'UNAUTHORIZED');grant=grants[0]
        # Values are bounded queries + source barriers, never expected answers.
        require(params['request'] in grant['requests'],'UNAUTHORIZED')
        request=query(AttributeQuery(**grant['requests'][params['request']]))
        require(request.scope_ref==grant['scope'] and request.cursor is None,'UNAUTHORIZED')
        def hook(stage):
            if config.get('test_pause_at')==stage:
                Path(config['test_marker']).write_text(stage);os.kill(os.getpid(),signal.SIGSTOP)
        modules=open_lookup(config['private_config'],grant['credential'],grant['scope'],hook=hook)
        consumer=LookupConsumer(modules.root/'hive-lookup.sqlite',modules.atoms,modules.relations,modules.search,modules.access,modules.selections,hook)
        identity=digest(canonical([actor['principal'],ctx.swarm_id,key]))
        result=consumer.lookup(Mutation(grant['scope'],identity),request)
        return {'status':'done','receipt':{'state':'committed','id':key},'detail':{
            'profile':request.profile,'roots':len(result['roots']),'relations':len(result['relations']),
            'payloads':len(result['documents']),'complete':True,'hop_limit':result['hop_limit']}}
    except ContractError as error:
        return {'status':'error' if error.wire()['retryable'] else 'refused','detail':{'error':error.wire()}}
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):
        return {'status':'error','detail':{'error':ContractError('NOT_AVAILABLE').wire()}}
