"""Real browser HTTP/session/SQLite boundaries with explicitly fixture tools.

No native tool, Kubernetes process or generative runtime is run. The owner API,
scoped metadata, authorization, catalogue, receipt replay and HTTP are real;
model/native completion values are labelled authored fixtures.
"""
import copy
from hashlib import sha256
import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from fusion.contracts import ContractError, canonical
from fusion.preview_session_service import SessionPorts
from integration.single_node import pilot_browser_observation as observation
from integration.single_node.pilot_browser_configure import configure
from integration.single_node.pilot_browser_sessions import Sessions, PROFILE
from integration.single_node.pilot_workbench import ScopedWorkbench
from integration.single_node.preview_workbench import handler, PAGE
from integration.single_node.pilot_browser_page import page
from tests import test_phase3_composition as fixture


class BrowserTests(unittest.TestCase):
    settings=fixture.DynamicConfiguration.settings
    build=fixture.DynamicConfiguration.build

    def setUp(self):
        fixture.DynamicConfiguration.setUp(self)
        for spec in self.preview['agents'].values():spec['tools']+=['pin','unpin','task-context']
        _,self.cfg,self.state,self.run=self.build();self.path=self.run/'owner.json'
        self.root=self.path.parent;self.bootstrap='synthetic-bootstrap-alice-'+('a'*32)
        private=copy.deepcopy(self.cfg['native_sessions']['allocation']['templates']['shared'])
        private['scope']='synthetic-private-canary'
        self.cfg['native_sessions']['allocation']['templates']['private']=private
        # Add a second private scope only to its own fresh, provisioned actors.
        secret=self.root/'browser-secrets';secret.mkdir()
        users={}
        for name,role,scope in [('alice','developer',self.scope),('bob','viewer',private['scope']),('operator','operator',self.scope)]:
            (secret/('browser-'+name+'-token')).write_text('fixture-service-'+name+'-'+'x'*32)
            users[name]=dict(role=role,scopes=[scope],credential_key='browser-'+name+'-token')
        configure({'pilot_browser':{'profile':PROFILE,'users':users}},self.cfg,secret)
        self.path.write_bytes(canonical(self.cfg))
        self.browser_path=self.root/'browser.json'
        self.browser_cfg=dict(profile=PROFILE,namespace='omega-ref-browser-fixture',users={name:dict(
            bootstrap_sha256=sha256((self.bootstrap if name=='alice' else 'fixture-bootstrap-'+name+'-'+'b'*32).encode()).hexdigest(),
            revision=1,role=role['role'],enabled=True,session_seconds=60,
            targets={'omega-agent':dict(principal='A',scope=role['scopes'][0],endpoint=dict(host='127.0.0.1',port=9443,ca_file=str(secret/'ca.crt')),
                credential_file=str(secret/role['credential_key']))}) for name,role in users.items()})
        self.browser_path.write_bytes(canonical(self.browser_cfg));self.workbench=ScopedWorkbench(self.browser_path)
        self.sessions=Sessions(self.browser_path);self.calls=[]
        self.mock=patch('integration.single_node.pilot_workbench.invoke',side_effect=self.transport);self.mock.start();self.addCleanup(self.mock.stop)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.workbench,0,self.sessions));self.port=self.server.server_address[1]
        self.server.RequestHandlerClass=handler(self.workbench,self.port,self.sessions)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True);self.thread.start();self.addCleanup(self.close)
        self.cookie=None;self.csrf=None

    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(2)

    def transport(self,cfg,path,q):
        self.calls.append((path,copy.deepcopy(q),cfg['credential']))
        if path=='/preview/session':return SessionPorts(self.path).invoke(cfg['credential'],q)
        if path==observation.ROUTE:return observation.invoke(self.path,self.state,self.run,cfg['credential'],q)
        if path=='/preview/subscriptions':
            from integration.single_node.pilot_subscription_ports import invoke
            return invoke(self.path,cfg['credential'],q)
        if path=='/preview/capabilities':
            from integration.single_node.integrated_permissions import invoke
            return invoke(self.path,self.state,self.run,cfg['credential'],q)
        raise AssertionError(path)

    def request(self,path='/',body=None,*,cookie=True,csrf=True,headers=None):
        method='GET' if body is None else 'POST';raw=None if body is None else canonical(body)
        selected={'Host':'127.0.0.1:'+str(self.port)}
        if cookie and self.cookie:selected['Cookie']=self.cookie
        if method=='POST':
            selected.update(Origin='http://127.0.0.1:'+str(self.port),**{'Content-Type':'application/json','Content-Length':str(len(raw))})
            if csrf and self.csrf:selected['X-Omega-CSRF']=self.csrf
        if headers:selected.update(headers)
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=3)
        try:
            conn.request(method,path,body=raw,headers=selected);res=conn.getresponse();data=res.read()
            return res.status,dict(res.getheaders()),data
        finally:conn.close()

    def login(self,user='alice'):
        bootstrap=self.bootstrap if user=='alice' else 'fixture-bootstrap-'+user+'-'+'b'*32
        status,headers,data=self.request('/api/login',dict(user=user,credential=bootstrap),cookie=False,csrf=False)
        self.assertEqual(status,200,data);self.cookie=headers['Set-Cookie'].split(';')[0];self.csrf=json.loads(data)['csrf']
        return headers,json.loads(data)

    def allocate(self,key='allocation'):
        with self.workbench.as_user('alice'):
            return self.workbench.action(dict(role='omega-agent',session='',operation='allocate',identity=key,template='shared'))['session']

    def submission(self,sid,key='input'):
        with self.workbench.as_user('alice'):
            catalogue=self.workbench.capabilities(dict(role='omega-agent',session=sid))['catalogue']
        return dict(role='omega-agent',session=sid,operation='submit',identity=key,text='pin note Synthetic memory',assignment=self.cfg['native_sessions']['assignments'][0],catalogue=catalogue)

    def test_cookie_csrf_logout_and_no_credentials_in_public_document(self):
        status,headers,document=self.request();self.assertEqual(status,200)
        for secret in (self.bootstrap,self.scope,str(self.path),'fixture-service-alice'):self.assertNotIn(secret.encode(),document)
        headers,auth=self.login();self.assertIn('HttpOnly',headers['Set-Cookie']);self.assertIn('SameSite=Strict',headers['Set-Cookie'])
        self.assertEqual(auth['role'],'developer');self.assertFalse(auth['expiry_renewal'])
        self.assertEqual(self.request('/api/state')[0],200)
        self.assertEqual(self.request('/api/logout',{},csrf=False)[0],400)
        self.assertEqual(self.request('/api/logout',{})[0],200)
        self.assertEqual(self.request('/api/state')[0],400)

    def test_unauthorized_second_user_csrf_cross_origin_and_bearer_refuse_without_owner(self):
        self.login();before=len(self.calls)
        attempts=[('/api/login',dict(user='bob',credential=self.bootstrap),{}),
            ('/api/logout',{}, {'X-Omega-CSRF':'wrong'}),('/api/logout',{}, {'Origin':'https://evil.invalid'}),
            ('/api/state',None, {'Authorization':'Bearer '+self.bootstrap}),('/api/state',None, {'Sec-Fetch-Site':'cross-site'})]
        for path,body,headers in attempts:self.assertEqual(self.request(path,body,headers=headers)[0],400)
        self.assertEqual(len(self.calls),before)

    def test_policy_rotation_revokes_existing_session_without_deadline_renewal(self):
        self.login();first=json.loads(self.request('/api/auth')[2])
        self.assertEqual(json.loads(self.request('/api/auth')[2])['expires_ms'],first['expires_ms'])
        self.browser_cfg['users']['alice']['revision']+=1;self.browser_path.write_bytes(canonical(self.browser_cfg))
        self.assertEqual(self.request('/api/state')[0],400)
        self.login();self.assertEqual(self.request('/api/state')[0],200)
        self.browser_cfg['users']['alice']['enabled']=False;self.browser_path.write_bytes(canonical(self.browser_cfg))
        self.assertEqual(self.request('/api/state')[0],400)

    def test_finite_expiry_clock_regression_and_session_capacity(self):
        now=[100.0];sessions=Sessions(self.browser_path,clock=lambda:now[0],wall=lambda:100000)
        token,_=sessions.login('alice',self.bootstrap)
        now[0]=160
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):sessions.authenticate('omega_pilot='+token)
        now[0]=159
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):sessions.login('alice',self.bootstrap)
        now[0]=200
        for _ in range(4):sessions.login('alice',self.bootstrap)
        with self.assertRaisesRegex(ContractError,'OVERLOADED'):sessions.login('alice',self.bootstrap)

    def test_scope_filtered_inventory_counts_and_foreign_session_refusal(self):
        sid=self.allocate();self.login('bob');status,_,raw=self.request('/api/state');self.assertEqual(status,200)
        self.assertNotIn(sid.encode(),raw);self.assertNotIn(self.scope.encode(),raw)
        inv=json.loads(raw)['agents']['omega-agent'];self.assertEqual(inv['sessions'],{});self.assertEqual(set(inv['templates']),{'private'})
        denied=self.request('/api/session?role=omega-agent&session='+sid+'&after=0')
        self.assertEqual(denied[0],400);self.assertEqual(json.loads(denied[2]),{'error':'UNAUTHORIZED'})
        self.assertNotIn(sid.encode(),denied[2])

    def test_browser_principal_cannot_complete_or_allocate_foreign_template(self):
        sid=self.allocate();credential=self.cfg['principals']['browser-alice']['credential']
        for op,body in [('complete',dict(session=sid,identity='forged',result={})),('allocate',dict(identity='forged',template='private'))]:
            with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
                SessionPorts(self.path).invoke(credential,dict(id='forged',profile='omega-native-sessions/3',operation=op,body=body))
        self.assertNotEqual(credential,self.cfg['principals']['operator']['credential'])

    def test_lost_acceptance_replay_same_deadline_and_actor_bound_identity(self):
        sid=self.allocate();body=self.submission(sid);self.login()
        original=self.transport
        def lose(cfg,path,q):
            result=original(cfg,path,q)
            if path=='/preview/session' and q['operation']=='submit':raise ContractError('NOT_AVAILABLE')
            return result
        with patch('integration.single_node.pilot_workbench.invoke',side_effect=lose):self.assertEqual(self.request('/api/action',body)[0],400)
        status,_,raw=self.request('/api/session?role=omega-agent&session='+sid+'&after=0');first=json.loads(raw)['inputs'][0]
        self.assertEqual(self.request('/api/action',body)[0],200)
        later=json.loads(self.request('/api/session?role=omega-agent&session='+sid+'&after=0')[2])['inputs']
        self.assertEqual(len(later),1);self.assertEqual(later[0]['deadline'],first['deadline']);self.assertEqual(later[0]['id'],first['id'])
        with self.workbench.as_user('alice'):a=self.workbench.identity('submit','input')
        with self.workbench.as_user('operator'):b=self.workbench.identity('submit','input')
        self.assertNotEqual(a,b)

    def test_stale_catalogue_and_viewer_mutation_refuse_before_submission(self):
        sid=self.allocate();body=self.submission(sid);self.login();body['catalogue']='stale'
        self.assertEqual(self.request('/api/action',body)[0],400)
        self.assertFalse(any(q['operation']=='submit' for path,q,_ in self.calls if path=='/preview/session'))
        self.login('bob');self.assertEqual(self.request('/api/action',body)[0],400)

    def test_current_owner_revocation_and_response_actor_binding(self):
        sid=self.allocate();self.login();self.cfg['principals']['browser-alice']['scopes'][self.scope]=[];self.path.write_bytes(canonical(self.cfg))
        self.assertEqual(self.request('/api/session?role=omega-agent&session='+sid+'&after=0')[0],400)
        with self.workbench.as_user('alice'),patch('integration.single_node.pilot_workbench.invoke',return_value={'actor':'operator'}):
            with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):self.workbench.state()

    def test_bounded_backpressure_does_not_wait_or_accept(self):
        self.login();self.workbench.lock.acquire()
        try:
            start=time.monotonic();status,_,raw=self.request('/api/state')
            self.assertLess(time.monotonic()-start,1);self.assertEqual(status,400);self.assertEqual(json.loads(raw),{'error':'OVERLOADED'})
        finally:self.workbench.lock.release()

    def test_reconnect_reads_saved_fixture_capture_without_new_admission(self):
        sid=self.allocate();body=self.submission(sid);self.login();self.assertEqual(self.request('/api/action',body)[0],200)
        # This is explicitly a test-owned completion, not a native tool claim.
        with self.workbench.as_user('alice'):iid=self.workbench.identity('submit','input')
        from fusion.sustained_sessions import SustainedSessionStore
        store=SustainedSessionStore(self.cfg['native_sessions']['database'],lambda *_:None,self.cfg['native_sessions']['allocation'])
        store.next_input('A',sid);store.complete('A',sid,iid,dict(turn=1,projection='<script>INERT_AUTHORED_FIXTURE</script>',occurrences=[]));store.close()
        path='/api/session?role=omega-agent&session='+sid+'&after=0'
        first=self.request(path)[2];self.request('/api/logout',{});self.login();second=self.request(path)[2]
        self.assertEqual(first,second)
        self.assertEqual(sum(q.get('operation')=='submit' for _,q,_ in self.calls),1)

    def test_browser_subscription_reconnect_uses_owner_cursor_and_refuses_wrong_session(self):
        self.cfg['native_sessions']['pilot_subscriptions']='application-commit-subscription/1';self.path.write_bytes(canonical(self.cfg))
        sid=self.allocate();other=self.allocate('second');self.login()
        body=dict(role='omega-agent',session=sid,operation='create',subscription='browser-view',action='create',body=dict(session=sid,lifetime_ms=5000))
        self.assertEqual(self.request('/api/subscriptions',body)[0],200)
        accepted=self.request('/api/action',self.submission(sid));self.assertEqual(accepted[0],200)
        read=dict(body,operation='read',action=None,body={'limit':16})
        status,_,raw=self.request('/api/subscriptions',read);self.assertEqual(status,200);hints=json.loads(raw)
        self.assertEqual(hints['events'][0]['state'],'accepted');self.assertFalse(hints['notifications_are_results'])
        self.assertEqual(self.request('/api/subscriptions',dict(read,session=other))[0],400)
        self.request('/api/logout',{});self.login();self.assertEqual(json.loads(self.request('/api/subscriptions',read)[2]),hints)
        self.assertEqual(sum(q.get('operation')=='submit' for _,q,_ in self.calls),1)

    def test_provider_credential_rotation_preserves_browser_session_but_uses_current_actor(self):
        sid=self.allocate();self.login();target=self.browser_cfg['users']['alice']['targets']['omega-agent'];path=Path(target['credential_file'])
        old=path.read_text();new='rotated-scoped-provider-'+'r'*32
        path.write_text(new);self.cfg['principals']['browser-alice']['credential']=new;self.path.write_bytes(canonical(self.cfg))
        self.assertEqual(self.request('/api/session?role=omega-agent&session='+sid+'&after=0')[0],200)
        self.assertEqual(self.calls[-1][2],new)
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):
            SessionPorts(self.path).invoke(old,dict(id='old',profile='omega-native-sessions/3',operation='binding',body={'session':sid}))
    def test_cleanup_requires_operator_and_explicit_separate_provider_selection(self):
        sid=self.allocate();self.login();body=dict(role='omega-agent',session=sid,operation='planCleanup',args=[{},[]])
        self.assertEqual(self.request('/api/search-maintenance',body)[0],400)
        self.login('operator');status,_,raw=self.request('/api/search-maintenance',body)
        self.assertEqual(status,400);self.assertEqual(json.loads(raw)['error'],'UNSUPPORTED_PROFILE')
        self.assertFalse(any('search-operator' in credential for _,_,credential in self.calls))

    def test_cleanup_broker_uses_exact_separate_scope_and_actor_identity(self):
        sid=self.allocate();target=self.browser_cfg['users']['operator']['targets']['omega-agent']
        credential=self.root/'browser-search-token';credential.write_text('SEARCH_ONLY_FIXTURE_'+'s'*32)
        target['search_maintenance']=dict(profile='expired-unpublished-search-reclamation/1',endpoint=target['endpoint'],credential_file=str(credential))
        self.browser_path.write_bytes(canonical(self.browser_cfg));self.login('operator')
        plan={'plan':{'scope':self.scope},'plan_sha256':'EXPLICIT_PLAN_FIXTURE'}
        body=dict(role='omega-agent',session=sid,operation='applyCleanup',args=[{},plan,'stable-cleanup'])
        with patch('fusion.pilot_search_maintenance.Client') as client:
            client.return_value.call.return_value={'boundary':'MAINTENANCE_CLIENT_FIXTURE'}
            self.assertEqual(self.request('/api/search-maintenance',body)[0],200)
            cfg=client.call_args.args[0];self.assertEqual(cfg['principal'],'browser-operator')
            self.assertEqual(cfg['credential'],credential.read_text());self.assertEqual(cfg['scope'],self.scope)
            self.assertEqual(client.return_value.call.call_args.args[0],'applyCleanup')
            with self.workbench.as_user('operator'):expected=self.workbench.identity('search-cleanup','stable-cleanup')
            self.assertEqual(client.return_value.call.call_args.args[-1],expected)
            calls=client.call_count
            foreign=dict(body,args=[{},dict(plan,plan={'scope':'synthetic-other'}),'stable-cleanup'])
            self.assertEqual(self.request('/api/search-maintenance',foreign)[0],400);self.assertEqual(client.call_count,calls)

    def test_real_same_host_https_session_ports_with_distinct_credentials(self):
        import ssl,subprocess
        from http.server import BaseHTTPRequestHandler
        from fusion.preview_client import strict_json
        from integration.single_node import pilot_workbench
        certificate=self.root/'browser-ca.crt';key=self.root/'browser-ca.key'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(certificate),
            '-days','1','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
        fixture_transport=self.transport
        class OwnerHandler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_POST(self):
                try:
                    credential=self.headers['Authorization'].removeprefix('Bearer ')
                    q=strict_json(self.rfile.read(int(self.headers['Content-Length'])))
                    value=fixture_transport({'credential':credential},self.path,q)
                except ContractError as error:value={'error':{'code':error.code,'retryable':False}}
                raw=canonical(value);self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        server=ThreadingHTTPServer(('127.0.0.1',0),OwnerHandler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(certificate,key)
        server.socket=ctx.wrap_socket(server.socket,server_side=True)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True);thread.start()
        try:
            self.mock.stop()
            for user in self.browser_cfg['users'].values():user['targets']['omega-agent']['endpoint'].update(port=server.server_address[1],ca_file=str(certificate))
            self.browser_path.write_bytes(canonical(self.browser_cfg))
            sid=self.allocate();self.login();self.assertEqual(self.request('/api/state')[0],200)
            body=self.submission(sid);self.assertEqual(self.request('/api/action',body)[0],200)
            read=json.loads(self.request('/api/session?role=omega-agent&session='+sid+'&after=0')[2]);self.assertEqual(len(read['inputs']),1)
            self.assertTrue(all(credential.startswith('fixture-service-alice-') for _,_,credential in self.calls))
            self.login('bob');self.assertEqual(self.request('/api/session?role=omega-agent&session='+sid+'&after=0')[0],400)
        finally:server.shutdown();server.server_close();thread.join(2)

    def test_page_uses_text_only_descriptor_forms_and_bounded_observation(self):
        document=page(PAGE)
        self.assertNotIn('innerHTML',document);self.assertNotIn('location.hash.slice',document)
        self.assertIn('watchRemaining=150',document);self.assertIn('serial!==observeSerial',document)
        self.assertIn("input.id='toolArg'+i",document);self.assertIn('body.catalogue=effective?.catalogue',document)
        self.assertNotIn("'Authorization':'Bearer '",document)


