"""Exact registered synthetic workflow artifact on the existing chain profile.

The operator registers an observed inspection, independently of the caller.
The owner revalidates both stored artifact and actual inspect result on every
operation. No prompt, episode ledger, model response or caller-provided code is
part of the fixed commitment term. Keys remain only with this owner.
"""
import importlib.util,json,time,re
from dataclasses import asdict
from pathlib import Path
from .contracts import canonical,digest,require,label,validate_ref,ContractError
from .ports import ApprovedCommitment,Mutation
from .policy import Policy
from .registry import selection_token
from .adapters.f1r3 import F1R3HTTP
from .adapters.f1r3_m4 import GeneratedCommitments,DESCRIPTOR
from .adapters.f1r3_signing import signer
from .preview_inspect import Client as Inspection
from .preview_atoms import client as atoms_client
from .preview_artifact_contracts import record as artifact_record,encode as artifact_bytes,PROFILE as ARTIFACT
from .client import Peer
from .chain_services import observation
from .preview_transport import invoke

PROFILE='synthetic-workflow-commitment/1'
ROUTE='/preview/commitment'


def registration(value,scope):
    require(type(value) is dict and set(value)=={'profile','approved','binding','job_id','result','artifact','principal'},'INVALID_ARGUMENT')
    require(value['profile']==PROFILE and scope.startswith('synthetic-') and value['principal'] in ('A','B'),'UNAUTHORIZED')
    require(label(value['job_id']) and type(value['binding']) is dict)
    require(type(value['approved']) is dict and set(value['approved'])=={'scope_ref','result_ref','commitment_digest','approval_record'})
    require(label(value['approved']['approval_record']))
    from .responses import atom_write
    from .registry import select,descriptors
    atom_write(value['result'],scope,select(descriptors())['execution'])
    validate_ref(value['artifact'],scope)
    require('authority' in value['binding'])
    approved=ApprovedCommitment(**value['approved'])
    require(approved.scope_ref==scope and approved.result_ref==value['result']['ref'] and
        approved.result_ref['digest']==approved.commitment_digest,'CONFLICT')
    require(value['artifact']['scope_ref']==scope,'UNAUTHORIZED')
    authority=value['binding']['authority']
    require(type(authority) is dict and set(authority)=={'purpose','expires_at_ms','artifact_digest'} and
        authority['purpose']=='approved-synthetic-agent-artifact' and authority['artifact_digest']==value['artifact']['digest'] and
        type(authority['expires_at_ms']) is int,'UNAUTHORIZED')
    return approved


