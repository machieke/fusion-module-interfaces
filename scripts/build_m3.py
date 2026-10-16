"""Fresh pinned M1/M2 provider recipe plus a separately selected deduction runtime."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_m2 import build as build_m2
from fusion import cognition_contracts as c
from fusion.adapters.pln_deduction import GuardedDeduction


def configure(destination):
    destination=destination.resolve()
    revision=json.loads((destination/'revision-environment.json').read_text())
    deduction=dict(revision,runtime_profile=c.RUNTIME)
    path=destination/'deduction-environment.json';path.write_text(json.dumps(deduction,indent=2)+'\n')
    env=json.loads((destination/'environment.json').read_text());env['M3_DEDUCTION_ENV']=str(path)
    (destination/'environment.json').write_text(json.dumps(env,indent=2)+'\n')
    (destination/'m3-build.json').write_text(json.dumps({'base_build':json.loads((destination/'build.json').read_text()),
        'deduction_profile':GuardedDeduction(path).profile(),'recipe_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('destination',type=Path)
    args=parser.parse_args();build_m2(args.destination);configure(args.destination)
