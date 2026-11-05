"""Additional owner-local capacity dimensions; no foreign owner is opened.

Only fixed journal names under the selected owner's configured root are read.
Unbounded lifetime dimensions retain actual usage with an unknown bound; no
capacity promise, private consumer endpoint or shared quota database is added.
"""
import json,time,sqlite3,uuid
from pathlib import Path
from fusion.contracts import require,digest,canonical,ContractError
from .integrated_capacity import snapshot

PROFILE='pilot-owner-headroom/1'


def dimension(name,used,limit=None,*,reserved=None,unit='records',basis='retained',control=0):
    require(used is None or type(used) is int and used>=0)
    require(limit is None or type(limit) is int and limit>0)
    require(reserved is None or type(reserved) is int and reserved>=0)
    return dict(category=name,used=used,limit=limit,reserved=reserved,unit=unit,basis=basis,
        remaining=None if used is None or limit is None or reserved is None else limit-used-reserved,
        bound_status='UNKNOWN' if limit is None else 'OWNER_ENFORCED',control_reserve=control,reclaimable_derived_bytes=None)


def inspect(db,config=None):
    from fusion import promotion_contracts as pc,lookup_contracts as lc,nal_memory_contracts as nc
    from fusion.preview_workspace import MAX_FILES,MAX_COMMANDS
    from fusion.preview_lifecycle import MAX_EVENTS
    config=config or {}
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    def n(sql):return db.execute(sql).fetchone()[0]
    out=[]
    def count(table,name,limit=None,reserved=0,basis='retained'):
        if table in tables:out.append(dimension(name,n('SELECT count(*) FROM '+table),limit,reserved=reserved,basis=basis))
    def measure(name,sql,limit=None,unit='records',basis='retained',reserved=0):
        out.append(dimension(name,n(sql),limit,reserved=reserved,unit=unit,basis=basis))
    def largest(table,key,name,limit):
        measure(name,'SELECT coalesce(max(amount),0) FROM (SELECT count(*) AS amount FROM '+table+' GROUP BY '+key+')',limit,basis='per-identity-maximum')
    if 'model_calls' in tables:
        limit=config.get('model_completion',{}).get('max_calls')
        count('model_calls','model_occurrences',limit)
        measure('model_reserved_calls','SELECT coalesce(sum(reserved),0) FROM model_calls',limit,unit='attempts')
        measure('model_captures','SELECT count(*) FROM model_calls WHERE response IS NOT NULL',limit)
        measure('model_uncaptured_reservations','SELECT count(*) FROM model_calls WHERE reserved>0 AND response IS NULL',limit)
    if 'pilot_model_clock' in tables:
        count('pilot_model_clock','model_clock_rows',1)
        count('pilot_model_capture_clocks','model_capture_clock_rows',config.get('model_completion',{}).get('max_calls'))
        measure('model_clock_anomalies','SELECT anomalies FROM pilot_model_clock',unit='observations')
        measure('model_clock_invalid_captures','SELECT count(*) FROM pilot_model_capture_clocks WHERE valid=0')
    if 'encode_intents' in tables:
        from fusion.embedding_contracts import MAX_OCCURRENCES
        count('encode_intents','embedding_occurrences',MAX_OCCURRENCES)
        count('encode_attempts','embedding_attempts',MAX_OCCURRENCES*3)
        largest('encode_attempts','id','largest_embedding_attempts',3)
        measure('embedding_uncaptured_reservations','SELECT count(*) FROM encode_attempts WHERE finished=0',MAX_OCCURRENCES*3)
    if 'feed_meta' in tables:
        meta=json.loads(n('SELECT value FROM feed_meta'));policy=meta.get('capacity')
        count('feed_atoms','feed_published_records',None if policy else lc.MAX_ATOMS)
        if policy:
            from fusion.sustained_feed import usage
            for index,scope in enumerate(policy['scopes']):
                value=usage(None,db,scope);prefix='feed_scope_'+str(index)+'_'
                for key,limit,unit in [('reserved_records',policy['records'],'records'),('charged_bytes',policy['bytes'],'bytes'),('pending_records',policy['records'],'records'),('published_payload_bytes',None,'bytes')]:
                    out.append(dimension(prefix+key,value[key],limit,reserved=0,unit=unit))
                if 'feed_archive_intents' in tables:
                    records,charge,pending=db.execute("SELECT count(*),coalesce(sum(charge),0),coalesce(sum(state='reserved'),0) FROM feed_archive_intents WHERE scope=?",(scope,)).fetchone()
                    for key,used,limit,unit in [('archive_segments',records,meta['archive']['segments'],'records'),('archive_charged_bytes',charge,meta['archive']['bytes'],'bytes'),('archive_pending',pending,meta['archive']['segments'],'records')]:
                        out.append(dimension(prefix+key,used,limit,reserved=0,unit=unit))
    count('atoms','immutable_atoms')
    if 'sustained_allocations' in tables:
        from types import SimpleNamespace
        from fusion.sustained_sessions import SustainedSessionStore,MAX_ACTIONS
        usage=SustainedSessionStore._usage(SimpleNamespace(db=db));limits=config.get('native_sessions',{}).get('allocation',{})
        for key in ('retained','active','pending'):
            out.append(dimension('application_'+key,usage[key],limits.get(key),reserved=0,basis='retained' if key=='retained' else 'concurrent'))
        out.append(dimension('application_logical_bytes',usage['logical_bytes'],limits.get('bytes'),reserved=usage['completion_reserved_bytes'],unit='bytes'))
        count('sustained_actions','application_actions',MAX_ACTIONS)
        count('preview_inputs','application_input_history')
        measure('application_uncertain_inputs',"SELECT count(*) FROM preview_inputs WHERE state IN ('dispatched','cancel-requested','needs-reconciliation')",basis='concurrent')
    if 'pilot_subscription_source' in tables:
        from fusion.pilot_subscriptions import usage,LIMITS
        value=usage(db)
        for key in ('subscriptions','actions','retained_hints','logical_bytes'):
            out.append(dimension('subscription_'+key,value[key],LIMITS.get(key),reserved=value['closure_reserved_actions'] if key=='actions' else value['closure_reserved_bytes'] if key=='logical_bytes' else 0,unit='bytes' if key=='logical_bytes' else 'records'))
        largest('pilot_subscription_events','session','largest_retained_subscription_hints',LIMITS['window'])
    if 'pilot_workflows' in tables:
        from fusion.guarded_continuation import LIMITS,TABLES
        count('pilot_workflows','guarded_workflows',LIMITS['workflows'])
        for table,key,limit in [('pilot_workflow_steps','steps',LIMITS['steps']),('pilot_workflow_observations','observations',LIMITS['observations']),('pilot_workflow_checkpoints','checkpoints',LIMITS['checkpoints']),('pilot_workflow_versions','versions',LIMITS['amendments']+1)]:
            count(table,'workflow_'+key,LIMITS['workflows']*limit);largest(table,'workflow','largest_workflow_'+key,limit)
        total=sum(sum(len(canonical(dict(row))) for row in db.execute('SELECT * FROM '+table)) for table in TABLES)
        active=n("SELECT count(*) FROM pilot_workflows WHERE status NOT IN ('complete','refused')")
        out.append(dimension('workflow_logical_bytes',total,LIMITS['metadata_bytes'],reserved=active*LIMITS['completion_reserved_bytes'],unit='bytes'))
        measure('workflow_spent_reservations','SELECT coalesce(sum(reservations),0) FROM pilot_workflows',unit='attempts')
    if 'pilot_derived_cleanup_charges' in tables:
        from .pilot_derived_maintenance import LIMITS
        count('pilot_derived_cleanup_charges','derived_cleanup_plans',LIMITS['plans'])
        measure('derived_cleanup_logical_bytes','SELECT coalesce(sum(intent_bytes+result_bytes),0) FROM pilot_derived_cleanup_charges',unit='bytes',reserved=n("SELECT coalesce(sum(result_bound),0) FROM pilot_derived_cleanup_charges WHERE state!='complete'"))
    count('pilot_derived_cleanup','derived_cleanup_receipts',32)
    if 'pilot_registry_meta' in tables:
        from fusion.provider_retention import Retention
        obj=object.__new__(Retention);obj.db=db;obj.limits=json.loads(n('SELECT policy FROM pilot_registry_meta'))
        for key,value in obj.usage().items():
            out.append(dimension('registry_'+key,value,obj.limits[key],reserved=0,unit='bytes' if key.endswith('bytes') else 'records',control=obj.limits['control_bytes'] if key in ('active_bytes','retained_bytes') else 0))
    if {'episodes','events','deliveries'}<=tables:
        count('episodes','episodes');count('events','episode_events')
        # MAX_EVENTS is per episode, not a false aggregate cap.
        out.append(dimension('largest_episode_events',n('SELECT coalesce(max(head),0) FROM episodes'),nc.MAX_EVENTS,reserved=0,basis='per-episode-maximum'))
        cols={r[1] for r in db.execute('PRAGMA table_info(deliveries)')}
        if 'completed' in cols:pending=n('SELECT count(*) FROM deliveries WHERE completed=0')
        elif 'decision' in cols:pending=n('SELECT count(*) FROM deliveries WHERE decision IS NULL')
        else:pending=None
        out.append(dimension('evidence_delivery_pending',pending,reserved=0,basis='concurrent'))
        if 'decision' in cols:
            out.append(dimension('largest_episode_pending',n('SELECT coalesce(max(amount),0) FROM (SELECT count(*) AS amount FROM deliveries WHERE decision IS NULL GROUP BY episode)'),nc.MAX_PENDING,reserved=0,basis='per-episode-maximum'))
        count('mutations','episode_replay_identities')
    if {'snapshots','attempts'}<=tables:
        count('snapshots','belief_snapshots');count('attempts','belief_admissions');count('nal_priors','labelled_compatibility_priors')
        # Per-claim support bounds do not bound lifetime claims/snapshots.
        maximum=0
        for (value,) in db.execute('SELECT value FROM snapshots'):
            maximum=max(maximum,len(json.loads(value)['observations']))
        out.append(dimension('largest_belief_observations',maximum,nc.MAX_SUPPORTS,reserved=0,basis='per-claim-snapshot'))
    if {'contexts','history','bindings'}<=tables:
        count('contexts','attention_contexts',pc.MAX_CONTEXTS);count('bindings','attention_bindings',pc.MAX_BINDINGS);count('history','retained_attention_revisions')
        out.append(dimension('attention_evaluation_reservations',n('SELECT coalesce(sum(calls),0) FROM bindings'),reserved=0,unit='attempts'))
        out.append(dimension('attention_uncaptured_bindings',n('SELECT count(*) FROM bindings WHERE calls>0 AND result IS NULL'),reserved=0))
    count('accepted','relation_assertions',lc.MAX_RELATIONS);count('commands','relation_commands',lc.MAX_COMMANDS)
    count('preview_relation_intents','structural_commands',lc.MAX_COMMANDS);count('preview_relation_events','structural_events')
    count('lifecycle_intents','memory_lifecycle_commands',MAX_EVENTS);count('lifecycle_events','memory_lifecycle_events',MAX_EVENTS)
    count('workspace_files','workspace_files',MAX_FILES);count('workspace_effects','workspace_occurrences',MAX_COMMANDS)
    if 'workspace_effects' in tables:measure('workspace_uncaptured_effects','SELECT count(*) FROM workspace_effects WHERE receipt IS NULL')
    if 'messages' in tables:
        count('messages','retained_mailbox_messages');count('acknowledgements','mailbox_acknowledgments')
        cols={r[1] for r in db.execute('PRAGMA table_info(messages)')}
        if 'acknowledged' in cols:
            # Capacity is enforced per route, not against total history.
            out.append(dimension('mailbox_unacknowledged',n('SELECT count(*) FROM messages WHERE acknowledged=0'),reserved=0,basis='concurrent'))
            maximum=n('SELECT coalesce(max(amount),0) FROM (SELECT count(*) AS amount FROM messages WHERE acknowledged=0 GROUP BY route)')
            out.append(dimension('largest_mailbox_pending',maximum,(config or {}).get('capacity'),reserved=0,basis='per-route-maximum'))
    if 'jobs' in tables:
        from fusion.neoclaw_contracts import MAX_REQUESTS
        count('jobs','execution_jobs',MAX_REQUESTS if 's01_work' in tables else None)
        count('outbox','execution_outbox')
        measure('execution_pending',"SELECT (SELECT count(*) FROM jobs WHERE state='queued')+(SELECT count(*) FROM outbox WHERE sent=0)",config.get('capacity'),basis='concurrent')
        measure('execution_unpublished_results','SELECT count(*) FROM outbox WHERE sent=0',basis='concurrent')
    # Caller journals belong to this application owner. Captures and old views
    # are retained independently of current active capacity; no quota is invented.
    for table,name in [('app_occurrences','native_occurrences'),('app_turns','native_turns'),('app_memory_reads','query_occurrences'),('app_memory_writes','remember_occurrences'),('app_query_views','retained_query_bindings'),('app_read_views','retained_memory_views'),('app_embeddings','caller_embedding_occurrences'),('preview_memory_plans','memory_lifecycle_plans'),('preview_memory_handles','memory_handles'),('preview_context_receipts','working_context_occurrences'),('preview_context_views','working_context_history'),('preview_history_materializations','derived_history_materializations'),('preview_task_outbox','task_envelopes'),('preview_inspections','inspection_occurrences')]:count(table,name)
    if 'preview_task_outbox' in tables:
        measure('task_relay_reservations','SELECT coalesce(sum(calls),0) FROM preview_task_outbox',unit='attempts')
        measure('largest_task_relay_reservations','SELECT coalesce(max(calls),0) FROM preview_task_outbox',24,unit='attempts',basis='per-envelope-maximum')
        measure('task_unobserved_publications','SELECT count(*) FROM preview_task_outbox WHERE receipt IS NULL')
    if 'app_memory_reads' in tables:
        measure('captured_search_results','SELECT count(*) FROM app_memory_reads WHERE candidates IS NOT NULL')
        measure('captured_payload_results','SELECT count(*) FROM app_memory_reads WHERE payloads IS NOT NULL')
        measure('query_spent_requests','SELECT coalesce(sum(calls),0) FROM app_memory_reads',unit='attempts')
        measure('query_spent_searches','SELECT coalesce(sum(queries),0) FROM app_memory_reads',unit='attempts')
    for table,prefix in [('app_query_vectors','query_encoder'),('app_memory_vectors','memory_encoder')]:
        if table in tables:
            count(table,prefix+'_occurrences')
            measure(prefix+'_captured_vectors','SELECT count(*) FROM '+table+' WHERE result IS NOT NULL')
            measure(prefix+'_spent_attempts','SELECT coalesce(sum(attempts),0) FROM '+table,unit='attempts')
            measure('largest_'+prefix+'_attempts','SELECT coalesce(max(attempts),0) FROM '+table,3,unit='attempts',basis='per-occurrence-maximum')
    if 'preview_context_views' in tables:
        from fusion.preview_context import MAX_ITEMS,MAX_BYTES
        values=[json.loads(row[0]) for row in db.execute('SELECT body FROM preview_context_views')]
        out.append(dimension('largest_working_context_items',max(map(len,values),default=0),MAX_ITEMS,reserved=0,basis='per-view-maximum'))
        out.append(dimension('largest_working_context_bytes',max((len(canonical(x)) for x in values),default=0),MAX_BYTES,reserved=0,unit='bytes',basis='per-view-maximum'))
    for table,name,limit in [('integrated_inspection_continuations','inspection_continuations',128),('integrated_inspection_steps','inspection_steps',128*7),('integrated_inspection_controls','inspection_controls',128*2),('integrated_chain_continuations','chain_continuations',128),('integrated_chain_reads','chain_observations',128*16)]:count(table,name,limit)
    if 'integrated_chain_continuations' in tables:
        measure('chain_spent_submit_reservations','SELECT coalesce(sum(submit_reserved),0) FROM integrated_chain_continuations',128,unit='attempts')
        measure('chain_uncaptured_reservations','SELECT count(*) FROM integrated_chain_continuations WHERE submit_reserved>0 AND result IS NULL',128)
        measure('largest_chain_observations','SELECT coalesce(max(observations),0) FROM integrated_chain_continuations',16,basis='per-continuation-maximum')
    count('m4_intent','chain_signed_intents',1);count('m4_observations','chain_owner_observations',256)
    if 'm4_intent' in tables:
        measure('chain_signed_uncaptured_receipts','SELECT count(*) FROM m4_intent WHERE signed IS NOT NULL AND receipt IS NULL',1)
    for table,name in [('channel_epochs','irc_connection_epochs'),('channel_ingress','irc_captured_inputs'),('channel_egress','irc_outputs'),('app_channel_inputs','caller_channel_inputs'),('app_channel_outputs','caller_channel_outputs')]:count(table,name)
    if 'channel_egress' in tables:
        measure('irc_spent_send_reservations','SELECT coalesce(sum(reserved),0) FROM channel_egress',unit='attempts')
        measure('irc_uncertain_sends',"SELECT count(*) FROM channel_egress WHERE reserved>0 AND outcome='pending'")
    return out


