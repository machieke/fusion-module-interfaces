package omega

import (
	"bytes"
	"encoding/json"
	"encoding/pem"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestCanonicalIntegerAndUnicode(t *testing.T) {
	input := []byte("{\"z\":9007199254740993,\"a\":\"snow 雪 < > & \u2028\",\"n\":-0}")
	v, e := Decode(input)
	if e != nil {
		t.Fatal(e)
	}
	raw, e := Canonical(v)
	if e != nil {
		t.Fatal(e)
	}
	expected := []byte("{\"a\":\"snow 雪 < > & \u2028\",\"n\":0,\"z\":9007199254740993}")
	if !bytes.Equal(raw, expected) {
		t.Fatalf("%s", raw)
	}
	if _, e = Canonical(Object{"float": 1.1}); e == nil {
		t.Fatal("unsupported request float accepted")
	}
}

func TestNormativeGoldenWireAndUUID(t *testing.T) {
	raw, e := os.ReadFile("testdata/golden.json")
	if e != nil {
		t.Fatal(e)
	}
	v, e := Decode(raw)
	if e != nil {
		t.Fatal(e)
	}
	g := v.(Object)
	request, e := Canonical(g["request"])
	if e != nil || string(request) != g["canonical_request"] || hash(request) != g["request_sha256"] {
		t.Fatal("canonical mismatch", e)
	}
	descriptor, e := Canonical(g["descriptor"])
	if e != nil || hash(descriptor) != g["selection"] {
		t.Fatal("selection mismatch", e)
	}
	for i := 0; i < 16; i++ {
		if !uuid.MatchString(requestID()) {
			t.Fatal("non-canonical wire identity")
		}
	}
}
func TestStrictMalformedJSON(t *testing.T) {
	for _, raw := range []string{`{"x":1,"x":2}`, `{"x":{"a":1,"a":2}}`, `{"x":NaN}`, `{"x":1} {}`, `"\ud800"`, `"\udfff"`, strings.Repeat("[", 66) + "1" + strings.Repeat("]", 66), string([]byte{'"', 0xff, '"'})} {
		if _, e := Decode([]byte(raw)); e == nil {
			t.Fatalf("accepted %q", raw)
		}
	}
	for _, raw := range []string{`"\ud83d\ude80"`, `"\\ud800"`, `{"large":9223372036854775808}`} {
		if _, e := Decode([]byte(raw)); e != nil {
			t.Fatal(raw, e)
		}
	}
}
func sessionFixture(t *testing.T, callback func(Object) Object) (*Client, *int) {
	t.Helper()
	calls := 0
	srv := httptest.NewTLSServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		if r.Header.Get("Authorization") != "Bearer generated-secret" {
			t.Error("wrong authority")
		}
		raw, _ := io.ReadAll(r.Body)
		q, e := Decode(raw)
		if e != nil {
			t.Error(e)
		}
		request := q.(Object)
		reply := Object{"id": request["id"], "profile": SessionProfile, "request_digest": hash(raw), "actor": "operator", "principal": "A", "value": Object{"session": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "scope": "synthetic-go", "principal": "A", "state": "active", "expires_ms": json.Number("9007199254740993")}}
		if callback != nil {
			reply = callback(reply)
		}
		if reply == nil {
			h := w.(http.Hijacker)
			c, _, _ := h.Hijack()
			c.Close()
			return
		}
		_ = json.NewEncoder(w).Encode(reply)
	}))
	t.Cleanup(srv.Close)
	root := t.TempDir()
	ca := filepath.Join(root, "ca.pem")
	secret := filepath.Join(root, "token")
	os.WriteFile(ca, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: srv.Certificate().Raw}), 0600)
	os.WriteFile(secret, []byte("generated-secret"), 0600)
	c, e := New(Config{Profile: "fusion-go-client/1", Kind: "session", Endpoint: srv.URL, CAFile: ca, CredentialFile: secret, Principal: "A", Actor: "operator", Scope: "synthetic-go", Contract: SessionProfile})
	if e != nil {
		t.Fatal(e)
	}
	return c, &calls
}
func TestRealTLSMetadataAndExactLargeNumber(t *testing.T) {
	c, calls := sessionFixture(t, nil)
	v, e := c.Session("binding", Object{"session": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}, time.Now().UnixMilli()+3000)
	if e != nil {
		t.Fatal(e)
	}
	if v["expires_ms"] != json.Number("9007199254740993") || *calls != 1 {
		t.Fatal(v, *calls)
	}
}
func TestSemanticBindingRefusals(t *testing.T) {
	for _, key := range []string{"id", "principal", "request_digest", "profile", "actor"} {
		t.Run(key, func(t *testing.T) {
			c, calls := sessionFixture(t, func(v Object) Object { v[key] = "wrong"; return v })
			_, e := c.Session("binding", Object{"session": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}, time.Now().UnixMilli()+3000)
			if e == nil || *calls != 1 {
				t.Fatal("unbound result", e, *calls)
			}
		})
	}
}
func TestLostResponseAndDeadlineHaveNoRetry(t *testing.T) {
	c, calls := sessionFixture(t, func(Object) Object { return nil })
	body := Object{"session": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "identity": "new", "assignment": "synthetic-task", "text": "query synthetic compass"}
	_, e := c.Session("submit", body, time.Now().UnixMilli()+3000)
	if e == nil || *calls != 1 {
		t.Fatal(e, *calls)
	}
	_, e = c.Session("submit", body, time.Now().UnixMilli()-1)
	if e == nil || *calls != 1 {
		t.Fatal("renewed deadline")
	}
}
func TestWrongScopeProfileAndMethodAreNotCoerced(t *testing.T) {
	c, calls := sessionFixture(t, nil)
	if _, e := c.Session("arbitrary", Object{}, time.Now().UnixMilli()+3000); e == nil {
		t.Fatal("arbitrary method")
	}
	if _, e := c.Session("submit", Object{"session": "bad"}, time.Now().UnixMilli()+3000); e == nil {
		t.Fatal("bad identity")
	}
	if *calls != 0 {
		t.Fatal("bad request transmitted")
	}
	r := Object{"scope_ref": "other", "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "revision": json.Number("1"), "digest": strings.Repeat("a", 64)}
	if _, e := ref(r, "synthetic-go"); e == nil {
		t.Fatal("cross scope")
	}
}

func observationFixture() Object {
	row := Object{"session": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "id": "one", "sequence": json.Number("1"), "assignment": "synthetic-task", "deadline": json.Number("120001"), "accepted": json.Number("1"), "state": "complete", "outcome": nil}
	return Object{"session": row["session"], "scope": "synthetic-go", "principal": "A", "state": "active", "profile": SessionProfile, "ordering": "causal-session-fence/1", "observations_do_not_dispatch": true, "live_generations": json.Number("0"), "complete": true, "next_after": nil, "binding": Object{}, "allocation": Object{}, "capacity": Object{}, "inputs": []interface{}{row}}
}
func TestObservationStatesOrderingAndMandatoryFields(t *testing.T) {
	for _, mode := range []string{"valid", "unknown-state", "order", "unknown-field", "bad-deadline", "float-deadline", "unknown-result"} {
		t.Run(mode, func(t *testing.T) {
			c, _ := sessionFixture(t, func(reply Object) Object {
				v := observationFixture()
				row := v["inputs"].([]interface{})[0].(Object)
				switch mode {
				case "unknown-state":
					row["state"] = "restarted-free"
				case "order":
					v["inputs"] = []interface{}{row, row}
				case "unknown-field":
					v["mandatory_new_semantics"] = true
				case "bad-deadline":
					row["deadline"] = json.Number("0")
				case "float-deadline":
					row["deadline"] = 1.2
				case "unknown-result":
					row["payload"] = Object{}
					row["result"] = Object{"expected": "fixture answer"}
				}
				reply["value"] = v
				return reply
			})
			_, e := c.Session("observe", Object{"session": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "content": true}, time.Now().UnixMilli()+3000)
			if (e == nil) != (mode == "valid") {
				t.Fatal(mode, e)
			}
		})
	}
}
