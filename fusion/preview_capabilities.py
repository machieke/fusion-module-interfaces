"""Executable current catalogue and evidence projection; historical map is fixed.

This registry is shared by admission and diagnostics. Evidence is an explicit
hashed observation attachment, never inferred from a rendered tool or endpoint.
"""
import argparse,json
from pathlib import Path
from .contracts import canonical,digest,require
from . import preview_tools as t

IMPLEMENTATIONS={
 'application.context.pin':('fusion.preview_application.PreviewAdoption.execute','pin'),
 'application.context.unpin':('fusion.preview_application.PreviewAdoption.execute','unpin'),
 'application.context.inspect':('fusion.preview_application.PreviewAdoption.execute','task-context'),
 'native.memory.remember':('fusion.neoclaw_append.MemoryAppend','createMemory / remember'),
 'native.memory.query':('fusion.neoclaw_memory.MemoryRead','query / getQueryResults'),
 'workspace.read':('fusion.preview_workspace.Workspace','read-file'),
 'workspace.write':('fusion.preview_workspace.Workspace','write-file'),
 'workspace.append':('fusion.preview_workspace.Workspace','append-file'),
 'native.history.episodes':('fusion.preview_native_history.NativeHistory','episodes'),
 'native.nal.truth-deduction':('fusion.neoclaw_application.Application','metta / NAL_Apply / Truth_Deduction'),
 'native.memory.supersede':('fusion.preview_native_memory.SharedMemory','update'),
 'native.memory.withdraw':('fusion.preview_native_memory.SharedMemory','forget'),
 'native.structure.link':('fusion.preview_native_relations.NativeRelations','link'),
 'native.structure.unlink':('fusion.preview_native_relations.NativeRelations','unlink'),
 'native.assessment.support':('fusion.preview_native_cognition.PreviewEvidence','support / Truth_Revision'),
 'native.assessment.contradict':('fusion.preview_native_cognition.PreviewEvidence','contradict / Truth_Revision'),
 'native.priority.promote':('fusion.preview_native_cognition.PreviewPriority','promote'),
 'native.priority.demote':('fusion.preview_native_cognition.PreviewPriority','demote'),
 'native.task.delegate':('fusion.preview_native_tasks.NativeTasks','delegate'),
 'native.execution.inspect-artifact':('fusion.preview_native_inspect.NativeInspection','inspect-atom / inspect_atom'),
}


def registered_tools(*,active=False,feed_profile='immutable-commit-feed/1'):
    values=(*t.context_tools(),*t.memory_tools(active=active,feed_profile=feed_profile),*t.workspace_tools(),*t.history_tools(),
        *t.deduction_tools(),*t.lifecycle_tools(feed_profile=feed_profile),*t.relation_tools(),*t.cognitive_tools(feed_profile=feed_profile),*t.task_tools(),*t.inspection_tools(feed_profile=feed_profile))
    require({x.tool_id for x in values}==set(IMPLEMENTATIONS) and len(values)==len(IMPLEMENTATIONS),'NOT_AVAILABLE')
    return values


def manifest(evidence=None):
    evidence={} if evidence is None else evidence
    require(type(evidence) is dict and set(evidence)<=set(IMPLEMENTATIONS))
    capabilities=[]
    for tool in registered_tools(active=True):
        implementation,entrypoint=IMPLEMENTATIONS[tool.tool_id];observed=evidence.get(tool.tool_id,{})
        require(type(observed) is dict and set(observed)<={'native','deployed','fixture','real_provider','reports'})
        require(all(type(observed[k]) is bool for k in set(observed)-{'reports'}))
        reports=observed.get('reports',[]);require(type(reports) is list)
        for report in reports:
            require(type(report) is dict and set(report)=={'path','sha256','source_manifest_sha256','classification'})
            require(report['classification'] in ('recorded-model-real-tools','fixture','real-provider','unrun','blocked'))
            require(type(report['source_manifest_sha256']) is str and len(report['source_manifest_sha256'])==64)
            path=Path(report['path']);require(not path.is_absolute() and '..' not in path.parts and path.parts[0]=='evidence','UNAUTHORIZED')
            require(digest(path.read_bytes())==report['sha256'],'CONFLICT')
        require(not any(observed.get(k,False) for k in ('native','deployed','fixture','real_provider')) or bool(reports),'NOT_AVAILABLE')
        capabilities.append(dict(tool=tool.wire(),implementation=implementation,native_entrypoint=entrypoint,
            families=sorted({r.interface for r in tool.requirements}) or ['application'],
            result_schema=dict(type='native-projection-text',max_utf8_bytes=tool.max_result_bytes,profile=tool.profile),
            scope='explicit synthetic session policy; handles are not authority',
            profile_combinations='operator selection validated against every declared requirement; no automatic fallback',
            semantics_changed=tool.semantics,evidence=observed,implemented=True,
            native_adopted=observed.get('native',False),deployed=observed.get('deployed',False)))
    return dict(schema='omega-current-capabilities/2',historical_family_denominator=15,historical_mapping_unchanged=True,
        capabilities=capabilities,extensions=['X01 ModelInference','X02 Embedding','X05 ToolDescriptor'],
        internal_capabilities=[dict(name=name,classification=classification,consumer=symbol) for name,classification,symbol in (
            ('bounded-native-session','application','fusion.preview_sessions.SessionStore'),
            ('recorded-model-completion','X01','fusion.preview_model.PreviewModel'),
            ('query-and-memory-embedding','X02','fusion.neoclaw_embedding.QueryEmbedding / MemoryEmbedding'),
            ('shared-lifecycle-view','explicit-preview-profile','fusion.preview_native_memory.SharedMemory'),
            ('correlated-task-result','Messaging + application','fusion.preview_native_tasks.NativeTasks.complete'),
            ('exact-approved-commitment','ConsensusFinality','fusion.preview_chain.Ports'))],
        excluded=['arbitrary-shell','arbitrary-metta','live-generation','physical-erasure','migration','multi-node'],additional_live_generations=0)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence');p.add_argument('--output',required=True);a=p.parse_args()
    value=json.loads(Path(a.evidence).read_text()) if a.evidence else None
    Path(a.output).write_bytes(canonical(manifest(value)))

if __name__=='__main__':main()
