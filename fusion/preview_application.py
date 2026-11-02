"""Opt-in application facets; native parsing/evaluation remains upstream.

The preview shares Application's occurrence and projection journal. It does
not introduce another tool execution lifecycle or change historical profiles.
"""
import json
from pathlib import Path
import time

from .contracts import canonical, require
from .preview_context import WorkingContext
from .preview_tools import Catalogue, SessionAuthority, context_tools, memory_tools, workspace_tools, history_tools,deduction_tools,lifecycle_tools,relation_tools,cognitive_tools,task_tools,inspection_tools
from .registry import descriptor_read, selection_token

APPLICATION = 'omega-developer-native-session/1'


def configuration(value):
    required = {'profile', 'base', 'authority_file', 'tools', 'scope'}
    require(type(value) is dict and required <= set(value) <= required | {'providers'})
    require(type(value['scope']) is str and value['scope'].startswith('synthetic-'), 'UNAUTHORIZED')
    require(value['profile'] == APPLICATION and value['base'] in ('controlled-native-loop/1', 'controlled-native-loop/5','controlled-native-loop/12'), 'UNSUPPORTED_PROFILE')
    require(type(value['tools']) is list and len(set(value['tools'])) == len(value['tools']))
    active=any('semantic-active-memory-view/1' in d.get('profiles',[]) for d in value.get('providers',[]))
    from .preview_capabilities import registered_tools,IMPLEMENTATIONS
    tools = {t.native_name:t for t in registered_tools(active=active)}
    require(set(value['tools']) <= tools.keys(), 'UNSUPPORTED_OPERATION')
    selected = [tools[name] for name in value['tools']]
    catalogue = Catalogue(selected, IMPLEMENTATIONS, [descriptor_read(d) for d in value.get('providers', [])])
    return catalogue


