"""Disabled task-local final-packet H rehearsal; existing owners and qualifiers only."""
import argparse,base64,datetime,hashlib,importlib.util,json,os,re,signal,socket,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
B=module('h19_base',HERE/'h19-adopter-namespace.py')
NS='omega-ref-pilot-adopter19';GNS=NS+'-go';SCOPE='synthetic-pilot-adopter19-browser';GSCOPE='synthetic-pilot-adopter19-go'
PROFILE='task-local-final-H-native-rehearsal/1'
SOURCES={'h19-native.py','h19-browser-phase.py','h19-go-phases.py','h19-adopter-namespace.py'}
PUBLIC_ROOT='artifacts/operator-pilot/h19-rehearsal-source'
CHART='a6d4715b4aee610394dbfde805fc22076ce37d79f41cb1097599353b2d9c7df5'
ROLES=B.ROLES

def validate(p,execute):
    B.check(execute and p.get('enabled')is True,'H native recipe disabled')
    B.check(p['profile']==PROFILE and p['namespaces']==[NS,GNS]and p['scopes']==[SCOPE,GSCOPE],'scope/profile drift')
    B.check(p['maximum_programme_seconds']==4200 and p['cleanup_reserved_seconds']==300,'original bound drift')
    B.check(p['native_direct_ceiling']==22 and p['native_internal_ceiling']==6 and p['additional_live_generations']==0,'work bound drift')
    B.check(p['native_input_deadline_ms']==120000 and p['provider_stage_seconds']==900 and p['browser_story_seconds']==900,'native limits drift')
    B.check(p['runtime_source_manifest_sha256']==B.SOURCE and p['operator_build_manifest_sha256']==B.SDK and p['operator_wheel_sha256']==B.WHEEL,'artifact epoch drift')
    for k in ('distribution_sha256','chart_archive_sha256','clean_install_PASS_report_sha256','clean_install_launcher_sha256','clean_install_driver_sha256','clean_install_executed_plan_sha256','release_record_sha256','selected_kubeconfig_sha256','story_plan_sha256','public_plan_sha256'):B.check(B.digest(p.get(k)),'unfrozen '+k)
    B.check(bool(re.fullmatch('[0-9a-f]{40}',p.get('implementation_commit')or''))and p['selected_node_uid']and p['selected_node_name'],'source/node not frozen')
    B.check(p['context']=='default'and p['protected_namespaces']==['omega-demo'],'context/protection drift')
    B.check(p['driver_output_subdirectory']=='h19-native'and p['generative_runtime_contact']is False and p['chain']is False,'unauthorized work')
    B.check(p['provider_state_transfer']is False and p['corpora_shared_between_namespaces']is False,'corpus/owner isolation drift')
    B.check(set(p['source_files'])==SOURCES and all(B.digest(x)for x in p['source_files'].values()),'source binding absent')
    B.check(set(p['asset_trees'])=={'node','chrome','go'} and all(B.digest(x['manifest_sha256']) and type(x['files']) is int and 1<=x['files']<=25000 for x in p['asset_trees'].values()),'asset selection drift')
    B.check(p['chart16_source_sha256']==CHART and p['source_bundle_relative']==PUBLIC_ROOT,'packet source/chart drift')
    B.check(p['broad_host_etc_mount'] is False and p['model_boundary']=='RECORDED_FIXTURE','disclosure/model boundary drift')
    return p

def check_sources(p,root):
    for name,digest in p['source_files'].items():B.check(Path(name).name==name and B.sha(root/name)==digest,'task-local source drift '+name)

def cleanup_identity(meta,row):
    B.check(meta.get('labels',{}).get('omega.reference/owner')==B.OWNER,'cleanup namespace ownership unproven')
    if row['uid'] is not None:B.check(meta['uid']==row['uid'],'namespace UID changed')
    else:
        created=datetime.datetime.fromisoformat(meta['creationTimestamp'].replace('Z','+00:00')).timestamp()
        attempted=datetime.datetime.fromisoformat(row['attempted_utc']).timestamp()
        B.check(created>=int(attempted),'namespace predates this attempt');row['uid']=meta['uid']
    return row['uid']

