"""Pure grounded kernel: pinned upstream guards and native mathematics only."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from .pln_revision import PINS, RevisionRuntime, GuardedRevision, run, verify_source, reuse, remaining
from .. import cognition_contracts as c
from ..contracts import ContractError, canonical, digest, require


def from_literal(upstream, value):
    c.literal(value)
    return upstream.Literal(upstream.Statement(value['predicate'], tuple(value['arguments'])), value['positive'])


def from_ancestors(values):
    literals=[{'predicate':v.statement.predicate,'arguments':list(v.statement.arguments),'positive':v.positive} for v in values]
    return sorted(literals,key=canonical)


def to_support(upstream, value):
    c.support(value, value['claim']['scope_ref'])
    return upstream.ProbabilisticSupport(value['id'], value['context'], from_literal(upstream, value['literal']),
        upstream.TruthValue(c.decimal(value['truth']['strength']), c.decimal(value['truth']['confidence'], True)),
        tuple(value['evidence_ids']), tuple(value['lineage_roots']), tuple(from_literal(upstream,a) for a in value['ancestors']))


def numerical(proposal):
    return {'model': c.MODEL, 'strength': repr(proposal.support.truth.strength),
            'confidence': repr(proposal.support.truth.confidence), 'evidence_count': None}


class DeductionRuntime(RevisionRuntime):
    """A separate allowlist; the revision-only runtime retains its old meaning."""
    def __init__(self, config, upstream, deadline_ms, *, timeout=10):
        super().__init__(config, upstream, timeout=timeout); self.deadline_ms=deadline_ms

    @c.boundary
    def check(self):
        require(self.config['runtime_profile']==c.RUNTIME,'UNSUPPORTED_PROFILE')
        for name in ('reachability','pln','petta'): verify_source(name,self.config[name],self.deadline_ms)
        remaining(self.deadline_ms)
        binary=Path(self.config['swipl']).resolve()
        require(hashlib.sha256(binary.read_bytes()).hexdigest()==self.config['swipl_sha256'],'UNSUPPORTED_PROFILE')
        version=run([binary,'--version'],deadline_ms=self.deadline_ms)
        require(version.startswith('SWI-Prolog version 10.1.14 '),'UNSUPPORTED_PROFILE')

    def evaluate(self, formula, truths):
        require(formula=='Truth_Deduction' and type(truths) is tuple and len(truths)==5)
        require(all(type(t) is self.upstream.TruthValue for t in truths));self.check()
        library=str(Path(self.config['pln'])/'lib_pln.metta')
        require(not any(x in library for x in ('"','\\','\n','\r')),'UNSUPPORTED_PROFILE')
        p,q,r,pq,qr=[repr(t.strength) for t in truths]
        formula_expression='(Truth_Deduction ' + ' '.join(t.metta() for t in truths) + ')' 
        # The upstream runtime's guard expression, with its unchanged native formula.
        expression=f'(if (and (conditional-probability-consistency {p} {q} {pq}) (conditional-probability-consistency {q} {r} {qr})) {formula_expression} ReachabilityRejected)'
        with tempfile.TemporaryDirectory(prefix='fusion-private-deduction-') as directory:
            path=Path(directory)/'deduction.metta';path.write_text(f'!(import! &self "{library}")\n!{expression}\n')
            output=run([self.config['swipl'],'-q','-s',str(Path(self.config['petta'])/'src/main.pl'),'--',path,'--silent'],
                       timeout=self.timeout,deadline_ms=self.deadline_ms,env=dict(os.environ,**self.config.get('environment',{})))
        if output.strip().splitlines()==['true','ReachabilityRejected']:
            raise self.upstream.PLNRejected(self.upstream.Status.UNKNOWN,'runtime probability check disagrees with exact precheck')
        return self.parse(output)


class GuardedDeduction:
    def __init__(self, environment, *, runtime_fixture=None, timeout=10):
        lock=json.loads((Path(__file__).resolve().parents[2]/'integration/pln/deduction-sources.json').read_text())
        require(lock['sources']==PINS['sources'] and lock['runtime_profile']==c.RUNTIME and lock['rule_profile']==c.RULE and lock['allowlist']==['Truth_Deduction'],'UNSUPPORTED_PROFILE')
        self.config=json.loads(Path(environment).read_text());self.upstream=reuse(self.config['reachability'])
        self.timeout,self.runtime_fixture=timeout,runtime_fixture
        DeductionRuntime(self.config,self.upstream,None,timeout=timeout).check()
        self.identity={'profile':c.RULE,'model':c.MODEL,'runtime_profile':c.RUNTIME,
            'provider':'recording-runtime-fixture' if runtime_fixture else 'real-petta-pln',
            'sources':PINS['sources'],'swipl':PINS['swipl_version'],'binary_sha256':self.config['swipl_sha256']}

    def profile(self): return c.detached(self.identity)

    @c.boundary
    def applyRule(self, task, premises, deadline_ms):
        c.integer(deadline_ms,1);remaining(deadline_ms)
        scope=task['ref']['scope_ref'];context=task['record']['context'];literals=c.task(task,scope,context)
        require(type(premises) is tuple and len(premises)==5)
        for role,item in zip(c.ROLES,premises):
            c.fields(item,'binding support');c.binding(item['binding'],scope,context);c.support(item['support'],scope)
            b,s=item['binding'],item['support']
            require(b['claim']==task['record']['roles'][role]==s['claim'] and b['support_id']==s['id'])
            require(s['context']==context and s['literal']==literals[role])
        native=DeductionRuntime(self.config,self.upstream,deadline_ms,timeout=self.timeout)
        native.check()  # source/profile checks count against the operation's deadline
        adapter=self.upstream.PLNAdapter(self.runtime_fixture or native)
        rule=self.upstream.DeductionRule(*[digest(canonical(task['record']['roles'][role])) for role in ('p','q','r')])
        snapshot=self.upstream.ProbabilitySnapshot(context,0,tuple(to_support(self.upstream,p['support']) for p in premises))
        try: proposal=adapter.apply_rule(rule,snapshot)
        except self.upstream.PLNRejected as error:
            return {'status':error.status.value,'detail':str(error)[:256],'proposal':None}
        remaining(deadline_ms)
        vector=[p['binding'] for p in premises];kernel=digest(canonical(self.profile()))
        identity=c.logical_id(task['ref'],vector,kernel)
        support={'id':identity,'claim':task['record']['roles']['pr'],'context':context,'truth':numerical(proposal),
            'evidence_ids':list(proposal.support.evidence_ids),'lineage_roots':list(proposal.support.lineage_roots),
            'coverage':[identity],'premises':vector,'formula':proposal.formula_id,'assumptions':list(proposal.assumptions),
            'kind':'deduction','literal':literals['pr'],'ancestors':from_ancestors(proposal.support.ancestors),
            'coverage_kind':c.COVERAGE,'task':task['ref'],'kernel_selection':kernel}
        result={'status':'PASS','detail':'native guarded grounded deduction','proposal':support}
        c.response(c.kernel_result,result,task,premises,kernel);return result


class GuardedRevisionWithAncestry(GuardedRevision):
    """M3 literal mapping; numerical revision remains the same guarded implementation."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        self.identity={**super().profile(),'support_profile':c.BELIEF_PROFILE}

    def profile(self): return c.detached(self.identity)

    def revise(self, existing, incoming, revision, independence):
        self.native.check();c.integer(revision)
        a,b=to_support(self.upstream,existing),to_support(self.upstream,incoming)
        require(existing['claim']==incoming['claim'] and existing['context']==incoming['context'],'CONFLICT')
        declaration=None
        if independence is not None:
            c.independence(independence);require(set(independence['supports'])=={existing['id'],incoming['id']},'CONFLICT')
            declaration=self.upstream.IndependenceDeclaration(independence['model_id'],(a,b))
        result=self.adapter.revise(a,b,revision,declaration);support=None
        if result.proposal:
            p=result.proposal
            support={'id':p.support.support_id,'claim':existing['claim'],'context':existing['context'],'truth':numerical(p),
                'evidence_ids':list(p.support.evidence_ids),'lineage_roots':list(p.support.lineage_roots),
                'coverage':sorted(set(existing['coverage'])|set(incoming['coverage'])),
                'premises':list(p.premise_ids),'formula':p.formula_id,'assumptions':list(p.assumptions),
                'kind':'revision','literal':existing['literal'],'ancestors':from_ancestors(p.support.ancestors),'coverage_kind':c.COVERAGE}
        output={'status':result.status.value,'detail':result.detail,'proposal':support}
        c.response(c.math_result,output,existing,incoming,independence);return output