class PreviewAdoption:
    def __init__(self, app):
        self.app, self.db = app, app.db
        self.config = app.preview_config
        self.catalogue = configuration(self.config)
        actual = set(app.binding.get('selections',{}).values())
        for name in ('memory', 'memory_append'):
            actual.update(app.binding.get(name, {}).get('selections', {}).values())
        for name in ('query_embedding', 'memory_embedding'):
            if name in app.binding: actual.add(app.binding[name]['selection'])
        if 'evidence' in app.binding:actual.update(app.binding['evidence']['selections'].values())
        self.facets={}
        for name,path in app.config.get('facet_configs',{}).items():
            from .preview_ports import Client,descriptor
            self.facets[name]=Client(path,name)
            require(self.facets[name].frozen==app.binding['preview_facets'][name], 'CONFLICT')
            actual.add(selection_token(descriptor(name)))
        if 'active_memory_configs' in app.config:
            from .preview_memory_services import descriptor as active_descriptor
            actual.update(selection_token(active_descriptor(n)) for n in app.config['active_memory_configs'])
        if 'tasks' in app.binding:
            from .preview_tasks import descriptor as task_descriptor
            actual.add(selection_token(task_descriptor()))
        if 'inspection' in app.binding:
            from .registry import descriptors as inspection_descriptors
            actual.update(selection_token(d) for d in inspection_descriptors() if d.interface in ('execution','agent.messaging'))
        require(all(selection_token(d) in actual for selected in self.catalogue.selections.values() for d in selected), 'UNSUPPORTED_PROFILE')
        self.context = WorkingContext(self.db, self.authorize, app.hook)
        self.memory=None
        if 'active_memory_configs' in app.config:
            from .preview_native_memory import SharedMemory
            self.memory=SharedMemory(app)
        self.input = None
        if 'session_config' in app.config:
            from .preview_input import NativeInput
            self.input = NativeInput(app)
        self.history=None
        if 'episodic.memory' in self.facets:
            from .preview_native_history import NativeHistory
            require(self.input is not None,'UNSUPPORTED_PROFILE')
            self.history=NativeHistory(app,self.facets['episodic.memory'])
        self.relations=None
        if 'relations' in self.facets:
            from .preview_native_relations import NativeRelations
            require(self.history is not None and self.memory is not None,'UNSUPPORTED_PROFILE')
            self.relations=NativeRelations(app,self.facets['relations'])
        self.tasks=None
        if 'task_config' in app.config:
            from .preview_native_tasks import NativeTasks
            require(self.memory is not None and self.input is not None,'UNSUPPORTED_PROFILE')
            self.tasks=NativeTasks(app)
        self.inspection=None
        if 'inspect_config' in app.config:
            from .preview_native_inspect import NativeInspection
            require(self.tasks is not None,'UNSUPPORTED_PROFILE');self.inspection=NativeInspection(app)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS preview_context_acceptance (
                occurrence TEXT PRIMARY KEY, expected_revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_context_captures (
                turn INTEGER PRIMARY KEY, view TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_file_acceptances (
                occurrence TEXT PRIMARY KEY, revision INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS preview_dispatch_budget (
                occurrence TEXT PRIMARY KEY, attempts INTEGER NOT NULL);
        ''')

    def authority(self):
        cfg = json.loads(Path(self.config['authority_file']).read_text())
        require(set(cfg) == {'principal', 'scope', 'tools', 'revision', 'expires_ms', 'revoked'})
        authority = SessionAuthority(**{**cfg, 'tools': frozenset(cfg['tools'])})
        require(authority.principal == self.app.binding['principal'] and authority.scope == self.config['scope'], 'UNAUTHORIZED')
        return authority

    def authorize(self, operation):
        authority = self.authority()
        authority.check(self.app.binding['principal'], time.time_ns()//1_000_000)
        if operation == 'context.write': require({'pin', 'unpin'} & authority.tools, 'UNAUTHORIZED')
        return authority

    def skills(self):
        return self.catalogue.skills(self.authority(), self.app.binding['principal'], time.time_ns()//1_000_000)

    def reserve_dispatch(self,row,name):
        """A native dispatch attempt is distinct from each owner's RPC budget.

        A crash spends this reservation. Saved tool results remain observable
        without reserving another effect attempt, under current authority.
        """
        authority=self.authorize('dispatch');require(name in authority.tools,'UNAUTHORIZED')
        if row['done']:return
        require(time.time_ns()//1_000_000<row['deadline'],'DEADLINE_EXCEEDED')
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            spent=self.db.execute('SELECT attempts FROM preview_dispatch_budget WHERE occurrence=?',(row['id'],)).fetchone()
            count=spent[0] if spent else 0
            require(count<self.catalogue.tools[name].attempts,'OVERLOADED')
            self.db.execute('INSERT INTO preview_dispatch_budget VALUES(?,?) ON CONFLICT(occurrence) DO UPDATE SET attempts=excluded.attempts',(row['id'],count+1))
        self.app.hook('after_preview_dispatch_reservation')

    def intent(self, command):
        value = self.catalogue.admit([command], self.authority(), self.app.binding['principal'], time.time_ns()//1_000_000)[0]
        if command[0]=='delegate':
            require(self.tasks is not None and command[1]!=self.app.binding['principal'],'UNAUTHORIZED')
            require('task_origin' not in self.input.source(),'UNAUTHORIZED')
        if command[0]=='inspect-atom':require(self.inspection is not None,'UNSUPPORTED_PROFILE')
        if command[0]=='metta':return None
        if command[0] in ('support','contradict','promote','demote'):
            require(self.app.evidence_enabled and self.app.priority_enabled,'NOT_AVAILABLE');return None
        if command[0] in ('update','forget'):
            require(self.memory is not None,'NOT_AVAILABLE')
            if command[0]=='update':
                from . import append_contracts as w
                from .preview_text import helper
                cfg,_=self.app.write.settings();helper(cfg,command[2],'remember')
                return dict(profile=w.PROFILE,operation='update',arguments=dict(content=command[2],target=command[1]))
        if command[0] in ('remember', 'query'):
            require(self.app.memory_enabled and self.app.append_enabled, 'NOT_AVAILABLE')
            return None  # Existing native memory adapter owns execution/capture.
        if command[0]=='episodes':
            require(self.history is not None,'NOT_AVAILABLE')
            import re
            require(command[1]=='current' or re.fullmatch(r'oh1:episode:[0-9a-f-]{36}@[0-9]+:[0-9]+',command[1]),'INVALID_ARGUMENT')
        if command[0] in ('link','unlink'):require(self.relations is not None,'NOT_AVAILABLE')
        return dict(profile=APPLICATION, operation=command[0], arguments=value)

    def admit(self, occurrence, intent):
        if intent.get('operation')=='update':
            self.memory.admit(occurrence,intent['arguments']['target']);return
        if intent['profile'] != APPLICATION: return
        if intent['operation']=='inspect-atom':
            self.inspection.admit(occurrence,intent['arguments']['arguments']['task']);return
        if intent['operation']=='forget':self.memory.admit(occurrence,intent['arguments']['arguments']['target']);return
        if intent['operation'] in ('link','unlink'):
            self.relations.admit(occurrence,intent['operation'],intent['arguments']['arguments']);return
        # Called in the existing application acceptance transaction.
        revision = self.context.read()['revision']
        pending = self.db.execute('SELECT count(*) FROM preview_context_acceptance a JOIN app_occurrences o ON a.occurrence=o.id WHERE o.done=0').fetchone()[0]
        if intent['operation'] in ('pin', 'unpin'):
            self.db.execute('INSERT INTO preview_context_acceptance VALUES(?,?)', (occurrence, revision+pending))

    def replay(self, row):
        intent = json.loads(row['premises'])
        op, bound = intent['operation'], intent['arguments']
        authority = self.authorize('context.read')
        require(op in authority.tools and bound['selection'] == self.catalogue.identity and bound['policy'] == authority.revision, 'UNAUTHORIZED')
        if op in ('read-file','write-file','append-file'):
            require(self.facets['execution.workspace'].call('authorize',op.split('-')[0])=={'authorized':True},'UNAUTHORIZED')
        if op=='episodes':
            require(self.facets['episodic.memory'].call('authorize','readHistory')=={'authorized':True},'UNAUTHORIZED')
        if op=='delegate':return self.tasks.delegate(row,bound['arguments'])
        if op=='inspect-atom':return self.inspection.replay(row,bound['arguments'])
        if op=='forget':return self.memory.withdraw(row,args=bound['arguments'])
        if op in ('link','unlink'):return self.relations.replay(row,op)
        if row['result'] is not None: return row['result']
        require(time.time_ns()//1_000_000 < row['deadline'], 'DEADLINE_EXCEEDED')
        args = bound['arguments']
        if op in ('read-file','write-file','append-file'):
            port=self.facets['execution.workspace']
            if op=='read-file':value=port.call('read',args['path'],deadline=row['deadline'])
            else:
                prior=self.db.execute('SELECT revision FROM preview_file_acceptances WHERE occurrence=?',(row['id'],)).fetchone()
                if prior: revision=prior[0]
                else:
                    version=port.call('version',args['path'],deadline=row['deadline'])
                    require(type(version) is dict and set(version)=={'profile','path','revision','digest'} and version['path']==args['path'],'NOT_AVAILABLE')
                    revision=version['revision'];require(type(revision) is int and 0<=revision<=128,'NOT_AVAILABLE')
                    with self.db:self.db.execute('INSERT INTO preview_file_acceptances VALUES(?,?)',(row['id'],revision))
                    self.app.hook('after_workspace_application_bind')
                value=port.call(op.split('-')[0],row['id'],args['path'],args['text'],revision,deadline=row['deadline'])
                require(value['identity']==row['id'] and value['revision']==revision+1 and value['outcome']=='committed','NOT_AVAILABLE')
        elif op=='episodes':value=self.history.read(args['selector'])
        elif op == 'task-context': value = self.context.read()
        else:
            expected = self.db.execute('SELECT expected_revision FROM preview_context_acceptance WHERE occurrence=?', (row['id'],)).fetchone()
            require(expected is not None, 'NOT_AVAILABLE')
            value = self.context.change(row['id'], args['item'], args.get('note') if op == 'pin' else None, expected[0])
        return canonical(value).decode()

    def execute(self, command):
        return self.app._invoke(command)

    def context_text(self):
        self.authorize('context.read')
        turn = self.app.processing_slot()
        old = self.db.execute('SELECT view FROM preview_context_captures WHERE turn=?', (turn,)).fetchone()
        if old: return old[0]
        value = canonical(self.context.read()).decode().replace(':-:-:-:', '\\u003a-\\u003a-\\u003a-\\u003a')
        with self.db: self.db.execute('INSERT INTO preview_context_captures VALUES(?,?)', (turn, value))
        return value

    def render_context(self,prompt,skills,feedback,history,promoted,observed_time):
        from .preview_context import allocate_context
        source=self.input.source()['payload']['text'] if self.input else ''
        # Required native feedback, task notes and current input never truncate.
        # Reserve the native user envelope/normalization expansion explicitly.
        origin=self.input.source().get('task_origin') if self.input else None
        if origin and origin['record']['kind']=='result':
            self.tasks.input()
            feedback=dict(native=feedback,delegated_report=origin,interpretation='agent-report-not-independent-corroboration')
        allocation=allocate_context(system=dict(prompt=prompt,skills=skills,time=observed_time,
            format='Up to five native command lines; no variables or arbitrary execution'),
            task=json.loads(self.context_text()),input_text=source,feedback=feedback,
            history=history,promoted=promoted,maximum_bytes=28000)
        rendered='PROMPT_AND_SKILLS_JSON: '+canonical(allocation['system']).decode()
        rendered+=' LAST_SKILL_USE_RESULTS: '+canonical(allocation['feedback']).decode()
        rendered+=' HISTORY: '+canonical(allocation['history']).decode()
        rendered+=' MOST_PROMOTED_MEMORIES: '+canonical(allocation['promoted']).decode()
        rendered+=' CONTEXT_ALLOCATION: '+canonical(dict(omitted=allocation['omitted'],bound_unit='utf8-bytes',maximum_bytes=28000)).decode()
        rendered+=' UNVERIFIED_TASK_CONTEXT_JSON: '+canonical(allocation['task']).decode()
        rendered=rendered.replace(':-:-:-:','\\u003a-\\u003a-\\u003a-\\u003a')
        require(len(rendered.encode())+len(source.encode())*2+256<=32768,'OVERLOADED')
        return rendered
