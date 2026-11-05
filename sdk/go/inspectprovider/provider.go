// Package inspectprovider independently implements bounded immutable inspection.
// It imports the existing wire/client codec, never a Python owner or evaluator.
package inspectprovider

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha1"
	"crypto/sha256"
	"crypto/subtle"
	"crypto/tls"
	"crypto/x509"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	omega "fusion.local/omega"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

//go:embed contract.json
var contractBytes []byte
var Contract omega.Object

func init() {
	v, e := omega.Decode(contractBytes)
	if e != nil {
		panic(e)
	}
	Contract = v.(omega.Object)
}
func hash(b []byte) string { h := sha256.Sum256(b); return hex.EncodeToString(h[:]) }
func raw(v interface{}) []byte {
	b, e := omega.Canonical(v)
	if e != nil {
		panic(e)
	}
	return b
}
func number(v int64) json.Number { return json.Number(strconv.FormatInt(v, 10)) }
func fail(s string) error        { return errors.New(s) }
func obj(v interface{}) (omega.Object, error) {
	o, ok := v.(omega.Object)
	if !ok {
		return nil, fail("INVALID_ARGUMENT")
	}
	return o, nil
}
func exact(o omega.Object, keys ...string) bool {
	if len(o) != len(keys) {
		return false
	}
	for _, k := range keys {
		if _, ok := o[k]; !ok {
			return false
		}
	}
	return true
}

var labelPattern = regexp.MustCompile(`^[a-zA-Z0-9_.:/-]{1,128}$`)

func text(v interface{}) (string, error) {
	s, ok := v.(string)
	if !ok || !labelPattern.MatchString(s) {
		return "", fail("INVALID_ARGUMENT")
	}
	return s, nil
}
func integer(v interface{}) (int64, error) {
	s, ok := v.(json.Number)
	if !ok {
		return 0, fail("INVALID_ARGUMENT")
	}
	n, e := s.Int64()
	if e != nil || n < 0 {
		return 0, fail("INVALID_ARGUMENT")
	}
	return n, nil
}
func uuid() string {
	b := make([]byte, 16)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	b[6] = (b[6] & 15) | 64
	b[8] = (b[8] & 63) | 128
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[:4], b[4:6], b[6:8], b[8:10], b[10:])
}
func jobID(identity string) string {
	ns, _ := hex.DecodeString("6ba7b8119dad11d180b400c04fd430c8")
	h := sha1.New()
	h.Write(ns)
	h.Write([]byte(identity))
	b := h.Sum(nil)[:16]
	b[6] = (b[6] & 15) | 80
	b[8] = (b[8] & 63) | 128
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[:4], b[4:6], b[6:8], b[8:10], b[10:])
}

type Principal struct {
	CredentialFile string              `json:"credential_file"`
	Scopes         map[string][]string `json:"scopes"`
}
type Route struct {
	Scope string `json:"scope"`
	Owner string `json:"owner"`
}
type Policy struct {
	Principals map[string]Principal `json:"principals"`
	Routes     map[string]Route     `json:"routes"`
}
type Endpoint struct {
	URL            string `json:"url"`
	CAFile         string `json:"ca_file"`
	CredentialFile string `json:"credential_file"`
}
type Config struct {
	Profile     string   `json:"profile"`
	Scope       string   `json:"scope"`
	State       string   `json:"state"`
	Policy      string   `json:"policy"`
	Storage     string   `json:"storage"`
	Completion  Endpoint `json:"completion"`
	Certificate string   `json:"certificate"`
	Key         string   `json:"key"`
	Listen      string   `json:"listen"`
}
type Job struct {
	ID          string       `json:"id"`
	Owner       string       `json:"owner"`
	Fingerprint string       `json:"fingerprint"`
	Request     omega.Object `json:"request"`
	Envelope    omega.Object `json:"envelope"`
	Acceptance  omega.Object `json:"acceptance"`
	Result      omega.Object `json:"result"`
	Error       string       `json:"error"`
	Outbox      omega.Object `json:"outbox"`
	Delivered   bool         `json:"delivered"`
	Attempts    int          `json:"attempts"`
	Events      []string     `json:"events"`
}
type State struct {
	Profile string          `json:"profile"`
	Binding string          `json:"binding"`
	Source  string          `json:"source"`
	Commit  int             `json:"commit"`
	LastMS  int64           `json:"last_ms"`
	Jobs    map[string]*Job `json:"jobs"`
}
type Owner struct {
	failed     bool
	mu         sync.Mutex
	cfg        Config
	binding    string
	state      State
	atoms      *omega.Client
	lock       *os.File
	Clock      func() int64
	Hook       func(string)
	completion func(omega.Object) (omega.Object, error)
	get        func(omega.Ref, int64) (omega.Envelope, error)
	create     func(string, string, []byte, int64) (omega.Object, error)
}

