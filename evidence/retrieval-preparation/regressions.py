"""Inspected impact-selected regressions. Run ONLY through preparation_guard.

Model hosts are explicitly recorded-response replacements or stopped before any
model RPC. No live campaign, real runtime readiness or generative startup is used.
Historical evidence output directories are replaced before tests execute.
"""
import importlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from integration.neoclaw.preparation_guard import verify
verify(os.environ['FUSION_PREP_PARENT_NET'])
OUT=ROOT/'artifacts/retrieval-preparation/regression-native'
OUT.mkdir(parents=True,exist_ok=True)
for scope in ('S01_1','S02','S03','S03_1','S03_2','S04','S05','S06'):
    os.environ[scope+'_EVIDENCE']=str(OUT/scope.lower())
NAMES=[
 'integration.neoclaw.test_memory.MemoryIntegration.test_real_metric_freshness_rebuild_empty_and_missing_payload',
 'integration.neoclaw.test_embedding.EmbeddingIntegration.test_https_certificate_outage_unauthorized_and_text_consent',
 'integration.neoclaw.test_append.AppendIntegration.test_existing_query_and_captured_result_keep_old_view',
 'integration.neoclaw.test_evidence_loop.NativeEvidenceLoop.test_native_dispatch_duplicate_contrary_readback_and_no_vector_rebuild',
 'integration.neoclaw.test_promotion_loop.NativePromotionLoop.test_priority_and_belief_independent_same_session',
 'integration.neoclaw.test_promotion_loop.NativePromotionLoop.test_retained_query_context_and_derived_file_repair',
 'integration.neoclaw.test_channel_loop.NativeChannel.test_local_and_https_native_consumption_equal_text_burst_and_send',
 'integration.neoclaw.test_channel_recovery.BridgeRecovery.test_spent_rpc_budget_and_expired_effect_remain_spent',
 'integration.neoclaw.test_model_loop.ModelLoop',
 'integration.neoclaw.test_model_preflight.ModelPreflight',
]
# Imports create historical output directories but do not run tests or models.
# Redirect even the two modules whose old tests lack an environment selector.
for name in ('test_model_loop','test_model_preflight'):
    module=importlib.import_module('integration.neoclaw.'+name)
    module.OUT=OUT/name;module.OUT.mkdir(parents=True,exist_ok=True)
suite=unittest.defaultTestLoader.loadTestsFromNames(NAMES)
class Result(unittest.TextTestResult):
    records=[]
    def addSuccess(self,test):
        self.records.append(dict(method=test.id(),outcome='PASS'));super().addSuccess(test)
    def addError(self,test,err):
        self.records.append(dict(method=test.id(),outcome='ERROR'));super().addError(test,err)
    def addFailure(self,test,err):
        self.records.append(dict(method=test.id(),outcome='FAIL'));super().addFailure(test,err)
    def addSkip(self,test,reason):
        self.records.append(dict(method=test.id(),outcome='SKIP',reason=reason));super().addSkip(test,reason)
result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
(ROOT/'evidence/retrieval-preparation/regression-native-results.json').write_text(json.dumps(dict(
    methods=result.records,method_executions=result.testsRun,successful=result.wasSuccessful(),
    additional_live_generations=0,model_boundary='recorded responses or pre-submission stop',
    evidence_directory=str(OUT)),indent=2)+'\n')
raise SystemExit(not result.wasSuccessful())
