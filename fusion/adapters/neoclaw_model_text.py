"""Pure pinned native text mapping. No model client, effects or runtime selection.

The original request-building statements and create() keyword expressions are
extracted from checked source. SDK construction, retry loops and unrelated media
code do not run. A future selected backend must independently authorize, reserve
and capture its invocation; this helper cannot establish those guarantees.
"""
import ast
from pathlib import Path

from ..contracts import digest, require
from ..neoclaw_contracts import PINS


class NativeChatText:
    def __init__(self, source):
        source = Path(source)
        require(digest(source.read_bytes()) == PINS['sources']['mettaclaw']['files']['lib_llm_ext.py'],
                'UNSUPPORTED_PROFILE')
        definitions = {node.name: node for node in ast.parse(source.read_text()).body
                       if isinstance(node, ast.FunctionDef)}
        chat = definitions['_chat']
        require(len(chat.body) == 5 and isinstance(chat.body[3], ast.For), 'UNSUPPORTED_PROFILE')
        call = chat.body[3].body[0].value
        require(isinstance(call, ast.Call) and ast.unparse(call.func) == 'client.chat.completions.create',
                'UNSUPPORTED_PROFILE')
        keywords = call.keywords
        require([key.arg for key in keywords] == ['model', 'messages', 'max_tokens', 'extra_body'],
                'UNSUPPORTED_PROFILE')
        body = [*chat.body[:3], ast.Return(ast.Dict(
            keys=[ast.Constant(key.arg) for key in keywords], values=[key.value for key in keywords]))]
        arguments = ast.arguments(posonlyargs=[], args=[ast.arg(arg=x) for x in ('content', 'model')],
                                  kwonlyargs=[], kw_defaults=[], defaults=[])
        # The selected original wrappers all use the native default. The helper
        # has no caller-controlled token, reasoning, model-routing or retry knobs.
        body.insert(0, ast.Assign(targets=[ast.Name(id='max_tokens', ctx=ast.Store())],
                                 value=chat.args.defaults[0]))
        function = ast.FunctionDef(name='request', args=arguments, body=body, decorator_list=[])
        module = ast.fix_missing_locations(ast.Module(body=[function, definitions['_clean']], type_ignores=[]))
        namespace = {}
        exec(compile(module, str(source), 'exec'), namespace)
        self._request, self._clean = namespace['request'], namespace['_clean']
        self.source_sha256 = digest(source.read_bytes())

    def request(self, content, selected_model):
        require(type(content) is str and ':-:-:-:' in content)
        require(type(selected_model) is str and 1 <= len(selected_model) <= 200)
        # selected_model is an operator-side adapter argument, never a native
        # command argument. No backend or endpoint is selected by this helper.
        return self._request(content, selected_model)

    def render(self, text):
        require(type(text) is str)
        return self._clean(text)