def provider_counts(stage_reports,native_reports):
    direct=set();internal=set()
    for stage,report,native in zip(('baseline','replacement'),stage_reports,native_reports):
        B.check(report['status']=='PASS' and report['stage']==stage and report['native_operator_inputs']==4,'provider stage did not pass')
        B.check(len(native['inputs'])==4,'provider direct count')
        for row in native['inputs']:
            observed=row['observed'];key=(row['session'],row['identity'])
            B.check(observed['id']==row['identity'] and observed['state']=='complete' and key not in direct,'provider direct identity/state');direct.add(key)
        returned=report['delegated_result'];B.check(returned['assignment']=='delegated-result' and returned['state']=='complete','provider return capture')
        captured=[(report['session'],returned)]
        closures=report['recipient_closures'] if stage=='baseline' else [x for x in report['closures']if x['role']=='omega-agent-b']
        for closure in closures:
            observation=closure['observation']
            B.check(observation['allocation']['allocation_id']=='incoming/A/'+report['session'],'recipient source mismatch')
            captured.extend((observation['session'],row)for row in observation['inputs'])
        B.check(len(captured)==2 and captured[1][1]['assignment']=='delegated-task','provider internal count')
        for sid,row in captured:
            key=(sid,row['id']);B.check(row['state']=='complete' and key not in internal and key not in direct,'provider internal identity/state');internal.add(key)
        if stage=='replacement':
            replaced=report['provider_replacement'];B.check(replaced['old_pod']!=replaced['new_pod'] and replaced['original_events_and_descriptor_exact'] is True and replaced['after']==report['provider_observation'],'provider replacement not established')
    B.check(len(stage_reports)==len(native_reports)==2 and len(direct)==8 and len(internal)==4 and not direct&internal,'provider aggregate count')
    return dict(direct=len(direct),internal=len(internal),retained_captures=len(direct|internal),original_profile_unchanged=True)

def gateway(values,secrets,root):
    from integration.single_node.pilot_browser_provision import provision
    import yaml
    preview=values['preview'];credentials={}
    for role in ('omega-agent','omega-agent-b','fusion-search'):
        secret=B.load(secrets/(role+'.secret.json'));B.check(secret['metadata']['namespace']==NS,'generated Secret namespace drift')
        credentials[role]={k:base64.b64decode(v,validate=True).decode()for k,v in secret['data'].items()if k.startswith('browser-')}
    agents={role:dict(principal=record['principal'],scopes=[preview['scope'],record['private_scope']])for role,record in preview['agents'].items()}
    made=provision(NS,preview['pilot']['browser']['users'],agents,cleanup=True,credentials=credentials)
    values['pilotWorkbench']=dict(enabled=True,configuration=made['gateway_configuration'],existingTrustSecret='omega-agent-tls-auth',credentials={r:dict(existingSecret=r+'-tls-auth',keys=keys)for r,keys in made['required_secret_keys'].items()})
    user=root/'user';user.mkdir(mode=0o700)
    # The client receives only its selected bootstrap, never owner tokens.
    (user/'shared.bootstrap').write_text(made['bootstrap']['shared']+'\n');(user/'shared.bootstrap').chmod(0o600)
    (user/'hosts').write_text('127.0.0.1 localhost\n::1 localhost\n')
    return values

