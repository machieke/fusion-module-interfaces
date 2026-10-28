"""Opt-in real memory deployment checks. Explicit external response fixtures only."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
from .test_cluster import Cluster,ROOT,PYTHON

ROLES=('omega-agent','fusion-storage','fusion-search','fusion-embedding')


class MemoryCluster(Cluster):
    def __init__(self,args,name):
        super().__init__(args,name)
        import yaml
        self.values=yaml.safe_load(Path(args.values).read_text());self.values['testFaultsEnabled']=True
        self.report.update(placements='separate agent/storage/search/embedding pods; same-node authenticated HTTPS',
            real=['native remember/query/parser/loop','E5 CPU','Chroma 1.5.5','DeTTa','HTTPS/DNS','k3s/Helm/PVCs'],
            fixtures=['model commands','empty channel input','unused global context/history','declared creation/enrichment clocks'])
    def config(self,role,**cfg):
        self.values['components'].setdefault(role,{}).setdefault('config',{}).update(cfg)
    def observe(self,role):
        # Execute observer bytes as an operator in THIS owner's pod. No file
        # crosses into another service; the application never calls this audit.
        return json.loads(self.exec(role,self.args.observer_source))
    def snapshot(self,key):
        data={role:self.observe(role) for role in ROLES};self.report['observations'][key]=data;return data
    def upgrade(self):
        file=self.root/'values.json';file.write_text(json.dumps(self.values))
        log=self.command(['helm','upgrade','--install','omega',str(self.args.chart),
            '--kubeconfig',self.args.kubeconfig,'--namespace',self.name,'-f',str(file.resolve())])
        with (self.root/'helm.log').open('a') as f:f.write(log)
    def install(self,wrong=False):
        self.k('create','namespace',self.name)
        self.command([sys.executable,str(ROOT/'deploy/single-node/create_secrets.py'),'--memory','--kubeconfig',self.args.kubeconfig,
            '--namespace',self.name,'--directory',str((self.root/'private-secrets').resolve())])
        if wrong:
            import base64
            self.k('patch','secret','omega-agent-tls-auth','--type=merge','--patch',json.dumps(dict(data={'fusion-storage-token':base64.b64encode(b'wrong-credential-'*4).decode()})))
        self.upgrade()
    def success(self,data):
        a,s,q,e=[data[r] for r in ROLES]
        assert a['native-status.json']['status']=='BOUNDED_STOP',a.get('native-status.json')
        writes=a['app_memory_writes'];reads=a['app_memory_reads'];occs=a['app_occurrences']
        assert len(writes)==3 and len(reads)==3 and len(occs)==6
        assert len({w['uuid'] for w in writes})==3 and all(w['linked']==1 and w['view'] for w in writes)
        assert all(o['done']==1 for o in occs)
        assert all(json.loads(w['intent'])['deadline_ms']==next(o['deadline'] for o in occs if o['id']==w['id']) for w in writes)
        assert [json.loads(r['request'])['snapshot']['head']['sequence'] for r in reads]==[4,8,12]
        assert [json.loads(w['through_head'])['sequence'] for w in writes]==[4,8,12]
        assert len(s['feed_atoms'])==12 and len(e['encode_attempts'])==6 and all(r['finished']==1 for r in e['encode_attempts'])
        assert len(q['publications']['generations'])==4
        assert len(a['model_contexts'])==7
        target=self.values['memory']['responses'][2].removeprefix('remember ')
        assert target not in a['model_contexts'][2]['feedback']
        assert target in a['model_contexts'][4]['feedback'] and target in a['model_contexts'][6]['feedback']
        assert all(a['native/embedding-boundary.json']['absent'].values())
        assert all(v=='inaccessible' for v in a['native/embedding-boundary.json']['denied_file_probes'].values())
        assert 'feed.sqlite' not in str(q['root_files']) and 'payloads' not in str(q['root_files'])
    def ended(self,seconds=60):
        from datetime import datetime
        created=self.k('get','pod','omega-agent-0','-o','jsonpath={.metadata.creationTimestamp}')
        minimum=datetime.fromisoformat(created.replace('Z','+00:00')).timestamp()
        def check():
            code="""import json
