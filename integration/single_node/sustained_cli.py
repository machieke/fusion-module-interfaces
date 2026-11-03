"""Installed operator entry point for the bounded sustained preview.

Uses the existing Helm recipe, owned namespace checks and pod-resident client.
It never opens provider databases, runs a model or regenerates credentials on
upgrade. All effect/cancellation identities are explicit operator inputs.
"""
import argparse,json,subprocess,sys
from pathlib import Path
from fusion.contracts import require
from .reference_ops import Operator,PYTHON


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kubeconfig',required=True);p.add_argument('--context',required=True);p.add_argument('--namespace',required=True)
    p.add_argument('--agent',choices=('omega-agent','omega-agent-b'),default='omega-agent')
    p.add_argument('action',choices=('preflight','install','upgrade','inventory','allocate','submit','observe','pause','resume','close','archive','cancel','reconcile','capacity','current','list','project','chain-observe','backup','restore','stop','qualify'))
    p.add_argument('--chart');p.add_argument('--values');p.add_argument('--directory');p.add_argument('--fenced',action='store_true')
    p.add_argument('--session');p.add_argument('--identity');p.add_argument('--text');p.add_argument('--assignment',default='synthetic-task');p.add_argument('--template');p.add_argument('--target');p.add_argument('--content',action='store_true');p.add_argument('--request-file')
    a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace)
    if a.action=='preflight':value=op.preflight()
    elif a.action in ('install','upgrade'):
        require(a.chart and a.values and Path(a.chart).exists() and Path(a.values).is_file())
        if a.action=='install':
            require(a.directory and not Path(a.directory).exists(),'CONFLICT');op.create()
            from fusion_operator.recipes.create_secrets import main as secrets
            original=sys.argv
            try:
                sys.argv=['fusion-create-secrets','--preview-values',str(Path(a.values).resolve()),'--kubeconfig',op.kubeconfig,'--context',op.context,'--namespace',op.namespace,'--directory',str(Path(a.directory).resolve())]
                secrets()
            finally:sys.argv=original
        else:op.owned()
        value=op.command(['helm','upgrade','--install','omega',str(Path(a.chart).resolve()),'-f',str(Path(a.values).resolve()),'--kubeconfig',op.kubeconfig,'--kube-context',op.context,'--namespace',op.namespace,'--wait','--timeout','5m'],timeout=320)
    elif a.action=='backup':require(a.directory is not None);value=op.backup(a.directory)
    elif a.action=='restore':
        require(a.directory is not None and a.fenced,'UNAUTHORIZED');op.create();value=op.restore(a.directory)
    elif a.action=='stop':value=op.quiesce()
    elif a.action=='qualify':
        require(a.directory is not None)
        from .sustained_qualification import qualify
        value=qualify(op,a.directory)
    else:
        op.owned();args=[a.action]
        for name in ('session','identity','text','template','target'):
            if getattr(a,name) is not None:args+=['--'+name,getattr(a,name)]
        if a.action=='submit':args+=['--assignment',a.assignment]
        if a.content:args+=['--content']
        if a.action=='project':
            # No request file or approval is installed as a provider default.
            require(a.request_file is not None)
            raw=Path(a.request_file).read_bytes();require(len(raw)<=16384)
            from fusion.preview_client import strict_json
            body=strict_json(raw)
            script='import json,sys;from integration.single_node.preview_operator import projection;print(json.dumps(projection(json.load(sys.stdin))))'
            value=json.loads(op.k('exec','-i',a.agent+'-0','--',PYTHON,'-c',script,data=json.dumps(body)))
        else:value=json.loads(op.k('exec',a.agent+'-0','--',PYTHON,'-m','integration.single_node.preview_operator',*args,timeout=45))
    print(json.dumps(value,indent=2))

if __name__=='__main__':main()
