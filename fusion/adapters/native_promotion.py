"""Checked extraction of native promotion arithmetic, no NAL import or Python formula."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
from .. import promotion_contracts as c
from ..contracts import ContractError,require,digest


def source(omega):
    from ..neoclaw_contracts import PINS
    text=(omega/'src/memory.metta').read_text()
    require(digest(text.encode())==PINS['sources']['mettaclaw']['files']['src/memory.metta'],'UNSUPPORTED_PROFILE')
    def body(name):
        start=text.index('(= ('+name+' ')
        return text[start:text.index('\n(= (',start+1)]
    value=body('get-promotion').replace('(get-promotion $current_time $uuid)','(promotion-score $current_time $promotion $last_time)')
    value=value.replace('(py-call (helper.promotion_get_value $uuid 0.0))','$promotion').replace('(py-call (helper.promotion_get_lasttime $uuid 0.0))','$last_time')
    # Extract exact native adjustment expressions after verifying whole source.
    expressions=[]
    for name,start in [('promote','(min 10.0'),('demote','(max 0.0')]:
        tail=body(name)[body(name).index(start):];depth=0
        for i,char in enumerate(tail):
            depth+=(char=='(')-(char==')')
            if depth==0:expressions.append(tail[:i+1]);break
    return value+'\n(= (promotion-plus $v) '+expressions[0]+')\n(= (promotion-minus $v) '+expressions[1]+')\n'


def checked_runtime(runtime_file):
    """Verify the existing build, but require only the pure interpreter sources.

    The native loop has its own full-source checks. This dependency must also
    work without MeTTaClaw NAL or PeTTa cognitive libraries being installed.
    """
    from ..neoclaw_contracts import PINS
    path=Path(runtime_file).resolve()
    try:
        runtime=json.loads(path.read_text());build=json.loads((path.parent/'build.json').read_text())
        require(build['source_pins']==PINS,'UNSUPPORTED_PROFILE')
        require(digest(path.read_bytes())==build['runtime_sha256'],'UNSUPPORTED_PROFILE')
        for key,sha in [('swipl','binary_sha256'),('python','python_binary_sha256')]:
            require(digest(Path(runtime[key]).resolve().read_bytes())==build[sha],'UNSUPPORTED_PROFILE')
        for file,sha in build['native_libraries'].items():
            require(digest((path.parent/file).read_bytes())==sha,'UNSUPPORTED_PROFILE')
        for file,sha in PINS['sources']['PeTTa']['files'].items():
            if file.startswith('src/') and file.endswith('.pl'):
                require(digest((Path(runtime['petta'])/file).read_bytes())==sha,'UNSUPPORTED_PROFILE')
        source(Path(runtime['mettaclaw']))
    except OSError:raise ContractError('NOT_AVAILABLE') from None
    env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','LC_ALL','TMPDIR')}
    env.update(runtime['environment']);return runtime,env


class NativePromotion:
    def __init__(self,runtime):
        self.path=Path(runtime)
        self.runtime,self.env=checked_runtime(self.path)
    def evaluate(self,rows,deadline_ms):
        require(type(rows) is list and len(rows)<=c.MAX_TARGETS,'INVALID_ARGUMENT')
        expr=[]
        for value,last,now,delta in rows:
            v=c.number(value,0,10);t=c.number(last);n=c.number(now);require(n>=t,'CONFLICT')
            require(type(delta) is int and delta in (-1,0,1),'INVALID_ARGUMENT')
            score='(promotion-score %s %s %s)'%(repr(n),repr(v),repr(t))
            expr.append('!'+('('+('promotion-plus' if delta==1 else 'promotion-minus')+' '+score+')' if delta else score))
        if not rows:return []
        remaining=deadline_ms/1000-time.time();require(remaining>0,'DEADLINE_EXCEEDED')
        runtime,env=checked_runtime(self.path)
        require(runtime==self.runtime and env==self.env,'CONFLICT')
        with tempfile.TemporaryDirectory(prefix='native-promotion-') as tmp:
            path=Path(tmp)/'promotion.metta'
            path.write_text(source(Path(self.runtime['mettaclaw']))+'\n'+'\n'.join(expr)+'\n')
            try:
                run=subprocess.run([self.runtime['swipl'],'-q','-s',str(Path(self.runtime['petta'])/'src/main.pl'),'--',str(path),'--silent'],
                    cwd=tmp,env=self.env,capture_output=True,text=True,timeout=min(5,remaining))
            except subprocess.TimeoutExpired:raise ContractError('DEADLINE_EXCEEDED') from None
            require(run.returncode==0 and len(run.stdout)<32768,'NOT_AVAILABLE')
        try:values=[float(x) for x in run.stdout.strip().splitlines()]
        except ValueError:raise ContractError('NOT_AVAILABLE') from None
        require(len(values)==len(rows),'NOT_AVAILABLE')
        for x in values:c.number(x,0,10)
        require(time.time()*1000<=deadline_ms,'DEADLINE_EXCEEDED');return values
