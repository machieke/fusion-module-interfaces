"""Disconnected pinned-tool qualification using a loopback-only authored page.

This is not the H native runner. It never mounts a packet, owner credential,
kubeconfig, operator wheel, corpus or application state. No external networking.
"""
import argparse, ctypes, hashlib, importlib.util, json, os, signal, socket, subprocess, sys, time
from pathlib import Path

HERE=Path(__file__).parent
def check(value,reason):
    if not value:raise RuntimeError(reason)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
def native():
    spec=importlib.util.spec_from_file_location('h21_tools',HERE/'h19-native.py')
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

FIXTURE=r'''from http.server import BaseHTTPRequestHandler,HTTPServer
PAGE=b'<!doctype html><html><title>Disconnected browser tool fixture</title><body><h1>Pinned browser fixture</h1><p>This page tests tools only; no Omega owner is present.</p><button id="toggle" onclick="document.getElementById(\'status\').textContent=\'clicked\'">Test fixture control</button><p id="status">ready</p></body></html>'
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(PAGE)));self.end_headers();self.wfile.write(PAGE)
HTTPServer(('127.0.0.1',18081),Handler).serve_forever()
'''

def inside():
    N=native();root=Path('/results');end=time.monotonic()+150
    report=dict(status='RUNNING',classification='DISCONNECTED_REAL_TOOLS_AUTHORED_LOOPBACK_PAGE',cluster_operations=0,native_submissions=0,additional_live_generations=0,network='ISOLATED_LOOPBACK_ONLY',commands=[])
    (root/'fixture_server.py').write_text(FIXTURE)
    save(root/'proofshot.config.json',dict(output=str(root/'proof')))
    def run(label,args,expected=0,seconds=40):
        remaining=end-time.monotonic();check(remaining>0,'original tool window expired')
        r=subprocess.run(args,cwd=root,capture_output=True,text=True,timeout=min(seconds,remaining))
        row=dict(label=label,args=args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
        report['commands'].append(row);save(root/'report.json',report)
        check(r.returncode==expected,label+' failed');return r.stdout.strip()
    started=False;server=None;server_out=None
    try:
        check(not Path('/home/purplezky').exists() and not Path('/credentials').exists(),'host authority exposed')
        check(Path('/node/bin/agent-browser').is_symlink() and not Path('/node/bin/agent-browser').exists(),'old absolute symlink failure no longer reproduced')
        check(sha('/browser-bin/agent-browser')==N.BROWSER_EXECUTABLE['sha256'],'binary drift')
        run('legacy-symlink-refusal',['/bin/sh','-c','PATH=/node/bin:/usr/bin:/bin agent-browser --version'],expected=127)
        run('native-precluster-preflight',N.browser_tool_args(),seconds=30)
        # This explicit fixture server uses file logs; ProofShot --run keeps
        # its dev-server pipe handles live in the selected version. The native
        # recipe likewise uses an already started operator port-forward.
        server_out=(root/'fixture-server.log').open('xb')
        server=subprocess.Popen(['/python/bin/python3','-I','/results/fixture_server.py'],stdout=server_out,stderr=server_out)
        until=min(end,time.monotonic()+5)
        while True:
            check(server.poll()is None and time.monotonic()<until,'fixture server unavailable')
            with socket.socket()as probe:
                if probe.connect_ex(('127.0.0.1',18081))==0:break
            time.sleep(.05)
        prefix=['/node/bin/proofshot']
        started=True
        run('proofshot-start',prefix+['start','--port','18081','--description','Disconnected pinned tools with an authored fixture page; no Omega services'])
        before=run('fixture-before',prefix+['exec','snapshot','-i']);check('Test fixture control'in before,'fixture page absent')
        run('fixture-before-screenshot',prefix+['exec','screenshot','/results/before.png'])
        run('fixture-click',prefix+['exec','click','#toggle'])
        actual=run('fixture-result',prefix+['exec','eval',"document.getElementById('status').textContent"]);check(actual=='"clicked"','fixture control did not execute')
        run('fixture-after-screenshot',prefix+['exec','screenshot','/results/after.png'])
        run('proofshot-stop',prefix+['stop']);started=False
        report['status']='PASS'
    except BaseException as error:
        report.update(status='FAIL_RETAINED',failure=dict(type=type(error).__name__,message=str(error)));raise
    finally:
        if started:
            try:run('proofshot-cleanup',['/node/bin/proofshot','stop'],seconds=25)
            except BaseException as error:report['cleanup_error']=dict(type=type(error).__name__,message=str(error))
        if server is not None:
            server.terminate()
            try:server.wait(timeout=3)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=3)
            report['fixture_server_stopped']=True
        if server_out is not None:server_out.close()
        save(root/'report.json',report)

