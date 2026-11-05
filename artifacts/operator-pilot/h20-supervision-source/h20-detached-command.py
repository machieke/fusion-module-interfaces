import ctypes, datetime, hashlib, json, os, select, signal, sys, time
from pathlib import Path

def check(ok, reason):
    if not ok: raise RuntimeError(reason)
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_bytes())
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def put(path, value):
    path = Path(path); tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w') as out: json.dump(value, out, sort_keys=True, indent=2)
    tmp.chmod(0o600); os.replace(tmp, path)
def ident(pid):
    raw = Path('/proc', str(pid), 'stat').read_text()
    f = raw[raw.rfind(')') + 2:].split()
    return dict(pid=pid, ppid=int(f[1]), process_group=int(f[2]),
                session=int(f[3]), start_ticks=int(f[19]), state=f[0])
LIBC_PATH = '/lib/x86_64-linux-gnu/libc.so.6'
LIBC_SHA256 = '53b909551f8e581120ddc2d24cfb5df76c52e3c2e2a5dac0d202b25638b3e902'
# Verified x86_64 UAPI: __NR_pidfd_open=434, __NR_pidfd_send_signal=424.
def pidfd_open(pid):
    value = libc.syscall(ctypes.c_long(434), ctypes.c_int(pid), ctypes.c_uint(0))
    if value < 0: raise OSError(ctypes.get_errno(), 'pidfd_open refused')
    return value
def pidfd_signal(fd, sig):
    value = libc.syscall(ctypes.c_long(424), ctypes.c_int(fd), ctypes.c_int(sig),
                         ctypes.c_void_p(), ctypes.c_uint(0))
    if value < 0: raise OSError(ctypes.get_errno(), 'pidfd_send_signal refused')

def descendants():
    rows = {}
    for name in os.listdir('/proc'):
        if not name.isdecimal(): continue
        try: rows[int(name)] = ident(int(name))
        except (FileNotFoundError, ProcessLookupError, PermissionError): pass
    ours = {os.getpid()}
    while True:
        more = {pid for pid, row in rows.items() if row['ppid'] in ours}
        if more <= ours: break
        ours |= more
    return {pid: rows[pid] for pid in ours if pid != os.getpid() and pid in rows}

stage, script_arg, plan_arg, directory_arg = sys.argv[1:]
check(stage in ('clean', 'native'), 'selected phase required')
script, plan_path, directory = map(lambda x: Path(x).resolve(),
                                  (script_arg, plan_arg, directory_arg))
plan = load(plan_path)
expected = {'clean': '6911b2ccc03042c4d0543b25b0881d01a80cf271f5f0608219b2a79b527371e3',
            'native': '30165c0fe79f7a5778ef2973d4d91cf8536ae6783f68e74191f693b62665bb28'}
check(sha(script) == expected[stage] and plan.get('enabled') is True,
      'source or enabled plan mismatch')
packet = Path(plan['distribution']).resolve()
if stage == 'native': packet = packet.parent
suffix = ('h20-clean-install-source/h20-offline.py' if stage == 'clean'
          else 'h19-rehearsal-source/h19-native.py')
check(script == packet / 'artifacts/operator-pilot' / suffix,
      'must execute the selected final-packet source')
check(sha(packet / 'distribution.json') == plan['distribution_sha256'],
      'final packet mismatch')
if stage == 'native':
    release = Path(plan['release_record']); r = load(release)
    check(sha(release) == plan['release_record_sha256']
          and r['heavy_slot_released'] is True
          and r['distribution_sha256'] == plan['distribution_sha256']
          and r['implementation_commit'] == plan['implementation_commit']
          and r['namespaces'] == plan['namespaces'], 'separate root release mismatch')
    check(plan['maximum_programme_seconds'] == 4200
          and plan['cleanup_reserved_seconds'] == 300, 'native bounds changed')
    start_file = Path(plan['clean_install_output']) / 'h19-native/start.json'
    check(not start_file.parent.exists(), 'native attempt already exists')
