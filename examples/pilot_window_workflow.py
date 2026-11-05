"""Finite registered recipe checkpoints between the existing four windows.

The 160 original native inputs retain separate accounting. Three independent
workflows are explicit operator work with their own original fixed bounds.
This helper neither schedules future work nor replenishes any prior budget.
"""
import json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from examples.pilot_workflows import qualify

VARIANTS=('unchanged','withdrawn','unchanged')


def between_windows(op,directory,boundary,programme_end):
    require(type(boundary) is int and 0<=boundary<len(VARIANTS),'INVALID_ARGUMENT')
    remaining=int(programme_end-time.monotonic());require(remaining>=30,'DEADLINE_EXCEEDED')
    root=Path(directory)
    report=qualify(op,root,VARIANTS[boundary],maximum_seconds=min(600,remaining),case='window-'+str(boundary),checkpoint_restart=boundary==1)
    require(report['status']=='PASS' and report['final']['reservations_spent']==3,'NOT_AVAILABLE')
    native=json.loads((root/'workflow-native.json').read_bytes())
    receipts=[dict(role='omega-agent',value=report['native_session'])]
    receipts.extend(dict(role=x['role'],value=x['observation']) for x in report['session_closure'] if 'observation' in x)
    internal={}
    for observed in receipts:
        for item in observed['value']['inputs']:
            if item['assignment'] in ('delegated-task','delegated-result'):
                require(item['state']=='complete' and item['result'] is not None,'NOT_AVAILABLE')
                key=(observed['role'],item['session'],item['id']);require(key not in internal,'CONFLICT');internal[key]=item
    value=dict(profile='finite-inter-window-recipe/1',boundary=boundary,variant=VARIANTS[boundary],status='PASS',
        workflow=report['workflow'],session=report['session'],recipe_native_inputs=report['workflow_native_inputs'],
        separate_direct_inputs=native['direct_operator_inputs'],observed_internal_native_inputs=len(internal),
        all_extra_native_inputs=len(native['inputs'])+len(internal),counts_excluded_from_original_160=True,
        report_sha256=digest((root/'report.json').read_bytes()),native_report_sha256=digest((root/'workflow-native.json').read_bytes()),
        checkpoint=report['checkpoint'],decision=report['final']['checkpoints'][-1]['decision'],
        evaluation=report['counterfactual_evaluation'],original_deadline_ms=report['final']['deadline_ms'],
        original_reservations_spent=report['final']['reservations_spent'],checkpoint_restart=report.get('checkpoint_restart'),deadline_renewals=0,reservation_refunds=0,
        internal_observations=receipts,additional_live_generations=0)
    require(value['decision']['effective'] is True and value['decision']['action']=='approve','NOT_AVAILABLE')
    (root/'boundary.json').write_bytes(canonical(value));return value
