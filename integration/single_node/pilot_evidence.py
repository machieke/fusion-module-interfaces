"""Offline evidence and distribution verification; no service/runtime execution.

This checks exported bytes and reported owner observations. It cannot attest a
malicious host, unavailable private evidence, current chain finality or model
competence. Native application modules are neither imported nor instantiated.
"""
import argparse,ast,hashlib,json,re
from pathlib import Path
from fusion.contracts import canonical,digest,require
from .reference_artifacts import verify as verify_distribution,sha

PROFILE='operator-pilot-evidence/1'
PLAN='operator-pilot-scenarios/1'
STATUSES={'PASS','FAIL','PARTIAL','BLOCKED','NOT_RUN','UNAVAILABLE_PRIVATE'}
KINDS={'unittest-verbose','go-test-json','native-session','primary-json','chain-trace'}
CLASSES={'FIXTURE','STATIC','REAL_PROVIDER','REAL_NATIVE_RECORDED_MODEL','REAL_CHAIN'}
ZERO_KEYS={'additional_live_generations','live_generations','live_generation_authorization','new_live_generations',
           'generative_calls','live_reservations','live_captures','generation_reservations'}
LIMIT=32*1024*1024


def fields(value,names):require(type(value) is dict and set(value)==set(names.split()),'INVALID_ARGUMENT')
def integer(value):require(type(value) is int and value>=0,'INVALID_ARGUMENT');return value
def pin(value):require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value),'INVALID_ARGUMENT');return value
def name(value):require(type(value) is str and re.fullmatch('[a-zA-Z0-9_.:/-]{1,192}',value),'INVALID_ARGUMENT');return value

def primary_status(value):
    # Existing restore observers use FAILED. Preserve those literal bytes and
    # recognize only this exact failure spelling; never infer PASS from state.
    require(value in ('PASS','FAIL','FAILED','PARTIAL'),'NOT_AVAILABLE')
    return 'FAIL' if value=='FAILED' else value

def load(raw):
    require(len(raw)<=LIMIT,'OVERLOADED')
    def pairs(items):
        result={}
        for key,value in items:require(key not in result,'INVALID_ARGUMENT');result[key]=value
        return result
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:require(False,'INVALID_ARGUMENT'))


