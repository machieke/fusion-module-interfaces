"""M3 closed local contracts. M2's validators and profiles remain unchanged."""
from dataclasses import asdict, replace
from . import memory_contracts as m
from .memory_contracts import (boundary, detached, response_copy, response, fields, integer, identifier,
    mutation, truth, roots, independence, evidence_ref, evidence_record, grounded_claim, decimal,
    MAX_SUPPORTS, MODEL)
from .contracts import canonical, digest, require, validate_ref
from .ports import DerivationSubmission, InferenceRequest, WorkBudget

BELIEF_PROFILE = 'pln-derived-private/1'
RULE = 'grounded-five-premise-deduction/1'
WORKSET = 'bounded-explicit-workset/1'
CONTROL = 'bounded-grounded-inference/1'
RUNTIME = 'fusion-petta-swi-10.1.14-deduction/1'
COVERAGE = 'local-admitted-supports/1'
PREFIX = 'trueagi-pln/4405956947c4b53c7ff01bd565aa3b114bc970a1/'
ROLES = ('p','q','r','pq','qr','pr')
ASSUMPTIONS = ['upstream-heuristic-deduction', 'upstream-q>0.9999-uses-r']
MAX_TASKS, MAX_STEPS = 16, 128


def submission(value):
    require(value.profile == BELIEF_PROFILE, 'UNSUPPORTED_PROFILE')
    m.submission(replace(value, profile=m.BELIEF_PROFILE))
    return detached(asdict(value))


def literal(value):
    grounded_claim(value)
    require(value['predicate'] in ('pln:proposition','pln:implication') and value['positive'])
    require(len(value['arguments']) == (1 if value['predicate']=='pln:proposition' else 2))
    for entity in value['arguments']: require(len(entity)==64 and all(x in '0123456789abcdef' for x in entity))


def claim_literal(ref, record):
    grounded_claim(record)
    require(digest(canonical(record)) == ref['digest'])
    require(record['positive'] and record['predicate'] in ('pln:proposition','pln:implication'))
    if record['predicate']=='pln:proposition':
        require(len(record['arguments'])==1)
        return {'predicate':'pln:proposition','arguments':[digest(canonical(ref))],'positive':True}
    literal(record); return record


def ancestry(supports):
    values = {canonical(v): v for s in supports for v in [s['literal'], *s['ancestors']]}
    require(len(values) <= 64, 'OVERLOADED')
    return [values[k] for k in sorted(values)]


def binding(value, scope, context):
    fields(value, 'claim context revision support_id')
    validate_ref(value['claim'], scope); require(value['context']==context)
    integer(value['revision'],1); identifier(value['support_id'])


def manifest(value, scope, context):
    fields(value, 'profile context roles')
    require(value['profile']==RULE, 'UNSUPPORTED_PROFILE'); require(value['context']==context)
    fields(value['roles'], ' '.join(ROLES))
    for ref in value['roles'].values(): validate_ref(ref,scope)
    require(len({canonical(ref) for ref in value['roles'].values()})==6)


def task(value, scope, context):
    fields(value, 'ref record claims')
    validate_ref(value['ref'],scope); manifest(value['record'],scope,context)
    require(digest(canonical(value['record']))==value['ref']['digest'])
    fields(value['claims'], ' '.join(ROLES))
    roles=value['record']['roles']
    literals={key:claim_literal(roles[key],value['claims'][key]) for key in ROLES}
    p,q,r=[digest(canonical(roles[key])) for key in ('p','q','r')]
    expected=[('pln:proposition',[p]),('pln:proposition',[q]),('pln:proposition',[r]),
              ('pln:implication',[p,q]),('pln:implication',[q,r]),('pln:implication',[p,r])]
    for key,(predicate,args) in zip(ROLES,expected):
        require(literals[key]=={'predicate':predicate,'arguments':args,'positive':True})
    return literals


def workset(value, scope, context):
    fields(value,'profile context tasks'); require(value['profile']==WORKSET,'UNSUPPORTED_PROFILE')
    require(value['context']==context and type(value['tasks']) is list and 1<=len(value['tasks'])<=MAX_TASKS)
    seen=set()
    for entry in value['tasks']:
        fields(entry,'task premises'); validate_ref(entry['task'],scope)
        identity=canonical(entry['task']); require(identity not in seen); seen.add(identity)
        require(type(entry['premises']) is list and len(entry['premises'])==5)
        for item in entry['premises']: binding(item,scope,context)


