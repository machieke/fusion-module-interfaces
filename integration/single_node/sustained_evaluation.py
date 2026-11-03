"""Frozen synthetic workloads and independent observations, outside providers.

The authored model provider never imports this module or receives expected
answers. Scoring is not command admission or evidence of autonomous planning.
"""
import copy
from fusion.contracts import canonical,digest,require

PROFILE='sustained-native-evaluation/1'
DATASETS={
 'new':dict(fact='The synthetic silver prism is stored in crate orchid',query='synthetic silver prism storage',required=['crate orchid'],forbidden=['crate saffron']),
 'changed':dict(fact='The synthetic silver prism is stored in crate saffron',query='synthetic silver prism storage',required=['crate saffron'],forbidden=['crate orchid']),
 'absent':dict(query='synthetic missing topaz key',required=[],forbidden=['topaz key is stored']),
}

def workload():
    return dict(profile=PROFILE,datasets=copy.deepcopy(DATASETS),agents=2,sequential_shared_sessions_per_agent=3,
        maximum_operator_inputs=72,maximum_wall_seconds=3600,source_records_limit=2048,source_bytes_limit=33554432,
        old_record_threshold=512,required_operations_after_crossing=4,maximum_active_user_memories=8,
        original_input_timeout_ms=120000,observer_overrun_seconds=8,
        current_fact_scoring='exact required and forbidden substrings in actual native projection; no response repair',
        absent_scoring='no invented exact absent fact; nearest neighbours may legitimately appear',
        held_out_live=dict(enabled=False,allowance=0,selection='operator-supplied new synthetic variant withheld from model setup',runtime='DO_NOT_CONTACT'),
        proposals='recorded input-command only; no tool results or evaluator answers supplied',
        live_generations=0)

def freeze():
    value=workload();return dict(plan=value,sha256=digest(canonical(value)))

def score(projection,case,*,permitted=True):
    require(type(projection) is str and type(case) is dict)
    correct=all(x in projection for x in case.get('required',[])) and not any(x in projection for x in case.get('forbidden',[]))
    return dict(permission='PERMITTED' if permitted else 'REJECTED',factual_correctness='CORRECT' if correct else 'INCORRECT',
        task_pass=bool(permitted and correct),actual_projection_sha256=digest(projection.encode()),
        peer_observation='NOT_APPLICABLE_NATIVE_MEMORY_QUERY',chain_finality='NOT_EVALUATED_BY_THIS_ORACLE')

def stopped_premise(before,after,observation):
    require(type(observation) is str)
    return dict(premise_changed=before!=after,explicit_reassessment='REASSESS' in observation,
        task_pass=before!=after and 'REASSESS' in observation,
        selection='RECORDED_OPERATOR_PROPOSAL_NOT_AUTONOMOUS_MODEL_REASONING')