def pointer(value,path):
    require(type(path) is str and path.startswith('/') and len(path)<=512,'INVALID_ARGUMENT')
    for key in path[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        if type(value) is list:
            require(re.fullmatch('0|[1-9][0-9]*',key) is not None,'INVALID_ARGUMENT');value=value[int(key)]
        else:require(type(value) is dict and key in value,'NOT_AVAILABLE');value=value[key]
    return value


def counters(value):
    if type(value) is dict:
        for key,child in value.items():
            if key in ZERO_KEYS:require(type(child) is int and child==0,'UNAUTHORIZED')
            counters(child)
    elif type(value) is list:
        for child in value:counters(child)


def images(value):
    """Accept exact maps or the existing image export/installed-record vocabulary."""
    if type(value) is dict and value and all(type(v) is str for v in value.values()):items=value.items()
    elif type(value) is list:
        require(value,'NOT_AVAILABLE');items=[]
        for row in value:
            require(type(row) is dict,'INVALID_ARGUMENT')
            key=row.get('kind',row.get('role'));image=row.get('manifest_digest',row.get('manifest',row.get('image')))
            require(type(image) is str,'INVALID_ARGUMENT');items.append((key,image))
    else:require(False,'INVALID_ARGUMENT')
    result={}
    for key,value in items:
        name(key);require(key not in result,'CONFLICT');value=value.split('@')[-1]
        require(value.startswith('sha256:'),'INVALID_ARGUMENT');pin(value[7:]);result[key]=value
    return result


def image_role_bindings(packet,candidate,selected,distribution):
    """Map role names only through exact exported placement selections.

    This is an offline binding check, not a deployment/readiness claim. Actual
    primary reports must still contain the same observed role/image digest.
    """
    bindings=candidate.get('image_roles',{});require(type(bindings) is dict and len(bindings)<=64,'INVALID_ARGUMENT')
    result={}
    for role,binding in bindings.items():
        name(role);fields(binding,'kind plan');kind=binding['kind'];name(kind)
        require(role not in selected and kind in selected,'CONFLICT')
        plan=packet.document(binding['plan'])
        require(plan.get('profile')=='omega-single-node-placement/1' and
            plan.get('source_manifest_sha256')==candidate['source_manifest_sha256'],'CONFLICT')
        require(plan.get('additional_live_generations')==0 and
            plan['images']['source_export_verification']=='PASS' and
            plan['images']['source_manifest_sha256']==candidate['source_manifest_sha256'],'CONFLICT')
        require(packet.file(binding['plan']).read_bytes()==canonical(plan),'CONFLICT')
        records=[x for x in plan['images']['images'] if x['kind']==kind];require(len(records)==1,'CONFLICT');record=records[0]
        require(record['manifest_digest']==selected[kind],'CONFLICT')
        expected_source=record.get('source_manifest_sha256',plan['source_manifest_sha256'])
        if kind=='inspect-go':
            require(distribution is not None and kind in distribution['images'],'NOT_AVAILABLE')
            independent=distribution['images'][kind]
            require(record.get('source_kind')=='independent-go' and independent['source_kind']=='independent-go'
                and independent['source_manifest_sha256']==expected_source
                and independent['manifest']==record['manifest_digest']
                and independent['manifest_sha256']==record['reference_artifact_sha256'],'CONFLICT')
        else:require(expected_source==candidate['source_manifest_sha256'] and record.get('source_kind')!='independent-go','CONFLICT')
        values=plan['values'];components=values['components']
        if role=='omega-workbench':
            require(values.get('pilotWorkbench',{}).get('enabled') is True,'CONFLICT')
            selection=values['pilotWorkbench'].get('image',values['image'])
        else:
            require(role in components,'NOT_AVAILABLE');selection=components[role].get('image',values['image'])
        image=record['repository']+'@'+record['manifest_digest']
        require(selection['repository']+'@'+selection['digest']==image,'CONFLICT')
        node=plan['graph']['nodes'].get(role)
        if node is None:
            # The chain node is deliberately frozen inactive before isolation
            # checks. Its selected image is still explicit in the same values.
            require(role=='f1r3node' and kind=='chain' and values['preview'].get('chain',{}).get('nodeEnabled') is False,'NOT_AVAILABLE')
        else:require(node['image']==image,'CONFLICT')
        result[role]=dict(kind=kind,image=selected[kind],plan=binding['plan'],
            plan_sha256=packet.registry[binding['plan']]['sha256'],source_manifest_sha256=expected_source)
    return result


def unittest_log(raw):
    require(len(raw)<=LIMIT,'OVERLOADED');text=raw.decode('utf-8');rows=[];pending=None;diagnostics=0;diagnostic_bytes=0
    # Python 3.12 verbose output is the primary source of authored identities.
    # Warnings/stdout may occur after the header and before its standalone
    # outcome. Pair only that one pending header; never discard diagnostics to
    # reconstruct an assumed success or borrow an outcome from another test.
    terminal=r'ok|FAIL|ERROR|skipped .+'
    for line in text.splitlines():
        match=re.match(r'^test[^ ]* \(([^)]+)\) \.\.\.(?: (.*))?$',line)
        if match:
            require(pending is None,'CONFLICT');identity,outcome=match.groups()
            require(re.fullmatch('[A-Za-z0-9_.$]+',identity),'INVALID_ARGUMENT')
            if outcome is not None and re.fullmatch(terminal,outcome):rows.append((identity,outcome))
            else:
                pending=identity;diagnostics=int(bool(outcome));diagnostic_bytes=len((outcome or '').encode())
        elif re.fullmatch(terminal,line):
            require(pending is not None,'CONFLICT');rows.append((pending,line));pending=None
        elif pending is not None:
            require(not re.match(r'^Ran [0-9]+ tests? in ',line) and not line.startswith(('OK','FAILED (')),'NOT_AVAILABLE')
            diagnostics+=1;diagnostic_bytes+=len(line.encode())
        require(diagnostics<=256 and diagnostic_bytes<=32768,'OVERLOADED')
    require(pending is None,'NOT_AVAILABLE')
    totals=re.findall(r'^Ran ([0-9]+) tests? in [0-9.]+s$',text,re.M)
    require(len(totals)==1 and rows and int(totals[0])==len(rows),'NOT_AVAILABLE')
    require(all(re.fullmatch('[A-Za-z0-9_.$]+',key) for key,_ in rows),'INVALID_ARGUMENT')
    success=bool(re.search(r'^OK(?: \(skipped=[0-9]+\))?$',text,re.M)) and all(v=='ok' or v.startswith('skipped ') for _,v in rows)
    require(success or bool(re.search(r'^FAILED \(',text,re.M)),'NOT_AVAILABLE')
    return dict(status='PASS' if success else 'FAIL',methods=sorted({k for k,v in rows if not v.startswith('skipped ')}),
                invocations=len(rows),skips=sum(v.startswith('skipped ') for _,v in rows),test_scenarios=[])


def test_source_aliases(packet,bindings):
    """Explicit source files bind only package/discovery names of those files.

    This never strips a module prefix generically. Unbound raw log identities
    stay distinct; ambiguous imports or a missing source class are refused.
    Test source is separate from the runtime image source manifest.
    """
    require(type(bindings) is dict and len(bindings)<=4096,'INVALID_ARGUMENT');aliases={}
    for logical,artifact in bindings.items():
        require(type(logical) is str and re.fullmatch(r'tests/(?:[A-Za-z_][A-Za-z0-9_]*/)*test_[A-Za-z0-9_]+\.py',logical),'INVALID_ARGUMENT')
        raw=packet.file(artifact).read_bytes();require(len(raw)<=LIMIT,'OVERLOADED')
        tree=ast.parse(raw,filename=logical)
        classes={n.name for n in tree.body if isinstance(n,ast.ClassDef)}
        require(classes,'NOT_AVAILABLE');module=logical[:-3].replace('/','.')
        for alias in (module,module.removeprefix('tests.')):
            require(alias not in aliases,'CONFLICT')
            aliases[alias]=dict(source=logical,sha256=packet.registry[artifact]['sha256'],classes=classes)
    return aliases


def test_identity(raw,aliases):
    matches=[(alias,binding) for alias,binding in aliases.items() if raw.startswith(alias+'.')]
    if not matches:return raw,None
    require(len(matches)==1,'CONFLICT');alias,binding=matches[0];suffix=raw[len(alias)+1:]
    parts=suffix.split('.');require(len(parts)==2 and parts[0] in binding['classes'] and parts[1].startswith('test'),'NOT_AVAILABLE')
    canonical_id=binding['source']+'::'+suffix
    return canonical_id,dict(raw=raw,canonical=canonical_id,source=binding['source'],source_sha256=binding['sha256'])


def go_log(raw):
    terminals={};packages={};started=set()
    for line in raw.splitlines():
        row=load(line);require(type(row) is dict and type(row.get('Action')) is str,'INVALID_ARGUMENT')
        package=row.get('Package');name(package);action=row['Action'];test=row.get('Test')
        if test:
            require(type(test) is str and test.startswith('Test'),'INVALID_ARGUMENT');key=package+'.'+test
            if action=='run':require(key not in started,'CONFLICT');started.add(key)
            elif action in ('pass','fail','skip'):
                require(key in started and key not in terminals,'CONFLICT');terminals[key]=action
        elif action in ('pass','fail','skip'):
            require(package not in packages,'CONFLICT');packages[package]=action
    require(packages and started and started==terminals.keys(),'NOT_AVAILABLE')
    success='fail' not in terminals.values() and 'fail' not in packages.values()
    return dict(status='PASS' if success else 'FAIL',methods=sorted(k for k,v in terminals.items() if '/' not in k.split('.Test',1)[-1] and v!='skip'),
        invocations=sum('/' not in k.split('.Test',1)[-1] for k in terminals),
        skips=sum(v=='skip' for v in terminals.values()),test_scenarios=sorted(k for k in terminals if '/' in k.split('.Test',1)[-1]))


def native_inputs(document):
    require(type(document) is dict and document.get('classification')=='RECORDED_MODEL_REAL_NATIVE_TOOLS','UNSUPPORTED_PROFILE')
    require(type(document.get('inputs')) is list and document['inputs'],'NOT_AVAILABLE')
    seen=set();complete=0;captured=0
    for row in document['inputs']:
        require(type(row) is dict and {'role','session','identity','command'}<=row.keys(),'INVALID_ARGUMENT')
        identity=(row['role'],row['session'],row['identity']);require(identity not in seen,'CONFLICT');seen.add(identity)
        require(all(type(x) is str and x for x in identity) and type(row['command']) is str and row['command'],'INVALID_ARGUMENT')
        accepted=row.get('accepted');observed=row.get('observed')
        if accepted is None:
            require('failure' in row and observed is None,'NOT_AVAILABLE');continue
        require(accepted['id']==row['identity'] and accepted['session']==row['session'],'CONFLICT')
        integer(accepted['accepted']);integer(accepted['deadline']);require(accepted['accepted']<accepted['deadline'],'CONFLICT')
        if observed is None:require('failure' in row,'NOT_AVAILABLE');continue
        require(observed['id']==row['identity'] and observed['accepted']==accepted['accepted'] and observed['deadline']==accepted['deadline'],'CONFLICT')
        require(observed['payload']==dict(assignment=accepted['assignment'],text=row['command']),'CONFLICT')
        if observed['result'] is not None:
            require(type(observed['result']) is dict and type(observed['result'].get('projection')) is str
                    and type(observed['result'].get('occurrences')) is list and observed['result']['occurrences'],'NOT_AVAILABLE');captured+=1
        if observed['state']=='complete':require(observed['result'] is not None,'NOT_AVAILABLE');complete+=1
    return dict(operator_inputs=len(seen),completed_inputs=complete,captured_inputs=captured,identities=sorted(seen))


def chain_export(trace,artifact_bytes,result_bytes,readback=None):
    """Validate approved exported bytes; never invoke the node observer."""
    from examples.preview_chain_observer import trace_plan
    from fusion.preview_artifact_contracts import record,encode
    approved,_=trace_plan(trace);registration=trace['reg']
    require(digest(artifact_bytes)==registration['artifact']['digest'],'CONFLICT')
    artifact=record(load(artifact_bytes),approved.scope_ref)
    require(encode(artifact)==artifact_bytes and artifact['sender']==registration['principal'],'CONFLICT')
    require(result_bytes==canonical(dict(digest=digest(artifact_bytes),length=len(artifact_bytes),
        operation='inspect_atom',provider_version='0.1.0')),'CONFLICT')
    require(digest(result_bytes)==approved.commitment_digest==approved.result_ref['digest'],'CONFLICT')
    if readback is not None:
        require(type(readback) is dict and readback.get('profile')=='synthetic-chain-readback/1','UNSUPPORTED_PROFILE');counters(readback)
        if readback.get('status')!='PASS':return 'PARTIAL'
        require(readback['trace_sha256']==digest(canonical(trace)) and readback['artifact_ref']==registration['artifact']
            and readback['inspect_result_ref']==approved.result_ref and readback['inspect_result_sha256']==digest(result_bytes)
            and readback['deploy_id']==trace['saved_intent']['deploy_id'] and readback['read_name']==trace['saved_intent']['read_name'],'CONFLICT')
        require(readback['submissions']==0 and readback['signing_performed'] is False and readback['owner_journals_accessed'] is False
            and readback['independent_reads'] is True,'UNAUTHORIZED')
        require(readback['observation']['effect_finality']=='finalized'
            and readback['observation']['inclusion_block']==trace['final_observation']['inclusion_block'],'CONFLICT')
    return 'PASS'


class Packet:
    def __init__(self,path):
        self.path=Path(path).resolve();self.root=self.path.parent;raw=self.path.read_bytes();self.manifest=load(raw)
        require(raw==canonical(self.manifest),'CONFLICT');require(self.path.with_suffix('.sha256').read_text().strip()==digest(raw),'CONFLICT')
        self.digest=digest(raw);self.registry={};self.documents={};self.private=[]
    def register(self,rows):
        require(type(rows) is list and 1<=len(rows)<=4096,'OVERLOADED');paths=set()
        for row in rows:
            fields(row,'id path sha256 bytes visibility');name(row['id'])
            require(row['id'] not in self.registry and row['path'] not in paths,'CONFLICT');paths.add(row['path'])
            path=Path(row['path']);require(not path.is_absolute() and '..' not in path.parts and path.parts,'UNAUTHORIZED')
            target=self.root/path;require(target.resolve().is_relative_to(self.root) and not target.is_symlink(),'UNAUTHORIZED')
            require(target.resolve()!=self.path,'CONFLICT')
            require(row['visibility'] in ('approved-public','unavailable-private'),'INVALID_ARGUMENT')
            if row['visibility']=='unavailable-private':
                require(row['sha256'] is None and row['bytes'] is None and not target.exists(),'UNAUTHORIZED');self.private.append(row['id'])
            else:
                pin(row['sha256']);integer(row['bytes'])
                require(target.is_file() and target.stat().st_size==row['bytes'] and sha(target)==row['sha256'],'CONFLICT')
            self.registry[row['id']]=row
    def file(self,key):
        require(key in self.registry and key not in self.private,'NOT_AVAILABLE');return self.root/self.registry[key]['path']
    def document(self,key):
        if key not in self.documents:self.documents[key]=load(self.file(key).read_bytes());counters(self.documents[key])
        return self.documents[key]
    def reference(self,value):
        fields(value,'artifact pointer');return pointer(self.document(value['artifact']),value['pointer'])


def verify(path):
    packet=Packet(path);m=packet.manifest
    expected=set('profile release_status candidate distribution artifacts runs scenario_plan gates packages counts historical authorization limitations'.split())
    require(type(m) is dict and set(m) in (expected,expected|{'test_sources'}),'INVALID_ARGUMENT')
    require(m['profile']==PROFILE and m['release_status'] in ('PASS','PARTIAL'),'UNSUPPORTED_PROFILE')
    fields(m['authorization'],'additional_live_generations live_reservations live_captures generative_runtime_contact')
    counters(m['authorization']);require(m['authorization']['generative_runtime_contact'] is False,'UNAUTHORIZED')
    require(type(m['limitations']) is list and m['limitations'] and all(type(x) is str and x for x in m['limitations']),'INVALID_ARGUMENT')
    packet.register(m['artifacts'])
    aliases=test_source_aliases(packet,m.get('test_sources',{}));raw_methods=set();normalized_methods={}
    candidate=m['candidate'];require(type(candidate) is dict and set(candidate) in (set('source source_manifest_sha256 images'.split()),set('source source_manifest_sha256 images image_roles'.split())),'INVALID_ARGUMENT')
    require(type(candidate['source']) is dict and candidate['source'],'NOT_AVAILABLE')
    for filename,binding in candidate['source'].items():name(filename);pin(binding)
    pin(candidate['source_manifest_sha256']);require(digest(canonical(candidate['source']))==candidate['source_manifest_sha256'],'CONFLICT')
    selected=images(candidate['images']);distribution=None
    if m['distribution'] is not None:
        distribution=verify_distribution(packet.file(m['distribution']))
        original=packet.document(m['distribution'])
        require(original['tested_source']==candidate['source'],'CONFLICT')
        require(images({k:v['manifest'] for k,v in distribution['images'].items()})==selected,'CONFLICT')
    else:require(m['release_status']=='PARTIAL','NOT_AVAILABLE')
    role_images=image_role_bindings(packet,candidate,selected,distribution)
    # Immutable historical pins are checked against an independently included old index.
    require(type(m['historical']) is list,'INVALID_ARGUMENT'); historical_edges={}
    for row in m['historical']:
        fields(row,'artifact index pointer');actual=packet.registry[row['artifact']]['sha256']
        prior=pointer(packet.document(row['index']),row['pointer']);require(prior==actual,'CONFLICT')
        require(row['artifact']!=row['index'] and row['artifact'] not in historical_edges,'CONFLICT');historical_edges[row['artifact']]=row['index']
    for start in historical_edges:
        seen=set();current=start
        while current in historical_edges:
            require(current not in seen,'CONFLICT');seen.add(current);current=historical_edges[current]
    runs={};methods=set();invocations=0;skips=0;test_scenarios=set();operator={};captures={};internal={};internal_runs=set();run_failures=[];independent_test_sources={}
    require(type(m['runs']) is list and 1<=len(m['runs'])<=256,'NOT_AVAILABLE')
    for run in m['runs']:
        fields(run,'id kind phase status classification primary native internal chain source_manifest_sha256 images image_binding components depends_on reason')
        name(run['id']);require(run['id'] not in runs,'CONFLICT');require(run['kind'] in KINDS and run['phase'] in ('candidate','historical'),'INVALID_ARGUMENT')
        require(run['status'] in STATUSES and run['classification'] in CLASSES,'INVALID_ARGUMENT');pin(run['source_manifest_sha256'])
        require(type(run['internal']) is list,'INVALID_ARGUMENT')
        if run['kind']!='chain-trace':require(run['chain'] is None,'INVALID_ARGUMENT')
        require(type(run['depends_on']) is list and len(set(run['depends_on']))==len(run['depends_on']),'INVALID_ARGUMENT')
        require(type(run['reason']) is str and (run['status']=='PASS' or run['reason']),'INVALID_ARGUMENT')
        if run['phase']=='candidate' and run['source_manifest_sha256']!=candidate['source_manifest_sha256']:
            # The independently built reference provider has its own source
            # archive. Only its Go conformance log may use that exact verified
            # source instead of falsely inheriting the Python image source.
            require(run['kind']=='go-test-json' and run['classification'] in ('STATIC','FIXTURE')
                and distribution is not None,'CONFLICT')
            independent=distribution['images'].get('inspect-go',{})
            require(independent.get('source_kind')=='independent-go' and
                independent.get('source_manifest_sha256')==run['source_manifest_sha256'],'CONFLICT')
            independent_test_sources[run['id']]=dict(kind='inspect-go',source_manifest_sha256=run['source_manifest_sha256'],
                image=independent['manifest'],reference_artifact_sha256=independent['manifest_sha256'])
        if run['status'] in ('BLOCKED','NOT_RUN','UNAVAILABLE_PRIVATE'):
            require(run['primary'] is None and run['native'] is None and not run['internal'] and not run['images'] and run['image_binding'] is None and not run['components'],'CONFLICT')
            runs[run['id']]=dict(**run,observed_status=run['status']);continue
        require(run['primary'] is not None,'NOT_AVAILABLE');file=packet.file(run['primary'])
        native=None;test=None;report_artifacts={run['primary'],run['native']}-{None}
        if run['kind'] in ('unittest-verbose','go-test-json'):
            require(run['classification'] in ('FIXTURE','STATIC') and run['native'] is None and not run['images'] and run['image_binding'] is None,'CONFLICT')
            test=(unittest_log if run['kind']=='unittest-verbose' else go_log)(file.read_bytes());actual=test['status']
        else:
            primary=packet.document(run['primary']);require(type(primary) is dict,'INVALID_ARGUMENT')
            if run['kind']=='chain-trace':
                require(type(run['chain']) is dict and set(run['chain']) in (
                    {'artifact','inspection_result','readback'},
                    {'artifact','inspection_result','readback','execution_report'}),'INVALID_ARGUMENT')
                actual=chain_export(primary,packet.file(run['chain']['artifact']).read_bytes(),
                    packet.file(run['chain']['inspection_result']).read_bytes(),
                    packet.document(run['chain']['readback']) if run['chain']['readback'] is not None else None)
                require(run['classification']=='REAL_CHAIN','CONFLICT')
                if 'execution_report' in run['chain']:
                    execution_id=run['chain']['execution_report'];require(execution_id not in report_artifacts,'CONFLICT')
                    execution=packet.document(execution_id)
                    require(type(execution) is dict,'NOT_AVAILABLE');execution_status=primary_status(execution.get('status'))
                    require(all(execution.get(key)==primary[field] for key,field in (
                        ('registration','reg'),('saved_intent','saved_intent'),('final_observation','final_observation'))),'CONFLICT')
                    require(execution.get('source_manifest_sha256',run['source_manifest_sha256'])==run['source_manifest_sha256'],'CONFLICT')
                    require(execution.get('fixture') is not True and execution.get('classification') not in (
                        'FIXTURE','UNIT_FIXTURE','RECORDED_RESPONSE_FIXTURE','RECORDED_FIXTURE'),'CONFLICT')
                    # A later execution failure cannot be hidden behind an
                    # otherwise valid finalized trace. Readback stays separate.
                    if execution_status=='PASS':require(actual=='PASS','CONFLICT')
                    actual=execution_status;report_artifacts.add(execution_id)
            else:
                actual=primary_status(primary.get('status'))
            if run['kind']=='native-session':
                require(run['classification']=='REAL_NATIVE_RECORDED_MODEL' and run['native'] is not None,'CONFLICT')
                document=packet.document(run['native']);native=native_inputs(document)
                require(primary.get('native_report_sha256')==packet.registry[run['native']]['sha256'],'CONFLICT')
                if document.get('status') in ('FAIL','FAILED'):actual='FAIL'
            else:require(run['native'] is None,'CONFLICT')
        require(actual==run['status'],'CONFLICT')
        require(type(run['components']) is dict,'INVALID_ARGUMENT')
        real=[]
        if run['classification'] in ('REAL_PROVIDER','REAL_NATIVE_RECORDED_MODEL','REAL_CHAIN'):
            require(primary.get('classification') not in ('FIXTURE','UNIT_FIXTURE','RECORDED_RESPONSE_FIXTURE','RECORDED_FIXTURE')
                and primary.get('fixture') is not True,'CONFLICT')
        for component,claim in run['components'].items():
            name(component);fields(claim,'kind evidence');require(claim['kind'] in ('REAL','FIXTURE','UNRUN','UNAVAILABLE'),'INVALID_ARGUMENT')
            require(type(claim['evidence']) is list and (claim['kind'] not in ('REAL','FIXTURE') or claim['evidence']),'NOT_AVAILABLE')
            for ref in claim['evidence']:
                require(ref['artifact'] in report_artifacts,'CONFLICT')
                observed=packet.reference(ref);require(observed not in (None,False,'',[],{}),'NOT_AVAILABLE')
                if claim['kind']=='REAL':
                    encoded=canonical(observed).decode().lower();require('fixture' not in encoded and 'not_run' not in encoded and 'not_checked' not in encoded,'CONFLICT')
            if claim['kind']=='REAL':real.append(component)
        if run['classification'] in ('REAL_PROVIDER','REAL_NATIVE_RECORDED_MODEL','REAL_CHAIN'):
            require(real and run['images'] and run['image_binding'] is not None,'NOT_AVAILABLE')
            require(run['image_binding']['artifact'] in report_artifacts,'CONFLICT')
            declared=images(run['images']);require(images(packet.reference(run['image_binding']))==declared,'CONFLICT')
            if run['phase']=='candidate':require(all((selected.get(k) if k in selected else role_images.get(k,{}).get('image'))==v for k,v in declared.items()),'CONFLICT')
        else:require(not real,'CONFLICT')
        if run['phase']=='candidate':
            if test:
                raw_methods.update(test['methods'])
                for raw_id in test['methods']:
                    canonical_id,binding=test_identity(raw_id,aliases) if run['kind']=='unittest-verbose' else (raw_id,None)
                    methods.add(canonical_id)
                    if binding is not None:normalized_methods[raw_id]=binding
                invocations+=test['invocations'];skips+=test['skips']
                test_scenarios.update((run['id'],x) for x in test['test_scenarios'])
            if native:
                for row in packet.document(run['native'])['inputs']:
                    identity=(row['role'],row['session'],row['identity'])
                    accepted=row.get('accepted');semantic=canonical(dict(command=row['command'],accepted=accepted))
                    if identity in operator:
                        prior=load(operator[identity]);require(prior['command']==row['command'] and
                            (prior['accepted'] is None or prior['accepted']==accepted),'CONFLICT')
                    operator[identity]=semantic
                    result=(row.get('observed') or {}).get('result')
                    if result is not None:
                        captured=digest(canonical(result));require(identity not in captures or captures[identity]==captured,'CONFLICT');captures[identity]=captured
        for ref in run['internal']:
            require(ref['artifact'] in report_artifacts,'CONFLICT')
            observed=packet.reference(ref);require(type(observed) is dict and type(observed.get('inputs')) is list,'INVALID_ARGUMENT')
            require(type(observed.get('session')) is str and type(observed.get('principal')) is str,'INVALID_ARGUMENT')
            if run['phase']=='candidate':internal_runs.add(run['id'])
            for row in observed['inputs']:
                if row['assignment'] not in ('delegated-task','delegated-result'):continue
                integer(row['accepted']);integer(row['deadline']);require(row['accepted']<row['deadline'],'CONFLICT')
                key=(observed['principal'],observed['session'],row['id'])
                value={k:row[k] for k in ('accepted','deadline','assignment','payload')}
                if run['phase']=='candidate':
                    require(key not in internal or internal[key]==value,'CONFLICT');internal[key]=value
        if actual!='PASS':run_failures.append(dict(run=run['id'],status=actual,phase=run['phase']))
        runs[run['id']]=dict(**run,observed_status=actual,report_artifacts=report_artifacts)
    def graph(key,seen):
        require(key in runs and key not in seen,'CONFLICT')
        for dependency in runs[key]['depends_on']:graph(dependency,seen|{key})
    for key in runs:graph(key,set())
    plan=packet.document(m['scenario_plan']);fields(plan,'profile scenarios');require(plan['profile']==PLAN and type(plan['scenarios']) is list,'INVALID_ARGUMENT')
    scenarios={}
    for scenario in plan['scenarios']:
        fields(scenario,'id run assertions');name(scenario['id']);require(scenario['id'] not in scenarios and scenario['run'] in runs,'CONFLICT')
        require(type(scenario['assertions']) is list and scenario['assertions'],'NOT_AVAILABLE');results=[];substantive=False
        for assertion in scenario['assertions']:
            fields(assertion,'artifact pointer operator expected');require(assertion['operator'] in ('equals','contains'),'INVALID_ARGUMENT')
            require(assertion['artifact'] in runs[scenario['run']].get('report_artifacts',set()),'CONFLICT')
            actual=packet.reference({k:assertion[k] for k in ('artifact','pointer')})
            if assertion['pointer'].split('/')[-1] not in ('status','passed','success','profile','classification'):substantive=True
            if assertion['operator']=='equals':passed=type(actual) is type(assertion['expected']) and actual==assertion['expected']
            else:require(type(actual) is str and type(assertion['expected']) is str and assertion['expected'],'INVALID_ARGUMENT');passed=assertion['expected'] in actual
            results.append(passed)
        require(substantive,'NOT_AVAILABLE');passed=all(results)
        require(runs[scenario['run']]['status']!='PASS' or passed,'CONFLICT');scenarios[scenario['id']]=dict(run=scenario['run'],passed=passed)
    require(type(m['gates']) is dict and set('ABCDEFGH')<=m['gates'].keys(),'NOT_AVAILABLE')
    exceptions=[]
    for key,gate in m['gates'].items():
        name(key);fields(gate,'status runs scenarios reason');require(gate['status'] in STATUSES and type(gate['reason']) is str,'INVALID_ARGUMENT')
        require(type(gate['runs']) is list and len(set(gate['runs']))==len(gate['runs']) and all(x in runs for x in gate['runs']),'CONFLICT')
        require(type(gate['scenarios']) is list and len(set(gate['scenarios']))==len(gate['scenarios']) and all(x in scenarios for x in gate['scenarios']),'CONFLICT')
        if gate['status']=='PASS':
            require(gate['runs'] and gate['scenarios'],'NOT_AVAILABLE')
            require(all(runs[x]['phase']=='candidate' and runs[x]['status']=='PASS' for x in gate['runs']),'CONFLICT')
            require(all(scenarios[x]['passed'] and scenarios[x]['run'] in gate['runs'] for x in gate['scenarios']),'CONFLICT')
        else:require(gate['reason'],'INVALID_ARGUMENT');exceptions.append(dict(gate=key,status=gate['status'],reason=gate['reason']))
    require(type(m['packages']) is dict and set(m['packages'])=={'V%02d'%n for n in range(1,41)},'NOT_AVAILABLE')
    for key,package in m['packages'].items():
        fields(package,'status gates reason');require(package['status'] in STATUSES and type(package['reason']) is str,'INVALID_ARGUMENT')
        require(type(package['gates']) is list and len(set(package['gates']))==len(package['gates']) and all(x in m['gates'] for x in package['gates']),'CONFLICT')
        if package['status']=='PASS':require(package['gates'] and all(m['gates'][x]['status']=='PASS' for x in package['gates']),'CONFLICT')
        else:require(package['reason'],'INVALID_ARGUMENT');exceptions.append(dict(package=key,status=package['status'],reason=package['reason']))
    counted=dict(authored_test_methods=len(methods),test_method_invocations=invocations,
        test_runs=sum(r['kind'] in ('unittest-verbose','go-test-json') and r['phase']=='candidate' and r['primary'] is not None for r in runs.values()),
        test_subscenarios=len(test_scenarios),test_skipped_invocations=skips,workflow_scenarios=sum(runs[x['run']]['phase']=='candidate' for x in scenarios.values()),
        native_operator_inputs=len(operator),native_accepted_inputs=sum(load(v)['accepted'] is not None for v in operator.values()),
        observed_internal_native_inputs=len(internal),native_captures=len(captures),additional_live_generations=0)
    require(type(m['counts']) is dict and all(type(v) is int and v>=0 for v in m['counts'].values()) and m['counts']==counted,'CONFLICT')
    if m['release_status']=='PASS':require(distribution is not None and not exceptions and not any(x['phase']=='candidate' for x in run_failures) and not packet.private,'CONFLICT')
    return dict(profile=PROFILE,status='VERIFIED_'+m['release_status'],manifest_sha256=packet.digest,counts=counted,
        authored_test_methods=sorted(methods),raw_authored_test_methods=sorted(raw_methods),
        independent_test_sources=independent_test_sources,
        test_identity_bindings=[normalized_methods[x] for x in sorted(normalized_methods)],exceptions=exceptions,unsuccessful_runs=run_failures,
        unavailable_private_evidence=packet.private,internal_input_observation_runs=sorted(internal_runs),distribution_verified=distribution is not None,image_role_bindings=role_images,
        scope='Offline exported artifact, source/image, primary test, scenario and authority-counter consistency only',
        not_established=['malicious-host execution authenticity','current chain finality without authorized observer','model competence','unavailable private evidence'],
        additional_live_generations=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['verify']);parser.add_argument('manifest');parser.add_argument('--output');args=parser.parse_args()
    result=verify(args.manifest);raw=json.dumps(result,indent=2)+'\n'
    if args.output:Path(args.output).write_text(raw)
    else:print(raw)
if __name__=='__main__':main()
