"""Recorded-response oracle for pinned native text wrappers; never generates text.

Only the exact checked function definitions run. Eager API clients, embeddings,
media and credentials are not imported. This is deterministic compatibility
evidence, not a ModelInference provider or an alternative native startup.
"""
import ast
import json
from pathlib import Path
from types import SimpleNamespace

from fusion.contracts import canonical, digest, require
from fusion.neoclaw_contracts import PINS

WRAPPERS = {
    'useClaude': 'ANTHROPIC_CLIENT',
    'useMiniMax': 'ASI_CLIENT',
    'useOpenRouter': 'OPENROUTER_CLIENT',
}


def functions(source):
    source = Path(source)
    require(digest(source.read_bytes()) == PINS['sources']['mettaclaw']['files']['lib_llm_ext.py'],
            'UNSUPPORTED_PROFILE')
    tree = ast.parse(source.read_text())
    names = {'_chat', '_clean', *WRAPPERS}
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    require({node.name for node in selected} == names, 'UNSUPPORTED_PROFILE')
    return compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec')


def observe(source, wrapper, content, recorded_texts):
    require(wrapper in WRAPPERS and type(content) is str)
    require(type(recorded_texts) is list and 1 <= len(recorded_texts) <= 5)
    require(all(value is None or type(value) is str for value in recorded_texts))
    requests, sleeps = [], []

    def create(**request):
        require(len(requests) < len(recorded_texts), 'NOT_AVAILABLE')
        raw = recorded_texts[len(requests)]
        requests.append(request)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    namespace = {name: client for name in WRAPPERS.values()}
    namespace['time'] = SimpleNamespace(sleep=sleeps.append)
    exec(functions(source), namespace)
    error = None
    try:
        rendered = namespace[wrapper](content)
    except RuntimeError as exc:
        require(str(exc) == 'LLM returned None after all retry attempts', 'NOT_AVAILABLE')
        rendered, error = None, 'NATIVE_NULL_RETRY_EXHAUSTED'
    return dict(classification='RECORDED_RESPONSE_FIXTURE', wrapper=wrapper,
                source_commit=PINS['sources']['mettaclaw']['commit'],
                source_sha256=digest(Path(source).read_bytes()), input=content,
                recorded_texts=recorded_texts, requests=requests,
                rendered=rendered, error=error, helper_sleeps=sleeps,
                sdk_executed=False, live_generation=False)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    cases = [
        ('Synthetic <tool_call>policy</tool_call><arg_value>Ω</arg_value>:-:-:-:Synthetic input:-:-:-:retained',
         ['((send _quote_Synthetic reply Ω_quote_))']),
        ('Synthetic policy:-:-:-:   ', ['((send _quote_Synthetic reply_apostrophe_s_quote_))']),
    ]
    evidence = [observe(args.source, wrapper, content, responses)
                for wrapper in WRAPPERS for content, responses in cases]
    from fusion.adapters.neoclaw_model_text import NativeChatText
    adapter = NativeChatText(args.source)
    for case in evidence:
        case['adapted_request'] = adapter.request(case['input'], case['requests'][0]['model'])
        case['adapted_rendered'] = adapter.render(case['recorded_texts'][0])
        require(case['adapted_request'] == case['requests'][0] and
                case['adapted_rendered'] == case['rendered'], 'CONFLICT')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical(evidence))
    print(json.dumps(dict(classification='RECORDED_RESPONSE_FIXTURE', cases=len(evidence),
                          live_generation=False, source_sha256=digest(args.source.read_bytes()))))


if __name__ == '__main__':
    main()