func decodeFile(path string, out interface{}) error {
	b, e := os.ReadFile(path)
	if e != nil {
		return e
	}
	if _, e = omega.Decode(b); e != nil {
		return e
	}
	d := json.NewDecoder(bytes.NewReader(b))
	d.UseNumber()
	d.DisallowUnknownFields()
	return d.Decode(out)
}
func Open(cfg Config) (*Owner, error) {
	if cfg.Profile != "go-immutable-inspect-reference/1" || !strings.HasPrefix(cfg.Scope, "synthetic-") {
		return nil, fail("UNSUPPORTED_PROFILE")
	}
	if e := os.MkdirAll(filepath.Dir(cfg.State), 0700); e != nil {
		return nil, e
	}
	directory := filepath.Dir(cfg.State)
	lock, e := os.OpenFile(filepath.Join(directory, "owner.lock"), os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	if e = syscall.Flock(int(lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		lock.Close()
		return nil, fail("OVERLOADED")
	}
	done := false
	defer func() {
		if !done {
			lock.Close()
		}
	}()
	if _, e := os.Stat(filepath.Join(directory, "restore-fence.json")); e == nil || !os.IsNotExist(e) {
		return nil, fail("UNAUTHORIZED")
	}
	seal := raw(omega.Object{"composition": "omega-single-node-sustained-preview/1", "role": "fusion-inspect-go", "scope": cfg.Scope})
	sealPath := filepath.Join(directory, "owner-seal.json")
	old, sealErr := os.ReadFile(sealPath)
	if os.IsNotExist(sealErr) {
		f, err := os.OpenFile(sealPath, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
		if err != nil {
			return nil, err
		}
		_, err = f.Write(seal)
		if err == nil {
			err = f.Sync()
		}
		closeErr := f.Close()
		if err != nil {
			return nil, err
		}
		if closeErr != nil {
			return nil, closeErr
		}
		dir, err := os.Open(directory)
		if err != nil {
			return nil, err
		}
		err = dir.Sync()
		dir.Close()
		if err != nil {
			return nil, err
		}
	} else if sealErr != nil {
		return nil, sealErr
	} else {
		decoded, err := omega.Decode(old)
		if err != nil || !bytes.Equal(raw(decoded), seal) {
			return nil, fail("CONFLICT")
		}
	}
	storage, e := omega.ReadConfig(cfg.Storage)
	if e != nil {
		return nil, e
	}
	if storage.Scope != cfg.Scope {
		return nil, fail("UNAUTHORIZED")
	}
	atoms, e := omega.New(storage)
	if e != nil {
		return nil, e
	}
	trust, e := os.ReadFile(cfg.Completion.CAFile)
	if e != nil {
		return nil, e
	}
	stable := omega.Object{"profile": cfg.Profile, "scope": cfg.Scope, "selection": Contract["selection"], "storage": storage, "completion_url": cfg.Completion.URL, "completion_ca_sha256": hash(trust)}
	// Canonical only accepts codec objects, so decode typed configuration first.
	typed, _ := json.Marshal(stable)
	v, e := omega.Decode(typed)
	if e != nil {
		return nil, e
	}
	binding := hash(raw(v))
	o := &Owner{cfg: cfg, binding: binding, atoms: atoms, lock: lock, Clock: func() int64 { return time.Now().UnixMilli() }, Hook: func(string) {}}
	o.get = atoms.Get
	o.create = atoms.CreateReceipt
	o.completion = func(q omega.Object) (omega.Object, error) {
		current, e := os.ReadFile(cfg.Completion.CAFile)
		if e != nil || hash(current) != hash(trust) {
			return nil, fail("CONFLICT")
		}
		return exchange(cfg.Completion, Contract["completion"].(string), q, 5000)
	}
	if _, e = os.Stat(cfg.State); os.IsNotExist(e) {
		o.state = State{Profile: cfg.Profile, Binding: binding, Source: uuid(), Jobs: map[string]*Job{}}
		if e = o.save(); e != nil {
			return nil, e
		}
	} else if e != nil {
		return nil, e
	} else {
		if e = decodeFile(cfg.State, &o.state); e != nil {
			return nil, e
		}
		if o.state.Profile != cfg.Profile || o.state.Binding != binding || o.validateStored() != nil {
			return nil, fail("CONFLICT")
		}
	}
	done = true
	return o, nil
}

// validateStored rejects corrupted accounting or fabricated closure on restart.
// It does not consult current authority: revocation must preserve retained state.
func (o *Owner) validateStored() error {
	if len(o.state.Jobs) > 128 || o.state.Jobs == nil || o.state.Commit < 1 || o.state.LastMS < 0 || len(o.state.Source) != 36 {
		return fail("CONFLICT")
	}
	for id, j := range o.state.Jobs {
		if j == nil || j.ID != id || j.Attempts < 0 || j.Attempts > 32 {
			return fail("CONFLICT")
		}
		if _, e := text(j.Owner); e != nil {
			return e
		}
		op, e := o.validate(j.Request)
		if e != nil || op != "submit" {
			return fail("CONFLICT")
		}
		identity := string(raw([]interface{}{j.Owner, o.cfg.Scope, "execution", "submit", j.Request["idempotency_key"]}))
		semantic := omega.Object{}
		for k, v := range j.Request {
			if k != "message_id" && k != "extensions" && k != "causation_id" {
				semantic[k] = v
			}
		}
		if jobID(identity) != id || hash(raw(semantic)) != j.Fingerprint || j.Envelope == nil || j.Acceptance == nil {
			return fail("CONFLICT")
		}
		if j.Acceptance["job_id"] != id || j.Acceptance["scope_ref"] != o.cfg.Scope || j.Acceptance["correlation_id"] != j.Request["correlation_id"] || j.Acceptance["reply_route"] != j.Request["reply_route"] {
			return fail("CONFLICT")
		}
		if j.Error != "" && (j.Error != "DEADLINE_EXCEEDED" || j.Result != nil) {
			return fail("CONFLICT")
		}
		expectedEvents := []string{"accepted"}
		if j.Result != nil || j.Error != "" {
			if j.Attempts < 1 || j.Outbox == nil {
				return fail("CONFLICT")
			}
			var result, errValue interface{}
			if j.Result != nil {
				if !exact(j.Result, "ref", "receipt") {
					return fail("CONFLICT")
				}
				r, e := omega.ParseRef(raw(j.Result["ref"]))
				if e != nil || r.Scope != o.cfg.Scope {
					return fail("CONFLICT")
				}
				result = j.Result
			}
			if j.Error != "" {
				errValue = j.Error
			}
			expected := omega.Object{"job_id": id, "correlation_id": j.Request["correlation_id"], "causation_id": j.Request["message_id"], "result": result, "error": errValue}
			if !bytes.Equal(raw(expected), raw(j.Outbox)) {
				return fail("CONFLICT")
			}
			expectedEvents = append(expectedEvents, "result-committed")
		} else if j.Outbox != nil || j.Delivered {
			return fail("CONFLICT")
		}
		if j.Delivered {
			if j.Attempts < 2 {
				return fail("CONFLICT")
			}
			expectedEvents = append(expectedEvents, "completion-delivered")
		}
		if len(j.Events) != len(expectedEvents) {
			return fail("CONFLICT")
		}
		for i := range expectedEvents {
			if j.Events[i] != expectedEvents[i] {
				return fail("CONFLICT")
			}
		}
	}
	return nil
}
func (o *Owner) Close() { o.lock.Close() }
func (o *Owner) save() (result error) {
	defer func() {
		if result != nil {
			o.failed = true
		}
	}()
	if o.failed {
		return fail("NOT_AVAILABLE")
	}
	now := o.Clock()
	if now < o.state.LastMS {
		return fail("CONFLICT")
	}
	o.state.LastMS = now
	o.state.Commit++
	b, e := json.Marshal(o.state)
	if e != nil {
		return e
	}
	if len(b) > omega.MaxWire {
		return fail("OVERLOADED")
	}
	f, e := os.CreateTemp(filepath.Dir(o.cfg.State), ".inspect-pending-")
	if e != nil {
		return e
	}
	name := f.Name()
	defer os.Remove(name)
	if e = f.Chmod(0600); e == nil {
		_, e = f.Write(b)
	}
	if e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e == nil {
		e = ce
	}
	if e != nil {
		return e
	}
	if e = os.Rename(name, o.cfg.State); e != nil {
		return e
	}
	d, e := os.Open(filepath.Dir(o.cfg.State))
	if e != nil {
		return e
	}
	defer d.Close()
	return d.Sync()
}
func (o *Owner) policy() (Policy, error) {
	var p Policy
	e := decodeFile(o.cfg.Policy, &p)
	return p, e
}
func (o *Owner) authenticate(token string) (string, error) {
	if len(token) < 16 {
		return "", fail("UNAUTHORIZED")
	}
	p, e := o.policy()
	if e != nil {
		return "", fail("UNAUTHORIZED")
	}
	found := ""
	for name, principal := range p.Principals {
		b, e := os.ReadFile(principal.CredentialFile)
		if e == nil && subtle.ConstantTimeCompare([]byte(strings.TrimSpace(string(b))), []byte(token)) == 1 {
			if found != "" {
				return "", fail("UNAUTHORIZED")
			}
			found = name
		}
	}
	if found == "" {
		return "", fail("UNAUTHORIZED")
	}
	return found, nil
}
func (o *Owner) authorize(principal, operation, route string) error {
	p, e := o.policy()
	if e != nil {
		return fail("UNAUTHORIZED")
	}
	selected, ok := p.Principals[principal]
	if !ok {
		return fail("UNAUTHORIZED")
	}
	allowed := false
	for _, permission := range selected.Scopes[o.cfg.Scope] {
		if permission == operation {
			allowed = true
		}
	}
	if !allowed {
		return fail("UNAUTHORIZED")
	}
	if route != "" {
		r, ok := p.Routes[route]
		if !ok || r.Scope != o.cfg.Scope || r.Owner != principal {
			return fail("UNAUTHORIZED")
		}
	}
	return nil
}
func (o *Owner) fresh(j *Job) error {
	deadline, e := integer(j.Request["deadline_ms"])
	if e != nil {
		return e
	}
	if o.Clock() < o.state.LastMS {
		return fail("CONFLICT")
	}
	if o.Clock() >= deadline {
		return fail("DEADLINE_EXCEEDED")
	}
	return nil
}

func (o *Owner) Invoke(token string, q omega.Object) (omega.Object, error) {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.failed {
		return nil, fail("NOT_AVAILABLE")
	}
	principal, e := o.authenticate(token)
	if e != nil {
		return nil, e
	}
	if q["profile"] != Contract["wrapper"] || q["selection"] != Contract["selection"] {
		return nil, fail("UNSUPPORTED_PROFILE")
	}
	if exact(q, "profile", "selection", "events") {
		result, err := o.events(principal, q)
		if err != nil {
			return nil, err
		}
		if current, err := o.authenticate(token); err != nil || current != principal {
			return nil, fail("UNAUTHORIZED")
		}
		if err := o.authorize(principal, "execution.status", ""); err != nil {
			return nil, err
		}
		return result, nil
	}
	if !exact(q, "profile", "selection", "request") && !exact(q, "profile", "selection", "request", "envelope") {
		return nil, fail("INVALID_ARGUMENT")
	}
	request, e := obj(q["request"])
	if e != nil {
		return nil, e
	}
	op, e := o.validate(request)
	if e != nil {
		return nil, e
	}
	if e = o.authorize(principal, "execution."+op, ""); e != nil {
		return nil, e
	}
	body, _ := obj(request["body"])
	var value omega.Object
	if op != "submit" {
		if value, ok := request["deadline_ms"]; ok {
			d, e := integer(value)
			if e != nil {
				return nil, e
			}
			if o.Clock() >= d {
				return nil, fail("DEADLINE_EXCEEDED")
			}
		}
	}
	if op == "submit" {
		value, e = o.submit(principal, request, q["envelope"])
	} else {
		id, _ := text(body["job_id"])
		job, ok := o.state.Jobs[id]
		if !ok || job.Owner != principal {
			return nil, fail("NOT_FOUND")
		}
		if op == "result" {
			if job.Error != "" {
				return nil, fail(job.Error)
			}
			if job.Result == nil {
				return nil, fail("NOT_AVAILABLE")
			}
			value = job.Result
		} else {
			state := "queued"
			var errValue interface{}
			var durability interface{}
			if job.Error != "" {
				state = "failed"
				errValue = job.Error
			} else if job.Result != nil {
				state = "succeeded"
				r, _ := obj(job.Result["receipt"])
				durability = r["durability"]
			}
			delivery := "not-observed"
			if job.Delivered {
				delivery = "mailbox-accepted"
			}
			value = omega.Object{"job_id": id, "execution": state, "error": errValue, "scope_ref": o.cfg.Scope, "correlation_id": job.Request["correlation_id"], "result_persistence": durability, "completion_delivery": delivery, "chain": nil}
		}
	}
	if e != nil {
		return nil, e
	}
	if current, e := o.authenticate(token); e != nil || current != principal {
		return nil, fail("UNAUTHORIZED")
	}
	if e = o.authorize(principal, "execution."+op, ""); e != nil {
		return nil, e
	}
	return omega.Object{"ok": value, "provider": Contract["selection"], "request_digest": hash(raw(q))}, nil
}

func (o *Owner) validate(r omega.Object) (string, error) {
	mandatory := []string{"message_id", "interface_ref", "operation", "scope_ref", "profile", "body"}
	allowed := map[string]bool{}
	for _, k := range append(mandatory, "idempotency_key", "correlation_id", "reply_route", "causation_id", "deadline_ms", "required_features", "extensions") {
		allowed[k] = true
	}
	for _, k := range mandatory {
		if _, ok := r[k]; !ok {
			return "", fail("INVALID_ARGUMENT")
		}
	}
	for k := range r {
		if !allowed[k] {
			return "", fail("INVALID_ARGUMENT")
		}
	}
	iface, e := obj(r["interface_ref"])
	if e != nil || !exact(iface, "id", "version") || iface["id"] != "execution" || iface["version"] != "1.0.0" {
		return "", fail("UNSUPPORTED_VERSION")
	}
	if r["profile"] != "inspect-atom/2" {
		return "", fail("UNSUPPORTED_PROFILE")
	}
	if r["scope_ref"] != o.cfg.Scope {
		return "", fail("UNAUTHORIZED")
	}
	for _, k := range []string{"message_id", "idempotency_key", "correlation_id", "reply_route", "causation_id"} {
		if v, present := r[k]; present {
			if _, e = text(v); e != nil {
				return "", e
			}
		}
	}
	if v, present := r["deadline_ms"]; present {
		if n, err := integer(v); err != nil || n == 0 {
			return "", fail("INVALID_ARGUMENT")
		}
	}
	op, e := text(r["operation"])
	if e != nil {
		return "", e
	}
	body, e := obj(r["body"])
	if e != nil {
		return "", e
	}
	if f, ok := r["required_features"]; ok {
		a, ok := f.([]interface{})
		if !ok || len(a) != 0 {
			return "", fail("UNSUPPORTED_PROFILE")
		}
	}
	if x, ok := r["extensions"]; ok {
		if _, ok = x.(omega.Object); !ok {
			return "", fail("INVALID_ARGUMENT")
		}
	}
	if op == "submit" {
		if !exact(body, "operation", "ref") || body["operation"] != "inspect_atom" {
			return "", fail("UNSUPPORTED_OPERATION")
		}
		ref, e := omega.ParseRef(raw(body["ref"]))
		if e != nil {
			return "", e
		}
		if ref.Scope != o.cfg.Scope {
			return "", fail("UNAUTHORIZED")
		}
		for _, k := range []string{"idempotency_key", "correlation_id", "reply_route"} {
			if _, e = text(r[k]); e != nil {
				return "", e
			}
		}
		d, e := integer(r["deadline_ms"])
		if e != nil || d == 0 {
			return "", fail("INVALID_ARGUMENT")
		}
	} else if op == "status" || op == "result" {
		if !exact(body, "job_id") {
			return "", fail("INVALID_ARGUMENT")
		}
		if _, e = text(body["job_id"]); e != nil {
			return "", e
		}
	} else {
		return "", fail("UNSUPPORTED_OPERATION")
	}
	if len(raw(r)) > 100000 {
		return "", fail("INVALID_ARGUMENT")
	}
	return op, nil
}

func (o *Owner) submit(principal string, r omega.Object, envelope interface{}) (omega.Object, error) {
	route, _ := text(r["reply_route"])
	if e := o.authorize(principal, "execution.submit", route); e != nil {
		return nil, e
	}
	if e := o.authorize(principal, "atom.storage.get", ""); e != nil {
		return nil, e
	}
	env, e := obj(envelope)
	if e != nil {
		return nil, fail("UNSUPPORTED_PROFILE")
	}
	body, _ := obj(r["body"])
	desc := Contract["descriptor"].(omega.Object)
	published := Contract["envelope"].(omega.Object)
	expected := omega.Object{"profile": published["profile"], "task": r["idempotency_key"], "correlation": r["correlation_id"], "scope": o.cfg.Scope,
		"operation": omega.Object{"interface": r["interface_ref"], "profile": r["profile"], "name": "inspect_atom"}, "inputs": omega.Object{"ref": body["ref"]}, "initiator": principal,
		"delegation": omega.Object{"service": "execution", "actor": "worker", "authority": "current-scoped-policy"}, "provider": omega.Object{"id": desc["provider"], "selection": Contract["selection"]},
		"disclosure": "approved-synthetic-agent-artifact", "deadline_ms": r["deadline_ms"], "limits": published["limits"],
		"completion": omega.Object{"owner": principal, "route": route, "profile": "durable-mailbox/2"}, "guarantee": "one-logical-admission-independent-owner-commits"}
	if !bytes.Equal(raw(env), raw(expected)) {
		return nil, fail("CONFLICT")
	}
	identity := string(raw([]interface{}{principal, o.cfg.Scope, "execution", "submit", r["idempotency_key"]}))
	id := jobID(identity)
	semantic := omega.Object{}
	for k, v := range r {
		if k != "message_id" && k != "extensions" && k != "causation_id" {
			semantic[k] = v
		}
	}
	fingerprint := hash(raw(semantic))
	if old, ok := o.state.Jobs[id]; ok {
		if old.Owner != principal || old.Fingerprint != fingerprint || !bytes.Equal(raw(old.Envelope), raw(env)) {
			return nil, fail("CONFLICT")
		}
		return old.Acceptance, nil
	}
	if len(o.state.Jobs) >= 128 {
		return nil, fail("OVERLOADED")
	}
	pending := 0
	for _, j := range o.state.Jobs {
		if !j.Delivered {
			pending++
		}
	}
	if pending >= 4 {
		return nil, fail("OVERLOADED")
	}
	job := &Job{ID: id, Owner: principal, Fingerprint: fingerprint, Request: r, Envelope: env, Events: []string{"accepted"}}
	if e = o.fresh(job); e != nil {
		return nil, e
	}
	job.Acceptance = omega.Object{"job_id": id, "execution": "queued", "acceptance": "process-restart", "evidence": omega.Object{"backend": "go-atomic-file", "fsync": "file-and-parent-directory", "single_writer": true},
		"scope_ref": o.cfg.Scope, "correlation_id": r["correlation_id"], "reply_route": route, "completion_delivery": "not-observed", "chain": nil}
	// Reserve logical journal space for every pending completion before any
	// mutation or dependency call. Duplicate acceptance replay happened above.
	projected, e := o.completionProjection(job)
	if e != nil || projected > omega.MaxWire {
		return nil, fail("OVERLOADED")
	}
	deadline, _ := integer(r["deadline_ms"])
	ref, e := omega.ParseRef(raw(body["ref"]))
	if e != nil {
		return nil, e
	}
	item, e := o.get(ref, deadline)
	if e != nil {
		return nil, e
	}
	if len(item.Bytes) > 4096 {
		return nil, fail("INVALID_ARGUMENT")
	}
	if e = o.fresh(job); e != nil {
		return nil, e
	}
	if e = o.authorize(principal, "execution.submit", route); e != nil {
		return nil, e
	}
	if e = o.authorize(principal, "atom.storage.get", ""); e != nil {
		return nil, e
	}
	o.state.Jobs[id] = job
	if e = o.save(); e != nil {
		return nil, e
	}
	o.Hook("after_acceptance_commit")
	return job.Acceptance, nil
}

func (o *Owner) events(principal string, q omega.Object) (omega.Object, error) {
	if e := o.authorize(principal, "execution.status", ""); e != nil {
		return nil, e
	}
	b, e := obj(q["events"])
	if e != nil || !exact(b, "job_id", "source", "after", "limit") {
		return nil, fail("INVALID_ARGUMENT")
	}
	id, e := text(b["job_id"])
	if e != nil {
		return nil, e
	}
	job, ok := o.state.Jobs[id]
	if !ok || job.Owner != principal {
		return nil, fail("NOT_FOUND")
	}
	after, e := integer(b["after"])
	if e != nil || after > 384 {
		return nil, fail("INVALID_ARGUMENT")
	}
	limit, e := integer(b["limit"])
	if e != nil || limit < 1 || limit > 16 {
		return nil, fail("INVALID_ARGUMENT")
	}
	source := b["source"]
	if source != nil {
		if _, ok := source.(string); !ok {
			return nil, fail("INVALID_ARGUMENT")
		}
	}
	gap := (source != nil && source != o.state.Source) || after > int64(len(job.Events)) || (source == nil && after != 0)
	events := []interface{}{}
	next := after
	if !gap {
		end := int64(len(job.Events))
		if after+limit < end {
			end = after + limit
		}
		for i := after; i < end; i++ {
			events = append(events, omega.Object{"sequence": number(i + 1), "kind": job.Events[i], "job_id": id})
		}
		next = end
	}
	value := omega.Object{"profile": Contract["event_profile"], "source": o.state.Source, "scope": o.cfg.Scope, "job_id": id, "head": number(int64(len(job.Events))), "after": number(after), "next": number(next), "gap": gap, "ordering": "per-task-owner-commit", "events": events}
	return omega.Object{"value": value, "provider": Contract["selection"], "request_digest": hash(raw(q))}, nil
}

func (o *Owner) WorkOne() error {
	o.mu.Lock()
	defer o.mu.Unlock()
	if o.failed {
		return fail("NOT_AVAILABLE")
	}
	var job *Job
	for _, j := range o.state.Jobs {
		if !j.Delivered && j.Attempts < 32 {
			job = j
			break
		}
	}
	if job == nil {
		return nil
	}
	route, _ := text(job.Request["reply_route"])
	if e := o.authorize(job.Owner, "execution.submit", route); e != nil {
		return e
	}
	if e := o.authorize(job.Owner, "atom.storage.get", ""); e != nil {
		return e
	}
	if e := o.authorize("worker", "atom.storage.get", ""); e != nil {
		return e
	}
	job.Attempts++
	if e := o.save(); e != nil {
		return e
	}
	o.Hook("after_worker_reservation")
	if job.Result == nil && job.Error == "" {
		if e := o.fresh(job); e != nil {
			if e.Error() != "DEADLINE_EXCEEDED" {
				return e
			}
			job.Error = e.Error()
		} else {
			body, _ := obj(job.Request["body"])
			ref, e := omega.ParseRef(raw(body["ref"]))
			if e != nil {
				return e
			}
			deadline, _ := integer(job.Request["deadline_ms"])
			item, e := o.get(ref, deadline)
			if e != nil {
				return e
			}
			if len(item.Bytes) > 4096 {
				return fail("INVALID_ARGUMENT")
			}
			if e = o.fresh(job); e != nil {
				return e
			}
			if e = o.authorize(job.Owner, "execution.submit", route); e != nil {
				return e
			}
			if e = o.authorize(job.Owner, "atom.storage.get", ""); e != nil {
				return e
			}
			output := raw(omega.Object{"digest": hash(item.Bytes), "length": number(int64(len(item.Bytes))), "operation": "inspect_atom", "provider_version": "0.1.0"})
			if e = o.authorize("worker", "atom.storage.create", ""); e != nil {
				return e
			}
			result, e := o.create("result/"+job.ID, "application/json", output, deadline)
			if e != nil {
				return e
			}
			o.Hook("after_result_persist")
			// The selected client validates the storage receipt. Bound its
			// retained JSON size as well: it appears in both result and outbox.
			// An oversized upstream receipt leaves this attempt spent and the
			// prior acceptance intact; it must not poison the owner journal.
			retained, sizeErr := json.Marshal(result)
			if sizeErr != nil || len(retained) > RetainedResultLimit {
				return fail("NOT_AVAILABLE")
			}
			job.Result = result
		}
		var errValue interface{}
		if job.Error != "" {
			errValue = job.Error
		}
		var resultValue interface{}
		if job.Result != nil {
			resultValue = job.Result
		}
		job.Outbox = omega.Object{"job_id": job.ID, "correlation_id": job.Request["correlation_id"], "causation_id": job.Request["message_id"], "result": resultValue, "error": errValue}
		job.Events = append(job.Events, "result-committed")
		if e := o.save(); e != nil {
			return e
		}
		o.Hook("after_result_outbox_commit")
		return nil
	}
	q := omega.Object{"profile": Contract["wrapper"], "id": uuid(), "scope": o.cfg.Scope, "route": route, "delivery_id": job.ID, "completion": job.Outbox}
	reply, e := o.completion(q)
	if e != nil {
		return e
	}
	if !exact(reply, "id", "request_digest", "value") || reply["id"] != q["id"] || reply["request_digest"] != hash(raw(q)) {
		return fail("NOT_AVAILABLE")
	}
	v, e := obj(reply["value"])
	if e != nil || !exact(v, "delivery_id", "acceptance", "delivery", "evidence", "scope_ref", "route", "correlation_id") || v["delivery_id"] != job.ID || v["scope_ref"] != o.cfg.Scope || v["route"] != route || v["correlation_id"] != job.Request["correlation_id"] || v["acceptance"] != "process-restart" || v["delivery"] != "not-observed" {
		return fail("NOT_AVAILABLE")
	}
	if _, e = obj(v["evidence"]); e != nil {
		return fail("NOT_AVAILABLE")
	}
	o.Hook("after_delivery_acceptance")
	if e = o.authorize(job.Owner, "execution.submit", route); e != nil {
		return e
	}
	job.Delivered = true
	job.Events = append(job.Events, "completion-delivered")
	if e = o.save(); e != nil {
		return e
	}
	o.Hook("after_delivery_capture")
	return nil
}

func exchange(ep Endpoint, path string, q omega.Object, timeout int64) (omega.Object, error) {
	u, e := url.Parse(ep.URL)
	if e != nil || u.Scheme != "https" || u.User != nil || u.RawQuery != "" || u.Fragment != "" || u.Path != "" {
		return nil, fail("UNAUTHORIZED")
	}
	pem, e := os.ReadFile(ep.CAFile)
	if e != nil {
		return nil, e
	}
	roots := x509.NewCertPool()
	if !roots.AppendCertsFromPEM(pem) {
		return nil, fail("UNAUTHORIZED")
	}
	credential, e := os.ReadFile(ep.CredentialFile)
	if e != nil {
		return nil, e
	}
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeout)*time.Millisecond)
	defer cancel()
	req, e := http.NewRequestWithContext(ctx, "POST", ep.URL+path, bytes.NewReader(raw(q)))
	if e != nil {
		return nil, e
	}
	req.Header.Set("Authorization", "Bearer "+strings.TrimSpace(string(credential)))
	req.Header.Set("Content-Type", "application/json")
	transport := &http.Transport{TLSClientConfig: &tls.Config{RootCAs: roots, MinVersion: tls.VersionTLS12}, DisableKeepAlives: true}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, CheckRedirect: func(*http.Request, []*http.Request) error { return fail("UNAUTHORIZED") }}
	reply, e := client.Do(req)
	if e != nil {
		return nil, fail("NOT_AVAILABLE")
	}
	defer reply.Body.Close()
	data, e := io.ReadAll(io.LimitReader(reply.Body, omega.MaxWire+1))
	if e != nil || len(data) > omega.MaxWire || reply.StatusCode != 200 {
		return nil, fail("NOT_AVAILABLE")
	}
	v, e := omega.Decode(data)
	if e != nil {
		return nil, e
	}
	return obj(v)
}
