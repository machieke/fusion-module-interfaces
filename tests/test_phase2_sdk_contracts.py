"""Installed pure DTO surface: no checkout imports, owner or native runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[1]


class InstalledPureContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='fusion-sdk-pure-')
        cls.root = Path(cls.temporary.name)
        subprocess.run([sys.executable, str(ROOT / 'sdk/build.py'), '--output', str(cls.root / 'wheels')],
                       check=True, capture_output=True)
        venv.create(cls.root / 'venv', with_pip=True)
        cls.python = cls.root / 'venv/bin/python'
        cls.environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
        cls.environment['PYTHONNOUSERSITE'] = '1'
        subprocess.run([str(cls.python), '-I', '-m', 'pip', 'install', '--no-index', '--no-deps',
                        str(next((cls.root / 'wheels').glob('fusion_module_client-*.whl')))],
                       cwd=cls.root, env=cls.environment, check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_installed(self, code):
        return subprocess.run([str(self.python), '-I', '-c', code], cwd=self.root,
                              env=self.environment, check=True, capture_output=True, text=True)

    def test_client_only_install_exports_exact_pure_contracts(self):
        result = self.run_installed('''import importlib.util,json,sys
from importlib.metadata import distribution
from importlib.resources import files
def audit(event,args):
    assert event != 'sqlite3.connect', 'import attempted to open an owner database'
sys.addaudithook(audit)
import fusion_sdk as sdk
from fusion import preview_handles as handles,preview_tools as tools
assert sdk.make is handles.make and sdk.envelope is handles.envelope
assert sdk.ToolDescriptor is tools.ToolDescriptor and sdk.Catalogue is tools.Catalogue
assert distribution('fusion-module-client').version == '0.3.0'
for module in ('chromadb','torch','transformers','phase2_provider','fusion.policy',
               'fusion.atom_feed','fusion.neoclaw_application','fusion.preview_ports',
               'fusion.preview_memory_services','fusion.neoclaw_contracts'):
    assert importlib.util.find_spec(module) is None, module
for unsupported in ('deduction_tools','memory_tools','workspace_tools','history_tools',
                    'lifecycle_tools','relation_tools'):
    assert not hasattr(sdk,unsupported), unsupported
api=json.loads(files('fusion_sdk').joinpath('public-api.json').read_text())
assert api['profiles']['handles']==sdk.HANDLE_PROFILE
assert api['profiles']['tools']==sdk.TOOL_PROFILE
assert api['profiles']['vocabulary']==sdk.VOCABULARY
assert set(api['handle_kinds'])==set(handles.KINDS)
assert all(getattr(sdk,name) is not None for name in sdk.__all__)
assert not any(x.startswith(('torch','chromadb','transformers')) for x in sys.modules)
print(json.dumps({'pure_exports':'PASS','owner_imports':'ABSENT','database_opens':0}))
''')
        self.assertEqual(json.loads(result.stdout),
                         {'pure_exports': 'PASS', 'owner_imports': 'ABSENT', 'database_opens': 0})

    def test_handle_kinds_and_typed_batch_admission_execute_when_installed(self):
        result = self.run_installed('''import json
from dataclasses import replace
from fusion_sdk import *
scope='synthetic-sdk'
atom=dict(scope_ref=scope,id='opaque-atom',revision=1,digest='a'*64)
episode=dict(scope_ref=scope,id='opaque-episode')
targets=dict(memory=dict(enrollment=atom,payload=atom),episode=episode,
 event=dict(episode=episode,occurrence_id='input-1',sequence=1,event_ref=atom),
 relation=atom,task=dict(session='11111111-1111-4111-8111-111111111111',id='task-1'),
 result=dict(occurrence='command-1',payload=atom))
def refuses(code,fn):
    try: fn()
    except ContractError as exc: assert exc.code==code,(code,exc.code)
    else: raise AssertionError('accepted invalid contract')
handles={kind:make(kind,scope,'agent-a',value) for kind,value in targets.items()}
for kind,item in handles.items():
    assert envelope(item,kind=kind,scope=scope,principal='agent-a')==item
    assert parse(item['handle']).kind==kind
    refuses('UNAUTHORIZED',lambda: envelope(item,principal='agent-b'))
assert Argument('target','memory-handle').validate(handles['memory']['handle'])
assert Argument('target','relation-handle').validate(handles['relation']['handle'])
for kind in ('episode','event'):
    assert Argument('target','history-handle').validate(handles[kind]['handle'])
refuses('INVALID_ARGUMENT',lambda: Argument('target','history-handle').validate(handles['memory']['handle']))
refuses('INVALID_ARGUMENT',lambda: Argument('target','memory-handle').validate('timestamp-or-alias'))
tool=ToolDescriptor('example.lookup','lookup','example-handle-read/1',
 (Argument('target','memory-handle'),),'read',(),'Read a typed synthetic handle',
 'Contract-only example; no implementation dispatch or owner authority.')
catalogue=Catalogue((tool,),{'example.lookup'},[])
authority=SessionAuthority('agent-a',scope,frozenset({'lookup'}),'policy-1',100)
command=['lookup',handles['memory']['handle']]
admitted=catalogue.admit([command],authority,'agent-a',1,catalogue.identity)
assert admitted[0]['arguments']['target']==handles['memory']['handle']
assert admitted[0]['selection']==catalogue.identity
refuses('UNSUPPORTED_OPERATION',lambda: catalogue.admit([command,['arbitrary-exec']],authority,'agent-a',1))
refuses('UNAUTHORIZED',lambda: catalogue.admit([command],replace(authority,revoked=True),'agent-a',1))
refuses('UNAUTHORIZED',lambda: catalogue.admit([command],authority,'agent-a',100))
refuses('CONFLICT',lambda: catalogue.admit([command],authority,'agent-a',1,'changed-binding'))
assert len(context_tools())==3
print(json.dumps({'handle_kinds':len(handles),'typed_batch_admission':'PASS','dispatches':0}))
''')
        self.assertEqual(json.loads(result.stdout),
                         {'handle_kinds': 6, 'typed_batch_admission': 'PASS', 'dispatches': 0})
