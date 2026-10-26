"""Bounded retrieval rehearsal. Authored completions; real adopted memory/IRC.

Must run under preparation_guard. This entrypoint cannot activate a live plan.
"""
import copy
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time
import uuid

from fusion import model_contracts as m, neoclaw_retrieval_disclosure as r
from fusion.contracts import canonical, digest, require
from fusion.registry import descriptor_wire
from .channel_composition import ChannelRun, write
from .controlled_run import ControlledRun
from .embedding_run import start, observed_finish
from .model_startup import retrieval_scaffold
from .preparation_guard import verify
from .memory_composition import ROOT

QUERY = 'Synthetic project Aster calibration card location'
QUESTION = 'Where does synthetic project Aster keep its calibration card? Use query '+QUERY
FOLLOWUP = 'Use the actual preceding query result to answer the project question with send.'
LOCATIONS = ('amber cabinet', 'violet drawer', 'copper locker')
BODIES = ['Synthetic answer: '+x+'.' for x in LOCATIONS] + ['Insufficient retrieved information.']


def generated(variant=0):
    """Empty initial corpus; native remember is the only enrollment route."""
    from .memory_embedding import load
    from .memory_composition import ROOT, MODEL
    encode = load(ROOT/'artifacts/s01/native-02/sources/mettaclaw/lib_llm_ext.py', MODEL,
                  json.loads((ROOT/'integration/neoclaw/memory-model.json').read_text())['files'])
    texts = ['Synthetic project '+name+' keeps its calibration card in '+location+'.'
             for name, location in zip(('Aster' if variant != 2 else 'Lumen', 'Birch', 'Cedar'),
                                       (LOCATIONS[variant % 2], LOCATIONS[2], LOCATIONS[1 - variant % 2]))]
    return dict(corpus_id='synthetic-retrieval-preparation-'+str(variant), records=[], queries={QUERY:encode(QUERY)},
                clock=2_000_000_000., embedding_boundary='real-native-e5',
                approved_append_inputs=texts, creation_clock_fixture='2032-10-20 12:00:00')


def rows(path, table):
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute('SELECT * FROM '+table+' ORDER BY rowid')]


