"""Supplemental evidence on the exact tested runtime; no private bytes/hashes emitted."""
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);parser.add_argument('environment',type=Path)
args=parser.parse_args();source=args.source.resolve()
commit=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
assert commit=='bfb0ec8856c932dc2bcbc05b8949c957da8d72cd'
sys.path.insert(0,str(source));os.environ.update(json.loads(args.environment.read_text()))
from tests.m3_support import CognitionHarness
from tests.m5_support import LookupHarness,SCOPE
from fusion.ports import Mutation
cases=[]
for attention in ('sqlite','atomic-file-fixture'):
    old=CognitionHarness(provider=attention)
    try:
        entry,_,episode=old.generated();old.stimulate(entry)
        request=old.request(old.workset([entry]),attempts=1)
        previous=old.controller.step(request)
        assert previous['counts']['reserved']==1 and previous['counts']['refused']==1
        def protected_state():
            return {str(p.relative_to(old.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in (old.root/'private').rglob('*') if p.is_file()}
        before=protected_state()
        for search in ('sqlite','atomic-file-fixture'):
            h=LookupHarness(real=True,search=search)
            try:
                oracle=h.seed();h.drain();q=h.query(oracle['head'],kind='task',topic='retrieval-demo')
                result=h.consumer('before').lookup(Mutation(SCOPE,'first'),q)
                h.search.beginRebuild(Mutation(SCOPE,'rebuild'));h.drain()
                rebuilt=h.consumer('after').lookup(Mutation(SCOPE,'second'),q)
                assert result['roots']==rebuilt['roots']==oracle['order']
                assert protected_state()==before
                assert old.controller.step(request)==previous
                assert protected_state()==before
                cases.append({'attention':attention,'search':search,'reserved_before':1,'reserved_after':1,
                    'episodes_beliefs_attention_and_inference_files_unchanged':True,
                    'budget_and_result_replay_unchanged':True,'lookup_and_rebuild':'PASS'})
            finally:h.close()
    finally:old.close()
print(json.dumps({'tested_runtime':commit,'status':'PASS','classification':{
    'real':['DeTTa lookup bytes','SQLite owned journals'],
    'fixture':['generated corpus','guard-only revision/refusing deduction for pre-existing cognitive state','atomic-file attention/Search alternatives'],
    'new_cognition_during_lookup':False},'cases':cases},indent=2))
