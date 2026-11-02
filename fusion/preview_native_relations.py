"""Native structural actions over owned Relations, C1 and immutable atoms.

No timestamp aliases, Chroma mutation, evidence revision or reference casts.
Application acceptances bind the actual endpoints/CAS, owner receipts remain
independently committed. Relation handles are discovered from real traversals.
"""
import json
import time
from .contracts import ContractError,canonical,digest,require,validate_ref
from .ports import Mutation
from .preview_handles import parse,make,envelope
from .preview_relations import PROFILE
from . import lookup_contracts as c

SCHEMAS={name:dict(roles=['memory',role],origins=[0],destinations=[1],directed=True)
    for name,role in [('memory-event/1','event'),('memory-episode/1','episode')]}
ENDPOINT='application/omega-history-handle-v1'


class NativeRelations:
    def __init__(self,app,port):
        self.app,self.db,self.port=app,app.db,port;self.scope=app.preview_config['scope']
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS preview_link_acceptances(id TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_link_handles(handle TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_link_calls(id TEXT PRIMARY KEY,calls INTEGER NOT NULL DEFAULT 0);
        ''')

    def call(self,row,op,*args):
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO preview_link_calls(id) VALUES(?)',(row['id'],))
            used=self.db.execute('SELECT calls FROM preview_link_calls WHERE id=?',(row['id'],)).fetchone()[0]
            require(used<16,'OVERLOADED')
            require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
            self.db.execute('UPDATE preview_link_calls SET calls=calls+1 WHERE id=?',(row['id'],))
        self.app.hook('after_relation_rpc_reservation')
        return self.port.call(op,*args,deadline=row['deadline'])

    def checked(self,value):
        try:return self._checked(value)
        except (KeyError,TypeError,ValueError,ContractError):
            raise ContractError('NOT_AVAILABLE') from None

    def _checked(self,value):
        require(type(value) is dict and set(value) in ({'profile','ref','body','asserted_at','state'},
            {'profile','ref','body','asserted_at','state','retracted_at'}) and value.get('profile')==PROFILE,'NOT_AVAILABLE')
        require(value['state']=='asserted' and value.get('retracted_at') is None,'NOT_AVAILABLE')
        c.head(value['asserted_at'],self.scope,PROFILE)
        require(value['asserted_at']['sequence']>0,'NOT_AVAILABLE')
        validate_ref(value['ref'],self.scope)
        body=value['body'];require(type(body) is dict and set(body)=={'profile','assertion_id','structure'} and body['profile']==PROFILE,'NOT_AVAILABLE')
        require(type(body['assertion_id']) is str and len(body['assertion_id'])==64,'NOT_AVAILABLE')
        require(type(body['structure']) is dict and set(body['structure'])=={'profile','scope_ref','relation_type','schema','roles','directed'},'NOT_AVAILABLE')
        structure=body['structure'];schema=SCHEMAS.get(structure['relation_type'])
        require(schema is not None and structure['schema']==schema and structure['directed'] is True,'NOT_AVAILABLE')
        require([r[0] for r in structure['roles']]==schema['roles'],'NOT_AVAILABLE')
        for _,ref in structure['roles']:validate_ref(ref,self.scope)
        require(digest(canonical(body))==value['ref']['digest'],'NOT_AVAILABLE')
        handle=make('relation',self.scope,self.app.binding['principal'],value['ref'])
        encoded=canonical(value).decode()
        with self.db:
            old=self.db.execute('SELECT value FROM preview_link_handles WHERE handle=?',(handle['handle'],)).fetchone()
            if old:
                prior=json.loads(old[0]);require(prior['body']==body and prior['asserted_at']==value['asserted_at'],'CONFLICT')
            self.db.execute('INSERT OR REPLACE INTO preview_link_handles VALUES(?,?)',(handle['handle'],encoded))
        return handle

    def admit(self,occurrence,op,args):
        if op=='link':
            memory=self.app.preview.memory.resolve(args['memory'])
            history=self.app.preview.history.resolve(args['history'])
            value=dict(memory=memory,history=history)
        else:
            parse(args['relation'],'relation')
            old=self.db.execute('SELECT value FROM preview_link_handles WHERE handle=?',(args['relation'],)).fetchone()
            require(old is not None,'NOT_FOUND');value=json.loads(old[0])
            require(value['state']=='asserted','CONFLICT')
        self.db.execute('INSERT INTO preview_link_acceptances VALUES(?,?)',(occurrence,canonical(value).decode()))

    def replay(self,row,op):
        require(self.port.call('authorize','assertRelation' if op=='link' else 'retract')=={'authorized':True},'UNAUTHORIZED')
        value=json.loads(self.db.execute('SELECT value FROM preview_link_acceptances WHERE id=?',(row['id'],)).fetchone()[0])
        if op=='link':
            memory=value['memory'];history=envelope(value['history'],scope=self.scope,principal=self.app.binding['principal'])
            self.app.preview.history.resolve(history['handle'])
            self.app.preview.memory.clients['memory.lifecycle'].call('disclose',memory['logical_id'],
                dict(uuid=memory['uuid'],payload=memory['envelope']['target']['payload'],enrollment=memory['envelope']['target']['enrollment']),
                self.app.preview.memory.clients['memory.lifecycle'].call('head'),False)
            if row['result'] is not None:return row['result']
            require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
            # Stable principal-neutral wrapper, scoped and verified by C1 above.
            wrapper={k:v for k,v in history.items() if k!='principal'}
            endpoint=self.app.preview.memory.atoms(row['deadline']).create(
                Mutation(self.scope,'history-endpoint/'+digest(canonical(wrapper))),ENDPOINT,canonical(wrapper))['ref']
            self.app.hook('after_relation_endpoint')
            kind=history['kind'];schema='memory-'+kind+'/1'
            result=self.call(row,'assertRelation',Mutation(self.scope,row['id']),schema,
                [['memory',memory['envelope']['target']['payload']],[kind,endpoint]],True)
            require(type(result) is dict and type(result.get('body')) is dict,'NOT_AVAILABLE')
            require(result['body'].get('assertion_id')==digest(canonical([self.app.binding['principal'],self.scope,row['id']]))
                and result['body'].get('structure')==c.relation_body(self.scope,schema,
                    (('memory',memory['envelope']['target']['payload']),(kind,endpoint)),True,SCHEMAS),'NOT_AVAILABLE')
            handle=self.checked(result)
            return canonical(dict(status='LINKED',relation=handle,asserted_at=result['asserted_at'],
                history=history,memory=memory['envelope'],evidence_changed=False)).decode()
        # A saved retraction still checks current relation and historical-read authority.
        observed=self.port.call('getRelation',value['ref'],True)
        require(observed['body']==value['body'] and observed['asserted_at']==value['asserted_at'],'NOT_AVAILABLE')
        if row['result'] is not None:return row['result']
        result=self.call(row,'retract',Mutation(self.scope,row['id']),value['ref'],value['asserted_at'])
        require(type(result) is dict and set(result)=={'profile','ref','state','at','effect','evidence_changed','payload_erased'},'NOT_AVAILABLE')
        require(result['profile']==PROFILE and result['ref']==value['ref'] and result['state']=='retracted'
            and result['effect']=='structural-only' and result['evidence_changed'] is False and result['payload_erased'] is False,'NOT_AVAILABLE')
        c.head(result['at'],self.scope,PROFILE)
        require(result['at']['source']==value['asserted_at']['source'] and result['at']['sequence']>value['asserted_at']['sequence'],'NOT_AVAILABLE')
        self.app.hook('after_native_retraction_receipt')
        return canonical(dict(status='STRUCTURALLY_RETRACTED',relation=make('relation',self.scope,
            self.app.binding['principal'],value['ref']),receipt=result)).decode()

    def presentation(self,payload):
        # Scope-authorized structural labels are not permission to read another
        # agent's C1 body. Recheck C1 read authority even for immutable wrappers.
        history=self.app.preview.history
        history.port.call('historySnapshot',history.episode())
        page=self.port.call('outgoing',payload,8,None,None)
        require(page['profile']==PROFILE and page['page_complete'] is True and page['cursor'] is None,'OVERLOADED')
        values=[]
        for ref in page['refs']:
            result=self.port.call('getRelation',ref,False)
            require(result['ref']==ref and result['state']=='asserted','NOT_AVAILABLE')
            handle=self.checked(result);structure=result['body']['structure']
            require(structure['roles'][0][1]==payload,'NOT_AVAILABLE')
            endpoint=self.app.preview.memory.atoms().get(structure['roles'][1][1])
            require(endpoint.content_type==ENDPOINT,'NOT_AVAILABLE')
            stored=json.loads(endpoint.bytes)
            declared=envelope(dict(stored,principal=self.app.binding['principal']),scope=self.scope)
            values.append(dict(relation=handle,history=declared,asserted_at=result['asserted_at']))
        return dict(snapshot=page['at'],links=values)
