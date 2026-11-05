"""CLI equivalents for the narrow scoped Workbench methods (no Kubernetes).

Trusted operator supplies the provisioned configuration and username. The JSON
body is passed as data through the same validators as the browser; no endpoint,
credential, Python/MeTTa expression or executable is accepted in that body.
"""
import argparse,json,sys
from fusion.contracts import canonical,require
from fusion.preview_client import strict_json
from .pilot_workbench import ScopedWorkbench


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--configuration',required=True);p.add_argument('--user',required=True)
    p.add_argument('operation',choices=('state','observe','current','capabilities','action','subscription','registry-maintenance','maintenance','explore','handover','workflow'))
    args=p.parse_args();owner=ScopedWorkbench(args.configuration)
    with owner.as_user(args.user):
        if args.operation=='state':value=owner.state()
        else:
            body=strict_json(sys.stdin.buffer.read(65537));require(len(canonical(body))<=65536)
            method={'registry-maintenance':'registry_maintenance'}.get(args.operation,args.operation)
            value=getattr(owner,method)(body)
    print(json.dumps(value,sort_keys=True))


if __name__=='__main__':main()
