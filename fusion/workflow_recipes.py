"""Three fixed native recipe selections; no executable user-defined graph.

Arguments are approved data or closed references to actual captured results.
The existing recorded proposal, native parser and whole-batch authority remain
in the execution path. No expected answer or provider implementation lives here.
"""
import json
from .contracts import canonical,digest,require
from .preview_tools import Argument

PROFILE='registered-native-workflow-recipes/1'
RECIPES={
 'knowledge-handoff/1':[('remember',('remember',)),('delegate',('delegate',)),('followup',('query','task-context'))],
 'evidence-aware-review/1':[('remember',('remember',)),('support',('support',)),('contrary',('contradict',)),
                          ('priority',('promote','demote')),('review',('query','task-context'))],
 'approved-artifact-delivery/1':[('delegate',('delegate',)),('artifact',('write-file',)),('inspect',('inspect-atom',))]}
ARITY={'remember':1,'query':1,'delegate':2,'task-context':0,'support':2,'contradict':2,
       'promote':1,'demote':1,'write-file':2,'inspect-atom':1}
CAPTURE_FIELDS={'memory','task','logical_id','projection','task-result'}


def definition(recipe):
    require(recipe in RECIPES,'UNSUPPORTED_PROFILE')
    return dict(profile=PROFILE,recipe=recipe,nodes=[dict(id=x,tools=list(y)) for x,y in RECIPES[recipe]],
        execution='existing-native-session-input',model='RECORDED_PROPOSALS',maximum_inflight=1,
        chain='separate-exact-result-approval-and-existing-chain-continuation',source_lineage='owner-observations-only')


def validate_steps(recipe,steps):
    registered=RECIPES.get(recipe); require(registered is not None,'UNSUPPORTED_PROFILE')
    require(type(steps) is list and len(steps)<=len(registered),'OVERLOADED'); seen=set(); previous=-1
    for step in steps:
        require(type(step) is dict and set(step)=={'node','tool','arguments','guards','checkpoint'})
        found=[(i,tools) for i,(name,tools) in enumerate(registered) if name==step['node']]
        require(len(found)==1 and step['node'] not in seen,'UNSUPPORTED_OPERATION')
        index,tools=found[0]; require(index>previous and step['tool'] in tools,'UNSUPPORTED_OPERATION')
        require(type(step['arguments']) is list and len(step['arguments'])==ARITY[step['tool']])
        require(type(step['guards']) is list and len(step['guards'])<=8 and type(step['checkpoint']) is bool)
        for arg in step['arguments']:
            if type(arg) is str: require(0<len(arg.encode())<=4096 and not any(x in arg for x in ('\n','\r','\x00')))
            else:
                require(type(arg) is dict and set(arg)=={'capture','field'})
                require(arg['capture'] in seen and arg['field'] in CAPTURE_FIELDS)
        seen.add(step['node']); previous=index
    require(len(canonical(steps))<=32768,'OVERLOADED'); return steps


def native_object(result):
    require(type(result) is dict and type(result.get('projection')) is str,'NOT_AVAILABLE')
    raw=result['projection'].replace('_quote_','"'); require(len(raw.encode())<=65536,'OVERLOADED')
    try: value=json.JSONDecoder().raw_decode(raw[raw.index('{'):])[0]
    except (ValueError,TypeError):require(False,'NOT_AVAILABLE')
    require(type(value) is dict,'NOT_AVAILABLE'); return value


def render(step,captured):
    args=[]
    for raw in step['arguments']:
        if type(raw) is str:value=raw
        else:
            require(raw['capture'] in captured,'NOT_AVAILABLE'); result=captured[raw['capture']]
            if raw['field']=='projection':value=result['projection']
            elif raw['field']=='task-result':value=result['_task_result']
            else:
                obj=native_object(result); require(raw['field'] in obj,'NOT_AVAILABLE'); value=obj[raw['field']]
                if raw['field']=='memory':
                    require(type(value) is dict and type(value.get('handle')) is str,'NOT_AVAILABLE'); value=value['handle']
            require(type(value) is str and 0<len(value.encode())<=4096,'NOT_AVAILABLE')
        require(not any(x in value for x in ('\n','\r','\x00'))); args.append(value)
    tool=step['tool']
    if tool=='delegate':Argument('recipient','agent').validate(args[0])
    if tool in ('support','contradict','promote','demote'):Argument('memory','memory-handle').validate(args[0])
    if tool in ('support','contradict'):Argument('source','history-handle').validate(args[1])
    if tool=='write-file':Argument('path','path').validate(args[0])
    command=' '.join([tool,*args]); require(len(command.encode())<=4096,'OVERLOADED'); return command


def catalogue():
    return dict(profile=PROFILE,recipes=[dict(**definition(name),definition_sha256=digest(canonical(definition(name))))
        for name in RECIPES],additional_live_generations=0)


def knowledge_handoff(fact,query,recipient='B'):
    """The consumer receives a query, never the remembered answer reference."""
    return [dict(node='remember',tool='remember',arguments=[fact],guards=[],checkpoint=False),
        dict(node='delegate',tool='delegate',arguments=[recipient,query],guards=[],checkpoint=False),
        dict(node='followup',tool='query',arguments=[query],guards=[dict(id='source-still-active',
            from_capture='remember',kind='memory-active')],checkpoint=True)]


def evidence_review(fact,positive_source,contrary_source,query,belief_condition):
    """Source handles and the finite belief predicate are explicit operator input.

    They must name actual already captured sources; native source resolution and
    C1/C2 remain authoritative. Copies do not become independent observations.
    """
    def memory():return {'capture':'remember','field':'memory'}
    return [dict(node='remember',tool='remember',arguments=[fact],guards=[],checkpoint=False),
        dict(node='support',tool='support',arguments=[memory(),positive_source],guards=[],checkpoint=False),
        dict(node='contrary',tool='contradict',arguments=[memory(),contrary_source],guards=[],checkpoint=False),
        dict(node='priority',tool='promote',arguments=[memory()],guards=[],checkpoint=False),
        dict(node='review',tool='query',arguments=[query],guards=[belief_condition],checkpoint=True)]


def artifact_delivery(query,filename,recipient='B'):
    """Actual consumed B result supplies the workspace bytes, never an answer constant.

    Inspection retains its existing typed task-result operation. The exact
    postcapture approval and chain continuation remain separate explicit acts.
    """
    return [dict(node='delegate',tool='delegate',arguments=[recipient,query],guards=[],checkpoint=False),
        dict(node='artifact',tool='write-file',arguments=[filename,{'capture':'delegate','field':'task-result'}],guards=[],checkpoint=False),
        dict(node='inspect',tool='inspect-atom',arguments=[{'capture':'delegate','field':'task'}],guards=[],checkpoint=True)]