class BrowserPageStateTests(unittest.TestCase):
    """Execute the shipped JavaScript with a small explicit DOM/network fixture.

    Real-browser validation is separate. No owner, native tool, model or cluster
    runs here. Late HTTP responses and denied logout are deterministic fixtures.
    """
    def javascript(self, scenario):
        import shutil,subprocess
        node=shutil.which('node')
        if node is None:self.skipTest('Node executable unavailable for page state fixture')
        harness=r'''
const vm=require('vm'),fs=require('fs'),assert=require('assert').strict;
const input=JSON.parse(fs.readFileSync(0,'utf8')),elements={},buttons=[];
function element(id=''){return {id,value:'',textContent:'',disabled:false,children:[],events:{},
 replaceChildren(){this.children=[];this.textContent='';this.value=''},
 append(...items){this.children.push(...items);if(items[0]?.tag==='option'&&!this.value)this.value=items[0].value},
 addEventListener(name,fn){(this.events[name]??=[]).push(fn)},focus(){},click(){return this.onclick?.()},className:''}}
for(const match of input.html.matchAll(/<([\w-]+)[^>]*\bid="([^"]+)"/g)){let e=element(match[2]);elements[e.id]=e;if(match[1]==='button')buttons.push(e)}
const saved=new Map(),storage={getItem:k=>saved.get(k)??null,setItem:(k,v)=>saved.set(k,String(v)),removeItem:k=>saved.delete(k)};
const response=(value,ok=true)=>({ok,json:async()=>value});let handle=async()=>response({error:'UNAUTHORIZED'},false);
const context=vm.createContext({document:{getElementById:id=>{assert(elements[id],id);return elements[id]},querySelectorAll:s=>{assert.equal(s,'button');return buttons},createElement:tag=>Object.assign(element(),{tag})},
 location:{hash:'',pathname:'/'},history:{replaceState(){}},sessionStorage:storage,crypto:require('crypto').webcrypto,
 setTimeout,clearTimeout,performance,URLSearchParams,Date,Blob,URL,confirm:()=>true,
 fetch:(...args)=>handle(...args),assert,fixture:{elements,saved,buttons,response,setHandle(fn){handle=fn}},console});
(async()=>{vm.runInContext(input.html.match(/<script>([\s\S]*?)<\/script>/)[1],context);await new Promise(r=>setImmediate(r));
 await vm.runInContext('(async()=>{'+input.scenario+'})()',context);console.log('PASS')})().catch(e=>{console.error(e);process.exitCode=1});
'''
        result=subprocess.run([node,'-e',harness],input=json.dumps(dict(html=page(PAGE),scenario=scenario)),text=True,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual(result.stdout.strip(),'PASS')

    def test_denied_and_unavailable_logout_clear_all_rendered_state_and_controls(self):
        self.javascript(r'''
for(let unavailable of [false,true]){
 csrf='csrf-fixture';browserRole='operator';browserUser='alice';inventory={private:'AUTHORED_PRIVATE_FIXTURE'};
 for(let id of ['events','notice','workflowState','explorerState','subscriptionState','currentState'])el(id).textContent='AUTHORED_PRIVATE_FIXTURE';
 for(let id of ['text','target','occurrence','cleanupGenerations','workflowId','access','user'])el(id).value='AUTHORED_PRIVATE_FIXTURE';
 el('modelMode').textContent='OLD_SELECTION';watchTimer=setTimeout(()=>assert.fail('observer continued'),1000);watchRemaining=10;
 fixture.setHandle(async()=>{if(unavailable)throw Error('OFFLINE_FIXTURE');return fixture.response({error:'UNAUTHORIZED'},false)});
 await el('logout').onclick();assert.equal(browserUser,'');assert.equal(csrf,'');assert.equal(watchRemaining,0);
 for(let id of ['events','workflowState','explorerState','subscriptionState','currentState'])assert.equal(el(id).textContent,'',id);
 for(let id of ['text','target','occurrence','cleanupGenerations','workflowId','access','user'])assert.equal(el(id).value,'',id);
 assert(!el('notice').textContent.includes('AUTHORED_PRIVATE_FIXTURE'));assert(el('notice').textContent.includes('not confirmed'));
 assert.equal(el('modelMode').textContent,'Model selection not observed');
 assert(fixture.buttons.every(b=>b.disabled===!['connect','logout'].includes(b.id)));
}
''')

    def test_user_bound_action_and_decision_identity_survive_logout_without_payload_storage(self):
        self.javascript(r'''
const auth={user:'operator',role:'operator',csrf:'csrf-fixture',expires_ms:200000};
fixture.setHandle(async path=>fixture.response(path==='/api/state'?{agents:{},services:[],namespace:'synthetic'}:{}));
await signedIn(auth);el('key').value='accepted-action-key';retainActionKey();
const key='omega-pilot-workflow-decision/operator/agent/session/workflow/checkpoint';
const decision={identity:'accepted-decision',action:'approve',binding_sha256:'fixture-binding'};sessionStorage.setItem(key,JSON.stringify(decision));
const sub='omega-pilot-subscription/operator/agent/session';sessionStorage.setItem(sub,'accepted-subscription');
el('text').value='AUTHORED_PRIVATE_PAYLOAD';await el('logout').onclick();
assert.equal(el('text').value,'');assert.equal(sessionStorage.getItem(key),JSON.stringify(decision));assert.equal(sessionStorage.getItem(sub),'accepted-subscription');
await signedIn({...auth,user:'another-user',csrf:'another-csrf'});assert.notEqual(el('key').value,'accepted-action-key');await el('logout').onclick();
await signedIn(auth);assert.equal(el('key').value,'accepted-action-key');assert.equal(sessionStorage.getItem(key),JSON.stringify(decision));
assert(!JSON.stringify([...fixture.saved]).includes('AUTHORED_PRIVATE_PAYLOAD'));
''')

    def test_late_response_and_interrupted_login_cannot_repopulate_signed_out_view(self):
        self.javascript(r'''
let release;fixture.setHandle(()=>new Promise(resolve=>release=resolve));
csrf='old-csrf';browserUser='alice';const old=api('/api/session?fixture').catch(e=>e.message);clearView();release(fixture.response({private:'LATE_FIXTURE'}));
assert((await old).includes('discarded older observation.'));assert.equal(el('events').textContent,'');
fixture.setHandle(()=>new Promise(resolve=>release=resolve));const login=signedIn({user:'alice',role:'operator',csrf:'new-csrf',expires_ms:200000});
clearView();release(fixture.response({agents:{},services:[],namespace:'LATE_NAMESPACE'}));await login;
assert.equal(browserUser,'');assert.equal(csrf,'');assert.equal(el('namespace').textContent,'');assert.equal(el('authState').textContent,'Signed out');assert(el('submit').disabled);
''')


if __name__=='__main__':unittest.main()
