"""Selected S04 local NAL contracts. Historical PLN DTOs remain unchanged."""
from dataclasses import asdict, dataclass
from decimal import Decimal
from . import memory_contracts as m
from .memory_contracts import (boundary, detached, response_copy, response, fields, integer,
    identifier, mutation, roots, independence, evidence_ref, episode_ref, grounded_claim,
    decimal, atom_write, delivery, MAX_EVENTS, MAX_PAGE, MAX_PENDING, MAX_SUPPORTS)
from .contracts import canonical, digest, require, validate_ref
from .ports import Mutation, EvidenceSubmission
from typing import Protocol
from .ports import EpisodeJournal

APPLICATION = 'controlled-native-loop/6'
PROFILE = 'neoclaw-episodic-assessment/1'
EPISODE_PROFILE = 'neoclaw-local-source-assessment/1'
BELIEF_PROFILE = 'neoclaw-nal-revision-private/1'
MODEL = 'neoclaw-nal-stv-capped-099/1'
RUNTIME = 'neoclaw-petta-swi-10.0.1-revision/1'
INGESTION = 'neoclaw-sign-half-confidence/1'
PRIOR = 'neoclaw-fresh-memory-compatibility-prior/1'
FORMULA = 'mettaclaw/2af37c3fec18613de54ca42fde2382a9087d4524/Truth_Revision'
MAX_EVALUATIONS, MAX_APP_ATTEMPTS = 3, 96


@dataclass(frozen=True, kw_only=True)
class Admission(EvidenceSubmission):
    work_id: str
    deadline_ms: int
    max_evaluations: int


class SourceJournal(EpisodeJournal, Protocol):
    def occurrenceIdentity(self, command: Mutation, episode: dict) -> str: ...
    def readOccurrence(self, episode: dict, occurrence: str) -> dict | None: ...


class LocalNALBeliefs(Protocol):
    def registerPrior(self, command: Mutation, claim: dict, context: str,
                      creation: dict, deadline_ms: int) -> dict: ...
    def submitEvidence(self, request: Admission) -> dict: ...
    def observeDecision(self, request: Admission) -> dict | None: ...
    def readBelief(self, claim: dict, context: str, revision: int | None) -> dict: ...


class LocalRevision(Protocol):
    def profile(self) -> dict: ...
    def revise(self, existing: dict, incoming: dict, revision: int,
               independence: dict | None, *, deadline_ms: int) -> dict: ...


def truth(value):
    fields(value, 'model strength confidence evidence_count')
    require(value['model'] == MODEL, 'UNSUPPORTED_PROFILE')
    require(value['evidence_count'] is None)
    decimal(value['strength']); decimal(value['confidence'], True)


def stv(strength, confidence):
    value = dict(model=MODEL, strength=strength, confidence=confidence, evidence_count=None)
    truth(value); return value


def numerical(value, scope):
    fields(value, 'claim context relationship truth ingestion_profile')
    validate_ref(value['claim'], scope); identifier(value['context'])
    require(value['relationship'] in ('supports', 'contradicts'))
    require(value['ingestion_profile'] == INGESTION, 'UNSUPPORTED_PROFILE')
    truth(value['truth'])
    require(value['truth'] == stv('1.0' if value['relationship']=='supports' else '0.0', '0.5'))


def event(value, scope):
    fields(value, 'occurrence_id kind source observed_time payload causation provenance numerical deadline_ms')
    # Reuse the historical structural validator without impersonating its model.
    plain = {k:v for k,v in value.items() if k!='deadline_ms'}
    plain['numerical'] = None
    m.event(plain, scope); integer(value['deadline_ms'], 1)
    if value['numerical'] is not None:
        numerical(value['numerical'], scope)
        require(value['kind']=='action' and len(value['provenance'])==1)
    else: require(value['kind']=='observation')


def evidence_record(value, expected):
    fields(value, 'evidence event lineage_roots'); evidence_ref(value['evidence'])
    require(value['evidence']==expected)
    event(value['event'], expected['episode']['scope_ref'])
    require(value['event']['occurrence_id']==expected['occurrence_id'])
    roots(value['lineage_roots'], True)


