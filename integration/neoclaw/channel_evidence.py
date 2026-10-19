"""Publish S06 channel traces without exporting local cognitive audit journals."""
import argparse
import json
from pathlib import Path
from fusion.contracts import canonical,require


def trace(value):
    selected=('irc','traffic','mailbox_placement','mailbox','channel_boundary','bridge_boundary','mailbox_boundary',
              'channel_epochs','channel_ingress','channel_egress','app_channel_inputs','app_channel_outputs','same_host','fixtures','real')
    result={k:value[k] for k in selected if k in value}
    result['native_observations']=[dict(index=r['index'],human=r['context'].split(':-:-:-:',1)[-1],
        deduction_result_consumed='(stv 0.5599999999999999 0.4032)' in r['feedback'],
        send_acceptance_consumed='SEND-ACCEPTED' in r['feedback'],priority_success_consumed='PROMOTE-SUCCESS' in r['feedback'],
        generated_private_context_present='S05_LOCAL_PRIORITY' in r['context']) for r in value['observations']]
    result['local_source_handoff']=[dict(slot=r['slot'],channel_occurrence=json.loads(r['accepted'])['spec']['message_id'],
        receipt_captured=r['receipt'] is not None,exposed=bool(r['exposed']),calls=r['calls']) for r in value['app_sources']]
    result['local_owner_audit']=dict(source_count=len(value['app_sources']),assessment_count=len(value['app_assessments']),
        priority_adjustments=len(value['app_priority']),context_captures=len(value['app_priority_contexts']),
        index_maintenance_count=len(value['maintenance_audit']),private_journals_published=False)
    result['send_occurrences']=[r for r in value['occurrences'] if r['premises'] and json.loads(r['premises']).get('operation')=='send']
    require(len(result['local_source_handoff'])==len(result['app_channel_inputs']),'CONFLICT')
    for source,received in zip(result['local_source_handoff'],result['app_channel_inputs']):
        require(source['channel_occurrence']==received['id'] and source['slot']==received['slot'],'CONFLICT')
    return result


def publish(source,destination):
    source,destination=Path(source),Path(destination);destination.mkdir(parents=True,exist_ok=True)
    for path in source.glob('*.json'):
        value=json.loads(path.read_text())
        if path.name=='native-paths.json':value=[trace(x) for x in value]
        elif path.name=='native-kills.json':
            value=[dict(stage=x['stage'],signal=x['signal'],before=x['before'],
                bound_commands_before=[dict(id=r['id'],deadline=r['deadline'],turn=r['turn'],position=r['position']) for r in x['commands_before']],
                source_count_before=len(x['sources_before']),model_calls_before=x['model_calls_before'],trace=trace(x['trace'])) for x in value]
        else:require(path.name in ('native-empty-budget.json','private-refusal.json','bridge-ingress-kills.json','bridge-egress-kills.json',
                    'capacity-discontinuity.json','spent-budgets.json','reservation-revocation.json','provider-kills.json','pre-capture-loss.json','capture-revocation.json'),'INVALID_ARGUMENT')
        (destination/path.name).write_bytes(canonical(value))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source');p.add_argument('destination');a=p.parse_args();publish(a.source,a.destination)
