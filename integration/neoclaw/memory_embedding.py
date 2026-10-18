"""Source-checked native Local embedding functions, pinned local model directory.

Only model location resolution changes. The original normalized encode function
is compiled unchanged; no query/passage prefixes, eager media or hosted clients.
"""
import ast
import json
from pathlib import Path
from fusion.contracts import digest, require
from fusion import neoclaw_contracts as c

REVISION = 'f169b11e22de13617baa190a028a32f3493550b6'


def load(source, model, hashes):
    source, model = Path(source), Path(model)
    require(hashes == json.loads((Path(__file__).with_name('memory-model.json')).read_text())['files'], 'UNSUPPORTED_PROFILE')
    require(digest(source.read_bytes()) == c.PINS['sources']['mettaclaw']['files']['lib_llm_ext.py'], 'UNSUPPORTED_PROFILE')
    for file, sha in hashes.items():
        require(digest((model/file).read_bytes()) == sha, 'UNSUPPORTED_PROFILE')
    tree = ast.parse(source.read_text())
    nodes = [x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name in ('initLocalEmbedding','useLocalEmbedding')]
    require(len(nodes) == 2, 'UNSUPPORTED_PROFILE')
    class Location(ast.NodeTransformer):
        def visit_Constant(self, node):
            if node.value == 'intfloat/e5-large-v2': return ast.copy_location(ast.Constant(str(model.resolve())), node)
            return node
    module = ast.fix_missing_locations(Location().visit(ast.Module(body=nodes, type_ignores=[])))
    import torch
    torch.set_num_threads(2)
    scope = {'_embedding_model': None}
    exec(compile(module, str(source), 'exec'), scope)
    native = scope['initLocalEmbedding']()
    require(str(native.dtype) == 'torch.float32' and native.get_sentence_embedding_dimension() == 1024, 'UNSUPPORTED_PROFILE')
    return scope['useLocalEmbedding']
