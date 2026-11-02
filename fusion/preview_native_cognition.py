"""Handle/visibility adapters on the existing NAL revision and Attention clients.

Numerical owners and native functions are unchanged. Only fresh operator input
is a source; administrative history alone never acquires empirical provenance.
The bounded preview initially assesses memories created by the acting agent.
"""
from datetime import datetime,timezone
import copy,json
from .contracts import canonical,digest,require
from . import nal_memory_contracts as n
from .neoclaw_evidence import EvidenceAdoption
from .neoclaw_priority import PriorityAdoption
from .preview_handles import make,derive,parse


class PreviewEvidence(EvidenceAdoption):
    def source(self,text):
        source=self.app.preview.input.source()
        if 'task_origin' in source:
            require(text==source['payload']['text'],'CONFLICT')
            return text  # Administrative task/report capture is not a fresh empirical root.
        return super().source(text)
    def source_spec(self,cfg,slot):
        source=self.app.preview.input.source()
        return dict(text=source['payload']['text'],label='input-'+source['occurrence'],
            source='preview-synthetic-operator',message_id=source['occurrence'],
            observed_time=datetime.fromtimestamp(source['accepted']/1000,timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'),
            deadline_ms=source['deadline'])
    def source_observation(self,spec,text):
        return dict(spec=spec,raw=text,observed_time=spec['observed_time'],deadline_ms=spec['deadline_ms'])
    def source_result(self,text,spec,receipt):
        source=self.app.preview.input.source()
        handle=make('event',self.app.preview_config['scope'],self.app.binding['principal'],receipt['evidence'])
        self.app.preview.history.record(source['occurrence']+'/source','external-observation',
            dict(observed_ms=source['accepted'],source=handle,classification='authenticated-synthetic-input-not-independent-of-its-copies'),deadline=source['deadline'])
        return text
    def resolve_source(self,handle):
        parse(handle,'event');scope=self.app.preview_config['scope'];found=[]
        for row in self.db.execute('SELECT * FROM app_sources WHERE exposed=1'):
            ref=json.loads(row['receipt'])['evidence']
            if derive('event',scope,ref)==handle:found.append(ref)
        require(len(found)==1,'NOT_FOUND' if not found else 'CONFLICT')
        self.record(found[0])
        return make('event',scope,self.app.binding['principal'],found[0])
    def intent(self,command):
        cfg=self.authorize();memory=self.app.preview.memory.resolve(command[1])
        source=self.resolve_source(command[2])
        rows=self.db.execute('SELECT w.*,o.result FROM app_memory_writes w JOIN app_occurrences o ON o.id=w.id WHERE uuid=?',(memory['uuid'],)).fetchall()
        require(len(rows)==1,'NOT_FOUND' if not rows else 'CONFLICT');written=rows[0]
        require(written['result'] is not None and written['view'] is not None,'NOT_AVAILABLE')
        return dict(profile=n.PROFILE,operation=command[0],arguments=dict(target=command[1],source=command[2],
            memory=written['id'],uuid=written['uuid'],evidence=source['target'],context=cfg['context']))
    def validate_view(self,view):
        # Preserve owner-verified STV/provenance validation; structural display
        # labels are independently bound in this preview view, never evidence.
        checked=copy.deepcopy(view)
        for binding in checked.get('beliefs',[]):
            item=next(x for x in checked['metadata']['records'] if x['uuid']==binding['uuid'])
            expected=list(dict.fromkeys([binding['creation_time'],*[x['label'] for x in binding['sources']]]))
            structure=checked.get('handles',{}).get(binding['uuid'],{}).get('structure')
            declared=[x['history']['handle'] for x in structure['links']] if structure else []
            require(all(x in expected+declared for x in item['links']) and all(x in item['links'] for x in expected),'CONFLICT')
            item['links']=expected
        checked['metadata_seal']=digest(canonical(checked['metadata']))
        super().validate_view(checked)
        require(view['metadata_seal']==digest(canonical(view['metadata'])),'CONFLICT')
        return view
    def refresh(self,records,handles):
        old=self.db.execute('SELECT value FROM app_read_views WHERE id=(SELECT view FROM app_active_view)').fetchone()
        previous=json.loads(old[0]);bindings=[];defaults={}
        for item in records:
            prior=next((b for b in previous.get('beliefs',[]) if b['uuid']==item['uuid']),None)
            if prior is None:defaults[item['uuid']]=n.PRIOR+':not-registered';continue
            # A new input explicitly observes the latest committed owner view.
            snapshot=self.belief(prior['claim'],prior['context'],None);sources=[]
            for observation in snapshot['observations']:
                assessment=self.record(observation['evidence'])
                for ref in assessment['event']['provenance']:
                    source=self.record(ref);payload=self.modules.atoms.get(source['event']['payload'])
                    require(payload.content_type=='application/neoclaw-source','NOT_AVAILABLE')
                    sources.append(dict(ref=ref,label=json.loads(payload.bytes)['label']))
            binding=dict(prior,revision=snapshot['revision'],snapshot_digest=digest(canonical(snapshot)),sources=sources)
            item['stv']=[float(snapshot['truth'][k]) for k in ('strength','confidence')]
            item['links']=list(dict.fromkeys([prior['creation_time'],*[s['label'] for s in sources],*item['links']]))
            bindings.append(binding)
        return dict(beliefs=bindings,defaults=defaults)


class PreviewPriority(PriorityAdoption):
    def payload_view(self,key,deadline):
        self.authorize();view=self.view(key);items={}
        for uid,value in view['handles'].items():
            ref=value['envelope']['target']['payload'];payload=self.payload(ref,view)
            require(payload['uuid']==uid,'NOT_AVAILABLE')
            items[uid]=dict(ref=ref,time=payload['time'])
        require(set(items)=={r['uuid'] for r in view['metadata']['records']},'CONFLICT')
        return items
    def intent(self,command):
        self.authorize();key,view=self.active_view();value=self.app.preview.memory.resolve(command[1])
        return dict(profile=__import__('fusion.promotion_contracts',fromlist=['PROFILE']).PROFILE,
            operation=command[0],arguments=dict(alias=command[1],target=value['uuid'],view=key))
    def context_deadline(self):return self.app.preview.input.source()['deadline']
