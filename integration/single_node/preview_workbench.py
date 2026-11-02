"""Loopback operator workbench over the installed native session client.

Only task-owned namespaces and named agent/session actions. The browser never
receives credentials, kubeconfig, foreign journals or an execution shell.
"""
import argparse,json,threading,subprocess,secrets,hmac,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse,parse_qs
from fusion.contracts import canonical,require,ContractError
from fusion.preview_client import strict_json
from .reference_ops import Operator,PYTHON

PAGE=r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Omega developer workbench</title><style>
:root{font:15px/1.5 system-ui,sans-serif;color:#18302f;background:#edf2f0}*{box-sizing:border-box}body{margin:0}header{background:#102e2d;color:white;padding:24px 5vw}header small{color:#b4d7cd}h1{font-size:26px;margin:2px 0}h2{font-size:18px;margin-top:0}main{max-width:1350px;margin:24px auto;padding:0 24px;display:grid;grid-template-columns:320px 1fr;gap:20px}.card{background:white;border:1px solid #cfddda;border-radius:10px;padding:20px;margin-bottom:16px;min-width:0}.pill{display:inline-block;border-radius:20px;background:#e2f4eb;color:#205945;padding:3px 10px;margin:3px;font-size:12px}.warn{background:#fff1ce;color:#684500}button,select,input,textarea{font:inherit;border:1px solid #a7bbb6;border-radius:6px;padding:9px}button{background:#e8f3ee;cursor:pointer}button.primary{background:#175b4b;color:white}button:hover{filter:brightness(.95)}button:disabled{opacity:.55;cursor:wait}label{display:block;margin:12px 0 5px}select,input,textarea{width:100%;background:white}textarea{min-height:90px;resize:vertical}.row{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.metrics{display:flex;gap:18px;margin:12px 0}.metrics b{font-size:25px;display:block}.metrics span{font-size:12px;color:#536b64}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f7f6;padding:12px;border-radius:6px;max-height:440px;overflow:auto;font-size:12px}details{border-top:1px solid #dae3df;padding:12px 0}summary{cursor:pointer}#notice{padding:12px;border-left:4px solid #537b68;background:#e7f1ea;overflow-wrap:anywhere}#notice.error{border-color:#ae4c37;background:#fff0ec}small{color:#586f67}.heading{display:flex;align-items:center;justify-content:space-between}.muted{color:#60736b}.service{padding:6px 0;display:flex;justify-content:space-between;border-bottom:1px solid #edf1ef}@media(max-width:850px){main{grid-template-columns:1fr}header{padding:20px 24px}}
</style><header><small>OMEGA · BOUNDED SINGLE-NODE PREVIEW</small><h1>Developer workbench</h1><div id="namespace"></div><span class="pill">Recorded model proposals</span><span class="pill">Live generations: 0</span><span class="pill warn">Synthetic data only</span></header>
<main><aside><section class="card"><h2>Operator access</h2><label for="access">Local workbench token</label><input id="access" type="password" autocomplete="off"><button id="connect">Connect</button><small>Separate local access token. Provider credentials remain inside their pods.</small></section><section class="card"><h2>Native sessions</h2><label for="agent">Agent</label><select id="agent"></select><label for="session">Session</label><select id="session"></select><div class="row"><button id="create">Open session</button><button id="refresh">Refresh</button></div><p id="identity" class="muted"></p><details><summary>Selected capabilities</summary><pre id="catalogue"></pre></details></section><section class="card"><h2>Deployed services</h2><div id="services"></div><small>Health checks do not execute tools. One writer per owner.</small></section></aside>
<div><section class="card"><div class="heading"><h2>Session progress</h2><span id="sessionState" class="pill">Choose a session</span></div><div id="notice" role="status">Loading selected deployment…</div><div class="metrics"><div><b id="accepted">—</b><span>Accepted inputs (page if total unavailable)</span></div><div><b id="completed">—</b><span>Committed completions</span></div><div><b id="pending">—</b><span>Incomplete inputs</span></div></div><div class="row"><button id="pause">Pause</button><button id="resume">Resume</button><button id="close">Close session</button><button id="next" disabled>Next result page</button></div><small>Pause and close preserve reservations, original deadlines and effects. Refresh never resubmits work.</small></section>
<section class="card"><h2>Admit a synthetic input</h2><label for="assignment">Assignment</label><select id="assignment"></select><label for="key">Occurrence identity</label><input id="key" autocomplete="off"><small>Keep this identity to observe/retry the same input. A new intentional input needs a new identity.</small><label for="text">Input / authored command proposal</label><textarea id="text" placeholder="pin task Verify the synthetic shipment location"></textarea><div class="row"><button id="submit" class="primary">Submit input</button><button id="newIdentity">New occurrence identity</button></div><small>The selected recorded provider proposes text; native parsing, whole-batch authority and real tools perform the work.</small></section>
<section class="card"><h2>Selected state and causal observations</h2><p>Current owner receipts and retained native results are separate observations. Priority is not evidence weight; withdrawal is not erasure.</p><details><summary>Current policy and remaining capacity</summary><pre id="policyState"></pre></details><details><summary>Memory, lifecycle, relations and history</summary><pre id="knowledgeState"></pre></details><details><summary>Evidence, belief and priority</summary><pre id="cognitionState"></pre></details><details><summary>Tasks, inspection and external effects</summary><pre id="effectState"></pre></details><small id="nextAction"></small><div class="row"><button id="chainObserve">Observe registered chain effect</button></div><pre id="chainState">Chain observation not requested.</pre></section><section class="card"><h2>Captured inputs and results</h2><div id="events">No session selected.</div><details><summary>Worker observation</summary><pre id="worker"></pre></details></section></div></main>
<script>
'use strict';let inventory={},after=0,nextAfter=null,accessToken=decodeURIComponent(location.hash.slice(1));history.replaceState(null,'',location.pathname);const el=id=>document.getElementById(id);const json=v=>JSON.stringify(v,null,2);const set=(id,text)=>el(id).textContent=text;
function note(text,error=false){set('notice',text);el('notice').className=error?'error':''}
async function api(path,body){let headers={'Authorization':'Bearer '+accessToken};if(body)headers['Content-Type']='application/json';let response=await fetch(path,body?{method:'POST',headers,body:JSON.stringify(body)}:{headers});let value=await response.json();if(!response.ok)throw Error(value.error||'Request failed');return value}
function options(id,values){el(id).replaceChildren();for(let value of values){let o=document.createElement('option');o.value=value;o.textContent=value;el(id).append(o)}}
function project(value){let groups={knowledgeState:[],cognitionState:[],effectState:[]};for(let x of value.inputs){let command=x.payload?.text?.split(' ')[0],g=['remember','query','episodes','link','unlink','update','forget'].includes(command)?'knowledgeState':['support','contradict','promote','demote'].includes(command)?'cognitionState':'effectState';groups[g].push({occurrence:x.id,assignment:x.assignment,state:x.state,original_deadline:x.deadline,result:x.result});}for(let [name,items] of Object.entries(groups))set(name,json(items.length?items:{observation:'No records in this selected page; not an absence claim.'}));set('policyState',json({policy:inventory[selected().role]?.policies?.[selected().session],binding:value.binding,capacity:value.capacity||{observation:'Unavailable on this provider version'}}));set('nextAction',value.inputs.some(x=>x.state!=='complete')?'Incomplete or unknown work: observe owner diagnostics before retry. Preserve identity, spent budget and deadline.':'Captured completion is not a claim of factual correctness or chain finality.');}
function selected(){return {role:el('agent').value,session:el('session').value}}
function capabilities(){let a=inventory[selected().role];if(!a)return;set('identity',a.principal+' · '+a.scope);set('catalogue',json(a.catalogues[selected().session]));set('worker',json(a.worker));options('assignment',a.assignments)}
async function observe(reset=false){if(reset)after=0;let q=new URLSearchParams({...selected(),after:String(after)});try{let value=await api('/api/session?'+q);project(value);set('sessionState',value.state);set('accepted',value.capacity?.accepted??value.inputs.length);set('completed',value.capacity?.completed??value.inputs.filter(x=>x.state==='complete').length);set('pending',value.capacity?.pending??value.inputs.filter(x=>x.state!=='complete').length);el('events').replaceChildren();for(let x of value.inputs){let details=document.createElement('details'),summary=document.createElement('summary'),pre=document.createElement('pre');summary.textContent='#'+x.sequence+' · '+x.state+' · '+x.id;pre.textContent=json(x);details.append(summary,pre);el('events').append(details)}nextAfter=value.next_after;el('next').disabled=nextAfter===null;note('Read committed session state. Deadlines and receipts are unchanged.')}catch(e){note(e.message,true)}}
async function act(operation){let body={...selected(),operation,identity:el('key').value};if(operation==='submit'){body.text=el('text').value;body.assignment=el('assignment').value}else if(operation!=='create'){body.identity=crypto.randomUUID()};try{let value=await api('/api/action',body);note(json(value));await observe(true)}catch(e){note(e.message,true)}}
async function load(){try{let state=await api('/api/state');inventory=state.agents;set('namespace',state.namespace);options('agent',Object.keys(inventory));changeAgent();el('services').replaceChildren();for(let x of state.services){let row=document.createElement('div');row.className='service';let name=document.createElement('span'),status=document.createElement('span');name.textContent=x.name;status.textContent=x.ready?'Ready':'Not ready';row.title=x.image+' · '+x.name+'.'+state.namespace+'.svc.cluster.local';row.append(name,status);el('services').append(row)}note('Select and open a bounded native session.')}catch(e){note(e.message,true)}}
function changeAgent(){options('session',Object.keys(inventory[el('agent').value].sessions));capabilities();after=0}
el('chainObserve').onclick=async()=>{try{set('chainState',json(await api('/api/chain?'+new URLSearchParams({role:selected().role}))))}catch(e){note(e.message,true)}};el('agent').onchange=changeAgent;el('session').onchange=()=>{capabilities();observe(true)};for(let action of ['create','submit','pause','resume','close'])el(action).onclick=()=>act(action);el('refresh').onclick=()=>observe(true);el('next').onclick=()=>{after=nextAfter;observe()};el('newIdentity').onclick=()=>el('key').value=crypto.randomUUID();el('key').value=crypto.randomUUID();el('connect').onclick=()=>{accessToken=el('access').value;el('access').value='';load()};if(accessToken)load();else note('Enter the separate local workbench access token.');
</script></html>'''


class Workbench:
    def __init__(self,operator,token=None):
        self.operator=operator;self.lock=threading.Lock();self.agents={};self.token=token or secrets.token_urlsafe(32)
        require(type(self.token) is str and len(self.token)>=32,'UNAUTHORIZED')
    def invoke(self,role,args):
        require(role in ('omega-agent','omega-agent-b') and role in self.agents,'UNAUTHORIZED')
        raw=self.operator.k('exec',role+'-0','--',PYTHON,'-m','integration.single_node.preview_operator',*args,timeout=40)
        return json.loads(raw)
    def state(self):
        items=self.operator.workloads();roles=[x['metadata']['name'] for x in items]
        self.agents={role:{} for role in roles if role in ('omega-agent','omega-agent-b')}
        result={}
        for role in self.agents:result[role]=self.invoke(role,['inventory'])
        self.agents=result
        return dict(namespace=self.operator.namespace,agents=result,services=[dict(name=x['metadata']['name'],
            ready=x.get('status',{}).get('readyReplicas',0)==1,image=x['spec']['template']['spec']['containers'][0]['image']) for x in items],
            additional_live_generations=0)
    def chain(self,role):
        require(role in self.agents,'UNAUTHORIZED')
        return self.invoke(role,['chain-observe'])
    def selected(self,body):
        require(type(body) is dict and type(body.get('role')) is str and type(body.get('session')) is str)
        require(body['role'] in self.agents and body['session'] in self.agents[body['role']]['sessions'],'UNAUTHORIZED')
    def observe(self,body):
        self.selected(body);after=body.get('after',0);require(type(after) is int and 0<=after<=32)
        return self.invoke(body['role'],['observe','--session',body['session'],'--content','--after',str(after)])
    def action(self,body):
        self.selected(body);op=body.get('operation');require(op in ('create','submit','pause','resume','close'),'UNSUPPORTED_OPERATION')
        require(set(body)=={'role','session','operation','identity'}|({'text','assignment'} if op=='submit' else set()))
        args=[op,'--session',body['session']]
        if op!='create':
            require(type(body['identity']) is str and 0<len(body['identity'])<=128);args+=['--identity',body['identity']]
        if op=='submit':
            require(type(body['text']) is str and 0<len(body['text'].encode())<=4096)
            require(body['assignment'] in self.agents[body['role']]['assignments'],'UNAUTHORIZED')
            args+=['--text',body['text'],'--assignment',body['assignment']]
        return self.invoke(body['role'],args)


def handler(workbench,port):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup();self.connection.settimeout(3)
        def log_message(self,*_):pass
        def reply(self,value,status=200,html=False):
            raw=PAGE.encode() if html else canonical(value);self.send_response(status)
            self.send_header('Content-Type','text/html; charset=utf-8' if html else 'application/json')
            self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; connect-src 'self'")
            self.end_headers();self.wfile.write(raw)
        def process(self,post=False):
            try:
                require(len(self.headers.get_all('Host',[]))==1 and not self.headers.get_all('Transfer-Encoding',[]),'UNAUTHORIZED')
                require(self.headers.get('Host') in ('127.0.0.1:'+str(port),'localhost:'+str(port)),'UNAUTHORIZED')
                require(self.client_address[0]=='127.0.0.1','UNAUTHORIZED')
                parsed=urlparse(self.path)
                if parsed.path.startswith('/api/'):
                    auth=self.headers.get_all('Authorization',[])
                    require(len(auth)==1 and hmac.compare_digest(auth[0],'Bearer '+workbench.token),'UNAUTHORIZED')
                body=None
                if post:
                    require(len(self.headers.get_all('Origin',[]))==1 and len(self.headers.get_all('Content-Length',[]))==1 and len(self.headers.get_all('Content-Type',[]))==1)
                    require(self.headers.get('Origin') in ('http://127.0.0.1:'+str(port),'http://localhost:'+str(port)),'UNAUTHORIZED')
                    require(self.headers.get('Content-Type')=='application/json','UNSUPPORTED_OPERATION')
                    size=int(self.headers.get('Content-Length','0'));require(0<size<=16384)
                    raw=self.rfile.read(size);require(len(raw)==size)
                    body=strict_json(raw);require(type(body) is dict)
                with workbench.lock:
                    if post:
                        require(self.headers.get('Origin') in ('http://127.0.0.1:'+str(port),'http://localhost:'+str(port)),'UNAUTHORIZED')
                        require(parsed.path=='/api/action' and self.headers.get('Content-Type')=='application/json','UNSUPPORTED_OPERATION')
                        self.reply(workbench.action(body))
                    elif parsed.path=='/':self.reply(None,html=True)
                    elif parsed.path=='/api/state':self.reply(workbench.state())
                    elif parsed.path=='/api/chain':
                        args=parse_qs(parsed.query);require(set(args)=={'role'} and len(args['role'])==1)
                        self.reply(workbench.chain(args['role'][0]))
                    elif parsed.path=='/api/session':
                        args=parse_qs(parsed.query);require(set(args)=={'role','session','after'} and all(len(v)==1 for v in args.values()))
                        self.reply(workbench.observe(dict(role=args['role'][0],session=args['session'][0],after=int(args['after'][0]))))
                    elif parsed.path=='/favicon.ico':self.reply({})
                    else:self.reply({'error':'NOT_FOUND'},404)
            except (ContractError,ValueError,RuntimeError,TimeoutError,KeyError,TypeError,OSError,subprocess.SubprocessError) as error:
                self.reply({'error':error.code if isinstance(error,ContractError) else 'NOT_AVAILABLE'},400)
        def do_GET(self):self.process()
        def do_POST(self):self.process(True)
    return Handler


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kubeconfig',required=True);p.add_argument('--context',required=True);p.add_argument('--namespace',required=True);p.add_argument('--port',type=int,default=8768);p.add_argument('--access-file',required=True,help='New private file for the separate local access token')
    a=p.parse_args();require(1024<=a.port<=65535)
    require(a.namespace not in ('omega-demo','omega-ref-live01'),'UNAUTHORIZED')
    owner=Operator(a.kubeconfig,a.context,a.namespace);owner.owned()
    workbench=Workbench(owner)
    access=Path(a.access_file);access.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(access,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w') as file:file.write(workbench.token+'\n')
    server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(workbench,a.port))
    print('Omega synthetic operator workbench: http://127.0.0.1:'+str(a.port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
