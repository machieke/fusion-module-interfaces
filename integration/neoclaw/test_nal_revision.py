"""Real pure NAL oracle plus explicitly injected malformed/timeout guards."""
import json
import os
from pathlib import Path
from fractions import Fraction
import subprocess
import time
import unittest
from unittest.mock import patch
from fusion import nal_memory_contracts as c
from fusion.contracts import ContractError,canonical
from fusion.adapters.neoclaw_revision import NativeTruthRevision
from tests.neoclaw_support import RUNTIME


class NativeNalRevision(unittest.TestCase):
    def setUp(self):self.math=NativeTruthRevision(RUNTIME)
    def test_original_native_values_order_and_cap(self):
        cases=[(('1','0.5','1','0.5'),(1,Fraction(2,3))),
            (('1','0.5','0','0.5'),(Fraction(1,2),Fraction(2,3))),
            (('0.75','0.5','0.25','0.75'),(Fraction(3,8),Fraction(4,5))),
            (('0.75','0.99','0.25','0.99'),(Fraction(1,2),Fraction(99,100))),
            (('0','0','1','0.5'),(1,Fraction(1,2)))]
        evidence=[]
        for (a,b,d,e),expected in cases:
            for pair in ((c.stv(a,b),c.stv(d,e)),(c.stv(d,e),c.stv(a,b))):
                result=self.math.evaluate(*pair,int(time.time()*1000)+30000)
                for k,want in zip(('strength','confidence'),expected):self.assertAlmostEqual(float(result['truth'][k]),float(want),delta=1e-14)
                evidence.append(dict(inputs=pair,result=result,reference=[str(x) for x in expected]))
        path=Path(os.environ.get('S04_EVIDENCE','artifacts/s04/tests'));path.mkdir(parents=True,exist_ok=True)
        (path/'pure-native.json').write_bytes(canonical(dict(profile=self.math.profile(),cases=evidence,real_native=True)))
    def test_singular_nonfinite_injection_model_and_output_refusals(self):
        for a,b in [(c.stv('0','0'),c.stv('1','0')),
            (dict(model='wrong',strength='1',confidence='.5',evidence_count=None),c.stv('1','0.5'))]:
            with self.assertRaises(ContractError):self.math.evaluate(a,b,int(time.time()*1000)+10000)
        for number in ('1','0.9999999999999999999','NaN','inf','(shell x)','-0.1'):
            with self.assertRaises(ContractError):c.stv('1',number)
        for text in ('','true','true\n(stv 1 0.6)\n(stv 1 0.6)','false\n(stv 1 0.6)',
                     'true\n(stv NaN 0.6)','true\n(stv 1 1)','true\n(stv 1 0.999)'):
            with self.assertRaises(ContractError):self.math.parse(text)
    def test_expiry_timeout_and_source_revalidation(self):
        pair=(c.stv('1','0.5'),c.stv('0','0.5'))
        with self.assertRaises(ContractError) as error:self.math.evaluate(*pair,1)
        self.assertEqual(error.exception.code,'DEADLINE_EXCEEDED')
        with patch('fusion.adapters.neoclaw_revision.subprocess.run',side_effect=subprocess.TimeoutExpired('fixture',1)):
            with self.assertRaises(ContractError) as error:self.math.evaluate(*pair,int(time.time()*1000)+10000)
        self.assertEqual(error.exception.code,'NOT_AVAILABLE')
        with patch('fusion.adapters.neoclaw_revision.NativeTruthDeduction',side_effect=ContractError('UNSUPPORTED_PROFILE')):
            with self.assertRaises(ContractError) as error:self.math.evaluate(*pair,int(time.time()*1000)+10000)
        self.assertEqual(error.exception.code,'UNSUPPORTED_PROFILE')
