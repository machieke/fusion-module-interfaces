"""Opt-in real cluster tests. Fresh namespaces, real native/DeTTa/HTTPS only.

The existing external model, channel and unused memory fixtures are explicit.
No model runtime is contacted. Observations read each owner's own PVC via exec.
"""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2]
ROLES=('omega-agent','fusion-execution','fusion-storage','fusion-messaging')
PYTHON='/opt/native/python/bin/python3.12'
GOLDEN='(stv 0.5599999999999999 0.4032)'


class Cluster:
    def __init__(self,args,name):
        self.args=args;self.name=args.prefix+'-'+name;self.case=name
        self.root=Path(args.output)/name;self.root.mkdir(parents=True,exist_ok=False)
        self.values=dict(image=dict(tag=args.image_tag),testFaultsEnabled=True,components={})
        self.report=dict(case=name,namespace=self.name,status='RUNNING',started=datetime.now(timezone.utc).isoformat(),
            placements='four distinct pods; one k3s node; ClusterIP DNS; authenticated HTTPS',
            real=['native Omega loop/parser/skill','pinned NAL deduction','DeTTa','TLS/TCP','k3s/Helm/PVCs'],
            fixtures=['external model responses','unused IRC ingress','unused memory enrichment'],observations={},actions=[])

    def command(self,args,**kw):
        result=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=kw.pop('timeout',60),**kw)
        if result.returncode:raise RuntimeError(str(args[:3])+' '+result.stderr[-2000:])
        return result.stdout

    def k(self,*args,**kw):return self.command(['kubectl','--kubeconfig',self.args.kubeconfig,'-n',self.name,*args],**kw)
    def exec(self,role,code):return self.k('exec',role+'-0','--',PYTHON,'-c',code)
    def observe(self,role):return json.loads(self.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.observe'))
    def config(self,role,**cfg):self.values['components'].setdefault(role,dict(config={} ))['config'].update(cfg)

    def upgrade(self):
        file=self.root/'values.json';file.write_text(json.dumps(self.values))
        log=self.command(['helm','upgrade','--install','omega',str(ROOT/'deploy/helm/omega-fusion'),
            '--kubeconfig',self.args.kubeconfig,'--namespace',self.name,'-f',str(file.resolve())])
        with (self.root/'helm.log').open('a') as f:f.write(log)

    def install(self,wrong=False):
        self.k('create','namespace',self.name)
        self.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),'--kubeconfig',self.args.kubeconfig,
            '--namespace',self.name,'--directory',str((self.root/'private-secrets').resolve())])
        if wrong:
            patch=dict(data={'fusion-execution-token':base64.b64encode(b'wrong-credential-'*4).decode()})
            self.k('patch','secret','omega-agent-tls-auth','--type=merge','--patch',json.dumps(patch))
        self.upgrade()

    def wait(self,fn,seconds=55):
        until=time.monotonic()+seconds;last=None
        while time.monotonic()<until:
            try:
                value=fn()
                if value:return value
            except (RuntimeError,json.JSONDecodeError) as exc:last=str(exc)
            time.sleep(.15)
        raise AssertionError('bounded observer expired: '+str(last))

    def file(self,role,name):
        return json.loads(self.exec(role,f'import json;from pathlib import Path;p=Path("/state/{name}");print(p.read_text() if p.exists() else "null")'))
    def pause(self,role):return self.wait(lambda:self.file(role,'pause.json'))
    def terminal(self):return self.wait(lambda:self.file('omega-agent','native-status.json'),45)
    def uid(self,role):return self.k('get','pod',role+'-0','-o','jsonpath={.metadata.uid}')

    def replace(self,role):
        before=self.uid(role);self.k('delete','pod',role+'-0','--grace-period=1','--wait=false')
        after=self.wait(lambda:(v if (v:=self.uid(role))!=before else None),20)
        self.report['actions'].append(dict(action='pod-replacement',role=role,old_uid=before,new_uid=after))

    def snapshot(self,key):
        data={role:self.observe(role) for role in ROLES}
        self.report['observations'][key]=data;return data

    def success(self,data):
        a,e,s,m=[data[r] for r in ROLES]
        assert a['native-status.json']['status']=='BOUNDED_STOP'
        assert len(a['app_occurrences'])==len(a['caller_requests'])==len(e['jobs'])==len(e['s01_work'])==len(s['atoms'])==len(m['messages'])==1
        assert a['app_occurrences'][0]['done']==a['caller_requests'][0]['acknowledged']==m['messages'][0]['acknowledged']==1
        assert e['jobs'][0]['state']=='succeeded' and e['s01_work'][0]['attempts']==1
        assert len(e['outbox'])==1 and e['outbox'][0]['sent']==1
        assert len(a['model_contexts'])==2 and a['model_contexts'][1]['feedback'].count(GOLDEN)==1
        assert a['app_occurrences'][0]['result']==GOLDEN
        request=json.loads(a['caller_requests'][0]['request'])
        assert request==json.loads(e['jobs'][0]['request'])
        assert request['deadline_ms']==a['app_occurrences'][0]['deadline']
        assert a['caller_requests'][0]['calls']<=a['caller_requests'][0]['max_calls']==64
        assert request['body']['max_attempts']==3
        assert json.loads(s['atoms'][0]['receipt'])['provider']=='detta-local-rs/1'

    def same_identity(self,before,after):
        b=before['omega-agent']['caller_requests'][0];a=after['omega-agent']['caller_requests'][0]
        assert b['id']==a['id'] and b['request']==a['request'] and a['calls']>=b['calls']
        assert b['max_calls']==a['max_calls']

    def run(self):
        case=self.case
        if case=='caller-replacement':self.config('omega-agent',test=dict(pause_at='after_caller_receipt'))
        if case in ('provider-replacement','storage-outage'):
            self.config('omega-agent',test=dict(pause_at='after_submit_reply'))
            self.config('fusion-execution',workerEnabled=False,test=dict(pause_at='after_output_commit'))
        if case.startswith('lost-'):
            role,op={'lost-submit':('fusion-execution','submit'),'lost-storage':('fusion-storage','/ports/atom-create'),
                     'lost-completion':('fusion-messaging','/ports/completion')}[case]
            self.config(role,test=dict(drop_response_operation=op))
        if case=='service-outage':self.config('omega-agent',test=dict(pause_at='after_submit_reply'))
        if case=='health':self.config('omega-agent',nativeEnabled=False)
        self.install(wrong=case=='wrong-credential')
        if case=='health':
            for role in ROLES:self.wait(lambda:self.file(role,'process.json'))
            before=self.snapshot('before-health')
            response=self.exec('omega-agent','''import http.client,ssl,json
ctx=ssl.create_default_context(cafile='/secrets/ca.crt'); result=[]
cfg=json.load(open('/config/component.json'))
for name in ['omega-agent',*cfg['peers']]:
 host=(name+'.'+cfg['peers']['fusion-storage'].split('.',1)[1])
 for path in ['/health/startup','/health/ready','/health/live']:
  c=http.client.HTTPSConnection(host,8443,context=ctx,timeout=2);c.request('GET',path);r=c.getresponse();r.read();result.append([name,path,r.status]);c.close()
print(json.dumps(result))''')
            self.report['health_responses']=json.loads(response)
            assert all(r[2]==200 for r in self.report['health_responses'])
            assert before==self.snapshot('after-health')
            assert 'caller_requests' not in before['omega-agent'] and before['fusion-execution']['jobs']==[]
            duplicate=subprocess.run(['kubectl','--kubeconfig',self.args.kubeconfig,'-n',self.name,'exec','fusion-messaging-0','--',
                PYTHON,'-m','integration.single_node.server'],capture_output=True,text=True,timeout=5)
            assert duplicate.returncode!=0 and 'OWNER_ALREADY_RUNNING' in duplicate.stderr
            self.report['single_writer_guard']=dict(returncode=duplicate.returncode,error='OWNER_ALREADY_RUNNING')
        elif case in ('caller-replacement','provider-replacement','storage-outage'):
            self.pause('omega-agent')
            if case in ('provider-replacement','storage-outage'):
                self.config('fusion-execution',workerEnabled=True);self.upgrade()
                self.pause('fusion-execution')
            before=self.snapshot('before-replacement')
            if case in ('provider-replacement','storage-outage'):
                assert before['fusion-execution']['jobs'][0]['state']=='queued'
                assert before['fusion-execution']['s01_work'][0]['output'] is not None
            if case=='storage-outage':
                self.k('patch','service','fusion-storage','--type=merge','--patch',json.dumps(dict(spec=dict(selector={'app.kubernetes.io/name':'unavailable'}))))
                self.wait(lambda:all(not v.get('endpoints') for v in json.loads(self.k('get','endpointslices',
                    '-l','kubernetes.io/service-name=fusion-storage','-o','json'))['items']),10)
                self.replace('fusion-execution')
                pending=self.wait(lambda:(v if (v:=self.observe('fusion-execution')).get('jobs') else None),15)
                assert pending['jobs'][0]['state']=='queued' and pending['s01_work'][0]['output'] is not None
                self.report['observations']['storage-unavailable']=pending
                self.k('patch','service','fusion-storage','--type=merge','--patch',json.dumps(dict(spec=dict(selector={'app.kubernetes.io/name':'fusion-storage'}))))
                self.wait(lambda:self.observe('fusion-execution')['jobs'][0]['state']=='succeeded',15)
            elif case=='provider-replacement':
                self.replace('fusion-execution')
                self.wait(lambda:self.observe('fusion-execution')['jobs'][0]['state']=='succeeded',15)
            self.replace('omega-agent');self.terminal();after=self.snapshot('after-replacement')
            self.success(after);self.same_identity(before,after)
            assert before['fusion-execution']['s01_work'][0]['attempts']==after['fusion-execution']['s01_work'][0]['attempts']==1
        elif case=='service-outage':
            self.pause('omega-agent');before=self.snapshot('before-outage')
            # An unavailable listening port returns connection refusal quickly,
            # exercising the full existing 64-call ceiling before its deadline.
            # The caller's accepted endpoint/identity/limits stay untouched.
            self.k('patch','service','fusion-execution','--type=merge','--patch',json.dumps(dict(spec=dict(
                ports=[dict(name='https',port=8443,targetPort=8444,protocol='TCP')]))))
            self.wait(lambda:all(v['ports'][0]['port']==8444 for v in json.loads(self.k('get','endpointslices',
                '-l','kubernetes.io/service-name=fusion-execution','-o','json'))['items']),10)
            self.exec('omega-agent','import os,signal,json;os.kill(json.load(open("/state/process.json"))["native_pid"],signal.SIGCONT)')
            terminal=self.terminal();assert terminal['status']=='PENDING_OR_FAILED'
            failed=self.observe('omega-agent');self.report['observations']['outage-terminal']=failed
            assert failed['caller_requests'][0]['receipt'] is None and failed['caller_requests'][0]['calls']==64
            self.k('patch','service','fusion-execution','--type=merge','--patch',json.dumps(dict(spec=dict(
                ports=[dict(name='https',port=8443,targetPort='https',protocol='TCP')]))))
            self.replace('omega-agent')
            self.wait(lambda:self.file('omega-agent','process.json')['configuration_revision']=='initial')
            # Observe the restarted native process exit; stale status files alone
            # are not proof of the new process having consumed retained state.
            self.wait(lambda: self.exec('omega-agent','import json;from pathlib import Path;p=json.load(open("/state/process.json"))["native_pid"];print(not Path(f"/proc/{p}").exists())').strip()=='True',10)
            after=self.snapshot('after-outage');self.same_identity(before,after)
            assert after['omega-agent']['caller_requests'][0]['calls']==failed['caller_requests'][0]['calls']
            assert len(after['fusion-execution']['jobs'])==1 and after['fusion-execution']['s01_work'][0]['attempts']==1
            assert after['omega-agent']['caller_requests'][0]['receipt'] is None
        elif case=='wrong-credential':
            assert self.terminal()['status']=='PENDING_OR_FAILED'
            data=self.snapshot('rejected');a=data['omega-agent']
            assert a['native-status.json']['code']=='UNAUTHORIZED'
            assert a['caller_requests'][0]['calls']==1 and a['caller_requests'][0]['receipt'] is None
            assert data['fusion-execution']['jobs']==[] and data['fusion-storage']['atoms']==[]
        else:
            self.terminal();before=self.snapshot('completed');self.success(before)
            if case.startswith('lost-'):assert before[role]['response-dropped.json']['operation']==op
            if case=='config-restart':
                old={r:self.uid(r) for r in ROLES}
                for r in ROLES:self.config(r,revision='config-restart-1')
                self.upgrade()
                for r in ROLES:
                    self.wait(lambda:self.uid(r)!=old[r],45)
                    self.wait(lambda:self.file(r,'process.json')['configuration_revision']=='config-restart-1',30)
                after=self.snapshot('after-configuration-rollout');self.success(after)
                self.same_identity(before,after)
                for r in ROLES:
                    self.report['actions'].append(dict(action='config-checksum-rollout',role=r,old_uid=old[r],new_uid=self.uid(r)))
                    assert after[r]['shutdown.json']['graceful'] is True
                assert before['omega-agent']['caller_requests']==after['omega-agent']['caller_requests']
        self.report['pods']=json.loads(self.k('get','pods','-o','json'))
        self.report['pvcs']=json.loads(self.k('get','pvc','-o','json'))
        assert len(self.report['pvcs']['items'])==4
        self.report['status']='PASS'

    def finish(self):
        self.report['finished']=datetime.now(timezone.utc).isoformat()
        # Exclude K8s verbose managed fields. Pod specs contain Secret references,
        # never Secret contents. Raw private TLS material stays under artifacts.
        for kind in ('pods','pvcs'):
            for item in self.report.get(kind,{}).get('items',[]):item.get('metadata',{}).pop('managedFields',None)
        (self.root/'report.json').write_text(json.dumps(self.report,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--prefix',required=True)
    p.add_argument('--output',required=True);p.add_argument('--image-tag',required=True)
    p.add_argument('cases',nargs='+',choices=['baseline','health','lost-submit','lost-storage','lost-completion',
        'caller-replacement','provider-replacement','storage-outage','service-outage','wrong-credential','config-restart']);args=p.parse_args()
    failed=False
    for name in args.cases:
        test=Cluster(args,name)
        try:test.run()
        except Exception as exc:
            failed=True;test.report.update(status='FAIL',failure=str(exc),traceback=traceback.format_exc())
            try:test.snapshot('failure')
            except Exception:pass
        finally:test.finish()
        print(name+': '+test.report['status']+' '+test.report.get('failure',''),flush=True)
    raise SystemExit(1 if failed else 0)


if __name__=='__main__':main()