def append_receipt(value):
    fields(value,'evidence head delivery_id persistence');evidence_ref(value['evidence'])
    require(value['head']==value['evidence']['sequence'] and value['persistence']=='process-restart')
    require(value['delivery_id'] in (None,digest(canonical(value['evidence']))))


def occurrence_reply(value,episode,occurrence):
    if value is None:return None
    value=response_copy(value);fields(value,'record receipt')
    append_receipt(value['receipt']);evidence_record(value['record'],value['receipt']['evidence'])
    ref=value['receipt']['evidence'];require(ref['episode']==episode and ref['occurrence_id']==occurrence)
    require((value['receipt']['delivery_id'] is None)==(value['record']['event']['numerical'] is None))
    return value


def episode_page(value, ref, start, limit):
    fields(value, 'ref head events next_sequence complete'); require(value['ref']==ref)
    integer(value['head'], 0, MAX_EVENTS)
    require(type(value['events']) is list and len(value['events'])<=limit)
    for n, record in enumerate(value['events'], start):
        evidence_record(record, record['evidence'])
        require(record['evidence']['episode']==ref and record['evidence']['sequence']==n)
    following=start+len(value['events'])
    require(type(value['complete']) is bool and value['complete']==(following>value['head']))
    require(value['next_sequence']==(None if value['complete'] else following))
    require(value['complete'] or len(value['events'])==limit)


def submission(value):
    require(type(value) is Admission); mutation(value.command)
    validate_ref(value.claim,value.command.scope_ref); identifier(value.context)
    require(value.evidence is not None and value.support_id is None)
    evidence_ref(value.evidence,value.command.scope_ref); integer(value.expected_revision)
    require(value.profile==BELIEF_PROFILE,'UNSUPPORTED_PROFILE')
    from .delivery_contracts import sha
    sha(value.runtime_selection); identifier(value.work_id); integer(value.deadline_ms,1)
    require(value.work_id==digest(canonical(value.evidence)), 'CONFLICT')
    require(value.max_evaluations==MAX_EVALUATIONS)
    if value.independence is not None: independence(value.independence)
    return detached(asdict(value))


def request(semantic):
    return Admission(**{**semantic, 'command': Mutation(**semantic['command'])})


def prior_id(claim,context,creation): return 'prior/'+digest(canonical([PRIOR,claim,context,creation]))
def contribution(record):
    # The source occurrence is preserved even for unknown lineage; copies with
    # verified roots share contribution identity. Opposite assessments differ.
    n=record['event']['numerical']
    source=record['lineage_roots'] or record['event']['provenance']
    return 'assessment/'+digest(canonical([source,n]))


def support(value,scope):
    common='id claim context truth evidence_ids lineage_roots coverage premises formula assumptions kind'
    fields(value,common+(' creation' if value.get('kind')=='prior' else ' representation' if value.get('kind')=='revision' else ''))
    identifier(value['id']); identifier(value['context']); validate_ref(value['claim'],scope); truth(value['truth'])
    for key in ('evidence_ids','lineage_roots','coverage'): roots(value[key],value['kind']=='prior')
    require(type(value['assumptions']) is list and len(value['assumptions'])<=8)
    for a in value['assumptions']: require(type(a) is str and 0<len(a)<=256)
    kind=value['kind']; require(kind in ('prior','observation','revision'))
    if kind=='prior':
        validate_ref(value['creation'],scope)
        require(value['id']==prior_id(value['claim'],value['context'],value['creation']))
        require(value['truth']==stv('1.0','0.5') and value['assumptions']==[PRIOR])
        require(value['premises']==[] and value['formula'] is None)
        require(all(value[k]==[] for k in ('evidence_ids','lineage_roots','coverage')))
    elif kind=='observation':
        require(value['premises']==[] and value['formula'] is None and value['assumptions']==[])
        require(value['coverage']==[value['id']] and len(value['evidence_ids'])==1)
    else:
        require(type(value['premises']) is list and len(value['premises'])==2 and len(set(value['premises']))==2)
        require(value['formula']==FORMULA and value['assumptions'])
        parsed=native_truth(value['representation']); require(parsed==value['truth'])


def native_truth(representation):
    from .neoclaw_contracts import native_truth as parse
    value=stv(**parse(representation))
    require(Decimal(value['confidence'])<=Decimal('0.99'),'NOT_AVAILABLE')
    return value