JOURNALS=('session-inbox.sqlite','caller.sqlite','model.sqlite','encoder.sqlite','atoms.sqlite',
    'memory/feed.sqlite','memory/lifecycle.sqlite','episodes.sqlite','beliefs.sqlite','attention.sqlite','relations.sqlite',
    'preview-relations.sqlite','session-history.sqlite','messages.sqlite','messaging.sqlite','workspace.sqlite',
    'preview-facets/workspace.sqlite','preview-facets/session-history.sqlite','preview-facets/preview-relations.sqlite',
    'memory/episodes.sqlite','memory/beliefs.sqlite','memory/attention.sqlite','memory/relations.sqlite',
    'cognitive/episodes.sqlite','cognitive/beliefs.sqlite','cognitive/attention.sqlite','cognitive/relations.sqlite',
    'execution.sqlite','preview-inspect.sqlite','tasks.sqlite','commitments.sqlite','chain-progress.sqlite','inspect.sqlite','bridge.sqlite')
SEARCH_ROOTS=('search','memory/search','memory/active-search','vector-search')


def local(path,root):
    """Never follow a symlink or an operator-selected foreign-owner location."""
    require(path.is_relative_to(root) and path.resolve().is_relative_to(root.resolve()),'UNAUTHORIZED')
    require(not path.is_symlink() and all(not p.is_symlink() for p in path.parents if p.is_relative_to(root)),'UNAUTHORIZED')
    return path


