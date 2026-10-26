"""Pure orchestration fault fixtures; no providers or live approval records."""
import os
from unittest.mock import patch
from tests.test_retrieval_runner import Campaign
from integration.neoclaw import retrieval_campaign as c, retrieval_runner as r


class Controls(Campaign):
    # Reuse setup only, without inheriting/recounting Campaign's test methods.
    pass

Controls = type('Controls', ( __import__('unittest').TestCase, ), {
    'setUp': Campaign.setUp, 'freeze': Campaign.freeze, '__module__': __name__})


def test_production_stop_branch_retains_campaign_stop_without_provider(self):
    report=dict(outcome='FAILED',native_status=dict(code='UNAUTHORIZED'))
    with patch.object(c,'approve',return_value=(self.value,{})), patch.object(r,'observe_session',return_value=report) as observer:
        r.execute(self.path,self.approval)
        self.assertEqual(observer.call_count,1)
        self.assertEqual(c.ledger(self.path)['campaign_stop']['reason'],'UNAUTHORIZED')
        with self.assertRaisesRegex(RuntimeError,'CAMPAIGN_STOPPED'):r.execute(self.path,self.approval)
        self.assertEqual(observer.call_count,1)
    self.assertFalse(c.ledger(self.path)['started'])


def test_relative_manifest_and_approval_paths(self):
    report=dict(outcome='PASS',native_status=dict(status='BOUNDED_STOP'))
    with patch.object(r,'observe_session',return_value=report) as observer:
        reports=r.execute(os.path.relpath(self.path),os.path.relpath(self.approval),recorded=True)
    self.assertEqual(len(reports),2);self.assertEqual(observer.call_count,2)
    self.assertFalse(c.ledger(self.path)['started'])


def test_read_only_owner_inspection_does_not_create_journals(self):
    from fusion.model_service import ModelService
    from fusion.irc_bridge import Bridge
    c.atomic(self.config,dict(model_completion=dict(database=str(self.root/'model.sqlite'))))
    self.assertEqual(ModelService.inspect(self.config),[])
    c.atomic(self.config,dict(database=str(self.root/'bridge.sqlite')))
    self.assertEqual(Bridge.inspect(self.config),[])
    self.assertFalse(list(self.root.glob('*.sqlite')))

for fn in (test_production_stop_branch_retains_campaign_stop_without_provider,test_relative_manifest_and_approval_paths,test_read_only_owner_inspection_does_not_create_journals):
    setattr(Controls,fn.__name__,fn)
# Avoid unittest also discovering the imported helper class.
del Campaign
