"""Current authority and same-CA renewal on retained native-created records.

No business submission, native generation, foreign journal reads or fixture
payloads. Detailed synthetic refs stay in the operator's private artifact path.
"""
import argparse,base64,json,secrets,subprocess
from pathlib import Path
from fusion.contracts import canonical,digest,require
from integration.single_node.reference_ops import Operator,PYTHON
from integration.single_node.preview_scope_qualification import Qualification
from integration.single_node.sustained_qualification import Runner


def qualify(op,directory,material,native_report):
    prior=json.loads(Path(native_report).read_bytes())
    require(prior['status']=='PASS' and prior['namespace']==op.namespace,'CONFLICT')
    q=Qualification(op,directory,material);q.report['synthetic_private_records']=0
    q.report['native_report_sha256']=digest(Path(native_report).read_bytes())
    api=Runner.__new__(Runner);api.op=op
    def snapshots():
        rows={}
        for role in ('omega-agent','omega-agent-b'):
            rows[role]={}
            for item in api.call(role,'list'):
                value=api.call(role,'observe',item['session'],'--content')
                # Retain incomplete/uncertain attempts too. Rotation is an
                # authority check, never permission to complete or retry them.
                rows[role][item['session']]=value
        return rows
    def models():
        script="""import json
from pathlib import Path
from fusion.model_service import ModelService
from fusion.contracts import canonical,digest
path=Path('/run/fusion/owner.json');cfg=json.loads(path.read_bytes())
paths=[path]+[Path(x['directory'])/'owner.json' for x in cfg.get('scope_routes',{}).get('scopes',{}).values()]
rows=[ModelService.inspect(p) for p in paths]
print(json.dumps(dict(partitions=len(rows),calls=sum(map(len,rows)),reserved=sum(r['reserved'] for group in rows for r in group),captured=sum(r['response'] is not None for group in rows for r in group),owner_snapshot_digest=digest(canonical(rows)))))"""
        return json.loads(op.k('exec','fusion-model-0','--',PYTHON,'-c',script,timeout=25))
    try:
        op.owned();before=snapshots();accounting=models();refs={};heads={}
        for role in ('omega-agent','omega-agent-b'):
            item=next(x for x in prior['inputs'] if x['role']==role and x['command'].startswith('remember The synthetic private'))
            refs[role]=Runner.object(item['observed']['result']['projection'])['memory']['target']['payload']
            q.case(role+'-native-private-get',q.call(role,'get',ref=refs[role]))
            heads[role]=q.case(role+'-native-private-head',q.call(role,'head'))
            q.case(role+'-wrong-credential',q.call(role,'head',wrong=True),'UNAUTHORIZED')
        for actor,target in [('omega-agent','omega-agent-b'),('omega-agent-b','omega-agent')]:
            for method in ('get','getMany','availability','head','readCommits'):
                q.case(actor+'-denied-'+target+'-'+method,q.call(actor,method,scope=refs[target]['scope_ref'],
                    ref=refs[target],through=heads[target]),'UNAUTHORIZED')
        q.report['original_heads']=heads;q.save()
        storage=q.secret('fusion-storage');caller=q.secret('omega-agent')
        token=base64.b64encode(secrets.token_hex(32).encode()).decode()
        storage['data']['cog-caller-A-token']=token;q.put_secret(storage)
        q.report['provider_credential_replacement']=q.replace('fusion-storage');q.save()
        q.case('old-A-authority-revoked',q.call('omega-agent','get',ref=refs['omega-agent']),'UNAUTHORIZED')
        q.case('B-unaffected-by-A-rotation',q.call('omega-agent-b','get',ref=refs['omega-agent-b']))
        caller['data']['atom-A-token']=token;q.put_secret(caller)
        q.report['caller_credential_replacement']=q.replace('omega-agent');q.save()
        q.case('new-A-current-authority',q.call('omega-agent','get',ref=refs['omega-agent']))
        certdir=Path(material).resolve()/'integrated-rotation';certdir.mkdir(mode=0o700)
        def ssl(*args):subprocess.run(['openssl',*map(str,args)],cwd=certdir,check=True,capture_output=True,timeout=20)
        ssl('req','-newkey','rsa:2048','-nodes','-keyout','server.key','-out','server.csr','-subj','/CN=fusion-storage')
        (certdir/'extensions').write_text('subjectAltName=DNS:fusion-storage.'+op.namespace+'.svc.cluster.local\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n')
        ssl('x509','-req','-in','server.csr','-CA',Path(material).resolve()/'ca.crt','-CAkey',Path(material).resolve()/'ca.key',
            '-set_serial',str(secrets.randbits(120)),'-out','server.crt','-days','7','-extfile','extensions')
        storage=q.secret('fusion-storage');old=digest(base64.b64decode(storage['data']['tls.crt']))
        for key,name in [('tls.crt','server.crt'),('tls.key','server.key')]:storage['data'][key]=base64.b64encode((certdir/name).read_bytes()).decode()
        q.put_secret(storage);q.report['certificate_replacement']=q.replace('fusion-storage')
        q.report['leaf_sha256']={'before':old,'after':digest((certdir/'server.crt').read_bytes())}
        require(q.report['leaf_sha256']['before']!=q.report['leaf_sha256']['after'],'CONFLICT')
        for role in refs:
            q.case(role+'-renewed-same-CA-read',q.call(role,'get',ref=refs[role]))
            require(q.case(role+'-unchanged-head',q.call(role,'head'))==heads[role],'CONFLICT')
        after=snapshots();final=models();require(before==after and accounting==final,'CONFLICT')
        q.report.update(status='PASS',retained_captures_exact=True,model_accounting_unchanged=True,
            model_calls=final['calls'],reserved=final['reserved'],captured=final['captured'],new_native_inputs=0,
            new_storage_records=0,automatic_resubmission=0,ca_unchanged=True,private_refs_publication='FORBIDDEN')
    except BaseException as error:
        q.report.update(status='FAIL',failure=dict(type=type(error).__name__,code=getattr(error,'code',None),detail=str(error)[-1200:]));raise
    finally:op.quiesce();q.report['quiesced']=True;q.save()
    return q.report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('kubeconfig','context','namespace','directory','material','native-report'):p.add_argument('--'+name,required=True)
    a=p.parse_args();v=qualify(Operator(a.kubeconfig,a.context,a.namespace),a.directory,a.material,a.native_report)
    print(json.dumps(dict(status=v['status'],additional_live_generations=0)))
