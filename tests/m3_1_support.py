"""Explicit closure-profile configuration; all fixture/provider labels retained."""
from dataclasses import replace
from fusion import delivery_contracts as d, cognition_contracts as c
from fusion.private import descriptors as private_descriptors
from fusion.cognition import descriptors, contract, select
from fusion.registry import descriptor_wire,selection_token
from tests.m3_support import CognitionHarness,SCOPE

class ClosureHarness(CognitionHarness):
    def reopen(self):
        # Do not open an old-profile journal just to construct a fresh test config.
        if not hasattr(self,'kernel_fixture'):return self
        if not hasattr(self,'closure_configured'):
            providers=private_descriptors(closure=True)
            if not self.real: providers=[replace(x,receipt_providers=frozenset({'contract-fixture-files/1'})) for x in providers]
            catalogue=descriptors(self.provider,closure=True)
            selected=select(catalogue,'belief.revision',closure=True)
            self.config.update(delivery_closure=d.CONFIG,private_descriptors=[descriptor_wire(x) for x in providers],
                cognition_descriptors=[descriptor_wire(x) for x in catalogue],
                evidence_consumer={'principal':'owner','provider':selected.provider,'profile':c.BELIEF_PROFILE,'selection':selection_token(selected)})
            methods=self.config['principals']['owner']['scopes'][SCOPE]
            methods.extend(['episodic.memory.acknowledgeDelivery','attention.submitFeedback','attention.resolveFeedback',
                            'inference.control.readProgress','inference.control.reconcile'])
            self.closure_configured=True;self.save()
        return super().reopen()
