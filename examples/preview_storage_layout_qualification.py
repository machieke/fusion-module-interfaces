"""Bounded real DeTTa layout characterization, with generated opaque bytes only.

No cluster, model, native Omega, external endpoint or private store is opened.
Legacy and partitioned roots are fresh and retained under the selected output.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

from fusion.adapters.detta import DettaStorage
from fusion.adapters.detta_layout import CoordinateStorage, LAYOUT
from fusion.contracts import ContractError, canonical, digest, require


def run(binary, expected, output, count):
    binary=Path(binary).resolve();root=Path(output).resolve()
    require(1<=count<=128 and not root.exists(),'CONFLICT')
    require(digest(binary.read_bytes())==expected,'CONFLICT')
    root.mkdir(parents=True)
    report=dict(schema='real-detta-layout-qualification/1',binary_sha256=expected,
        classification='REAL_PINNED_DETTA_NO_MODEL_NO_CLUSTER',additional_live_generations=0,
        count_per_layout=count,scope='synthetic-coordinate-layout',layouts={},process_kill={})
    def save():(root/'report.json').write_bytes(canonical(report))
    save()
    try:
        for name,cls in [('historical',DettaStorage),('coordinate',CoordinateStorage)]:
            store=cls(str(binary),str(root/name));latencies=[];records=[]
            for i in range(count):
                data=('Generated opaque record %03d. '%i+'x'*160).encode();started=time.monotonic()
                locator,receipt=store.put(report['scope'],'generated-'+str(i),data)
                latencies.append(round((time.monotonic()-started)*1000,3))
                require(receipt['provider']=='detta-local-rs/1' and receipt['evidence']['shares']==6
                    and receipt['evidence']['threshold']==4,'NOT_AVAILABLE')
                require(store.get(report['scope'],locator)==data,'NOT_AVAILABLE')
                require(store.availability(report['scope'],locator)['content_hash']==digest(data),'NOT_AVAILABLE')
                records.append((locator,data))
            reopened=cls(str(binary),str(root/name))
            require(all(reopened.get(report['scope'],r)==data for r,data in (records[0],records[-1])),'NOT_AVAILABLE')
            report['layouts'][name]=dict(put_ms=latencies,median_ms=statistics.median(latencies),
                first_eight_mean_ms=statistics.mean(latencies[:8]),last_eight_mean_ms=statistics.mean(latencies[-8:]),
                restart_readback='PASS',shares=6,threshold=4,root_files=sum(1 for p in (root/name).rglob('*') if p.is_file()))
            save()
        crashroot=root/'crash';data=b'Generated immutable interrupted record'
        code="""import os,signal
from fusion.adapters.detta import DettaStorage
from fusion.adapters.detta_layout import CoordinateStorage
original=DettaStorage.put
def kill_after_native(self,*args):
 result=original(self,*args)
 os.kill(os.getpid(),signal.SIGKILL)
DettaStorage.put=kill_after_native
CoordinateStorage(BINARY,ROOT).put(SCOPE,'interrupted',DATA)
"""
        for key,value in [('BINARY',str(binary)),('ROOT',str(crashroot)),('SCOPE',report['scope']),('DATA',data)]:code=code.replace(key,repr(value))
        child=subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=30)
        require(child.returncode==-9,'NOT_AVAILABLE')
        recovered=CoordinateStorage(str(binary),crashroot)
        try:recovered.put(report['scope'],'interrupted',b'changed')
        except ContractError as error:require(error.code=='CONFLICT','CONFLICT')
        else:raise RuntimeError('CHANGED_INTENT_ACCEPTED')
        locator,receipt=recovered.put(report['scope'],'interrupted',data)
        require(recovered.get(report['scope'],locator)==data,'NOT_AVAILABLE')
        report['process_kill']=dict(signal='SIGKILL',stage='after_native_put_before_locator_manifest_seal',
            changed_intent='CONFLICT',same_intent='RECOVERED',actual_backend_receipt=receipt)
        report['status']='PASS'
    except Exception as error:
        report.update(status='FAILED',failure=dict(type=type(error).__name__,code=getattr(error,'code',None)));raise
    finally:save()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','binary-sha256','output'):p.add_argument('--'+name,required=True)
    p.add_argument('--count',type=int,default=48);a=p.parse_args()
    r=run(a.binary,a.binary_sha256,a.output,a.count)
    print(json.dumps(dict(status=r['status'],count_per_layout=r['count_per_layout'],additional_live_generations=0)))
if __name__=='__main__':main()