def snapshot(value,claim,context,runtime_selection):
    fields(value,'claim context revision truth aggregate covered_supports alternatives supports observations model runtime_selection')
    require(value['claim']==claim and value['context']==context and value['runtime_selection']==runtime_selection)
    from .delivery_contracts import sha
    sha(runtime_selection); require(value['model']==MODEL,'UNSUPPORTED_PROFILE'); integer(value['revision'])
    require(type(value['supports']) is list and len(value['supports'])<=MAX_SUPPORTS*2)
    prior={}; priors=[]
    for s in value['supports']:
        support(s,claim['scope_ref']); require(s['claim']==claim and s['context']==context and s['id'] not in prior)
        if s['kind']=='prior': priors.append(s)
        if s['kind']=='revision':
            require(set(s['premises'])<=set(prior)); a,b=[prior[x] for x in s['premises']]
            for k in ('coverage','evidence_ids','lineage_roots'): require(s[k]==sorted(set(a[k])|set(b[k])))
            require(not set(a['lineage_roots']) & set(b['lineage_roots']))
            require(not set(a['evidence_ids']) & set(b['evidence_ids']))
        prior[s['id']]=s
    require(len(priors)<=1)
    roots(value['covered_supports'],True); roots(value['alternatives'],True)
    leaves={s['id'] for s in value['supports'] if s['kind']=='observation'}
    require(set(value['covered_supports'])<=leaves and value['alternatives']==sorted(leaves-set(value['covered_supports'])))
    if value['aggregate'] is None: require(value['truth'] is None and not value['covered_supports'])
    else:
        require(value['aggregate'] in prior); a=prior[value['aggregate']]
        require(value['truth']==a['truth'] and value['covered_supports']==a['coverage'])
    require(type(value['observations']) is list and len(value['observations'])<=MAX_SUPPORTS)
    seen=set()
    for o in value['observations']:
        fields(o,'evidence relationship truth support_id lineage_roots contribution')
        evidence_ref(o['evidence'],claim['scope_ref']); identifier(o['contribution'])
        require(o['contribution'] not in seen); seen.add(o['contribution'])
        require(o['relationship'] in ('supports','contradicts')); truth(o['truth']); roots(o['lineage_roots'],True)
        if o['support_id'] is not None:
            require(o['support_id'] in prior); s=prior[o['support_id']]
            require(s['kind']=='observation' and s['id']==o['contribution'] and s['truth']==o['truth'])
            require(s['lineage_roots']==o['lineage_roots'] and s['evidence_ids']==[digest(canonical(o['evidence']))])
    require(len(canonical(value))<=262144)


def decision(value,claim,context,runtime_selection):
    fields(value,'decision_id evidence support_id admission numerical detail snapshot'); identifier(value['decision_id'])
    evidence_ref(value['evidence'],claim['scope_ref'])
    if value['support_id'] is not None: identifier(value['support_id'])
    require(value['admission'] in ('admitted','duplicate'))
    require(value['numerical'] in ('revised','no-change','retained-alternative','model-inapplicable'))
    require(type(value['detail']) is str and len(value['detail'])<=256)
    snapshot(value['snapshot'],claim,context,runtime_selection)


def snapshot_reply(value,claim,context):
    value=response_copy(value); response(snapshot,value,claim,context,value['runtime_selection']); return value


def math_result(value,a,b,declaration):
    fields(value,'status detail proposal'); require(value['status'] in ('PASS','FAIL','UNKNOWN'))
    require(type(value['detail']) is str and len(value['detail'])<=256)
    p=value['proposal']
    if p is None: require(value['status']!='PASS'); return
    require(value['status']=='PASS' and declaration is not None)
    independence(declaration); require(set(declaration['supports'])=={a['id'],b['id']})
    require(not set(a['lineage_roots']) & set(b['lineage_roots']) and not set(a['evidence_ids']) & set(b['evidence_ids']))
    support(p,a['claim']['scope_ref']); require(p['kind']=='revision' and p['claim']==a['claim']==b['claim'] and p['context']==a['context']==b['context'])
    require(p['premises']==[a['id'],b['id']] and p['id'] not in p['premises'])
    for k in ('coverage','evidence_ids','lineage_roots'): require(p[k]==sorted(set(a[k])|set(b[k])))