def derivation(value):
    require(type(value) is DerivationSubmission); mutation(value.command)
    validate_ref(value.task,value.command.scope_ref); identifier(value.context)
    require(type(value.premises) is tuple and len(value.premises)==5)
    for item in value.premises: binding(item,value.command.scope_ref,value.context)
    integer(value.expected_revision); integer(value.deadline_ms,1)
    require(value.profile==BELIEF_PROFILE,'UNSUPPORTED_PROFILE'); identifier(value.kernel_selection)
    return detached(asdict(value))


def logical_id(task_ref, vector, kernel):
    return 'derivation/' + digest(canonical([RULE,task_ref,vector,kernel]))


def support(value, scope):
    base='id claim context truth evidence_ids lineage_roots coverage premises formula assumptions kind literal ancestors coverage_kind'
    fields(value, base + (' task kernel_selection' if value.get('kind')=='deduction' else ''))
    identifier(value['id']);identifier(value['context']);validate_ref(value['claim'],scope);truth(value['truth'])
    for key in ('evidence_ids','lineage_roots','coverage'): roots(value[key])
    require(value['coverage_kind']==COVERAGE); literal(value['literal'])
    require(type(value['ancestors']) is list and len(value['ancestors'])<=64)
    for ancestor in value['ancestors']: literal(ancestor)
    require(value['ancestors']==[v for _,v in sorted({canonical(v):v for v in value['ancestors']}.items())])
    kind=value['kind']; require(kind in ('observation','revision','deduction'))
    require(type(value['premises']) is list and type(value['assumptions']) is list)
    if kind=='observation':
        require(value['premises']==[] and value['formula'] is None and value['assumptions']==[] and value['ancestors']==[])
        require(value['coverage']==[value['id']] and len(value['evidence_ids'])==1)
    elif kind=='revision':
        require(len(value['premises'])==2 and len(set(value['premises']))==2)
        for p in value['premises']: identifier(p)
        require(value['formula']==PREFIX+'Truth_Revision')
        require(len(value['assumptions'])==2 and value['assumptions'][0]=='finite-evidence-weight-k=1')
        require(type(value['assumptions'][1]) is str and value['assumptions'][1].startswith('independence:') and len(value['assumptions'][1])<=256)
    else:
        require(len(value['premises'])==5 and value['formula']==PREFIX+'Truth_Deduction' and value['assumptions']==ASSUMPTIONS)
        for p in value['premises']: binding(p,scope,value['context'])
        validate_ref(value['task'],scope);identifier(value['kernel_selection'])
        require(value['id']==logical_id(value['task'],value['premises'],value['kernel_selection']))
        require(value['coverage']==[value['id']] and value['literal'] not in value['ancestors'])


def snapshot(value, claim, context, runtime_selection):
    fields(value,'claim context revision truth aggregate covered_supports alternatives supports observations model runtime_selection coverage_kind')
    require(value['claim']==claim and value['context']==context and value['runtime_selection']==runtime_selection)
    require(value['model']==MODEL and value['coverage_kind']==COVERAGE);integer(value['revision'])
    require(type(value['supports']) is list and len(value['supports'])<=MAX_SUPPORTS*2)
    prior={}
    for s in value['supports']:
        support(s,claim['scope_ref']);require(s['claim']==claim and s['context']==context and s['id'] not in prior)
        if s['kind']=='revision':
            require(set(s['premises'])<=set(prior));a,b=[prior[p] for p in s['premises']]
            require(a['literal']==b['literal']==s['literal'])
            for key in ('coverage','evidence_ids','lineage_roots'): require(s[key]==sorted(set(a[key])|set(b[key])))
            require(not set(a['evidence_ids']) & set(b['evidence_ids']) and not set(a['lineage_roots']) & set(b['lineage_roots']))
            require(s['ancestors']==ancestry([a,b]))
        prior[s['id']]=s
    roots(value['covered_supports'],True);roots(value['alternatives'],True)
    base={s['id'] for s in value['supports'] if s['kind']!='revision'}
    require(set(value['covered_supports'])<=base)
    require(value['alternatives']==sorted(base-set(value['covered_supports'])))
    if value['aggregate'] is None: require(value['truth'] is None and not value['covered_supports'])
    else:
        require(value['aggregate'] in prior);aggregate=prior[value['aggregate']]
        require(value['truth']==aggregate['truth'] and value['covered_supports']==aggregate['coverage'])
    require(type(value['observations']) is list and len(value['observations'])<=MAX_SUPPORTS)
    seen=set()
    for o in value['observations']:
        fields(o,'evidence relationship truth support_id lineage_roots');evidence_ref(o['evidence'],claim['scope_ref'])
        key=canonical(o['evidence']);require(key not in seen);seen.add(key)
        require(o['relationship'] in ('supports','contradicts','reports'));roots(o['lineage_roots'],True)
        if o['truth'] is not None: truth(o['truth'])
        require(o['relationship']!='reports' or o['truth'] is None)
        if o['support_id'] is not None:
            require(o['support_id'] in prior);leaf=prior[o['support_id']]
            require(leaf['kind']=='observation' and leaf['truth']==o['truth'] and leaf['lineage_roots']==o['lineage_roots'])
            require(leaf['evidence_ids']==[digest(canonical(o['evidence']))])
    require(len(canonical(value))<=262144)