def document(path,root):
    local(path,root);require(path.is_file() and path.stat().st_size<=1048576,'NOT_AVAILABLE')
    return json.loads(path.read_bytes())


def search_dimensions(root,owner_root):
    """Metadata observations only: no index, encoder, feed or provider access."""
    local(root,owner_root);entries=list(root.iterdir());require(len(entries)<=1024,'OVERLOADED')
    values=[dimension('search_metadata_files',sum(x.name.endswith('.json') for x in entries),reserved=0)]
    directories=[x for x in entries if x.is_dir()];require(len(directories)<=32,'OVERLOADED')
    values.append(dimension('search_generation_directories',len(directories),32,reserved=0))
    manifest=document(root/'published.json',owner_root) if (root/'published.json').exists() else None
    values.append(dimension('retained_search_generations',len(manifest['generations']) if manifest else None,32,reserved=0))
    values.append(dimension('search_cleanup_receipts',sum(x.name.startswith('reclaim-') and x.name.endswith('.json') for x in entries),32,reserved=0))
    attempts=0;largest=0;complete=0;records=0;unknown=0
    for path in directories:
        local(path,owner_root)
        try:require(str(uuid.UUID(path.name))==path.name,'UNSUPPORTED_PROFILE')
        except ValueError:require(False,'UNSUPPORTED_PROFILE')
        journal=path/'maintenance.json';capture=path/'manifest.json'
        if journal.exists():
            record=document(journal,owner_root);used=record['attempts'];require(type(used) is int and 0<=used<=3,'NOT_AVAILABLE')
            attempts+=used;largest=max(largest,used)
        else:unknown+=1
        if capture.exists():
            data=document(capture,owner_root);complete+=1;records=max(records,len(data['records']))
    from fusion.vector_contracts import MAX_RECORDS
    values.extend([dimension('search_build_attempts',attempts if not unknown else None,32*3,reserved=0,unit='attempts'),
        dimension('largest_search_build_attempts',largest if not unknown else None,3,reserved=0,unit='attempts',basis='per-generation-maximum'),
        dimension('captured_search_generations',complete,32,reserved=0),
        dimension('largest_indexed_membership',records,MAX_RECORDS,reserved=0,basis='per-generation-maximum')])
    return values


