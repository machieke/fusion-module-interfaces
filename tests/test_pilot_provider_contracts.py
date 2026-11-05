"""Finite descriptor/wire compatibility, not deployed/native provider evidence."""
import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from fusion.contracts import ContractError,canonical
from fusion.registry import descriptors,select,descriptor_wire
from fusion.reference_inspect_contracts import descriptor
from fusion.preview_inspect import selections,Client,PROFILE
from fusion.execution_envelope import PROFILE as ENVELOPE
from sdk.provider_contracts import generated,ROOT

class ReferenceCompatibility(unittest.TestCase):
    def test_generated_contract_drift_fails_closed(self):
        actual=(ROOT/'sdk/go/inspectprovider/contract.json').read_bytes()
        self.assertEqual(actual,canonical(generated())+b'\n')
        self.assertEqual(generated()['descriptor'],descriptor_wire(descriptor()))

    def test_historical_default_and_numerical_profiles_unchanged(self):
        self.assertEqual(selections({}),select(descriptors()))
        selected=selections(dict(envelopes=ENVELOPE,execution_descriptor=descriptor_wire(descriptor())))
        self.assertEqual(selected['execution'],descriptor())
        self.assertEqual({k:v for k,v in selected.items() if k!='execution'},
                         {k:v for k,v in select(descriptors()).items() if k!='execution'})
        self.assertEqual(descriptor().profiles,frozenset({'inspect-atom/2'}))

    def test_weaker_profile_guarantees_features_and_size_refused(self):
        original=descriptor_wire(descriptor())
        variants=[('profiles',['inspect-atom/1']),('guarantees',['scoped','idempotent']),
                  ('operations',['submit','status']),('features',[]),('max_payload_bytes',4095),
                  ('version','2.0.0')]
        for key,value in variants:
            with self.subTest(key=key):
                changed=copy.deepcopy(original);changed[key]=value
                with self.assertRaises(ContractError):selections(dict(envelopes=ENVELOPE,execution_descriptor=changed))
        with self.assertRaises(ContractError):selections(dict(execution_descriptor=original))

    def test_selected_endpoint_and_descriptor_freeze_at_client_construction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);ca=root/'ca';ca.write_text('synthetic trust bytes; no connection')
            endpoint=dict(host='fusion-inspect-go',port=8443,ca_file=str(ca))
            cfg=dict(profile=PROFILE,fallback=False,scope='synthetic-reference',principal='A',envelopes=ENVELOPE,
                execution_descriptor=descriptor_wire(descriptor()),ports={k:dict(endpoint=endpoint,credential='generated-test-secret')
                    for k in ('execution','agent.messaging')})
            path=root/'caller.json';path.write_bytes(canonical(cfg));client=Client(path)
            cfg['ports']['execution']['endpoint']['host']='another-service';path.write_bytes(canonical(cfg))
            with patch('fusion.preview_inspect.invoke') as exchange:
                with self.assertRaisesRegex(ContractError,'CONFLICT'):client.events('accepted-job')
                exchange.assert_not_called()