def decision(value, claim, context, runtime_selection):
    fields(value,'decision_id evidence support_id admission numerical detail snapshot')
    identifier(value['decision_id']);require(value['admission'] in ('admitted','duplicate'))
    require(value['numerical'] in ('initialized','revised','no-change','retained-alternative','model-inapplicable'))
    if value['evidence'] is not None: evidence_ref(value['evidence'],claim['scope_ref'])
    if value['support_id'] is not None: identifier(value['support_id'])
    require(type(value['detail']) is str and len(value['detail'])<=256)
    snapshot(value['snapshot'],claim,context,runtime_selection)


def snapshot_reply(value, claim, context):
    value=response_copy(value);response(snapshot,value,claim,context,value['runtime_selection']);return value


def math_result(value, a, b, declaration):
    fields(value,'status detail proposal');require(value['status'] in ('PASS','FAIL','UNKNOWN'))
    require(type(value['detail']) is str and len(value['detail'])<=256)
    p=value['proposal']
    if p is None: return
    require(value['status']=='PASS' and declaration is not None)
    require(set(declaration['supports'])=={a['id'],b['id']})
    require(not set(a['evidence_ids']) & set(b['evidence_ids']) and not set(a['lineage_roots']) & set(b['lineage_roots']))
    support(p,a['claim']['scope_ref']); require(p['kind']=='revision' and p['claim']==a['claim']==b['claim'])
    require(p['context']==a['context']==b['context'] and p['literal']==a['literal']==b['literal'])
    require(set(p['premises'])=={a['id'],b['id']} and p['id'] not in p['premises'])
    for key in ('coverage','evidence_ids','lineage_roots'): require(p[key]==sorted(set(a[key])|set(b[key])))
    require(p['ancestors']==ancestry([a,b]))


def kernel_result(value, task_value, resolved, kernel):
    fields(value,'status detail proposal');require(value['status'] in ('PASS','FAIL','UNKNOWN'))
    require(type(value['detail']) is str and len(value['detail'])<=256)
    p=value['proposal']
    if p is None: require(value['status']!='PASS');return
    record=task_value['record'];scope=task_value['ref']['scope_ref'];literals=task(task_value,scope,record['context'])
    support(p,scope);require(value['status']=='PASS' and p['kind']=='deduction')
    require(p['claim']==record['roles']['pr'] and p['context']==record['context'] and p['literal']==literals['pr'])
    require(p['task']==task_value['ref'] and p['kernel_selection']==kernel)
    require(p['premises']==[v['binding'] for v in resolved])
    inputs=[v['support'] for v in resolved]
    for key in ('evidence_ids','lineage_roots'): require(p[key]==sorted({x for s in inputs for x in s[key]}))
    require(p['ancestors']==ancestry(inputs))


def inference(value):
    require(type(value) is InferenceRequest and type(value.budget) is WorkBudget);mutation(value.command)
    identifier(value.context);validate_ref(value.workset,value.command.scope_ref)
    fields(value.selections,'attention beliefs kernel controller')
    for token in value.selections.values(): identifier(token)
    integer(value.budget.max_candidates,1,MAX_TASKS);integer(value.budget.max_rule_applications,0,16)
    integer(value.budget.max_feedback_generation,0,8);integer(value.budget.deadline_ms,1)
    return detached(asdict(value))

# Opt-in delivery closure; old controller identity remains supported.
CLOSURE_CONTROL = 'bounded-grounded-closure/1'
MAX_RECONCILIATIONS = 128
