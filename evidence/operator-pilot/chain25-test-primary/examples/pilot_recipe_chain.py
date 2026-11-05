"""Registered artifact recipe -> exact approval -> existing isolated chain graph.

No new workflow or chain semantics. The named historical inspection covers the
bounded retrieval-artifact envelope. The historical workspace representation
contains the exact captured task projection. An explicitly selected reference
document instead names that retained result without truncating it.
The operator approves only after both actual captures exist. Recorded proposals
select tools; native agents and deployed owners perform every effect.
"""
import argparse,json,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from fusion.workflow_recipes import native_object
from integration.single_node.reference_ops import Operator,PYTHON
from examples.integrated_sustained import IntegratedRunner as Runner
from examples.integrated_chain_continuation import IntegratedChain
from examples.pilot_recipe_qualification import qualify
from examples.pilot_go_provider import next_context


def check_lineage(workspace,readback,source):
    """Compare actual observations, never an evaluator answer or substituted bytes."""
    require(workspace['outcome']=='committed' and workspace['profile']==readback['profile'] and
        workspace['path']==readback['path']=='review.txt' and workspace['revision']==readback['revision'],'CONFLICT')
    require(type(source['projection']) is str and readback['text']==source['projection'],'CONFLICT')
    raw=source['projection'].encode()
    require(workspace['digest']==readback['digest']==digest(raw) and workspace['bytes']==len(raw),'CONFLICT')
    return dict(source_result_ref=source['result_ref'],projection_sha256=digest(raw),workspace=dict(workspace),
        workspace_readback_sha256=digest(canonical(readback)),same_task=source['task'],
        artifact_ref=source['artifact_ref'],inspection_boundary='IMMUTABLE_TASK_RESULT_ENVELOPE',
        workspace_and_inspection_share_captured_task_result=True)


class RecipeChain(IntegratedChain):
    representation='full-projection'

    def native(self):
        result=qualify(self.op,self.root/'registered-recipe','approved-artifact-delivery/1',
            retain_for_chain=True,representation=self.representation)
        native_path=self.root/'registered-recipe/workflow-native.json'
        native=json.loads(native_path.read_bytes());steps=result['final']['steps'];sid=result['session']
        inspection=next(x for x in native['inputs'] if x['identity']==steps['inspect']['input_id'])
        from examples.pilot_artifact_reference import returned_object
        written=next(x for x in native['inputs'] if x['identity']==steps['artifact']['input_id'])
        workspace=returned_object(written['observed']['result'],written['command'])
        inspected=result['evidence']['inspection'];require(inspected['caller_acknowledged'] is True,'NOT_AVAILABLE')
        # This is another explicit native read; it also consumes the captured
        # inspection in its next model context. No expected bytes are supplied.
        require(time.time_ns()//1000000+120000<result['qualification_end_ms'],'NOT_AVAILABLE')
        r=Runner(self.op,self.root/'workspace-readback',maximum_inputs=1);r.ids['omega-agent']=[sid]
        r.end=time.monotonic()+min(180,(result['qualification_end_ms']-time.time()*1000)/1000)
        r.run('read-file review.txt');r.save()
        readback=returned_object(r.report['inputs'][-1]['observed']['result'],'read-file review.txt')
        self.report['next_context_evidence']=next_context(self.op,sid,inspected)
        # Hydration uses the caller's current declared AtomStorage read port.
        # It reads neither provider databases nor another owner's mutable files.
        script='''import json,sys
from pathlib import Path
from fusion.preview_atoms import client
from fusion.preview_artifact_contracts import record
from fusion.preview_native_history import read_body
from fusion.preview_tasks import record as task_record
from fusion.contracts import require
sid,ref=sys.argv[1:];ref=json.loads(ref)
app=json.loads((Path('/run/fusion/sessions')/sid/'application.json').read_bytes())
a=client(json.loads(Path(app['history_atoms_config']).read_bytes()));artifact=record(json.loads(a.get(ref).bytes),app['preview']['scope'])
body=task_record(read_body(a,artifact['result_ref'])['body'],artifact['scope'])
require(body['id']==artifact['task'] and body['status']=='captured-native-query','CONFLICT')
print(json.dumps(dict(projection=body['projection'],result_ref=artifact['result_ref'],task=artifact['task'],artifact_ref=ref,body=body,artifact=artifact)))'''
        source=json.loads(self.op.k('exec','omega-agent-0','--',PYTHON,'-c',script,sid,json.dumps(inspected['artifact']),timeout=40))
        require(source['body']==result['artifact_source']['result'] and
            source['artifact']==result['artifact_source']['inspection_preflight'],'CONFLICT')
        if self.representation=='reference-document':
            from examples.pilot_artifact_reference import verify
            self.report['workspace_source_lineage']=verify(workspace,readback,result['artifact_source'],source['artifact'])
        else:self.report['workspace_source_lineage']=check_lineage(workspace,readback,source)
        self.report['representation']=self.representation
        self.report.update(native_report_sha256=digest(native_path.read_bytes()),session=sid,
            occurrence=inspection['observed']['result']['occurrences'][0],inspection=inspected,
            native_workflow=dict(result,accepted_deadline_retained=inspection['observed']['deadline']),
            original_inputs=[*native['inputs'],*r.report['inputs']],
            direct_operator_inputs=2,registered_workflow_inputs=3,total_operator_selected_native_inputs=5,
            model='RECORDED_PROPOSALS',providers='REAL_NATIVE_E5_CHROMA_DETTA_EXECUTION_MESSAGING_POD_HTTPS')
        self.save()

    def save(self):
        # Retain the established Q owner/recovery implementation while recording
        # this programme's exact authorization and input count in every report.
        if 'approval_basis' in self.report:
            self.report['approval_basis']='Assigned V34/Story G generated shareable recipe; separate exact observed result registration after native capture'
        if 'maximum_native_operator_inputs' in self.report:self.report['maximum_native_operator_inputs']=5
        super().save()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','values','chart','output','observer'):p.add_argument('--'+name,required=True)
    p.add_argument('--resume-from');p.add_argument('--readback-only',action='store_true')
    p.add_argument('--representation',choices=['full-projection','reference-document'],default='full-projection')
    p.add_argument('--consumer-path-health',action='store_true',help='Bounded non-work TLS readiness before one original independent reader')
    a=p.parse_args();q=RecipeChain(Operator(a.kubeconfig,a.context,a.namespace),a.values,a.chart,a.output)
    q.representation=a.representation
    try:
        if a.readback_only:
            require(a.resume_from is not None,'INVALID_ARGUMENT');q.readback_only(a.resume_from)
        else:q.run_graph(a.resume_from)
        q.independent(a.observer,consumer_path_health=a.consumer_path_health)
    except BaseException as error:
        q.report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[:1024]));raise
    finally:
        q.op.quiesce();q.report['quiesced']=True;q.save()
    print(json.dumps(dict(status=q.report['status'],additional_live_generations=0)))

if __name__=='__main__':main()
