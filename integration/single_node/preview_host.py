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
import uuid
from fusion.contracts import ContractError, require
from fusion.preview_session_service import SessionPorts
from fusion.preview_sessions import PROFILE
from .configure import write


class NativeSupervisor:
    def __init__(self, config, state, run, *, enabled=True):
        self.config,self.state,self.run=Path(config),Path(state),Path(run)
        self.guard=threading.Lock();self.pending=[];self.child=None;self.session=None;self.log=None
        require(type(enabled) is bool);self.enabled=enabled
        self.stopped=False;self.incarnation=None

    def workers(self):
        """Trusted same-owner lifecycle; never an execution permission."""
        from fusion.resident_workers import Workers
        cfg=json.loads(self.config.read_bytes())['native_sessions']
        if 'resident_worker' not in cfg:return None
        def authorize(principal,scope,_):
            require(principal==cfg['principal'] and any(t['scope']==scope for t in cfg['allocation']['templates'].values()),'UNAUTHORIZED')
        return Workers(cfg['database'],authorize,cfg['allocation'],cfg['resident_worker'])

    def retire(self):
        if self.incarnation is None:return
        owner=self.workers()
        try:owner.retire(json.loads(self.config.read_bytes())['native_sessions']['principal'],self.session,self.incarnation)
        finally:owner.close();self.incarnation=None

    def projections(self, session):
        from .sustained_runtime import saved_projections
        return saved_projections(self.config,self.state,session)

    def wake(self, session):
        with self.guard:
            require(not self.stopped,'NOT_AVAILABLE')
            # Admission already rechecked the current actor. The live native
            # worker observes its inbox itself; do not rewrite its config.
            if session==self.session and self.child is not None and self.child.poll() is None:return
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
                self.retire()
                write(self.state/'worker-status.json',dict(session=self.session,exit_code=code,
                    status='NATIVE_STOPPED',automatic_retry=False))
                if code==0:
                    cfg=json.loads(self.config.read_text())
                    if cfg['native_sessions']['profile']=='omega-native-sessions/3':
                        # A bounded quantum per child. Rotate only untouched
                        # accepted work after a clean stop, never retry a failed
                        # or uncertain child automatically.
                        try:observed=SessionPorts(self.config).invoke(cfg['principals']['worker']['credential'],dict(
                            id='quantum-observe',profile=cfg['native_sessions']['profile'],operation='observe',
                            body=dict(session=self.session,content=False)))['value']
                        except ContractError:observed={'state':'unavailable'}
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
            self.session=sid
            command=[sys.executable,'-m','integration.neoclaw.native_loop',str(application)]
            try:
                owner=self.workers()
                if owner is not None:
                    epoch=str(uuid.uuid4())
                    try:owner.register(json.loads(self.config.read_bytes())['native_sessions']['principal'],sid,epoch)
                    finally:owner.close()
                    self.incarnation=epoch;command+=['--incarnation',epoch]
                self.child=subprocess.Popen(command,stdout=self.log,stderr=self.log,start_new_session=True)
            except (ContractError,OSError) as error:
                # No automatic replacement of a refused/uncertain session.
                self.retire();self.log.close();self.log=None;self.session=None
                write(self.state/'worker-status.json',dict(session=sid,status='START_REFUSED',code=getattr(error,'code','NOT_AVAILABLE'),automatic_retry=False))
                return
            write(self.state/'worker-status.json',dict(session=sid,pid=self.child.pid,incarnation=self.incarnation,status='RUNNING',pending=len(self.pending)))

    def recover(self):
        if not self.enabled:return
        from fusion.contracts import ContractError
        cfg=json.loads(self.config.read_text());policy=cfg['native_sessions']
        credential=cfg['principals']['worker']['credential']
        owner=self.workers()
        if owner is not None:
            # The service holds the exclusive PVC lock. On container startup
            # its previous process group is gone; fence its incarnation before
            # inspecting captures or starting any replacement.
            try:
                row=owner.db.execute('SELECT e.* FROM native_worker_epochs e JOIN native_worker_current c ON e.incarnation=c.incarnation WHERE c.slot=1').fetchone()
                if row is not None and row['state'] not in ('stopped','uncertain'):
                    owner.retire(policy['principal'],row['session'],row['incarnation'])
            finally:owner.close()
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
                if row['state']=='active':
                    if 'resident_worker' in policy:
                        observed=SessionPorts(self.config,projections=self.projections).invoke(credential,dict(
                            id='startup-reconcile',profile=policy['profile'],operation='reconcile',body=dict(session=row['session'])))['value']
                        if any(x['state'] in ('dispatched','needs-reconciliation','cancel-requested') for x in observed['inputs']):continue
                        if not any(x['state']=='accepted' for x in observed['inputs']):continue
                    self.wake(row['session'])
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
            self.retire()
        if self.log:self.log.close();self.log=None
