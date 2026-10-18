"""Bounded S01 + S02 session using the existing controlled operator lifecycle.

Live mode makes one SDK invocation and never retries another backend. Captured
result recovery is optional and makes no further external call. Model/channel/
unused memory remain declared fixtures. Only generated public query QUERY is used.
"""
import argparse
import json
from pathlib import Path
import signal
import sqlite3
import traceback

from fusion.contracts import canonical, digest
from fusion import neoclaw_search_contracts as s
from .controlled_run import ControlledRun
from .search_composition import COMMAND, QUERY, audit
from tests.neoclaw_support import COMMAND as NAL, GOLDEN


def observation(run):
    with sqlite3.connect(run.h.config['database']) as db:
        rows=db.execute('SELECT request,output FROM jobs JOIN s01_work ON id=job_id').fetchall()
    return next(raw for request,raw in rows if json.loads(request)['profile']==s.PROFILE)


def execute(placement, boundary, destination, recover_capture=False):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    run=ControlledRun(placement,[NAL,COMMAND,''],{'1':[[GOLDEN,1]]},search=dict(boundary=boundary))
    recovery=None
    try:
        if recover_capture:
            run.h.config['pause_at']='after_search_capture';run.h.save()
        operator=run.operator();native=run.start()
        if recover_capture:
            marker=Path(run.h.config['failpoint_marker']);run.h.wait_file(marker,operator)
            point=json.loads(marker.read_text())
            assert point['stage']=='after_search_capture' and point['pid']==operator.pid
            selected=observation(run);assert selected is not None
            before=audit(run);rows=run.rows('app_occurrences')
            run.kill(native);run.kill(operator)
            assert operator.returncode == -signal.SIGKILL
            run.h.config.pop('pause_at');run.h.save()  # Test fault control only.
            run.operator();native=run.start()
            recovery=dict(signal=9,capture_sha256=digest(selected.encode()),before_audit=before,
                          original_occurrences=rows,fault_control_removed=True)
        code,status=run.finish(native)
        if code!=0 or status!=dict(status='BOUNDED_STOP'):
            report=dict(outcome='FAIL',placement=placement,boundary=boundary,status=status,audit=audit(run))
            destination.write_bytes(canonical(report));return report
        raw=observation(run);value=json.loads(raw)
        assert value['observation']['boundary']==boundary
        if boundary=='live':assert value['observation']['items'], 'No live results'
        assert len(run.observations())==3
        assert 'TITLE:' in run.observations()[2]['feedback']
        assert run.rows('app_occurrences')[1]['result']==value['representation']
        assert sum(x['event']=='sdk-start' for x in audit(run))==1
        assert run.h.counts()['jobs']==2 and run.h.counts()['unacked']==0
        if recovery:
            assert raw==selected and audit(run)==before
            for previous,current in zip(rows,run.rows('app_occurrences')):
                assert all(previous[k]==current[k] for k in ('id','deadline','premises'))
        # Read back through the independent real storage owner's port, byte exact.
        service=run.h.service()
        try:
            atom=service.db.execute("SELECT result FROM jobs WHERE id=?",(value['job_id'],)).fetchone()[0]
            data=service.atoms_for('worker',service.profiles[s.PROFILE]).get(json.loads(atom)['ref']).bytes
            assert data==raw.encode()
        finally:service.close()
        report=dict(outcome='PASS',boundary=boundary,query=QUERY,selected_observation=value,
            captured_bytes_sha256=digest(data),exact_atom_readback=True,recovery=recovery,audit=audit(run),
            caller_boundary=json.loads((Path(run.app['workdir'])/'caller-boundary.json').read_text()),**run.report())
        serialized=canonical(report)
        assert run.h.client['credential'].encode() not in serialized
        assert str(run.h.server_root).encode() not in serialized
        destination.write_bytes(serialized);return report
    except Exception as exc:
        report=dict(outcome='TIMEOUT' if isinstance(exc,(TimeoutError,)) or 'timeout' in str(exc).lower() else 'FAIL',
                    placement=placement,boundary=boundary,failure_type=type(exc).__name__,audit=audit(run))
        # Keep diagnostics locally; never publish raw SDK text/credentials.
        destination.write_bytes(canonical(report))
        (destination.with_suffix('.diagnostic.log')).write_text(traceback.format_exc()+'\n'+(run.h.root/'native.log').read_text())
        return report
    finally:run.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--placement',choices=('local','network'),required=True)
    parser.add_argument('--boundary',choices=('live','recorded-response'),required=True)
    parser.add_argument('--evidence',required=True)
    parser.add_argument('--recover-capture',action='store_true')
    args=parser.parse_args()
    result=execute(args.placement,args.boundary,args.evidence,args.recover_capture)
    print(json.dumps({k:result[k] for k in ('outcome','boundary')}))
    raise SystemExit(0 if result['outcome']=='PASS' else 1)
