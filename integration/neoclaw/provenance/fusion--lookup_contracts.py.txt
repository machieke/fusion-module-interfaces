"""Bounded private M5 DTO validation. No provider, SQL or runtime dependencies."""
import base64
from dataclasses import asdict, dataclass
import hashlib
import hmac
import json
import uuid
from .contracts import ContractError, canonical, digest, label, require, validate_ref

FEED = 'immutable-commit-feed/1'
RELATIONS = 'schema-ordered-relations/2'
SEARCH = 'exact-attributes/1'
EXTRACTION = 'knowledge-attributes/1'
KNOWLEDGE = 'application/fusion-knowledge-v1'
RELATION = 'application/fusion-relation-v2'
MAX_ATOMS = 512
MAX_BYTES = 4096
MAX_RELATIONS = 128
MAX_COMMANDS = 512
MAX_RECORDS = 256
PAGE = 8
BATCH = 8
# Explicit operator configuration; role labels do not determine direction.
SCHEMAS = {
    'requires/1': {'roles': ['dependent', 'prerequisite'], 'origins': [0], 'destinations': [1], 'directed': True},
    'transfer/1': {'roles': ['sender', 'object', 'recipient'], 'origins': [0], 'destinations': [1, 2], 'directed': True},
    'association/1': {'roles': ['first', 'second'], 'origins': [0, 1], 'destinations': [0, 1], 'directed': False},
}

@dataclass(frozen=True)
class AttributeQuery:
    scope_ref: str
    expression: dict
    minimum: dict
    limit: int = 2
    cursor: str | None = None
    profile: str = SEARCH

class ProjectionError(ContractError):
    """Private maintenance diagnostic; public native receipts expose only code."""
    def __init__(self, reason, sequence, code='NOT_AVAILABLE'):
        super().__init__(code); self.reason, self.sequence = reason, sequence

def copy(value):
    return json.loads(canonical(value))

def integer(value, low, high):
    require(type(value) is int and low <= value <= high)

def identity(value):
    require(type(value) is str)
    try: require(str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError, TypeError): raise ContractError('INVALID_ARGUMENT') from None

def head(value, scope=None, profile=FEED):
    require(type(value) is dict and set(value) == {'source', 'scope_ref', 'sequence', 'profile'})
    identity(value['source']); require(label(value['scope_ref']))
    integer(value['sequence'], 0, MAX_ATOMS)
    require(value['profile'] == profile, 'UNSUPPORTED_PROFILE')
    if scope is not None: require(value['scope_ref'] == scope, 'UNAUTHORIZED')
    return copy(value)

def make_head(source, scope, sequence, profile=FEED):
    return head(dict(source=source, scope_ref=scope, sequence=sequence, profile=profile), scope, profile)

def mutation(command):
    require(label(command.scope_ref) and label(command.idempotency_key))
    require(command.intent_digest is None)  # New local profile; no undeclared wire intent.

def scope_of(value):
    require(type(value) is dict and label(value.get('scope_ref')))
    return value['scope_ref']

def ref(value, scope):
    validate_ref(value, scope)
    require(value['revision'] == 1 and type(value['revision']) is int)
    return copy(value)

def schemas(value):
    require(type(value) is dict and 1 <= len(value) <= 8)
    for name, spec in value.items():
        require(label(name) and type(spec) is dict and set(spec) == {'roles','origins','destinations','directed'})
        roles = spec['roles']; require(type(roles) is list and 2 <= len(roles) <= 3)
        require(all(label(x) for x in roles) and len(set(roles)) == len(roles))
        require(type(spec['directed']) is bool)
        for key in ('origins','destinations'):
            indexes=spec[key];require(type(indexes) is list and 1<=len(indexes)<=3)
            for x in indexes: integer(x,0,len(roles)-1)
            require(len(set(indexes)) == len(indexes))
        if spec['directed']:
            require(not set(spec['origins']) & set(spec['destinations']))
            require(set(spec['origins']) | set(spec['destinations']) == set(range(len(roles))))
        else: require(spec['origins'] == spec['destinations'] == list(range(len(roles))))
    return copy(value)

