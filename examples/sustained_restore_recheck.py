"""Recheck an existing fenced clone without importing or replacing its state.

Both deployments must already have generation disabled and native workers
disabled. Only current declared read ports are used. Original and clone are
started sequentially to stay inside the measured single-node capacity.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON


def verify(original,clone,original_values,clone_values,chart,backup,directory):
    import yaml
    root=Path(directory);root.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',original=original.namespace,clone=clone.namespace,
        additional_live_generations=0,new_native_inputs=0,archives_imported=0,
        backup_manifest_sha256=digest(Path(backup).read_bytes()),observations=[])
    def save():(root/'report.json').write_bytes(canonical(report))
    def call(op,role,operation,sid=None,*args):
        command=[PYTHON,'-m','integration.single_node.preview_operator',operation]
        if sid:command+=['--session',sid]
        return json.loads(op.k('exec',role+'-0','--',*command,*args,timeout=45))
    def start(op,path):
        selected=yaml.safe_load(Path(path).read_text());op.owned()
        require(not selected.get('futureLive',{}).get('activated'),'UNAUTHORIZED')
        require(not selected['preview']['chain']['nodeEnabled'],'UNAUTHORIZED')
        for role in ('omega-agent','omega-agent-b'):
            require(selected['components'][role]['config']['nativeEnabled'] is False,'UNAUTHORIZED')
            require(selected['components'][role]['config']['workerEnabled'] is False,'UNAUTHORIZED')
        (root/(op.namespace+'-install.log')).write_text(op.command(['helm','upgrade','omega',str(chart),
            '-f',str(path),'--namespace',op.namespace,'--kubeconfig',op.kubeconfig,
            '--kube-context',op.context,'--wait','--timeout','300s'],timeout=320))
    save();before={}
    try:
        start(original,original_values)
        for role in ('omega-agent','omega-agent-b'):
            before[role]={}
            for row in call(original,role,'list'):
                value=call(original,role,'observe',row['session'],'--content')
                require(value['state']=='closed','NOT_AVAILABLE')
                before[role][row['session']]=value
        original.quiesce();report['original_quiesced']=True;save()
        start(clone,clone_values)
        for role,rows in before.items():
            require({x['session'] for x in call(clone,role,'list')}==set(rows),'CONFLICT')
            for sid,old in rows.items():
                new=call(clone,role,'observe',sid,'--content')
                require(new['restore_fenced'] is True and new['execution_authorized'] is False,'CONFLICT')
                for key in ('inputs','binding','allocation','capacity','state'):
                    require(new[key]==old[key],'CONFLICT')
                current=call(clone,role,'current',sid)
                require(current['restore_fenced'] is True,'CONFLICT')
                report['observations'].append(dict(role=role,
                    scope_class='private' if old['allocation']['template']=='private' else 'shared',
                    original_session_digest=digest(sid.encode()),retained_inputs=len(old['inputs']),
                    captured_projection_digest=digest(canonical(old['inputs'])),
                    original_deadlines_and_accounting_retained=True,
                    original_allocation_retained=True,current_owner_reads='PASS',
                    current_source_sequence=current.get('source_head',{}).get('sequence')))
                save()
            for operation,args in [('allocate',['--identity','forbidden-recheck','--template','shared']),
                                   ('reconcile',['--session',next(iter(rows))])]:
                try:call(clone,role,operation,None,*args)
                except RuntimeError as error:
                    require('UNAUTHORIZED' in str(error),'CONFLICT')
                else:require(False,'CONFLICT')
        report.update(status='PASS',restored_execution_authority=False,
            duplicate_effect_execution='NO_EXECUTOR_STARTED',current_private_port_selection='PASS')
        save()
    except BaseException as error:
        report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));save();raise
    finally:
        for name,op in [('original',original),('clone',clone)]:
            op.quiesce();report[name+'_quiesced']=True
        save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','original','clone','original-values','clone-values','chart','backup','directory'):
        p.add_argument('--'+name,required=True)
    a=p.parse_args();print(json.dumps(verify(Operator(a.kubeconfig,a.context,a.original),
        Operator(a.kubeconfig,a.context,a.clone),a.original_values,a.clone_values,a.chart,a.backup,a.directory)))
if __name__=='__main__':main()