class Ports:
    def __init__(self,path,hook=lambda _:None):self.path,self.hook=Path(path),hook
    def invoke(self,path,credential,q):
        require(path==ROUTE and type(q) is dict and set(q)=={'profile','selection','registration','operation','body'})
        require(q['profile']==PROFILE and q['selection']==selection_token(DESCRIPTOR),'UNSUPPORTED_PROFILE')
        op=q['operation'];require(op in ('submit','observe','intent'),'UNSUPPORTED_OPERATION')
        policy=Policy(self.path);principal=policy.authenticate(credential);cfg=policy.current();scope=cfg['scope']
        permission='consensus.finality.'+('observe' if op=='intent' else op)
        policy.check(principal,scope,permission);reg=cfg.get('registration');require(reg is not None,'UNAUTHORIZED')
        approved=registration(reg,scope);require(q['registration']==digest(canonical(reg)),'CONFLICT')
        binding=reg['binding']
        def authorize():
            current=policy.current();require(current.get('registration')==reg and policy.authenticate(credential)==principal,'UNAUTHORIZED')
            policy.check(principal,scope,permission)
            require(time.time_ns()//1_000_000<binding['authority']['expires_at_ms'],'UNAUTHORIZED')
            peer=Peer(Inspection(current['inspection']),scope,'inspect-'+reg['principal'])
            result=peer.result(reg['job_id']);status=peer.status(reg['job_id'])
            require(result==reg['result'] and status['execution']=='succeeded' and status['error'] is None,'NOT_AVAILABLE')
            atoms=atoms_client(current['atoms']);item=atoms.get(reg['artifact']);record=artifact_record(json.loads(item.bytes),scope)
            require(item.content_type==ARTIFACT and item.bytes==artifact_bytes(record) and record['sender']==reg['principal'],'UNAUTHORIZED')
            output=atoms.get(approved.result_ref)
            require(output.content_type=='application/json' and output.bytes==canonical(dict(digest=digest(item.bytes),length=len(item.bytes),operation='inspect_atom',provider_version='0.1.0')) and
                digest(output.bytes)==approved.commitment_digest,'UNAUTHORIZED')
        def signing(plan):
            require(digest(Path(cfg['protobuf']).read_bytes())==binding['protobuf_sha256'],'UNSUPPORTED_PROFILE')
            spec=importlib.util.spec_from_file_location('preview_signing_pb2',cfg['protobuf']);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            return signer(cfg['signer_file'],binding['signer'],module.DeployDataProto)(plan)
        authorize();owner=GeneratedCommitments(F1R3HTTP(cfg['node_endpoint']),signing,cfg['journal'],approved,binding,authorize,self.hook)
        if op=='submit':
            require(set(q['body'])=={'command'})
            command=Mutation(**q['body']['command'])
            require(command.scope_ref==scope and command.idempotency_key==binding['operation'] and command.intent_digest is None,'CONFLICT')
            # Always observe a persisted signed intent before any replay of its
            # identical bytes. A matching included/finalized effect needs no RPC.
            saved=owner.saved_intent()
            prior=owner.observe(saved['deploy_id']) if saved else None
            result=prior if prior and prior.effect_finality in ('included','finalized','rejected') else owner.submit(command,approved)
            value=asdict(result)
        elif op=='observe':
            require(set(q['body'])=={'deploy_id'});value=asdict(owner.observe(q['body']['deploy_id']))
        else:
            require(q['body']=={});value=owner.saved_intent()
        authorize()
        return dict(profile=PROFILE,request_digest=digest(canonical(q)),value=value)


class Client:
    def __init__(self,path):
        self.path=Path(path);self.cfg=json.loads(self.path.read_text());self.reg=self.cfg['registration']
        registration(self.reg,self.reg['approved']['scope_ref'])
        self.frozen=self.binding(self.cfg)
    @staticmethod
    def binding(cfg):
        return canonical(dict(endpoint=cfg['endpoint'],ca_sha256=digest(Path(cfg['endpoint']['ca_file']).read_bytes()),registration=cfg['registration']))
    def validate_observation(self,value):
        observation(value)
        if value['effect_finality'] in ('included','finalized'):
            from .adapters.f1r3_m4 import NAMESPACE,expected_expr
            operation=self.reg['binding']['operation'];hash_value=self.reg['approved']['commitment_digest'];e=value['evidence']
            require(e.get('value')==dict(namespace=NAMESPACE,operation=operation,digest=hash_value) and
                e['effect']['expr']==expected_expr(operation,hash_value),'NOT_AVAILABLE')
        return value
    def call(self,operation,body):
        current=json.loads(self.path.read_text());require(self.binding(current)==self.frozen,'CONFLICT')
        q=dict(profile=PROFILE,selection=selection_token(DESCRIPTOR),registration=digest(canonical(self.reg)),operation=operation,body=body)
        reply=invoke(current,ROUTE,q,time.time_ns()//1_000_000+30000)
        require(type(reply) is dict and set(reply)=={'profile','request_digest','value'} and reply['profile']==PROFILE and reply['request_digest']==digest(canonical(q)),'NOT_AVAILABLE')
        if operation!='intent':
            self.validate_observation(reply['value'])
            if operation=='observe':require(reply['value']['deploy_id']==body['deploy_id'],'NOT_AVAILABLE')
        elif reply['value'] is not None:
            value=reply['value'];require(type(value) is dict and set(value)=={'deploy_id','read_name','receipt'},'NOT_AVAILABLE')
            require(type(value['deploy_id']) is str and re.fullmatch('[0-9a-f]{128,144}',value['deploy_id']) is not None and
                type(value['read_name']) is str and re.fullmatch('[0-9a-f]{64}',value['read_name']) is not None,'NOT_AVAILABLE')
            if value['receipt'] is not None:
                self.validate_observation(value['receipt']);require(value['receipt']['deploy_id']==value['deploy_id'],'NOT_AVAILABLE')
        return reply['value']
