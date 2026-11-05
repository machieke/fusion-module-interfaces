"""Opt-in writable activation of a current, drained synthetic copy.

Historical journal rows stay byte/semantically intact. A separate local fence
indexes old identities and sessions; current external writer authority is still
mandatory. Only new generation session templates execute. Old model/send/task/
chain requests remain observation-only, including uncertain effects.
"""
import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.pilot_writer_fence import PROFILE,check,hash_value
from .configure import write

MARKER='pilot-activation.json'
TABLE='pilot_historical_sessions'
ID_KEYS={'id','identity','session','session_id','occurrence','occurrence_id','request_id','idempotency_key','allocation_id','call_id','key',
         'operation_id','transaction_id','message_id','input_id','evidence_id','adjustment_id','delivery_id','source_id'}
# Exemptions are tied to the installed route AND interface. An operation named
# "query", "published" or "observe" on another surface never bypasses the old
# identity fence. Final descriptor/profile validation and current authority still
# belong to the selected owner port.
READ_PORTS={
 '/preview/session':{None:{'capacity','list','binding','observe'}},
 '/preview/providers':{None:{'inspect'}},
 '/preview/model':{'model.inference':{'observe','authorize'}},
 '/memory-source':{None:{'get','head','readCommits','observe'}},
 '/s03-read':{'atom.storage':{'get','getMany','head','readCommits'},'search':{'query','authorize-ready'}},
 '/s03-append':{'atom.storage':{'observe'}},
 '/preview/memory':{'memory.lifecycle':{'head','readEvents','activeSet','disclose'},
                    'search':{'published','current','ready','query','authorize'}},
 '/preview/facets':{'execution.workspace':{'read','version'},'episodic.memory':{'historySnapshot','readHistory'},
                   'relations':{'getRelation','outgoing','incoming'}},
 '/reference-cognition':{'atom.storage':{'get','getMany','availability','head','readCommits','capacity','observe','observeArchive'},
    'episodic.memory':{'readEpisode','readEvidence','pendingEvidence','readOccurrence'},
    'belief.revision':{'readBelief','observeDecision','readDecisions'},'relations':{'getRelation','outgoing','incoming'},
    'search':{'query'}},
 '/preview/search-maintenance':{None:{'observeRepair','observeCleanup'}},
}
MAX_IDENTITIES=65536


def strings(value, found, depth=0):
    require(depth<=48 and len(found)<=MAX_IDENTITIES,'OVERLOADED')
    if type(value) is dict:
        # References identify retained payloads, not executable occurrences. New
        # work may lawfully hydrate old immutable payloads.
        if set(value)=={'scope_ref','id','revision','digest'}:return
        for key,v in value.items():
            if key in ID_KEYS and type(v) is str and 0<len(v)<=256:found.add(digest(v.encode()))
            strings(v,found,depth+1)
    elif type(value) is list:
        for v in value:
            if type(v) is str and 0<len(v)<=256:found.add(digest(v.encode()))
            strings(v,found,depth+1)
    elif type(value) is str and value[:1] in ('{','[') and len(value)<=131072:
        try:strings(json.loads(value),found,depth+1)
        except ValueError:pass


