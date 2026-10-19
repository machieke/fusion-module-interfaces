"""Task-owned loopback Ollama, exact existing blobs; no download or generation."""
import hashlib,json,os,socket
from pathlib import Path
root=Path.cwd();task=root/'artifacts/s07/isolated-runtime';task.mkdir(mode=0o700)
source=Path('/usr/share/ollama/.ollama/models')
manifest=source/'manifests/registry.ollama.ai/library/qwen3.8/27b'
raw=manifest.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9a8921f5b297f01451509b60e4a7e754674fe40d4a64dd9f89fc4a56c4fc5ee1'
model=json.loads(raw);store=task/'models';(store/'blobs').mkdir(parents=True)
target=store/'manifests/registry.ollama.ai/library/qwen3.8/27b';target.parent.mkdir(parents=True);target.write_bytes(raw)
for item in [model['config'],*model['layers']]:
 name=item['digest'].replace(':','-');(store/'blobs'/name).symlink_to(source/'blobs'/name)
with socket.socket() as s:s.bind(('127.0.0.1',11435))
# HOME retains its actual value; its filesystem is empty and ephemeral here.
# Only this task's approved model links and logs are rebound into that namespace.
args=['bwrap','--die-with-parent','--ro-bind','/','/','--tmpfs',str(Path.home()),'--bind',str(task),str(task),'--proc','/proc','--dev','/dev','--','/usr/local/bin/ollama','serve']
env={k:os.environ[k] for k in ('PATH','HOME','USER','LANG') if k in os.environ}
selected=dict(OLLAMA_HOST='127.0.0.1:11435',OLLAMA_MODELS=str(store),OLLAMA_NO_CLOUD='true',OLLAMA_MAX_LOADED_MODELS='1',OLLAMA_NUM_PARALLEL='1',OLLAMA_KEEP_ALIVE='10m',OLLAMA_CONTEXT_LENGTH='32768')
env.update(selected)
metadata=dict(pid=os.getpid(),argv=args,selected_environment=selected,model_manifest=hashlib.sha256(raw).hexdigest(),binary_sha256=hashlib.sha256(Path('/usr/local/bin/ollama').read_bytes()).hexdigest(),private_home_visible=False,scope='task-owned local runtime; same pinned model and binary; no generation in launcher')
(task/'launch.json').write_text(json.dumps(metadata,indent=2)+'\n');print(json.dumps(metadata),flush=True)
log=os.open(task/'server.log',os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600);os.dup2(log,1);os.dup2(log,2)
os.execvpe(args[0],args,env)
