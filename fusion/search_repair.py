"""Bounded repair of one retained Search projection from authoritative ports.

Only derived Chroma/manifest bytes may be rebuilt. Source records, vectors,
payloads, lifecycle, captured queries and spent effects are never rewritten.
Corrupt database containers require offline diagnosis, not automatic deletion.
"""
import json,time,uuid
from .contracts import canonical,digest,require,ContractError,label
from . import preview_vector_contracts as c,vector_contracts as v
from .registry import Descriptor
from .adapters.chroma_vector import publish

from .preview_deployment_contracts import SEARCH_MAINTENANCE_PROFILE as PROFILE
LIMITS=dict(source_records=2048,index_records=c.MAX_RECORDS,attempts=3,repairs=32,window_ms=120000)


def descriptor():
    return Descriptor('preview-derived-search-maintenance','search','3.3.0','1.0.0',
        frozenset({PROFILE}),frozenset({'planRepair','repair','observeRepair'}),
        frozenset({'scoped','process-restart','idempotent','no-authoritative-repair'}),16384,
        privacy=v.PRIVACY,features=frozenset({c.PROFILE,v.EMBEDDING,v.INDEX}))


class Repair:
    def __init__(self,search):self.search=search

    def selected(self,snapshot):
        owner=self.search;owner.access.authorize(owner.scope,'ready');c.snapshot(snapshot,owner.scope)
        require(snapshot['embedding']==owner.embedding and snapshot['corpus']==owner.corpus and
            snapshot['profile']==c.PROFILE and all(snapshot.get(k)==value for k,value in owner._snapshot_extension().items()),'UNSUPPORTED_PROFILE')
        require(snapshot['head']['sequence']<=LIMITS['source_records'],'OVERLOADED')
        path=owner.root/snapshot['generation'];require(not path.is_symlink(),'UNAUTHORIZED')
        try:
            publication=owner.root/'published.json';require(not publication.is_symlink() and publication.stat().st_size<=131072,'NOT_AVAILABLE')
            data=json.loads(publication.read_bytes())
        except (OSError,ValueError):raise ContractError('NOT_AVAILABLE') from None
        require(type(data) is dict and type(data.get('generations')) is dict and
            data['generations'].get(snapshot['generation'])==snapshot,'NOT_AVAILABLE')
        return path

    def plan(self,snapshot):
        owner=self.search;directory=self.selected(snapshot);manifest=directory/'manifest.json';index=directory/'index';database=index/'chroma.sqlite3'
        require(not manifest.is_symlink() and not index.is_symlink() and not database.is_symlink(),'UNAUTHORIZED')
        hashed=None
        if manifest.exists():
            require(manifest.stat().st_size<=131072,'OVERLOADED');hashed=digest(manifest.read_bytes())
        if not database.exists():problem='MISSING_DERIVED_INDEX'
        else:
            with database.open('rb') as stream:header=stream.read(16)
            problem='CORRUPT_DERIVED_INDEX' if header!=b'SQLite format 3\x00' else 'DERIVED_INDEX_UNVERIFIED'
        if hashed is None and problem=='DERIVED_INDEX_UNVERIFIED':problem='MISSING_DERIVED_MANIFEST'
        value=dict(profile=PROFILE,scope=owner.scope,snapshot=snapshot,manifest_sha256=hashed,
            classification=problem,limits=dict(LIMITS),authority='replayable-owner-feed-and-lifecycle',
            physical_erasure=False,effect_replay=False,capacity_refund=False,
            supported=problem!='CORRUPT_DERIVED_INDEX')
        owner.access.authorize(owner.scope,'ready');return dict(plan=value,plan_sha256=digest(canonical(value)))

    def validate(self,plan):
        require(type(plan) is dict and set(plan)=={'plan','plan_sha256'})
        value=plan['plan'];require(type(value) is dict and set(value)==set('profile scope snapshot manifest_sha256 classification limits authority physical_erasure effect_replay capacity_refund supported'.split()))
        require(value['profile']==PROFILE and value['scope']==self.search.scope and value['limits']==LIMITS,'UNSUPPORTED_PROFILE')
        require(value['authority']=='replayable-owner-feed-and-lifecycle' and value['physical_erasure'] is False and
            value['effect_replay'] is False and value['capacity_refund'] is False,'UNAUTHORIZED')
        require(value['classification'] in ('MISSING_DERIVED_INDEX','CORRUPT_DERIVED_INDEX','DERIVED_INDEX_UNVERIFIED','MISSING_DERIVED_MANIFEST'))
        require(value['supported']==(value['classification']!='CORRUPT_DERIVED_INDEX') and type(value['supported']) is bool)
        require(value['manifest_sha256'] is None or (type(value['manifest_sha256']) is str and
            len(value['manifest_sha256'])==64 and all(x in '0123456789abcdef' for x in value['manifest_sha256'])))
        require(plan['plan_sha256']==digest(canonical(value)),'CONFLICT');self.selected(value['snapshot'])
        return value

    def location(self,principal,identity,plan):
        require(label(identity))
        # One operator occurrence cannot silently become another generation's
        # maintenance request by changing the selected snapshot.
        key=str(uuid.uuid5(uuid.NAMESPACE_URL,canonical([PROFILE,plan['scope'],principal,identity]).decode()))
        path=self.search.root/('repair-'+key+'.json');require(not path.is_symlink(),'UNAUTHORIZED');return path

    def observe(self,plan,identity):
        owner=self.search;principal=owner.access.authorize(owner.scope,'ready');value=self.validate(plan);path=self.location(principal,identity,value)
        if not path.exists():return dict(state='absent',identity=identity,plan_sha256=plan['plan_sha256'])
        require(path.stat().st_size<=32768,'OVERLOADED');record=json.loads(path.read_bytes())
        require(record['intent']['plan']==plan and record['intent']['principal']==principal and record['intent']['identity']==identity,'CONFLICT')
        owner.access.authorize(owner.scope,'ready')
        return dict(state='verified' if record['result'] else 'needs-reconciliation',identity=identity,
            plan_sha256=plan['plan_sha256'],deadline_ms=record['intent']['deadline_ms'],attempts_spent=record['attempts'],
            result=record['result'])

    def apply(self,plan,identity,deadline):
        owner=self.search;principal=owner.access.authorize(owner.scope,'build');value=self.validate(plan)
        require(value['supported'],'NOT_AVAILABLE');require(type(deadline) is int and 0<deadline<2**53)
        path=self.location(principal,identity,value);intent=dict(plan=plan,identity=identity,principal=principal,deadline_ms=deadline)
        with owner._lock():
            if path.exists():
                require(path.stat().st_size<=32768,'OVERLOADED')
                record=json.loads(path.read_bytes());require(record['intent']==intent,'CONFLICT')
            else:
                now=time.time_ns()//1000000;require(now<deadline<=now+LIMITS['window_ms'],'DEADLINE_EXCEEDED')
                require(len(list(owner.root.glob('repair-*.json')))<LIMITS['repairs'],'OVERLOADED')
                require(self.plan(value['snapshot'])==plan,'CONFLICT')
                record=dict(intent=intent,attempts=0,result=None);publish(path,record)
            if record['result'] is not None:
                owner.ready(owner.scope,value['snapshot']);return self.observe(plan,identity)
            # Source identity/head is checked before any derived write. Provider
            # outage is unknown, never an empty index or a new source identity.
            owner._head(owner.scope,value['snapshot']['head'])
            verified=None
            if record['attempts']:
                try:verified=owner._verified(value['snapshot']['generation'],value['snapshot']['head'])['snapshot']
                except ContractError as error:
                    if error.code!='NOT_AVAILABLE':raise
            if verified is None:
                owner._deadline(deadline);require(record['attempts']<LIMITS['attempts'],'OVERLOADED')
                record['attempts']+=1;publish(path,record);owner.hook('after_search_repair_reservation')
                verified=owner._project(owner.scope,value['snapshot']['head'],value['snapshot']['generation'],deadline,rebuild=True)
            require(verified==value['snapshot'],'CONFLICT');owner.access.authorize(owner.scope,'build')
            record['result']=dict(profile=PROFILE,identity=identity,snapshot=verified,source='authoritative-feed-replay',
                captured_queries_rewritten=False,capacity_refund=False,original_generation_retained=True)
            publish(path,record);owner.hook('after_search_repair_capture')
            return self.observe(plan,identity)