def browser_args(phase,root,end):
    args=['/usr/bin/bwrap','--unshare-all','--share-net','--die-with-parent','--new-session','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home','--dir','/work','--dir','/etc']
    for system in ('/usr','/lib','/lib64','/bin','/sbin'):args+=['--ro-bind',system,system]
    args+=['--ro-bind','/python','/python','--ro-bind','/work/operator','/work/operator','--ro-bind',str(root/'user'),'/user','--ro-bind',str(root/'user/hosts'),'/etc/hosts','--ro-bind','/story-plan.json','/story-plan.json','--ro-bind','/packet/examples/pilot_browser_story.py','/story.py','--ro-bind','/helpers/h19-browser-phase.py','/entry.py','--bind',str(root/'browser-results'),'/results']
    if phase=='visual':args+=['--ro-bind','/node','/node','--ro-bind','/chrome','/chrome']
    for denied in ('/usr/local/bin/k3s','/usr/local/bin/kubectl','/usr/bin/docker','/usr/bin/ollama','/usr/bin/systemctl','/usr/sbin/service'):
        if Path(denied).exists():args+=['--ro-bind','/dev/null',denied]
    env=dict(PATH='/node/bin:/work/operator/bin:/usr/bin:/bin',HOME='/tmp/browser-home',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',H19_NATIVE_END=str(end),AGENT_BROWSER_SESSION='omega-final-h19',AGENT_BROWSER_SOCKET_DIR='/tmp/h19-browser-sockets',AGENT_BROWSER_EXECUTABLE_PATH='/chrome/chrome')
    for k,v in env.items():args+=['--setenv',k,v]
    args+=['--chdir','/results','/work/operator/bin/python','-I','/entry.py',phase];return args

def inside():
    p=validate(B.load('/plan.json'),True);check_sources(p,Path('/helpers'));B.validate_clean(p,Path('/work'))
    root=Path('/work/h19-native');packet=Path('/packet');started=float(os.environ['H19_START_MONOTONIC']);end=started+4200;work_end=end-300
    report=dict(profile=PROFILE,status='RUNNING',distribution_sha256=p['distribution_sha256'],implementation_commit=p['implementation_commit'],runtime_source_manifest_sha256=B.SOURCE,operator_wheel_sha256=B.WHEEL,started_utc=os.environ['H19_START_UTC'],started_monotonic=started,original_end_monotonic=end,commands=[],phases=[],additional_live_generations=0,physical_HTTP_attempts='NOT_INSTRUMENTED',corpora_shared_between_namespaces=False,execution_environment='CLEAN_INSTALLED_OPERATOR_AND_SEPARATE_BROWSER_MOUNT_NAMESPACE',cleanup=[])
    def save():B.save(root/'progress.json',report,False)
    def record(name,value):report['phases'].append(dict(name=name,value=value));save();return value
    def run(label,args,seconds=90,as_json=False,cleanup=False):
        remaining=(end if cleanup else work_end)-time.monotonic();B.check(remaining>0,'original phase bound expired')
        row=dict(label=label,args=args,started=B.utc(),timeout_seconds=min(seconds,remaining));report['commands'].append(row);save()
        out=root/(str(len(report['commands'])).zfill(3)+'-'+label+'.stdout');err=out.with_suffix('.stderr');proc=None
        try:
            with out.open('xb')as stdout,err.open('xb')as stderr:
                proc=subprocess.Popen(args,cwd=root,stdout=stdout,stderr=stderr,start_new_session=True)
                try:code=proc.wait(timeout=row['timeout_seconds'])
                except BaseException:
                    try:os.killpg(proc.pid,signal.SIGTERM)
                    except ProcessLookupError:pass
                    try:proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:os.killpg(proc.pid,signal.SIGKILL)
                        except ProcessLookupError:pass
                        proc.wait(timeout=2)
                    raise
            row['exit_code']=code;B.check(code==0,label+' failed');return B.load(out)if as_json else out.read_text()
        except BaseException as error:row['failure']=dict(type=type(error).__name__,message=str(error)[:600]);raise
        finally:row.update(finished=B.utc(),stdout=out.name,stderr=err.name);save()
    def cli(label,*args,**kw):return run(label,['/work/operator/bin/fusion-pilot',*args],**kw)
    from integration.single_node.reference_ops import Operator
    class BoundedOperator(Operator):
        cleanup_mode=False
        def command(self,args,**kw):
            remaining=(end if self.cleanup_mode else work_end)-time.monotonic();B.check(remaining>0,'original operator bound expired')
            timeout=min(kw.pop('timeout',120),remaining);binary=kw.pop('binary',False);data=kw.pop('data',None);B.check(not kw,'unknown operator option')
            entries=report.setdefault('operator_commands',[]);index=len(entries)+1;row=dict(namespace=self.namespace,args=args,timeout_seconds=timeout,started=B.utc(),input_recorded=False);entries.append(row);save()
            stdout=root/('operator-'+str(index).zfill(4)+'.stdout');stderr=stdout.with_suffix('.stderr');proc=None
            try:
                with stdout.open('xb')as out,stderr.open('xb')as err:
                    proc=subprocess.Popen(args,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True)
                    try:proc.communicate(input=data if binary or data is None else data.encode(),timeout=timeout)
                    except BaseException:
                        try:os.killpg(proc.pid,signal.SIGTERM)
                        except ProcessLookupError:pass
                        try:proc.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            try:os.killpg(proc.pid,signal.SIGKILL)
                            except ProcessLookupError:pass
                            proc.wait(timeout=1)
                        raise
                row['exit_code']=proc.returncode
                if proc.returncode:
                    secret_input=False
                    if isinstance(data,str):
                        try:secret_input=json.loads(data).get('kind')=='Secret'
                        except (ValueError,AttributeError):pass
                    detail='Secret update failed; material suppressed'if secret_input else stderr.read_text(errors='replace')[-2000:]
                    raise RuntimeError(str(args[:3])+' '+detail)
                return stdout.read_bytes()if binary else stdout.read_text()
            except BaseException as error:row['failure']=dict(type=type(error).__name__,message=str(error)[:600]);raise
            finally:row.update(finished=B.utc(),stdout=stdout.name,stderr=stderr.name);save()
    import yaml
    from integration.single_node.placement import freeze,verify_installed
    from examples.integrated_sustained import IntegratedRunner
    from examples.pilot_endurance import cleanup
    hgo=module('h19_go',Path('/helpers/h19-go-phases.py'))
    ops={n:BoundedOperator('/credentials/kubeconfig','default',n)for n in (NS,GNS)}
    attempted=[];ready={};forward=None;protected=None;main_ok=False
    signal.signal(signal.SIGTERM,lambda *_:(_ for _ in ()).throw(B.Interrupted('termination requested')))
    def stop(op):
        op.cleanup_mode=True
        if op.namespace not in attempted:return
        row=dict(namespace=op.namespace,status='FAIL');report['cleanup'].append(row);save()
        try:
            raw=op.k('get','namespace',op.namespace,'--ignore-not-found','-o','json')
            if not raw.strip():row.update(status='PASS',namespace_absent=True,pods=0,pvcs={});return
            ns=json.loads(raw);cleanup_identity(ns['metadata'],next(x for x in report['namespaces']if x['namespace']==op.namespace));save()
            current=json.loads(op.k('get','pods,pvc,statefulsets,deployments','-o','json'))
            if any(x['kind']=='StatefulSet' for x in current['items']):op.quiesce()
            else:
                # A chart can fail before its first owner. Only the already
                # supported scoped stateless gateway may be stopped here.
                if op.stateless_workloads():
                    op.k('scale','deployment','omega-workbench','--replicas=0')
                    if json.loads(op.k('get','pods','-l','app.kubernetes.io/instance=omega','-o','json'))['items']:
                        op.k('wait','--for=delete','pod','-l','app.kubernetes.io/instance=omega','--timeout=90s',timeout=100)
            resources=json.loads(op.k('get','pods,pvc,statefulsets,deployments','-o','json'))
            B.check(not [x for x in resources['items']if x['kind']=='Pod'],'writers remain')
            pvcs={x['metadata']['name']:x['metadata']['uid']for x in resources['items']if x['kind']=='PersistentVolumeClaim'}
            if op.namespace in ready:B.check(pvcs==ready[op.namespace]['pvcs'],'PVC identity changed')
            row.update(status='PASS',pods=0,pvcs=pvcs)
        except BaseException as error:row['failure']=dict(type=type(error).__name__,message=str(error)[:500]);raise
        finally:save()
    def resources(op,roles,gateway_selected=False):
        items=json.loads(op.k('get','pods,pvc,statefulsets,deployments','-o','json'))['items']
        sts={x['metadata']['name']:x for x in items if x['kind']=='StatefulSet'};pods=[x for x in items if x['kind']=='Pod'];deploy=[x for x in items if x['kind']=='Deployment']
        B.check(set(sts)==roles and len(pods)==len(roles)+int(gateway_selected),'workload cardinality')
        B.check(all(x['spec']['persistentVolumeClaimRetentionPolicy']=={'whenDeleted':'Retain','whenScaled':'Retain'}for x in sts.values()),'PVC retention policy drift')
        B.check({x['metadata']['name']for x in deploy}==({'omega-workbench'}if gateway_selected else set()),'unexpected stateless workload')
        B.check(all(len(x['status'].get('containerStatuses',[]))==1 and x['status']['containerStatuses'][0]['ready']for x in pods),'pod not Ready')
        value=dict(pods=len(pods),pvcs={x['metadata']['name']:x['metadata']['uid']for x in items if x['kind']=='PersistentVolumeClaim'})
        B.check(len(value['pvcs'])==len(roles),'PVC cardinality');ready[op.namespace]=value;return value
    def create(op):
        B.check(not op.k('get','namespace',op.namespace,'--ignore-not-found','-o','json').strip(),'namespace exists')
        node=op.preflight();B.check(node['node_uid']==p['selected_node_uid']and node['node']==p['selected_node_name'],'node identity drift')
        attempted.append(op.namespace);report.setdefault('namespaces',[]).append(dict(namespace=op.namespace,uid=None,attempted_utc=B.utc()));save()
        op.create();report['namespaces'][-1]['uid']=op.owned()['metadata']['uid'];save()
    def secrets(op,values,directory):
        return run('secrets-'+op.namespace,['/work/operator/bin/fusion-create-secrets','--kubeconfig',op.kubeconfig,'--context','default','--namespace',op.namespace,'--preview-values',str(values),'--directory',str(directory)],seconds=120)
    def helm(op,values,label):
        return cli(label,'services','--kubeconfig',op.kubeconfig,'--context','default','--namespace',op.namespace,'upgrade','--chart',str(chart),'--values',str(values),seconds=340)
    try:
        B.check(B.sha(packet/'distribution.json')==p['distribution_sha256'],'packet drift');B.check(B.sha('/story-plan.json')==p['story_plan_sha256'],'synthetic corpus drift')
        verified=cli('verify-artifacts','verify-artifacts','/packet/distribution.json',seconds=600,as_json=True);B.check(verified['status']=='OFFLINE_VERIFIED','artifact verification did not pass')
        manifest=B.load(packet/'distribution.json');B.check(hashlib.sha256(B.canonical(manifest['tested_source'])).hexdigest()==B.SOURCE,'runtime source drift');chart=B.extract_chart(packet,manifest,root/'chart',p['chart_archive_sha256'])
        source_chart=packet/'deploy/helm/omega-fusion';files={str(x.relative_to(source_chart)):B.sha(x)for x in source_chart.rglob('*')if x.is_file()};B.check(hashlib.sha256(B.canonical(files)).hexdigest()==CHART,'source chart drift')
        actual={str(x.relative_to(chart)):B.sha(x)for x in chart.rglob('*')if x.is_file()};B.check(actual.keys()==files.keys(),'chart file-set drift')
        for name in actual:B.check(yaml.safe_load((chart/name).read_text())==yaml.safe_load((source_chart/name).read_text())if name=='Chart.yaml'else actual[name]==files[name],'packaged chart mismatch '+name)
        build=B.load(packet/'wheelhouse/build-manifest.json');B.check(B.sha(packet/'wheelhouse/build-manifest.json')==B.SDK,'SDK drift')
        site=Path('/work/operator/lib/python3.12/site-packages')
        for kind in ('operator','client','provider'):
            for name,row in build[kind]['sources'].items():B.check(B.sha(site/name)==row['sha256']and(site/name).stat().st_size==row['bytes'],'installed source drift '+name)
        record('installed_sources',{k:len(build[k]['sources'])for k in ('operator','client','provider')})
        record('extracted_go_rebuild',hgo.rebuild(packet,Path('/toolchain'),root/'go-rebuild',work_end))
        protected=json.loads(ops[NS].k('-n','omega-demo','get','statefulsets,deployments,pvc','-o','json'));report['protected_before']=B.resource_selection(protected);save()
        images=B.load(packet/'images.json')
        from integration.single_node.pilot_values import generate
        br=root/'browser';br.mkdir(mode=0o700);values=generate(images,SCOPE,NS);path=br/'base-values.yaml';path.write_text(yaml.safe_dump(values,sort_keys=False))
        create(ops[NS]);secrets(ops[NS],path,br/'secrets');values=gateway(values,br/'secrets',br);path=br/'values.yaml';path.write_text(yaml.safe_dump(values,sort_keys=False))
        plan=freeze(chart,NS,values,images);B.save(br/'placement.json',plan);helm(ops[NS],path,'install-browser')
        record('browser_placement',verify_installed(plan,ops[NS]));record('browser_resources',resources(ops[NS],ROLES,True))
        r=IntegratedRunner(ops[NS],br/'readiness',maximum_inputs=1,legacy_crossing_required=False)
        empty={}
        for role in ('omega-agent','omega-agent-b'):
            B.check(r.call(role,'list')==[],'fresh browser owner not empty');empty[role]=B.capacity_zero(r.call(role,'capacity'))
        record('four_initial_owner_reads',dict(calls=4,observations=empty,new_native_inputs=0))
        for role in ('omega-agent','omega-agent-b'):r.admit_selection(role,'final-h19-browser-readiness','shared')
        r.report.update(status='PASS',native_inputs=0);r.save()
        (br/'browser-results').mkdir(mode=0o700)
        with socket.socket()as probe:B.check(probe.connect_ex(('127.0.0.1',8878))!=0,'browser port occupied')
        forward=subprocess.Popen(['/tools/kubectl','--kubeconfig','/credentials/kubeconfig','--context','default','-n',NS,'port-forward','service/omega-workbench','--address','127.0.0.1','8878:8878'],stdout=(br/'forward.stdout').open('xb'),stderr=(br/'forward.stderr').open('xb'),start_new_session=True)
        until=min(work_end,time.monotonic()+30)
        while True:
            B.check(forward.poll()is None and time.monotonic()<until,'port-forward unavailable')
            with socket.socket()as probe:
                if probe.connect_ex(('127.0.0.1',8878))==0:break
            time.sleep(.2)
        for phase,bound in [('story',950),('visual',180),('close',120)]:
            run('browser-'+phase,browser_args(phase,br,work_end),seconds=bound);record('browser-'+phase,B.load(br/'browser-results'/(phase+'.json')))
        closed=B.load(br/'browser-results/close.json');before=next(x['value']for x in closed['actions']if x['name']=='retained_before_close');sid=before['omega-agent']['session']
        current=r.call('omega-agent','observe',sid,'--content');B.check(current['state']=='closed','browser close missing')
        maintenance=cleanup(ops[NS],'omega-agent',sid,work_end);B.check(maintenance['apply_calls']==1 and maintenance['result']['state']=='complete','normal maintenance not applied');record('browser_normal_maintenance',maintenance)
        B.check(r.call('omega-agent','observe',sid,'--content')['inputs']==current['inputs'],'maintenance capture drift')
        os.killpg(forward.pid,signal.SIGTERM);forward.wait(timeout=10);record('browser_forward_stopped',dict(pid=forward.pid,returncode=forward.returncode));forward=None
        stop(ops[NS]);record('browser_terminal',dict(direct=14,internal=2,closed_sessions=2,retained_captures=16))
        # A different corpus/scope prevents accumulated browser memories from
        # exceeding the unchanged inspection profile's three-payload domain.
        gr=root/'provider';gr.mkdir(mode=0o700);gv,gi=hgo.prepare(packet);vp=gr/'initial-values.yaml';vp.write_text(yaml.safe_dump(gv,sort_keys=False));B.save(gr/'images.json',gi)
        gp=freeze(chart,GNS,gv,gi);B.save(gr/'initial-plan.json',gp);create(ops[GNS]);secrets(ops[GNS],vp,gr/'secrets')
        record('capacity_provision',hgo.capacity_provision(ops[GNS],gr/'initial-plan.json',packet/'go-provider/provider-image.json',chart,gr/'capacity',work_end,packet=packet))
        helm(ops[GNS],vp,'install-provider');record('provider_placement_initial',verify_installed(gp,ops[GNS],{'inspect-go':str(packet/'go-provider/provider-image.json')}));record('provider_resources',resources(ops[GNS],ROLES|{'fusion-inspect-go'}))
        cli('provider-baseline','qualify-go-provider','--kubeconfig','/credentials/kubeconfig','--context','default','--namespace',GNS,'--plan',str(gr/'initial-plan.json'),'--artifact',str(packet/'go-provider/provider-image.json'),'--directory',str(gr/'baseline'),seconds=900)
        replacement=hgo.replacement(gv);rp=gr/'replacement-values.yaml';rp.write_text(yaml.safe_dump(replacement,sort_keys=False));newplan=freeze(chart,GNS,replacement,gi);B.save(gr/'replacement-plan.json',newplan);helm(ops[GNS],rp,'provider-additional-template')
        cli('provider-replacement','qualify-go-provider','--kubeconfig','/credentials/kubeconfig','--context','default','--namespace',GNS,'--plan',str(gr/'replacement-plan.json'),'--artifact',str(packet/'go-provider/provider-image.json'),'--directory',str(gr/'replacement'),'--original',str(gr/'baseline'),seconds=900)
        record('capacity_observe',hgo.capacity_observe(ops[GNS],gr/'replacement-plan.json',packet/'go-provider/provider-image.json',chart,gr/'capacity',gr/'capacity-observation',work_end,packet=packet))
        record('provider_drain_retained',hgo.drain_retained(ops[GNS],gr/'replacement/report.json',gr/'drain',work_end))
        reports=[B.load(gr/name/'native/report.json')for name in('baseline','replacement')];stages=[B.load(gr/name/'report.json')for name in('baseline','replacement')]
        provider_total=record('provider_terminal',provider_counts(stages,reports))
        browser_total=next(x['value']for x in report['phases']if x['name']=='browser_terminal')
        report['observed_native_counts']=dict(direct_inputs=browser_total['direct']+provider_total['direct'],internal_deliveries=browser_total['internal']+provider_total['internal'],captured_inputs=browser_total['retained_captures']+provider_total['retained_captures'])
        B.check(report['observed_native_counts']==dict(direct_inputs=22,internal_deliveries=6,captured_inputs=28),'aggregate native counts')
        report['classification']='RECORDED_MODEL_PROPOSALS_REAL_NATIVE_TOOLS_AND_DEPLOYED_PROVIDERS';main_ok=True
    except BaseException as error:report['primary_failure']=dict(type=type(error).__name__,message=str(error)[:1000]);save()
    finally:
        signal.signal(signal.SIGTERM,signal.SIG_IGN)
        if forward is not None:
            try:os.killpg(forward.pid,signal.SIGTERM);forward.wait(timeout=5)
            except BaseException as error:report['forward_cleanup_failure']=dict(type=type(error).__name__,message=str(error)[:300])
        for ns in reversed(attempted):
            if any(x['namespace']==ns and x['status']=='PASS'for x in report['cleanup']):continue
            try:stop(ops[ns])
            except BaseException:pass
        if protected is not None:
            try:
                ops[NS].cleanup_mode=True;after=json.loads(ops[NS].k('-n','omega-demo','get','statefulsets,deployments,pvc','-o','json'));report['protected_comparison']='PASS'if B.resource_selection(after)==report['protected_before']else'FAIL'
            except BaseException as error:report['protected_comparison']='FAIL';report['protected_error']=type(error).__name__
        report['elapsed_seconds']=time.monotonic()-started;report['finished_utc']=B.utc();report['status']='PASS'if main_ok and len(report['cleanup'])==2 and all(x['status']=='PASS'for x in report['cleanup'])and report.get('protected_comparison')=='PASS'and report['elapsed_seconds']<=4200 else'FAIL_RETAINED';save();B.save(root/'report.json',report)
    print(json.dumps(dict(status=report['status'],additional_live_generations=0)));return 0 if report['status']=='PASS'else 1

def outer(path,execute):
    planfile=Path(path).resolve();p=validate(B.load(planfile),execute);check_sources(p,HERE)
    packet=Path(p['distribution']).resolve().parent;B.check(HERE.resolve()==packet/PUBLIC_ROOT,'execute only the reviewed final-packet source copy');B.check(B.sha(HERE/'plan.DISABLED.json')==p['public_plan_sha256'],'public plan drift');B.check(B.sha(packet/'distribution.json')==p['distribution_sha256'],'packet drift');B.check(B.sha(packet/'wheelhouse/build-manifest.json')==B.SDK,'SDK drift')
    release=Path(p['release_record']);B.check(B.sha(release)==p['release_record_sha256'],'release record drift');v=B.load(release);B.check(v['namespaces']==[NS,GNS]and v['implementation_commit']==p['implementation_commit']and v['distribution_sha256']==p['distribution_sha256']and v['heavy_slot_released']is True,'release binding refused')
    work=Path(p['clean_install_output']).resolve();B.validate_clean(p,work);prefix=Path(p['python_prefix']).resolve();cfg=Path(p['selected_kubeconfig']).resolve();B.check(B.sha(cfg)==p['selected_kubeconfig_sha256'],'kubeconfig drift');B.check(B.sha(p['story_plan'])==p['story_plan_sha256'],'synthetic corpus drift')
    import ipaddress,urllib.parse,yaml
    config=yaml.safe_load(cfg.read_bytes());context=next(x['context']for x in config['contexts']if x['name']=='default');cluster=next(x['cluster']for x in config['clusters']if x['name']==context['cluster']);user=next(x['user']for x in config['users']if x['name']==context['user']);url=urllib.parse.urlsplit(cluster['server']);B.check(url.scheme=='https','cluster scheme');ipaddress.ip_address(url.hostname);B.check(cluster.get('certificate-authority-data')and not cluster.get('certificate-authority'),'external cluster CA');B.check(not any(k in user for k in ('exec','auth-provider','client-certificate','client-key','tokenFile')),'external cluster credentials')
    B.check(B.sha('/etc/ssl/openssl.cnf')==p['openssl_config_sha256']and not any(line.strip().startswith('.include')for line in Path('/etc/ssl/openssl.cnf').read_text().splitlines()),'OpenSSL config drift')
    for name,digest in p['tools'].items():B.check(B.sha(name)==digest,'tool drift '+name)
    for name,row in p['asset_trees'].items():
        root=Path(row['path']);actual={str(q.relative_to(root)):B.sha(q)for q in root.rglob('*')if q.is_file()};B.check(len(actual)==row['files'] and B.digest(row['manifest_sha256'])and hashlib.sha256(B.canonical(actual)).hexdigest()==row['manifest_sha256'],'asset tree drift '+name)
    out=work/'h19-native';B.check(not out.exists(),'prior H native attempt exists');out.mkdir(mode=0o700);start=time.monotonic();at=B.utc();B.save(out/'start.json',dict(started_utc=at,started_monotonic=start,original_end_monotonic=start+4200,plan_sha256=B.sha(planfile),source_files=p['source_files']))
    args=['/usr/bin/bwrap','--unshare-all','--share-net','--die-with-parent','--new-session','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home','--dir','/tools','--dir','/credentials','--dir','/etc','--dir','/etc/ssl','--dir','/helpers']
    for system in ('/usr','/lib','/lib64','/bin','/sbin'):args+=['--ro-bind',system,system]
    args+=['--ro-bind','/etc/ssl/openssl.cnf','/etc/ssl/openssl.cnf','--ro-bind',str(prefix),'/python','--ro-bind',str(packet),'/packet','--ro-bind',str(work),'/work','--bind',str(out),'/work/h19-native','--ro-bind',str(cfg),'/credentials/kubeconfig','--ro-bind',str(planfile),'/plan.json','--ro-bind',p['story_plan'],'/story-plan.json']
    for name in p['source_files']:args+=['--ro-bind',str(HERE/name),'/helpers/'+name]
    for original,target in B.TOOLS.items():
        if target!='/usr/bin/bwrap':args+=['--ro-bind',original,target]
    for name,target in [('node','/node'),('chrome','/chrome'),('go','/toolchain')]:args+=['--ro-bind',p['asset_trees'][name]['path'],target]
    for k,v in dict(PATH='/work/operator/bin:/tools:/python/bin:/usr/bin:/bin',HOME='/tmp/operator-home',PYTHONDONTWRITEBYTECODE='1',H19_START_MONOTONIC=str(start),H19_START_UTC=at).items():args+=['--setenv',k,v]
    args+=['--chdir','/work/h19-native','/work/operator/bin/python','-I','/helpers/h19-native.py','--inside']
    code=1;failure=None
    with(out/'launcher.stdout').open('xb')as stdout,(out/'launcher.stderr').open('xb')as stderr:
        proc=None
        try:proc=subprocess.Popen(args,stdout=stdout,stderr=stderr,start_new_session=True);code=proc.wait(timeout=max(.1,start+4200-time.monotonic()))
        except BaseException as error:
            failure=dict(type=type(error).__name__,message=str(error)[:500]);code=124
            if proc:
                try:os.killpg(proc.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                proc.wait(timeout=5)
    B.save(out/'launcher.json',dict(status='PASS'if code==0 else'FAIL',exit_code=code,failure=failure,plan_sha256=B.sha(planfile),elapsed_seconds=time.monotonic()-start,additional_live_generations=0));print(json.dumps(dict(status='PASS'if code==0 else'FAIL',private_output=str(out))));return code

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan');p.add_argument('--execute',action='store_true');p.add_argument('--inside',action='store_true');a=p.parse_args()
    try:sys.exit(inside()if a.inside else outer(a.plan,a.execute))
    except Exception as error:print(json.dumps(dict(status='REFUSED_BEFORE_LAUNCH',type=type(error).__name__,message=str(error)[:600])));sys.exit(2)
