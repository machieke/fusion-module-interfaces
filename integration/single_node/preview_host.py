"""Bounded native worker wakeups on the existing single-owner process host.

No retries of failed children, synthetic tool execution or model calls here.
The application and provider journals decide recovery. HTTP admission only
wakes the source-checked launcher with its immutable session composition.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
from fusion.contracts import ContractError, require
from fusion.preview_session_service import SessionPorts
from fusion.preview_sessions import PROFILE
from .configure import write


class NativeSupervisor:
    def __init__(self, config, state, run, *, enabled=True):
        self.config,self.state,self.run=Path(config),Path(state),Path(run)
        self.guard=threading.Lock();self.pending=[];self.child=None;self.session=None;self.log=None
        require(type(enabled) is bool);self.enabled=enabled
        self.stopped=False

    def projections(self, session):
        from .sustained_runtime import saved_projections
        return saved_projections(self.config,self.state,session)

    def wake(self, session):
        with self.guard:
            require(not self.stopped,'NOT_AVAILABLE')
            cfg=json.loads(self.config.read_text())['native_sessions']
            if cfg['profile']=='omega-native-sessions/3':
                from .sustained_runtime import materialize
                materialize(self.config,self.state,self.run,session)
            else:require(session in cfg['session_templates'],'UNAUTHORIZED')
            if session not in self.pending:
                require(len(self.pending)<8,'OVERLOADED');self.pending.append(session)

    def tick(self):
        if not self.enabled:return
        with self.guard:
            if self.child is not None:
                code=self.child.poll()
                if code is None:return
                write(self.state/'worker-status.json',dict(session=self.session,exit_code=code,
                    status='NATIVE_STOPPED',automatic_retry=False))
                if code==0:
                    cfg=json.loads(self.config.read_text())
                    if cfg['native_sessions']['profile']=='omega-native-sessions/3':
                        # One completed input per child. Rotate only untouched
                        # accepted work after a clean stop, never retry a failed
                        # or uncertain child automatically.
                        observed=SessionPorts(self.config).invoke(cfg['principals']['worker']['credential'],dict(
                            id='quantum-observe',profile=cfg['native_sessions']['profile'],operation='observe',
                            body=dict(session=self.session,content=False)))['value']
                        if observed['state']=='active' and any(x['state']=='accepted' for x in observed['inputs']):
                            if self.session not in self.pending:
                                require(len(self.pending)<8,'OVERLOADED');self.pending.append(self.session)
                self.log.close();self.log=None;self.child=None;self.session=None
            if self.stopped or not self.pending:return
            sid=self.pending.pop(0)
            application=self.run/'sessions'/sid/'application.json'
            require(application.exists(),'NOT_AVAILABLE')
            app=json.loads(application.read_text())
            if 'active_memory_configs' in app:
                from .preview_memory_configure import prepare
                try:
                    settings=json.loads(Path('/config/component.json').read_text())
                    prepare(settings,self.state/'sessions'/sid,application.parent)
                except (ContractError,OSError) as error:
                    # Acceptance is already durable. Failed preparation does not
                    # restart the owner, renew the input, or schedule a retry.
                    write(self.state/'worker-status.json',dict(session=sid,
                        status='PREPARATION_FAILED',code=getattr(error,'code','NOT_AVAILABLE'),
                        automatic_retry=False))
                    return
            log_path=self.state/'sessions'/sid/'worker.log';log_path.parent.mkdir(parents=True,exist_ok=True)
            self.log=open(os.devnull,'ab') if app.get('private_diagnostics')=='bounded-stages-only/1' else log_path.open('ab')
            self.child=subprocess.Popen([sys.executable,'-m','integration.neoclaw.native_loop',str(application)],
                stdout=self.log,stderr=self.log,start_new_session=True)
            self.session=sid
            write(self.state/'worker-status.json',dict(session=sid,pid=self.child.pid,status='RUNNING',pending=len(self.pending)))

    def recover(self):
        if not self.enabled:return
        from fusion.contracts import ContractError
        cfg=json.loads(self.config.read_text());policy=cfg['native_sessions']
        credential=cfg['principals']['worker']['credential']
        if 'task_ingress' in cfg:
            from .preview_task_ingress import Ingress
            try:Ingress(self.config,self.wake).drain()
            except (ContractError,OSError) as error:
                write(self.state/'task-ingress-status.json',dict(status='NOT_AVAILABLE',code=getattr(error,'code','NOT_AVAILABLE')))
        if policy['profile']=='omega-native-sessions/3':
            # Startup observes accepted sessions; it must not mark dispatch on
            # behalf of a native child that has not received an input.
            rows=SessionPorts(self.config).invoke(credential,dict(id='startup-list',profile=policy['profile'],operation='list',body={}))['value']
            for row in rows:
                if row['state']=='active':self.wake(row['session'])
            return
        for sid in policy['session_templates']:
            try:
                result=SessionPorts(self.config).invoke(credential,dict(id='startup-observe',profile=PROFILE,
                    operation='next',body={'session':sid}))['value']
                if result is not None:self.wake(sid)
            except ContractError as error:
                if error.code not in ('NOT_FOUND','NOT_AVAILABLE','DEADLINE_EXCEEDED'):raise
                if error.code=='DEADLINE_EXCEEDED':self.wake(sid)

    def stop(self):
        with self.guard:
            self.stopped=True
            if self.child and self.child.poll() is None:
                try:os.killpg(self.child.pid,signal.SIGTERM)
                except ProcessLookupError:pass
        if self.child:
            try:self.child.wait(timeout=25)
            except subprocess.TimeoutExpired:
                os.killpg(self.child.pid,signal.SIGKILL);self.child.wait(timeout=2)
        if self.log:self.log.close();self.log=None
