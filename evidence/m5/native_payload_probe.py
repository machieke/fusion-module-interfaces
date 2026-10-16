"""Full private-result comparison on the pinned native path; safe output only."""
from dataclasses import asdict
import argparse,json,os,secrets,subprocess,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('environment',type=Path)
args=parser.parse_args();source=args.source.resolve();tested=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
assert tested=='bfb0ec8856c932dc2bcbc05b8949c957da8d72cd'
config=json.loads(args.environment.read_text());os.environ.update(config)
os.environ['PYTHONPATH']=str(source)+os.pathsep+config['HIVE_REPO'];sys.path.insert(0,str(source))
from integration.hive.test_m5_integration import setup,act,local
from fusion.contracts import canonical
from fusion.lookup_composition import descriptors
from fusion.registry import descriptor_wire
from fusion.ports import Mutation
from tests.m5_support import SCOPE
reports=[]
with tempfile.TemporaryDirectory(prefix='m5-native-payload-check-') as directory:
    cleanup=[]
    try:
        h,caller,grant,path,body,oracle=setup.__wrapped__(Path(directory),SimpleNamespace(addfinalizer=cleanup.append))
        # Test oracle stays here. Neither the registered query nor consumer receives these refs.
        expected=oracle['order']+[oracle['refs']['pre-'+str(i)] for i in range(3)]
        def compare(command,stage):
            receipt=act(caller,command);assert receipt['status']=='done'
            private=local(h,grant,command)
            wanted={canonical(ref).decode():json.loads(h.atoms.get(ref).bytes) for ref in expected}
            actual={canonical(doc['ref']).decode():doc['record'] for doc in private['documents']}
            assert actual==wanted and len(actual)==len(private['documents'])
            for doc in private['documents']:assert canonical(doc['record'])==h.atoms.get(doc['ref']).bytes
            reports.append({'stage':stage,'roots':len(private['roots']),'payloads':len(private['documents']),
                'exact_reference_set':True,'all_payload_fields_and_canonical_bytes_match':True})
        compare(body,'initial')
        late=h.create('payload-probe-later',kind='task',topic='retrieval-demo',label='PRIVATE-EXACT-'+secrets.token_hex(16))
        expected.append(late)
        grant['grants'][0]['requests']['later']=asdict(h.query(kind='task',topic='retrieval-demo'));path.write_bytes(canonical(grant))
        later={**body,'idempotency_key':'payload-probe-later','params':{'request':'later'}}
        assert act(caller,later)['detail']['error']['code']=='NOT_AVAILABLE'
        h.drain();compare(later,'after-catchup')
        h.search.beginRebuild(Mutation(SCOPE,'payload-probe-rebuild'));h.drain()
        compare({**later,'idempotency_key':'payload-probe-rebuilt'},'after-rebuild')
        h.config['lookup_descriptors']=[descriptor_wire(d) for d in descriptors('detta','atomic-file-fixture')];h.save();h.reopen();h.drain()
        compare({**later,'idempotency_key':'payload-probe-substitute'},'after-substitution')
    finally:
        for finalizer in reversed(cleanup):finalizer()
print(json.dumps({'tested_runtime':tested,'status':'PASS','real':['authenticated native Hive dispatch','local DeTTa','SQLite Relations and primary Search'],
    'fixture':['generated corpus','independent atomic-file Search substitution'],'observations':reports},indent=2))
