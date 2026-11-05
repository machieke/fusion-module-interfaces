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
    p.add_argument('action',choices=('preflight','install','upgrade','inventory','allocate','submit','observe','pause','resume','close','archive','cancel','reconcile','capacity','current','list','project','chain-observe','backup','restore','stop','qualify','providers','continuation','search-maintenance','derived-maintenance','capabilities','worker-control','chain-continuation'))
    p.add_argument('--chart');p.add_argument('--values');p.add_argument('--directory');p.add_argument('--fenced',action='store_true')
    p.add_argument('--session');p.add_argument('--identity');p.add_argument('--text');p.add_argument('--assignment',default='synthetic-task');p.add_argument('--template');p.add_argument('--target');p.add_argument('--content',action='store_true');p.add_argument('--request-file')
    p.add_argument('--provider');p.add_argument('--provider-action',choices=('inspect','selected','probe','add','enable','disable','drain','retire','plan','seal','headroom'));p.add_argument('--retained',choices=('required','explicit-unavailable'))
    p.add_argument('--head');p.add_argument('--occurrence');p.add_argument('--continuation-action',choices=('observe','cancel','unsubscribe'))
    p.add_argument('--worker-action',choices=('observe','drain','recycle','resume'))
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
        for name in ('session','identity','text','template','target','provider','provider_action','retained','occurrence','continuation_action','worker_action','head'):
            if getattr(a,name) is not None:args+=['--'+name.replace('_','-'),getattr(a,name)]
        if a.action=='submit':args+=['--assignment',a.assignment]
        if a.content:args+=['--content']
        if a.action in ('project','search-maintenance','derived-maintenance','chain-continuation') or (a.action=='capabilities' and a.request_file):
            # No request file or approval is installed as a provider default.
            require(a.request_file is not None)
            raw=Path(a.request_file).read_bytes();require(len(raw)<=(131072 if a.action=='search-maintenance' else 65536 if a.action=='derived-maintenance' else 16384))
            from fusion.preview_client import strict_json
            body=strict_json(raw)
            if a.action=='project':
                script='import json,sys;from integration.single_node.preview_operator import projection;print(json.dumps(projection(json.load(sys.stdin))))';pod=a.agent+'-0'
            elif a.action=='chain-continuation':
                script='import json,sys;from integration.single_node.preview_operator import chain_continuation;print(json.dumps(chain_continuation(json.load(sys.stdin))))';pod=a.agent+'-0'
            elif a.action=='derived-maintenance':
                script='import json,sys;from integration.single_node.pilot_derived_maintenance import request;print(json.dumps(request(json.load(sys.stdin))))';pod=a.agent+'-0'
            elif a.action=='search-maintenance':
                script='import json,sys;from integration.single_node.integrated_search_operator import request;print(json.dumps(request(json.load(sys.stdin))))';pod='fusion-search-0'
            else:
                require(a.session is not None)
                script='import json,sys;from integration.single_node.preview_operator import capabilities;print(json.dumps(capabilities(sys.argv[1],json.load(sys.stdin))))';pod=a.agent+'-0'
            argv=[a.session] if a.action=='capabilities' else []
            value=json.loads(op.k('exec','-i',pod,'--',PYTHON,'-c',script,*argv,data=json.dumps(body),timeout=130))
        else:value=json.loads(op.k('exec',a.agent+'-0','--',PYTHON,'-m','integration.single_node.preview_operator',*args,timeout=45))
    print(json.dumps(value,indent=2))

if __name__=='__main__':main()
