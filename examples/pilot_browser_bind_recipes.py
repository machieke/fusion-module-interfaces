"""Bind static operator qualification recipes offline; never execute them.

The packet's reviewed recipe templates contain no credentials or corpus. The
private parameter file selects task paths and namespace before qualification.
This writes a fresh directory and a source manifest, with no network/process API.
"""
import argparse,hashlib,json,os,re
from pathlib import Path

NAMES=('workflow_browser_case.py','browser_cleanup_case.py','rotate_owner_credentials.py',
       'rotate_browser_policy.py','verify_owner_rotation.py','archive_browser_history.py',
       'policy_projection_barrier.py','user-client/ui.py','user-client/reconnect_probe.py')
KEYS={'PRIVATE_ROOT','KUBECONFIG','NAMESPACE','PACKET','PROOFSHOT','NODE_BIN',
      'BROWSER_EXECUTABLE','BROWSER_SOCKET_DIR','BROWSER_SESSION','IDENTITY','KUBECTL'}

def bind(templates,parameters,output):
    source=Path(templates);out=Path(output)
    if type(parameters) is not dict or set(parameters)!=KEYS:raise ValueError('EXACT_PARAMETERS_REQUIRED')
    for key,value in parameters.items():
        if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_./-]{1,512}',value):raise ValueError('UNSAFE_PARAMETER')
        if key not in ('NAMESPACE','BROWSER_SESSION','IDENTITY') and not value.startswith('/'):raise ValueError('ABSOLUTE_PATH_REQUIRED')
    if not re.fullmatch(r'omega-ref-pilot-[a-z0-9-]{1,40}',parameters['NAMESPACE']):raise ValueError('TASK_NAMESPACE_REQUIRED')
    if out.exists():raise ValueError('FRESH_OUTPUT_REQUIRED')
    manifest=json.loads((source/'manifest.json').read_bytes());rows=manifest['files']
    if {x['path'] for x in rows}!=set(NAMES) or len(rows)!=len(NAMES):raise ValueError('EXACT_RECIPE_SET_REQUIRED')
    staged={}
    for row in rows:
        path=source/(row['path']+'.in');raw=path.read_bytes()
        if len(raw)>65536 or hashlib.sha256(raw).hexdigest()!=row['template_sha256']:raise ValueError('TEMPLATE_MISMATCH')
        text=raw.decode()
        for key,value in parameters.items():text=text.replace('@@'+key+'@@',value)
        if '@@' in text:raise ValueError('UNBOUND_TEMPLATE')
        compile(text,row['path'],'exec');staged[row['path']]=text.encode()
    os.umask(0o077);out.mkdir(parents=True,exist_ok=False)
    for name,raw in staged.items():
        target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    report=dict(classification='OFFLINE_RECIPE_BINDING_ONLY',cluster_calls=0,process_calls=0,
        additional_live_generations=0,files={name:hashlib.sha256(raw).hexdigest() for name,raw in staged.items()})
    (out/'bound-recipes.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--templates',required=True);p.add_argument('--parameters',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    if Path(a.parameters).stat().st_size>8192:raise ValueError('PARAMETERS_TOO_LARGE')
    bind(a.templates,json.loads(Path(a.parameters).read_bytes()),a.output);print('Static recipes bound; nothing executed.')

if __name__=='__main__':main()