def install(root,role,checkpoint,generation):
    import fcntl
    root=Path(root)
    with (root/'owner.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return _install(root,role,checkpoint,generation)


def _install(root,role,checkpoint,generation):
    """Owner-local, offline operation on a separately restored disposable copy."""
    root=Path(root);hash_value(checkpoint);require(type(generation) is int and 2<=generation<=65,'INVALID_ARGUMENT')
    fence=json.loads((root/'restore-fence.json').read_bytes())
    seal=json.loads((root/'owner-seal.json').read_bytes())
    require(fence['mode']=='READ_ONLY_RECONCILIATION' and fence['role']==role and fence['external_effect_authority'] is False and
            seal['scope'].startswith('synthetic-') and seal['role']==role and seal['composition']=='omega-single-node-sustained-preview/1','UNAUTHORIZED')
    workspaces=list(root.rglob('workspace.sqlite'))
    if workspaces:
        require(role=='fusion-execution' and workspaces==[root/'preview-facets'/'workspace.sqlite'] and
                fence.get('original_scope')==seal['scope'] and type(fence.get('namespace')) is str and
                fence['namespace'].startswith('omega-ref-') and fence['namespace']!='omega-demo','UNAUTHORIZED')
        hash_value(fence.get('backup_manifest_sha256'))
    if (root/MARKER).exists():
        old=json.loads((root/MARKER).read_bytes())
        require(old['profile']==PROFILE and old['role']==role and old['checkpoint_sha256']==checkpoint and old['generation']==generation,'CONFLICT')
        return dict(profile=PROFILE,role=role,generation=generation,historical_sessions=len(old['historical_sessions']),
                    historical_identities=len(old['historical_identity_digests']),marker_sha256=digest(canonical(old)),
                    writable_authority='EXTERNAL_POLICY_REQUIRED')
    identities=set();sessions={};database_hashes={}
    for p in sorted(root.rglob('*')):
        require(not p.is_symlink(),'UNAUTHORIZED')
        if not p.is_file() or p.suffix not in ('.sqlite','.sqlite3','.db'):continue
        wal=Path(str(p)+'-wal');require(not wal.exists() or wal.stat().st_size==0,'NOT_AVAILABLE')
        database_hashes[str(p.relative_to(root))]=digest(p.read_bytes())
        with closing(sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)) as db:
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON')
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
                require(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',table),'UNSUPPORTED_PROFILE')
                if table.startswith('pilot_'):continue
                names=[x[1] for x in db.execute('PRAGMA table_info('+table+')')]
                wanted=[name for name in names if name in ID_KEYS or name in ('intent','result','request','binding','frozen','value')]
                if not wanted:continue
                columns=','.join('"'+name+'"' for name in wanted)
                rows=db.execute('SELECT '+columns+' FROM '+table+' LIMIT 65537').fetchall()
                require(len(rows)<=65536,'OVERLOADED')
                for row in rows:strings(dict(zip(wanted,row)),identities)
            if p.name=='session-inbox.sqlite':
                for row in db.execute('SELECT session,template,frozen FROM sustained_allocations'):
                    sessions[row['session']]=dict(template=row['template'],frozen=row['frozen'])
    require(len(identities)<=MAX_IDENTITIES and len(sessions)<=16,'OVERLOADED')
    value=dict(profile=PROFILE,role=role,checkpoint_sha256=checkpoint,generation=generation,
               historical_identity_digests=sorted(identities),historical_sessions=sorted(sessions),
               imported_database_sha256=database_hashes,old_effects='OBSERVATION_ONLY',old_deadlines='UNCHANGED',
               spent_reservations='UNCHANGED',new_scope=seal['scope'])
    pending=root/'pilot-activation-intent.json'
    if pending.exists():
        prior=json.loads(pending.read_bytes())
        require(all(prior[k]==v for k,v in value.items() if k!='imported_database_sha256'),'CONFLICT')
        value=prior
    else:write(pending,value)
    if workspaces:
        workspace=root/'preview-facets'/'workspace.sqlite'
        require(role=='fusion-execution' and workspaces==[workspace], 'UNAUTHORIZED')
        from fusion.preview_workspace import reattest_root
        receipt=reattest_root(workspace.parent/'workspace',workspace,scope=seal['scope'],checkpoint=checkpoint,generation=generation)
        value['workspace_root_reattestation']=receipt
    if sessions:
        with closing(sqlite3.connect(root/'session-inbox.sqlite')) as db:
            with db:
                db.execute('CREATE TABLE IF NOT EXISTS pilot_historical_sessions(session TEXT PRIMARY KEY,template TEXT NOT NULL,frozen TEXT NOT NULL,generation INTEGER NOT NULL)')
                expected=sorted((s,v['template'],v['frozen'],generation) for s,v in sessions.items())
                db.executemany('INSERT OR IGNORE INTO pilot_historical_sessions VALUES(?,?,?,?)',expected)
                require(db.execute('SELECT * FROM pilot_historical_sessions ORDER BY session').fetchall()==expected,'CONFLICT')
    require(len(canonical(value))<=8*1024*1024,'OVERLOADED');write(root/MARKER,value)
    return dict(profile=PROFILE,role=role,generation=generation,historical_sessions=len(sessions),historical_identities=len(identities),
                marker_sha256=digest(canonical(value)),writable_authority='EXTERNAL_POLICY_REQUIRED')


def selected(settings,root):
    selection=settings.get('preview',{}).get('pilot',{}).get('handover')
    if selection is None:return None
    require(type(selection) is dict and set(selection)=={'profile','checkpoint_sha256','generation'} and selection['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    hash_value(selection['checkpoint_sha256'])
    path=Path(root)/MARKER;require(path.is_file() and not path.is_symlink() and path.stat().st_size<=8*1024*1024,'UNAUTHORIZED')
    marker=json.loads(path.read_bytes())
    require(all(marker[k]==selection[k] for k in selection) and marker['role']==settings['role'] and marker['old_effects']=='OBSERVATION_ONLY','CONFLICT')
    fence=settings['preview']['pilot'].get('writer_fence');require(fence and fence['generation']==selection['generation'],'UNAUTHORIZED')
    check(dict(writer_fence=fence),'writer.start')
    require(not settings['preview'].get('chain',{}).get('enabled') and not settings.get('workflow',{}).get('enabled'),'UNAUTHORIZED')
    require(not settings['preview'].get('tasks',{}).get('enabled'),'UNAUTHORIZED')
    allowed={'pin','unpin','task-context','episodes','remember','query','read-file','write-file','append-file'}
    require(all(set(agent['tools'])<=allowed for agent in settings['preview']['agents'].values()),'UNAUTHORIZED')
    return marker


def historical(db,session):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_historical_sessions'").fetchone():return None
    return db.execute('SELECT * FROM pilot_historical_sessions WHERE session=?',(session,)).fetchone()


def configure(settings,cfg,state,run):
    marker=selected(settings,state)
    if marker is None:return
    cfg['pilot_handover']=dict(profile=PROFILE,generation=marker['generation'],checkpoint_sha256=marker['checkpoint_sha256'])
    cfg.pop('task_ingress',None)
    if 'native_sessions' not in cfg:return
    owner=cfg['native_sessions'];prefix='g'+str(marker['generation'])+'-'
    # This deliberately narrow handover admits only NEW shared synthetic work.
    # Old private selections remain readable, with all original records kept.
    # Admitting two fresh template sets beside both retained sets would exceed
    # the unchanged finite Registry record bound (20 retained +20 new >32).
    require('shared' in owner['allocation']['templates'] and 'shared' in owner['runtime_templates'],'UNSUPPORTED_PROFILE')
    owner['allocation']['templates']={prefix+'shared':owner['allocation']['templates']['shared']}
    owner['runtime_templates']={prefix+'shared':owner['runtime_templates']['shared']}
    # Old allocation templates are reconstructed from unchanged owner rows.
    # Only the newly named templates contain replacement endpoints/runtime pins.
    owner['handover']=cfg['pilot_handover']
    if 'provider_registry' in owner:
        reg=owner['provider_registry'];old={}
        with closing(sqlite3.connect(Path(owner['database']).resolve().as_uri()+'?mode=ro',uri=True)) as db:
            from fusion.provider_retention import present,unpack
            compact=present(db)
            tables={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'integrated_providers' not in tables:
                # A never-used caller has no Registry schema yet. Observing
                # that empty owner must not initialize it, adopt partial state
                # or erase evidence of an earlier allocation.
                require(not any(name.startswith(('integrated_provider','pilot_registry')) for name in tables) and
                    not marker['historical_sessions'] and {'sustained_allocations','preview_sessions'}<=tables,'CONFLICT')
                require(db.execute('SELECT count(*) FROM sustained_allocations').fetchone()[0]==0 and
                    db.execute('SELECT count(*) FROM preview_sessions').fetchone()[0]==0,'CONFLICT')
            else:
                for key,record in db.execute('SELECT id,record FROM integrated_providers'):
                    old[key]=unpack(db,record) if compact else json.loads(record)
        keys=reg['templates']['shared'];new={prefix+k:reg['records'][k] for k in keys}
        # The current generation survives an owner restart. Its already
        # admitted record must be exactly the selected record, and must never
        # alias an imported historical identity. This observes persisted
        # admission only: no probe, receipt rewrite or readiness renewal.
        for key in set(old)&set(new):
            require(digest(key.encode()) not in marker['historical_identity_digests'] and
                    canonical(old[key])==canonical(new[key]),'CONFLICT')
        reg['records']={**old,**new};reg['templates']={prefix+'shared':[prefix+x for x in keys]}
        from fusion.provider_lifecycle import configuration
        configuration(reg)


def request_guard(settings,root,path,request):
    marker=selected(settings,root)
    if marker is None:return
    require(type(request) is dict,'INVALID_ARGUMENT')
    operation=request.get('operation')
    reference=request.get('interface_ref',{});require(type(reference) is dict,'INVALID_ARGUMENT')
    interface=request.get('interface',reference.get('id'))
    require(interface is None or type(interface) is str,'INVALID_ARGUMENT')
    if operation in READ_PORTS.get(path,{}).get(interface,set()):return
    inspected=request
    derived=set()
    if path=='/reference-cognition' and interface=='attention' and operation in ('bind','adjust','scores','rank','observe'):
        # This profile's UUID targets name retained memory data. They are not
        # operation identities: fresh context selection must be able to rank
        # the imported corpus. Validate the exact existing wire shape before
        # excluding only this typed field from the historical-effect scan.
        # The outer request id and the inner bind id remain fenced, including
        # for a retained binding presented to adjust/rank/observe.
        from fusion import promotion_contracts as promotion
        from fusion.cognitive_services import COMPOSITION
        require(set(request)=={'id','composition','scope','interface','selection','operation','args'} and
                request['composition']==COMPOSITION and type(request['args']) is list and len(request['args'])==1,'INVALID_ARGUMENT')
        argument=request['args'][0]
        bound=promotion.request(argument) if operation=='bind' else promotion.binding(argument)['request']
        require(bound['scope']==request['scope'] and bound['selection']==request['selection'],'CONFLICT')
        if operation in ('adjust','scores','rank'):require(bound['kind']==operation,'CONFLICT')
        executable={key:value for key,value in bound.items() if key!='targets'}
        inspected=dict(request,args=[executable if operation=='bind' else dict(argument,request=executable)])
    elif path=='/s03-encode' and interface=='embedding':
        from fusion import embedding_contracts as embedding
        require(type(request.get('intent')) is dict,'INVALID_ARGUMENT')
        embedding.request(request,embedding.descriptor(request['intent'].get('profile')))
        inspected=dict(request,intent={k:v for k,v in request['intent'].items() if k!='text'})
    elif path=='/s03-append' and interface=='atom.storage':
        from fusion import append_contracts as append
        feed_profile=request.get('profile')
        require(feed_profile in (append.a.FEED,append.a.SUSTAINED_FEED),'UNSUPPORTED_PROFILE')
        append.request(request,append.select(append.descriptors(feed_profile),feed_profile))
        inspected=dict(request,intent={k:v for k,v in request['intent'].items() if k not in ('content','helper_input')})
    elif path=='/preview/model' and interface=='model.inference':
        from fusion import preview_model_contracts as recorded,model_contracts as native
        require(type(request.get('intent')) is dict,'INVALID_ARGUMENT')
        contract=recorded if request['intent'].get('profile')==recorded.PROFILE else native
        contract.request(request)
        inspected=dict(request,intent={k:v for k,v in request['intent'].items() if k not in ('native_prompt','messages')})
    elif path=='/preview/facets' and interface=='execution.workspace' and operation in ('write','append'):
        from fusion.preview_ports import COMPOSITION,descriptor
        from fusion.registry import selection_token
        from fusion.preview_tools import Argument
        from fusion.preview_workspace import MAX_COMMANDS
        require(set(request)=={'id','composition','scope','interface','selection','operation','args'} and
                request['composition']==COMPOSITION and request['selection']==selection_token(descriptor(interface)),'UNSUPPORTED_PROFILE')
        args=request['args'];require(type(args) is list and len(args)==4,'INVALID_ARGUMENT')
        identity,name,text,revision=args
        require(type(identity) is str and 1<=len(identity)<=128,'INVALID_ARGUMENT')
        Argument('path','path').validate(name);Argument('content',max_bytes=8192).validate(text)
        require(max(map(len,text.splitlines()),default=0)<=4096 and type(revision) is int and 0<=revision<=MAX_COMMANDS,'INVALID_ARGUMENT')
        # Workspace persists a principal/scope-derived effect key. Compare the
        # actual key for every configured native principal as well as the raw
        # identity. A pending old effect must not escape fencing merely because
        # its journal has not yet stored a receipt containing the raw identity.
        principals={agent.get('principal') for agent in settings['preview']['agents'].values()}
        require(principals and all(type(p) is str and p for p in principals),'UNAUTHORIZED')
        derived={digest(digest(canonical([p,request['scope'],identity])).encode()) for p in principals}
        inspected=dict(request,args=[{'identity':identity}])
    elif path=='/preview/session' and operation=='submit':
        from fusion.sustained_sessions import PROFILE as SESSIONS
        require(set(request)=={'id','profile','operation','body'} and request['profile']==SESSIONS,'UNSUPPORTED_PROFILE')
        body=request['body'];require(type(body) is dict and set(body)=={'session','identity','text','assignment'} and type(body['text']) is str,'INVALID_ARGUMENT')
        require(len(canonical(request))<=16384,'OVERLOADED')
        inspected=dict(request,body={k:v for k,v in body.items() if k!='text'})
    elif (path=='/preview/worker' or path=='/preview/session') and operation=='complete':
        from fusion.resident_workers import PROFILE as WORKER
        from fusion.sustained_sessions import PROFILE as SESSIONS,MAX_INPUTS
        worker=path=='/preview/worker'
        require(set(request)==({'id','profile','operation','session','incarnation','body'} if worker else {'id','profile','operation','body'}) and
                request['profile']==(WORKER if worker else SESSIONS),'UNSUPPORTED_PROFILE')
        body=request['body'];require(type(body) is dict and set(body)==({'identity','result'} if worker else {'session','identity','result'}),'INVALID_ARGUMENT')
        result=body['result'];require(type(result) is dict and set(result)=={'turn','projection','occurrences'},'INVALID_ARGUMENT')
        require(type(result['turn']) is int and 1<=result['turn']<=MAX_INPUTS and type(result['projection']) is str and
                type(result['occurrences']) is list and len(result['occurrences'])<=8 and all(type(x) is str for x in result['occurrences']),'INVALID_ARGUMENT')
        require(len(canonical(result))<=65536 and len(canonical(request))<=98304,'OVERLOADED')
        inspected=dict(request,body=dict(body,result={k:v for k,v in result.items() if k!='projection'}))
    # No old identity is executable through any mutated port, even if the old
    # endpoint is manually called with a currently valid replacement credential.
    found=set(derived);strings(inspected,found)
    require(not found.intersection(marker['historical_identity_digests']),'UNAUTHORIZED')


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--root',default='/state');p.add_argument('--role',required=True)
    p.add_argument('--checkpoint-sha256',required=True);p.add_argument('--generation',type=int,required=True)
    a=p.parse_args();print(json.dumps(install(a.root,a.role,a.checkpoint_sha256,a.generation),sort_keys=True))


if __name__=='__main__':main()