else:
    check(plan['max_seconds'] == 1800 and not Path(plan['output']).exists(),
          'clean bounds or fresh output mismatch')
    start_file = None
check(not directory.exists(), 'launch record already exists; do not relaunch')
directory.mkdir(mode=0o700)
put(directory / 'launch.json', dict(stage=stage, launcher=ident(os.getpid()),
    command_sha256=sha(__file__), source_sha256=sha(script),
    plan_sha256=sha(plan_path), distribution_sha256=plan['distribution_sha256'],
    recorded_utc=utc(), additional_live_generations=0))

first = os.fork()
if first:
    _, code = os.waitpid(first, 0)
    check(os.waitstatus_to_exitcode(code) == 0, 'detach failed')
    until = time.monotonic() + 8
    while not (directory / 'ready.json').exists() and time.monotonic() < until:
        time.sleep(.05)
    check((directory / 'ready.json').exists(), 'launch uncertain; DO NOT relaunch')
    print(json.dumps(dict(status='DETACHED_ACK_ONLY', record=str(directory / 'ready.json'))))
    sys.exit(0)
os.setsid()
if os.fork(): os._exit(0)
os.umask(0o077); os.chdir('/')
for name in os.listdir('/proc/self/fd'):
    if name.isdecimal() and int(name) > 2:
        try: os.close(int(name))
        except OSError: pass
for number, path in ((0, '/dev/null'), (1, directory / 'supervisor.stdout'),
                     (2, directory / 'supervisor.stderr')):
    flags = os.O_RDONLY if number == 0 else os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600); os.dup2(fd, number)
    if fd != number: os.close(fd)
check(os.uname().machine == 'x86_64' and sha(LIBC_PATH) == LIBC_SHA256,
      'selected libc/architecture unavailable; no launch')
libc = ctypes.CDLL(LIBC_PATH, use_errno=True); libc.syscall.restype = ctypes.c_long
check(libc.prctl(36, 1, 0, 0, 0) == 0, 'child subreaper unavailable; no launch')
probe = pidfd_open(os.getpid())
try: pidfd_signal(probe, 0)
finally: os.close(probe)
began = time.monotonic()
report = dict(status='RUNNING', stage=stage, supervisor=ident(os.getpid()),
    started_utc=utc(), started_monotonic=began, source_sha256=sha(script),
    plan_sha256=sha(plan_path), limits=dict(native_seconds=4200 if stage == 'native' else 0,
    child_process_seconds=4330 if stage == 'native' else 1950,
    terminal_barrier_seconds=30), signals=[], child_exits=[], signals_sent=[],
    additional_live_generations=0, external_owner_cleanup_calls=0)
abort = None; child = None; exit_code = None; no_children = False
def save(): put(directory / 'status.json', report)
def interrupted(number, _frame):
    global abort
    abort = 'signal:' + signal.Signals(number).name
    report['signals'].append(dict(signal=number, utc=utc(), monotonic=time.monotonic()))
for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
    signal.signal(sig, interrupted)
def reap():
    global exit_code, no_children
    no_children = False
    while True:
        try: pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError: no_children = True; break
        if pid == 0: break
        code = os.waitstatus_to_exitcode(status)
        report['child_exits'].append(dict(pid=pid, exit_code=code, utc=utc()))
        if pid == child: exit_code = code
def send(row, sig):
    try:
        fd = pidfd_open(row['pid'])
        try:
            check(ident(row['pid'])['start_ticks'] == row['start_ticks'], 'PID reuse')
            pidfd_signal(fd, sig)
            report['signals_sent'].append(dict(process=row, signal=sig, utc=utc()))
        finally: os.close(fd)
    except (ProcessLookupError, FileNotFoundError): pass