def setup(corpus, *, root=None):
    from .promotion_composition import configure
    from .append_run import report
    from fusion.neoclaw_application import Application
    texts = corpus['approved_append_inputs']
    run = ControlledRun('local', ['remember '+x for x in texts]+[''], search={'boundary':'recorded-response'}, root=root)
    try:
        if root is not None: run.app['writable_paths'] = [str(run.h.root)]
        run.model['expected_feedback'] = {}; run.save()
        cfg = configure(run, corpus, inputs={text:text for text in texts})
        timing = observed_finish(run, observer_seconds=120 if root is not None else 45)
        evidence = report(run, cfg)
        evidence['timing'] = timing
        app = Application(run.app_path)
        try:
            # Application-owned selected view export, validated by existing owners.
            key = app.db.execute('SELECT view FROM app_active_view').fetchone()[0]
            view = app.priority.view(key)
            app.evidence.validate_view(view)
            refs = app.priority.payload_view(key, time.time_ns()//1_000_000+30000)
            payloads = {uid:app.priority.payload(item['ref'], view) for uid,item in refs.items()}
        finally: app.close()
        require(len(evidence['app_memory_writes']) == len(texts) == 3, 'CONFLICT')
        require(all(x['linked'] and 'native-success-captured' in x['observations'] for x in evidence['app_memory_writes']), 'NOT_AVAILABLE')
        require(set(view['defaults'].values()) == {r.PRIOR}, 'CONFLICT')
        cfg.update(setup=evidence, view=view, payloads=payloads, setup_session=run.app['session_id'])
        return run, cfg
    except BaseException:
        if (run.h.root/'native.log').exists(): print((run.h.root/'native.log').read_text()[-6000:], file=sys.stderr)
        run.close(); raise


def measured(run, cfg, *, placement='local', responses=None):
    """Fresh application journal from a ready immutable view, same existing owners.

    Setup is completed before composition. No operator edits occur between query
    and reply. No database copy/migration or direct index enrollment is performed.
    """
    parent = os.environ['FUSION_PREP_PARENT_NET']; verify(parent)
    view = cfg['view']; root = run.h.root
    write(root/'setup-application.json', run.app)
    session = str(uuid.uuid4())
    run.h.client['database'] = str(run.h.caller_root/'measured.sqlite'); run.h.save_client()
    run.app.update(session_id=session, workdir=str(run.h.caller_root/'measured-native'),
                   status_file=str(run.h.caller_root/'measured-status.json'))
    append = json.loads(Path(run.app['memory_append_config']).read_bytes()); append['session'] = session
    write(run.app['memory_append_config'], append)
    read = json.loads(Path(run.app['memory_read_config']).read_bytes())
    read.update(snapshot=view['snapshot'], metadata_seal=view['metadata_seal']); write(run.app['memory_read_config'], read)
    native = json.loads(Path(run.app['memory_native_config']).read_bytes())
    native['metadata_seal'] = view['metadata_seal']
    write(native['metadata_manifest'], view['metadata']); write(run.app['memory_native_config'], native)
    # Revoke setup writes at the owner and encoder. The measured application
    # retains read-view machinery, but possesses no append capability.
    methods = run.h.config['principals']['A']['scopes']['generated-s03']
    run.h.config['principals']['A']['scopes']['generated-s03'] = [x for x in methods if x not in
        ('memory.append.write', 'memory.append.disclose', 'atom.storage.create', 'search.build')]
    run.h.save()
    encoder = json.loads(Path(cfg['encoder_config']).read_bytes())
    encoder['principals']['A']['scopes']['generated-s03'] = [x for x in encoder['principals']['A']['scopes']['generated-s03']
                                                          if not x.startswith('embedding.memory.')]
    write(cfg['encoder_config'], encoder)
    channel = ChannelRun('network', True, session=session, inputs=[QUESTION, FOLLOWUP], outputs=BODIES,
                         denied=[str(run.h.caller_root), str(run.h.server_root)])
    local = run.h.caller_root/'channel.json'; local.write_bytes(channel.clients['application'].read_bytes()); local.chmod(0o600)
    channel.start_server()
    run.app.update(channel_config=str(local), channel_wait_ms=10000, channel_poll_limit=128,
                   channel_irc_probe_port=channel.irc_port)
    run.app['denied_paths'] += [str(x) for x in (channel.provider, channel.peer_root, channel.bridge_root, channel.server_root)]
    completion = root/'completion'; completion.mkdir(mode=0o700)
    authority = root/'completion-authority'; authority.mkdir(mode=0o700)
    policy_path = authority/'policy.json'
    receipts = root/'disclosure-receipts'; receipts.mkdir(mode=0o700)
    recipient = 'preparation-authored-completion-A'
    metadata = {x['uuid']:x for x in view['metadata']['records']}
    records = [dict(uuid=x['uuid'], time=x['time'], content=x['content'], metadata=metadata[x['uuid']], default=r.PRIOR)
               for x in cfg['payloads'].values()]
    consent = dict(recipient=recipient, records=records)
    # Evaluator never participates in prompt building, retrieval or authorization.
    evaluator = root/'evaluator'; evaluator.mkdir(mode=0o700)
    write(evaluator/'truth.json', dict(project='Aster', records=records))
    fixture = dict(boundary='AUTHORED_MODEL_RESPONSE_FIXTURE', parent_namespace=parent, root=str(completion),
                   python=sys.executable, responses=responses or ['query '+QUERY, 'send '+BODIES[0]],
                   denied_paths=[str(x) for x in (run.h.caller_root, run.h.server_root, root/'encoder', evaluator,
                                                   channel.provider, channel.caller, channel.bridge_root, channel.peer_root,
                                                   ROOT/'artifacts/retrieval-preparation', ROOT/'evidence/retrieval-preparation')])
    fixture_path = completion/'fixture.json'; write(fixture_path, fixture)
    lock = dict(path=str(fixture_path), sha256=digest(fixture_path.read_bytes()))
    disclosure = dict(policy=r.POLICY, scaffold=retrieval_scaffold(), memories=['()'],
                      users=[str(['HUMAN-MSG:', 'peer: '+x]) for x in (QUESTION, FOLLOWUP)], query=QUERY,
                      receipt_root=str(receipts), recipient=recipient, consent_sha256=digest(canonical(consent)),
                      view_sha256=digest(canonical(view)), authority_policy=str(policy_path))
    owner = dict(database=str(completion/'model.sqlite'), scope='synthetic-retrieval-preparation', sharing=m.PRIVACY,
                 sessions=[session], max_calls=2, expires_ms=time.time_ns()//1_000_000+900000,
                 catalogue=[descriptor_wire(m.descriptor(m.CPU_PROFILE))], runtime_lock=lock, disclosure=disclosure)
    credential = secrets.token_hex(24)
    policy = dict(model_completion=owner, principals={'A':dict(credential=credential, scopes={owner['scope']:
                  ['model.'+x for x in ('complete', 'observe', 'authorize', 'disclose')]})},
                  test_failpoints=True, failpoint_marker=str(completion/'pause.json'))
    client = {k:owner[k] for k in ('scope', 'sharing', 'catalogue', 'disclosure')}
    client.update(profile=m.CPU_PROFILE, principal='A', session=session, placement=placement, fallback=False,
                  commands=[['query', QUERY]]+[['send', b] for b in BODIES], credential=credential)
    host = None
    if placement == 'local': client['provider_config'] = str(policy_path)
    else:
        require(placement == 'network', 'UNSUPPORTED_PROFILE')
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(completion/'server.key'),
                        '-out', str(completion/'server.pem'), '-days', '1', '-subj', '/CN=127.0.0.1',
                        '-addext', 'subjectAltName=IP:127.0.0.1'], check=True, capture_output=True)
        (completion/'server.key').chmod(0o600)
        policy.update(tls_certificate=str(completion/'server.pem'), tls_key=str(completion/'server.key'))
        write(policy_path, policy)
        ready = completion/'ready.json'
        host = run.spawn('integration.neoclaw.retrieval_fixture', ['serve', policy_path, 0, ready], 'completion-fixture')
        run.h.wait_file(ready, host)
        ca = run.h.caller_root/'completion-ca.pem'; ca.write_bytes((completion/'server.pem').read_bytes())
        client['endpoint'] = dict(host='127.0.0.1', port=json.loads(ready.read_bytes())['port'], ca_file=str(ca))
        # Fixture selection lives outside the hidden provider root for the caller.
        run.app['denied_paths'] += [str(completion), str(evaluator)]
        run.app['model_denied_files'] = [str(completion/'fixture.json'), str(evaluator/'truth.json')]
    write(policy_path, policy)
    selected = run.h.caller_root/'model-client.json'; write(selected, client)
    run.app.pop('model_fixture', None)
    run.app.update(composition=r.APPLICATION, model_config=str(selected), turn_limit=2, preparation_diagnostics=True,
                   retrieval=dict(initial_view=view, consent=consent), readonly_paths=[str(authority)])
    # Local evaluation injection is explicit and namespace-checked. Network
    # clients use the real authenticated transport, with no adapter replacement.
    if placement == 'local': run.app['preparation_fixture_lock'] = lock
    else: run.app['preparation_fixture_boundary'] = 'AUTHORED_MODEL_RESPONSE_FIXTURE'
    run.save(); run.model_path.unlink(missing_ok=True)
    cfg.update(channel=channel, completion=completion, policy=policy_path, model_client=selected,
               disclosure_root=receipts, host=host, fixture_lock=lock, placement=placement)
    return cfg


