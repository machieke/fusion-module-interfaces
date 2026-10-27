"""Resolve a ConfigMap and mounted Secret files into process-local configuration.

No credentials in Helm values, images, logs or PVCs. Configuration contains no
model-selected endpoint/path. This is deployment composition, not a new caller.
"""
import json
import os
from pathlib import Path
from fusion import neoclaw_contracts as c
from fusion.contracts import canonical, require
from fusion.neoclaw_services import COMPOSITION
from fusion.registry import descriptor_wire

ROLES = ('omega-agent', 'fusion-execution', 'fusion-storage', 'fusion-messaging')
COMMAND = 'metta (Truth_Deduction (stv 0.8 0.9) (stv 0.7 0.8))'
GOLDEN = '(stv 0.5599999999999999 0.4032)'


def write(path, value):
    path = Path(path)
    temporary = path.with_suffix('.pending')
    with open(temporary, 'w') as f:
        os.chmod(temporary, 0o600)
        f.write(canonical(value).decode()); f.flush(); os.fsync(f.fileno())
    temporary.replace(path)


def configure(path='/config/component.json'):
    settings = json.loads(Path(path).read_text()); role = settings['role']
    require(role in ROLES and settings['service_composition'] == COMPOSITION, 'UNSUPPORTED_PROFILE')
    state = Path(settings.get('state', '/state')); run = Path(settings.get('run', '/run/fusion'))
    state.mkdir(parents=True, exist_ok=True); run.mkdir(parents=True, exist_ok=True)
    secret = Path(settings.get('secret_directory', '/secrets'))
    def token(name):
        value = (secret/name).read_text().strip()
        require(value.isascii() and 32 <= len(value) <= 256, 'UNAUTHORIZED')
        return value
    def endpoint(name):
        return dict(host=settings['peers'][name], port=settings['https_port'], ca_file=str(secret/'ca.crt'))
    routes = {'reply-A': dict(scope=c.SCOPE, owner='A')}
    # Each owner authenticates its own distinct Secret credentials; peer tokens
    # exist only in the calling pod. No global administrator bearer token.
    def principal(name, methods):
        return dict(credential=token(name), scopes={c.SCOPE: methods})
    config = dict(service_composition=COMPOSITION, profile=c.PROFILE, sharing='generated-shareable',
        capacity=settings['capacity'], atom_provider='detta', routes=routes,
        tls_certificate=str(secret/'tls.crt'), tls_key=str(secret/'tls.key'))
    test = settings.get('test', {})
    require(not test or settings.get('enable_test_faults') is True, 'UNAUTHORIZED')
    # A declared kill barrier fires once on fresh synthetic state. Replacement
    # observes the durable marker; no operator edits or deadline reset needed.
    pause = test.get('pause_at') if not (state/'pause.json').exists() else None
    config.update(test_failpoints=bool(test), failpoint_marker=str(state/'pause.json'))
    if pause: config['pause_at'] = pause
    if role == 'omega-agent':
        client = dict(database=str(state/'caller.sqlite'), scope=c.SCOPE, principal='A',
            sharing='generated-shareable', reply_route='reply-A', max_calls=64, max_attempts=3,
            fallback=False, placement='service-network', service_composition=COMPOSITION,
            catalogue=[descriptor_wire(d) for d in c.catalogue('detta')],
            endpoints={k:endpoint(v) for k,v in zip(('execution','atom.storage','agent.messaging'),ROLES[1:])},
            service_credentials={k:token(v+'-token') for k,v in zip(('execution','atom.storage','agent.messaging'),ROLES[1:])})
        write(run/'caller.json', client)
        app = dict(composition='controlled-native-loop/1', runtime='/opt/native/runtime.json',
            caller_config=str(run/'caller.json'), turn_limit=2, invocation_timeout_ms=30000,
            model_fixture=str(run/'model.json'), workdir=str(state/'native'),
            status_file=str(state/'native-status.json'), test_failpoints=bool(test),
            failpoint_marker=str(state/'pause.json'))
        if pause: app['pause_at'] = pause
        write(run/'application.json', app)
        write(run/'model.json', dict(responses=[COMMAND,''], expected_feedback={'1':[[GOLDEN,1]]},
                                    log=str(state/'model-contexts.jsonl')))
    elif role == 'fusion-execution':
        config.update(database=str(state/'execution.sqlite'), runtime='/opt/native/runtime.json',
            principals={'A':principal('caller-token', ['execution.submit','execution.status','execution.result','agent.messaging.poll']),
                        'worker':dict(credential=token('worker-token'), scopes={c.SCOPE:['atom.storage.create']})},
            peers={name:dict(endpoint=endpoint(name),credential=token(name+'-token')) for name in ROLES[2:]})
    elif role == 'fusion-storage':
        config.update(atoms_database=str(state/'atoms.sqlite'), da_root=str(state/'da'),
            detta_binary='/opt/native/fusion-detta-adapter',
            principals={'A':principal('caller-token',['atom.storage.get','agent.messaging.poll']),
                        'worker':principal('worker-token',['atom.storage.create'])})
    else:
        config.update(messages_database=str(state/'messages.sqlite'),
            principals={'A':principal('caller-token',['agent.messaging.poll','agent.messaging.ack']),
                        'worker':principal('worker-token',['execution.completion'])})
    write(run/'owner.json', config)
    return settings, config, state, run
