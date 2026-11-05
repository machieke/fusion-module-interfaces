"""Read-only socket/pool authorization qualification on a task-owned gateway.

The old Secret JSON is private input; credentials are never printed or copied to
the report. No policy change, work submission, retry or generation is performed.
Run using the installed operator Python -I, with the reviewed script as artifact.
"""
import argparse,base64,hashlib,json
from pathlib import Path
from integration.single_node.reference_ops import Operator,PYTHON

CODE=r'''
import http.client,json,ssl,sys,uuid
from pathlib import Path
from fusion import https_pool
from fusion.contracts import ContractError,canonical,require
from fusion.preview_transport import invoke
q=json.load(sys.stdin);cfg=json.loads(Path('/config/browser.json').read_bytes())
t=cfg['users']['shared']['targets']['omega-agent'];ep=t['endpoint']
current=Path(t['credential_file']).read_text().strip();require(current!=q['former'],'CONFLICT')
body=dict(profile='omega-native-sessions/3',id=str(uuid.uuid4()),operation='binding',body={'session':q['session']})
ctx=ssl.create_default_context(cafile=ep['ca_file'])
c=http.client.HTTPSConnection(ep['host'],ep['port'],timeout=5,context=ctx)
def read(token):
 c.request('POST','/preview/session',canonical(body),{'Authorization':'Bearer '+token,'Content-Type':'application/json'})
 r=c.getresponse();require(r.status==200 and r.fp is not None,'NOT_AVAILABLE');wire=r.fp.raw._sock;identity=(wire.fileno(),wire.getsockname(),wire.getpeername());v=json.loads(r.read(131073));return v,wire,identity
try:
 v,sock,identity=read(current);require('error' not in v and c.sock is sock,'UNAUTHORIZED')
 denied,wire,second_identity=read(q['former']);same=wire is sock and identity==second_identity
 require(same and denied['error']['code']=='UNAUTHORIZED','CONFLICT')
 direct=dict(success_then_former_token='UNAUTHORIZED',same_socket_object=same,connection_requests=2,socket_identity=identity,denial_closes_connection=c.sock is None)
finally:c.close()
https_pool.configure(dict(https_pool.LIMITS,idle_ms=1000));selected=dict(endpoint=ep,credential=current)
try:
 invoke(selected,'/preview/session',body)
 require(len(https_pool._entries)==1,'CONFLICT');row=https_pool._entries[0];sock=row['connection'].sock
 invoke(selected,'/preview/session',body)
 require(len(https_pool._entries)==1 and https_pool._entries[0] is row and row['connection'].sock is sock and row['count']==2,'CONFLICT')
 pooled=dict(current_token_requests=2,same_pool_entry=True,same_socket_object=True,socket_identity=(sock.fileno(),sock.getsockname(),sock.getpeername()))
 try:invoke(dict(endpoint=ep,credential=q['former']),'/preview/session',body)
 except ContractError as e:require(e.code=='UNAUTHORIZED','CONFLICT');pooled['former_token']=e.code
 else:require(False,'CONFLICT')
 require(row not in https_pool._entries and row['connection'].sock is None,'CONFLICT')
 pooled['credential_epoch_old_entry_closed']=True
finally:https_pool.close();https_pool.configure(None)
print(json.dumps(dict(status='PASS',direct_socket=direct,pool=pooled,physical_requests=5,submissions=0,policy_mutations=0,additional_live_generations=0,limitation='No claim that a pre-revocation formerly authorized pool entry remained connected; old credential is selected only after its prior rotation.')))
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','namespace','former-secret','story-report','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--context',default='default');a=p.parse_args();out=Path(a.output)
    if out.exists():raise RuntimeError('Report exists; do not rerun implicitly')
    o=Operator(a.kubeconfig,a.context,a.namespace);o.stateless_workloads()
    old=json.loads(Path(a.former_secret).read_bytes());story=json.loads(Path(a.story_report).read_bytes())
    q=dict(former=base64.b64decode(old['data']['browser-shared-token']).decode(),session=story['sessions']['shared']['session'])
    report=dict(status='OBSERVING',source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),additional_live_generations=0)
    try:
        raw=o.k('exec','-i','deployment/omega-workbench','--',PYTHON,'-c',CODE,data=json.dumps(q),timeout=35)
        report.update(json.loads(raw))
    except BaseException as e:
        report.update(status='FAILED_RETAINED',failure=type(e).__name__)
        raise
    finally:
        out.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');out.chmod(0o600)
    print('Read-only actual socket and selected HTTPS pool qualification '+report['status'])

if __name__=='__main__':main()
