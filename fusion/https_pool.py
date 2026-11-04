"""Explicit bounded HTTPS reuse, with no request retry or authority cache.

Only trusted process composition enables this transport. Every lease binds the
exact endpoint, CA bytes, credential epoch and caller/profile audience. Callers
still validate every semantic response. A failed exchange closes its socket and
returns an error; it never reconnects and retransmits that request.
"""
import atexit,http.client,ssl,threading,time
from pathlib import Path
from .contracts import ContractError,digest,require
from .native_telemetry import span

PROFILE='bounded-authenticated-https-reuse/1'
LIMITS=dict(profile=PROFILE,connections=16,idle_ms=500,lifetime_ms=60000,requests=64)
_policy=None
_entries=[]
_guard=threading.Lock()

def selection(value):
    require(type(value) is dict and set(value)==set(LIMITS) and value['profile']==PROFILE,'UNSUPPORTED_PROFILE')
    for key,maximum in [('connections',32),('idle_ms',1000),('lifetime_ms',60000),('requests',64)]:
        require(type(value[key]) is int and 1<=value[key]<=maximum,'UNSUPPORTED_PROFILE')
    require(value['idle_ms']<=value['lifetime_ms'],'UNSUPPORTED_PROFILE');return value

def configure(value):
    global _policy
    if value is not None:selection(value)
    with _guard:
        if value==_policy:return
        require(not any(x['busy'] for x in _entries),'NOT_AVAILABLE')
        for row in _entries:row['connection'].close()
        _entries.clear();_policy=None if value is None else dict(value)

def enabled():return _policy is not None

def close():
    with _guard:
        for row in _entries:row['connection'].close()
        _entries.clear()

atexit.register(close)

def exchange(endpoint,credential,path,body,audience,remaining,maximum):
    require(_policy is not None,'UNSUPPORTED_PROFILE')
    require(type(body) is bytes and 0<len(body)<=131072 and 1<=maximum<=131072,'OVERLOADED')
    require(type(credential) is str and credential.isascii() and 1<=len(credential)<=256 and '\r' not in credential and '\n' not in credential,'UNAUTHORIZED')
    ca=Path(endpoint['ca_file']).read_bytes();require(len(ca)<=65536,'OVERLOADED')
    seconds=remaining();require(seconds>0,'DEADLINE_EXCEEDED');until=time.monotonic()+seconds
    def timeout():
        left=min(remaining(),until-time.monotonic());require(left>0,'DEADLINE_EXCEEDED');return left
    identity=(endpoint['host'],endpoint['port'],path,digest(ca),digest(credential.encode()),audience)
    with _guard:
        now=time.monotonic()
        for old in list(_entries):
            stale=now-old['last']>=_policy['idle_ms']/1000 or now-old['created']>=_policy['lifetime_ms']/1000 or old['count']>=_policy['requests']
            rotated=old['identity'][:3]==identity[:3] and old['identity'][3:5]!=identity[3:5]
            if not old['busy'] and (stale or rotated):old['connection'].close();_entries.remove(old)
        row=next((x for x in _entries if x['identity']==identity and not x['busy']),None)
        reused=row is not None
        if row is None:
            # Evict idle connections to preserve finite headroom for another
            # authorized audience. Never interrupt another in-flight request.
            if len(_entries)>=_policy['connections']:
                idle=sorted((x for x in _entries if not x['busy']),key=lambda x:x['last'])
                if idle:idle[0]['connection'].close();_entries.remove(idle[0])
            require(len(_entries)<_policy['connections'],'OVERLOADED')
            context=ssl.create_default_context(cadata=ca.decode('ascii'));context.minimum_version=ssl.TLSVersion.TLSv1_2
            conn=http.client.HTTPSConnection(endpoint['host'],endpoint['port'],context=context,timeout=timeout())
            row=dict(identity=identity,connection=conn,created=now,last=now,count=0,busy=True);_entries.append(row)
        else:row['busy']=True
    conn=row['connection'];retain=False
    try:
        conn.timeout=timeout()
        if reused:
            require(conn.sock is not None,'NOT_AVAILABLE');conn.sock.settimeout(timeout())
            with span('transport.connection_reuse'):pass
        else:
            with span('transport.connection_open'):conn.connect()
        conn.sock.settimeout(timeout())
        conn.request('POST',path,body,{'Authorization':'Bearer '+credential,'Content-Type':'application/json'})
        conn.sock.settimeout(timeout());response=conn.getresponse()
        sizes=response.headers.get_all('Content-Length',[])
        require(len(sizes)==1 and sizes[0].isdigit() and 0<int(sizes[0])<=maximum and not response.headers.get('Transfer-Encoding'),'NOT_AVAILABLE')
        size=int(sizes[0]);chunks=[];count=0
        while count<size:
            require(response.fp is not None,'NOT_AVAILABLE');response.fp.raw._sock.settimeout(timeout())
            block=response.read1(min(16384,size-count));require(block,'NOT_AVAILABLE')
            chunks.append(block);count+=len(block)
        timeout();retain=response.version>=11 and not response.will_close and conn.sock is not None
        return response.status,b''.join(chunks)
    except (OSError,ValueError,http.client.HTTPException):raise ContractError('NOT_AVAILABLE') from None
    finally:
        with _guard:
            row['count']+=1;row['last']=time.monotonic();row['busy']=False
            if not retain:
                conn.close()
                if row in _entries:_entries.remove(row)
