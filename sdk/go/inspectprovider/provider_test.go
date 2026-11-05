package inspectprovider

// Numerical/model/channel work is absent. Storage/completion ports below are
// explicit contract fixtures; provider journal, computation, TLS and kills real.
import (
	"bytes"
	"encoding/json"
	omega "fusion.local/omega"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
)

const fixtureToken = "generated-synthetic-token"

func fixture(t *testing.T, root string) (*Owner, omega.Ref) {
	t.Helper()
	policy := Policy{Principals: map[string]Principal{"A": {CredentialFile: filepath.Join(root, "credential"), Scopes: map[string][]string{"synthetic-go-inspect": {"execution.submit", "execution.status", "execution.result", "atom.storage.get"}}}}, Routes: map[string]Route{"inspect-A": {Scope: "synthetic-go-inspect", Owner: "A"}}}
	policy.Principals["worker"] = Principal{CredentialFile: filepath.Join(root, "worker-credential"), Scopes: map[string][]string{"synthetic-go-inspect": {"atom.storage.get", "atom.storage.create"}}}
	b, _ := json.Marshal(policy)
	os.WriteFile(filepath.Join(root, "policy.json"), b, 0600)
	os.WriteFile(filepath.Join(root, "credential"), []byte(fixtureToken), 0600)
	o := &Owner{cfg: Config{Profile: "go-immutable-inspect-reference/1", Scope: "synthetic-go-inspect", State: filepath.Join(root, "state.json"), Policy: filepath.Join(root, "policy.json")}, Clock: func() int64 { return 1000 }, Hook: func(string) {}}
	if _, e := os.Stat(o.cfg.State); os.IsNotExist(e) {
		o.state = State{Profile: o.cfg.Profile, Binding: "fixture-binding", Source: uuid(), Jobs: map[string]*Job{}}
		if e = o.save(); e != nil {
			t.Fatal(e)
		}
	} else {
		if e = decodeFile(o.cfg.State, &o.state); e != nil {
			t.Fatal(e)
		}
	}
	payload := []byte("generated raw payload with snow 雪")
	ref := omega.Ref{Scope: o.cfg.Scope, ID: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", Revision: number(1), Digest: hash(payload)}
	o.get = func(r omega.Ref, d int64) (omega.Envelope, error) {
		if r != ref {
			return omega.Envelope{}, fail("NOT_FOUND")
		}
		if o.Clock() >= d {
			return omega.Envelope{}, fail("DEADLINE_EXCEEDED")
		}
		return omega.Envelope{Ref: ref, ContentType: "application/fixture", Bytes: payload}, nil
	}
	o.create = func(id, kind string, data []byte, d int64) (omega.Object, error) {
		path := filepath.Join(root, "result-"+strings.TrimPrefix(id, "result/"))
		if old, e := os.ReadFile(path); e == nil && !bytes.Equal(old, data) {
			return nil, fail("CONFLICT")
		}
		if e := os.WriteFile(path, data, 0600); e != nil {
			return nil, e
		}
		return omega.Object{"ref": omega.Object{"scope_ref": o.cfg.Scope, "id": jobID(id), "revision": number(1), "digest": hash(data)}, "receipt": omega.Object{"provider": "contract-fixture-files/1", "durability": "local-files-process-restart", "evidence": omega.Object{"fixture": true}}}, nil
	}
	o.completion = func(q omega.Object) (omega.Object, error) {
		c := q["completion"].(omega.Object)
		return omega.Object{"id": q["id"], "request_digest": hash(raw(q)), "value": omega.Object{"delivery_id": q["delivery_id"], "acceptance": "process-restart", "delivery": "not-observed", "evidence": omega.Object{"fixture": true}, "scope_ref": q["scope"], "route": q["route"], "correlation_id": c["correlation_id"]}}, nil
	}
	return o, ref
}
func request(o *Owner, ref omega.Ref, key string) omega.Object {
	rb, _ := json.Marshal(ref)
	rv, _ := omega.Decode(rb)
	r := omega.Object{"message_id": "delivery-" + key, "interface_ref": omega.Object{"id": "execution", "version": "1.0.0"}, "operation": "submit", "scope_ref": o.cfg.Scope, "profile": "inspect-atom/2", "body": omega.Object{"operation": "inspect_atom", "ref": rv}, "idempotency_key": key, "correlation_id": key, "reply_route": "inspect-A", "deadline_ms": number(5000)}
	d := Contract["descriptor"].(omega.Object)
	p := Contract["envelope"].(omega.Object)
	env := omega.Object{"profile": p["profile"], "task": key, "correlation": key, "scope": o.cfg.Scope, "operation": omega.Object{"interface": r["interface_ref"], "profile": r["profile"], "name": "inspect_atom"}, "inputs": omega.Object{"ref": rv}, "initiator": "A", "delegation": omega.Object{"service": "execution", "actor": "worker", "authority": "current-scoped-policy"}, "provider": omega.Object{"id": d["provider"], "selection": Contract["selection"]}, "disclosure": "approved-synthetic-agent-artifact", "deadline_ms": number(5000), "limits": p["limits"], "completion": omega.Object{"owner": "A", "route": "inspect-A", "profile": "durable-mailbox/2"}, "guarantee": "one-logical-admission-independent-owner-commits"}
	return omega.Object{"profile": Contract["wrapper"], "selection": Contract["selection"], "request": r, "envelope": env}
}
func submitted(t *testing.T, o *Owner, q omega.Object) string {
	t.Helper()
	v, e := o.Invoke(fixtureToken, q)
	if e != nil {
		t.Fatal(e)
	}
	return v["ok"].(omega.Object)["job_id"].(string)
}
func TestActualInspectionAndIndependentDurableCommits(t *testing.T) {
	root := t.TempDir()
	o, ref := fixture(t, root)
	q := request(o, ref, "one")
	before := o.state.Commit
	id := submitted(t, o, q)
	if o.state.Commit <= before || o.state.Jobs[id].Result != nil {
		t.Fatal("acceptance not independent")
	}
	accept := raw(o.state.Jobs[id].Acceptance)
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	j := o.state.Jobs[id]
	if j.Result == nil || j.Outbox == nil || j.Delivered {
		t.Fatal("result/outbox phase")
	}
	payload, e := os.ReadFile(filepath.Join(root, "result-"+id))
	if e != nil {
		t.Fatal(e)
	}
	v, e := omega.Decode(payload)
	if e != nil {
		t.Fatal(e)
	}
	got := v.(omega.Object)
	if got["digest"] != ref.Digest || got["length"] != number(int64(len([]byte("generated raw payload with snow 雪")))) || got["provider_version"] != "0.1.0" {
		t.Fatal("independent result mismatch")
	}
	reloaded, _ := fixture(t, root)
	reloaded.get = func(omega.Ref, int64) (omega.Envelope, error) {
		t.Fatal("captured result recomputed")
		return omega.Envelope{}, nil
	}
	if e = reloaded.WorkOne(); e != nil {
		t.Fatal(e)
	}
	if !reloaded.state.Jobs[id].Delivered || len(reloaded.state.Jobs[id].Events) != 3 {
		t.Fatal("completion phase")
	}
	reloaded.Clock = func() int64 { return 9000 }
	if _, e = reloaded.Invoke(fixtureToken, q); e != nil {
		t.Fatal(e)
	}
	if !bytes.Equal(accept, raw(reloaded.state.Jobs[id].Acceptance)) {
		t.Fatal("acceptance changed")
	}
}
func TestIdentityDeadlineConflictAndNewOccurrence(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	q := request(o, r, "one")
	id := submitted(t, o, q)
	q["request"].(omega.Object)["message_id"] = "new-transport"
	if submitted(t, o, q) != id || len(o.state.Jobs) != 1 {
		t.Fatal("transport became occurrence")
	}
	q["request"].(omega.Object)["deadline_ms"] = number(6000)
	if _, e := o.Invoke(fixtureToken, q); e == nil {
		t.Fatal("deadline topup")
	}
	if submitted(t, o, request(o, r, "two")) == id || len(o.state.Jobs) != 2 {
		t.Fatal("intentional occurrence deduped")
	}
}
func TestRevocationWrongScopeAndNoUnknownOperation(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	q := request(o, r, "one")
	submitted(t, o, q)
	if _, e := o.Invoke("wrong", q); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("wrong auth")
	}
	q["request"].(omega.Object)["scope_ref"] = "synthetic-other"
	if _, e := o.Invoke(fixtureToken, q); e == nil {
		t.Fatal("wrong scope")
	}
	os.WriteFile(o.cfg.Policy, []byte(`{"principals":{},"routes":{}}`), 0600)
	if e := o.WorkOne(); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("worker ignored revocation")
	}
}
func TestLostCompletionReplyAndMalformedReceiptRemainPending(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	id := submitted(t, o, request(o, r, "one"))
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	original := o.completion
	o.completion = func(q omega.Object) (omega.Object, error) { _, _ = original(q); return nil, fail("NOT_AVAILABLE") }
	if e := o.WorkOne(); e == nil || o.state.Jobs[id].Delivered {
		t.Fatal("unknown delivery acknowledged")
	}
	spent := o.state.Jobs[id].Attempts
	o.completion = func(q omega.Object) (omega.Object, error) {
		v, e := original(q)
		v["value"].(omega.Object)["correlation_id"] = "wrong"
		return v, e
	}
	if e := o.WorkOne(); e == nil || o.state.Jobs[id].Delivered {
		t.Fatal("malformed receipt accepted")
	}
	o.completion = original
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	if !o.state.Jobs[id].Delivered || o.state.Jobs[id].Attempts <= spent {
		t.Fatal("budget refund")
	}
}
func TestExpiryDoesNotComputeAndCapturedCompletionDoesNotRegenerate(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	id := submitted(t, o, request(o, r, "one"))
	o.Clock = func() int64 { return 5000 }
	o.get = func(omega.Ref, int64) (omega.Envelope, error) { t.Fatal("expired work"); return omega.Envelope{}, nil }
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	j := o.state.Jobs[id]
	if j.Error != "DEADLINE_EXCEEDED" || j.Result != nil || j.Outbox["result"] != nil {
		t.Fatal("expiry fabricated result")
	}
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
}
func TestFiniteSpentAttemptsSurviveRestart(t *testing.T) {
	root := t.TempDir()
	o, r := fixture(t, root)
	id := submitted(t, o, request(o, r, "one"))
	o.get = func(omega.Ref, int64) (omega.Envelope, error) { return omega.Envelope{}, fail("NOT_AVAILABLE") }
	for i := 0; i < 32; i++ {
		if e := o.WorkOne(); e == nil {
			t.Fatal("outage hidden")
		}
	}
	reload, _ := fixture(t, root)
	if reload.state.Jobs[id].Attempts != 32 {
		t.Fatal("spent budget lost")
	}
	before := reload.state.Commit
	if e := reload.WorkOne(); e != nil {
		t.Fatal(e)
	}
	if reload.state.Commit != before || reload.state.Jobs[id].Result != nil {
		t.Fatal("spent budget resumed")
	}
}
func TestRealHTTPSAndDuplicateJSONRefusal(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	server := httptest.NewTLSServer(o)
	defer server.Close()
	q := request(o, r, "tls")
	req, _ := http.NewRequest("POST", server.URL+Contract["route"].(string), bytes.NewReader(raw(q)))
	req.Header.Set("Authorization", "Bearer "+fixtureToken)
	resp, e := server.Client().Do(req)
	if e != nil {
		t.Fatal(e)
	}
	b, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatal(string(b))
	}
	if _, e = omega.Decode(b); e != nil {
		t.Fatal(e)
	}
	req, _ = http.NewRequest("POST", server.URL+Contract["route"].(string), strings.NewReader(`{"profile":"one","profile":"two"}`))
	req.Header.Set("Authorization", "Bearer "+fixtureToken)
	resp, e = server.Client().Do(req)
	if e != nil {
		t.Fatal(e)
	}
	bad, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != 200 || !bytes.Contains(bad, []byte("INVALID_ARGUMENT")) || len(o.state.Jobs) != 1 {
		t.Fatal("duplicate keys accepted")
	}
}
func TestCursorGapAndPrivateJobRefusal(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	id := submitted(t, o, request(o, r, "one"))
	q := omega.Object{"profile": Contract["wrapper"], "selection": Contract["selection"], "events": omega.Object{"job_id": id, "source": nil, "after": number(0), "limit": number(1)}}
	v, e := o.Invoke(fixtureToken, q)
	if e != nil {
		t.Fatal(e)
	}
	page := v["value"].(omega.Object)
	if page["head"] != number(1) || page["gap"] != false {
		t.Fatal("cursor")
	}
	q["events"].(omega.Object)["source"] = "wrong-source"
	v, e = o.Invoke(fixtureToken, q)
	if e != nil || v["value"].(omega.Object)["gap"] != true {
		t.Fatal("gap defaulted empty")
	}
	q["events"].(omega.Object)["job_id"] = "unowned"
	if _, e = o.Invoke(fixtureToken, q); e == nil {
		t.Fatal("foreign task")
	}
}
func TestProcessKillHelper(t *testing.T) {
	root := os.Getenv("OMEGA_INSPECT_KILL_FIXTURE")
	if root == "" {
		t.Skip("subprocess helper")
	}
	o, r := fixture(t, root)
	o.Hook = func(stage string) {
		if stage == os.Getenv("OMEGA_INSPECT_KILL_STAGE") {
			syscall.Kill(os.Getpid(), syscall.SIGKILL)
		}
	}
	if len(o.state.Jobs) == 0 {
		submitted(t, o, request(o, r, "kill"))
	} else {
		o.WorkOne()
	}
	t.Fatal("kill stage not reached")
}
func TestRealProcessKillAcceptanceAndResultRecovery(t *testing.T) {
	for _, stage := range []string{"after_acceptance_commit", "after_result_outbox_commit"} {
		t.Run(stage, func(t *testing.T) {
			root := t.TempDir()
			o, r := fixture(t, root)
			if stage != "after_acceptance_commit" {
				submitted(t, o, request(o, r, "kill"))
			}
			cmd := exec.Command(os.Args[0], "-test.run=^TestProcessKillHelper$")
			cmd.Env = append(os.Environ(), "OMEGA_INSPECT_KILL_FIXTURE="+root, "OMEGA_INSPECT_KILL_STAGE="+stage)
			if e := cmd.Run(); e == nil {
				t.Fatal("expected SIGKILL")
			}
			o, _ = fixture(t, root)
			if len(o.state.Jobs) != 1 {
				t.Fatal("identity lost")
			}
			for i := 0; i < 2; i++ {
				if e := o.WorkOne(); e != nil {
					t.Fatal(e)
				}
			}
			for _, j := range o.state.Jobs {
				if !j.Delivered || len(j.Events) != 3 || j.Request["deadline_ms"] != number(5000) {
					t.Fatal("recovery changed lineage/bounds")
				}
			}
		})
	}
}

