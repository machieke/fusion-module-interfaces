"""Closed C3 local contract. No payload, belief, PLN or Hive dependency."""
from dataclasses import asdict
import re
from .contracts import canonical, digest, require, validate_ref
from .memory_contracts import boundary, detached, fields, integer, identifier, mutation, response
from .ports import Stimulus, FeedbackIntent, Mutation

PROFILE = 'sti-additive-linear-decay/1'
CLOSURE_PROFILE = 'sti-additive-linear-decay-closure/1'
RESOLUTION = 'causal-feedback-resolution/1'
DEFAULT_POLICY = {'profile': PROFILE, 's_max': '100', 'budget': '300', 'decay': '1',
                  'max_targets': 16, 'max_advances': 16, 'max_contexts': 8,
                  'max_causes': 512, 'max_commands': 1024, 'max_feedback_generation': 3}


def units(value):
    require(type(value) is str and re.fullmatch(r'0|[1-9][0-9]{0,15}', value) is not None)
    return int(value)


def policy(value):
    fields(value, 'profile s_max budget decay max_targets max_advances max_contexts max_causes max_commands max_feedback_generation')
    require(value['profile'] == PROFILE, 'UNSUPPORTED_PROFILE')
    for key in ('s_max', 'budget', 'decay'): units(value[key])
    require(0 < units(value['s_max']) <= units(value['budget']))
    for key in ('max_targets','max_advances','max_contexts'): integer(value[key],1,64)
    for key in ('max_causes','max_commands'): integer(value[key],1,4096)
    integer(value['max_feedback_generation'],0,8)
    return digest(canonical(value))


def target_key(ref): return canonical(ref).decode()
def context_key(scope, context): return digest(canonical([scope,context]))


def stimulus(value, selected):
    require(type(value) is Stimulus)
    body = detached(asdict(value)); mutation(value.command)
    identifier(value.context); validate_ref(value.target, value.command.scope_ref)
    units(value.amount); identifier(value.cause); integer(value.generation,0,8); integer(value.expected_step)
    require(value.policy == selected, 'UNSUPPORTED_PROFILE')
    require(value.kind in ('ingress','feedback'))
    if value.kind == 'ingress': require(value.generation == 0 and value.parent is None)
    else: identifier(value.parent); require(value.generation > 0)
    return body


def row(value, scope, parameters):
    fields(value,'target sti generation cause')
    validate_ref(value['target'],scope)
    require(units(value['sti']) <= units(parameters['s_max']))
    integer(value['generation'],0,parameters['max_feedback_generation'])
    if value['cause'] is None: require(value['sti']=='0' and value['generation']==0)
    else: identifier(value['cause'])


def selection(value, scope, context, eligible, limit, parameters):
    fields(value,'scope_ref context policy logical_step revision eligible_digest values ranked limit')
    require(value['scope_ref']==scope and value['context']==context and value['policy']==policy(parameters))
    require(value['limit']==limit and value['eligible_digest']==digest(canonical(eligible)))
    integer(value['logical_step']);integer(value['revision'])
    require(type(value['values']) is list and len(value['values'])==len(eligible))
    require([v['target'] for v in value['values']]==list(eligible))
    for v in value['values']: row(v,scope,parameters)
    require(sum(units(v['sti']) for v in value['values']) <= units(parameters['budget']))
    ranked=sorted((v for v in value['values'] if units(v['sti'])>0),key=lambda v:(-units(v['sti']),target_key(v['target'])))[:limit]
    require(value['ranked']==ranked)


def receipt(value, request, parameters):
    fields(value,'scope_ref context policy target cause generation kind parent requested applied saturated logical_step revision')
    for key in ('context','policy','target','cause','generation','kind','parent'):
        require(value[key]==getattr(request,key))
    require(value['scope_ref']==request.command.scope_ref and value['logical_step']==request.expected_step)
    require(value['requested']==request.amount and 0<=units(value['applied'])<=units(request.amount))
    require(type(value['saturated']) is bool and value['saturated']==(units(value['applied'])<units(request.amount)))
    integer(value['revision'],1)
    require(units(value['applied'])<=units(parameters['s_max']))


def eligible_refs(scope, context, eligible, limit, parameters):
    identifier(scope);identifier(context);integer(limit,1,parameters['max_targets'])
    require(type(eligible) is tuple and len(eligible)<=parameters['max_targets'])
    for ref in eligible: validate_ref(ref,scope)
    require(len({target_key(r) for r in eligible})==len(eligible))


def zero(target): return {'target':target,'sti':'0','generation':0,'cause':None}


def feedback(intent, selected):
    require(type(intent) is FeedbackIntent)
    body = stimulus(intent.stimulus, selected)
    require(body['kind'] == 'feedback')
    integer(intent.effect_deadline_ms, 1)
    return {'stimulus': body, 'effect_deadline_ms': intent.effect_deadline_ms}


def feedback_copy(intent, selected):
    body = feedback(intent, selected)
    stimulus_body = body['stimulus']
    return FeedbackIntent(Stimulus(**{**stimulus_body, 'command': Mutation(**stimulus_body['command'])}), body['effect_deadline_ms'])


def resolution(value, intent, parameters):
    fields(value, 'profile intent_digest outcome reason receipt retirement')
    body = feedback(intent, policy(parameters))
    require(value['profile'] == RESOLUTION and value['intent_digest'] == digest(canonical(body)))
    if value['outcome'] == 'applied':
        require(value['reason'] is None and value['retirement'] is None)
        receipt(value['receipt'], intent.stimulus, parameters)
    elif value['outcome'] == 'retired':
        require(value['reason'] in ('expired', 'obsolete-step', 'obsolete-parent') and value['receipt'] is None)
        fields(value['retirement'], 'logical_step revision')
        integer(value['retirement']['logical_step']); integer(value['retirement']['revision'], 1)
        require(value['retirement']['logical_step'] >= intent.stimulus.expected_step)
        if value['reason'] == 'obsolete-step': require(value['retirement']['logical_step'] > intent.stimulus.expected_step)
    else:
        require(value['outcome'] == 'pending' and value['reason'] == 'eligible' and
                value['receipt'] is None and value['retirement'] is None)
