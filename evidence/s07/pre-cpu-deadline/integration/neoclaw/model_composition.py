"""Fresh synthetic S07 composition. Backend and mailbox placement are independent."""
import json
from pathlib import Path
import secrets
import subprocess
import time
from fusion import model_contracts as c
from fusion.contracts import canonical,digest,require
from fusion.registry import descriptor_wire
from .channel_composition import configure as channel_configure,write
from .model_startup import scaffold

EXPRESSION='(Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))'
OUTPUT='Synthetic S07 reply: native calculation observed.'
INPUTS=['Synthetic S07 first request: call metta with '+EXPRESSION+'.',
        'Synthetic S07 second request: inspect the actual tool result above, then send exactly '+OUTPUT]


def configure(run,corpus,placement='local',mailbox='local',*,runtime_lock):
    value=channel_configure(run,corpus,mailbox,inputs=INPUTS,outputs=[OUTPUT]);ch=value['channel']
    root=run.h.root/'completion';root.mkdir(mode=0o700)
    cfg=dict(database=str(root/'model.sqlite'),scope='synthetic-s07',sharing=c.PRIVACY,sessions=[run.app['session_id']],
        max_calls=2,expires_ms=time.time_ns()//1_000_000+600000,
        catalogue=[descriptor_wire(c.descriptor())],runtime_lock=runtime_lock,
        disclosure=dict(scaffold=scaffold(),memories=['()'],
            users=[str(['HUMAN-MSG:','peer: '+text]) for text in INPUTS],feedback_expressions=[EXPRESSION]))
    credential=secrets.token_hex(24)
    policy=dict(model_completion=cfg,principals={'A':dict(credential=credential,scopes={cfg['scope']:
        ['model.'+x for x in ('complete','observe','authorize','disclose')]})},
        test_failpoints=True,failpoint_marker=str(root/'pause.json'))
    policy_path=root/'config.json'
    client={k:cfg[k] for k in ('scope','sharing','catalogue','disclosure')}
    client.update(profile=c.PROFILE,principal='A',session=run.app['session_id'],placement=placement,fallback=False,
        commands=[['metta',EXPRESSION],['send',OUTPUT]],credential=credential)
    if placement=='local':client['provider_config']=str(policy_path)
    else:
        require(placement=='network','UNSUPPORTED_PROFILE')
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'server.key'),
            '-out',str(root/'server.pem'),'-days','1','-subj','/CN=127.0.0.1','-addext','subjectAltName=IP:127.0.0.1'],capture_output=True,check=True)
        (root/'server.key').chmod(0o600)
        policy.update(tls_certificate=str(root/'server.pem'),tls_key=str(root/'server.key'),
            memory_read=dict(denied_paths=[str(run.h.caller_root),str(run.h.server_root),str(ch.provider),str(ch.bridge_root),str(ch.peer_root)]))
        write(policy_path,policy)
        ready=root/'ready.json';host=run.spawn('integration.neoclaw.host',['serve',policy_path,'--ready',ready],'completion-host')
        run.h.wait_file(ready,host)
        ca=run.h.caller_root/'model-ca.pem';ca.write_bytes((root/'server.pem').read_bytes())
        client['endpoint']=dict(host='127.0.0.1',port=json.loads(ready.read_text())['port'],ca_file=str(ca))
        # Model assets, source/build tree and owner state inaccessible in the caller.
        run.app['denied_paths'] += [str(p) for p in [root,Path('/usr/share/ollama'),Path('/home/purplezky/work/takopi/ollama')] if p.exists()]
        run.app['model_denied_files']=['/usr/share/ollama/.ollama/models/blobs/sha256-f5f1dd8920d417aac2718b0bda3403da274301efdd6760b4f0f4b864ff2ad57d',
            '/usr/share/ollama/.ollama/models/manifests/registry.ollama.ai/library/qwen3.8/27b',str(root/'server.key')]
    write(policy_path,policy)
    selected=run.h.caller_root/'completion.json';write(selected,client)
    run.app.pop('model_fixture',None)
    run.app.update(composition=c.APPLICATION,model_config=str(selected),turn_limit=2)
    run.save()
    # Historical helper creates this file only for old fixtures. It is not a
    # supported import or configuration input in the new composition.
    run.model_path.unlink(missing_ok=True)
    value.update(completion_root=root,completion_policy=policy_path,completion_client=selected)
    return value


def runtime_lock(root):
    from .channel_composition import ROOT
    path=Path(root)/'ollama-runtime.json'
    value=dict(binary='/usr/local/bin/ollama',version='0.40.0+mlx.cpu.1',model_digest=c.MODEL_DIGEST,
        native_source=str(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py'))
    write(path,value);return dict(path=str(path.resolve()),sha256=digest(path.read_bytes()))