def relation_body(scope, relation_type, roles, directed, configured):
    require(type(relation_type) is str and relation_type in configured, 'UNSUPPORTED_PROFILE')
    spec=configured[relation_type]
    require(type(directed) is bool and directed == spec['directed'])
    require(type(roles) is tuple and len(roles) == len(spec['roles']))
    result=[]
    for item, name in zip(roles,spec['roles']):
        require(type(item) is tuple and len(item)==2 and item[0] == name)
        result.append([name, ref(item[1],scope)])
    # Repeated endpoints/self-links are permitted; incidence returns each relation once.
    return dict(profile=RELATIONS, scope_ref=scope, relation_type=relation_type, schema=copy(spec), roles=result, directed=directed)

def relation(value, scope, expected=None):
    require(type(value) is dict and set(value)=={'ref','body','accepted'}, 'NOT_AVAILABLE')
    ref(value['ref'],scope)
    if expected is not None: require(value['ref']==expected,'NOT_AVAILABLE')
    body=value['body'];require(type(body) is dict and set(body)=={'profile','scope_ref','relation_type','schema','roles','directed'},'NOT_AVAILABLE')
    require(body['profile']==RELATIONS and body['scope_ref']==scope,'NOT_AVAILABLE')
    require(type(body['relation_type']) is str and type(body['roles']) is list and len(body['roles'])<=3,'NOT_AVAILABLE')
    require(all(type(x) is list and len(x)==2 for x in body['roles']),'NOT_AVAILABLE')
    configured=schemas({body['relation_type']:body['schema']})
    require(body==relation_body(scope,body['relation_type'],tuple((r,v) for r,v in body['roles']),body['directed'],configured),'NOT_AVAILABLE')
    require(digest(canonical(body))==value['ref']['digest'],'NOT_AVAILABLE')
    head(value['accepted'],scope,RELATIONS);require(value['accepted']['sequence']>0,'NOT_AVAILABLE')
    return copy(value)

def scalar(value):
    require(type(value) is str and 1 <= len(value) <= 128)
    try: require(len(value.encode('utf-8')) <= 512)
    except UnicodeError: raise ContractError('INVALID_ARGUMENT') from None

def record(data):
    require(type(data) is bytes and 0 < len(data) <= MAX_BYTES)
    try: value=json.loads(data)
    except (ValueError,UnicodeError,RecursionError):raise ContractError('INVALID_ARGUMENT') from None
    require(type(value) is dict and set(value)<={'kind','topic','label'} and 'kind' in value)
    for v in value.values():scalar(v)
    require(canonical(value)==data)  # A single bounded, explicit UTF-8 record format.
    return value

def query(value):
    require(isinstance(value,AttributeQuery))
    require(value.profile==SEARCH,'UNSUPPORTED_PROFILE');require(label(value.scope_ref))
    minimum=head(value.minimum,value.scope_ref);integer(value.limit,1,PAGE)
    expression=value.expression
    require(type(expression) is dict and set(expression)=={'all'})
    clauses=expression['all'];require(type(clauses) is list and 1<=len(clauses)<=3)
    fields=[]
    for clause in clauses:
        require(type(clause) is dict and set(clause)=={'field','eq'} and type(clause['field']) is str and clause['field'] in {'kind','topic','label'})
        scalar(clause['eq'])
        fields.append(clause['field'])
    require(len(set(fields))==len(fields) and len(canonical(expression))<=1024)
    expression=copy(expression)
    require(value.cursor is None or (type(value.cursor) is str and 1<=len(value.cursor)<=4096))
    return AttributeQuery(value.scope_ref,expression,minimum,value.limit,value.cursor,value.profile)

def query_binding(value,principal):
    return digest(canonical([value.scope_ref,value.profile,value.expression,value.minimum,value.limit,principal]))

def matches(fields,expression):
    return all(clause['field'] in fields and fields[clause['field']]==clause['eq'] for clause in expression['all'])