def wait_for(predicate, process=None, seconds=30):
    until = time.monotonic()+seconds
    while time.monotonic() < until:
        if predicate(): return
        if process is not None and process.poll() is not None: break
        time.sleep(.03)
    raise TimeoutError('bounded preparation observer')


def export(run, cfg):
    db = run.h.client['database']
    value = {table:rows(db, table) for table in (
        'app_session', 'app_turns', 'app_occurrences', 'app_model_calls', 'app_memory_reads',
        'app_query_vectors', 'app_query_views', 'app_read_views', 'app_priority_contexts',
        'app_channel_inputs', 'app_channel_outputs')}
    value.update(model_provider=rows(cfg['completion']/'model.sqlite', 'model_calls'),
                 fixture_evaluations=[json.loads(x) for x in (cfg['completion']/'evaluations.jsonl').read_text().splitlines()],
                 disclosure_receipts=[json.loads(p.read_bytes()) for p in sorted(cfg['disclosure_root'].glob('*.json'))],
                 peer=cfg['channel'].traffic(), placement=cfg['placement'], mailbox='authenticated-same-host-HTTPS',
                 retrieval='local', encoder='local', setup_session=cfg['setup_session'],
                 startup=json.loads((Path(run.app['workdir'])/'startup.json').read_bytes()),
                 setup=cfg['setup'], additional_live_generations=0, live_memory_workflow='NOT_RUN')
    # Operator-authorized synthetic test audit, never a consumer retrieval path.
    value['bridge_ingress_audit'] = rows(cfg['channel'].bridge_root/'bridge.sqlite', 'channel_ingress')
    value['bridge_egress_audit'] = rows(cfg['channel'].bridge_root/'bridge.sqlite', 'channel_egress')
    value['native_boundary_probes'] = {
        name:json.loads((Path(run.app['workdir'])/name).read_bytes())
        for name in ('embedding-boundary.json', 'model-boundary.json', 'channel-boundary.json')}
    value['measured_process_resources'] = (run.h.caller_root/'caller-time.txt').read_text()
    return value