func TestBoundedPayloadAndRevocationAtAcceptance(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	get := o.get
	o.get = func(ref omega.Ref, d int64) (omega.Envelope, error) {
		item, e := get(ref, d)
		item.Bytes = make([]byte, 4097)
		return item, e
	}
	if _, e := o.Invoke(fixtureToken, request(o, r, "oversize")); e == nil || e.Error() != "INVALID_ARGUMENT" || len(o.state.Jobs) != 0 {
		t.Fatal("oversize acceptance")
	}
	o.get = func(ref omega.Ref, d int64) (omega.Envelope, error) {
		item, e := get(ref, d)
		os.WriteFile(o.cfg.Policy, []byte(`{"principals":{},"routes":{}}`), 0600)
		return item, e
	}
	if _, e := o.Invoke(fixtureToken, request(o, r, "revoked")); e == nil || e.Error() != "UNAUTHORIZED" || len(o.state.Jobs) != 0 {
		t.Fatal("revoked before acceptance")
	}
}
func TestCorruptionAndClockRollbackRefuse(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	id := submitted(t, o, request(o, r, "one"))
	if e := o.validateStored(); e != nil {
		t.Fatal(e)
	}
	o.state.Jobs[id].Attempts = 33
	if e := o.validateStored(); e == nil {
		t.Fatal("corrupt budget accepted")
	}
	o.state.Jobs[id].Attempts = 0
	o.state.Jobs[id].Delivered = true
	if e := o.validateStored(); e == nil {
		t.Fatal("manufactured closure accepted")
	}
	o.state.Jobs[id].Delivered = false
	o.Clock = func() int64 { return 999 }
	if e := o.WorkOne(); e == nil || e.Error() != "CONFLICT" {
		t.Fatal("clock rollback accepted")
	}
	if e := o.WorkOne(); e == nil || e.Error() != "NOT_AVAILABLE" {
		t.Fatal("failed commit did not fence process")
	}
}
func TestOptionalFieldsAndWorkerAuthority(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	q := request(o, r, "one")
	q["request"].(omega.Object)["causation_id"] = omega.Object{}
	if _, e := o.Invoke(fixtureToken, q); e == nil {
		t.Fatal("malformed optional field")
	}
	delete(q["request"].(omega.Object), "causation_id")
	id := submitted(t, o, q)
	p, e := o.policy()
	if e != nil {
		t.Fatal(e)
	}
	delete(p.Principals, "worker")
	b, _ := json.Marshal(p)
	os.WriteFile(o.cfg.Policy, b, 0600)
	if e := o.WorkOne(); e == nil || e.Error() != "UNAUTHORIZED" || o.state.Jobs[id].Attempts != 0 {
		t.Fatal("worker authority ignored")
	}
}