def outer(output):
    N=native();p=N.B.load(HERE/'plan.DISABLED.json');out=Path(output).resolve()
    check(not out.exists(),'prior tool qualification output exists');out.mkdir(mode=0o700)
    node=Path(p['asset_trees']['node']['path']);chrome=Path(p['asset_trees']['chrome']['path']);prefix=Path(p['python_prefix'])
    check(sha(node/N.BROWSER_EXECUTABLE['path_in_node'])==N.BROWSER_EXECUTABLE['sha256'],'unpinned executable')
    for name in ('node','chrome'):
        row=p['asset_trees'][name];root=Path(row['path']);actual={str(f.relative_to(root)):sha(f)for f in root.rglob('*')if f.is_file()}
        check(len(actual)==row['files']and hashlib.sha256(N.B.canonical(actual)).hexdigest()==row['manifest_sha256'],'asset tree drift '+name)
    args=['/usr/bin/bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/home','--dir','/helpers']
    for system in ('/usr','/lib','/lib64','/bin','/sbin'):args+=['--ro-bind',system,system]
    args+=['--ro-bind',str(node),'/node','--ro-bind',str(chrome),'/chrome','--dir','/browser-bin','--ro-bind',str(node/N.BROWSER_EXECUTABLE['path_in_node']),'/browser-bin/agent-browser','--ro-bind',str(prefix),'/python','--bind',str(out),'/results']
    for name in ('h19-native.py','h19-adopter-namespace.py','qualify_browser_tools.py'):args+=['--ro-bind',str(HERE/name),'/helpers/'+name]
    env=dict(PATH='/browser-bin:/node/bin:/usr/bin:/bin',HOME='/tmp/browser-home',PYTHONDONTWRITEBYTECODE='1',AGENT_BROWSER_SESSION='h21-disconnected-tools',AGENT_BROWSER_SOCKET_DIR='/tmp/h21-tool-sockets',AGENT_BROWSER_EXECUTABLE_PATH='/chrome/chrome')
    for key,value in env.items():args+=['--setenv',key,value]
    args+=['--chdir','/results','/python/bin/python3','-I','/helpers/qualify_browser_tools.py','--inside']
    libc=ctypes.CDLL(None,use_errno=True);check(libc.prctl(36,1,0,0,0)==0,'subreaper unavailable')
    report=dict(status='RUNNING',commands=[args],source_sha256=sha(__file__),source_files={name:sha(HERE/name)for name in ('h19-native.py','h19-adopter-namespace.py','qualify_browser_tools.py')},elapsed_seconds=None,cluster_operations=0,native_submissions=0,additional_live_generations=0)
    started=time.monotonic();proc=None;code=1
    try:
        with(out/'launcher.stdout').open('xb')as stdout,(out/'launcher.stderr').open('xb')as stderr:
            proc=subprocess.Popen(args,stdout=stdout,stderr=stderr,start_new_session=True)
            try:code=proc.wait(timeout=165)
            except BaseException:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=3)
                raise
        report.update(status='PASS'if code==0 else'FAIL_RETAINED',exit_code=code)
    finally:
        # The PID namespace has exited; reap adopted helper children as well.
        until=time.monotonic()+5;reaped=0
        while True:
            try:
                pid,_=os.waitpid(-1,os.WNOHANG)
                if pid:reaped+=1;continue
                check(time.monotonic()<until,'descendant reap barrier expired');time.sleep(.05)
            except ChildProcessError:break
        report.update(all_children_reaped=True,adopted_children_reaped=reaped,elapsed_seconds=time.monotonic()-started)
        save(out/'launcher.json',report)
    print(json.dumps(dict(status=report['status'],all_children_reaped=report['all_children_reaped'],additional_live_generations=0)))
    return code

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output');p.add_argument('--inside',action='store_true');a=p.parse_args()
    sys.exit(inside()if a.inside else outer(a.output))