def evaluate(feedback, body, peer_observed, target_fact):
    permitted = body in BODIES
    decisive = target_fact is not None and target_fact in feedback
    correct = body == ('Synthetic answer: '+target_fact.split(' in ')[-1] if decisive else BODIES[-1])
    return dict(output_permitted=permitted, retrieval_decisive=decisive, answer_correct=correct,
                peer_observed=peer_observed, task='PASS' if permitted and correct and peer_observed else 'FAIL',
                model_usefulness='NOT_RUN')


def workflow(corpus, placement='local', responses=None):
    run, cfg = setup(corpus)
    try:
        measured(run, cfg, placement=placement, responses=responses)
        ch = cfg['channel']; ch.start_bridge(); ch.start_peer()
        process = start(run)
        wait_for(lambda:(Path(run.app['workdir'])/'embedding-ready.json').exists(), process)
        ch.send(QUESTION)
        wait_for(lambda:any(x['projection'] is not None for x in rows(run.h.client['database'], 'app_turns')), process)
        ch.send(FOLLOWUP)
        code, status = run.finish(process)
        require((code, status) == (0, {'status':'BOUNDED_STOP'}), 'NOT_AVAILABLE')
        wait_for(lambda:any(BODIES[0] in str(x) for x in ch.traffic()), seconds=10)
        return export(run, cfg)
    except BaseException:
        if (run.h.root/'native.log').exists(): print((run.h.root/'native.log').read_text()[-12000:], file=sys.stderr)
        status = Path(run.app['status_file'])
        if status.exists(): print(status.read_text(), file=sys.stderr)
        raise
    finally:
        if 'channel' in cfg: cfg['channel'].close()
        run.close()


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--evidence', required=True); p.add_argument('--placement', choices=['local', 'network'], default='local')
    a = p.parse_args()
    write(a.evidence, workflow(generated(), a.placement))
