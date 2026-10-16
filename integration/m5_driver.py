"""Disposable writer/recovery driver. Only the test process reads the oracle file."""
from dataclasses import asdict
import argparse,json,os,signal
from pathlib import Path
from fusion.contracts import canonical
from fusion.ports import Mutation
from tests.m5_support import LookupHarness,SCOPE

def main():
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('operation',choices=['seed','create','relation','catchup','rebuild'])
    parser.add_argument('--stage');parser.add_argument('--seed',type=int,default=11);parser.add_argument('--search',default='sqlite');parser.add_argument('--real',action='store_true')
    args=parser.parse_args()
    def hook(stage):
        if stage==args.stage:
            (args.root/'paused').write_text(stage);os.kill(os.getpid(),signal.SIGSTOP)
    h=LookupHarness(args.root,real=args.real,search=args.search,hook=hook)
    if args.operation=='seed':
        oracle=h.seed(args.seed);h.drain();(args.root/'oracle.json').write_bytes(canonical(oracle));(args.root/'oracle.json').chmod(0o600)
        requests={'positive':asdict(h.query(oracle['head'],kind='task',topic='retrieval-demo')),
                  'empty':asdict(h.query(oracle['head'],kind='task',topic='no-match-'+str(args.seed)))}
        (args.root/'requests.json').write_bytes(canonical(requests));(args.root/'requests.json').chmod(0o600)
    elif args.operation=='create':h.create('lost-ack',kind='task',topic='recovery')
    elif args.operation=='relation':
        a=h.create('endpoint-a',kind='task');b=h.create('endpoint-b',kind='prerequisite')
        h.relations.assertRelation(Mutation(SCOPE,'lost-relation-ack'),'requires/1',(('dependent',a),('prerequisite',b)),True)
    elif args.operation=='catchup':h.search.catchUp(SCOPE,2)
    elif args.operation=='rebuild':h.search.beginRebuild(Mutation(SCOPE,'interrupted-rebuild'))
    h.close()
if __name__=='__main__':main()
