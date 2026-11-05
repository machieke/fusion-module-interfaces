package inspectprovider

// Dependency ports are fixtures. Accounting/admission, HTTPS and journal I/O
// exercise the actual independent Go owner, never another owner's database.
import (
	"bytes"
	"encoding/json"
	"encoding/pem"
	"fmt"
	omega "fusion.local/omega"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

const operatorToken = "generated-capacity-operator-token"

func capacityAuthority(t *testing.T, o *Owner) {
	t.Helper()
	p, e := o.policy()
	if e != nil {
		t.Fatal(e)
	}
	credential := filepath.Join(filepath.Dir(o.cfg.Policy), "capacity-credential")
	if e = os.WriteFile(credential, []byte(operatorToken), 0600); e != nil {
		t.Fatal(e)
	}
	p.Principals["capacity-operator"] = Principal{CredentialFile: credential, Scopes: map[string][]string{o.cfg.Scope: {"execution.capacity"}}}
	b, _ := json.Marshal(p)
	if e = os.WriteFile(o.cfg.Policy, b, 0600); e != nil {
		t.Fatal(e)
	}
}
func capacityValue(t *testing.T, o *Owner) omega.Object {
	t.Helper()
	v, e := o.Capacity(operatorToken)
	if e != nil {
		t.Fatal(e)
	}
	if e = checkCapacity(v, o.cfg.Scope); e != nil {
		t.Fatal(e)
	}
	return v
}
func disk(t *testing.T, o *Owner) []byte {
	t.Helper()
	b, e := os.ReadFile(o.cfg.State)
	if e != nil {
		t.Fatal(e)
	}
	return b
}
func TestCapacityExplicitAuthorityAndReadOnlySnapshot(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	id := submitted(t, o, request(o, r, "one"))
	capacityAuthority(t, o)
	if _, e := o.Capacity(fixtureToken); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("job status granted aggregate authority")
	}
	if _, e := o.Capacity("wrong-credential-for-capacity"); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("wrong credential")
	}
	before := disk(t, o)
	commit, last, attempts := o.state.Commit, o.state.LastMS, o.state.Jobs[id].Attempts
	originalClock := o.Clock
	o.Clock = func() int64 { t.Fatal("observation read clock"); return 0 }
	o.Hook = func(string) { t.Fatal("observation executed phase") }
	v := capacityValue(t, o)
	if v["revision"] != number(int64(commit)) || v["last_commit_ms"] != number(last) || v["unknown"].(omega.Object)["observation_time_ms"] != nil || v["journal"].(omega.Object)["control_reserved"] != number(0) {
		t.Fatal("missing revision/time/control accounting", v)
	}
	if v["jobs"].(omega.Object)["used"] != number(1) || v["pending"].(omega.Object)["used"] != number(1) || v["worker_phases"].(omega.Object)["spent"] != number(0) {
		t.Fatal(v)
	}
	if !bytes.Equal(before, disk(t, o)) || o.state.Commit != commit || o.state.LastMS != last || o.state.Jobs[id].Attempts != attempts {
		t.Fatal("capacity mutated accounting")
	}
	if strings.Contains(string(raw(v)), id) || strings.Contains(string(raw(v)), "delivery-one") {
		t.Fatal("job identity leaked")
	}
	o.Clock = originalClock
	o.Hook = func(string) {}
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	v = capacityValue(t, o)
	if v["closure"].(omega.Object)["captured"] != number(1) || v["worker_phases"].(omega.Object)["spent"] != number(1) {
		t.Fatal(v)
	}
	if e := o.WorkOne(); e != nil {
		t.Fatal(e)
	}
	v = capacityValue(t, o)
	if v["closure"].(omega.Object)["delivered"] != number(1) || v["pending"].(omega.Object)["used"] != number(0) || v["worker_phases"].(omega.Object)["spent"] != number(2) {
		t.Fatal(v)
	}
	p, _ := o.policy()
	p.Principals["capacity-operator"] = Principal{CredentialFile: p.Principals["capacity-operator"].CredentialFile, Scopes: map[string][]string{"synthetic-other": {"execution.capacity"}}}
	b, _ := json.Marshal(p)
	os.WriteFile(o.cfg.Policy, b, 0600)
	if _, e := o.Capacity(operatorToken); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("wrong scope")
	}
}
func TestCompletionSpaceSaturationPreservesReplayReadbackAndFinish(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	capacityAuthority(t, o)
	previous := submitted(t, o, request(o, r, "captured"))
	for i := 0; i < 2; i++ {
		if e := o.WorkOne(); e != nil {
			t.Fatal(e)
		}
	}
	captured := raw(o.state.Jobs[previous].Result)
	large := request(o, r, "large")
	large["request"].(omega.Object)["extensions"] = omega.Object{"padding": strings.Repeat("x", 88000)}
	accepted := submitted(t, o, large)
	acceptance := raw(o.state.Jobs[accepted].Acceptance)
	refused := false
	for i := 0; i < 4; i++ {
		before := disk(t, o)
		count := len(o.state.Jobs)
		original := o.get
		calls := 0
		o.get = func(ref omega.Ref, d int64) (omega.Envelope, error) { calls++; return original(ref, d) }
		_, e := o.Invoke(fixtureToken, request(o, r, fmt.Sprintf("next-%d", i)))
		o.get = original
		if e != nil {
			if e.Error() != "OVERLOADED" || o.failed || !bytes.Equal(before, disk(t, o)) || len(o.state.Jobs) != count || calls != 0 {
				t.Fatal("overload poisoned or mutated owner", e)
			}
			refused = true
			break
		}
	}
	if !refused {
		t.Fatal("did not exercise saturation")
	}
	v := capacityValue(t, o)
	if v["pending"].(omega.Object)["used"] == number(4) {
		t.Fatal("only job-count limit exercised")
	}
	if v["journal"].(omega.Object)["completion_covered"] != true {
		t.Fatal("no finish reservation")
	}
	if submitted(t, o, large) != accepted || !bytes.Equal(acceptance, raw(o.state.Jobs[accepted].Acceptance)) {
		t.Fatal("duplicate refused at saturation")
	}
	for i := 0; i < 8; i++ {
		if e := o.WorkOne(); e != nil {
			t.Fatal(e)
		}
	}
	v = capacityValue(t, o)
	if v["pending"].(omega.Object)["used"] != number(0) || o.failed {
		t.Fatal("admitted work did not finish")
	}
	if !bytes.Equal(captured, raw(o.state.Jobs[previous].Result)) {
		t.Fatal("prior capture changed")
	}
	reloaded, _ := fixture(t, filepath.Dir(o.cfg.State))
	capacityAuthority(t, reloaded)
	if e := reloaded.validateStored(); e != nil {
		t.Fatal(e)
	}
	if !bytes.Equal(raw(v), raw(capacityValue(t, reloaded))) {
		t.Fatal("capacity changed across restart")
	}
}
func TestOversizedReceiptKeepsHealthAcceptanceAndSpentReservations(t *testing.T) {
	root := t.TempDir()
	o, r := fixture(t, root)
	capacityAuthority(t, o)
	old := submitted(t, o, request(o, r, "old"))
	for i := 0; i < 2; i++ {
		if e := o.WorkOne(); e != nil {
			t.Fatal(e)
		}
	}
	prior := raw(o.state.Jobs[old].Result)
	id := submitted(t, o, request(o, r, "oversized"))
	accepted := raw(o.state.Jobs[id].Acceptance)
	original := o.create
	o.create = func(identity, kind string, b []byte, d int64) (omega.Object, error) {
		v, e := original(identity, kind, b, d)
		if e != nil {
			return nil, e
		}
		v["receipt"].(omega.Object)["evidence"] = omega.Object{"fixture": true, "padding": strings.Repeat("x", RetainedResultLimit)}
		return v, nil
	}
	for i := 0; i < 32; i++ {
		if e := o.WorkOne(); e == nil || e.Error() != "NOT_AVAILABLE" {
			t.Fatal(e)
		}
	}
	if o.failed || o.state.Jobs[id].Attempts != 32 || o.state.Jobs[id].Result != nil || !bytes.Equal(accepted, raw(o.state.Jobs[id].Acceptance)) || !bytes.Equal(prior, raw(o.state.Jobs[old].Result)) {
		t.Fatal("oversize corrupted owner")
	}
	before := disk(t, o)
	if e := o.WorkOne(); e != nil || !bytes.Equal(before, disk(t, o)) {
		t.Fatal("exhaustion retried")
	}
	v := capacityValue(t, o)
	if v["closure"].(omega.Object)["exhausted_pending"] != number(1) || v["worker_phases"].(omega.Object)["spent"] != number(34) || v["worker_phases"].(omega.Object)["remaining_for_pending"] != number(0) {
		t.Fatal(v)
	}
	reloaded, _ := fixture(t, root)
	capacityAuthority(t, reloaded)
	if !bytes.Equal(raw(v), raw(capacityValue(t, reloaded))) {
		t.Fatal("spent accounting changed")
	}
}
func TestRetainedResultBoundaryCompletesWithinProjection(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	capacityAuthority(t, o)
	id := submitted(t, o, request(o, r, "boundary"))
	create := o.create
	o.create = func(identity, kind string, data []byte, d int64) (omega.Object, error) {
		v, e := create(identity, kind, data, d)
		if e != nil {
			return nil, e
		}
		v["receipt"].(omega.Object)["evidence"] = omega.Object{"padding": ""}
		b, _ := json.Marshal(v)
		v["receipt"].(omega.Object)["evidence"].(omega.Object)["padding"] = strings.Repeat("x", RetainedResultLimit-len(b))
		b, _ = json.Marshal(v)
		if len(b) != RetainedResultLimit {
			t.Fatal(len(b))
		}
		return v, nil
	}
	projected := capacityValue(t, o)["journal"].(omega.Object)["completion_projection"]
	for i := 0; i < 2; i++ {
		if e := o.WorkOne(); e != nil {
			t.Fatal(e)
		}
	}
	n, e := integer(projected)
	if e != nil || !o.state.Jobs[id].Delivered || int64(len(disk(t, o))) > n {
		t.Fatal("projection understated finish", e)
	}
}
func TestPendingSaturationRetainsAuthenticatedCapacityRead(t *testing.T) {
	o, r := fixture(t, t.TempDir())
	capacityAuthority(t, o)
	for i := 0; i < 4; i++ {
		submitted(t, o, request(o, r, fmt.Sprintf("pending-%d", i)))
	}
	before := disk(t, o)
	if _, e := o.Invoke(fixtureToken, request(o, r, "refused")); e == nil || e.Error() != "OVERLOADED" {
		t.Fatal(e)
	}
	if capacityValue(t, o)["pending"].(omega.Object)["headroom"] != number(0) || !bytes.Equal(before, disk(t, o)) || o.failed {
		t.Fatal("saturated reads failed")
	}
}
func capacityClientConfig(t *testing.T, o *Owner, server *httptest.Server) string {
	t.Helper()
	root := t.TempDir()
	ca := filepath.Join(root, "ca.pem")
	os.WriteFile(ca, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: server.Certificate().Raw}), 0600)
	token := filepath.Join(root, "token")
	os.WriteFile(token, []byte(operatorToken), 0600)
	cfg := CapacityConfig{Profile: "go-inspect-capacity-client/1", Scope: o.cfg.Scope, Provider: Contract["selection"].(string), Endpoint: Endpoint{URL: server.URL, CAFile: ca, CredentialFile: token}}
	b, _ := json.Marshal(cfg)
	path := filepath.Join(root, "client.json")
	os.WriteFile(path, b, 0600)
	return path
}
func TestCapacityHTTPSCurrentAuthorityAndClosedClient(t *testing.T) {
	o, _ := fixture(t, t.TempDir())
	capacityAuthority(t, o)
	server := httptest.NewTLSServer(o)
	defer server.Close()
	path := capacityClientConfig(t, o, server)
	before := disk(t, o)
	v, e := ObserveCapacity(path, time.Now().Add(10*time.Second).UnixMilli())
	if e != nil || v["profile"] != CapacityProfile {
		t.Fatal(v, e)
	}
	for _, test := range []struct {
		name, method, path, body, token string
		duplicate                       bool
		code                            string
	}{
		{"native-denied", "GET", "/capacity", "", fixtureToken, false, "UNAUTHORIZED"},
		{"wrong-credential", "GET", "/capacity", "", "wrong-token-unknown", false, "UNAUTHORIZED"},
		{"query-denied", "GET", "/capacity?scope=synthetic-other", "", operatorToken, false, "INVALID_ARGUMENT"},
		{"body-denied", "GET", "/capacity", "{}", operatorToken, false, "INVALID_ARGUMENT"},
		{"write-denied", "POST", "/capacity", "{}", operatorToken, false, "INVALID_ARGUMENT"},
		{"duplicate-authorization", "GET", "/capacity", "", operatorToken, true, "UNAUTHORIZED"},
	} {
		t.Run(test.name, func(t *testing.T) {
			req, _ := http.NewRequest(test.method, server.URL+test.path, strings.NewReader(test.body))
			req.Header.Set("Authorization", "Bearer "+test.token)
			if test.duplicate {
				req.Header.Add("Authorization", "Bearer "+test.token)
			}
			resp, e := server.Client().Do(req)
			if e != nil {
				t.Fatal(e)
			}
			b, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			v, e := omega.Decode(b)
			if e != nil || v.(omega.Object)["error"].(omega.Object)["code"] != test.code {
				t.Fatal(string(b), e)
			}
		})
	}
	if _, e = ObserveCapacity(path, time.Now().Add(-time.Second).UnixMilli()); e == nil || e.Error() != "DEADLINE_EXCEEDED" {
		t.Fatal("deadline renewed", e)
	}
	p, _ := o.policy()
	delete(p.Principals, "capacity-operator")
	b, _ := json.Marshal(p)
	os.WriteFile(o.cfg.Policy, b, 0600)
	if _, e = ObserveCapacity(path, time.Now().Add(10*time.Second).UnixMilli()); e == nil || e.Error() != "UNAUTHORIZED" {
		t.Fatal("revocation cached", e)
	}
	if !bytes.Equal(before, disk(t, o)) {
		t.Fatal("HTTP observation wrote journal")
	}
}
func TestCapacityClientRejectsMalformedAccounting(t *testing.T) {
	o, _ := fixture(t, t.TempDir())
	capacityAuthority(t, o)
	base := capacityValue(t, o)
	for _, test := range []struct {
		name   string
		change func(omega.Object)
	}{
		{"zero-revision", func(v omega.Object) { v["revision"] = number(0) }},
		{"fake-control-reserve", func(v omega.Object) { v["journal"].(omega.Object)["control_reserved"] = number(100) }},
		{"invented-read-time", func(v omega.Object) { v["unknown"].(omega.Object)["observation_time_ms"] = number(1234) }},
		{"wrong-scope", func(v omega.Object) { v["scope"] = "synthetic-other" }},
		{"wrong-selection", func(v omega.Object) { v["provider"] = strings.Repeat("0", 64) }},
		{"extra-field", func(v omega.Object) { v["job_ids"] = []interface{}{} }},
		{"invented-physical-measurement", func(v omega.Object) { v["unknown"].(omega.Object)["filesystem_free_bytes"] = number(100) }},
		{"wrong-headroom", func(v omega.Object) { v["pending"].(omega.Object)["headroom"] = number(5) }},
		{"negative-spent", func(v omega.Object) { v["worker_phases"].(omega.Object)["spent"] = number(-1) }},
		{"false-completion-coverage", func(v omega.Object) { v["journal"].(omega.Object)["completion_covered"] = false }},
		{"wrong-reserve", func(v omega.Object) { v["journal"].(omega.Object)["completion_reserved"] = number(0) }},
	} {
		t.Run(test.name, func(t *testing.T) {
			v, e := omega.Decode(raw(base))
			if e != nil {
				t.Fatal(e)
			}
			value := v.(omega.Object)
			test.change(value)
			if e = checkCapacity(value, o.cfg.Scope); e == nil {
				t.Fatal("accepted malformed accounting")
			}
		})
	}
}
