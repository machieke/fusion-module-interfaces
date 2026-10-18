"""Pure, local, pinned MeTTaClaw Truth_Revision. No Python production formula."""
import json
from pathlib import Path
import subprocess
import tempfile
import time
from .neoclaw_nal import NativeTruthDeduction
from .. import nal_memory_contracts as c
from ..contracts import ContractError, canonical, digest, require


class NativeTruthRevision(NativeTruthDeduction):
    def profile(self):
        return dict(model=c.MODEL, runtime=c.RUNTIME, formula=c.FORMULA,
                    runtime_sha256=digest(self.runtime_file.read_bytes()), cap='0.99',
                    inputs='finite-binary64-strength-closed-confidence-half-open', privacy='private-local-only')

    @staticmethod
    def parse(output):
        require(type(output) is str and len(output)<=8192,'NOT_AVAILABLE')
        lines=output.strip().splitlines()
        require(len(lines)==2 and lines[0]=='true','NOT_AVAILABLE')
        try: truth=c.native_truth(lines[1])
        except ContractError: raise ContractError('NOT_AVAILABLE') from None
        return dict(representation=lines[1],truth=truth)

    def evaluate(self,a,b,deadline_ms):
        c.truth(a); c.truth(b); c.integer(deadline_ms,1)
        values=[c.decimal(x[k], k=='confidence') for x in (a,b) for k in ('strength','confidence')]
        require(values[1]>0 or values[3]>0,'INVALID_ARGUMENT')
        remaining=deadline_ms/1000-time.time(); require(remaining>0,'DEADLINE_EXCEEDED')
        # Revalidate the source/runtime at every evaluation, not only at startup.
        NativeTruthDeduction(self.runtime_file)
        expression='(Truth_Revision (stv %s %s) (stv %s %s))'%tuple(map(repr,values))
        with tempfile.TemporaryDirectory(prefix='neoclaw-revision-') as directory:
            path=Path(directory)/'revision.metta'
            path.write_text('!(import! &self '+json.dumps(str(Path(self.runtime['mettaclaw'])/'lib_nal.metta'))+')\n!'+expression+'\n')
            try:
                run=subprocess.run([self.runtime['swipl'],'-q','-s',str(Path(self.runtime['petta'])/'src/main.pl'),
                    '--',str(path),'--silent'],cwd=directory,env=self.env,capture_output=True,text=True,timeout=min(5,remaining))
            except subprocess.TimeoutExpired:
                raise ContractError('DEADLINE_EXCEEDED' if time.time()*1000>=deadline_ms else 'NOT_AVAILABLE') from None
            except OSError: raise ContractError('NOT_AVAILABLE') from None
        require(run.returncode==0,'NOT_AVAILABLE'); result=self.parse(run.stdout)
        require(time.time()*1000<deadline_ms,'DEADLINE_EXCEEDED'); return result

    def revise(self,existing,incoming,revision,independence,*,deadline_ms):
        for value in (existing,incoming): c.support(value,existing['claim']['scope_ref'])
        require(existing['claim']==incoming['claim'] and existing['context']==incoming['context'],'CONFLICT')
        if independence is None: return dict(status='UNKNOWN',detail='independence or prior application not authorized',proposal=None)
        c.independence(independence)
        require(set(independence['supports'])=={existing['id'],incoming['id']},'CONFLICT')
        if set(existing['lineage_roots']) & set(incoming['lineage_roots']) or set(existing['evidence_ids']) & set(incoming['evidence_ids']):
            return dict(status='UNKNOWN',detail='overlapping source lineage; retain assessment',proposal=None)
        if not incoming['lineage_roots']: return dict(status='UNKNOWN',detail='unknown source lineage',proposal=None)
        if not (c.decimal(existing['truth']['confidence'],True)>0 or c.decimal(incoming['truth']['confidence'],True)>0):
            return dict(status='FAIL',detail='zero total weight',proposal=None)
        result=self.evaluate(existing['truth'],incoming['truth'],deadline_ms)
        p=dict(id='revision/'+digest(canonical([existing,incoming,revision,independence,self.profile(),result])),
            claim=existing['claim'],context=existing['context'],truth=result['truth'],
            premises=[existing['id'],incoming['id']],formula=c.FORMULA,
            assumptions=['compatibility-mass-not-calibrated','independence:'+independence['model_id']],kind='revision',
            representation=result['representation'])
        for k in ('coverage','evidence_ids','lineage_roots'): p[k]=sorted(set(existing[k])|set(incoming[k]))
        response=dict(status='PASS',detail='pinned native capped NAL revision',proposal=p)
        c.math_result(response,existing,incoming,independence); return response