func TestMaintainedContractGeneratedHandoffAndResult(t *testing.T) {
	o, _ := fixture(t, t.TempDir())
	sample := Contract["samples"].(omega.Object)
	q := omega.Object{"profile": Contract["wrapper"], "selection": Contract["selection"], "request": sample["request"], "envelope": sample["envelope"]}
	if hash(raw(sample["request"])) != sample["request_sha256"] {
		t.Fatal("generated wire drift")
	}
	id := submitted(t, o, q)
	if id != sample["accepted_job_id"] {
		t.Fatal("cross-language occurrence identity drift")
	}
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	got, e := os.ReadFile(filepath.Join(filepath.Dir(o.cfg.State), "result-"+id))
	if e != nil {
		t.Fatal(e)
	}
	if string(got) != sample["result"] {
		t.Fatal("native inspect representation drift")
	}
}
func TestOpenWriterSealRestoreFenceAndChangedBinding(t *testing.T) {
	root := t.TempDir()
	_, _ = fixture(t, root)
	os.Remove(filepath.Join(root, "state.json"))
	ca := filepath.Join(root, "ca")
	os.WriteFile(ca, []byte("fixture trust bytes; startup does not contact service"), 0600)
	golden, e := os.ReadFile("../testdata/golden.json")
	if e != nil {
		t.Fatal(e)
	}
	parsed, e := omega.Decode(golden)
	if e != nil {
		t.Fatal(e)
	}
	storage := omega.Config{Profile: "fusion-go-client/1", Kind: "atom", Endpoint: "https://fixture-storage:8443", CAFile: ca, CredentialFile: filepath.Join(root, "worker-credential"), Principal: "inspect-worker", Scope: "synthetic-go-inspect", Contract: "immutable-commit-feed/2", Composition: "synthetic-cognitive-services/1", Descriptor: parsed.(omega.Object)["descriptor"].(omega.Object)}
	b, _ := json.Marshal(storage)
	storagePath := filepath.Join(root, "storage.json")
	os.WriteFile(storagePath, b, 0600)
	cfg := Config{Profile: "go-immutable-inspect-reference/1", Scope: storage.Scope, State: filepath.Join(root, "state.json"), Policy: filepath.Join(root, "policy.json"), Storage: storagePath, Completion: Endpoint{URL: "https://fixture-messaging:8443", CAFile: ca, CredentialFile: filepath.Join(root, "worker-credential")}}
	owner, e := Open(cfg)
	if e != nil {
		t.Fatal(e)
	}
	if _, e = Open(cfg); e == nil || e.Error() != "OVERLOADED" {
		t.Fatal("second writer")
	}
	if _, e = os.Stat(filepath.Join(root, "owner-seal.json")); e != nil {
		t.Fatal(e)
	}
	owner.Close()
	os.WriteFile(filepath.Join(root, "restore-fence.json"), []byte("{}"), 0600)
	if _, e = Open(cfg); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("restored owner started")
	}
	os.Remove(filepath.Join(root, "restore-fence.json"))
	cfg.Completion.URL = "https://changed-messaging:8443"
	if _, e = Open(cfg); e == nil || e.Error() != "CONFLICT" {
		t.Fatal("accepted binding changed")
	}
}
