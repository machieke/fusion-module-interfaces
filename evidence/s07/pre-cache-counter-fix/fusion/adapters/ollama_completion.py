"""One pinned Ollama /api/chat call. No SDK, retry, tools or hidden text capture."""
import http.client
import json
from pathlib import Path
import time
from dataclasses import asdict

from fusion import model_contracts as c
from fusion.contracts import ContractError, canonical, digest, require
from fusion.neoclaw_transport import json_loads
from .neoclaw_model_text import NativeChatText

VERSION = '0.40.0+mlx.cpu.1'
BINARY_SHA256 = 'db8d6a16322494d762bf5394d5e5318d48f42e93f9dd44888d48d3a12099d43c'


def exchange(path, body=None, timeout=2, limit=c.MAX_WIRE, *, port=11434):
    c.integer(port, 1, 65535)
    connection = http.client.HTTPConnection('127.0.0.1', port, timeout=timeout)
    try:
        connection.request('GET' if body is None else 'POST', path,
            body=None if body is None else canonical(body), headers={'Content-Type':'application/json'})
        response = connection.getresponse()
        require(response.status == 200, 'NOT_AVAILABLE')
        data = response.read(limit+1); require(len(data) <= limit, 'NOT_AVAILABLE')
        return json_loads(data)
    except (OSError, http.client.HTTPException, ValueError):
        raise ContractError('NOT_AVAILABLE') from None
    finally: connection.close()


def convert(value):
    require(type(value) is dict and value.get('done') is True, 'NOT_AVAILABLE')
    require(value.get('model') == c.MODEL, 'NOT_AVAILABLE')
    require(set(value) <= {'model','created_at','message','done','done_reason','total_duration','load_duration',
        'prompt_eval_count','prompt_eval_duration','eval_count','eval_duration'}, 'NOT_AVAILABLE')
    message = value.get('message')
    require(type(message) is dict and message.get('role') == 'assistant', 'NOT_AVAILABLE')
    require(set(message) <= {'role','content','thinking','tool_calls','images'}, 'NOT_AVAILABLE')
    require(not message.get('tool_calls') and not message.get('images') and not message.get('thinking'), 'NOT_AVAILABLE')
    raw = c.text(message.get('content'), c.MAX_TEXT)
    finish = value.get('done_reason')
    require(finish in ('stop','length'), 'NOT_AVAILABLE')
    result = dict(raw_text=raw, native_text=c.clean(raw), observed_model=value['model'],
        provider_request_id=None, usage=dict(input_tokens=value.get('prompt_eval_count'),
        output_tokens=value.get('eval_count'), reasoning_tokens=None), finish_reason=finish,
        outcome='truncated' if finish == 'length' else 'empty' if not raw.strip() else 'complete',
        durations_ns={k:value.get(v) for k,v in dict(total='total_duration',load='load_duration',
            prompt='prompt_eval_duration',generation='eval_duration').items()})
    return c.completion(result)


class OllamaCompletion:
    def __init__(self, lock):
        # Lock contains paths only to operator-verified public runtime inputs.
        require(type(lock) is dict and set(lock) == {'path','sha256'}, 'UNSUPPORTED_PROFILE')
        data = Path(lock['path']).read_bytes()
        require(digest(data) == lock['sha256'], 'UNSUPPORTED_PROFILE')
        self.runtime = json.loads(data)
        self.port = c.integer(self.runtime.get('port',11434), 1, 65535)
        if 'asset_root' in self.runtime:
            manifest=Path(self.runtime['asset_root'])/'manifests/registry.ollama.ai/library/qwen3.8/27b'
            require(digest(manifest.read_bytes())==c.MODEL_DIGEST,'UNSUPPORTED_PROFILE')
        require(self.runtime['model_digest'] == c.MODEL_DIGEST and self.runtime['version'] == VERSION, 'UNSUPPORTED_PROFILE')
        require(digest(Path(self.runtime['binary']).read_bytes()) == BINARY_SHA256, 'UNSUPPORTED_PROFILE')
        self.native = NativeChatText(self.runtime['native_source'])

    def readiness(self):
        require(exchange('/api/version',port=self.port) == {'version':VERSION}, 'UNSUPPORTED_PROFILE')
        tags = exchange('/api/tags',port=self.port)['models']
        require(any(v['name'] == c.MODEL and v['digest'] == c.MODEL_DIGEST for v in tags), 'UNSUPPORTED_PROFILE')

    def complete(self, accepted):
        value = asdict(accepted); c.intent(value)
        require(accepted.profile == c.CPU_PROFILE or self.port == 11434, 'UNSUPPORTED_PROFILE')
        self.readiness()
        remaining = (accepted.deadline_ms - time.time_ns()//1_000_000)/1000
        require(0 < remaining <= c.deadline_limit(accepted.profile)/1000, 'DEADLINE_EXCEEDED')
        native = self.native.request(accepted.native_prompt, c.MODEL)
        require(native['messages'] == accepted.messages and native['max_tokens'] == 6000, 'UNSUPPORTED_PROFILE')
        request = dict(model=c.MODEL, messages=native['messages'], stream=False, think=False,
            truncate=False, options=dict(c.OPTIONS))
        value = convert(exchange('/api/chat', request, timeout=remaining,port=self.port))
        require(value['native_text'] == self.native.render(value['raw_text']), 'NOT_AVAILABLE')
        return value
