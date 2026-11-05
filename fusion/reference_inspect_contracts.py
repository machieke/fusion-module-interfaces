"""Published descriptor for the independently implemented Go inspection owner.

This is normative contract data only. It executes no provider transition.
The native generated-artifact bound is 4096; the reference does not claim /1.
"""
from .registry import Descriptor
from .execution_envelope import PROFILE


def descriptor():
    return Descriptor('go-immutable-inspect-reference','execution','1.0.0','0.1.0',
        frozenset({'inspect-atom/2'}),frozenset({'submit','status','result'}),
        frozenset({'process-restart','scoped','idempotent'}),4096,
        features=frozenset({PROFILE}),receipt_providers=frozenset({'detta-local-rs/1','contract-fixture-files/1'}))
