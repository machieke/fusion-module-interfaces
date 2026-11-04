"""Fenced archive/capture continuity using the existing quiesced restore recipe.

The original result report chooses a read reference only; it cannot supply the
returned bytes. No native worker, model, encoder, task, socket or chain effect
starts in the clone. Backup/Secret files remain private operator artifacts.
"""
import argparse,json
from pathlib import Path
from fusion.contracts import canonical,require,digest
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.sustained_restore_qualification import drill

READ='''import json,sys,time
from pathlib import Path
from fusion.contracts import digest,canonical,require
from fusion.preview_client import AtomFeedClient,Endpoint
from fusion.registry import descriptor_read
from fusion.archive_contracts import PROFILE
q=json.load(sys.stdin);cfg=json.loads(Path('/run/fusion/cognitive-owner.json').read_bytes());c=json.loads(Path('/config/component.json').read_bytes())
d=next(descriptor_read(x) for x in cfg['catalogue'] if PROFILE in x['profiles'])
client=AtomFeedClient(Endpoint(c['peers']['fusion-storage'],c['https_port'],'/secrets/ca.crt'),cfg['principals']['archive-operator']['credential'],
 'archive-operator',q['ref']['scope_ref'],d,deadline_ms=time.time_ns()//1000000+30000,composition=cfg['composition'],feed_profile=cfg['feed_profile'])
item=client.get(q['ref']);require(digest(item.bytes)==q['ref']['digest'],'CONFLICT')
print(json.dumps({'bytes':len(item.bytes),'payload_digest':digest(item.bytes),'ref':item.ref,'restore_fenced':Path('/state/restore-fence.json').exists(),
 'head':client.head(q['ref']['scope_ref'])}))
'''

def qualify(a):
    images=json.loads(Path(a.images).read_bytes());caller=next(i for i in images['images'] if i['kind']=='caller')
    maintenance=caller['repository']+'@'+caller['manifest_digest']
    previous=json.loads(Path(a.native_report).read_bytes());ref=previous['archive_maintenance']['hydrated_payload']
    def readback(clone):
        result=json.loads(clone.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',READ,data=json.dumps(dict(ref=ref))))
        require(result['restore_fenced'] and result['ref']==ref,'CONFLICT')
        # The same endpoint must refuse archive publication, even with fresh
        # maintenance authority. It cannot turn a restored segment into work.
        script=READ.replace("item=client.get(q['ref']);", "from fusion.ports import Mutation\nclient.publishArchive(Mutation(q['ref']['scope_ref'],'forbidden-restore-publication'),0,client.head(q['ref']['scope_ref']),1)\nitem=client.get(q['ref']);")
        try:clone.k('exec','-i','fusion-storage-0','--',PYTHON,'-c',script,data=json.dumps(dict(ref=ref)))
        except RuntimeError as error:require('UNAUTHORIZED' in str(error),'CONFLICT')
        else:require(False,'CONFLICT')
        return dict(early_archived_payload='PASS',read=result,archive_effect_refused=True)
    return drill(Operator(a.kubeconfig,a.context,a.original),Operator(a.kubeconfig,a.context,a.clone),a.values,a.chart,a.directory,
                 maintenance_image=maintenance,images=images,after_restore=readback)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','original','clone','values','chart','directory','images','native-report'):p.add_argument('--'+name,required=True)
    a=p.parse_args();result=qualify(a);print(json.dumps(dict(status=result['status'],additional_live_generations=0)))