try:
    save(); put(directory / 'ready.json', dict(supervisor=report['supervisor'],
        source_sha256=report['source_sha256'], plan_sha256=report['plan_sha256'],
        started_utc=report['started_utc'], started_monotonic=began))
    check(abort is None, 'interrupted before child launch')
    ready_r, ready_w = os.pipe(); go_r, go_w = os.pipe()
    child = os.fork()
    if child == 0:
        try:
            os.close(ready_r); os.close(go_w); os.setsid()
            for number, name in ((1, 'entry.stdout'), (2, 'entry.stderr')):
                fd = os.open(directory / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                os.dup2(fd, number); os.close(fd)
            os.write(ready_w, b'R'); os.close(ready_w)
            check(os.read(go_r, 1) == b'G', 'launch barrier closed'); os.close(go_r)
            env = dict(os.environ); env.pop('PYTHONPATH', None); env.pop('PYTHONHOME', None)
            os.execve(sys.executable, [sys.executable, '-B', '-I', str(script),
                      '--plan', str(plan_path), '--execute'], env)
        except BaseException: os._exit(127)
    os.close(ready_w); os.close(go_r)
    check(select.select([ready_r], [], [], 5)[0] and os.read(ready_r, 1) == b'R',
          'child identity handshake failed')
    os.close(ready_r); report['child'] = ident(child)
    check(report['child']['session'] == child == report['child']['process_group'],
          'child isolation failed')
    save(); os.write(go_w, b'G'); os.close(go_w)
    deadline = began + (4330 if stage == 'native' else 1950)
    native_start = None
    while exit_code is None:
        reap()
        if exit_code is not None: break
        if stage == 'native' and native_start is None:
            if start_file.exists():
                try: candidate = load(start_file)
                except json.JSONDecodeError: candidate = None
                if candidate is not None:
                    check(candidate['plan_sha256'] == sha(plan_path)
                          and candidate['original_end_monotonic'] == candidate['started_monotonic'] + 4200
                          and began <= candidate['started_monotonic'] <= began + 120,
                          'native start binding or preflight bound changed')
                    native_start = candidate; report['native_start'] = candidate
                    deadline = min(deadline, candidate['original_end_monotonic'] + 10); save()
            if native_start is None and time.monotonic() >= began + 120:
                abort = 'static preflight exceeded 120 seconds'
        if abort or time.monotonic() >= deadline:
            abort = abort or 'finite process envelope expired'; break
        time.sleep(.2)
except BaseException as error:
    abort = abort or ('supervisor:' + type(error).__name__)
    report['supervisor_failure_type'] = type(error).__name__
finally:
    # No external owner action is allowed before this complete-tree barrier.
    barrier_start = time.monotonic(); quiet_since = None; signaled = set()
    while time.monotonic() < barrier_start + 30:
        reap(); rows = descendants()
        if not rows and no_children:
            if quiet_since is None: quiet_since = time.monotonic()
            if time.monotonic() - quiet_since >= 1: break
        else:
            quiet_since = None
            sig = signal.SIGTERM if time.monotonic() < barrier_start + 20 else signal.SIGKILL
            for row in rows.values():
                key = (row['pid'], row['start_ticks'], sig)
                if key not in signaled:
                    send(row, sig); signaled.add(key)
        time.sleep(.1)
    reap(); remaining = descendants()
    passed = not remaining and no_children and exit_code is not None
    report.update(status='CHILD_TERMINAL' if passed and not abort else 'FAIL_RETAINED',
        entry_exit_code=exit_code, interruption=abort,
        terminal_barrier=dict(passed=passed, remaining=list(remaining.values()),
            elapsed_seconds=time.monotonic() - barrier_start, no_unreaped_children=no_children),
        elapsed_seconds=time.monotonic() - began, finished_utc=utc())
    save(); put(directory / 'terminal.json', report)
os._exit(0 if report['status'] == 'CHILD_TERMINAL' and exit_code == 0 else 1)