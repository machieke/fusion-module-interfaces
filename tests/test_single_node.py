"""Service boundary unit tests. Fixture kernel/backend, never native evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fusion import neoclaw_contracts as c
from fusion.contracts import ContractError, canonical, digest, encode
from fusion.neoclaw import NalService
from fusion.neoclaw_services import COMPOSITION, OwnerService, RoutedNetwork, service_hostname
from fusion.neoclaw_transport import Network, json_loads
from fusion.registry import selection_token
from tests.neoclaw_support import Harness, FixtureKernel


class ServiceBoundaries(unittest.TestCase):
    def error(self,code,fn,*args,**kwargs):
        with self.assertRaises(ContractError) as caught:fn(*args,**kwargs)
        self.assertEqual(caught.exception.code,code)

    def test_dns_is_explicit_and_does_not_expand_historical_loopback_profile(self):
        host='fusion-storage.synthetic.svc.cluster.local'
        self.assertEqual(service_hostname(host),host)
        for invalid in ['localhost','127.0.0.1','https://example.org','example.org',host+'/path',host+':8443']:
            self.error('UNSUPPORTED_PROFILE',service_hostname,invalid)
        self.error('UNSUPPORTED_PROFILE',Network,dict(host=host,port=8443,ca_file='unused'),'token',{})
        cfg=dict(service_composition=COMPOSITION,fallback=True)
        self.error('UNSUPPORTED_PROFILE',RoutedNetwork,cfg,{})

    def test_separated_execution_has_no_storage_or_mailbox_journal(self):
        h=Harness();self.addCleanup(h.close)
        owners=h.service();atoms_for,mailbox=owners.atoms_for,owners.mailbox;owners.close()
        for key in ('atoms_database','messages_database','da_root','atom_records'):h.config.pop(key)
        h.save()
        svc=NalService(h.config_path,kernel=FixtureKernel(),atoms_for=atoms_for,mailbox=mailbox)
        self.addCleanup(svc.close)
        self.assertTrue(svc.separate_owners)
        caller=h.caller();self.addCleanup(caller.close)
        poll=caller._request('agent.messaging','poll',dict(route='reply-A'))
        self.error('UNSUPPORTED_OPERATION',svc.invoke,h.config['principals']['A']['credential'],poll)
        self.error('UNSUPPORTED_PROFILE',NalService,h.config_path,atoms_for=atoms_for)
        h.config['atoms_database']='foreign.sqlite';h.save()
        self.error('UNSUPPORTED_PROFILE',NalService,h.config_path,atoms_for=atoms_for,mailbox=mailbox)

    def test_completion_port_auth_binding_duplicates_and_live_revocation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);file=root/'config.json'
            cfg=dict(service_composition=COMPOSITION,sharing='generated-shareable',capacity=8,
                     messages_database=str(root/'mailbox.sqlite'),
                     principals={'worker':dict(credential='worker',scopes={c.SCOPE:['execution.completion']}),
                                 'A':dict(credential='caller',scopes={c.SCOPE:['agent.messaging.poll']})},
                     routes={'reply-A':dict(scope=c.SCOPE,owner='A')})
            file.write_bytes(canonical(cfg));owner=OwnerService(file,'fusion-messaging')
            request=dict(profile='completion-delivery/1',selection=selection_token(owner.chosen['agent.messaging']),
                scope_ref=c.SCOPE,route='reply-A',delivery_id='job-1',
                completion=dict(job_id='job-1',correlation_id='correlation-1',causation_id='cause-1',result=None,error='NOT_AVAILABLE'))
            self.error('UNAUTHORIZED',owner.private,'caller','/ports/completion',request)
            first=owner.private('worker','/ports/completion',request)
            self.assertEqual(first,owner.private('worker','/ports/completion',request))
            self.assertEqual(first['request_digest'],digest(canonical(request)))
            for changes,code in [({'selection':'0'*64},'UNSUPPORTED_PROFILE'),({'scope_ref':'private'},'UNAUTHORIZED'),
                                  ({'unexpected':1},'INVALID_ARGUMENT'),({'delivery_id':'other'},'INVALID_ARGUMENT')]:
                self.error(code,owner.private,'worker','/ports/completion',{**request,**changes})
            bad=copy.deepcopy(request);bad['completion']['result']={}
            self.error('INVALID_ARGUMENT',owner.private,'worker','/ports/completion',bad)
            cfg['principals']['worker']['scopes'][c.SCOPE]=[];file.write_bytes(canonical(cfg))
            self.error('UNAUTHORIZED',owner.private,'worker','/ports/completion',request)
            self.assertEqual({p.name for p in root.glob('*.sqlite')},{'mailbox.sqlite'})

    def test_private_create_validates_before_backend_and_preserves_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);file=root/'config.json'
            cfg=dict(service_composition=COMPOSITION,sharing='generated-shareable',capacity=8,
                atoms_database=str(root/'atoms.sqlite'),detta_binary='unused',da_root=str(root/'da'),
                principals={'worker':dict(credential='worker',scopes={c.SCOPE:['atom.storage.create']})},routes={})
            file.write_bytes(canonical(cfg))
            with patch('fusion.neoclaw_services.DettaStorage') as backend:
                owner=OwnerService(file,'fusion-storage')
                request=dict(profile='immutable-bytes/1',selection=selection_token(owner.chosen['atom.storage']),
                    scope_ref=c.SCOPE,idempotency_key='write-1',intent_digest=None,content_type='s01-result',bytes=encode(b'payload'))
                for changes,code in [({'selection':'0'*64},'UNSUPPORTED_PROFILE'),({'scope_ref':'private'},'UNAUTHORIZED'),
                                     ({'bytes':'invalid-base64'},'INVALID_ARGUMENT'),({'intent_digest':True},'INVALID_ARGUMENT')]:
                    self.error(code,owner.private,'worker','/ports/atom-create',{**request,**changes})
                backend.return_value.put.assert_not_called()

    def test_bounded_json_depth_and_duplicate_keys_across_python_versions(self):
        self.assertEqual(json_loads(b'{"ok":[1]}'),{'ok':[1]})
        for value in ['['*1500+']'*1500,'{"a":1,"a":2}','{"value":NaN}']:
            self.error('INVALID_ARGUMENT',json_loads,value)


if __name__=='__main__':unittest.main()
