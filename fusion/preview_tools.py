"""Operator-selected native vocabulary, separate from provider discovery.

This opt-in catalogue never grants authority by describing a tool. The same
closed argument schema is used for prompt presentation and whole-batch
admission. Historical fixed-profile catalogues are not changed.
"""
from dataclasses import asdict, dataclass
import re

from .contracts import canonical, digest, require
from .registry import Requirement, resolve, selection_token

PROFILE = 'omega-developer-tools/1'
VOCABULARY = 'omega-developer-native/1'
EFFECTS = frozenset({'read', 'application-mutation', 'shared-mutation',
                     'external-observation', 'external-send'})
AUDIENCES = frozenset({'model', 'operator', 'internal', 'fixture'})


@dataclass(frozen=True)
class Argument:
    name: str
    kind: str = 'text'
    max_bytes: int = 4096

    def validate(self, value):
        require(type(value) is str and 0 < len(value.encode('utf-8')) <= self.max_bytes)
        require('\x00' not in value)
        if self.kind in ('handle','memory-handle','relation-handle','history-handle'):
            from .preview_handles import parse
            parsed=parse(value,{'memory-handle':'memory','relation-handle':'relation'}.get(self.kind))
            if self.kind=='history-handle':require(parsed.kind in ('episode','event'))
        elif self.kind=='agent':require(value in ('A','B'),'UNAUTHORIZED')
        elif self.kind=='deduction':
            from .neoclaw_contracts import parse_expression
            parse_expression(value)
        elif self.kind == 'label':
            require(re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', value) is not None)
        elif self.kind == 'path':
            require(re.fullmatch(r'[a-zA-Z0-9_-]{1,48}(?:\.[a-zA-Z0-9_-]{1,12})?', value) is not None)
        else:
            require(self.kind == 'text', 'UNSUPPORTED_PROFILE')
        return value


@dataclass(frozen=True)
class ToolDescriptor:
    tool_id: str
    native_name: str
    profile: str
    arguments: tuple[Argument, ...]
    effect: str
    requirements: tuple[Requirement, ...]
    summary: str
    semantics: str
    replay: str = 'same-occurrence-saved-result-current-authority'
    audience: frozenset[str] = frozenset({'model', 'operator'})
    max_result_bytes: int = 16384
    timeout_ms: int = 30000
    attempts: int = 2
    vocabulary: str = VOCABULARY
    version: str = '1.0.0'

    def __post_init__(self):
        require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', self.native_name) is not None)
        require(self.effect in EFFECTS and self.audience <= AUDIENCES)
        require(1 <= self.timeout_ms <= 120000 and 1 <= self.attempts <= 4)
        require(1 <= self.max_result_bytes <= 65536 and len(self.arguments) <= 4)
        # Descriptions are trusted source, still rendered only as quoted data.
        require(type(self.summary) is str and 0 < len(self.summary.encode()) <= 1024)

    def validate(self, command):
        require(type(command) is list and len(command) == 1 + len(self.arguments))
        require(command[0] == self.native_name, 'UNSUPPORTED_OPERATION')
        return {a.name: a.validate(v) for a, v in zip(self.arguments, command[1:])}

    def wire(self):
        def normal(value):
            if isinstance(value, (set, frozenset)): return sorted(value)
            if isinstance(value, (list, tuple)): return [normal(v) for v in value]
            if isinstance(value, dict): return {k: normal(v) for k, v in value.items()}
            return value
        return normal(asdict(self))


class Catalogue:
    """Only locally registered adapters plus operator-trusted providers qualify."""
    def __init__(self, tools, implementations, providers):
        self.tools = {}
        self.selections = {}
        for tool in tools:
            require(tool.tool_id in implementations, 'NOT_AVAILABLE')
            require(tool.native_name not in self.tools, 'CONFLICT')
            self.tools[tool.native_name] = tool
            self.selections[tool.native_name] = [resolve(providers, r) for r in tool.requirements]

    def binding(self):
        return dict(profile=PROFILE, tools={name: dict(descriptor=tool.wire(),
            providers=[selection_token(d) for d in self.selections[name]])
            for name, tool in sorted(self.tools.items())})

    @property
    def identity(self): return digest(canonical(self.binding()))

    def skills(self, authority, principal, now_ms):
        authority.check(principal, now_ms)
        return ['- '+t.summary+': '+name+' '+' '.join(a.kind for a in t.arguments)
                for name, t in sorted(self.tools.items())
                if name in authority.tools and 'model' in t.audience]

    def admit(self, commands, authority, principal, now_ms, expected_binding=None):
        authority.check(principal, now_ms)
        require(expected_binding is None or expected_binding == self.identity, 'CONFLICT')
        require(type(commands) is list and 1 <= len(commands) <= 5)
        admitted = []
        for command in commands:
            require(type(command) is list and command and type(command[0]) is str)
            name = command[0]
            require(name in self.tools, 'UNSUPPORTED_OPERATION')
            require(name in authority.tools, 'UNAUTHORIZED')
            tool = self.tools[name]
            admitted.append(dict(tool_id=tool.tool_id, profile=tool.profile,
                arguments=tool.validate(command), selection=self.identity,
                policy=authority.revision, scope=authority.scope))
        # No dispatch occurs here. Every command must pass before admission.
        return admitted


@dataclass(frozen=True)
class SessionAuthority:
    principal: str
    scope: str
    tools: frozenset[str]
    revision: str
    expires_ms: int
    revoked: bool = False

    def __post_init__(self):
        from .contracts import label
        require(label(self.principal) and label(self.scope) and label(self.revision))
        require(type(self.expires_ms) is int and self.expires_ms > 0 and type(self.revoked) is bool)
        require(type(self.tools) is frozenset and len(self.tools) <= 32)
        require(all(type(x) is str and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', x) for x in self.tools))

    def check(self, principal, now_ms):
        require(principal == self.principal and not self.revoked, 'UNAUTHORIZED')
        require(type(now_ms) is int and now_ms < self.expires_ms, 'UNAUTHORIZED')
        require(self.scope.startswith('synthetic-'), 'UNAUTHORIZED')


def context_tools():
    return (
        ToolDescriptor('application.context.pin', 'pin', 'working-task-context/1',
            (Argument('item', 'label'), Argument('note')), 'application-mutation', (),
            'Set an unverified task note', 'New preview behavior; no truth or attention effect.'),
        ToolDescriptor('application.context.unpin', 'unpin', 'working-task-context/1',
            (Argument('item', 'label'),), 'application-mutation', (),
            'Clear a task note', 'Logical removal from new context; prior captures retained.'),
        ToolDescriptor('application.context.inspect', 'task-context', 'working-task-context/1',
            (), 'read', (), 'Inspect bounded task notes', 'Read committed application state, not evidence.'),
    )


def deduction_tools():
    from . import neoclaw_contracts as c
    profiles={'atom.storage':'immutable-bytes/1','agent.messaging':'durable-mailbox/2','pln.kernel':c.PROFILE,'execution':c.PROFILE}
    requirements=tuple(Requirement(d.interface,d.version,str(int(d.version.split('.')[0])+1)+'.0.0',
        profiles[d.interface],d.operations,d.guarantees,
        privacy=d.privacy,features=d.features) for d in c.catalogue('detta'))
    return (ToolDescriptor('native.nal.truth-deduction','metta',c.PROFILE,(Argument('expression','deduction'),),
        'shared-mutation',requirements,'Execute only two-STV Truth_Deduction',
        'Pinned original NAL operation; no arbitrary MeTTa, import or other function.'),)


def memory_tools(*,active=False,feed_profile='immutable-commit-feed/1'):
    from . import append_contracts as w, embedding_contracts as e, vector_contracts as v
    from .vector_composition import descriptors as read_descriptors
    def requirement(d, maximum):
        return Requirement(d.interface, d.version, maximum, next(iter(d.profiles)), d.operations,
                           d.guarantees, privacy=d.privacy, features=d.features)
    write = [requirement(d, '1.3.0' if d.interface == 'atom.storage' else '3.2.0') for d in w.descriptors(feed_profile)]
    write.append(requirement(e.descriptor(e.MEMORY_PROFILE), '1.1.0'))
    read = [requirement(d, '1.2.0' if d.interface == 'atom.storage' else '3.2.0') for d in read_descriptors(v.EMBEDDING, True,feed_profile)]
    read.append(requirement(e.descriptor(), '1.1.0'))
    if active:
        from .preview_memory_services import descriptor
        from .preview_vector_contracts import PROFILE as active_profile
        read=[r for r in read if r.interface!='search']
        read.append(requirement(descriptor('search'),'3.3.0'))
    return (
        ToolDescriptor('native.memory.remember', 'remember', w.PROFILE, (Argument('content', max_bytes=1024),),
                       'shared-mutation', tuple(write), 'Remember new synthetic content',
                       'Append-only immutable content; storage, publication and native readiness are separate.'),
        ToolDescriptor('native.memory.query', 'query', active_profile if active else v.PROFILE, (Argument('query', max_bytes=1024),),
                       'read', tuple(read), 'Query approved synthetic memories',
                       'Captured E5 vector, retained Search view, verified payloads and native local enrichment.'),
    )


def workspace_tools():
    from .preview_ports import descriptor
    d=descriptor('execution.workspace')
    requirement=Requirement(d.interface,d.version,'1.1.0',next(iter(d.profiles)),d.operations,
                            d.guarantees,privacy=d.privacy,features=d.features)
    return tuple(ToolDescriptor('workspace.'+op,op+'-file',next(iter(d.profiles)),
        (Argument('path','path'),) if op=='read' else (Argument('path','path'),Argument('text',max_bytes=8192)),
        'read' if op=='read' else 'shared-mutation',(requirement,),
        {'read':'Read a synthetic workspace file','write':'Replace a synthetic workspace file','append':'Append a synthetic workspace line'}[op],
        'Explicit bounded workspace; logical filename only; atomic bytes and separate durable effect receipt.')
        for op in ('read','write','append'))


def history_tools():
    from .preview_ports import descriptor
    d=descriptor('episodic.memory')
    requirement=Requirement(d.interface,d.version,'1.1.0',next(iter(d.profiles)),d.operations,d.guarantees,
                            privacy=d.privacy,features=d.features)
    return (ToolDescriptor('native.history.episodes','episodes',next(iter(d.profiles)),
        (Argument('selector',max_bytes=100),),'read',(requirement,),
        'Read chronological session events using current or a returned page selector',
        'New history profile; administrative event sequence, fixed snapshot and explicit pagination, no empirical weight.'),)


def lifecycle_tools(*,feed_profile='immutable-commit-feed/1'):
    from .preview_memory_services import descriptor
    req=tuple(Requirement(d.interface,d.version,'1.1.0' if n=='memory.lifecycle' else '3.3.0',next(iter(d.profiles)),
        d.operations,d.guarantees,privacy=d.privacy,features=d.features) for n in ('memory.lifecycle','search') for d in [descriptor(n)])
    remember=memory_tools(active=True,feed_profile=feed_profile)[0]
    return (
        ToolDescriptor('native.memory.supersede','update','immutable-memory-lifecycle/1',
            (Argument('target','memory-handle'),Argument('content',max_bytes=1024)),'shared-mutation',remember.requirements+req,
            'Supersede a memory handle with new immutable content','Experimental supersession; no empirical weight, links or priority transferred. Prior bytes/history retained.'),
        ToolDescriptor('native.memory.withdraw','forget','immutable-memory-lifecycle/1',(Argument('target','memory-handle'),),
            'shared-mutation',req,'Withdraw a memory handle from active retrieval','Logical withdrawal, not physical erasure; old captured results retained but normal disclosure rechecks visibility.'),
    )


def relation_tools():
    from .preview_ports import descriptor
    req=tuple(Requirement(d.interface,d.version,'1.1.0',next(iter(d.profiles)),d.operations,
        d.guarantees,privacy=d.privacy,features=d.features)
        for name in ('relations','episodic.memory') for d in [descriptor(name)])
    return (
        ToolDescriptor('native.structure.link','link','schema-ordered-retractable-relations/1',
            (Argument('memory','memory-handle'),Argument('history','history-handle')),'shared-mutation',req,
            'Link an active memory to an exact returned episode or event handle',
            'Typed ordered structural association; creates no evidence weight or priority.'),
        ToolDescriptor('native.structure.unlink','unlink','schema-ordered-retractable-relations/1',
            (Argument('relation','relation-handle'),),'shared-mutation',req,
            'Retract one exact returned relation handle',
            'Logical structural retraction only; historical payloads and evidence contributions remain.'),
    )


def cognitive_tools(*,feed_profile='immutable-commit-feed/1'):
    from . import cognitive_services as cs,nal_memory_contracts as n,promotion_contracts as p
    requirements={d.interface:Requirement(d.interface,d.version,'1.1.0',feed_profile if d.interface=='atom.storage' else cs.PROFILES[d.interface],d.operations,
        d.guarantees,privacy=d.privacy,features=d.features) for d in cs.descriptors(feed_profile=feed_profile)}
    return tuple(ToolDescriptor('native.assessment.'+op,op,n.PROFILE,
        (Argument('memory','memory-handle'),Argument('source','history-handle')),'shared-mutation',
        tuple(requirements[k] for k in ('atom.storage','episodic.memory','belief.revision')),
        'Assess a memory using an exact captured source-event handle',
        'Original guarded NAL revision; repeated source contributes once; contrary assessment is retained; prior is not evidence.')
        for op in ('support','contradict'))+tuple(ToolDescriptor('native.priority.'+op,op,p.PROFILE,
        (Argument('memory','memory-handle'),),'shared-mutation',(requirements['attention'],),
        'Adjust owned wall-clock memory priority',
        'Pinned native promotion policy; atomic value/time/receipt; no truth or vector-index changes.')
        for op in ('promote','demote'))


def task_tools():
    from .preview_tasks import PROFILE,descriptor
    d=descriptor()
    return (ToolDescriptor('native.task.delegate','delegate',PROFILE,(Argument('recipient','agent',1),Argument('query','text',512)),
        'shared-mutation',(Requirement('agent.messaging','1.0.0','1.1.0',PROFILE,frozenset({'authorize','send','published','poll','ack'}),
            frozenset({'scoped','idempotent','process-restart'}),privacy='generated-shareable'),),
        'Delegate one retrieval query to the other approved agent',
        'Fixed-role nonrecursive retrieval; actual captured result returns through Messaging; no independent evidence weight',timeout_ms=120000),)


def inspection_tools(*,feed_profile='immutable-commit-feed/1'):
    from .contracts import PROFILES
    from . import cognitive_services as cs
    atom=cs.descriptors(feed_profile=feed_profile)[0]
    requirements=tuple(Requirement(name,'1.0.0','1.0.1',PROFILES[name],frozenset(ops),
        frozenset({'process-restart','scoped','idempotent'})) for name,ops in
        [('execution',('submit','status','result')),('agent.messaging',('poll','ack'))])
    requirements+=(Requirement(atom.interface,atom.version,'1.1.0',feed_profile,frozenset({'create','get'}),atom.guarantees,privacy=atom.privacy),)
    return (ToolDescriptor('native.execution.inspect-artifact','inspect-atom','synthetic-agent-retrieval-artifact/1',
        (Argument('task','label'),),'shared-mutation',requirements,
        'Inspect a compact synthetic artifact from an already consumed delegated result',
        'Existing inspect_atom operation only; exact authoritative content, independent completion acknowledgment; grants no chain approval.'),)
