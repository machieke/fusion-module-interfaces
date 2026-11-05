"""Fresh Registry representation inside the existing application owner.

Exact canonical values are reconstructed from finite immutable objects. Epochs
retain all action identities/results; sealing is representation maintenance,
never deletion of audit facts, readiness renewal or allowance replenishment.
"""
import json
from .contracts import canonical, digest, require

PROFILE='trusted-provider-lifecycle/2'
LIMITS=dict(objects=4096,object_bytes=1048576,active_bytes=196608,control_bytes=32768,
            active_actions=256,actions=4096,epochs=64,epoch_actions=64,retained_bytes=4194304)


def limits(value):
    require(type(value) is dict and set(value)==set(LIMITS),'UNSUPPORTED_PROFILE')
    for key,maximum in LIMITS.items():require(type(value[key]) is int and 1<=value[key]<=maximum)
    require(value['control_bytes']<value['active_bytes']<=value['retained_bytes'])
    return value


def present(db):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_registry_meta'").fetchone())


class Retention:
    def __init__(self,db,policy):
        self.db,self.limits=db,limits(policy)
        existing=present(db)
        if not existing:
            require(not db.execute('SELECT 1 FROM integrated_providers LIMIT 1').fetchone(),'UNSUPPORTED_PROFILE')
        db.executescript('''
          CREATE TABLE IF NOT EXISTS pilot_registry_meta(policy TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pilot_registry_objects(id TEXT PRIMARY KEY,body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pilot_registry_epochs(id TEXT PRIMARY KEY,provider TEXT NOT NULL,head TEXT NOT NULL,body TEXT NOT NULL,state TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS pilot_registry_action_index(id TEXT PRIMARY KEY,epoch TEXT NOT NULL,position INTEGER NOT NULL);
        ''')
        with db:
            old=db.execute('SELECT policy FROM pilot_registry_meta').fetchone()
            require(old is None or old[0]==canonical(policy).decode(),'CONFLICT')
            if old is None:db.execute('INSERT INTO pilot_registry_meta VALUES(?)',(canonical(policy).decode(),))

    def pack(self,value):
        require(self.db.in_transaction,'CONFLICT')
        def encode(v,depth=0):
            require(depth<=16,'OVERLOADED')
            if isinstance(v,dict):node=['dict',[[k,encode(x,depth+1)] for k,x in sorted(v.items())]]
            elif isinstance(v,list):node=['list',[encode(x,depth+1) for x in v]]
            else:return ['scalar',v]
            body=canonical(node).decode()
            # Small nodes remain inline. Larger nodes are content addressed,
            # preserving ordered lists and exact admitted conjunction bytes.
            if len(body)<256:return node
            key=digest(body.encode());row=self.db.execute('SELECT body FROM pilot_registry_objects WHERE id=?',(key,)).fetchone()
            if row:require(row[0]==body,'CONFLICT')
            else:self.db.execute('INSERT INTO pilot_registry_objects VALUES(?,?)',(key,body))
            return ['ref',key]
        raw=canonical(encode(value)).decode()
        count,size=self.db.execute('SELECT count(*),coalesce(sum(length(CAST(body AS BLOB))),0) FROM pilot_registry_objects').fetchone()
        require(count<=self.limits['objects'] and size<=self.limits['object_bytes'],'OVERLOADED')
        return raw

    def unpack(self,raw):return unpack(self.db,raw)

    def action(self,identity):
        row=self.db.execute('SELECT intent,result FROM integrated_provider_actions WHERE id=?',(identity,)).fetchone()
        if row:return dict(intent=canonical(self.unpack(row[0])).decode(),result=canonical(self.unpack(row[1])).decode())
        row=self.db.execute('SELECT epoch,position FROM pilot_registry_action_index WHERE id=?',(identity,)).fetchone()
        if row:
            segment=self.db.execute("SELECT body,head,state FROM pilot_registry_epochs WHERE id=?",(row[0],)).fetchone()
            require(segment and segment[2]=='sealed' and digest(segment[0].encode())==segment[1],'NOT_AVAILABLE')
            entry=json.loads(segment[0])[row[1]];require(entry['id']==identity,'NOT_AVAILABLE')
            return dict(intent=canonical(self.unpack(entry['intent'])).decode(),result=canonical(self.unpack(entry['result'])).decode())

    def usage(self):
        def total(sql):return self.db.execute(sql).fetchone()[0] or 0
        active=total('SELECT sum(length(CAST(intent AS BLOB))+length(CAST(result AS BLOB))+512) FROM integrated_provider_actions')
        objects=total('SELECT sum(length(CAST(body AS BLOB))) FROM pilot_registry_objects')
        epochs=total('SELECT sum(length(CAST(body AS BLOB))+length(id)+length(provider)+length(head)) FROM pilot_registry_epochs')
        index=total('SELECT sum(length(id)+length(epoch)+16) FROM pilot_registry_action_index')
        projections=total('SELECT sum(length(CAST(record AS BLOB))+coalesce(length(CAST(readiness AS BLOB)),0)) FROM integrated_providers')+total('SELECT sum(length(CAST(selection AS BLOB))) FROM integrated_provider_bindings')
        actions=total('SELECT count(*) FROM integrated_provider_actions')
        retained=total('SELECT count(*) FROM pilot_registry_action_index')
        return dict(active_bytes=active,object_bytes=objects,retained_bytes=active+objects+epochs+index+projections,
                    active_actions=actions,actions=actions+retained,epochs=total('SELECT count(*) FROM pilot_registry_epochs'),
                    objects=total('SELECT count(*) FROM pilot_registry_objects'))

    def baseline_equivalent(self):
        """Reconstruct the former byte charge; never a physical storage claim."""
        total=0
        for record,readiness in self.db.execute('SELECT record,readiness FROM integrated_providers'):
            total+=len(canonical(self.unpack(record)))+(len(readiness.encode()) if readiness else 0)
        for (selection,) in self.db.execute('SELECT selection FROM integrated_provider_bindings'):
            total+=len(canonical(self.unpack(selection)))
        for intent,result in self.db.execute('SELECT intent,result FROM integrated_provider_actions'):
            total+=len(canonical(self.unpack(intent)))+len(canonical(self.unpack(result)))
        for body,head,state in self.db.execute('SELECT body,head,state FROM pilot_registry_epochs'):
            if state!='sealed':continue
            require(digest(body.encode())==head,'NOT_AVAILABLE')
            for item in json.loads(body):
                total+=len(canonical(self.unpack(item['intent'])))+len(canonical(self.unpack(item['result'])))
        return dict(bytes=total,former_limit_bytes=1048576,
            basis='RECONSTRUCTED_RECORDS_READINESS_ACTIONS_SELECTIONS_NOT_PHYSICAL_BYTES')

    def charge(self,extra,control=False):
        u=self.usage();p=self.limits
        reserve=0 if control else min(32,max(1,p['active_actions']//4))
        require(u['actions']<p['actions']-reserve and u['active_actions']<p['active_actions']-reserve,'OVERLOADED')
        require(u['active_bytes']+extra+1024<=p['active_bytes']-(0 if control else p['control_bytes']),'OVERLOADED')
        # Retention includes finite slack to finish each probe and a bounded
        # epoch plan/publication. Normal actions cannot spend control reserve.
        require(u['retained_bytes']+extra+1024<=p['retained_bytes']-(p['control_bytes']//2 if control else p['control_bytes']),'OVERLOADED')

    def preview(self,key):
        entries=[]
        for row in self.db.execute('SELECT * FROM integrated_provider_actions ORDER BY id'):
            intent=self.unpack(row['intent']);result=self.unpack(row['result'])
            if intent['provider']!=key or result.get('status')=='unknown':continue
            candidate=dict(id=row['id'],intent=row['intent'],result=row['result'])
            if len(canonical(entries+[candidate]))>self.limits['control_bytes']//2-1024:break
            entries.append(candidate)
            if len(entries)==self.limits['epoch_actions']:break
        require(entries,'NOT_AVAILABLE');body=canonical(entries).decode()
        return dict(provider=key,body=body,head=digest(body.encode()))

    def plan_seal(self,identity,key,expected=None):
        old=self.db.execute('SELECT * FROM pilot_registry_epochs WHERE id=?',(identity,)).fetchone()
        if old:
            require(old['provider']==key and (expected is None or old['head']==expected),'CONFLICT');return dict(old)
        preview=self.preview(key);body=preview['body']
        require(expected is None or preview['head']==expected,'CONFLICT');u=self.usage()
        require(u['epochs']<self.limits['epochs'] and u['retained_bytes']+len(body.encode())+1024<=self.limits['retained_bytes'],'OVERLOADED')
        self.db.execute('INSERT INTO pilot_registry_epochs VALUES(?,?,?,?,?)',(identity,key,digest(body.encode()),body,'planned'))
        return dict(id=identity,provider=key,head=digest(body.encode()),body=body,state='planned')

    def apply_seal(self,plan):
        require(digest(plan['body'].encode())==plan['head'],'NOT_AVAILABLE')
        if plan['state']=='sealed':return
        for index,item in enumerate(json.loads(plan['body'])):
            row=self.db.execute('SELECT intent,result FROM integrated_provider_actions WHERE id=?',(item['id'],)).fetchone()
            require(row and row[0]==item['intent'] and row[1]==item['result'],'CONFLICT')
            self.db.execute('INSERT INTO pilot_registry_action_index VALUES(?,?,?)',(item['id'],plan['id'],index))
            self.db.execute('DELETE FROM integrated_provider_actions WHERE id=?',(item['id'],))
        self.db.execute("UPDATE pilot_registry_epochs SET state='sealed' WHERE id=?",(plan['id'],))


def unpack(db,raw):
    visited=[0]
    def decode(node,depth=0):
        visited[0]+=1;require(depth<=32 and visited[0]<=65536,'NOT_AVAILABLE')
        require(type(node) is list and len(node)==2,'NOT_AVAILABLE');kind,body=node
        if kind=='ref':
            row=db.execute('SELECT body FROM pilot_registry_objects WHERE id=?',(body,)).fetchone()
            require(row is not None and digest(row[0].encode())==body,'NOT_AVAILABLE')
            return decode(json.loads(row[0]),depth+1)
        if kind=='dict':return {k:decode(v,depth+1) for k,v in body}
        if kind=='list':return [decode(v,depth+1) for v in body]
        require(kind=='scalar','NOT_AVAILABLE');return body
    return decode(json.loads(raw))


def retained_charge(db):
    # Added to the application's existing finite owner-byte accounting.
    total=0
    for table,columns in [('pilot_registry_objects',['body']),('pilot_registry_epochs',['id','provider','head','body']),('pilot_registry_action_index',['id','epoch'])]:
        sql='SELECT coalesce(sum('+ '+'.join('length(CAST('+c+' AS BLOB))' for c in columns)+'),0) FROM '+table
        total+=db.execute(sql).fetchone()[0]
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='pilot_registry_upgrade_originals'").fetchone():
        columns=[r[1] for r in db.execute('PRAGMA table_info(pilot_registry_upgrade_originals)')]
        require(all(c.replace('_','').isalnum() for c in columns),'NOT_AVAILABLE')
        total+=db.execute('SELECT coalesce(sum('+ '+'.join('coalesce(length(CAST('+c+' AS BLOB)),0)' for c in columns)+'),0) FROM pilot_registry_upgrade_originals').fetchone()[0]
    return total