from pathlib import Path
p=Path('/state/process.json');e=Path('/state/native-exit.json');s=Path('/state/native-status.json')
ready=(p.exists() and e.exists() and s.exists() and p.stat().st_mtime>=MINIMUM and e.stat().st_mtime>=p.stat().st_mtime)
print(s.read_text() if ready and json.loads(p.read_text())['native_pid']==json.loads(e.read_text())['pid'] else 'null')
""".replace('MINIMUM',repr(minimum))
            return json.loads(self.exec('omega-agent',code))
        return self.wait(check,seconds)
    def same(self,before,after):
        for b in before['omega-agent'].get('app_occurrences',[]):
            a=next(x for x in after['omega-agent']['app_occurrences'] if x['id']==b['id'])
            assert (a['deadline'],a['premises'])==(b['deadline'],b['premises'])
            if b['result'] is not None:assert a['result']==b['result']
        for table in ('app_memory_vectors','app_query_vectors','app_memory_writes','app_memory_reads'):
            for b in before['omega-agent'].get(table,[]):
                a=next(x for x in after['omega-agent'][table] if x['id']==b['id'])
                for counter in ('calls','attempts','builds','queries'):
                    if counter in b:assert a[counter]>=b[counter]
                for stable in ('uuid','sampled_time','snapshot','intent','result','request','candidates','payloads','view'):
                    if b.get(stable) is not None:assert a[stable]==b[stable],(table,stable)
    def run(self):
        case=self.case
        caller_pauses={'caller-vector':'after_memory_vector_capture','caller-publication':'after_append_publication',
                       'caller-result':'after_native_result_capture','encoder-capture':'after_native_result_capture',
                       'enrollment':'after_append_enrollment','expired-enrollment':'after_append_enrollment','revocation':'after_payload_validation','budget-outage':'after_append_enrollment','storage-outage':'after_memory_vector_capture',
                       'search-outage':'after_append_enrollment'}
        search_pauses={'search-before-publication':'before_checkpoint','search-after-publication':'after_publication'}
        if case=='storage-acceptance':self.config('fusion-storage',test=dict(pause_at='after_append_enrollment_acceptance'))
        if case in caller_pauses:self.config('omega-agent',test=dict(pause_at=caller_pauses[case]))
        if case in search_pauses:self.config('fusion-search',test=dict(pause_at=search_pauses[case]))
        if case=='lost-storage':self.config('fusion-storage',test=dict(drop_response_operation='create'))
        if case=='lost-publication':self.config('fusion-search',test=dict(drop_response_operation='build'))
        self.install(wrong=case=='wrong-credential')
        for role in ROLES:self.wait(lambda:self.file(role,'process.json'),150)
        if case in caller_pauses or case in search_pauses or case=='storage-acceptance':
            paused='fusion-storage' if case=='storage-acceptance' else 'fusion-search' if case in search_pauses else 'omega-agent';self.pause(paused)
            before=self.snapshot('at-boundary')
            if case=='expired-enrollment':
                deadline=before['omega-agent']['app_occurrences'][0]['deadline']
                while time.time()*1000<=deadline+50:time.sleep(.2)
            if case=='revocation':
                cm=json.loads(self.k('get','configmap','fusion-search','-o','json'))
                component=json.loads(cm['data']['component.json']);component['memory']['queries']=['Different approved synthetic query']
                self.k('patch','configmap','fusion-search','--type=merge','--patch',json.dumps(dict(data={'component.json':json.dumps(component)})))
                self.replace('fusion-search');self.wait(lambda:self.file('fusion-search','process.json'),30)
                self.replace('omega-agent');assert self.ended()['code']=='UNAUTHORIZED'
                after=self.snapshot('revoked');self.same(before,after)
                assert before['fusion-embedding']['encode_attempts']==after['fusion-embedding']['encode_attempts']
                assert len(after['omega-agent']['model_contexts'])==2
                self.report['status']='PASS';return
            if case in ('storage-outage','search-outage','budget-outage'):
                target='fusion-storage' if case in ('storage-outage','budget-outage') else 'fusion-search'
                patch=dict(spec=dict(ports=[dict(name='https',port=8443,targetPort=8444,protocol='TCP')]))
                self.k('patch','service',target,'--type=merge','--patch',json.dumps(patch))
                self.wait(lambda:all(v['ports'][0]['port']==8444 for v in json.loads(self.k('get','endpointslices','-l','kubernetes.io/service-name='+target,'-o','json'))['items']),10)
                if case=='budget-outage':
                    self.exec('omega-agent','import os,signal,json;os.kill(json.load(open("/state/process.json"))["native_pid"],signal.SIGKILL)')
                    code="""from fusion.neoclaw_application import Application
