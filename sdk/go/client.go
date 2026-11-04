// Package omega is an independent stdlib client for selected existing Fusion
// session and immutable AtomStorage ports. It imports no Python/runtime owner.
package omega

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"
)

const MaxWire = 131072
const SessionProfile = "omega-native-sessions/3"

type Object = map[string]interface{}
type Ref struct {
	Scope    string      `json:"scope_ref"`
	ID       string      `json:"id"`
	Revision json.Number `json:"revision"`
	Digest   string      `json:"digest"`
}
type Envelope struct {
	Ref         Ref
	ContentType string
	Bytes       []byte
}
type Config struct {
	Profile        string `json:"profile"`
	Kind           string `json:"kind"`
	Endpoint       string `json:"endpoint"`
	ServerName     string `json:"server_name"`
	CAFile         string `json:"ca_file"`
	CredentialFile string `json:"credential_file"`
	Principal      string `json:"principal"`
	Actor          string `json:"actor"`
	Scope          string `json:"scope"`
	Contract       string `json:"contract"`
	Composition    string `json:"composition"`
	Descriptor     Object `json:"descriptor"`
}
type Client struct {
	cfg       Config
	selection string
	trust     [32]byte
}

var label = regexp.MustCompile(`^[a-zA-Z0-9_.:/-]{1,128}$`)
var uuid = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`)
var shaPattern = regexp.MustCompile(`^[0-9a-f]{64}$`)

func failure(code string) error { return errors.New(code) }
func hash(b []byte) string      { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }

// Decode rejects duplicate keys, excess nesting, malformed UTF-8 and trailing
// values. Numbers never pass through float64, including integers above 2^53.
func Decode(raw []byte) (interface{}, error) {
	if len(raw) > MaxWire || !utf8.Valid(raw) || !validEscapes(raw) {
		return nil, failure("NOT_AVAILABLE")
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	var read func(int) (interface{}, error)
	read = func(depth int) (interface{}, error) {
		if depth > 64 {
			return nil, failure("NOT_AVAILABLE")
		}
		t, e := d.Token()
		if e != nil {
			return nil, e
		}
		switch x := t.(type) {
		case json.Delim:
			if x == '{' {
				v := Object{}
				for d.More() {
					k, e := d.Token()
					if e != nil {
						return nil, e
					}
					key, ok := k.(string)
					if !ok {
						return nil, failure("NOT_AVAILABLE")
					}
					if _, found := v[key]; found {
						return nil, failure("NOT_AVAILABLE")
					}
					item, e := read(depth + 1)
					if e != nil {
						return nil, e
					}
					v[key] = item
				}
				end, e := d.Token()
				if e != nil || end != json.Delim('}') {
					return nil, failure("NOT_AVAILABLE")
				}
				return v, nil
			}
			if x == '[' {
				v := []interface{}{}
				for d.More() {
					item, e := read(depth + 1)
					if e != nil {
						return nil, e
					}
					v = append(v, item)
				}
				end, e := d.Token()
				if e != nil || end != json.Delim(']') {
					return nil, failure("NOT_AVAILABLE")
				}
				return v, nil
			}
			return nil, failure("NOT_AVAILABLE")
		default:
			return t, nil
		}
	}
	v, e := read(0)
	if e != nil {
		return nil, failure("NOT_AVAILABLE")
	}
	if _, e = d.Token(); e != io.EOF {
		return nil, failure("NOT_AVAILABLE")
	}
	return v, nil
}
func validEscapes(raw []byte) bool {
	inside := false
	for i := 0; i < len(raw); i++ {
		if raw[i] == '"' {
			inside = !inside
			continue
		}
		if !inside || raw[i] != '\\' {
			continue
		}
		i++
		if i >= len(raw) {
			return false
		}
		if raw[i] != 'u' {
			continue
		}
		if i+4 >= len(raw) {
			return false
		}
		n, e := strconv.ParseUint(string(raw[i+1:i+5]), 16, 16)
		if e != nil {
			return false
		}
		i += 4
		if n >= 0xdc00 && n <= 0xdfff {
			return false
		}
		if n >= 0xd800 && n <= 0xdbff {
			if i+6 >= len(raw) || raw[i+1] != '\\' || raw[i+2] != 'u' {
				return false
			}
			low, e := strconv.ParseUint(string(raw[i+3:i+7]), 16, 16)
			if e != nil || low < 0xdc00 || low > 0xdfff {
				return false
			}
			i += 6
		}
	}
	return true
}

// Canonical implements the selected request domain (objects/arrays/strings,
// booleans/null/exact integers), matching Python's UTF-8 canonical wire bytes.
// Floating point request fields are deliberately unsupported, not rounded.
func Canonical(value interface{}) ([]byte, error) {
	var b bytes.Buffer
	var write func(interface{}, int) error
	quote := func(s string) error {
		if !utf8.ValidString(s) {
			return failure("INVALID_ARGUMENT")
		}
		b.WriteByte('"')
		for _, r := range s {
			switch r {
			case '"', '\\':
				b.WriteByte('\\')
				b.WriteRune(r)
			case '\b':
				b.WriteString(`\b`)
			case '\f':
				b.WriteString(`\f`)
			case '\n':
				b.WriteString(`\n`)
			case '\r':
				b.WriteString(`\r`)
			case '\t':
				b.WriteString(`\t`)
			default:
				if r < 32 {
					fmt.Fprintf(&b, `\u%04x`, r)
				} else {
					b.WriteRune(r)
				}
			}
		}
		b.WriteByte('"')
		return nil
	}
	write = func(v interface{}, depth int) error {
		if depth > 64 {
			return failure("INVALID_ARGUMENT")
		}
		switch x := v.(type) {
		case nil:
			b.WriteString("null")
		case bool:
			if x {
				b.WriteString("true")
			} else {
				b.WriteString("false")
			}
		case string:
			return quote(x)
		case int:
			b.WriteString(strconv.Itoa(x))
		case int64:
			b.WriteString(strconv.FormatInt(x, 10))
		case json.Number:
			n, ok := new(big.Int).SetString(string(x), 10)
			if !ok {
				return failure("UNSUPPORTED_PROFILE")
			}
			b.WriteString(n.String())
		case Object:
			keys := make([]string, 0, len(x))
			for k := range x {
				keys = append(keys, k)
			}
			sort.Strings(keys)
			b.WriteByte('{')
			for i, k := range keys {
				if i > 0 {
					b.WriteByte(',')
				}
				if e := quote(k); e != nil {
					return e
				}
				b.WriteByte(':')
				if e := write(x[k], depth+1); e != nil {
					return e
				}
			}
			b.WriteByte('}')
		case []interface{}:
			b.WriteByte('[')
			for i, v := range x {
				if i > 0 {
					b.WriteByte(',')
				}
				if e := write(v, depth+1); e != nil {
					return e
				}
			}
			b.WriteByte(']')
		default:
			return failure("UNSUPPORTED_PROFILE")
		}
		return nil
	}
	if e := write(value, 0); e != nil {
		return nil, e
	}
	if b.Len() > MaxWire {
		return nil, failure("OVERLOADED")
	}
	return b.Bytes(), nil
}
func exact(v Object, keys ...string) bool {
	if len(v) != len(keys) {
		return false
	}
	for _, k := range keys {
		if _, ok := v[k]; !ok {
			return false
		}
	}
	return true
}
func integer(v interface{}, lo, hi int64) (int64, error) {
	n, ok := v.(json.Number)
	if !ok {
		return 0, failure("NOT_AVAILABLE")
	}
	x, e := n.Int64()
	if e != nil || x < lo || x > hi {
		return 0, failure("NOT_AVAILABLE")
	}
	return x, nil
}
func contains(v interface{}, s string) bool {
	a, ok := v.([]interface{})
	if !ok {
		return false
	}
	for _, x := range a {
		if text, ok := x.(string); ok && text == s {
			return true
		}
	}
	return false
}

func ReadConfig(path string) (Config, error) {
	var c Config
	raw, e := os.ReadFile(path)
	if e != nil {
		return c, e
	}
	if _, e = Decode(raw); e != nil {
		return c, e
	}
	d := json.NewDecoder(bytes.NewReader(raw))
	d.UseNumber()
	d.DisallowUnknownFields()
	e = d.Decode(&c)
	return c, e
}
func New(c Config) (*Client, error) {
	u, e := url.Parse(c.Endpoint)
	if e != nil || u.Scheme != "https" || u.Hostname() == "" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" {
		return nil, failure("INVALID_ARGUMENT")
	}
	if c.Profile != "fusion-go-client/1" || !label.MatchString(c.Principal) || !label.MatchString(c.Scope) || !strings.HasPrefix(c.Scope, "synthetic-") {
		return nil, failure("UNSUPPORTED_PROFILE")
	}
	ca, e := os.ReadFile(c.CAFile)
	if e != nil {
		return nil, e
	}
	client := &Client{cfg: c, trust: sha256.Sum256(ca)}
	if c.Kind == "session" {
		if c.Contract != SessionProfile || c.Actor != "operator" {
			return nil, failure("UNSUPPORTED_PROFILE")
		}
	} else if c.Kind == "atom" {
		d := c.Descriptor
		if !exact(d, "provider", "interface", "version", "implementation_version", "profiles", "operations", "guarantees", "max_payload_bytes", "privacy", "deterministic", "features", "verified_evidence", "verification", "measured_slo", "receipt_providers", "durabilities") {
			return nil, failure("UNSUPPORTED_PROFILE")
		}
		if d["interface"] != "atom.storage" || (d["version"] != "1.0.0" && d["version"] != "1.1.0") || d["privacy"] != "generated-shareable" || (c.Contract != "immutable-commit-feed/1" && c.Contract != "immutable-commit-feed/2") || !contains(d["profiles"], c.Contract) {
			return nil, failure("UNSUPPORTED_PROFILE")
		}
		for _, op := range []string{"create", "get", "getMany", "availability", "head", "readCommits"} {
			if !contains(d["operations"], op) {
				return nil, failure("UNSUPPORTED_OPERATION")
			}
		}
		for _, g := range []string{"scoped", "process-restart"} {
			if !contains(d["guarantees"], g) {
				return nil, failure("NOT_AVAILABLE")
			}
		}
		if _, e = integer(d["max_payload_bytes"], 4096, 131072); e != nil {
			return nil, e
		}
		if c.Composition != "typed-atom-feed-https/1" && c.Composition != "synthetic-cognitive-services/1" {
			return nil, failure("UNSUPPORTED_PROFILE")
		}
		wire, e := Canonical(d)
		if e != nil {
			return nil, e
		}
		client.selection = hash(wire)
	} else {
		return nil, failure("UNSUPPORTED_PROFILE")
	}
	return client, nil
}

func (c *Client) exchange(path string, q Object, deadline int64) (Object, error) {
	if deadline <= time.Now().UnixMilli() {
		return nil, failure("DEADLINE_EXCEEDED")
	}
	raw, e := Canonical(q)
	if e != nil {
		return nil, e
	}
	ca, e := os.ReadFile(c.cfg.CAFile)
	if e != nil || sha256.Sum256(ca) != c.trust {
		return nil, failure("CONFLICT")
	}
	secret, e := os.ReadFile(c.cfg.CredentialFile)
	if e != nil {
		return nil, e
	}
	token := strings.TrimSuffix(string(secret), "\n")
	if len(token) < 1 || len(token) > 256 || strings.ContainsAny(token, "\r\n") {
		return nil, failure("UNAUTHORIZED")
	}
	for _, r := range token {
		if r > 127 {
			return nil, failure("UNAUTHORIZED")
		}
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(ca) {
		return nil, failure("NOT_AVAILABLE")
	}
	transport := &http.Transport{TLSClientConfig: &tls.Config{RootCAs: roots, ServerName: c.cfg.ServerName, MinVersion: tls.VersionTLS12}, DisableKeepAlives: true, MaxResponseHeaderBytes: 16384, ForceAttemptHTTP2: false}
	defer transport.CloseIdleConnections()
	end := time.UnixMilli(deadline)
	if cap := time.Now().Add(30 * time.Second); cap.Before(end) {
		end = cap
	}
	ctx, cancel := context.WithDeadline(context.Background(), end)
	defer cancel()
	request, e := http.NewRequestWithContext(ctx, "POST", c.cfg.Endpoint+path, bytes.NewReader(raw))
	if e != nil {
		return nil, e
	}
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+token)
	h := &http.Client{Transport: transport, CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse }}
	response, e := h.Do(request)
	if e != nil {
		return nil, failure("NOT_AVAILABLE")
	}
	defer response.Body.Close()
	if response.StatusCode != 200 && response.StatusCode != 400 && response.StatusCode != 401 && response.StatusCode != 403 && response.StatusCode != 503 {
		return nil, failure("NOT_AVAILABLE")
	}
	wire, e := io.ReadAll(io.LimitReader(response.Body, MaxWire+1))
	if e != nil {
		return nil, failure("NOT_AVAILABLE")
	}
	v, e := Decode(wire)
	if e != nil {
		return nil, e
	}
	reply, ok := v.(Object)
	if !ok {
		return nil, failure("NOT_AVAILABLE")
	}
	if exact(reply, "error") {
		item, ok := reply["error"].(Object)
		if !ok || !exact(item, "code", "retryable") {
			return nil, failure("NOT_AVAILABLE")
		}
		code, ok := item["code"].(string)
		if !ok || !contains([]interface{}{"UNAUTHORIZED", "NOT_AVAILABLE", "NOT_FOUND", "CONFLICT", "OVERLOADED", "DEADLINE_EXCEEDED", "INVALID_ARGUMENT", "UNSUPPORTED_PROFILE", "UNSUPPORTED_OPERATION", "UNSUPPORTED_VERSION", "INTERNAL"}, code) {
			return nil, failure("NOT_AVAILABLE")
		}
		retry, ok := item["retryable"].(bool)
		if !ok || retry != (code == "NOT_AVAILABLE" || code == "OVERLOADED") {
			return nil, failure("NOT_AVAILABLE")
		}
		return nil, failure(code)
	}
	if response.StatusCode != 200 || reply["id"] != q["id"] || reply["request_digest"] != hash(raw) {
		return nil, failure("NOT_AVAILABLE")
	}
	if reply["principal"] != c.cfg.Principal {
		return nil, failure("UNAUTHORIZED")
	}
	if time.Now().UnixMilli() >= deadline {
		return nil, failure("DEADLINE_EXCEEDED")
	}
	return reply, nil
}
func requestID() string {
	var b [16]byte
	if _, e := rand.Read(b[:]); e != nil {
		panic(e)
	}
	b[6] = (b[6] & 15) | 64
	b[8] = (b[8] & 63) | 128
	h := hex.EncodeToString(b[:])
	return h[:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:]
}
func (c *Client) atom(op string, args []interface{}, deadline int64) (interface{}, error) {
	if c.cfg.Kind != "atom" {
		return nil, failure("UNSUPPORTED_PROFILE")
	}
	q := Object{"id": requestID(), "composition": c.cfg.Composition, "scope": c.cfg.Scope, "interface": "atom.storage", "selection": c.selection, "operation": op, "args": args}
	reply, e := c.exchange("/reference-cognition", q, deadline)
	if e != nil {
		return nil, e
	}
	if !exact(reply, "id", "request_digest", "selection", "principal", "value") || reply["selection"] != c.selection {
		return nil, failure("NOT_AVAILABLE")
	}
	return reply["value"], nil
}
func ref(v interface{}, scope string) (Ref, error) {
	r := Ref{}
	o, ok := v.(Object)
	if !ok || !exact(o, "scope_ref", "id", "revision", "digest") {
		return r, failure("NOT_AVAILABLE")
	}
	if o["scope_ref"] != scope {
		return r, failure("UNAUTHORIZED")
	}
	id, ok := o["id"].(string)
	if !ok || !uuid.MatchString(id) {
		return r, failure("NOT_AVAILABLE")
	}
	d, ok := o["digest"].(string)
	if !ok || !shaPattern.MatchString(d) {
		return r, failure("NOT_AVAILABLE")
	}
	if _, e := integer(o["revision"], 1, 1); e != nil {
		return r, e
	}
	return Ref{scope, id, "1", d}, nil
}
func (r Ref) wire() Object {
	return Object{"scope_ref": r.Scope, "id": r.ID, "revision": r.Revision, "digest": r.Digest}
}

func ParseRef(raw []byte) (Ref, error) {
	value, err := Decode(raw)
	if err != nil {
		return Ref{}, err
	}
	o, ok := value.(Object)
	if !ok {
		return Ref{}, failure("INVALID_ARGUMENT")
	}
	scope, ok := o["scope_ref"].(string)
	if !ok || !label.MatchString(scope) {
		return Ref{}, failure("INVALID_ARGUMENT")
	}
	return ref(o, scope)
}
func (c *Client) Head(deadline int64) (Object, error) {
	v, e := c.atom("head", []interface{}{c.cfg.Scope}, deadline)
	if e != nil {
		return nil, e
	}
	o, ok := v.(Object)
	if !ok || !exact(o, "profile", "scope_ref", "source", "sequence") || o["profile"] != c.cfg.Contract || o["scope_ref"] != c.cfg.Scope {
		return nil, failure("NOT_AVAILABLE")
	}
	id, ok := o["source"].(string)
	if !ok || !uuid.MatchString(id) {
		return nil, failure("NOT_AVAILABLE")
	}
	if _, e = integer(o["sequence"], 0, 4096); e != nil {
		return nil, e
	}
	return o, nil
}
func (c *Client) Create(identity, contentType string, data []byte, deadline int64) (Ref, error) {
	if !label.MatchString(identity) || !label.MatchString(contentType) || len(data) < 1 || len(data) > 4096 {
		return Ref{}, failure("INVALID_ARGUMENT")
	}
	v, e := c.atom("create", []interface{}{Object{"scope_ref": c.cfg.Scope, "idempotency_key": identity, "intent_digest": nil}, contentType, Object{"bytes": base64.StdEncoding.EncodeToString(data)}}, deadline)
	if e != nil {
		return Ref{}, e
	}
	o, ok := v.(Object)
	if !ok || !exact(o, "ref", "receipt") {
		return Ref{}, failure("NOT_AVAILABLE")
	}
	r, e := ref(o["ref"], c.cfg.Scope)
	if e != nil {
		return r, e
	}
	if r.Digest != hash(data) {
		return r, failure("NOT_AVAILABLE")
	}
	receipt, ok := o["receipt"].(Object)
	if !ok || !exact(receipt, "provider", "durability", "evidence") {
		return r, failure("NOT_AVAILABLE")
	}
	provider, ok := receipt["provider"].(string)
	if !ok || !contains(c.cfg.Descriptor["receipt_providers"], provider) {
		return r, failure("NOT_AVAILABLE")
	}
	durability, ok := receipt["durability"].(string)
	if !ok || !contains(c.cfg.Descriptor["durabilities"], durability) {
		return r, failure("NOT_AVAILABLE")
	}
	if _, ok := receipt["evidence"].(Object); !ok {
		return r, failure("NOT_AVAILABLE")
	}
	return r, nil
}
func (c *Client) Get(r Ref, deadline int64) (Envelope, error) {
	var out Envelope
	if _, e := ref(r.wire(), c.cfg.Scope); e != nil {
		return out, e
	}
	v, e := c.atom("get", []interface{}{r.wire()}, deadline)
	if e != nil {
		return out, e
	}
	o, ok := v.(Object)
	if !ok || !exact(o, "ref", "content_type", "data") {
		return out, failure("NOT_AVAILABLE")
	}
	got, e := ref(o["ref"], c.cfg.Scope)
	if e != nil || got != r {
		return out, failure("NOT_AVAILABLE")
	}
	kind, ok := o["content_type"].(string)
	if !ok || !label.MatchString(kind) {
		return out, failure("NOT_AVAILABLE")
	}
	encoded, ok := o["data"].(string)
	if !ok {
		return out, failure("NOT_AVAILABLE")
	}
	data, e := base64.StdEncoding.Strict().DecodeString(encoded)
	if e != nil || len(data) < 1 || len(data) > 4096 || base64.StdEncoding.EncodeToString(data) != encoded || hash(data) != r.Digest {
		return out, failure("NOT_AVAILABLE")
	}
	return Envelope{r, kind, data}, nil
}
func (c *Client) Session(op string, body Object, deadline int64) (Object, error) {
	if c.cfg.Kind != "session" || !contains([]interface{}{"allocate", "binding", "submit", "observe", "capacity"}, op) {
		return nil, failure("UNSUPPORTED_OPERATION")
	}
	shapes := map[string][]string{"allocate": {"identity", "template"}, "binding": {"session"}, "submit": {"session", "identity", "text", "assignment"}, "observe": {"session", "content"}, "capacity": {}}
	if !exact(body, shapes[op]...) {
		return nil, failure("INVALID_ARGUMENT")
	}
	for _, key := range []string{"identity", "template", "assignment"} {
		if v, exists := body[key]; exists {
			s, ok := v.(string)
			if !ok || !label.MatchString(s) {
				return nil, failure("INVALID_ARGUMENT")
			}
		}
	}
	if op == "submit" {
		text, ok := body["text"].(string)
		if !ok || len(text) < 1 || len(text) > 1024 || !utf8.ValidString(text) {
			return nil, failure("INVALID_ARGUMENT")
		}
	}
	if op == "observe" {
		if _, ok := body["content"].(bool); !ok {
			return nil, failure("INVALID_ARGUMENT")
		}
	}
	if op != "allocate" && op != "capacity" {
		s, ok := body["session"].(string)
		if !ok || !uuid.MatchString(s) {
			return nil, failure("INVALID_ARGUMENT")
		}
	}
	q := Object{"id": requestID(), "profile": SessionProfile, "operation": op, "body": body}
	r, e := c.exchange("/preview/session", q, deadline)
	if e != nil {
		return nil, e
	}
	if !exact(r, "id", "profile", "request_digest", "actor", "principal", "value") || r["profile"] != SessionProfile || r["actor"] != c.cfg.Actor {
		return nil, failure("NOT_AVAILABLE")
	}
	value, ok := r["value"].(Object)
	if !ok {
		return nil, failure("NOT_AVAILABLE")
	}
	if op == "allocate" || op == "binding" || op == "observe" {
		if value["scope"] != c.cfg.Scope || value["principal"] != c.cfg.Principal {
			return nil, failure("UNAUTHORIZED")
		}
		if !contains([]interface{}{"active", "paused", "closed", "archived"}, fmt.Sprint(value["state"])) {
			return nil, failure("NOT_AVAILABLE")
		}
	}
	if op == "binding" {
		if !exact(value, "session", "principal", "scope", "state", "expires_ms") {
			return nil, failure("NOT_AVAILABLE")
		}
		if _, e = integer(value["expires_ms"], 1, 1<<63-1); e != nil {
			return nil, e
		}
	}
	if op == "allocate" || op == "binding" || op == "submit" || op == "observe" {
		sid, ok := value["session"].(string)
		if !ok || !uuid.MatchString(sid) {
			return nil, failure("NOT_AVAILABLE")
		}
		if op != "allocate" && sid != body["session"] {
			return nil, failure("NOT_AVAILABLE")
		}
	}
	if op == "submit" {
		if value["id"] != body["identity"] {
			return nil, failure("NOT_AVAILABLE")
		}
		if _, e = integer(value["deadline"], 1, 1<<63-1); e != nil {
			return nil, e
		}
	}
	if op == "observe" || op == "allocate" {
		if !exact(value, "session", "principal", "scope", "state", "binding", "inputs", "live_generations", "next_after", "complete", "capacity", "profile", "ordering", "allocation", "observations_do_not_dispatch") || value["profile"] != SessionProfile || value["ordering"] != "causal-session-fence/1" || value["observations_do_not_dispatch"] != true {
			return nil, failure("NOT_AVAILABLE")
		}
		if _, e = integer(value["live_generations"], 0, 0); e != nil {
			return nil, e
		}
		complete, ok := value["complete"].(bool)
		if !ok || complete && value["next_after"] != nil {
			return nil, failure("NOT_AVAILABLE")
		}
		if !complete {
			if _, e = integer(value["next_after"], 1, 32); e != nil {
				return nil, e
			}
		}
		rows, ok := value["inputs"].([]interface{})
		if !ok || len(rows) > 32 {
			return nil, failure("NOT_AVAILABLE")
		}
		last := int64(0)
		identities := map[string]bool{}
		for _, r := range rows {
			row, ok := r.(Object)
			if !ok || row["session"] != value["session"] {
				return nil, failure("NOT_AVAILABLE")
			}
			if !exact(row, "session", "id", "sequence", "assignment", "deadline", "state", "accepted", "outcome") && !exact(row, "session", "id", "sequence", "assignment", "deadline", "state", "accepted", "outcome", "payload", "result") {
				return nil, failure("NOT_AVAILABLE")
			}
			sequence, e := integer(row["sequence"], last+1, 32)
			if e != nil {
				return nil, e
			}
			last = sequence
			id, ok := row["id"].(string)
			if !ok || !label.MatchString(id) || identities[id] {
				return nil, failure("NOT_AVAILABLE")
			}
			identities[id] = true
			accepted, e := integer(row["accepted"], 1, 1<<63-1)
			if e != nil {
				return nil, e
			}
			if _, e = integer(row["deadline"], accepted+1, 1<<63-1); e != nil {
				return nil, e
			}
			state, ok := row["state"].(string)
			if !ok || !contains([]interface{}{"accepted", "dispatched", "complete", "cancel-requested", "needs-reconciliation", "expired-before-start", "cancelled-before-start", "rejected"}, state) {
				return nil, failure("NOT_AVAILABLE")
			}
			if result, exists := row["result"]; exists && result != nil {
				item, ok := result.(Object)
				if !ok || !exact(item, "occurrences", "projection", "turn") || state != "complete" {
					return nil, failure("NOT_AVAILABLE")
				}
				if _, e = integer(item["turn"], 1, 32); e != nil {
					return nil, e
				}
				text, ok := item["projection"].(string)
				if !ok || len(text) > 65536 {
					return nil, failure("NOT_AVAILABLE")
				}
				if _, ok = item["occurrences"].([]interface{}); !ok {
					return nil, failure("NOT_AVAILABLE")
				}
			}
		}
	}
	return value, nil
}