def collect(root,run):
    root,run=Path(root).absolute(),Path(run).absolute();dimensions=[];unavailable=[];cuts=[]
    partitions=[(root,run),(root/'scopes/private-a',run/'scopes/private-a'),(root/'scopes/private-b',run/'scopes/private-b')]
    errors=(sqlite3.Error,ContractError,ValueError,KeyError,TypeError,IndexError,OSError)
    def failed(partition,name,error):
        unavailable.append(dict(partition=partition,journal=name,status='UNKNOWN',reason=getattr(error,'code',type(error).__name__)))
    def record(partition,name,values):
        dimensions.extend(dict(row,partition=partition,journal=name) for row in values)
        cuts.append(dict(partition=partition,journal=name,semantic_observation=digest(canonical(values))))
    def journal(partition,name,path,config):
        try:
            local(path,root)
            with snapshot(path) as db:values=inspect(db,config)
            # SQLite logical content and physical allocated blocks are different
            # observations; no reclaim estimate is inferred from either one.
            for suffix,key in [('', 'journal'),('-wal','wal'),('-shm','shared_memory')]:
                item=Path(str(path)+suffix);local(item,root)
                if item.exists():values.append(dimension(key+'_allocated_bytes',item.stat().st_blocks*512,reserved=0,unit='bytes',basis='physical-observation'))
            record(partition,name,values)
        except errors as error:failed(partition,name,error)
    for partition,(base,configuration) in enumerate(partitions):
        config={};declared=set()
        for filename in ('owner.json','cognitive-owner.json','facet-owner.json'):
            file=configuration/filename
            if not file.exists():continue
            try:
                selected=document(file,run);config.update(selected)
                for key in ('model_completion','embedding','native_sessions'):
                    path=selected.get(key,{}).get('database')
                    if path is not None:
                        path=Path(path);local(path,base);name=str(path.relative_to(base));require(name in JOURNALS,'UNSUPPORTED_PROFILE');declared.add(name)
            except errors as error:failed(partition,filename,error)
        for name in JOURNALS:
            path=base/name
            if path.exists() or path.is_symlink() or name in declared:journal(partition,name,path,config)
        for name in SEARCH_ROOTS:
            path=base/name
            if path.exists() or path.is_symlink():
                try:record(partition,name,search_dimensions(path,root))
                except errors as error:failed(partition,name,error)
    # Session IDs are enumerated only from this owner's retained allocation
    # journal. Neither names nor scope strings leave the operator-only report.
    inbox=root/'session-inbox.sqlite'
    if inbox.is_file():
        try:
            local(inbox,root)
            with snapshot(inbox) as db:
                tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                sessions=db.execute('SELECT session FROM sustained_allocations ORDER BY session LIMIT 17').fetchall() if 'sustained_allocations' in tables else []
            require(len(sessions)<=16,'OVERLOADED')
            for index,(session,) in enumerate(sessions):
                require(str(uuid.UUID(session))==session,'NOT_AVAILABLE');path=root/'sessions'/session/'caller.sqlite'
                # A retained allocation need not have started its native caller.
                # Absence is UNKNOWN, never a newly created or empty journal.
                journal('session-'+str(index),'caller.sqlite',path,{})
        except errors as error:failed('sessions','caller.sqlite',error)
    require(len(dimensions)<=2048 and len(cuts)<=128 and len(unavailable)<=128,'OVERLOADED')
    return dict(profile=PROFILE,observed_ms=time.time_ns()//1000000,revision=digest(canonical(cuts)),dimensions=dimensions,unavailable=unavailable,
        unknown_lifetime_bounds='REPORTED_AS_NULL_NOT_UNLIMITED',authority='SCOPED_OPERATOR_OWNER_LOCAL',cross_owner_atomic=False,
        normal_admission_estimate='NO_MULTI_OWNER_PROMISE',control_reserve='ONLY_EXPLICIT_OWNER_RESERVES',additional_live_generations=0)
