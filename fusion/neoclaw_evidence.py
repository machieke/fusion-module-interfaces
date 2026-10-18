"""S04 application binding only. C1/C2 and trusted delivery remain separate owners."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
from . import nal_memory_contracts as c
from .contracts import ContractError,canonical,digest,require,decode
from .ports import Mutation,AtomEnvelope
from .responses import envelope
from .nal_private import configuration,open_local


def settings(app):
    cfg=json.loads(Path(app.config['evidence_config']).read_text())
    provider,_,frozen=configuration(cfg['policy'],cfg['credential'],cfg['scope'])
    require(cfg['placement']=='local','UNSUPPORTED_PROFILE')
    # No cognitive projection, label, hash or source is an argument to remote
    # memory providers. Combined HTTPS-memory/private-evidence is not this profile.
    for key in ('memory_read_config','memory_append_config','embedding_config','memory_embedding_config'):
        require(json.loads(Path(app.config[key]).read_text())['placement']=='local','UNSUPPORTED_PROFILE')
    frozen.update(sources=cfg['sources'],context=cfg['context'],assumption=cfg.get('assumption'),session=app.config['session_id'])
    require(frozen['principal']==app.binding['memory']['principal'],'UNAUTHORIZED')
    return cfg,frozen


class EvidenceAdoption:
    def __init__(self,app):
        self.app,self.db=app,app.db
        cfg,frozen=settings(app);require(frozen==app.binding['evidence'],'CONFLICT')
        self.modules=open_local(cfg['policy'],cfg['credential'],cfg['scope'],hook=app.hook)
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS app_sources(slot INTEGER PRIMARY KEY, accepted TEXT NOT NULL, episode TEXT,
            occurrence TEXT, receipt TEXT, exposed INTEGER NOT NULL DEFAULT 0, calls INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS app_assessments(id TEXT PRIMARY KEY, binding TEXT NOT NULL,
            calls INTEGER NOT NULL DEFAULT 0, creation TEXT, claim TEXT, event TEXT, receipt TEXT,
            declaration TEXT, decision TEXT, view TEXT);
        ''')
    def settings(self):
        cfg,frozen=settings(self.app);require(frozen==self.app.binding['evidence'],'CONFLICT');return cfg
    def authorize(self):
        cfg=self.settings()
        for name,operation in [('episodic.memory','readEvidence'),('belief.revision','readBelief')]:
            self.modules.access[name].authorize(cfg['scope'],operation)
        return cfg
    def deadline(self,value):require(time.time_ns()//1_000_000<=value,'DEADLINE_EXCEEDED')
    def record(self,ref):
        value=c.response_copy(self.modules.episodes.readEvidence(ref));c.response(c.evidence_record,value,ref);return value
    def belief(self,claim,context,revision=None):
        return c.snapshot_reply(self.modules.beliefs.readBelief(claim,context,revision),claim,context)
    def slot(self):
        pending=self.app.pending()
        return pending['id'] if pending else self.db.execute('SELECT coalesce(max(id),0)+1 FROM app_turns').fetchone()[0]
    def input_message(self):
        cfg=self.authorize();spec=cfg['sources'].get(str(self.slot()))
        return '' if spec is None else spec['text']
    def reserve_source(self,slot):
        with self.db:
            row=self.db.execute('SELECT calls FROM app_sources WHERE slot=?',(slot,)).fetchone()
            require(row is not None and row['calls']<c.MAX_APP_ATTEMPTS,'OVERLOADED')
            self.db.execute('UPDATE app_sources SET calls=calls+1 WHERE slot=?',(slot,))
    def source(self,text):
        cfg=self.authorize();slot=self.slot();spec=cfg['sources'].get(str(slot))
        if spec is None:require(text=='','CONFLICT');return text
        require(text==spec['text'] and type(text) is str and 0<len(text.encode())<=4096,'CONFLICT')
        old=self.db.execute('SELECT * FROM app_sources WHERE slot=?',(slot,)).fetchone()
        if old is None:
            accepted=dict(spec=spec,raw=text,observed_time=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                deadline_ms=time.time_ns()//1_000_000+self.app.config['invocation_timeout_ms'])
            with self.db:self.db.execute('INSERT INTO app_sources(slot,accepted) VALUES(?,?)',(slot,canonical(accepted).decode()))
            self.app.hook('after_source_identity')
        row=self.db.execute('SELECT * FROM app_sources WHERE slot=?',(slot,)).fetchone();accepted=json.loads(row['accepted'])
        require(accepted['spec']==spec and accepted['raw']==text,'CONFLICT')
        if row['receipt'] is None:
            self.reserve_source(slot)
            if row['episode'] is None:
                self.deadline(accepted['deadline_ms'])
                episode=self.modules.episodes.recordEpisode(Mutation(cfg['scope'],'session/'+self.app.session),'controlled-native-input')['ref']
                with self.db:self.db.execute('UPDATE app_sources SET episode=? WHERE slot=?',(canonical(episode).decode(),slot))
            else:episode=json.loads(row['episode'])
            command=Mutation(cfg['scope'],f'source/{self.app.session}/{slot}')
            occurrence=self.modules.episodes.occurrenceIdentity(command,episode)
            existing=c.occurrence_reply(self.modules.episodes.readOccurrence(episode,occurrence),episode,occurrence)
            if existing is None:
                self.deadline(accepted['deadline_ms'])
                payload=self.modules.atoms.create(Mutation(cfg['scope'],command.idempotency_key+'/payload'),'application/neoclaw-source',
                    canonical(dict(text=text,label=spec['label'],source=spec['source'],observed_time=accepted['observed_time'])))['ref']
                provenance=[]
                if spec.get('copy_of') is not None:
                    parent=self.db.execute('SELECT receipt FROM app_sources WHERE slot=? AND exposed=1',(spec['copy_of'],)).fetchone()
                    require(parent is not None,'NOT_FOUND');provenance=[json.loads(parent[0])['evidence']]
                head=self.modules.episodes.readEpisode(episode,1,1)['head']
                event=dict(occurrence_id=occurrence,kind='observation',source=spec['source'],observed_time=accepted['observed_time'],
                    payload=payload,causation=[],provenance=provenance,numerical=None,deadline_ms=accepted['deadline_ms'])
                receipt=self.modules.episodes.appendEvent(command,episode,head,event)
            else:receipt=existing['receipt']
            c.response(c.append_receipt,receipt)
            with self.db:self.db.execute('UPDATE app_sources SET occurrence=?,receipt=? WHERE slot=?',(occurrence,canonical(receipt).decode(),slot))
            self.app.hook('after_source_acceptance')
        else:receipt=json.loads(row['receipt'])
        recorded=self.record(receipt['evidence']);payload=self.modules.atoms.get(recorded['event']['payload']);envelope(payload,recorded['event']['payload'])
        require(payload.content_type=='application/neoclaw-source' and json.loads(payload.bytes)==dict(
            text=text,label=spec['label'],source=spec['source'],observed_time=accepted['observed_time']),'NOT_AVAILABLE')
        with self.db:self.db.execute('UPDATE app_sources SET exposed=1 WHERE slot=?',(slot,))
        return text+' RECORDED_SOURCE: '+spec['label'].replace(' ','_')

    def intent(self,command):
        require(len(command)==3 and all(type(x) is str for x in command),'INVALID_ARGUMENT')
        cfg=self.authorize();target,source=[x.replace('_',' ') for x in command[1:]]
        writes=self.db.execute('SELECT w.*,o.result FROM app_memory_writes w JOIN app_occurrences o ON o.id=w.id WHERE sampled_time=?',(target,)).fetchall()
        require(len(writes)==1,'CONFLICT' if writes else 'NOT_FOUND')
        memory=writes[0];require(memory['result']=='REMEMBER-SUCCESS' and memory['view'] is not None,'NOT_AVAILABLE')
        sources=[r for r in self.db.execute('SELECT * FROM app_sources WHERE exposed=1').fetchall() if json.loads(r['accepted'])['spec']['label']==source]
        require(len(sources)==1,'CONFLICT' if sources else 'NOT_FOUND')
        source_row=sources[0];receipt=json.loads(source_row['receipt']);record=self.record(receipt['evidence'])
        # Read and authenticate actual owner source before freezing its alias.
        c.evidence_record(record,receipt['evidence'])
        return dict(profile=c.PROFILE,operation=command[0],arguments=dict(target=target,source=source,memory=memory['id'],
            uuid=memory['uuid'],evidence=receipt['evidence'],context=cfg['context']))
    def admit(self,key,intent):
        if intent['profile']!=c.PROFILE:return
        binding=dict(intent=intent,base_view=None,observed_time=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'))
        self.db.execute('INSERT INTO app_assessments(id,binding) VALUES(?,?)',(key,canonical(binding).decode()))
    def begin(self):
        row=self.current();self.authorize();binding=json.loads(self.state(row)['binding'])
        if binding['base_view'] is None:
            self.deadline(row['deadline'])
            with self.db:
                binding['base_view']=self.db.execute('SELECT view FROM app_active_view').fetchone()[0]
                self.db.execute('UPDATE app_assessments SET binding=? WHERE id=?',(canonical(binding).decode(),row['id']))
    def current(self):
        require(self.app.current is not None,'CONFLICT')
        row=self.db.execute('SELECT * FROM app_occurrences WHERE turn=? AND position=?',self.app.current).fetchone()
        require(row is not None and json.loads(row['premises'])['profile']==c.PROFILE,'CONFLICT');return row
    def state(self,row):return self.db.execute('SELECT * FROM app_assessments WHERE id=?',(row['id'],)).fetchone()
    def save(self,row,key,value):
        require(key in ('creation','claim','event','receipt','declaration','decision','view'))
        with self.db:self.db.execute('UPDATE app_assessments SET '+key+'=? WHERE id=?',(canonical(value).decode(),row['id']))
    def reserve(self,row):
        self.authorize()
        with self.db:
            self.db.execute('BEGIN IMMEDIATE');state=self.state(row);require(state['calls']<c.MAX_APP_ATTEMPTS,'OVERLOADED')
            self.db.execute('UPDATE app_assessments SET calls=calls+1 WHERE id=?',(row['id'],))
        self.app.hook('after_assessment_reservation')

    def revise(self,target,source,sign):
        row=self.current();cfg=self.authorize();binding=json.loads(self.state(row)['binding']);intent=binding['intent'];args=intent['arguments']
        require(target.replace('_',' ')==args['target'] and source.replace('_',' ')==args['source'] and
            type(sign) is bool and sign==(intent['operation']=='support'),'CONFLICT')
        self.reserve(row);state=self.state(row)
        memory=self.db.execute('SELECT * FROM app_occurrences WHERE id=?',(args['memory'],)).fetchone()
        self.app.write.authorize(memory);write=self.app.write.state(memory);receipts=json.loads(write['receipts'])
        if state['creation'] is None:
            self.deadline(row['deadline'])
            # Verify payload bytes through the declared memory owner, then create
            # only a local creation binding; this is not an evidence observation.
            value=self.app.write.call(memory,'atom.storage','get',dict(ref=receipts['payload']['ref']))
            payload=AtomEnvelope(value['ref'],value['content_type'],decode(value['data']));envelope(payload,receipts['payload']['ref'])
            require(json.loads(payload.bytes)['uuid']==args['uuid'],'CONFLICT')
            creation=self.modules.atoms.create(Mutation(cfg['scope'],'creation/'+args['memory']),
                'application/neoclaw-fresh-creation',canonical(dict(policy=c.PRIOR,memory_uuid=args['uuid'],occurrence=args['memory'],
                    time=json.loads(payload.bytes)['time'],payload=receipts['payload']['ref'],enrollment=receipts['enrollment']['ref'])))['ref']
            self.save(row,'creation',creation)
        creation=json.loads(self.state(row)['creation'])
        if self.state(row)['claim'] is None:
            self.deadline(row['deadline'])
            claim=self.modules.atoms.create(Mutation(cfg['scope'],'claim/'+args['memory']),'application/fusion-claim',
                canonical(dict(predicate='neoclaw-memory-assessment',arguments=[creation['digest']],positive=True)))['ref']
            self.save(row,'claim',claim)
        claim=json.loads(self.state(row)['claim']);snapshot=self.belief(claim,args['context'],None)
        if snapshot['revision']==0:
            self.modules.beliefs.registerPrior(Mutation(cfg['scope'],'prior/'+args['memory']),claim,args['context'],creation,row['deadline'])
        if self.state(row)['receipt'] is None:
            source_record=self.record(args['evidence'])
            numeric=dict(claim=claim,context=args['context'],relationship='supports' if sign else 'contradicts',
                truth=c.stv('1.0' if sign else '0.0','0.5'),ingestion_profile=c.INGESTION)
            # C1 retains each assessment occurrence; contribution identity is C2's
            # source/claim/policy identity, independent of this command occurrence.
            command=Mutation(cfg['scope'],'assessment/'+row['id']);episode=args['evidence']['episode']
            occurrence=self.modules.episodes.occurrenceIdentity(command,episode)
            seen=c.occurrence_reply(self.modules.episodes.readOccurrence(episode,occurrence),episode,occurrence)
            if seen is None:
                self.deadline(row['deadline'])
                payload=self.modules.atoms.create(Mutation(cfg['scope'],'assessment-payload/'+row['id']),
                    'application/neoclaw-assessment',canonical(dict(command_occurrence=row['id'],source=args['evidence'],assessment=numeric)))['ref']
                event=dict(occurrence_id=occurrence,kind='action',source='native-agent-assessment',observed_time=binding['observed_time'],payload=payload,
                    causation=[creation],provenance=[args['evidence']],numerical=numeric,deadline_ms=row['deadline'])
                self.save(row,'event',event)
                head=self.modules.episodes.readEpisode(episode,1,1)['head']
                receipt=self.modules.episodes.appendEvent(command,episode,head,event)
            else:receipt=seen['receipt']
            c.response(c.append_receipt,receipt)
            self.save(row,'receipt',receipt);self.app.hook('after_assessment_acceptance')
        receipt=json.loads(self.state(row)['receipt']);record=self.record(receipt['evidence'])
        if self.state(row)['declaration'] is None:
            snapshot=self.belief(claim,args['context'],None);identity=c.contribution(record)
            exists=any(o['contribution']==identity for o in snapshot['observations'])
            declaration=None
            if not exists and record['lineage_roots']:
                declaration=dict(model_id=cfg['assumption'],supports=[snapshot['aggregate'],identity],status='assumption') if cfg.get('assumption') else None
            self.save(row,'declaration',declaration)
        declaration=json.loads(self.state(row)['declaration'])
        self.modules.relay.drain(receipt['evidence']['episode'],{receipt['delivery_id']:declaration} if declaration else {})
        decisions=self.modules.relay.decisions(receipt['evidence']['episode'])
        decision=next((x for x in decisions if x['evidence']==receipt['evidence']),None)
        require(decision is not None,'NOT_AVAILABLE')
        require(receipt['delivery_id'] not in {x['delivery_id'] for x in self.modules.episodes.pendingEvidence(receipt['evidence']['episode'],c.MAX_PENDING)},'NOT_AVAILABLE')
        self.save(row,'decision',decision);self.app.hook('after_assessment_delivery')
        self.presentation(row)
        return 'REVISION-SUCCESS' if decision['numerical']=='revised' else '(REVISION-OUTCOME '+decision['numerical']+' '+decision['admission']+')'

    def presentation(self,row):
        state=self.state(row)
        if state['view'] is not None:
            view=json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(json.loads(state['view']),)).fetchone()[0])
            self.validate_view(view);return view
        self.deadline(row['deadline']);self.authorize()
        binding=json.loads(state['binding']);args=binding['intent']['arguments'];decision=json.loads(state['decision'])
        base=json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(binding['base_view'],)).fetchone()[0])
        snapshot=decision['snapshot'];metadata=base['metadata']
        item=next(x for x in metadata['records'] if x['uuid']==args['uuid'])
        item['stv']=[float(snapshot['truth'][k]) for k in ('strength','confidence')]
        labels=[];sources=[]
        for o in snapshot['observations']:
            assessment=self.record(o['evidence'])
            for ref in assessment['event']['provenance']:
                source=self.record(ref);atom=self.modules.atoms.get(source['event']['payload']);envelope(atom,source['event']['payload'])
                require(atom.content_type=='application/neoclaw-source','NOT_AVAILABLE');label=json.loads(atom.bytes)['label']
                labels.append(label);sources.append(dict(ref=ref,label=label))
        creation_time=json.loads(self.app.write.state(self.db.execute('SELECT * FROM app_occurrences WHERE id=?',(args['memory'],)).fetchone())['intent'])['time']
        item['links']=list(dict.fromkeys([creation_time,*labels]))
        bindings=[x for x in base.get('beliefs',[]) if x['uuid']!=args['uuid']]
        bindings.append(dict(uuid=args['uuid'],claim=snapshot['claim'],context=snapshot['context'],revision=snapshot['revision'],
            snapshot_digest=digest(canonical(snapshot)),sources=sources,creation_time=creation_time))
        defaults={k:v for k,v in base.get('defaults',{}).items() if k!=args['uuid']}
        view=dict(snapshot=base['snapshot'],metadata=metadata,metadata_seal=digest(canonical(metadata)),beliefs=bindings,defaults=defaults)
        self.validate_view(view);key=digest(canonical(view));self.materialize(view,row['deadline'])
        self.app.hook('after_belief_presentation')
        with self.db:
            require(self.db.execute('SELECT view FROM app_active_view').fetchone()[0]==binding['base_view'],'CONFLICT')
            self.db.execute('INSERT OR IGNORE INTO app_read_views VALUES(?,?)',(key,canonical(view).decode()))
            self.db.execute('UPDATE app_active_view SET view=?',(key,));self.db.execute('UPDATE app_assessments SET view=? WHERE id=?',(canonical(key).decode(),row['id']))
        self.app.hook('after_belief_view_selection');return view

    def validate_view(self,view):
        self.authorize();require(digest(canonical(view['metadata']))==view['metadata_seal'],'CONFLICT')
        bound={x['uuid'] for x in view.get('beliefs',[])};defaults=view.get('defaults',{})
        require(not bound & set(defaults) and bound|set(defaults)=={x['uuid'] for x in view['metadata']['records']},'CONFLICT')
        require(all(x in ('fixture-metadata-not-a-belief',c.PRIOR+':not-registered') for x in defaults.values()),'CONFLICT')
        for binding in view.get('beliefs',[]):
            snapshot=self.belief(binding['claim'],binding['context'],binding['revision'])
            c.snapshot_reply(snapshot,binding['claim'],binding['context']);require(digest(canonical(snapshot))==binding['snapshot_digest'],'CONFLICT')
            item=next(x for x in view['metadata']['records'] if x['uuid']==binding['uuid'])
            prior=next(x for x in snapshot['supports'] if x['kind']=='prior')
            creation=self.modules.atoms.get(prior['creation']);envelope(creation,prior['creation'])
            created=json.loads(creation.bytes)
            require(created['memory_uuid']==binding['uuid'] and created['time']==binding['creation_time'],'CONFLICT')
            require(item['stv']==[float(snapshot['truth'][k]) for k in ('strength','confidence')],'CONFLICT')
            expected=[]
            for o in snapshot['observations']:
                assessment=self.record(o['evidence'])
                for ref in assessment['event']['provenance']:
                    source=self.record(ref);atom=self.modules.atoms.get(source['event']['payload']);envelope(atom,source['event']['payload'])
                    expected.append(dict(ref=ref,label=json.loads(atom.bytes)['label']))
            require(binding['sources']==expected and item['links']==list(dict.fromkeys([binding['creation_time'],*[x['label'] for x in expected]])),'CONFLICT')
        return view
    def materialize(self,view,deadline):
        self.validate_view(view)
        path=self.modules.root/'presentation'/digest(canonical(view));path.parent.mkdir(exist_ok=True,mode=0o700)
        raw=canonical(view)
        if path.exists():require(path.read_bytes()==raw,'CONFLICT')
        else:
            self.deadline(deadline)
            from .adapters.chroma_vector import publish
            publish(path,view)
        return path
    def projection(self,view):
        self.validate_view(view)
        path=self.modules.root/'presentation'/digest(canonical(view))
        require(path.is_file() and path.read_bytes()==canonical(view),'NOT_AVAILABLE')
        from .adapters.neoclaw_belief_presentation import Projection
        return Projection(view['metadata'])
    def capture(self,value):
        row=self.current();state=self.state(row);self.authorize();require(state['view'] is not None and state['decision'] is not None,'NOT_AVAILABLE')
        decision=json.loads(state['decision']);expected='REVISION-SUCCESS' if decision['numerical']=='revised' else '(REVISION-OUTCOME '+decision['numerical']+' '+decision['admission']+')'
        require(value==expected and (row['result'] is None or row['result']==value),'NOT_AVAILABLE')
        self.validate_view(json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(json.loads(state['view']),)).fetchone()[0]))
        with self.db:self.db.execute('UPDATE app_occurrences SET result=?,done=1 WHERE id=?',(value,row['id']))
        self.app.hook('after_assessment_result_capture');return value
    def replay(self,row=None):
        row=self.current() if row is None else row;self.reserve(row);state=self.state(row)
        require(row['result'] is not None and state['view'] is not None,'NOT_AVAILABLE')
        receipt=json.loads(state['receipt']);decision=json.loads(state['decision'])
        require(decision in self.modules.relay.decisions(receipt['evidence']['episode']),'NOT_AVAILABLE')
        self.validate_view(json.loads(self.db.execute('SELECT value FROM app_read_views WHERE id=?',(json.loads(state['view']),)).fetchone()[0]))
        return row['result']
