"""Qualify the extracted Go binary against task-owned deployed native services.

Python provisions/observes the test. Every contract request below is made by the
independent static Go executable, inside a mount namespace with no checkout,
Python, provider database, kubeconfig or provider signing key. The local-only
port-forward preserves certificate DNS validation and scoped bearer authority.
"""
import argparse,base64,contextlib,json,os,select,shutil,subprocess,tempfile,time
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON


@contextlib.contextmanager
def tunnel(op,role):
    command=['kubectl','--kubeconfig',op.kubeconfig,'--context',op.context,'-n',op.namespace,
             'port-forward','--address=127.0.0.1','service/'+role,':8443']
    proc=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        require(select.select([proc.stdout],[],[],20)[0],'NOT_AVAILABLE')
        line=proc.stdout.readline();require(line.startswith('Forwarding from 127.0.0.1:'),'NOT_AVAILABLE')
        yield int(line.split(':')[1].split()[0])
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()


def qualify(op,directory,binary):
    root=Path(directory).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    report=dict(status='RUNNING',additional_live_generations=0,namespace=op.namespace,
                client_sha256=digest(Path(binary).read_bytes()),model='RECORDED_PROPOSALS',
                services='REAL native Omega, DeTTa, E5, Chroma and authenticated HTTPS',
                placement='same-node local-only kubectl tunnel to pod; no multi-host claim',calls=[])
    def save():(root/'report.json').write_bytes(canonical(report))
    save();private=root/'private-client';private.mkdir(mode=0o700)
    artifact=Path(tempfile.mkdtemp(prefix='omega-go-artifact-'));os.chmod(artifact,0o700)
    shutil.copy2(binary,artifact/'omega-client')
    def write(name,value):
        path=private/name;path.write_bytes(value if type(value) is bytes else canonical(value));path.chmod(0o600)
    def call(kind,action,deadline,*,expected=None,**kwargs):
        args=['/app/omega-client','--config','/client/'+kind+'.json','--action',action,'--deadline-ms',str(deadline)]
        for key,value in kwargs.items():
            args+=['--'+key.replace('_','-')]
            if type(value) is not bool:args.append(str(value))
        command=['bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts',
                 '--ro-bind',str(artifact),'/app','--ro-bind',str(private),'/client',
                 '--proc','/proc','--dev','/dev','--clearenv','--setenv','HOME','/nonexistent',
                 '--chdir','/app',*args]
        start=time.time_ns()//1000000
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=35)
        entry=dict(kind=kind,action=action,started_ms=start,deadline_ms=deadline,returncode=result.returncode)
        if result.returncode:
            # Client errors contain only bounded public codes here, no config.
            error=result.stderr.decode().strip();entry['error']=error if len(error)<128 else 'BOUNDED_CLIENT_FAILURE'
            report['calls'].append(entry);save();require(expected==error,'NOT_AVAILABLE');return None
        require(expected is None,'CONFLICT');value=json.loads(result.stdout)
        entry.update(response_sha256=digest(result.stdout),finished_ms=time.time_ns()//1000000)
        report['calls'].append(entry);save();return value
    try:
        op.owned();report['images']={r['metadata']['name']:r['spec']['template']['spec']['containers'][0]['image'] for r in op.workloads()};save()
        # Trusted test provisioning reads only the caller's selected port config.
        script='''import json,base64
from pathlib import Path
o=json.loads(Path('/run/fusion/owner.json').read_bytes());c=json.loads(Path('/config/component.json').read_bytes())
a=json.loads(Path('/run/fusion/templates/shared/history-atoms.json').read_bytes())
print(json.dumps({'principal':o['native_sessions']['principal'],'scope':o['native_sessions']['scope'],
'operator':o['principals']['operator']['credential'],'host':c['peers'][c['role']],'atoms':a,
'ca':base64.b64encode(Path('/secrets/ca.crt').read_bytes()).decode()}))'''
        selected=json.loads(op.k('exec','omega-agent-0','--',PYTHON,'-c',script))
        write('ca.pem',base64.b64decode(selected['ca']));write('session.token',selected['operator'].encode())
        write('atom.token',selected['atoms']['credential'].encode());write('wrong.token',b'wrong-generated-token')
        with tunnel(op,'omega-agent') as agent_port,tunnel(op,'fusion-storage') as atom_port:
            shared=dict(profile='fusion-go-client/1',ca_file='/client/ca.pem',principal=selected['principal'],scope=selected['scope'])
            session=dict(shared,kind='session',endpoint='https://127.0.0.1:'+str(agent_port),server_name=selected['host'],credential_file='/client/session.token',actor='operator',contract='omega-native-sessions/3')
            atom=dict(shared,kind='atom',endpoint='https://127.0.0.1:'+str(atom_port),server_name=selected['atoms']['endpoint']['host'],credential_file='/client/atom.token',contract='immutable-commit-feed/2',composition=selected['atoms']['composition'],descriptor=selected['atoms']['descriptor'])
            write('session.json',session);write('atom.json',atom)
            end=time.time_ns()//1000000+600000
            report['initial_capacity']=call('session','capacity',end)
            # Opaque immutable bytes preserve Unicode and >2^53 integers exactly.
            payload=canonical(dict(synthetic='snow 雪, rocket 🚀',integer=9007199254740993))
            write('payload.json',payload);head=call('atom','head',end)
            ref=call('atom','create',end,identity='go-opaque-01',payload_file='/client/payload.json')
            replay=call('atom','create',end,identity='go-opaque-01',payload_file='/client/payload.json')
            require(ref==replay,'CONFLICT');write('ref.json',ref)
            got=call('atom','get',end,ref_file='/client/ref.json');require(base64.b64decode(got['bytes_base64'])==payload,'CONFLICT')
            after=call('atom','head',end);require(after['sequence']==head['sequence']+1,'CONFLICT')
            report['storage']=dict(ref=ref,exact_bytes=True,duplicate_one_commit=True,head=after)
            allocated=call('session','allocate',end,identity='go-native-session',template='shared');sid=allocated['session']
            repeated=call('session','allocate',end,identity='go-native-session',template='shared')
            require(repeated['allocation']==allocated['allocation'],'CONFLICT')
            report['allocation']=allocated;save()
            # The old session operator role does not grant binding; do not widen
            # authority merely for this test. Allocation carries exact metadata.
            inputs=[]
            for identity,command in [('go-remember','remember The synthetic copper lantern is stored in chest alder'),
                                     ('go-query','query synthetic copper lantern storage')]:
                accepted=call('session','submit',end,session=sid,identity=identity,text=command)
                row=dict(command=command,accepted=accepted);inputs.append(row);report['inputs']=inputs;save()
                # Each call exits. Re-open the extracted binary to observe the
                # same accepted identity; no resubmission or provider access.
                bound=min(end,accepted['deadline']+8000)
                while time.time_ns()//1000000<bound:
                    observed=call('session','observe',bound,session=sid,content=True)
                    item=next(x for x in observed['inputs'] if x['id']==identity)
                    if item['state']=='complete':break
                    if item['state'] not in ('accepted','dispatched'):break
                    time.sleep(1)
                row['observed']=item;save();require(item['state']=='complete','NOT_AVAILABLE')
                require(item['deadline']==accepted['deadline'],'CONFLICT')
            require('chest alder' in inputs[1]['observed']['result']['projection'],'CONFLICT')
            report['native_query_correctness']=True
            again=call('session','observe',end,session=sid,content=True)
            require(again['inputs'][-1]['result']==inputs[-1]['observed']['result'],'CONFLICT')
            report['disconnected_result_observation']=True
            write('wrong.json',dict(session,credential_file='/client/wrong.token'))
            call('wrong','capacity',end,expected='UNAUTHORIZED')
            write('wrong-profile.json',dict(session,contract='omega-native-sessions/999'))
            call('wrong-profile','capacity',end,expected='UNSUPPORTED_PROFILE')
            call('session','capacity',1,expected='DEADLINE_EXCEEDED')
            report['final_capacity']=call('session','capacity',end)
            report['status']='PASS'
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:
        save();op.quiesce();report['quiesced']=True;save();shutil.rmtree(artifact)
    return report


def replay_check(op,directory,binary,previous):
    """Revalidate a stricter client using captured identities, without input admission."""
    root=Path(directory).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    old=Path(previous).resolve();prior=json.loads((old/'report.json').read_bytes());require(prior['status']=='PASS','CONFLICT')
    report=dict(status='RUNNING',additional_live_generations=0,new_native_inputs=0,client_sha256=digest(Path(binary).read_bytes()),
                prior_report_sha256=digest((old/'report.json').read_bytes()),observations=[])
    artifact=Path(tempfile.mkdtemp(prefix='omega-go-replay-'));os.chmod(artifact,0o700)
    shutil.copy2(binary,artifact/'omega-client');private=root/'private-client';shutil.copytree(old/'private-client',private);os.chmod(private,0o700)
    try:
        op.owned()
        with tunnel(op,'omega-agent') as agent,tunnel(op,'fusion-storage') as atoms:
            for kind,port in [('session',agent),('atom',atoms)]:
                path=private/(kind+'.json');cfg=json.loads(path.read_bytes());cfg['endpoint']='https://127.0.0.1:'+str(port);path.write_bytes(canonical(cfg))
            end=time.time_ns()//1000000+30000
            for kind,action,args in [('session','observe',['--session',prior['allocation']['session'],'--content']),
                                     ('atom','get',['--ref-file','/client/ref.json'])]:
                result=subprocess.run(['bwrap','--die-with-parent','--unshare-pid','--unshare-ipc','--unshare-uts',
                    '--ro-bind',str(artifact),'/app','--ro-bind',str(private),'/client','--proc','/proc','--dev','/dev',
                    '--clearenv','--chdir','/app','/app/omega-client','--config','/client/'+kind+'.json',
                    '--action',action,'--deadline-ms',str(end),*args],capture_output=True,timeout=35)
                require(result.returncode==0,'NOT_AVAILABLE');value=json.loads(result.stdout)
                if kind=='session':
                    for expected in prior['inputs']:
                        got=next(x for x in value['inputs'] if x['id']==expected['accepted']['id'])
                        require(got==expected['observed'],'CONFLICT')
                else:require(base64.b64decode(value['bytes_base64'])==(private/'payload.json').read_bytes(),'CONFLICT')
                report['observations'].append(dict(kind=kind,action=action,response_sha256=digest(result.stdout),exact_retained=True))
        report['status']='PASS'
    except BaseException as error:
        report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:
        (root/'report.json').write_bytes(canonical(report));op.quiesce();report['quiesced']=True
        (root/'report.json').write_bytes(canonical(report));shutil.rmtree(artifact)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','binary'):p.add_argument('--'+name,required=True)
    p.add_argument('--replay-previous')
    a=p.parse_args();op=Operator(a.kubeconfig,a.context,a.namespace)
    value=replay_check(op,a.directory,a.binary,a.replay_previous) if a.replay_previous else qualify(op,a.directory,a.binary)
    print(json.dumps(dict(status=value['status'],additional_live_generations=0)))
