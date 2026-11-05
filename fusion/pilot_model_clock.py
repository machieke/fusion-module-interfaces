"""Fresh opt-in time guard for recorded ModelInference owner partitions.

Clock state belongs to the existing model journal. It does not replace the
historical model profile, retime a result, extend a deadline or refill a call.
Capture is durable even when its actual raw epoch sample is invalid. Such a
capture is retained for authorized owner inspection and cannot enter commands.
"""
import json
from .contracts import canonical, require

PROFILE = 'recorded-model-owner-time/1'
TABLES = {'pilot_model_clock', 'pilot_model_capture_clocks'}


def selection(cfg):
    value = cfg.get('owner_clock')
    if value is None:return None
    require(value == {'profile': PROFILE} and type(value) is dict, 'UNSUPPORTED_PROFILE')
    from .preview_model_contracts import PROFILE as recorded
    require(len(cfg['catalogue']) == 1 and cfg['catalogue'][0]['profiles'] == [recorded], 'UNSUPPORTED_PROFILE')
    return dict(value)


def expected_tables(cfg):
    return {'model_seal', 'model_calls'} | (TABLES if selection(cfg) else set())


def initialize(db, cfg):
    if selection(cfg) is None:return
    # Called within the same first-owner transaction as its historical seal.
    db.execute('CREATE TABLE pilot_model_clock(singleton INTEGER PRIMARY KEY CHECK(singleton=1),profile TEXT NOT NULL,water INTEGER NOT NULL,anomalies INTEGER NOT NULL,last_anomaly TEXT)')
    db.execute('INSERT INTO pilot_model_clock VALUES(1,?,0,0,NULL)', (PROFILE,))
    db.execute('CREATE TABLE pilot_model_capture_clocks(id TEXT PRIMARY KEY,raw_ms TEXT NOT NULL,prior_water INTEGER NOT NULL,valid INTEGER NOT NULL)')


def inspect(db, cfg):
    if selection(cfg) is None:return None
    rows=db.execute('SELECT * FROM pilot_model_clock').fetchall()
    require(len(rows)==1 and tuple(rows[0])[:2]==(1,PROFILE),'UNSUPPORTED_PROFILE')
    row=rows[0]
    require(type(row[2]) is int and row[2]>=0 and type(row[3]) is int and row[3]>=0,'NOT_AVAILABLE')
    require(db.execute('SELECT count(*) FROM pilot_model_capture_clocks').fetchone()[0]<=cfg['max_calls'],'OVERLOADED')
    require(not db.execute('SELECT 1 FROM pilot_model_capture_clocks c LEFT JOIN model_calls m ON m.id=c.id WHERE m.id IS NULL OR m.response IS NULL LIMIT 1').fetchone(),'NOT_AVAILABLE')
    return dict(profile=PROFILE,high_water_ms=row[2],anomalies=row[3],last_anomaly=json.loads(row[4]) if row[4] else None,
                observation='OWNER_LOCAL_RAW_EPOCH_NOT_DISTRIBUTED_CLOCK')


def record(db, raw, phase, identity=None):
    row=db.execute('SELECT water,anomalies FROM pilot_model_clock WHERE singleton=1').fetchone()
    require(row is not None,'NOT_AVAILABLE'); water,count=row
    valid=type(raw) is int and raw>0 and raw>=water
    if valid:db.execute('UPDATE pilot_model_clock SET water=? WHERE singleton=1',(raw,))
    else:
        anomaly=canonical(dict(phase=phase,occurrence=identity,raw_ms=raw,prior_water_ms=water)).decode()
        require(len(anomaly)<=2048,'OVERLOADED')
        db.execute('UPDATE pilot_model_clock SET anomalies=?,last_anomaly=? WHERE singleton=1',(min(count+1,9223372036854775807),anomaly))
    return dict(valid=valid,raw_ms=raw,prior_water=water)


def guard(db, raw, phase, identity):
    with db:
        db.execute('BEGIN IMMEDIATE');value=record(db,raw,phase,identity)
    require(value['valid'],'CONFLICT')
    return raw


def capture(db, identity, raw):
    require(db.in_transaction,'CONFLICT')
    value=record(db,raw,'capture',identity)
    db.execute('INSERT INTO pilot_model_capture_clocks VALUES(?,?,?,?)',
               (identity,canonical(raw).decode(),value['prior_water'],int(value['valid'])))


def checked_capture(db, identity):
    row=db.execute('SELECT raw_ms,prior_water,valid FROM pilot_model_capture_clocks WHERE id=?',(identity,)).fetchone()
    require(row is not None,'NOT_AVAILABLE')
    require(row[2]==1,'CONFLICT')
    return dict(raw_ms=json.loads(row[0]),prior_water_ms=row[1],valid=bool(row[2]))
