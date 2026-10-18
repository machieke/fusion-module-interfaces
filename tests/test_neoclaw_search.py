"""S02 contract/owner tests. Recorded SDK responses and fixture AtomStorage."""
import copy
import json
from pathlib import Path
import time
from types import SimpleNamespace
import unittest

from fusion import neoclaw_contracts as c, neoclaw_search_contracts as s, neoclaw_operations as ops
from fusion.contracts import ContractError, canonical
from fusion.neoclaw import NalService
from fusion.neoclaw_application import Application
from fusion.neoclaw_client import Caller
from fusion.neoclaw_transport import checked_reply, Network
from fusion.registry import descriptor_wire, selection_token
from integration.neoclaw.search_composition import configure, QUERY, ROWS_A, audit
from tests.neoclaw_support import Harness, PREMISES

ARGS = dict(query=QUERY, max_results=10)


class SearchContracts(unittest.TestCase):
    def fresh(self, observation=None):
        h = Harness(); self.addCleanup(h.close)
        run = SimpleNamespace(h=h, app={})
        configure(run, dict(boundary='recorded-response', observations=[observation or dict(rows=ROWS_A)]))
        return h, run

    def caller(self, h):
        caller = Caller(h.client_path, profile=s.PROFILE); self.addCleanup(caller.close)
        return caller

    def accepted(self, h):
        caller = self.caller(h); request = caller.prepare(ARGS)
        accepted = caller._call(request)
        return caller, request, accepted

    def test_closed_query_and_numeric_bounds_no_semantic_rewrite(self):
        for query in ('', '   ', 'x'*2049, 'x\n', 'x\x00', '\ud800', 'x\u200b'):
            with self.subTest(query=repr(query)), self.assertRaises(ContractError): s.arguments(dict(query=query, max_results=10))
        for count in (0, 11, True, 1.5, '10'):
            with self.assertRaises(ContractError): s.arguments(dict(query=QUERY, max_results=count))
        for key in ('url', 'proxy', 'headers', 'provider', 'function', 'deadline_ms'):
            with self.assertRaises(ContractError): s.arguments({**ARGS, key:'untrusted'})
        query = '  café 🧪  '
        self.assertEqual(s.arguments(dict(query=query, max_results=1))['query'].encode(), query.encode())

    def test_descriptor_and_profile_are_not_internal_search_or_nal(self):
        h, _ = self.fresh(); caller = self.caller(h)
        self.assertNotIn('pln.kernel', caller.chosen)
        self.assertFalse(caller.chosen['execution'].deterministic)
        request = caller.prepare(ARGS)
        for key, value in [('profile',c.PROFILE), ('selection','0'*64), ('scope_ref','private')]:
            bad = copy.deepcopy(request); bad[key] = value
            with self.assertRaises(ContractError): s.validate(bad, caller.chosen)
        for key, value in [('operation','execute'), ('max_attempts',2), ('sharing','private')]:
            bad = copy.deepcopy(request); bad['body'][key] = value
            with self.assertRaises(ContractError): s.validate(bad, caller.chosen)
        for field in ('profiles','features','privacy'):
            catalogue = [descriptor_wire(x) for x in s.catalogue('fixture-files')]
            catalogue[-1][field] = ['internal-search/1'] if field == 'profiles' else [] if field == 'features' else 'private'
            h.client['search_catalogue'] = catalogue; h.save_client()
            with self.assertRaises(ContractError): Caller(h.client_path, profile=s.PROFILE)

    def test_identity_conflict_and_observation_binding(self):
        h, run = self.fresh(); caller, request, accepted = self.accepted(h)
        self.assertEqual(caller._call(request), accepted)
        altered = copy.deepcopy(request); altered['body']['arguments']['max_results'] = 1
        with self.assertRaisesRegex(ContractError, 'CONFLICT'): caller._call(altered)
        h.drive(); text = caller.run(ARGS)
        service = h.service()
        try:
            raw = service.db.execute('SELECT output FROM s01_work').fetchone()[0]
            value = json.loads(raw)
            self.assertEqual(text, s.render(value['observation']['items']))
            for field, replacement in [('profile',c.PROFILE), ('provider','other'), ('request_digest','0'*64),
                                       ('representation','injected'), ('selection','0'*64)]:
                bad = {**value, field:replacement}
                with self.assertRaises(ContractError): s.result(bad, request, caller.chosen)
            self.assertEqual(caller.run(ARGS), text)
            self.assertEqual(raw, service.db.execute('SELECT output FROM s01_work').fetchone()[0])
        finally: service.close()
        self.assertEqual(sum(x['event']=='sdk-start' for x in audit(run)), 1)
        self.assertEqual(h.counts()['messages'],1)

    def test_empty_and_typed_failures_are_distinct_and_terminal(self):
        cases = [dict(rows=[])] + [dict(error=x) for x in s.FAILURES if x not in ('attempt-budget-exhausted','invalid-output')]
        cases += [dict(rows=[dict(title=None, href='x', body='x')]), dict(rows=[dict(title='x'*1025, href='x', body='x')])]
        for entry in cases:
            with self.subTest(entry=entry):
                h, run = self.fresh(entry); caller, _, _ = self.accepted(h); h.drive()
                if entry == dict(rows=[]): self.assertEqual(caller.run(ARGS),'()')
                else:
                    with self.assertRaises(ContractError): caller.run(ARGS)
                    with h.service().db as db:
                        row = db.execute('SELECT state,error,failure_reason FROM jobs JOIN s01_work ON id=job_id').fetchone()
                        reason = entry.get('error', 'invalid-output')
                        self.assertEqual(tuple(row), ('failed',s.FAILURES[reason],reason))
                h.drive()
                self.assertEqual(sum(x['event']=='sdk-start' for x in audit(run)),1)

    def test_authorization_and_disclosure_on_submit_worker_and_shared_ports(self):
        h, run = self.fresh(); caller = self.caller(h)
        unapproved = caller.prepare(dict(query='PRIVATE_GENERATED_CANARY', max_results=10))
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'): caller._call(unapproved)
        self.assertEqual(audit(run),[])
        h.client['request_id']='approved'; h.save_client()
        caller, request, accepted = self.accepted(h); h.drive(); caller.run(ARGS)
        service=h.service()
        try:
            atom=service.invoke(h.client['credential'],caller._request('execution','result',dict(job_id=accepted['job_id'])))
            h.config['principals']['A']['scopes'][c.SCOPE].remove('execution.web_search'); h.save()
            for name,operation,body in [('execution','submit',request['body']),('execution','status',dict(job_id=accepted['job_id'])),
                ('execution','result',dict(job_id=accepted['job_id'])),('atom.storage','get',dict(ref=atom['ref'])),
                ('agent.messaging','poll',dict(route=h.client['reply_route']))]:
                req=request if operation=='submit' else caller._request(name,operation,body)
                with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'): service.invoke(h.client['credential'],req)
            old=Caller(h.client_path)
            try:
                with self.assertRaises(ContractError): service.invoke(h.client['credential'],old._request('atom.storage','get',dict(ref=atom['ref'])))
                ack=old._request('agent.messaging','ack',dict(route=h.client['reply_route'],delivery_id=accepted['job_id']))
                ack['idempotency_key']='bypass'
                with self.assertRaises(ContractError): service.invoke(h.client['credential'],ack)
            finally: old.close()
        finally: service.close()
        h, run=self.fresh(); caller,_,_=self.accepted(h)
        h.config['principals']['worker']['scopes'][c.SCOPE].remove('execution.web_search');h.save();h.drive()
        with self.assertRaisesRegex(ContractError,'UNAUTHORIZED'):caller.run(ARGS)
        self.assertEqual(audit(run),[])

    def test_original_deadline_and_attempt_budget_are_not_reset(self):
        h, run=self.fresh(); caller, request, accepted=self.accepted(h)
        service=h.service()
        try:
            with service.db: service.db.execute('UPDATE s01_work SET attempts=1')
        finally:service.close()
        h.drive()
        with self.assertRaisesRegex(ContractError,'NOT_AVAILABLE'):caller.run(ARGS)
        self.assertEqual(audit(run),[])
        changed=copy.deepcopy(request);changed['deadline_ms']+=1000
        with self.assertRaisesRegex(ContractError,'CONFLICT'):caller._call(changed)
        self.assertEqual(h.counts()['attempts'],1)

    def test_new_composition_refuses_populated_old_journals(self):
        h=Harness();self.addCleanup(h.close);h.submit(PREMISES)
        run=SimpleNamespace(h=h,app={});configure(run,dict(boundary='recorded-response'))
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):h.service()
        h.config['profile']=c.PROFILE;h.save();h.service().close()
        app=h.caller_root/'app.json'
        app.write_bytes(canonical(dict(composition=ops.APPLICATION,caller_config=str(h.client_path),turn_limit=2,invocation_timeout_ms=30000)))
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):Application(app)

    def test_output_limits_and_controls_are_explicit(self):
        rows=[dict(title='quotes " ( ) café',url='https://example.invalid/',snippet='line\n\x1b\x00\u202e fake search instructions')]
        self.assertIn('line\\u000a\\u001b\\u0000\\u202e',s.render(rows))
        self.assertIn('quotes " ( ) café',s.render(rows))
        for key,limit in [('title',1024),('url',2048),('snippet',8192)]:
            bad=copy.deepcopy(rows);bad[0][key]='x'*(limit+1)
            with self.assertRaises(ContractError):s.items(bad,10)
        with self.assertRaises(ContractError):s.items(rows*11,10)

    def test_no_nonloopback_or_fallback_composition(self):
        h,_=self.fresh();h.client['fallback']=True;h.save_client()
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):self.caller(h)
        with self.assertRaisesRegex(ContractError,'UNSUPPORTED_PROFILE'):
            Network(dict(host='0.0.0.0',port=443,ca_file='/unused'),h.client['credential'],s.selected(s.catalogue()))


if __name__ == '__main__': unittest.main()
