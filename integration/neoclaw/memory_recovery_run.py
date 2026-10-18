"""Actual E5/Chroma/DeTTa/native HTTPS read killed at three capture boundaries."""
import argparse
import json
from pathlib import Path
import signal
import time
from fusion.contracts import canonical,require
from .controlled_run import ControlledRun
from .memory_composition import configure
from .memory_corpus import QUERY
from .memory_run import real_corpus,report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',required=True);args=parser.parse_args()
    corpus=real_corpus();run=ControlledRun('network',['query '+QUERY,'query '+QUERY,''],search={'boundary':'recorded-response'})
    try:
        run.model['expected_feedback']={};run.save();configure(run,corpus,'real');run.operator()
        captures=[]
        for stage in ('after_candidate_capture','after_payload_validation','after_native_result_capture'):
            marker=Path(run.app['failpoint_marker']);marker.unlink(missing_ok=True)
            run.app['pause_at']=stage;run.save();process=run.start()
            until=time.monotonic()+35  # Startup/model loading precedes occurrence acceptance.
            while not marker.exists() and process.poll() is None and time.monotonic()<until:time.sleep(.03)
            require(marker.exists(),'NOT_AVAILABLE')
            run.kill(process);require(process.returncode==-signal.SIGKILL)
            captures.append(dict(stage=stage,state=report(run)))
        run.app.pop('pause_at');run.save();code,status=run.finish(run.start())
        require(code==0 and status=={'status':'BOUNDED_STOP'},'NOT_AVAILABLE');final=report(run)
        occurrence=captures[0]['state']['occurrences'][0]
        for capture in captures[1:]:
            item=capture['state']['occurrences'][0]
            require(item['id']==occurrence['id'] and item['deadline']==occurrence['deadline'],'CONFLICT')
            require(capture['state']['read_receipts'][0]['candidates']==captures[0]['state']['read_receipts'][0]['candidates'],'CONFLICT')
        require(final['occurrences'][0]['result']==captures[-1]['state']['occurrences'][0]['result'],'CONFLICT')
        require(final['read_receipts'][0]['queries']==1 and final['read_receipts'][1]['queries']==1,'CONFLICT')
        require(final['occurrences'][0]['id']!=final['occurrences'][1]['id'],'CONFLICT')
        require(final['observations'][1]['feedback']==final['observations'][2]['feedback'],'CONFLICT')
        Path(args.evidence).write_bytes(canonical(dict(embedding='real-local-E5',placement='authenticated same-host HTTPS',captures=captures,final=final,
            deadline_unchanged=True,first_candidate_query_count=1,operator_business_configuration_edits=0)))
    except BaseException:
        Path(args.evidence+'.failure.log').write_text((run.h.root/'native.log').read_text() if (run.h.root/'native.log').exists() else 'startup failed')
        raise
    finally:run.close()

if __name__=='__main__':main()