from fusion.contracts import ContractError
import json
app=Application('/run/fusion/application.json')
row=app.db.execute('SELECT * FROM app_occurrences ORDER BY turn,position LIMIT 1').fetchone()
app.current=(row['turn'],row['position'])
errors={}
for _ in range(100):
 try:app.write.call(row,'atom.storage','authorize',{'mode':'disclose'})
 except ContractError as e:
  errors[e.code]=errors.get(e.code,0)+1
  if e.code=='OVERLOADED':break
state=app.write.state(row);print(json.dumps(dict(calls=state['calls'],errors=errors)));app.close()
"""
                    exhaustion=json.loads(self.exec('omega-agent',code));assert exhaustion['calls']==96
                    self.report['budget_probe']=exhaustion
                    failed=self.snapshot('exhausted')
                    patch['spec']['ports'][0]['targetPort']='https';self.k('patch','service',target,'--type=merge','--patch',json.dumps(patch))
                    self.replace('omega-agent');assert self.ended()['code']=='OVERLOADED'
                    after=self.snapshot('after-restoration');self.same(before,after)
                    assert after['omega-agent']['app_memory_writes'][0]['calls']==96
                    assert before['fusion-storage']['feed_atoms']==after['fusion-storage']['feed_atoms']
                    self.report['status']='PASS';return
                # Release the existing process after the dependency is unavailable.
                self.exec('omega-agent','import os,signal,json;os.kill(json.load(open("/state/process.json"))["native_pid"],signal.SIGCONT)')
                assert self.ended()['status']=='PENDING_OR_FAILED'
                failed=self.snapshot('unavailable');self.same(before,failed)
                assert failed['omega-agent']['app_occurrences'][0]['done']==0
                patch['spec']['ports'][0]['targetPort']='https';self.k('patch','service',target,'--type=merge','--patch',json.dumps(patch))
                self.replace('omega-agent')
            else:
                if case=='encoder-capture':
                    self.replace('fusion-embedding');self.wait(lambda:self.file('fusion-embedding','process.json'),60)
                if case in search_pauses or case in ('enrollment','expired-enrollment'):self.replace('fusion-search')
                if case=='storage-acceptance':self.replace('fusion-storage');self.ended()
                if case not in search_pauses:self.replace('omega-agent')
                else:
                    # Failed synchronous requests are not automatically retried by
                    # the application. Reopen its same pending occurrence.
                    status=self.ended()
                    if status['status']!='BOUNDED_STOP':self.replace('omega-agent')
            terminal=self.ended();after=self.snapshot('recovered');self.same(before,after)
            if case=='expired-enrollment':
                assert terminal['code']=='DEADLINE_EXCEEDED' and terminal['append']['native_success'] is False
                assert len(after['fusion-storage']['feed_atoms'])==4 and len(after['fusion-search']['publications']['generations'])==1
                assert before['fusion-embedding']['encode_attempts']==after['fusion-embedding']['encode_attempts']
                self.replace('omega-agent');assert self.ended()['code']=='DEADLINE_EXCEEDED'
                again=self.snapshot('expired-reopened');self.same(after,again)
                assert after['fusion-storage']['feed_atoms']==again['fusion-storage']['feed_atoms']
                self.report.update(status='PASS',workflow='NOT_COMPLETED_ORIGINAL_DEADLINE',safety='retained acceptance; no new publication, encoder call or native success')
                return
            self.success(after)
            if case=='encoder-capture':
                assert before['fusion-embedding']['encode_attempts'][0]==after['fusion-embedding']['encode_attempts'][0]
        elif case=='wrong-credential':
            assert self.ended()['code']=='UNAUTHORIZED';data=self.snapshot('rejected')
            assert data['fusion-storage']['feed_atoms']==[] and not data['fusion-embedding'].get('encode_attempts')
        elif case.startswith('lost-'):
            assert self.ended()['status']=='PENDING_OR_FAILED';before=self.snapshot('lost-response')
            self.replace('omega-agent');self.ended();after=self.snapshot('recovered');self.same(before,after);self.success(after)
        else:
            self.ended();before=self.snapshot('completed');self.success(before)
            if case=='health':
                code='''import http.client,ssl,json
cfg=json.load(open('/config/component.json'));suffix=cfg['peers']['fusion-storage'].split('.',1)[1]
results=[]
for role in ['omega-agent',*cfg['peers']]:
 for path in ['/health/startup','/health/ready','/health/live']:
  host=role+'.'+suffix
  client=http.client.HTTPConnection(host,8443,timeout=3) if role=='omega-agent' else http.client.HTTPSConnection(host,8443,timeout=3,context=ssl.create_default_context(cafile='/secrets/ca.crt'))
  client.request('GET',path);r=client.getresponse();r.read(4096);results.append([role,path,r.status]);client.close()
print(json.dumps(results))'''
                self.report['health_responses']=json.loads(self.exec('omega-agent',code))
                assert len(self.report['health_responses'])==18 and all(r[2]==200 for r in self.report['health_responses'])
                after=self.snapshot('after-health')
                for role in ROLES:
                    for key,value in before[role].items():
                        if key.startswith('app_') or key in ('feed_atoms','encode_attempts','encode_intents','publications','maintenance'):
                            assert after[role][key]==value,(role,key)
            if case in ('auth','rebuild'):
                probe=self.args.probe_source
                if case=='auth':
                    self.report['agent_probes']=json.loads(self.exec('omega-agent',probe+'\nprint(json.dumps(agent_auth()))'))
                    self.report['source_probes']=json.loads(self.exec('fusion-search',probe+'\nprint(json.dumps(search_authority()))'))
                else:self.report['rebuild']=json.loads(self.exec('fusion-search',probe+'\nprint(json.dumps(rebuild()))'))
                after=self.snapshot('after-probes');self.same(before,after)
                assert before['omega-agent']['app_occurrences']==after['omega-agent']['app_occurrences']
            if case=='config-restart':
                old={r:self.uid(r) for r in ROLES}
                for role in ROLES:self.config(role,revision='memory-config-2')
                self.upgrade()
                for role in ROLES:
                    self.wait(lambda:self.uid(role)!=old[role],60)
                    self.wait(lambda:self.file(role,'process.json')['configuration_revision']=='memory-config-2',90)
                    self.report['actions'].append(dict(action='config-rollout',role=role,old_uid=old[role],new_uid=self.uid(role)))
                self.ended();after=self.snapshot('after-rollout');self.same(before,after);self.success(after)
                assert before['fusion-embedding']['encode_attempts']==after['fusion-embedding']['encode_attempts']
                assert before['omega-agent']['app_occurrences']==after['omega-agent']['app_occurrences']
        self.report['pods']=json.loads(self.k('get','pods','-o','json'));self.report['pvcs']=json.loads(self.k('get','pvc','-o','json'))
        self.report['status']='PASS'


def main():
    p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True);p.add_argument('--prefix',required=True)
    p.add_argument('--output',required=True);p.add_argument('--values',default='deploy/single-node/memory-values.yaml')
    p.add_argument('--cleanup',action='store_true');p.add_argument('cases',nargs='+',choices=['baseline','health','lost-storage','lost-publication','caller-vector','caller-publication','caller-result','enrollment','expired-enrollment','storage-acceptance','search-before-publication','search-after-publication','encoder-capture','storage-outage','search-outage','budget-outage','wrong-credential','revocation','auth','rebuild','config-restart']);args=p.parse_args();args.image_tag='unused';failed=False
    import hashlib,shutil
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=False)
    args.chart=output/'frozen-chart';shutil.copytree(ROOT/'deploy/helm/omega-fusion',args.chart)
    values=output/'frozen-values.yaml';shutil.copyfile(args.values,values);args.values=str(values)
    args.observer_source=(ROOT/'integration/single_node/memory_observe.py').read_text()
    args.probe_source=(ROOT/'integration/single_node/memory_probe.py').read_text()
    files=[f for folder in ('fusion','integration','deploy') for f in (ROOT/folder).rglob('*') if f.is_file() and f.suffix in ('.py','.json','.yaml','.lock','.metta','.pl') and '__pycache__' not in f.parts]
    (output/'source-manifest.json').write_text(json.dumps({str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files},indent=2)+'\n')
    for name in args.cases:
        test=MemoryCluster(args,name)
        try:test.run()
        except Exception as exc:
            failed=True;test.report.update(status='FAIL',failure=str(exc),traceback=traceback.format_exc())
            try:test.snapshot('failure')
            except Exception as observation:test.report['observation_error']=str(observation)
            for role in ROLES:
                try:(test.root/(role+'.log')).write_text(test.k('logs',role+'-0'))
                except Exception:pass
        finally:
            try:
                test.report['pods']=json.loads(test.k('get','pods','-o','json'));test.report['pvcs']=json.loads(test.k('get','pvc','-o','json'))
            except Exception:pass
            test.finish()
            if args.cleanup:
                test.k('delete','namespace',test.name,'--wait=false','--ignore-not-found=true')
        print(name+': '+test.report['status']+' '+test.report.get('failure',''),flush=True)
    raise SystemExit(int(failed))

if __name__=='__main__':main()