def seal(secret,value):
    body=canonical(value);signature=hmac.new(secret.encode(),body,hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(body).decode()+'.'+signature

def unseal(secret,token):
    require(type(token) is str and len(token)<=4096)
    try:
        body,signature=token.split('.');raw=base64.b64decode(body,altchars=b'-_',validate=True)
        require(hmac.compare_digest(hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest(),signature),'CONFLICT')
        value=json.loads(raw);require(canonical(value)==raw,'CONFLICT');return value
    except (ValueError,UnicodeError,TypeError):raise ContractError('INVALID_ARGUMENT') from None

def commits(value,scope,after,through,limit):
    require(type(value) is dict and set(value)=={'through','after','records','next_after','complete'},'NOT_AVAILABLE')
    require(value['through']==through and type(value['after']) is int and value['after']==after,'NOT_AVAILABLE')
    entries=value['records'];require(type(entries) is list and len(entries)==min(limit,through['sequence']-after),'NOT_AVAILABLE')
    for i,e in enumerate(entries,after+1):
        require(type(e) is dict and set(e)=={'sequence','ref','content_type','size'} and e['sequence']==i,'NOT_AVAILABLE')
        integer(e['sequence'],1,MAX_ATOMS);ref(e['ref'],scope);require(label(e['content_type']),'NOT_AVAILABLE');integer(e['size'],1,MAX_BYTES)
    require(type(value['next_after']) is int and value['next_after']==after+len(entries) and type(value['complete']) is bool and value['complete']==(value['next_after']==through['sequence']),'NOT_AVAILABLE')
    return copy(value)

def search_result(value,request,principal,expected=None):
    require(type(value) is dict and set(value)=={'refs','at','observed_head','generation','profile','extraction','binding','prefix_complete','page_complete','fresh','at_observed_head','cursor'},'NOT_AVAILABLE')
    head(value['at'],request.scope_ref);identity(value['generation'])
    require(value['at']['source']==request.minimum['source'] and value['at']['sequence']>=request.minimum['sequence'],'NOT_AVAILABLE')
    require(value['profile']==SEARCH and value['extraction']==EXTRACTION and value['binding']==query_binding(request,principal),'NOT_AVAILABLE')
    require(value['prefix_complete'] is True and value['fresh'] is True and type(value['page_complete']) is bool,'NOT_AVAILABLE')
    observed=value['observed_head'];require(type(observed) is dict and set(observed)=={'head','via','observed_ms'},'NOT_AVAILABLE')
    head(observed['head'],request.scope_ref);require(observed['head']['source']==value['at']['source'] and observed['head']['sequence']>=value['at']['sequence'],'NOT_AVAILABLE')
    require(observed['via']=='maintenance.head' and type(observed['observed_ms']) is int and observed['observed_ms']>0,'NOT_AVAILABLE')
    require(type(value['at_observed_head']) is bool and value['at_observed_head']==(value['at']==observed['head']),'NOT_AVAILABLE')
    refs=value['refs'];require(type(refs) is list and len(refs)<=request.limit,'NOT_AVAILABLE')
    for r in refs:ref(r,request.scope_ref)
    require(len({canonical(r) for r in refs})==len(refs),'NOT_AVAILABLE')
    require((value['cursor'] is None)==value['page_complete'],'NOT_AVAILABLE')
    if value['cursor'] is not None:require(type(value['cursor']) is str and 1<=len(value['cursor'])<=4096 and len(refs)==request.limit,'NOT_AVAILABLE')
    if expected:require(all(value[k]==expected[k] for k in ('at','generation','observed_head','binding')),'NOT_AVAILABLE')
    return copy(value)


def relation_page(value,endpoint,direction,limit,principal,snapshot=None):
    require(type(value) is dict and set(value)=={'refs','sequences','at','binding','page_complete','cursor'},'NOT_AVAILABLE')
    head(value['at'],endpoint['scope_ref'],RELATIONS)
    if snapshot:require(value['at']==snapshot,'NOT_AVAILABLE')
    require(value['binding']==digest(canonical([direction,endpoint,limit,principal])),'NOT_AVAILABLE')
    require(type(value['refs']) is list and len(value['refs'])<=limit,'NOT_AVAILABLE')
    for r in value['refs']:ref(r,endpoint['scope_ref'])
    seq=value['sequences'];require(type(seq) is list and len(seq)==len(value['refs']),'NOT_AVAILABLE')
    for n in seq:integer(n,1,value['at']['sequence'])
    require(seq==sorted(set(seq)),'NOT_AVAILABLE')
    require(type(value['page_complete']) is bool and (value['cursor'] is None)==value['page_complete'],'NOT_AVAILABLE')
    if value['cursor'] is not None:require(type(value['cursor']) is str and len(value['cursor'])<=4096 and len(seq)==limit,'NOT_AVAILABLE')
    require(len({canonical(r) for r in value['refs']})==len(value['refs']),'NOT_AVAILABLE')
    return copy(value)
